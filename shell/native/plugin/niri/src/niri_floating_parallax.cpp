#include "niri_floating_parallax.h"

#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonObject>
#include <QSet>
#include <QPointer>
#include <QTimer>
#include <algorithm>
#include <cmath>

namespace {
QJsonObject moveRequest(quint64 id, double delta)
{
    return {
        {QStringLiteral("Action"),
         QJsonObject{{QStringLiteral("MoveFloatingWindow"),
                      QJsonObject{{QStringLiteral("id"), QJsonValue::fromVariant(id)},
                                  {QStringLiteral("x"), QJsonObject{{QStringLiteral("AdjustFixed"), delta}}},
                                  {QStringLiteral("y"), QJsonObject{{QStringLiteral("AdjustFixed"), 0}}}}}}}};
}

bool different(double a, double b) { return std::abs(a - b) > 0.01; }
} // namespace

NiriFloatingParallax::NiriFloatingParallax(QObject *parent) : QObject(parent) {}

NiriFloatingParallax *NiriFloatingParallax::shared()
{
    // QML engines may overlap during reload. Keep both the ledger and the
    // asynchronous transport outside them so restoration and reapplication
    // remain a single serialized transaction per window.
    static QPointer<NiriFloatingParallax> instance;
    if (!instance)
        instance = new NiriFloatingParallax(QCoreApplication::instance());
    return instance;
}

quint64 NiriFloatingParallax::acquire() { return ++m_lease; }

void NiriFloatingParallax::release(quint64 lease)
{
    if (owns(lease) && !QCoreApplication::closingDown())
        setOffsets({});
}

void NiriFloatingParallax::setConnected(bool connected, const QString &socketPath)
{
    const bool newSocket = connected && m_socketPath != socketPath;
    if (!newSocket && connected == m_connected)
        return;
    if (newSocket) {
        m_states.clear();
        m_windows.clear();
        m_socketPath = socketPath;
    }
    m_connected = connected;
    ++m_generation;
    for (auto &state : m_states) {
        state.pending = false;
        state.serial = ++m_serial;
    }
}

void NiriFloatingParallax::setWindows(const QList<NiriWindow> &windows)
{
    if (!m_connected)
        return;
    m_windows = windows;
    QSet<quint64> live;
    for (const auto &window : windows)
        live.insert(window.id);
    m_states.removeIf([&live](const auto &entry) { return !live.contains(entry.key()); });
    reconcile();
}

void NiriFloatingParallax::setOffsets(const QVariantMap &offsets)
{
    QHash<quint64, double> next;
    for (auto it = offsets.begin(); it != offsets.end(); ++it) {
        bool validId = false;
        bool validOffset = false;
        const auto id = it.key().toULongLong(&validId);
        const auto offset = it.value().toDouble(&validOffset);
        if (validId && id && validOffset && std::isfinite(offset) && different(offset, 0))
            next.insert(id, std::clamp(offset, -4096.0, 4096.0));
    }
    if (next == m_offsets)
        return;
    m_offsets = next;
    reconcile();
}

double NiriFloatingParallax::target(quint64 workspaceId) const { return m_offsets.value(workspaceId); }

bool NiriFloatingParallax::current(quint64 id, quint64 serial, quint64 generation) const
{
    const auto it = m_states.constFind(id);
    return m_connected && generation == m_generation && it != m_states.cend() && it->pending &&
           serial == it->serial;
}

void NiriFloatingParallax::reconcile()
{
    if (!m_connected)
        return;
    for (const auto &window : m_windows) {
        // Keep settled offsets while minimized or tiled: niri remembers the
        // floating position, so subtract our displacement when it floats again.
        if (!window.isFloating || window.isMinimized || !window.workspaceId || !window.hasLayoutPosition)
            continue;
        auto &state = m_states[window.id];
        if (state.pending || (!state.sent && !different(target(window.workspaceId), state.settledTarget)))
            continue;
        state.pending = true;
        state.serial = ++m_serial;
        readPosition(window.id, state.serial, state.sent);
    }
}

void NiriFloatingParallax::finish(quint64 id, bool continueWithLatest)
{
    auto it = m_states.find(id);
    if (it == m_states.end())
        return;
    it->pending = false;
    if (continueWithLatest)
        QTimer::singleShot(0, this, &NiriFloatingParallax::reconcile);
}

void NiriFloatingParallax::readPosition(quint64 id, quint64 serial, bool afterMove)
{
    const auto generation = m_generation;
    m_client.requestAsync(
        QStringLiteral("Windows"), this,
        [this, id, serial, generation, afterMove](const QJsonValue &value, const QString &error) {
            if (!current(id, serial, generation))
                return;
            if (!error.isEmpty() || !value.isArray()) {
                finish(id, false);
                return;
            }
            QJsonObject window;
            for (const auto &entry : value.toArray()) {
                if (quint64(entry.toObject().value(QStringLiteral("id")).toInteger()) == id) {
                    window = entry.toObject();
                    break;
                }
            }
            if (window.isEmpty()) {
                m_states.remove(id);
                return;
            }
            const auto point = window.value(QStringLiteral("layout"))
                                   .toObject()
                                   .value(QStringLiteral("tile_pos_in_workspace_view"))
                                   .toArray();
            const auto workspaceId = quint64(window.value(QStringLiteral("workspace_id")).toInteger());
            if (!window.value(QStringLiteral("is_floating")).toBool() ||
                window.value(QStringLiteral("is_minimized")).toBool() || !workspaceId || point.size() != 2) {
                finish(id, false);
                return;
            }

            auto &state = m_states[id];
            const auto x = point.at(0).toDouble();
            if (afterMove) {
                // Static IPC positions exclude niri's animated render offset. Measure
                // the actual displacement: an edge-clamped +96 may only move +20.
                // Restoration subtracts +20, preserving any subsequent user movement.
                state.appliedOffset = state.startOffset + x - state.startX;
                state.settledTarget = state.sentTarget;
                // Restoring may also clamp after a user move or output resize.
                // Adopt the reachable position instead of carrying a residual
                // into the next activation.
                if (!different(state.sentTarget, 0))
                    state.appliedOffset = 0;
                state.sent = false;
                finish(id, true);
                return;
            }

            const auto desired = target(workspaceId);
            const auto delta = desired - state.appliedOffset;
            if (!different(desired, state.settledTarget) || !different(delta, 0)) {
                state.settledTarget = desired;
                finish(id, false);
                return;
            }
            state.startX = x;
            state.startOffset = state.appliedOffset;
            state.sentTarget = desired;
            state.sent = true;
            m_client.requestAsync(
                moveRequest(id, delta), this,
                [this, id, serial, generation](const QJsonValue &, const QString &) {
                    if (!current(id, serial, generation))
                        return;
                    // An error/timeout can occur after niri has already moved the
                    // window. Always measure; never infer displacement from the reply.
                    readPosition(id, serial, true);
                },
                3000, m_socketPath);
        },
        3000, m_socketPath);
}

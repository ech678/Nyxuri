#include "window_preview_manager.h"
#include <memory>

WindowPreviewManager::WindowPreviewManager(QObject *parent) : QObject(parent)
{
    m_reconcile.setSingleShot(true);
    m_reconcile.setInterval(0);
    connect(&m_reconcile, &QTimer::timeout, this, &WindowPreviewManager::reconcile);
    m_snapshotTimeout.setSingleShot(true);
    m_snapshotTimeout.setInterval(750);
    connect(&m_snapshotTimeout, &QTimer::timeout, this, [this] { finishSnapshot(m_snapshot); });
    connect(&m_catalog, &WindowCaptureProbe::changed, this, [this] {
        m_reconcile.start();
        emit statusChanged();
    });
    connect(&m_catalog, &WindowCaptureProbe::windowsChanged, this, [this] { m_reconcile.start(); });
}
WindowPreviewManager::~WindowPreviewManager()
{
    disconnect(&m_catalog, nullptr, this, nullptr);
    close();
}
bool WindowPreviewManager::supported() const { return m_open && m_catalog.ready() && m_catalog.supported(); }
void WindowPreviewManager::open(const QString &displayName)
{
    close();
    m_display = displayName;
    m_open = true;
    m_catalog.open(displayName);
}
void WindowPreviewManager::close()
{
    m_open = false;
    // The cache's identity is (connection generation, exact ext identifier).
    // Also invalidate on lock/suspend, even when the compositor stays connected.
    m_cache.reset(++m_generation);
    m_waiters.clear();
    m_prefetch.clear();
    m_snapshot.clear();
    m_snapshotTimeout.stop();
    m_targets.clear();
    m_live.clear();
    m_minimized.clear();
    clearCaptures();
    m_catalog.close();
    m_reconcile.stop();
    emit capturesChanged();
}
void WindowPreviewManager::setWindows(const QStringList &live, const QStringList &minimized)
{
    const QSet<QString> next(live.begin(), live.end());
    const QSet<QString> hidden(minimized.begin(), minimized.end());
    const auto newlyVisible = (next - m_live) | (m_minimized - hidden);
    m_live = next;
    m_minimized = hidden;
    m_cache.retain(m_live);
    for (const auto &id : newlyVisible)
        prefetch(id);
    m_reconcile.start();
}
void WindowPreviewManager::setTargets(const QString &consumer, const QStringList &identifiers)
{
    if (consumer.isEmpty())
        return;
    if (identifiers.isEmpty())
        m_targets.remove(consumer);
    else
        m_targets.insert(consumer, identifiers);
    m_reconcile.start();
}
void WindowPreviewManager::release(const QString &consumer)
{
    m_targets.remove(consumer);
    m_reconcile.start();
}
WindowCaptureProbe *WindowPreviewManager::captureFor(const QString &identifier) const
{
    return m_captures.value(identifier, nullptr);
}
WindowPreviewFrame *WindowPreviewManager::frameFor(const QString &identifier)
{
    return m_open && m_live.contains(identifier) ? m_cache.frameFor(identifier) : nullptr;
}
void WindowPreviewManager::prefetch(const QString &id)
{
    if (!m_open || !m_live.contains(id) || m_minimized.contains(id) || m_cache.hasFrame(id) ||
        m_snapshot == id || m_prefetch.contains(id))
        return;
    m_prefetch.append(id);
    m_reconcile.start();
}
void WindowPreviewManager::requestSnapshot(const QString &id)
{
    if (m_waiters.contains(id))
        return;
    const auto serial = ++m_requestSerial;
    m_waiters.insert(id, serial);
    // The deadline includes time spent waiting behind another one-shot capture.
    // Minimize must proceed even without capture support or a responsive client.
    QTimer::singleShot(supported() && m_live.contains(id) && !m_minimized.contains(id) ? 250 : 0, this,
                       [this, id, serial] {
                           if (m_waiters.value(id) == serial)
                               finishSnapshot(id);
                       });
    if (supported() && m_live.contains(id) && !m_minimized.contains(id) && m_snapshot != id) {
        m_prefetch.removeAll(id);
        m_prefetch.prepend(id);
        m_reconcile.start();
    }
}
void WindowPreviewManager::finishSnapshot(const QString &identifier)
{
    const QString id = identifier;
    if (id.isEmpty())
        return;
    m_prefetch.removeAll(id);
    if (m_snapshot == id) {
        m_snapshot.clear();
        m_snapshotTimeout.stop();
    }
    const bool notify = m_waiters.remove(id) > 0;
    m_reconcile.start();
    if (notify)
        emit snapshotFinished(id);
}
void WindowPreviewManager::removeCapture(const QString &id)
{
    auto *capture = m_captures.take(id);
    if (!capture)
        return;
    disconnect(capture, nullptr, this, nullptr);
    capture->close();
    capture->deleteLater();
}
void WindowPreviewManager::clearCaptures()
{
    if (m_captures.isEmpty())
        return;
    for (const auto &id : m_captures.keys())
        removeCapture(id);
    emit capturesChanged();
}
void WindowPreviewManager::reconcile()
{
    if (!supported()) {
        clearCaptures();
        if (m_catalog.ready() || !m_catalog.error().isEmpty()) {
            m_cache.reset(m_generation);
            for (const auto &id : m_waiters.keys())
                finishSnapshot(id);
            m_prefetch.clear();
            m_snapshot.clear();
            m_snapshotTimeout.stop();
        }
        return;
    }
    QSet<QString> available, wanted;
    for (const auto &window : m_catalog.windows())
        available.insert(window.toMap().value("identifier").toString());
    available.intersect(m_live);
    m_cache.retain(available);
    if (!m_snapshot.isEmpty() && (!available.contains(m_snapshot) || m_minimized.contains(m_snapshot)))
        finishSnapshot(m_snapshot);
    const auto queued = m_prefetch;
    for (const auto &id : queued) {
        if (!m_live.contains(id) || m_minimized.contains(id))
            finishSnapshot(id);
    }
    // At most one background capture. Hover streams still share one session per window.
    if (m_snapshot.isEmpty()) {
        for (const auto &id : m_prefetch) {
            if (available.contains(id)) {
                m_snapshot = id;
                break;
            }
        }
        if (!m_snapshot.isEmpty()) {
            m_prefetch.removeAll(m_snapshot);
            m_snapshotTimeout.start();
        }
    }
    for (const auto &identifiers : m_targets)
        for (const auto &id : identifiers)
            if (available.contains(id) && !m_minimized.contains(id))
                wanted.insert(id);
    if (!m_snapshot.isEmpty())
        wanted.insert(m_snapshot);
    bool changed = false;
    for (const auto &id : m_captures.keys()) {
        if (!wanted.contains(id)) {
            removeCapture(id);
            changed = true;
        }
    }
    for (const auto &id : wanted) {
        if (m_captures.contains(id))
            continue;
        auto *capture = new WindowCaptureProbe(this);
        capture->setMaximumDimension(512);
        capture->setFrameInterval(66);
        m_captures.insert(id, capture);
        const auto generation = m_generation;
        connect(capture, &WindowCaptureProbe::imageChanged, this, [this, capture, id, generation] {
            if (generation != m_generation || m_captures.value(id) != capture || !m_live.contains(id) ||
                capture->image().isNull())
                return;
            m_cache.store(generation, id, capture->image(), capture->sourceSize());
            if (m_snapshot == id || m_waiters.contains(id))
                finishSnapshot(id);
        });
        auto started = std::make_shared<bool>(false);
        connect(capture, &WindowCaptureProbe::changed, this, [this, capture, id, started, generation] {
            if (generation != m_generation || m_captures.value(id) != capture)
                return;
            const auto error = capture->error();
            // A stopped session or revoked protocol is not a temporary missing frame.
            if (error == "session-stopped" || error == "capture-failed:2" || error == "target-closed" ||
                error == "capture-global-removed" || error == "toplevel-list-finished" ||
                error == "wayland-disconnected")
                m_cache.invalidate(id);
            if (!error.isEmpty() && (m_snapshot == id || m_waiters.contains(id)))
                finishSnapshot(id);
            if (*started || !capture->ready() || !capture->supported())
                return;
            *started = true;
            QTimer::singleShot(0, capture, [this, capture, id, generation] {
                if (generation == m_generation && m_captures.value(id) == capture && m_live.contains(id) &&
                    !m_minimized.contains(id))
                    capture->start(id);
            });
        });
        capture->open(m_display);
        changed = true;
    }
    if (changed)
        emit capturesChanged();
}

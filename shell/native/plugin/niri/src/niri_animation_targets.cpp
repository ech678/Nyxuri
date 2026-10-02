#include "niri_animation_targets.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

NiriAnimationTargets::NiriAnimationTargets(QObject *parent) : QObject(parent)
{
    m_send.setSingleShot(true);
    m_deadline.setSingleShot(true);
    m_deadline.setInterval(1500);
    connect(&m_send, &QTimer::timeout, this, &NiriAnimationTargets::publish);
    connect(&m_deadline, &QTimer::timeout, this, &NiriAnimationTargets::reconnect);
    connect(&m_socket, &QLocalSocket::connected, this, &NiriAnimationTargets::publish);
    connect(&m_socket, &QLocalSocket::disconnected, this, &NiriAnimationTargets::reconnect);
    connect(&m_socket, &QLocalSocket::errorOccurred, this, &NiriAnimationTargets::reconnect);
    connect(&m_socket, &QLocalSocket::readyRead, this, [this] {
        if (m_socket.bytesAvailable() > 65536) {
            reconnect();
            return;
        }
        if (!m_socket.canReadLine())
            return;
        const auto reply = QJsonDocument::fromJson(m_socket.readLine()).object();
        m_deadline.stop();
        m_pending = false;
        if (!reply.contains("Ok")) {
            qWarning("Niri rejected window animation targets");
            // publish() already cleared dirty for this payload. A newer pending value
            // must still be sent, even when the preceding value was rejected.
        }
        if (m_dirty)
            m_send.start(33);
    });
}
NiriAnimationTargets::~NiriAnimationTargets()
{
    disconnect(&m_socket, nullptr, this, nullptr);
    m_socket.abort();
}
void NiriAnimationTargets::setEnabled(bool enabled)
{
    if (m_enabled == enabled)
        return;
    m_enabled = enabled;
    m_dirty = true;
    m_pending = false;
    m_deadline.stop();
    m_send.stop();
    if (enabled)
        m_send.start(0);
    else
        m_socket.abort();
    emit enabledChanged();
}
void NiriAnimationTargets::setTargets(const QVariantList &targets)
{
    if (m_targets == targets)
        return;
    m_targets = targets;
    m_dirty = true;
    // Coalesce geometry changes without blocking the QML render thread on IPC.
    if (m_enabled && !m_send.isActive())
        m_send.start(33);
    emit targetsChanged();
}
void NiriAnimationTargets::reconnect()
{
    m_deadline.stop();
    m_pending = false;
    m_dirty = true;
    if (m_socket.state() != QLocalSocket::UnconnectedState)
        m_socket.abort();
    if (m_enabled)
        m_send.start(3000);
}
void NiriAnimationTargets::publish()
{
    if (!m_enabled || !m_dirty || m_pending)
        return;
    if (m_socket.state() == QLocalSocket::UnconnectedState) {
        m_socket.connectToServer(qEnvironmentVariable("NIRI_SOCKET"));
        m_deadline.start();
        return;
    }
    if (m_socket.state() != QLocalSocket::ConnectedState)
        return;
    const QJsonObject request{
        {"SetWindowAnimationTargets", QJsonObject{{"targets", QJsonArray::fromVariantList(m_targets)}}}};
    m_dirty = false;
    m_pending = true;
    m_socket.write(QJsonDocument(request).toJson(QJsonDocument::Compact) + '\n');
    m_deadline.start();
}

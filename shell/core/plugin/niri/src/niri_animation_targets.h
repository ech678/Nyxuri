#pragma once
#include <QLocalSocket>
#include <QObject>
#include <QTimer>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>

// One publisher per Dock surface. Its socket owns its hints on the compositor.
class NiriAnimationTargets : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(bool enabled READ enabled WRITE setEnabled NOTIFY enabledChanged)
    Q_PROPERTY(QVariantList targets READ targets WRITE setTargets NOTIFY targetsChanged)
  public:
    explicit NiriAnimationTargets(QObject *parent = nullptr);
    ~NiriAnimationTargets() override;
    bool enabled() const { return m_enabled; }
    void setEnabled(bool enabled);
    QVariantList targets() const { return m_targets; }
    void setTargets(const QVariantList &targets);
  signals:
    void enabledChanged();
    void targetsChanged();

  private:
    void publish();
    void reconnect();
    QLocalSocket m_socket;
    QTimer m_send;
    QTimer m_deadline;
    QVariantList m_targets;
    bool m_enabled = false;
    bool m_dirty = true;
    bool m_pending = false;
};

#pragma once
#include "window_capture_probe.h"
#include "window_preview_cache.h"
#include <QHash>
#include <QSet>
#include <QTimer>

// Sessions follow consumers; small last-good frames follow live window identity.
class WindowPreviewManager : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(bool supported READ supported NOTIFY statusChanged)
    Q_PROPERTY(bool ready READ ready NOTIFY statusChanged)
    Q_PROPERTY(QString error READ error NOTIFY statusChanged)
    Q_PROPERTY(int captureCount READ captureCount NOTIFY capturesChanged)
  public:
    explicit WindowPreviewManager(QObject *parent = nullptr);
    ~WindowPreviewManager() override;
    bool supported() const;
    bool ready() const { return m_catalog.ready(); }
    QString error() const { return m_catalog.error(); }
    int captureCount() const { return m_captures.size(); }
    Q_INVOKABLE void open(const QString &displayName);
    Q_INVOKABLE void close();
    Q_INVOKABLE void setWindows(const QStringList &live, const QStringList &minimized);
    Q_INVOKABLE void setTargets(const QString &consumer, const QStringList &identifiers);
    Q_INVOKABLE void release(const QString &consumer);
    Q_INVOKABLE WindowCaptureProbe *captureFor(const QString &identifier) const;
    Q_INVOKABLE WindowPreviewFrame *frameFor(const QString &identifier);
    Q_INVOKABLE void prefetch(const QString &identifier);
    Q_INVOKABLE void requestSnapshot(const QString &identifier);
  signals:
    void statusChanged();
    void capturesChanged();
    void snapshotFinished(const QString &identifier);

  private:
    void reconcile();
    void clearCaptures();
    void removeCapture(const QString &id);
    void finishSnapshot(const QString &id);
    WindowCaptureProbe m_catalog;
    WindowPreviewCache m_cache;
    QTimer m_reconcile;
    QTimer m_snapshotTimeout;
    QString m_display;
    bool m_open = false;
    quint64 m_generation = 0;
    quint64 m_requestSerial = 0;
    QSet<QString> m_live;
    QSet<QString> m_minimized;
    QStringList m_prefetch;
    QString m_snapshot;
    QHash<QString, quint64> m_waiters;
    QHash<QString, QStringList> m_targets;
    QHash<QString, WindowCaptureProbe *> m_captures;
};

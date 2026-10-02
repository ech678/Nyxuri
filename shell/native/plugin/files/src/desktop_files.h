#pragma once
#include <QFileSystemWatcher>
#include <QObject>
#include <QQmlEngine>
#include <QUrl>
#include <QVariantMap>
class DesktopFiles : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(int trashCount READ trashCount NOTIFY trashChanged)
    Q_PROPERTY(bool trashAvailable READ trashAvailable NOTIFY trashChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
  public:
    explicit DesktopFiles(QObject *parent = nullptr);
    ~DesktopFiles() override;
    int trashCount() const { return m_trashCount; }
    bool trashAvailable() const { return m_trashAvailable; }
    bool busy() const { return m_busy; }
    Q_INVOKABLE QVariantMap info(const QUrl &url) const;
    Q_INVOKABLE QUrl thumbnail(const QUrl &url) const;
    Q_INVOKABLE void watchUrls(const QStringList &urls);
    Q_INVOKABLE bool moveToTrash(const QList<QUrl> &urls);
    Q_INVOKABLE bool emptyTrash();
    Q_INVOKABLE QString defaultApplicationForFile(const QUrl &url) const;
    Q_INVOKABLE bool canOpenWith(const QString &desktopId) const;
    Q_INVOKABLE bool openWith(const QString &desktopId, const QList<QUrl> &urls);
    Q_INVOKABLE void refreshTrash();
  signals:
    void trashChanged();
    void busyChanged();
    void filesChanged();
    void finished(const QString &action, int succeeded, const QStringList &errors);

  private:
    void watchFiles();
    bool startProcess(const QString &action, const QString &program, const QStringList &arguments);
    QFileSystemWatcher m_watcher;
    QStringList m_urls;
    void *m_monitor = nullptr;
    int m_trashCount = 0;
    bool m_trashAvailable = false;
    bool m_refreshing = false;
    bool m_refreshAgain = false;
    bool m_busy = false;
};

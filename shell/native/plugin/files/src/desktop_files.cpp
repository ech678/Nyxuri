#include <gio/gdesktopappinfo.h>
#include <gio/gio.h>
#include "desktop_files.h"
#include "file_metadata.h"
#include <QDir>
#include <QFileInfo>
#include <QFutureWatcher>
#include <QProcess>
#include <QtConcurrentRun>

namespace {
GDesktopAppInfo *desktopInfo(QString id)
{
    if (id.isEmpty() || id.contains('/') || id.contains('\\') || id.contains(QChar::Null))
        return nullptr;
    if (!id.endsWith(".desktop"))
        id += ".desktop";
    return g_desktop_app_info_new(id.toUtf8().constData());
}
} // namespace
DesktopFiles::DesktopFiles(QObject *parent) : QObject(parent)
{
    auto *trash = g_file_new_for_uri("trash:///");
    auto *monitor = g_file_monitor_directory(trash, G_FILE_MONITOR_NONE, nullptr, nullptr);
    g_object_unref(trash);
    m_monitor = monitor;
    if (monitor)
        g_signal_connect(monitor, "changed",
                         G_CALLBACK(+[](GFileMonitor *, GFile *, GFile *, GFileMonitorEvent, gpointer data) {
                             auto *self = static_cast<DesktopFiles *>(data);
                             QMetaObject::invokeMethod(self, &DesktopFiles::refreshTrash,
                                                       Qt::QueuedConnection);
                         }),
                         this);
    const auto changed = [this] {
        watchFiles();
        emit filesChanged();
    };
    connect(&m_watcher, &QFileSystemWatcher::fileChanged, this, changed);
    connect(&m_watcher, &QFileSystemWatcher::directoryChanged, this, changed);
    refreshTrash();
}
DesktopFiles::~DesktopFiles()
{
    if (m_monitor) {
        g_signal_handlers_disconnect_by_data(m_monitor, this);
        g_file_monitor_cancel(static_cast<GFileMonitor *>(m_monitor));
        g_object_unref(m_monitor);
    }
}
QVariantMap DesktopFiles::info(const QUrl &url) const { return FileMetadata::read(url); }
QUrl DesktopFiles::thumbnail(const QUrl &url) const { return FileMetadata::thumbnail(url); }
void DesktopFiles::watchUrls(const QStringList &urls)
{
    if (m_urls == urls)
        return;
    m_urls = urls;
    watchFiles();
}
void DesktopFiles::watchFiles()
{
    QStringList paths;
    for (const auto &value : m_urls) {
        const auto url = FileMetadata::localUrl(QUrl(value));
        if (url.isEmpty())
            continue;
        const QFileInfo file(url.toLocalFile());
        if (file.exists())
            paths.append(file.absoluteFilePath());
        auto parent = file.dir();
        while (!parent.exists() && parent.cdUp()) {
        }
        if (parent.exists())
            paths.append(parent.absolutePath());
    }
    paths.removeDuplicates();
    const auto current = m_watcher.files() + m_watcher.directories();
    for (const auto &path : current)
        if (!paths.contains(path))
            m_watcher.removePath(path);
    for (const auto &path : paths)
        if (!current.contains(path))
            m_watcher.addPath(path);
}
void DesktopFiles::refreshTrash()
{
    if (m_refreshing) {
        m_refreshAgain = true;
        return;
    }
    m_refreshing = true;
    auto *watcher = new QFutureWatcher<QPair<bool, int>>(this);
    connect(watcher, &QFutureWatcherBase::finished, this, [this, watcher] {
        const auto result = watcher->result();
        m_trashAvailable = result.first;
        m_trashCount = result.second;
        m_refreshing = false;
        watcher->deleteLater();
        emit trashChanged();
        if (m_refreshAgain) {
            m_refreshAgain = false;
            refreshTrash();
        }
    });
    watcher->setFuture(QtConcurrent::run([] {
        auto *file = g_file_new_for_uri("trash:///");
        auto *info = g_file_query_info(file, "trash::item-count", G_FILE_QUERY_INFO_NONE, nullptr, nullptr);
        const QPair<bool, int> result{
            info != nullptr, info ? int(g_file_info_get_attribute_uint32(info, "trash::item-count")) : 0};
        if (info)
            g_object_unref(info);
        g_object_unref(file);
        return result;
    }));
}
bool DesktopFiles::moveToTrash(const QList<QUrl> &urls)
{
    if (m_busy || urls.isEmpty())
        return false;
    for (const auto &url : urls)
        if (FileMetadata::localUrl(url).isEmpty())
            return false;
    m_busy = true;
    emit busyChanged();
    auto *watcher = new QFutureWatcher<QPair<int, QStringList>>(this);
    connect(watcher, &QFutureWatcherBase::finished, this, [this, watcher] {
        const auto result = watcher->result();
        watcher->deleteLater();
        m_busy = false;
        emit busyChanged();
        refreshTrash();
        emit filesChanged();
        emit finished("trash", result.first, result.second);
    });
    watcher->setFuture(QtConcurrent::run([urls] {
        QPair<int, QStringList> result;
        QSet<QString> seen;
        for (const auto &url : urls) {
            const auto uri = FileMetadata::localUrl(url).toString(QUrl::FullyEncoded);
            if (seen.contains(uri))
                continue;
            seen.insert(uri);
            auto *file = g_file_new_for_uri(uri.toUtf8().constData());
            GError *error = nullptr;
            // GIO handles mount trash, collisions and symlinks. Never fall back to delete.
            if (g_file_trash(file, nullptr, &error))
                ++result.first;
            else
                result.second.append(QFileInfo(url.toLocalFile()).fileName() + ": " +
                                     QString::fromUtf8(error ? error->message : "Trash operation failed"));
            if (error)
                g_error_free(error);
            g_object_unref(file);
        }
        return result;
    }));
    return true;
}
bool DesktopFiles::startProcess(const QString &action, const QString &program, const QStringList &arguments)
{
    if (m_busy)
        return false;
    m_busy = true;
    emit busyChanged();
    auto *process = new QProcess(this);
    const auto complete = [this, process, action](bool success, const QString &error) {
        if (process->property("completed").toBool())
            return;
        process->setProperty("completed", true);
        m_busy = false;
        emit busyChanged();
        if (action == "empty")
            refreshTrash();
        emit finished(action, success ? 1 : 0, success ? QStringList{} : QStringList{error});
        process->deleteLater();
    };
    connect(process, &QProcess::finished, this, [process, complete](int code, QProcess::ExitStatus status) {
        complete(code == 0 && status == QProcess::NormalExit,
                 QString::fromUtf8(process->readAllStandardError()).trimmed());
    });
    connect(process, &QProcess::errorOccurred, this, [process, complete](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart)
            complete(false, process->errorString());
    });
    process->start(program, arguments);
    return true;
}
bool DesktopFiles::emptyTrash()
{
    return m_trashAvailable && startProcess("empty", "gio", {"trash", "--empty"});
}
QString DesktopFiles::defaultApplicationForFile(const QUrl &url) const
{
    const auto local = FileMetadata::localUrl(url);
    if (local.isEmpty())
        return {};
    auto *file = g_file_new_for_path(local.toLocalFile().toUtf8().constData());
    auto *info = g_file_query_info(file, G_FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE, G_FILE_QUERY_INFO_NONE,
                                   nullptr, nullptr);
    g_object_unref(file);
    if (!info)
        return {};
    // A file:// scheme handler is a file manager, not necessarily the default
    // application for this file's content. Resolve the MIME association first.
    const auto *type = g_file_info_get_content_type(info);
    auto *app = type ? g_app_info_get_default_for_type(type, false) : nullptr;
    g_object_unref(info);
    if (!app)
        return {};
    QString path;
    if (G_IS_DESKTOP_APP_INFO(app))
        path = QString::fromUtf8(g_desktop_app_info_get_filename(G_DESKTOP_APP_INFO(app)));
    g_object_unref(app);
    return path;
}
bool DesktopFiles::canOpenWith(const QString &desktopId) const
{
    auto *app = desktopInfo(desktopId);
    if (!app)
        return false;
    const bool supported =
        g_app_info_supports_files(G_APP_INFO(app)) || g_app_info_supports_uris(G_APP_INFO(app));
    g_object_unref(app);
    return supported;
}
bool DesktopFiles::openWith(const QString &desktopId, const QList<QUrl> &urls)
{
    if (urls.isEmpty() || !canOpenWith(desktopId))
        return false;
    auto *app = desktopInfo(desktopId);
    if (!app)
        return false;
    const auto path = QString::fromUtf8(g_desktop_app_info_get_filename(app));
    g_object_unref(app);
    QStringList arguments{
        "--user", "--scope", "--collect", "--quiet", "--slice=app.slice", "--expand-environment=no",
        "--",     "gio",     "launch",    path};
    for (const auto &url : urls) {
        const auto local = FileMetadata::localUrl(url);
        if (local.isEmpty())
            return false;
        arguments.append(local.toString(QUrl::FullyEncoded));
    }
    return startProcess("open", "systemd-run", arguments);
}

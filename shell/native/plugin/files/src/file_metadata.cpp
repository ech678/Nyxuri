#include "file_metadata.h"
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFileInfo>
#include <QImageReader>
#include <QMimeDatabase>
#include <QStandardPaths>

QUrl FileMetadata::localUrl(const QUrl &url)
{
    if (!url.isLocalFile() || (!url.host().isEmpty() && url.host() != "localhost") || url.hasQuery() ||
        url.hasFragment() || !QDir::isAbsolutePath(url.toLocalFile()) ||
        url.toLocalFile().contains(QChar::Null))
        return {};
    // Never canonicalize: a symlink must remain a reference to the link itself.
    return QUrl::fromLocalFile(QDir::cleanPath(url.toLocalFile()));
}
QVariantMap FileMetadata::read(const QUrl &input)
{
    const auto url = localUrl(input);
    if (url.isEmpty())
        return {};
    const QFileInfo file(url.toLocalFile());
    const auto mime = QMimeDatabase().mimeTypeForFile(file, QMimeDatabase::MatchExtension);
    QString icon = mime.iconName();
    if (file.isDir()) {
        icon = "folder";
        const QList<QPair<QStandardPaths::StandardLocation, QString>> places{
            {QStandardPaths::DownloadLocation, "folder-download"},
            {QStandardPaths::DocumentsLocation, "folder-documents"},
            {QStandardPaths::PicturesLocation, "folder-pictures"},
            {QStandardPaths::MusicLocation, "folder-music"},
            {QStandardPaths::MoviesLocation, "folder-videos"},
            {QStandardPaths::HomeLocation, "user-home"}};
        for (const auto &place : places)
            if (file.absoluteFilePath() == QStandardPaths::writableLocation(place.first))
                icon = place.second;
    }
    return {{"url", url.toString(QUrl::FullyEncoded)},
            {"path", file.absoluteFilePath()},
            {"name", file.fileName().isEmpty() ? QStringLiteral("/") : file.fileName()},
            {"available", file.exists()},
            {"readable", file.isReadable()},
            {"isDirectory", file.isDir()},
            {"isLink", file.isSymLink()},
            {"kind", file.isDir() ? "folder" : "file"},
            {"mimeType", mime.name()},
            {"icon", icon},
            {"genericIcon", mime.genericIconName()},
            {"typeName", mime.comment()},
            {"modified", file.lastModified()},
            {"created", file.birthTime()},
            {"size", file.isDir() ? qint64(0) : file.size()}};
}
QUrl FileMetadata::thumbnail(const QUrl &input)
{
    const auto url = localUrl(input);
    const QFileInfo file(url.toLocalFile());
    if (url.isEmpty() || !file.isFile())
        return {};
    const auto mime = QMimeDatabase().mimeTypeForFile(file, QMimeDatabase::MatchExtension);
    if (mime.name().startsWith("image/"))
        return url;
    const auto uri = url.toString(QUrl::FullyEncoded);
    const auto hash =
        QString::fromLatin1(QCryptographicHash::hash(uri.toUtf8(), QCryptographicHash::Md5).toHex());
    const auto root = QStandardPaths::writableLocation(QStandardPaths::GenericCacheLocation) + "/thumbnails/";
    for (const auto &size : {"large", "x-large", "normal"}) {
        const auto path = root + size + '/' + hash + ".png";
        QImageReader reader(path);
        bool hasTime = false;
        const auto modified = reader.text("Thumb::MTime").toLongLong(&hasTime);
        if (reader.canRead() && reader.text("Thumb::URI") == uri && hasTime &&
            modified == file.lastModified().toSecsSinceEpoch())
            return QUrl::fromLocalFile(path);
    }
    return {};
}

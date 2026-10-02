#pragma once
#include <QUrl>
#include <QVariantMap>
namespace FileMetadata {
QUrl localUrl(const QUrl &url);
QVariantMap read(const QUrl &url);
QUrl thumbnail(const QUrl &url);
} // namespace FileMetadata

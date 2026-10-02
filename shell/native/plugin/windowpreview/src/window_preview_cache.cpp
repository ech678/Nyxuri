#include "window_preview_cache.h"
#include <algorithm>

WindowPreviewCache::WindowPreviewCache(QObject *parent, qint64 budget)
    : QObject(parent), m_budget(std::max<qint64>(0, budget))
{}

void WindowPreviewCache::reset(quint64 generation)
{
    m_generation = generation;
    retain({});
}

WindowPreviewFrame *WindowPreviewCache::frameFor(const QString &id)
{
    if (id.isEmpty())
        return nullptr;
    auto *&frame = m_frames[id];
    if (!frame)
        frame = new WindowPreviewFrame(this);
    frame->m_lastUse = ++m_serial;
    return frame;
}

bool WindowPreviewCache::hasFrame(const QString &id) const
{
    const auto *frame = m_frames.value(id);
    return frame && frame->hasFrame();
}

bool WindowPreviewCache::store(quint64 generation, const QString &id, const QImage &image, QSize sourceSize)
{
    if (generation != m_generation || id.isEmpty() || image.isNull())
        return false;
    QImage owned = image.width() > 512 || image.height() > 512
                       ? image.scaled(512, 512, Qt::KeepAspectRatio, Qt::SmoothTransformation)
                       : image.copy();
    owned = owned.convertToFormat(QImage::Format_ARGB32_Premultiplied);
    if (owned.isNull() || owned.sizeInBytes() > m_budget)
        return false;
    auto *frame = frameFor(id);
    m_bytes -= frame->m_image.sizeInBytes();
    frame->m_image = std::move(owned);
    frame->m_sourceSize = sourceSize;
    m_bytes += frame->m_image.sizeInBytes();
    while (m_bytes > m_budget) {
        WindowPreviewFrame *oldest = nullptr;
        for (auto *candidate : m_frames) {
            if (candidate->hasFrame() && candidate != frame &&
                (!oldest || candidate->m_lastUse < oldest->m_lastUse))
                oldest = candidate;
        }
        if (!oldest)
            break;
        discardImage(oldest);
    }
    emit frame->changed();
    return true;
}

void WindowPreviewCache::discardImage(WindowPreviewFrame *frame)
{
    m_bytes -= frame->m_image.sizeInBytes();
    frame->m_image = {};
    frame->m_sourceSize = {};
    emit frame->changed();
}

void WindowPreviewCache::invalidate(const QString &id)
{
    if (auto *frame = m_frames.value(id))
        discardImage(frame);
}

void WindowPreviewCache::retain(const QSet<QString> &ids)
{
    for (const auto &id : m_frames.keys()) {
        if (ids.contains(id))
            continue;
        auto *frame = m_frames.take(id);
        discardImage(frame);
        frame->deleteLater();
    }
}

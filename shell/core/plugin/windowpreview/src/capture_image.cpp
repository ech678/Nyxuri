#include "capture_image.h"
#include <QPainter>

CaptureImage::CaptureImage(QQuickItem *parent) : QQuickPaintedItem(parent) {}
void CaptureImage::setFrame(WindowPreviewFrame *frame)
{
    if (m_frame == frame)
        return;
    if (m_frame)
        disconnect(m_frame, nullptr, this, nullptr);
    setCapture(nullptr);
    m_frame = frame;
    m_image = frame ? frame->image() : QImage();
    if (frame) {
        connect(frame, &WindowPreviewFrame::changed, this, [this] {
            m_image = m_frame ? m_frame->image() : QImage();
            update();
        });
        connect(frame, &QObject::destroyed, this, [this] {
            m_image = {};
            update();
            emit frameChanged();
        });
    }
    update();
    emit frameChanged();
}
void CaptureImage::setCapture(WindowCaptureProbe *capture)
{
    if (m_capture == capture)
        return;
    if (m_capture)
        disconnect(m_capture, nullptr, this, nullptr);
    if (capture && m_frame) {
        disconnect(m_frame, nullptr, this, nullptr);
        m_frame = nullptr;
        emit frameChanged();
    }
    m_capture = capture;
    m_image = capture ? capture->image() : QImage();
    if (capture) {
        connect(capture, &WindowCaptureProbe::imageChanged, this, [this] {
            m_image = m_capture ? m_capture->image() : QImage();
            update();
        });
        connect(capture, &QObject::destroyed, this, [this] {
            m_image = {};
            update();
            emit captureChanged();
        });
    }
    update();
    emit captureChanged();
}
void CaptureImage::paint(QPainter *painter)
{
    if (m_image.isNull())
        return;
    const auto size = m_image.size().scaled(boundingRect().size().toSize(), Qt::KeepAspectRatio);
    const QRectF target((width() - size.width()) / 2, (height() - size.height()) / 2, size.width(),
                        size.height());
    painter->setRenderHint(QPainter::SmoothPixmapTransform);
    painter->drawImage(target, m_image);
}

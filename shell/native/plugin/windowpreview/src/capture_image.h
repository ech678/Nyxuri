#pragma once
#include "window_capture_probe.h"
#include "window_preview_cache.h"
#include <QPointer>
#include <QQuickPaintedItem>

class CaptureImage : public QQuickPaintedItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(WindowCaptureProbe *capture READ capture WRITE setCapture NOTIFY captureChanged)
    Q_PROPERTY(WindowPreviewFrame *frame READ frame WRITE setFrame NOTIFY frameChanged)
  public:
    explicit CaptureImage(QQuickItem *parent = nullptr);
    WindowCaptureProbe *capture() const { return m_capture; }
    void setCapture(WindowCaptureProbe *capture);
    WindowPreviewFrame *frame() const { return m_frame; }
    void setFrame(WindowPreviewFrame *frame);
    void paint(QPainter *painter) override;
  signals:
    void captureChanged();
    void frameChanged();

  private:
    QPointer<WindowCaptureProbe> m_capture;
    QPointer<WindowPreviewFrame> m_frame;
    QImage m_image;
};

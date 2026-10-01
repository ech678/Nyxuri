#pragma once
#include <QImage>
#include <QObject>
#include <QVariantList>
#include <QtQml/qqmlregistration.h>
#include <memory>

class WindowCaptureProbe : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QVariantList windows READ windows NOTIFY windowsChanged)
    Q_PROPERTY(bool ready READ ready NOTIFY changed)
    Q_PROPERTY(bool supported READ supported NOTIFY changed)
    Q_PROPERTY(bool active READ active NOTIFY changed)
    Q_PROPERTY(QString error READ error NOTIFY changed)
    Q_PROPERTY(QString identifier READ identifier NOTIFY changed)
    Q_PROPERTY(int frameCount READ frameCount NOTIFY changed)
    Q_PROPERTY(qint64 firstFrameMs READ firstFrameMs NOTIFY changed)
    Q_PROPERTY(int maximumDimension READ maximumDimension WRITE setMaximumDimension NOTIFY limitsChanged)
    Q_PROPERTY(int frameInterval READ frameInterval WRITE setFrameInterval NOTIFY limitsChanged)
    Q_PROPERTY(QSize sourceSize READ sourceSize NOTIFY changed)
  public:
    explicit WindowCaptureProbe(QObject *parent = nullptr);
    ~WindowCaptureProbe() override;
    QVariantList windows() const;
    bool ready() const;
    bool supported() const;
    bool active() const;
    QString error() const;
    QString identifier() const;
    int frameCount() const;
    qint64 firstFrameMs() const;
    QSize sourceSize() const;
    QImage image() const;
    int maximumDimension() const;
    void setMaximumDimension(int value);
    int frameInterval() const;
    void setFrameInterval(int value);
    Q_INVOKABLE void open(const QString &displayName);
    Q_INVOKABLE void start(const QString &identifier);
    Q_INVOKABLE void stop();
    Q_INVOKABLE void close();
  signals:
    void limitsChanged();
    void changed();
    void windowsChanged();
    void imageChanged();

  private:
    struct Private;
    std::unique_ptr<Private> d;
};

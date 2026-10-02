#pragma once

#include <QHash>
#include <QImage>
#include <QObject>
#include <QSet>
#include <QtQml/qqmlregistration.h>

// A small owned image, never a protocol session or a view of shared memory.
class WindowPreviewFrame : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Frames are owned by WindowPreviewManager")
    Q_PROPERTY(bool hasFrame READ hasFrame NOTIFY changed)
    Q_PROPERTY(QSize sourceSize READ sourceSize NOTIFY changed)
  public:
    explicit WindowPreviewFrame(QObject *parent = nullptr) : QObject(parent) {}
    bool hasFrame() const { return !m_image.isNull(); }
    QSize sourceSize() const { return m_sourceSize; }
    const QImage &image() const { return m_image; }
  signals:
    void changed();

  private:
    friend class WindowPreviewCache;
    QImage m_image;
    QSize m_sourceSize;
    quint64 m_lastUse = 0;
};

class WindowPreviewCache : public QObject {
    Q_OBJECT
  public:
    explicit WindowPreviewCache(QObject *parent = nullptr, qint64 budget = 32 * 1024 * 1024);
    void reset(quint64 generation);
    WindowPreviewFrame *frameFor(const QString &id);
    bool hasFrame(const QString &id) const;
    bool store(quint64 generation, const QString &id, const QImage &image, QSize sourceSize);
    void invalidate(const QString &id);
    void retain(const QSet<QString> &ids);
    qint64 bytesUsed() const { return m_bytes; }
    quint64 generation() const { return m_generation; }

  private:
    void discardImage(WindowPreviewFrame *frame);
    QHash<QString, WindowPreviewFrame *> m_frames;
    quint64 m_generation = 0;
    quint64 m_serial = 0;
    qint64 m_budget;
    qint64 m_bytes = 0;
};

#pragma once
#include <QPointer>
#include <QQuickItem>
#include <QtQml/qqmlregistration.h>

// Route wheel input from a transformed visual region to a horizontal Flickable.
// Qt retains ownership of scroll phases, acceleration and boundary handling.
class HorizontalWheelArea : public QQuickItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QQuickItem *target READ target WRITE setTarget NOTIFY targetChanged)
    Q_PROPERTY(bool reverseVertical MEMBER m_reverseVertical NOTIFY reverseVerticalChanged)
  public:
    explicit HorizontalWheelArea(QQuickItem *parent = nullptr);
    QQuickItem *target() const { return m_target; }
    void setTarget(QQuickItem *target);
  signals:
    void targetChanged();
    void reverseVerticalChanged();

  protected:
    void wheelEvent(QWheelEvent *event) override;

  private:
    QPointer<QQuickItem> m_target;
    bool m_reverseVertical = false;
};

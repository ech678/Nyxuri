#include "horizontal_wheel_area.h"
#include <QCoreApplication>
#include <QWheelEvent>

HorizontalWheelArea::HorizontalWheelArea(QQuickItem *parent) : QQuickItem(parent)
{
    setAcceptedMouseButtons(Qt::NoButton);
}
void HorizontalWheelArea::setTarget(QQuickItem *target)
{
    if (m_target == target)
        return;
    m_target = target;
    emit targetChanged();
}
void HorizontalWheelArea::wheelEvent(QWheelEvent *event)
{
    if (!m_target || m_target == this) {
        event->ignore();
        return;
    }
    auto pixels = event->pixelDelta();
    auto angles = event->angleDelta();
    if (pixels.x() == 0 && angles.x() == 0) {
        const int direction = m_reverseVertical ? -1 : 1;
        pixels = QPoint(pixels.y() * direction, 0);
        angles = QPoint(angles.y() * direction, 0);
    }
    QWheelEvent mapped(m_target->mapFromItem(this, event->position()), event->globalPosition(), pixels,
                       angles, event->buttons(), event->modifiers(), event->phase(), event->inverted(),
                       event->source(), event->pointingDevice());
    mapped.setTimestamp(event->timestamp());
    QCoreApplication::sendEvent(m_target, &mapped);
    // At a list boundary the wheel still belongs to the fan, not the window below.
    event->accept();
}

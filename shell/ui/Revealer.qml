// Fork & Trim: end4-pC modules/common/widgets/Revealer.qml (GPL-3, see
// shell/LICENSE appendix end-4-dots-hyprland-GPL-3.0.txt). Recreation of the
// GTK revealer; takes exactly one child. Trimmed only for the tree's animation
// pool (the upstream elementMoveEnter curve maps onto the tree's
// expressiveFastEffects token).
import QtQuick
import qs.commons

Item {
    id: root
    property bool reveal
    property bool vertical: false
    clip: true

    readonly property Item child: children.length > 0 ? children[0] : null
    readonly property real childWidth: child ? child.implicitWidth : 0
    readonly property real childHeight: child ? child.implicitHeight : 0

    implicitWidth: (reveal || vertical) ? childWidth : 0
    implicitHeight: (reveal || !vertical) ? childHeight : 0

    visible: reveal || (implicitWidth > 0 && !vertical) || (implicitHeight > 0 && vertical)

    Behavior on implicitWidth {
        enabled: !vertical
        NumberAnimation {
            duration: Appearance.animation.expressiveFastEffects.duration
            easing.type: Appearance.animation.expressiveFastEffects.type
            easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
        }
    }
    Behavior on implicitHeight {
        enabled: vertical
        NumberAnimation {
            duration: Appearance.animation.expressiveFastEffects.duration
            easing.type: Appearance.animation.expressiveFastEffects.type
            easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
        }
    }
}

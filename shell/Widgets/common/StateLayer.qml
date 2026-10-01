import QtQuick
import qs.Common

Item {
    id: root

    property bool hovered: false
    property bool focused: false
    property bool pressed: false
    property bool selected: false
    property bool selectedEnabled: false
    property color color: Appearance.colors.colOnSurface
    property color hoverColor: root.color
    property color focusColor: root.color
    property color pressedColor: root.color
    property color selectedColor: root.color
    property real hoverOpacity: Appearance.interaction.hoverStateLayerOpacity
    property real focusOpacity: Appearance.interaction.focusStateLayerOpacity
    property real pressedOpacity: Appearance.interaction.pressedStateLayerOpacity
    property real selectedOpacity: Appearance.interaction.selectedStateLayerOpacity
    property real layerRadius: 0
    readonly property bool active: root.enabled && (root.pressed || root.hovered || root.focused || (root.selectedEnabled && root.selected))
    readonly property color activeColor: root.pressed ? root.pressedColor : root.hovered ? root.hoverColor : root.focused ? root.focusColor : root.selectedEnabled && root.selected ? root.selectedColor : root.color
    readonly property real activeOpacity: root.pressed ? root.pressedOpacity : root.hovered ? root.hoverOpacity : root.focused ? root.focusOpacity : root.selectedOpacity

    Rectangle {
        anchors.fill: parent
        radius: root.layerRadius
        color: root.activeColor
        opacity: root.active ? root.activeOpacity : 0

        Behavior on opacity {
            NumberAnimation {
                duration: Appearance.interaction.stateLayerTransitionDuration
                easing.type: Appearance.animation.expressiveFastEffects.type
                easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
            }

        }

    }

}

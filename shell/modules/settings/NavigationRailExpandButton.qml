import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components

Rectangle {
    id: root

    signal clicked()

    property bool expanded: true

    Layout.alignment: Qt.AlignLeft
    Layout.leftMargin: 8
    implicitWidth: 40
    implicitHeight: 40
    radius: Appearance.rounding.full
    color: mouse.pressed ? Appearance.colors.colLayer1Active : mouse.containsMouse ? Appearance.colors.colLayer1Hover : "transparent"
    rotation: root.expanded ? 0 : -180

    Behavior on rotation {
        NumberAnimation {
            duration: Appearance.animation.elementMoveFast.duration
            easing.type: Appearance.animation.elementMoveFast.type
            easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
        }
    }

    Behavior on color {
        ColorAnimation {
            duration: Appearance.animation.expressiveEffects.duration
            easing.type: Appearance.animation.expressiveEffects.type
            easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
        }
    }

    MaterialSymbol {
        anchors.centerIn: parent
        text: root.expanded ? "menu_open" : "menu"
        iconSize: 24
        color: Appearance.colors.colOnLayer1
    }

    MouseArea {
        id: mouse

        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}

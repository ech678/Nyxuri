import QtQuick
import qs.Common

Item {
    id: root

    property int second: 0
    property bool constantlyRotate: false
    property string style: "hide"
    property color color: Appearance.colors.colPrimary
    readonly property real handWidth: 2
    readonly property real handLength: 95
    readonly property real dotSize: 20

    anchors.fill: parent
    rotation: 90 + 6 * root.second

    Rectangle {
        width: root.style === "dot" ? root.dotSize : root.handLength
        height: root.style === "dot" ? root.dotSize : root.handWidth
        radius: Math.min(width, height) / 2
        color: root.color

        anchors {
            left: parent.left
            leftMargin: 10 + (root.style === "dot" ? root.dotSize : 0)
            verticalCenter: parent.verticalCenter
        }

    }

    Rectangle {
        visible: root.style === "classic"
        width: 14
        height: width
        radius: Appearance.rounding.small
        color: root.color

        anchors {
            left: parent.left
            leftMargin: 40
            verticalCenter: parent.verticalCenter
        }

    }

    Behavior on rotation {
        enabled: root.constantlyRotate

        RotationAnimation {
            direction: RotationAnimation.Clockwise
            duration: 1000
            easing.type: Easing.InOutQuad
        }

    }

}

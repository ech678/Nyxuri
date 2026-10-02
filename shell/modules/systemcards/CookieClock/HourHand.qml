import QtQuick
import qs.Common

Item {
    id: root

    property int hour: 0
    property int minute: 0
    property string style: "fill"
    property color color: Appearance.colors.colPrimary
    readonly property real handLength: 72
    readonly property real handWidth: 20
    readonly property real fillAlpha: root.style === "hollow" ? 0 : 1

    anchors.fill: parent
    rotation: -90 + 30 * (root.hour + root.minute / 60)

    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        x: (parent.width - root.handWidth) / 2 - 15 * (root.style === "classic")
        width: root.handLength
        height: root.style === "classic" ? 8 : root.handWidth
        radius: root.style === "classic" ? 2 : root.handWidth / 2
        color: Qt.rgba(root.color.r, root.color.g, root.color.b, root.fillAlpha)
        border.color: root.color
        border.width: 4

        Behavior on x {
            NumberAnimation {
                duration: Appearance.animation.standardSmall.duration
                easing.type: Appearance.animation.standardSmall.type
                easing.bezierCurve: Appearance.animation.standardSmall.bezierCurve
            }

        }

    }

    Behavior on rotation {
        RotationAnimation {
            direction: RotationAnimation.Clockwise
            duration: Appearance.animation.standard.duration
            easing.type: Appearance.animation.standard.type
            easing.bezierCurve: Appearance.animation.standard.bezierCurve
        }

    }

}

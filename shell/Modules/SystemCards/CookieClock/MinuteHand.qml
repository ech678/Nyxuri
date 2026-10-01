import QtQuick
import qs.Common

Item {
    id: root

    property int minute: 0
    property string style: "medium"
    property color color: Appearance.colors.colTertiary
    readonly property real handLength: 95
    readonly property real handWidth: root.style === "bold" ? 20 : root.style === "medium" ? 12 : 5

    anchors.fill: parent
    rotation: -90 + 6 * root.minute

    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        x: parent.width / 2 - root.handWidth / 2 - 15 * (root.style === "classic")
        width: root.handLength
        height: root.handWidth
        radius: root.style === "classic" ? 2 : root.handWidth / 2
        color: root.color

        Behavior on height {
            NumberAnimation {
                duration: Appearance.animation.standardSmall.duration
                easing.type: Appearance.animation.standardSmall.type
                easing.bezierCurve: Appearance.animation.standardSmall.bezierCurve
            }

        }

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

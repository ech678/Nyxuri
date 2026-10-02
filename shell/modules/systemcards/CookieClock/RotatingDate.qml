import QtQuick
import qs.Common

Item {
    id: root

    property bool active: true
    property int second: 0
    property string dateText: ""
    property color color: "transparent"
    readonly property real angleStep: 12 * Math.PI / 180
    readonly property real radius: 90

    anchors.fill: parent
    rotation: root.active ? 6 * root.second + 180 - root.angleStep * 180 / Math.PI * root.dateText.length / 2 : 0

    Repeater {
        model: root.dateText.length

        delegate: Text {
            required property int index
            readonly property real angle: index * root.angleStep - Math.PI / 2

            x: parent.width / 2 + root.radius * Math.cos(angle) - width / 2
            y: parent.height / 2 + root.radius * Math.sin(angle) - height / 2
            rotation: angle * 180 / Math.PI + 90
            text: root.dateText.charAt(index)
            color: root.color
            font.family: Fonts.expressive
            font.pixelSize: 30
        }

    }

}

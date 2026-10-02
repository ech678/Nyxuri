import QtQuick
import qs.Common

Rectangle {
    id: root

    property int day: 1
    property color fillColor: "transparent"
    property color textColor: "transparent"

    width: 45
    height: 30
    radius: Appearance.rounding.small
    color: root.fillColor

    Text {
        anchors.centerIn: parent
        text: String(root.day).padStart(2, "0")
        color: root.textColor
        font.family: Fonts.expressive
        font.pixelSize: 20
        font.weight: Font.Black
    }

}

import QtQuick
import qs.Common

Item {
    id: root

    property real numberSize: 80
    property real margins: 10
    property color color: "transparent"

    Repeater {
        model: 4

        delegate: Item {
            id: numberItem

            required property int index

            anchors.fill: parent
            rotation: 90 * (index + 1)

            Item {
                width: root.numberSize
                height: width

                anchors {
                    top: parent.top
                    topMargin: root.margins
                    horizontalCenter: parent.horizontalCenter
                }

                Text {
                    anchors.centerIn: parent
                    text: 3 * (numberItem.index + 1)
                    rotation: -numberItem.rotation
                    color: root.color
                    font.family: Fonts.expressive
                    font.pixelSize: 80
                    font.weight: Font.Black
                }

            }

        }

    }

}

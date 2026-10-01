import QtQuick

Item {
    id: root

    property real margins: 12
    property color color: "transparent"
    property real hourLineSize: 4
    property real minuteLineSize: 2
    property real hourLineLength: 18
    property real minuteLineLength: 7

    Repeater {
        model: 12

        delegate: Item {
            required property int index

            anchors.fill: parent
            rotation: 30 * index

            Rectangle {
                width: root.hourLineLength
                height: root.hourLineSize
                radius: width / 2
                color: root.color

                anchors {
                    left: parent.left
                    leftMargin: root.margins
                    verticalCenter: parent.verticalCenter
                }

            }

        }

    }

    Repeater {
        model: 60

        delegate: Item {
            required property int index

            anchors.fill: parent
            rotation: 6 * index

            Rectangle {
                width: root.minuteLineLength
                height: root.minuteLineSize
                radius: width / 2
                color: root.color

                anchors {
                    left: parent.left
                    leftMargin: root.margins
                    verticalCenter: parent.verticalCenter
                }

            }

        }

    }

}

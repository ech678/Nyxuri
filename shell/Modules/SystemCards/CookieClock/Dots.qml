import QtQuick

Item {
    id: root

    property real markSize: 12
    property real margins: 12
    property color color: "transparent"

    Repeater {
        model: 12

        delegate: Item {
            required property int index

            anchors.fill: parent
            rotation: 30 * index

            Rectangle {
                width: root.markSize
                height: width
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

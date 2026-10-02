import QtQuick

Item {
    id: root

    property real markLength: 12
    property real markWidth: 4
    property color color: "transparent"
    property color markColor: "transparent"
    property real padding: 8

    width: 135
    height: width

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: root.color

        Repeater {
            model: 12

            delegate: Item {
                required property int index

                anchors.fill: parent
                rotation: 30 * index

                Rectangle {
                    width: root.markLength
                    height: root.markWidth
                    radius: width / 2
                    color: root.markColor

                    anchors {
                        left: parent.left
                        leftMargin: root.padding
                        verticalCenter: parent.verticalCenter
                    }

                }

            }

        }

    }

}

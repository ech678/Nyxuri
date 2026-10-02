import QtQuick

Item {
    id: root

    property string style: "none"
    property color color: "transparent"

    Loader {
        active: root.style === "dots"
        visible: status === Loader.Ready

        anchors {
            fill: parent
            margins: 10
        }

        sourceComponent: Dots {
            color: root.color
            margins: 12
        }

    }

    Loader {
        active: root.style === "full"
        visible: status === Loader.Ready

        anchors {
            fill: parent
            margins: 10
        }

        sourceComponent: Lines {
            color: root.color
            margins: 12
        }

    }

    Loader {
        active: root.style === "numbers"
        visible: status === Loader.Ready
        anchors.fill: parent

        sourceComponent: BigHourNumbers {
            color: root.color
            margins: 10
        }

    }

}

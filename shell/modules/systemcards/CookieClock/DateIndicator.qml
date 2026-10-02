import QtQuick
import qs.Common

Item {
    id: root

    property string style: "hide"
    property date currentTime: new Date()
    property int second: 0
    property bool active: true
    property color infoColor: "transparent"
    readonly property int day: root.currentTime.getDate()
    readonly property int month: root.currentTime.getMonth() + 1
    readonly property string borderText: Qt.formatDateTime(root.currentTime, "ddd dd")

    anchors.fill: parent

    Loader {
        active: root.style === "bubble"
        visible: status === Loader.Ready

        anchors {
            left: parent.left
            top: parent.top
        }

        sourceComponent: BubbleDate {
            day: root.day
            targetSize: 64
        }

    }

    Loader {
        active: root.style === "bubble"
        visible: status === Loader.Ready

        anchors {
            right: parent.right
            bottom: parent.bottom
        }

        sourceComponent: BubbleDate {
            month: true
            monthNumber: root.month
            targetSize: 64
        }

    }

    Loader {
        active: root.style === "rect"
        visible: status === Loader.Ready

        anchors {
            right: parent.right
            rightMargin: 10
            verticalCenter: parent.verticalCenter
        }

        sourceComponent: RectangleDate {
            day: root.day
            fillColor: Appearance.mix(root.infoColor, Appearance.colors.colSecondaryContainerHover, 0.5)
            textColor: Appearance.colors.colSecondaryHover
        }

    }

    Loader {
        active: root.style === "border"
        visible: status === Loader.Ready
        anchors.fill: parent

        sourceComponent: RotatingDate {
            active: root.active
            second: root.second
            dateText: root.borderText
            color: root.infoColor
        }

    }

}

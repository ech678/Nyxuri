import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string label: ""
    property string icon: ""
    property string suffix: ""
    property bool active: false
    property bool dim: false
    property bool interactive: true
    property color tone: Theme.text
    property int padH: 11

    signal tapped()
    signal scrolled(int delta)
    signal secondaryTapped()

    implicitWidth: row.implicitWidth + root.padH * 2
    implicitHeight: 26
    radius: height / 2
    color: root.active ? Theme.chipActive()
        : (hover.hovered && root.interactive ? Theme.rgba("surfaceContainerHighest", 0.95) : Theme.chip())
    border.width: 0
    opacity: root.dim ? 0.55 : 1.0

    Behavior on color {
        ColorAnimation { duration: 130 }
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Text {
            visible: root.icon.length > 0
            text: root.icon
            color: root.active ? Theme.onAccentSoft : root.tone
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fs
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: root.label.length > 0
            text: root.label
            color: root.active ? Theme.onAccentSoft : root.tone
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fs
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            visible: root.suffix.length > 0
            text: root.suffix
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    HoverHandler {
        id: hover
        enabled: root.interactive
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        enabled: root.interactive
        acceptedButtons: Qt.LeftButton
        onTapped: root.tapped()
    }

    TapHandler {
        enabled: root.interactive
        acceptedButtons: Qt.RightButton
        onTapped: root.secondaryTapped()
    }

    WheelHandler {
        enabled: root.interactive
        onWheel: function (event) {
            root.scrolled(event.angleDelta.y > 0 ? 1 : -1)
        }
    }
}
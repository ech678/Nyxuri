import QtQuick
import Quickshell
import Quickshell.Wayland
import qs
import qs.core

PanelWindow {
    id: root

    property var host: null
    property var targetScreen: null
    property bool open: false
    property string icon: ""
    property string label: ""
    property real value: 0

    anchors {
        bottom: true
        left: true
        right: true
    }
    margins.bottom: 90
    exclusiveZone: 0
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    screen: root.targetScreen
    visible: root.open
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    WlrLayershell.layer: WlrLayer.Overlay

    implicitHeight: 56
    implicitWidth: 320

    Rectangle {
        id: card
        width: 320
        height: 56
        anchors.horizontalCenter: parent.horizontalCenter
        radius: 28
        color: Theme.panel()
        border.width: 1
        border.color: Theme.rgba("outlineVariant", 0.6)
        opacity: root.open ? 1 : 0
        scale: root.open ? 1 : 0.9

        Behavior on opacity {
            NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
        }
        Behavior on scale {
            NumberAnimation { duration: 180; easing.type: Easing.OutBack; easing.overshoot: 1.06 }
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 12

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.icon
                color: Theme.accent
                font.pixelSize: 18
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 100
                spacing: 5

                Row {
                    spacing: 8

                    Text {
                        text: root.label
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fs
                        font.weight: Font.Medium
                    }

                    Text {
                        text: Math.round(root.value * 100) + "%"
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 6
                    radius: 3
                    color: Theme.rgba("surfaceContainerHighest", 0.9)

                    Rectangle {
                        width: Math.max(0, Math.min(1, root.value)) * parent.width
                        height: parent.height
                        radius: 3
                        color: Theme.accent

                        Behavior on width {
                            NumberAnimation { duration: 90; easing.type: Easing.OutCubic }
                        }
                    }
                }
            }
        }
    }

    Timer {
        id: hideTimer
        interval: 1400
        onTriggered: root.open = false
    }

    function flash(iconGlyph, text, v) {
        root.icon = iconGlyph
        root.label = text
        root.value = v
        root.open = true
        hideTimer.restart()
    }
}
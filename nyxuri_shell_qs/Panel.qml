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
    property int panelWidth: 560
    property int panelHeight: 420
    property int topOffset: Theme.barHeight + 16
    property string title: ""
    property bool focusable: true

    anchors {
        top: true
        left: true
        right: true
        bottom: true
    }
    exclusiveZone: 0
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    screen: root.targetScreen
    visible: root.open
    WlrLayershell.keyboardFocus: root.open && root.focusable
        ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    WlrLayershell.layer: WlrLayer.Overlay

    Rectangle {
        id: scrim
        anchors.fill: parent
        color: Theme.rgba("scrim", root.open ? 0.35 : 0.0)
        opacity: root.open ? 1 : 0
        Behavior on opacity {
            NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
        }
        TapHandler {
            onTapped: root.host && root.host.closeAll()
        }
    }

    Rectangle {
        id: card
        width: Math.min(root.panelWidth, parent.width - 40)
        height: Math.min(root.panelHeight, parent.height - root.topOffset - 40)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: root.topOffset
        radius: Theme.radius
        color: Theme.panel()
        border.width: 1
        border.color: Theme.rgba("outlineVariant", 0.6)
        clip: true

        opacity: root.open ? 1 : 0
        scale: root.open ? 1.0 : 0.96

        Behavior on opacity {
            NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
        }
        Behavior on scale {
            NumberAnimation { duration: 200; easing.type: Easing.OutBack; easing.overshoot: 1.05 }
        }

        Column {
            anchors.fill: parent
            spacing: 0

            Item {
                width: parent.width
                height: 44

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.pad
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.title
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsBig
                    font.weight: Font.DemiBold
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Theme.rgba("outlineVariant", 0.5)
            }

            Item {
                id: holder
                width: parent.width
                height: parent.height - 45
            }
        }

        TapHandler {
            onTapped: {}
        }
    }
}
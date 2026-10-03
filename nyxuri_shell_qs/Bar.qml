import QtQuick
import Quickshell
import Quickshell.Wayland
import qs
import qs.core
import "core/Orbit.js" as Orbit

PanelWindow {
    id: root

    property var host: null
    property var targetScreen: null

    anchors {
        top: true
        left: true
        right: true
    }
    margins.top: 6
    margins.left: 8
    margins.right: 8
    exclusiveZone: Theme.barHeight + 8
    exclusionMode: ExclusionMode.Normal
    color: "transparent"
    screen: root.targetScreen

    implicitHeight: Theme.barHeight

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: height / 2
        color: Theme.panel()
        border.width: 1
        border.color: Theme.rgba("outlineVariant", 0.5)

        Row {
            id: leftRow
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Capsule {
                icon: "\u25CF"
                label: ""
                active: root.host && root.host.launcherOpen
                interactive: true
                onTapped: root.host && root.host.togglePanel("launcher")
            }

            Capsule {
                icon: "\u25CE"
                active: root.host && root.host.orbitOpen
                onTapped: root.host && root.host.toggleOrbit()
                onSecondaryTapped: root.host && root.host.toggleOrbit()
            }

            Repeater {
                model: Workspaces.items

                delegate: Capsule {
                    required property var modelData
                    required property int index

                    label: modelData.name
                    active: modelData.focused
                    dim: !modelData.occupied && !modelData.focused
                    tone: modelData.urgent ? Theme.err : Theme.text
                    padH: 9
                    onTapped: Workspaces.focus(index)
                }
            }
        }

        Row {
            id: centerRow
            anchors.centerIn: parent
            spacing: 6

            Capsule {
                label: Workspaces.focusedTitle.length > 0
                    ? Orbit.truncate(Workspaces.focusedTitle, 46)
                    : "Nyxuri"
                tone: Theme.textMuted
                interactive: Workspaces.focusedTitle.length > 0
                onTapped: root.host && root.host.togglePanel("session")
            }
        }

        Row {
            id: rightRow
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Capsule {
                icon: "\u2630"
                label: root.host ? String(root.host.trayCount) : "0"
                active: root.host && root.host.trayOpen
                onTapped: root.host && root.host.togglePanel("tray")
            }

            Capsule {
                icon: "\u2709"
                label: root.host ? String(root.host.notifCount) : "0"
                active: root.host && root.host.notifOpen
                tone: root.host && root.host.notifCount > 0 ? Theme.accent : Theme.text
                onTapped: root.host && root.host.togglePanel("notifications")
            }

            Capsule {
                icon: Sys.volIcon()
                label: Sys.volumeText
                onTapped: Sys.toggleMute()
                onScrolled: function (d) { Sys.bumpVolume(d * 0.05) }
            }

            Capsule {
                visible: Sys.hasBattery
                icon: Sys.batIcon()
                label: Sys.batteryText
                tone: Sys.battery < 0.15 && !Sys.charging ? Theme.err : Theme.text
                onTapped: root.host && root.host.togglePanel("session")
            }

            Capsule {
                icon: "\u25A6"
                label: Sys.cpuText + " \u00B7 " + Sys.ramText
                onTapped: root.host && root.host.togglePanel("sysmon")
            }

            Capsule {
                icon: "\u25F4"
                label: root.host ? root.host.clockText : ""
                onTapped: root.host && root.host.togglePanel("calendar")
            }

            Capsule {
                icon: "\u23FB"
                onTapped: root.host && root.host.togglePanel("session")
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton
        propagateComposedEvents: true
    }
}
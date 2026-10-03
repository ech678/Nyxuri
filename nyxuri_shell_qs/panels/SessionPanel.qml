import QtQuick
import qs
import qs.core

Item {
    id: root

    property var host: null
    property int selected: 0

    readonly property var actions: [
        { id: "lock", label: "Lock", icon: "\U0001F512", cmd: ["sh", "-c", "loginctl lock-session 2>/dev/null || swaylock -f 2>/dev/null || hyprlock 2>/dev/null || true"] },
        { id: "suspend", label: "Suspend", icon: "\u23FE", cmd: ["systemctl", "suspend"] },
        { id: "logout", label: "Log Out", icon: "\u23FB", cmd: ["sh", "-c", "loginctl terminate-session \"$XDG_SESSION_ID\" 2>/dev/null || niri msg action quit --skip-confirmation 2>/dev/null || swaymsg exit 2>/dev/null || true"] },
        { id: "reboot", label: "Reboot", icon: "\u21BB", cmd: ["systemctl", "reboot"] },
        { id: "shutdown", label: "Shut Down", icon: "\u23FB", cmd: ["systemctl", "poweroff"] }
    ]

    function run(i) {
        if (i < 0 || i >= root.actions.length) return
        var a = root.actions[i]
        if (a.id === "lock" || a.id === "logout") {
            Quickshell.execDetached(a.cmd)
        } else {
            Quickshell.execDetached(a.cmd)
        }
        if (root.host) root.host.closeAll()
    }

    function move(d) {
        var n = root.actions.length
        root.selected = ((root.selected + d) % n + n) % n
    }

    Column {
        anchors.fill: parent
        spacing: 0

        Item {
            width: parent.width
            height: 56

            Row {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Rectangle {
                    width: 36
                    height: 36
                    radius: 18
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.rgba("primaryContainer", 0.9)

                    Text {
                        anchors.centerIn: parent
                        text: "\u25CF"
                        color: Theme.onAccentSoft
                        font.pixelSize: 14
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                        text: Quickshell.env("USER") || "user"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fs
                        font.weight: Font.DemiBold
                    }

                    Text {
                        text: Workspaces.backend.length > 0 && Workspaces.backend !== "none"
                            ? Workspaces.backend + " \u00B7 " + (Sys.batteryActive ? "battery" : "ac")
                            : "no compositor"
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.rgba("outlineVariant", 0.5)
        }

        Repeater {
            model: root.actions

            delegate: Rectangle {
                required property var modelData
                required property int index

                width: root.width
                height: 46
                color: index === root.selected
                    ? Theme.rgba("primaryContainer", 0.55) : "transparent"

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    spacing: 12

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.icon
                        color: modelData.id === "shutdown" || modelData.id === "reboot"
                            ? Theme.err : Theme.text
                        font.pixelSize: 15
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        color: modelData.id === "shutdown" || modelData.id === "reboot"
                            ? Theme.err : Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fs
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.selected = index
                    onClicked: root.run(index)
                }
            }
        }

        Item {
            width: parent.width
            height: 8
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

            Capsule {
                icon: "\u25D0"
                label: Color.dark ? "Dark" : "Light"
                onTapped: Color.dark = !Color.dark
            }

            Capsule {
                icon: "\u2699"
                label: "Settings"
                onTapped: root.host && root.host.togglePanel("settings")
            }
        }
    }

    Keys.onPressed: function (event) {
        if (event.key === Qt.Key_Down) { root.move(1); event.accepted = true }
        else if (event.key === Qt.Key_Up) { root.move(-1); event.accepted = true }
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            root.run(root.selected)
            event.accepted = true
        }
    }
    focus: true
}
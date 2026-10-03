import QtQuick
import qs
import qs.core

Item {
    id: root

    property var host: null

    readonly property var roles: [
        "primary", "onPrimary", "primaryContainer", "onPrimaryContainer",
        "secondary", "secondaryContainer", "tertiary", "tertiaryContainer",
        "error", "surface", "onSurface", "surfaceVariant", "onSurfaceVariant",
        "outline", "outlineVariant", "surfaceContainerHigh", "inversePrimary"
    ]

    function roleLabel(r) {
        var s = r.replace(/([A-Z])/g, " $1")
        return s.charAt(0).toUpperCase() + s.slice(1)
    }

    Flickable {
        anchors.fill: parent
        contentHeight: col.height + 20
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: col
            width: parent.width
            spacing: 0

            Item {
                width: col.width
                height: 46

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 8

                    Capsule {
                        anchors.verticalCenter: parent.verticalCenter
                        icon: "\u25D0"
                        label: Color.dark ? "Dark" : "Light"
                        onTapped: Color.dark = !Color.dark
                    }

                    Capsule {
                        anchors.verticalCenter: parent.verticalCenter
                        icon: "\u25CE"
                        label: "Orbit"
                        onTapped: root.host && root.host.toggleOrbit()
                    }

                    Capsule {
                        anchors.verticalCenter: parent.verticalCenter
                        icon: "\u25A3"
                        label: "Wallpaper"
                        onTapped: root.host && root.host.togglePanel("wallpaper")
                    }
                }
            }

            Rectangle {
                width: col.width
                height: 1
                color: Theme.rgba("outlineVariant", 0.5)
            }

            Item {
                width: col.width
                height: 44

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    spacing: 10

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 90
                        text: "Seed"
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fs
                    }

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 30
                        height: 30
                        radius: 15
                        color: Qt.rgba(Color.seed[0] / 255, Color.seed[1] / 255, Color.seed[2] / 255, 1)
                        border.width: 1
                        border.color: Theme.rgba("outline", 0.7)
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "hue " + Color.hue + "\u00B0  chroma " + Color.chroma
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                    }
                }
            }

            Repeater {
                model: root.roles

                delegate: Item {
                    required property string modelData

                    width: col.width
                    height: 36

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        spacing: 10

                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 30
                            height: 22
                            radius: 6
                            color: Theme.p(modelData)
                            border.width: 1
                            border.color: Theme.rgba("outlineVariant", 0.6)
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 170
                            text: root.roleLabel(modelData)
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                            elide: Text.ElideRight
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: Theme.p(modelData)
                            color: Theme.textMuted
                            font.family: "monospace"
                            font.pixelSize: Theme.fsSmall
                        }
                    }
                }
            }

            Item {
                width: col.width
                height: 40

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Wallpaper: " + (Color.wallpaper.length > 0
                        ? Color.wallpaper : "(default seed)")
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                    elide: Text.ElideMiddle
                    width: parent.width - 28
                }
            }
        }
    }
}
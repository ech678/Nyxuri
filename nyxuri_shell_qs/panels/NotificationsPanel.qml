import QtQuick
import qs
import qs.core

Item {
    id: root

    property var host: null
    property int selected: 0

    readonly property var rows: Notif.items

    function move(d) {
        var n = root.rows.length
        if (n === 0) return
        root.selected = ((root.selected + d) % n + n) % n
        list.positionViewAtIndex(root.selected, ListView.Contain)
    }

    Column {
        anchors.fill: parent
        spacing: 0

        Item {
            width: parent.width
            height: 42

            Row {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: Notif.dnd ? "\u25CF" : "\u25CB"
                    label: Notif.dnd ? "Do Not Disturb" : "Notifications On"
                    active: Notif.dnd
                    onTapped: Notif.toggleDnd()
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u2715"
                    label: "Clear All"
                    onTapped: Notif.clear()
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.rows.length + " notifications"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.rgba("outlineVariant", 0.5)
        }

        ListView {
            id: list
            width: parent.width
            height: parent.height - 43
            clip: true
            model: root.rows
            currentIndex: root.selected
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                required property var modelData
                required property int index

                width: list.width
                height: Math.max(58, content.implicitHeight + 20)
                color: index === root.selected
                    ? Theme.rgba("primaryContainer", 0.45) : "transparent"

                Row {
                    id: content
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    anchors.topMargin: 10
                    anchors.bottomMargin: 10
                    spacing: 10

                    Rectangle {
                        width: 3
                        height: parent.height
                        radius: 1.5
                        color: Notif.urgencyColor(modelData.urgency)
                    }

                    Column {
                        width: parent.width - 80
                        spacing: 2

                        Row {
                            spacing: 6

                            Text {
                                text: modelData.app
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsSmall
                                font.weight: Font.DemiBold
                            }

                            Text {
                                text: Notif.ago(modelData.time)
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsSmall
                            }
                        }

                        Text {
                            width: parent.width
                            text: modelData.summary
                            visible: text.length > 0
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fs
                            font.weight: Font.Medium
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: modelData.body
                            visible: text.length > 0
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                            wrapMode: Text.WordWrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                        }
                    }

                    Capsule {
                        icon: "\u2715"
                        interactive: true
                        onTapped: Notif.dismiss(index)
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    z: -1
                    hoverEnabled: true
                    onEntered: root.selected = index
                }
            }
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.rows.length === 0
        text: Notif.dnd ? "Do not disturb" : "No notifications"
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fs
    }
}
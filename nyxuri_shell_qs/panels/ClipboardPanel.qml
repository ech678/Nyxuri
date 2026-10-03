import QtQuick
import qs
import qs.core

Item {
    id: root

    property var host: null
    property int selected: 0

    readonly property var rows: Clip.filtered

    function activate() {
        if (root.rows.length === 0) return
        Clip.copy(root.rows[root.selected].text)
        if (root.host) root.host.closeAll()
    }

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

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 250
                    height: 28
                    radius: Theme.radiusTiny
                    color: Theme.rgba("surfaceContainerHighest", 0.7)

                    TextInput {
                        id: filterInput
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fs
                        clip: true
                        focus: true
                        onTextChanged: {
                            Clip.filter = text
                            root.selected = 0
                        }
                        Keys.onDownPressed: root.move(1)
                        Keys.onUpPressed: root.move(-1)
                        Keys.onReturnPressed: root.activate()
                        Keys.onEscapePressed: {
                            if (root.host) root.host.closeAll()
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: filterInput.text.length === 0
                            text: "Filter clipboard\u2026"
                            color: Theme.textMuted
                            font: filterInput.font
                        }
                    }
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u2715"
                    label: "Clear"
                    onTapped: {
                        Clip.clear()
                        root.selected = 0
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.rows.length + " items"
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
                height: 52
                color: index === root.selected
                    ? Theme.rgba("primaryContainer", 0.55) : "transparent"

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 40
                        height: 22
                        radius: 11
                        color: Theme.rgba("secondaryContainer", 0.85)

                        Text {
                            anchors.centerIn: parent
                            text: modelData.kind
                            color: Theme.onAccentSoft
                            font.family: Theme.fontFamily
                            font.pixelSize: 9
                            font.weight: Font.DemiBold
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 130
                        spacing: 2

                        Text {
                            width: parent.width
                            text: Clip.preview(modelData.text)
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fs
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: modelData.text.length + " chars"
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                        }
                    }

                    Capsule {
                        anchors.verticalCenter: parent.verticalCenter
                        icon: "\u2715"
                        interactive: true
                        onTapped: {
                            Clip.remove(index)
                            if (root.selected >= Clip.filtered.length) root.selected = 0
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    z: -1
                    hoverEnabled: true
                    onEntered: root.selected = index
                    onClicked: root.activate()
                }
            }
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.rows.length === 0
        text: "Clipboard is empty"
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fs
    }
}
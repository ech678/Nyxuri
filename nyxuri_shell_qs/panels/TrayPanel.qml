import QtQuick
import qs
import qs.core
import Quickshell.Services.SystemTray

Item {
    id: root

    property var host: null
    property int selected: 0

    readonly property var items: {
        var m = SystemTray.items
        if (!m) return []
        var v = m.values
        return v ? v : []
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

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.items.length + " tray items"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u25CE"
                    label: "Orbit"
                    onTapped: root.host && root.host.toggleOrbit()
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.rgba("outlineVariant", 0.5)
        }

        ListView {
            width: parent.width
            height: parent.height - 43
            clip: true
            model: root.items
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                required property var modelData
                required property int index

                width: ListView.view.width
                height: 44
                color: index === root.selected
                    ? Theme.rgba("primaryContainer", 0.45) : "transparent"

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 22
                        height: 22
                        source: modelData.icon ? modelData.icon : ""
                        sourceSize.width: 22
                        sourceSize.height: 22
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 40
                        spacing: 1

                        Text {
                            width: parent.width
                            text: modelData.title && modelData.title.length > 0
                                ? modelData.title : modelData.id
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fs
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: modelData.tooltipDescription || ""
                            visible: text.length > 0
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                            elide: Text.ElideRight
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.selected = index
                    onClicked: {
                        if (modelData.onlyMenu) modelData.display(parent, 0, 0)
                        else modelData.activate()
                    }
                    onWheel: function (w) {
                        modelData.scroll(w.angleDelta.y > 0 ? 1 : -1, false)
                    }
                }
            }
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.items.length === 0
        text: "No tray items"
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fs
    }
}
import QtQuick
import qs
import qs.core

Item {
    id: root

    property string query: ""
    property var results: []
    property int selected: 0

    function refresh() {
        if (root.query.length === 0) {
            root.results = Apps.apps.slice(0, 60)
        } else {
            root.results = Apps.search(root.query, 60)
        }
        if (root.selected >= root.results.length) root.selected = 0
    }

    function move(d) {
        if (root.results.length === 0) return
        var n = root.results.length
        root.selected = ((root.selected + d) % n + n) % n
        list.positionViewAtIndex(root.selected, ListView.Contain)
    }

    function activate() {
        if (root.results.length === 0) return
        var a = root.results[root.selected]
        Apps.launch(a)
        if (root.host) root.host.closeAll()
    }

    function setQuery(q) {
        root.query = q
        root.selected = 0
        refresh()
    }

    property var host: null

    Component.onCompleted: refresh()

    Column {
        anchors.fill: parent
        spacing: 0

        Item {
            width: parent.width
            height: 54

            Rectangle {
                id: field
                anchors.fill: parent
                anchors.margins: 10
                radius: Theme.radiusSmall
                color: Theme.rgba("surfaceContainerHighest", 0.7)
                border.width: 1
                border.color: input.activeFocus
                    ? Theme.rgba("primary", 0.8) : "transparent"

                TextInput {
                    id: input
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsBig
                    selectionColor: Theme.accentSoft
                    selectedTextColor: Theme.onAccentSoft
                    clip: true
                    focus: true
                    onTextChanged: root.setQuery(text)
                    Component.onCompleted: forceActiveFocus()

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: input.text.length === 0
                        text: "Search or ask."
                        color: Theme.textMuted
                        font: input.font
                    }

                    Keys.onDownPressed: root.move(1)
                    Keys.onUpPressed: root.move(-1)
                    Keys.onTabPressed: root.move(1)
                    Keys.onBacktabPressed: root.move(-1)
                    Keys.onReturnPressed: root.activate()
                    Keys.onEnterPressed: root.activate()
                    Keys.onEscapePressed: {
                        if (root.host) root.host.closeAll()
                    }
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
            height: parent.height - 55
            clip: true
            model: root.results
            currentIndex: root.selected
            boundsBehavior: Flickable.StopAtBounds
            cacheBuffer: 400

            delegate: Rectangle {
                required property var modelData
                required property int index

                width: list.width
                height: 46
                color: index === root.selected
                    ? Theme.rgba("primaryContainer", 0.55) : "transparent"

                Behavior on color {
                    ColorAnimation { duration: 90 }
                }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Item {
                        width: 26
                        height: 26
                        anchors.verticalCenter: parent.verticalCenter

                        Image {
                            anchors.fill: parent
                            source: modelData.icon ? modelData.icon : ""
                            sourceSize.width: 26
                            sourceSize.height: 26
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            visible: status === Image.Ready
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: parent.children[0].status !== Image.Ready
                            text: "\u25A0"
                            color: Theme.accent
                            font.pixelSize: 14
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 60
                        spacing: 1

                        Text {
                            text: modelData.name
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fs
                            font.weight: Font.Medium
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: modelData.desc
                            visible: text.length > 0
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.selected = index
                    onClicked: root.activate()
                }
            }
        }
    }
}
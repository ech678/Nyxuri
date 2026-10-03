import QtQuick
import qs
import qs.core
import "../core/Orbit.js" as O

Item {
    id: root

    property var host: null
    property int columns: 3
    property int selected: 0

    function activate() {
        if (Wall.files.length === 0) return
        Wall.pick(root.selected)
    }

    function move(d) {
        var n = Wall.files.length
        if (n === 0) return
        root.selected = ((root.selected + d) % n + n) % n
        grid.positionViewAtIndex(root.selected, GridView.Contain)
    }

    Component.onCompleted: {
        if (Wall.current.length > 0 && Wall.files.indexOf(Wall.current) >= 0) {
            root.selected = Wall.files.indexOf(Wall.current)
        }
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
                    icon: "\u21BB"
                    label: "Random"
                    onTapped: Wall.random()
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u2190"
                    label: "Prev"
                    onTapped: Wall.prev()
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u2192"
                    label: "Next"
                    onTapped: Wall.next()
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u25D0"
                    label: Color.dark ? "Light" : "Dark"
                    onTapped: Color.dark = !Color.dark
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 420
                    text: Wall.dir.length > 0 ? Wall.dir : "scanning\u2026"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                    elide: Text.ElideLeft
                    horizontalAlignment: Text.AlignRight
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.rgba("outlineVariant", 0.5)
        }

        GridView {
            id: grid
            width: parent.width
            height: parent.height - 43
            clip: true
            cellWidth: width / root.columns
            cellHeight: cellWidth * 0.62
            model: Wall.files
            currentIndex: root.selected
            boundsBehavior: Flickable.StopAtBounds

            delegate: Item {
                required property string modelData
                required property int index

                width: grid.cellWidth
                height: grid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: Theme.radiusTiny
                    color: Theme.rgba("surfaceContainerHighest", 0.5)
                    border.width: index === root.selected ? 2 : 1
                    border.color: index === root.selected
                        ? Theme.accent : Theme.rgba("outlineVariant", 0.5)
                    clip: true

                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: "file://" + modelData
                        sourceSize.width: 320
                        sourceSize.height: 200
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        cache: true
                        smooth: true
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 20
                        color: Theme.rgba("scrim", 0.65)

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 6
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 12
                            text: Wall.prettyName(modelData)
                            color: "#ffffff"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                            elide: Text.ElideMiddle
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.selected = index
                    onClicked: {
                        root.selected = index
                        Wall.pick(index)
                    }
                }
            }
        }
    }
}
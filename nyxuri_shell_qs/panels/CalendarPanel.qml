import QtQuick
import qs
import qs.core

Item {
    id: root

    property var host: null
    property int monthOffset: 0
    property int tick: 0

    readonly property var now: {
        var t = root.tick
        return new Date()
    }
    readonly property var shown: {
        var d = new Date(root.now.getFullYear(), root.now.getMonth() + root.monthOffset, 1)
        return d
    }

    readonly property var days: {
        var d = root.shown
        var first = new Date(d.getFullYear(), d.getMonth(), 1)
        var startDow = first.getDay()
        var daysInMonth = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()
        var out = []
        for (var i = 0; i < startDow; i++) out.push({ day: 0, today: false })
        for (var k = 1; k <= daysInMonth; k++) {
            var isToday = k === root.now.getDate()
                && d.getMonth() === root.now.getMonth()
                && d.getFullYear() === root.now.getFullYear()
            out.push({ day: k, today: isToday })
        }
        while (out.length % 7 !== 0) out.push({ day: 0, today: false })
        return out
    }

    readonly property string monthName: {
        var names = ["January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"]
        return names[root.shown.getMonth()]
    }

    Column {
        anchors.fill: parent
        spacing: 0

        Item {
            width: parent.width
            height: 52

            Row {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u2190"
                    onTapped: root.monthOffset = root.monthOffset - 1
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 220
                    text: root.monthName + " " + root.shown.getFullYear()
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsBig
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "\u2192"
                    onTapped: root.monthOffset = root.monthOffset + 1
                }

                Capsule {
                    anchors.verticalCenter: parent.verticalCenter
                    label: "Today"
                    onTapped: root.monthOffset = 0
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.rgba("outlineVariant", 0.5)
        }

        Grid {
            width: parent.width
            columns: 7
            padding: 10
            spacing: 0

            Repeater {
                model: ["S", "M", "T", "W", "T", "F", "S"]

                delegate: Item {
                    required property string modelData
                    width: (root.width - 20) / 7
                    height: 22

                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                        font.weight: Font.DemiBold
                    }
                }
            }

            Repeater {
                model: root.days

                delegate: Item {
                    required property var modelData
                    width: (root.width - 20) / 7
                    height: 30

                    Rectangle {
                        anchors.centerIn: parent
                        width: 26
                        height: 26
                        radius: 13
                        visible: modelData.today
                        color: Theme.accent
                    }

                    Text {
                        anchors.centerIn: parent
                        text: modelData.day > 0 ? String(modelData.day) : ""
                        color: modelData.today ? Theme.onAccent : Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fs
                        font.weight: modelData.today ? Font.Bold : Font.Normal
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: 8
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.now.toLocaleString(Qt.locale(), "ddd, dd MMM yyyy \u00B7 HH:mm")
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
        }
    }
}
import QtQuick
import qs
import qs.core

Item {
    id: root

    property var host: null
    property var history: []
    property int maxPoints: 60

    function sample() {
        var h = root.history.slice()
        h.push({ cpu: Sys.cpu, ram: Sys.ram })
        if (h.length > root.maxPoints) h = h.slice(h.length - root.maxPoints)
        root.history = h
        chart.requestPaint()
    }

    Component.onCompleted: {
        var h = []
        for (var i = 0; i < 30; i++) h.push({ cpu: Sys.cpu, ram: Sys.ram })
        root.history = h
    }

    Timer {
        interval: 2000
        running: true
        repeat: true
        onTriggered: root.sample()
    }

    Column {
        anchors.fill: parent
        spacing: 0

        Item {
            width: parent.width
            height: 150

            Canvas {
                id: chart
                anchors.fill: parent
                anchors.margins: 12
                renderStrategy: Canvas.Cooperative
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    var w = width
                    var h = height
                    var n = root.history.length
                    if (n < 2) return

                    ctx.strokeStyle = Theme.rgba("outlineVariant", 0.35)
                    ctx.lineWidth = 1
                    for (var g = 1; g < 4; g++) {
                        var gy = h * g / 4
                        ctx.beginPath()
                        ctx.moveTo(0, gy)
                        ctx.lineTo(w, gy)
                        ctx.stroke()
                    }

                    var step = w / (n - 1)

                    var draw = function (key, color) {
                        ctx.beginPath()
                        for (var i = 0; i < n; i++) {
                            var x = i * step
                            var y = h - root.history[i][key] * h
                            if (i === 0) ctx.moveTo(x, y)
                            else ctx.lineTo(x, y)
                        }
                        ctx.strokeStyle = color
                        ctx.lineWidth = 2
                        ctx.stroke()
                    }

                    draw("ram", Theme.p("tertiary"))
                    draw("cpu", Theme.p("primary"))
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
            columns: 2
            padding: 14
            spacing: 10

            Column {
                spacing: 2
                width: parent.width / 2 - 20

                Text {
                    text: "CPU"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                Text {
                    text: Sys.cpuText
                    color: Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: 22
                    font.weight: Font.DemiBold
                }
            }

            Column {
                spacing: 2
                width: parent.width / 2 - 20

                Text {
                    text: "Memory"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                Text {
                    text: Sys.ramText
                    color: Theme.p("tertiary")
                    font.family: Theme.fontFamily
                    font.pixelSize: 22
                    font.weight: Font.DemiBold
                }
            }

            Column {
                spacing: 2
                width: parent.width / 2 - 20

                Text {
                    text: "Swap"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                Text {
                    text: Math.round(Sys.swap * 100) + "%"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                }
            }

            Column {
                spacing: 2
                width: parent.width / 2 - 20

                Text {
                    text: "Battery"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                Text {
                    text: Sys.hasBattery ? Sys.batteryText + (Sys.charging ? " \u26A1" : "") : "n/a"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                }
            }
        }

        Item {
            width: parent.width
            height: 6
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

            Capsule {
                icon: "\u266B"
                label: Sys.volumeText
                onTapped: Sys.toggleMute()
                onScrolled: function (d) { Sys.bumpVolume(d * 0.05) }
            }

            Capsule {
                icon: "\u25CE"
                label: "Orbit"
                onTapped: root.host && root.host.toggleOrbit()
            }
        }
    }
}
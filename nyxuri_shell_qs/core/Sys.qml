pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import Quickshell.Services.Pipewire

Singleton {
    id: root

    property real cpu: 0
    property real ram: 0
    property real swap: 0
    property bool hasBattery: false
    property real battery: 0
    property bool charging: false
    property bool batteryActive: false
    property real volume: 0
    property bool muted: false
    property bool hasAudio: false

    property real prevIdle: 0
    property real prevTotal: 0

    readonly property string cpuText: Math.round(cpu * 100) + "%"
    readonly property string ramText: Math.round(ram * 100) + "%"

    readonly property string batteryText: hasBattery
        ? (Math.round(battery * 100) + "%") : ""

    readonly property string volumeText: hasAudio
        ? (muted ? "MUTE" : Math.round(volume * 100) + "%") : "--"

    function parseStat(text) {
        if (!text || text.length === 0) return
        var line = text.split("\n")[0]
        var p = line.split(/\s+/)
        if (p.length < 8) return
        var vals = []
        for (var i = 1; i < 9; i++) vals.push(parseInt(p[i]) || 0)
        var idle = vals[3] + vals[4]
        var total = 0
        for (var j = 0; j < vals.length; j++) total += vals[j]
        if (root.prevTotal > 0) {
            var dt = total - root.prevTotal
            var di = idle - root.prevIdle
            if (dt > 0) {
                var v = 1 - di / dt
                if (v < 0) v = 0
                if (v > 1) v = 1
                root.cpu = v
            }
        }
        root.prevIdle = idle
        root.prevTotal = total
    }

    function parseMem(text) {
        if (!text || text.length === 0) return
        var rows = text.split("\n")
        var total = 0
        var avail = 0
        var st = 0
        var sf = 0
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i]
            var m = r.match(/^(\w+):\s+(\d+)/)
            if (!m) continue
            var k = m[1]
            var v = parseInt(m[2])
            if (k === "MemTotal") total = v
            else if (k === "MemAvailable") avail = v
            else if (k === "SwapTotal") st = v
            else if (k === "SwapFree") sf = v
        }
        if (total > 0) root.ram = (total - avail) / total
        if (st > 0) root.swap = (st - sf) / st
        else root.swap = 0
    }

    function refreshBattery() {
        var d = UPower.displayDevice
        if (!d || !d.ready) {
            root.hasBattery = false
            return
        }
        root.hasBattery = d.isPresent && d.isLaptopBattery
        root.battery = d.percentage
        root.charging = d.state === UPowerDeviceState.Charging
            || d.state === UPowerDeviceState.FullyCharged
        root.batteryActive = UPower.onBattery
    }

    function refreshAudio() {
        var s = Pipewire.defaultAudioSink
        if (!s || !s.ready || !s.audio) {
            root.hasAudio = false
            return
        }
        root.hasAudio = true
        root.volume = s.audio.volume
        root.muted = s.audio.muted
    }

    function setVolume(v) {
        var s = Pipewire.defaultAudioSink
        if (!s || !s.ready || !s.audio) return
        var nv = Math.max(0, Math.min(1, v))
        s.audio.volume = nv
        if (nv > 0 && s.audio.muted) s.audio.muted = false
    }

    function toggleMute() {
        var s = Pipewire.defaultAudioSink
        if (!s || !s.ready || !s.audio) return
        s.audio.muted = !s.audio.muted
    }

    function bumpVolume(delta) {
        if (!root.hasAudio) return
        root.setVolume(root.volume + delta)
    }

    function batIcon() {
        if (!root.hasBattery) return ""
        if (root.charging) return "\u26A1"
        var v = Math.round(root.battery * 100)
        if (v >= 90) return "\u2588"
        if (v >= 60) return "\u2586"
        if (v >= 40) return "\u2584"
        if (v >= 20) return "\u2582"
        return "\u2581"
    }

    function volIcon() {
        if (!root.hasAudio) return "\u266B"
        if (root.muted) return "\u266B\u0338"
        if (root.volume <= 0.01) return "\u266B"
        if (root.volume < 0.4) return "\u266A"
        return "\u266B"
    }

    Component.onCompleted: {
        statFile.path = "/proc/stat"
        memFile.path = "/proc/meminfo"
        refreshBattery()
        refreshAudio()
    }

    FileView {
        id: statFile
        printErrors: false
        watchChanges: false
        onFileChanged: {
            reload()
        }
        onTextChanged: root.parseStat(text())
    }

    FileView {
        id: memFile
        printErrors: false
        watchChanges: false
        onFileChanged: reload()
        onTextChanged: root.parseMem(text())
    }

    Timer {
        interval: 2000
        running: true
        repeat: true
        onTriggered: {
            statFile.reload()
            memFile.reload()
            root.refreshBattery()
            root.refreshAudio()
        }
    }

    Connections {
        target: UPower.displayDevice
        ignoreUnknownSignals: true
        function onPercentageChanged() { root.refreshBattery() }
        function onStateChanged() { root.refreshBattery() }
        function onIsPresentChanged() { root.refreshBattery() }
    }

    Connections {
        target: UPower
        ignoreUnknownSignals: true
        function onOnBatteryChanged() { root.refreshBattery() }
    }

    Connections {
        target: Pipewire.defaultAudioSink
        ignoreUnknownSignals: true
        function onReadyChanged() { root.refreshAudio() }
    }

    Connections {
        target: Pipewire
        ignoreUnknownSignals: true
        function onDefaultAudioSinkChanged() { root.refreshAudio() }
    }
}
pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "M3.js" as M3

Singleton {
    id: root

    property bool dark: true
    property string wallpaper: ""
    property var seed: [0x67, 0x50, 0xa4]
    property var scheme: ({})
    property string hue: "0"
    property string chroma: "0"
    property var stateFile: ""

    readonly property string sroot: {
        var h = Quickshell.env("XDG_STATE_HOME")
        if (!h || h.length === 0) {
            h = Quickshell.env("HOME") + "/.local/state"
        }
        return h
    }

    function dirOf(p) {
        var i = p.lastIndexOf("/")
        return i > 0 ? p.substring(0, i) : p
    }

    function hexOf(v) {
        var s = v.toString(16)
        while (s.length < 2) s = "0" + s
        return s
    }

    function rebuild() {
        var r = M3.generateScheme(root.seed, root.dark)
        root.scheme = r
        root.hue = r.__hue
        root.chroma = r.__chroma
    }

    function setWallpaper(path) {
        if (!path || path.length === 0) return
        root.wallpaper = path
        var u = path
        if (u.indexOf("file://") !== 0) u = "file://" + u
        quantizer.source = u
        saveState()
    }

    function saveState() {
        if (!stateFile || !stateWriter.path) return
        var lines = []
        lines.push("wallpaper=" + root.wallpaper)
        lines.push("dark=" + (root.dark ? "1" : "0"))
        lines.push("hue=" + root.hue)
        lines.push("chroma=" + root.chroma)
        stateWriter.setText(lines.join("\n") + "\n")
    }

    function loadState(text) {
        if (!text) return
        var rows = text.split("\n")
        for (var i = 0; i < rows.length; i++) {
            var p = rows[i].indexOf("=")
            if (p <= 0) continue
            var k = rows[i].substring(0, p)
            var v = rows[i].substring(p + 1)
            if (k === "wallpaper" && v.length > 0) {
                root.wallpaper = v
                var u = v
                if (u.indexOf("file://") !== 0) u = "file://" + u
                quantizer.source = u
            } else if (k === "dark") {
                root.dark = (v === "1")
            }
        }
    }

    Component.onCompleted: {
        stateFile = root.sroot + "/nyxuri-shell-qml/color.ini"
        stateWriter.path = stateFile
        rebuild()
        stateLoader.path = stateFile
    }

    onDarkChanged: {
        rebuild()
        saveState()
    }

    onSeedChanged: rebuild()

    FileView {
        id: stateLoader
        blockWrites: false
        printErrors: false
        onTextChanged: root.loadState(text())
    }

    FileView {
        id: stateWriter
        blockWrites: false
        printErrors: false
        watchChanges: false
    }

    FileView {
        id: homeProbe
        printErrors: false
    }

    ColorQuantizer {
        id: quantizer
        depth: 2
        rescaleSize: 64
        onColorsChanged: {
            var c = colors
            if (!c || c.length === 0) return
            var best = c[0]
            var bestScore = -1
            for (var i = 0; i < c.length; i++) {
                var col = c[i]
                var r = Math.round(col.r * 255)
                var g = Math.round(col.g * 255)
                var b = Math.round(col.b * 255)
                var mx = Math.max(r, Math.max(g, b))
                var mn = Math.min(r, Math.min(g, b))
                var sat = mx - mn
                var lum = 0.299 * r + 0.587 * g + 0.114 * b
                var score = sat * 2 + (255 - Math.abs(lum - 140)) / 4
                if (score > bestScore) {
                    bestScore = score
                    best = [r, g, b]
                }
            }
            root.seed = best
            rebuild()
            saveState()
        }
    }


}
pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    property var items: []
    property int maxItems: 60
    property string filter: ""
    property bool persist: true

    readonly property var filtered: {
        var f = root.filter
        if (!f || f.length === 0) return root.items
        var s = f.toLowerCase()
        var out = []
        for (var i = 0; i < root.items.length; i++) {
            if (root.items[i].text.toLowerCase().indexOf(s) >= 0) out.push(root.items[i])
        }
        return out
    }

    function filePath() {
        var h = Quickshell.env("XDG_STATE_HOME")
        if (!h || h.length === 0) h = Quickshell.env("HOME") + "/.local/state"
        return h + "/nyxuri-shell-qml/clipboard.txt"
    }

    function encode(s) {
        try {
            return Qt.btoa(s)
        } catch (e) {
            return ""
        }
    }

    function decode(s) {
        try {
            return Qt.atob(s)
        } catch (e) {
            return ""
        }
    }

    function preview(t) {
        if (!t) return ""
        var one = t.replace(/\s+/g, " ").trim()
        if (one.length > 90) return one.substring(0, 90) + "\u2026"
        return one
    }

    function kindOf(t) {
        if (!t) return "text"
        var s = t.trim()
        if (/^https?:\/\/\S+$/.test(s)) return "url"
        if (/^[\w.+-]+@[\w-]+\.[\w.]+$/.test(s)) return "mail"
        if (/^-?\d+(\.\d+)?$/.test(s)) return "number"
        if (/\n/.test(t)) return "multi"
        return "text"
    }

    function add(t) {
        if (!t || t.length === 0) return false
        if (t.length > 20000) return false
        var out = []
        out.push({ text: t, kind: root.kindOf(t), stamp: Date.now() })
        for (var i = 0; i < root.items.length; i++) {
            if (root.items[i].text === t) continue
            out.push(root.items[i])
        }
        if (out.length > root.maxItems) out = out.slice(0, root.maxItems)
        root.items = out
        root.save()
        return true
    }

    function copy(t) {
        if (!t) return false
        Quickshell.clipboardText = t
        root.add(t)
        return true
    }

    function remove(i) {
        if (i < 0 || i >= root.items.length) return false
        var out = root.items.slice()
        out.splice(i, 1)
        root.items = out
        root.save()
        return true
    }

    function clear() {
        root.items = []
        root.save()
    }

    function save() {
        if (!root.persist) return
        var lines = []
        for (var i = 0; i < root.items.length; i++) {
            var e = root.encode(root.items[i].text)
            if (e.length > 0) lines.push(e)
        }
        store.setText(lines.join("\n") + "\n")
    }

    function load(text) {
        if (!text) return
        var rows = text.split("\n")
        var out = []
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i].trim()
            if (r.length === 0) continue
            var t = root.decode(r)
            if (t.length === 0) continue
            out.push({ text: t, kind: root.kindOf(t), stamp: 0 })
            if (out.length >= root.maxItems) break
        }
        root.items = out
    }

    Component.onCompleted: {
        store.path = root.filePath()
        loader.path = root.filePath()
    }

    FileView {
        id: store
        printErrors: false
        watchChanges: false
    }

    FileView {
        id: loader
        printErrors: false
        watchChanges: true
        onLoaded: root.load(text())
        onFileChanged: reload()
    }

    Connections {
        target: Quickshell
        ignoreUnknownSignals: true
        function onClipboardTextChanged() {
            var t = Quickshell.clipboardText
            if (t && t.length > 0) root.add(t)
        }
    }
}
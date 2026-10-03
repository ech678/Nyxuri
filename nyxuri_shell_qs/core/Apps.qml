pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    property var apps: []
    property var groups: []
    property bool loaded: false

    function groupsPath() {
        var h = Quickshell.env("XDG_CONFIG_HOME")
        if (!h || h.length === 0) h = Quickshell.env("HOME") + "/.config"
        return h + "/nyxuri-shell-qml/groups.json"
    }

    function iconFor(name, entry) {
        var icons = Quickshell.env("HOME") + "/.local/share/icons"
        var flat = ["utilities-terminal", "org.gnome.Terminal", "kitty", "foot"]
        var theme = entry && entry.icon ? entry.icon : ""
        if (theme.length > 0) {
            var p = Quickshell.iconPath(theme, true)
            if (p && p.length > 0) return "image://icon/" + theme
        }
        var guess = (name || "").toLowerCase()
        for (var i = 0; i < flat.length; i++) {
            if (guess.indexOf(flat[i].toLowerCase()) >= 0) {
                var q = Quickshell.iconPath(flat[i], true)
                if (q && q.length > 0) return "image://icon/" + flat[i]
            }
        }
        return "image://icon/application-x-executable"
    }

    function loadEntries() {
        var m = DesktopEntries.applications
        if (!m) return
        var vals = m.values
        if (!vals) return
        var out = []
        for (var i = 0; i < vals.length; i++) {
            var e = vals[i]
            if (!e) continue
            if (e.noDisplay) continue
            var cmd = e.command
            if (!cmd || cmd.length === 0) continue
            out.push({
                id: e.id || ("app-" + i),
                name: e.name || e.id,
                desc: e.comment || e.genericName || "",
                icon: root.iconFor(e.name || "", e),
                command: cmd,
                terminal: e.runInTerminal === true,
                categories: e.categories || [],
                keywords: e.keywords || [],
                entry: e
            })
        }
        out.sort(function (a, b) {
            return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1
        })
        root.apps = out
        root.loaded = true
        buildGroups()
    }

    function groupKey(app) {
        var c = app.categories
        for (var i = 0; i < c.length; i++) {
            var k = c[i]
            if (k === "AudioVideo" || k === "Audio" || k === "Video" || k === "Player") return "Media"
            if (k === "Development" || k === "IDE" || k === "TextEditor") return "Development"
            if (k === "Graphics") return "Graphics"
            if (k === "Network" || k === "WebBrowser" || k === "Email" || k === "InstantMessaging") return "Websites"
            if (k === "Game") return "Games"
            if (k === "Office" || k === "Spreadsheet" || k === "WordProcessor") return "Office"
            if (k === "System" || k === "Settings" || k === "Utility") return "System Tools"
            if (k === "Education") return "Education"
        }
        return "Other"
    }

    function buildGroups() {
        var order = ["Websites", "Development", "Graphics", "Media", "Office", "System Tools", "Games", "Education", "Other"]
        var map = {}
        for (var i = 0; i < root.apps.length; i++) {
            var a = root.apps[i]
            var k = root.groupKey(a)
            if (!map[k]) map[k] = []
            map[k].push(a)
        }
        var custom = root.customGroups()
        var out = []
        for (var j = 0; j < order.length; j++) {
            var name = order[j]
            if (map[name] && map[name].length > 0) {
                out.push({
                    id: "group:" + name,
                    name: name,
                    kind: "group",
                    count: map[name].length,
                    children: map[name]
                })
            }
        }
        for (var c = 0; c < custom.length; c++) {
            var g = custom[c]
            if (!g || !g.name) continue
            var kids = []
            for (var m = 0; m < root.apps.length; m++) {
                var ap = root.apps[m]
                if (g.ids && g.ids.indexOf(ap.id) >= 0) kids.push(ap)
                else if (g.match && ap.name.toLowerCase().indexOf(g.match.toLowerCase()) >= 0) kids.push(ap)
            }
            if (kids.length > 0) {
                out.push({
                    id: "group:" + g.name,
                    name: g.name,
                    kind: "group",
                    count: kids.length,
                    children: kids
                })
            }
        }
        root.groups = out
    }

    function customGroups() {
        var t = groupsFile.text()
        if (!t || t.length === 0) return []
        try {
            var d = JSON.parse(t)
            if (d && d.groups) return d.groups
            return []
        } catch (e) {
            return []
        }
    }

    function search(q, limit) {
        if (!q || q.length === 0) return []
        var s = q.toLowerCase()
        var out = []
        for (var i = 0; i < root.apps.length; i++) {
            var a = root.apps[i]
            var hay = a.name.toLowerCase()
            if (hay.indexOf(s) === 0) {
                out.push(a)
                continue
            }
            if (hay.indexOf(s) >= 0) {
                out.push(a)
                continue
            }
            if (a.desc && a.desc.toLowerCase().indexOf(s) >= 0) {
                out.push(a)
                continue
            }
            var kw = a.keywords
            for (var k = 0; k < kw.length; k++) {
                if (kw[k].toLowerCase().indexOf(s) >= 0) {
                    out.push(a)
                    break
                }
            }
        }
        return out.slice(0, limit || 20)
    }

    function launch(app) {
        if (!app || !app.command || app.command.length === 0) return false
        Quickshell.execDetached(app.command)
        return true
    }

    Component.onCompleted: {
        groupsFile.path = groupsPath()
        loadEntries()
    }

    FileView {
        id: groupsFile
        printErrors: false
        onTextChanged: root.buildGroups()
    }

    Connections {
        target: DesktopEntries.applications
        ignoreUnknownSignals: true
        function onValuesChanged() { root.loadEntries() }
    }

    Timer {
        interval: 500
        running: true
        repeat: true
        onTriggered: {
            if (!root.loaded) root.loadEntries()
            if (root.apps.length > 0) stop()
        }
    }

    Timer {
        interval: 30000
        running: true
        repeat: true
        onTriggered: root.loadEntries()
    }
}
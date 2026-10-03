pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    property string backend: ""
    property var items: []
    property string focusedTitle: ""
    property string focusedApp: ""
    property bool available: false

    readonly property int focusedIndex: {
        for (var i = 0; i < root.items.length; i++) {
            if (root.items[i].focused) return i
        }
        return -1
    }

    readonly property var occupied: {
        var out = []
        for (var i = 0; i < root.items.length; i++) {
            if (root.items[i].occupied) out.push(root.items[i])
        }
        return out
    }

    function detect() {
        detectProc.command = ["sh", "-c",
            "if command -v niri >/dev/null 2>&1 && niri msg -j workspaces >/dev/null 2>&1; then echo niri; "
            + "elif command -v swaymsg >/dev/null 2>&1 && swaymsg -t get_workspaces >/dev/null 2>&1; then echo sway; "
            + "elif [ -n \"$HYPRLAND_INSTANCE_SIGNATURE\" ]; then echo hyprland; "
            + "else echo none; fi"]
        detectProc.running = true
    }

    function poll() {
        if (root.backend === "niri") {
            wsProc.command = ["niri", "msg", "-j", "workspaces"]
            wsProc.running = true
            winProc.command = ["niri", "msg", "-j", "focused-window"]
            winProc.running = true
        } else if (root.backend === "sway") {
            wsProc.command = ["swaymsg", "-t", "get_workspaces"]
            wsProc.running = true
            winProc.command = ["swaymsg", "-t", "get_tree"]
            winProc.running = true
        } else if (root.backend === "hyprland") {
            wsProc.command = ["sh", "-c", "hyprctl -j workspaces"]
            wsProc.running = true
            winProc.command = ["sh", "-c", "hyprctl -j activewindow"]
            winProc.running = true
        }
    }

    function parseNiriWorkspaces(text) {
        var d = null
        try {
            d = JSON.parse(text)
        } catch (e) {
            return
        }
        if (!d || !d.length) {
            root.items = []
            return
        }
        var out = []
        for (var i = 0; i < d.length; i++) {
            var w = d[i]
            out.push({
                id: w.id,
                name: w.name && w.name.length > 0 ? w.name : String(w.idx),
                idx: w.idx,
                output: w.output,
                focused: w.is_focused === true,
                active: w.is_active === true,
                urgent: w.is_urgent === true,
                occupied: w.active_window_id !== null && w.active_window_id !== undefined
            })
        }
        out.sort(function (a, b) { return a.idx - b.idx })
        root.items = out
        root.available = true
    }

    function parseSwayWorkspaces(text) {
        var d = null
        try {
            d = JSON.parse(text)
        } catch (e) {
            return
        }
        if (!d || !d.length) {
            root.items = []
            return
        }
        var out = []
        for (var i = 0; i < d.length; i++) {
            var w = d[i]
            out.push({
                id: w.num,
                name: w.name,
                idx: w.num,
                output: w.output,
                focused: w.focused === true,
                active: w.visible === true,
                urgent: w.urgent === true,
                occupied: true
            })
        }
        out.sort(function (a, b) { return a.idx - b.idx })
        root.items = out
        root.available = true
    }

    function parseHyprWorkspaces(text) {
        var d = null
        try {
            d = JSON.parse(text)
        } catch (e) {
            return
        }
        if (!d || !d.length) {
            root.items = []
            return
        }
        var out = []
        for (var i = 0; i < d.length; i++) {
            var w = d[i]
            out.push({
                id: w.id,
                name: w.name && w.name.length > 0 ? w.name : String(w.id),
                idx: w.id,
                output: w.monitor,
                focused: w.id === (d.focused || -1),
                active: w.windows > 0,
                urgent: false,
                occupied: w.windows > 0
            })
        }
        out.sort(function (a, b) { return a.idx - b.idx })
        root.items = out
        root.available = true
    }

    function parseNiriWindow(text) {
        var d = null
        try {
            d = JSON.parse(text)
        } catch (e) {
            root.focusedTitle = ""
            root.focusedApp = ""
            return
        }
        if (!d || !d.id) {
            root.focusedTitle = ""
            root.focusedApp = ""
            return
        }
        root.focusedTitle = d.title ? d.title : ""
        root.focusedApp = d.app_id ? d.app_id : ""
    }

    function parseHyprWindow(text) {
        var d = null
        try {
            d = JSON.parse(text)
        } catch (e) {
            return
        }
        if (!d || !d.title) {
            root.focusedTitle = ""
            root.focusedApp = ""
            return
        }
        root.focusedTitle = d.title
        root.focusedApp = d.class ? d.class : ""
    }

    function focus(idx) {
        if (idx < 0 || idx >= root.items.length) return false
        var w = root.items[idx]
        if (root.backend === "niri") {
            Quickshell.execDetached(["niri", "msg", "action", "focus-workspace", String(w.id)])
        } else if (root.backend === "sway") {
            Quickshell.execDetached(["swaymsg", "workspace", "number", String(w.idx)])
        } else if (root.backend === "hyprland") {
            Quickshell.execDetached(["hyprctl", "dispatch", "workspace", String(w.id)])
        } else {
            return false
        }
        return true
    }

    function cycle(delta) {
        var i = root.focusedIndex
        if (i < 0) return false
        var n = root.items.length
        if (n === 0) return false
        var t = ((i + delta) % n + n) % n
        return root.focus(t)
    }

    Component.onCompleted: detect()

    Process {
        id: detectProc
        command: []
        running: false
        stdout: StdioCollector {
            id: detectOut
            waitForEnd: true
            onStreamFinished: {
                var t = (detectOut.text || "").trim()
                root.backend = t
                if (t !== "none") {
                    root.poll()
                    pollTimer.running = true
                }
            }
        }
    }

    Process {
        id: wsProc
        command: []
        running: false
        stdout: StdioCollector {
            id: wsOut
            waitForEnd: true
            onStreamFinished: {
                if (root.backend === "niri") root.parseNiriWorkspaces(wsOut.text)
                else if (root.backend === "sway") root.parseSwayWorkspaces(wsOut.text)
                else if (root.backend === "hyprland") root.parseHyprWorkspaces(wsOut.text)
            }
        }
    }

    Process {
        id: winProc
        command: []
        running: false
        stdout: StdioCollector {
            id: winOut
            waitForEnd: true
            onStreamFinished: {
                if (root.backend === "niri") root.parseNiriWindow(winOut.text)
                else if (root.backend === "hyprland") root.parseHyprWindow(winOut.text)
            }
        }
    }

    Timer {
        id: pollTimer
        interval: 1200
        running: false
        repeat: true
        onTriggered: root.poll()
    }
}
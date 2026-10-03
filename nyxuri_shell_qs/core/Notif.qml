pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Services.Notifications

Singleton {
    id: root

    property var items: []
    property int maxItems: 40
    property bool dnd: false

    readonly property int count: root.dnd ? 0 : root.items.length
    readonly property bool hasAny: root.items.length > 0

    function push(n) {
        if (!n) return
        if (root.dnd) {
            n.tracked = false
            return
        }
        n.tracked = true
        var out = [{
            id: n.id,
            app: n.appName || "",
            summary: n.summary || "",
            body: n.body || "",
            urgency: n.urgency,
            time: Date.now(),
            ref: n
        }]
        for (var i = 0; i < root.items.length; i++) {
            if (root.items[i].id === n.id) continue
            out.push(root.items[i])
        }
        if (out.length > root.maxItems) out = out.slice(0, root.maxItems)
        root.items = out
    }

    function dismiss(i) {
        if (i < 0 || i >= root.items.length) return
        var it = root.items[i]
        if (it.ref) it.ref.dismiss()
        var out = root.items.slice()
        out.splice(i, 1)
        root.items = out
    }

    function clear() {
        for (var i = 0; i < root.items.length; i++) {
            if (root.items[i].ref) root.items[i].ref.dismiss()
        }
        root.items = []
    }

    function toggleDnd() {
        root.dnd = !root.dnd
        if (root.dnd) root.clear()
    }

    function urgencyColor(u) {
        if (u === NotificationUrgency.Critical) return Theme.err
        if (u === NotificationUrgency.Low) return Theme.textMuted
        return Theme.accent
    }

    function ago(t) {
        if (!t) return ""
        var d = Math.floor((Date.now() - t) / 1000)
        if (d < 60) return d + "s"
        if (d < 3600) return Math.floor(d / 60) + "m"
        return Math.floor(d / 3600) + "h"
    }

    NotificationServer {
        id: server
        keepOnReload: true
        bodySupported: true
        bodyMarkupSupported: false
        actionsSupported: true
        imageSupported: true
        onNotification: function (n) { root.push(n) }
    }
}
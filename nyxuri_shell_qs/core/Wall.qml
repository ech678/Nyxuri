pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    property string dir: ""
    property var files: []
    property int index: 0
    property string current: ""
    property bool scanning: false
    property string lastError: ""

    function baseName(p) {
        var i = p.lastIndexOf("/")
        return i >= 0 ? p.substring(i + 1) : p
    }

    function prettyName(p) {
        var b = root.baseName(p)
        var d = b.lastIndexOf(".")
        if (d > 0) b = b.substring(0, d)
        return b.replace(/[-_]+/g, " ")
    }

    function scanScript() {
        return "for d in \"$HOME/Pictures/Wallpapers\" \"$HOME/\u56fe\u7247/Wallpapers\" \"$HOME/Pictures\" \"$HOME/\u56fe\u7247\" \"$HOME/.local/share/wallpapers\"; do "
            + "if [ -d \"$d\" ]; then echo \"__DIR__$d\"; "
            + "find \"$d\" -maxdepth 2 -type f \\( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.avif' -o -iname '*.gif' \\) 2>/dev/null | sort; "
            + "break; fi; done"
    }

    function parseList(text) {
        root.scanning = false
        if (!text) {
            root.files = []
            return
        }
        var rows = text.split("\n")
        var out = []
        var d = ""
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i].replace(/\r$/, "")
            if (r.length === 0) continue
            if (r.indexOf("__DIR__") === 0) {
                d = r.substring(7)
                continue
            }
            out.push(r)
        }
        if (d.length > 0) root.dir = d
        root.files = out
        if (out.length > 0 && out.indexOf(root.current) < 0) {
            root.index = 0
        }
    }

    function startScan() {
        root.scanning = true
        scan.command = ["sh", "-c", scanScript()]
        scan.running = true
    }

    function pick(i) {
        if (root.files.length === 0) return false
        var n = ((i % root.files.length) + root.files.length) % root.files.length
        root.index = n
        root.current = root.files[n]
        root.apply(root.current)
        return true
    }

    function random() {
        if (root.files.length === 0) return false
        return root.pick(Math.floor(Math.random() * root.files.length))
    }

    function next() {
        return root.pick(root.index + 1)
    }

    function prev() {
        return root.pick(root.index - 1)
    }

    function quote(p) {
        return "'" + p.replace(/'/g, "'\\''") + "'"
    }

    function applyScript() {
        return "f=\"$1\"; "
            + "if command -v swww >/dev/null 2>&1; then swww img \"$f\" >/dev/null 2>&1; "
            + "elif command -v awww >/dev/null 2>&1; then awww img \"$f\" >/dev/null 2>&1; "
            + "elif command -v swaybg >/dev/null 2>&1; then pkill -x swaybg >/dev/null 2>&1; setsid swaybg -i \"$f\" -m fill >/dev/null 2>&1 & "
            + "elif command -v hyprpaper >/dev/null 2>&1; then hyprctl hyprpaper wallpaper \",$f\" >/dev/null 2>&1; "
            + "elif command -v feh >/dev/null 2>&1; then feh --bg-fill \"$f\" >/dev/null 2>&1; "
            + "else echo NO_APPLIER; fi"
    }

    function apply(path) {
        if (!path || path.length === 0) return false
        Color.setWallpaper(path)
        applyProc.command = ["sh", "-c", applyScript() + " sh " + quote(path)]
        applyProc.running = true
        return true
    }

    Component.onCompleted: startScan()

    Process {
        id: scan
        command: []
        running: false
        stdout: StdioCollector {
            id: scanOut
            waitForEnd: true
            onStreamFinished: root.parseList(scanOut.text)
        }
        onExited: function (code) { root.scanning = false }
    }

    Process {
        id: applyProc
        command: []
        running: false
        stdout: StdioCollector {
            id: applyOut
            waitForEnd: true
            onStreamFinished: {
                var t = applyOut.text
                if (t && t.indexOf("NO_APPLIER") >= 0) root.lastError = "no wallpaper backend found"
                else root.lastError = ""
            }
        }
    }
}
pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.app

// LogService — the shell's single logging front door. Every domain logs
// through here instead of bare console.*: callers get level + domain tags,
// an in-memory ring surfaced over IPC and the settings page, and a bounded
// state-dir file for post-mortems. console.* passthrough keeps `qs log`
// working as the raw firehose.
//
// File semantics: shell.log holds the CURRENT session (rewritten on first
// flush), shell.prev.log holds the previous one — diagnosis usually needs
// "what happened in the run before I restarted", so one generation of
// history is kept, nothing more.
Singleton {
    id: root

    readonly property string logDir: Paths.stateHome + "/logs"
    readonly property string logPath: root.logDir + "/shell.log"
    readonly property string prevLogPath: root.logDir + "/shell.prev.log"
    readonly property int ringCapacity: 400
    // Bumps on every append; consumers re-read text()/recent() off this.
    property int revision: 0
    property var _ring: []
    property bool _dirty: false
    property bool _firstFlush: true

    function debug(domain, message) {
        root._append("DEBUG", domain, message);
    }

    function info(domain, message) {
        root._append("INFO", domain, message);
    }

    function warn(domain, message) {
        root._append("WARN", domain, message);
    }

    function error(domain, message) {
        root._append("ERROR", domain, message);
    }

    function text() {
        return root._ring.join("\n");
    }

    function recent(count) {
        return root._ring.slice(Math.max(0, root._ring.length - (count || 40)));
    }

    // Binding-facing variant: reads revision so Text bindings re-evaluate
    // on every append (the ring itself is a non-notifying array).
    function recentText(count) {
        void root.revision;
        return root.recent(count).join("\n");
    }

    function _append(level, domain, message) {
        const now = new Date();
        const stamp = String(now.getHours()).padStart(2, "0") + ":" + String(now.getMinutes()).padStart(2, "0")
              + ":" + String(now.getSeconds()).padStart(2, "0");
        const line = stamp + " [" + level + "] " + domain + ": " + String(message === undefined ? "" :
                                                                                                  message);
        root._ring.push(line);
        if (root._ring.length > root.ringCapacity)
            root._ring.splice(0, root._ring.length - root.ringCapacity);
        root.revision += 1;
        if (level === "WARN")
            console.warn(line);
        else if (level === "ERROR")
            console.error(line);
        else
            console.info(line);
        root._dirty = true;
        flushTimer.restart();
    }

    function _settlePreviousSession() {
        if (!root._firstFlush)
            return;
        root._firstFlush = false;
        rotatePrevious.running = true;
    }

    // Runs at construction, long before the first debounced flush.
    Process {
        id: ensureDir

        command: ["mkdir", "-p", root.logDir]
        running: true
    }

    Process {
        id: rotatePrevious

        command: ["mv", "-f", root.logPath, root.prevLogPath]
        onExited: root._write()
    }

    Timer {
        id: flushTimer

        interval: 2000
        repeat: false
        onTriggered: {
            if (!root._dirty)
                return;
            root._dirty = false;
            // The previous session's log must be rotated out BEFORE the
            // first write of this one, or the mv races the fresh file.
            if (root._firstFlush)
                rotatePrevious.running = true;
            else
                root._write();
        }
    }

    function _write() {
        logFile.setText(root.text() + "\n");
    }

    FileView {
        id: logFile

        path: root.logPath
        atomicWrites: true
        blockWrites: true
        printErrors: false
        onSaveFailed: error => console.warn("[LogService] log write failed:", error)
    }

    Component.onDestruction: {
        flushTimer.stop();
        if (root._dirty)
            root._write();
    }
}

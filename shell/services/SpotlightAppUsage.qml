pragma Singleton

import QtQuick
import qs.services
import Quickshell
import Quickshell.Io
import qs.commons
import "../commons/SpotlightAppOrder.js" as AppOrder

Singleton {
    id: root

    readonly property string filePath: Paths.stateHome + "/spotlight-app-usage.json"
    property var records: ({})
    property var pending: ({})
    property bool ready: false
    // Reads start immediately: a missing state dir simply reads as "no history".
    // The directory is created lazily, only when the first save needs it.
    property bool storeReady: true
    property bool writable: false
    property bool dirReady: false
    property bool savePending: false

    function finishLoad(history, canWrite) {
        if (ready)
            return;
        writable = canWrite;
        records = AppOrder.mergePending(history, pending);
        const hadPending = Object.keys(pending).length > 0;
        pending = ({});
        ready = true;
        if (hadPending)
            save();
    }

    function launch(id) {
        const app = ApplicationService.findById(id);
        if (!app || !ApplicationService.launchApplication(app))
            return false;
        recordLaunch(String(app.id));
        return true;
    }

    function recordLaunch(id) {
        if (typeof id !== "string" || id.trim() === "")
            return;
        const now = Date.now();
        if (!ready) {
            pending = AppOrder.addLaunch(pending, id, now);
            return;
        }
        records = AppOrder.addLaunch(records, id, now);
        save();
    }

    function save() {
        if (!ready || !writable)
            return;
        if (!dirReady) {
            // First write: create the state dir once, then write on exit.
            savePending = true;
            if (!ensureStateDir.running)
                ensureStateDir.running = true;
            return;
        }
        usageFile.setText(JSON.stringify({
                                             schemaVersion: 1,
                                             applications: records
                                         }, null, 2));
    }

    Process {
        id: ensureStateDir
        command: ["mkdir", "-p", Paths.stateHome]
        onExited: exitCode => {
            if (exitCode !== 0) {
                console.warn("SpotlightAppUsage: state directory unavailable; using session history");
                root.writable = false;
                root.savePending = false;
                return;
            }
            root.dirReady = true;
            if (root.savePending) {
                root.savePending = false;
                root.save();
            }
        }
    }

    FileView {
        id: usageFile
        path: root.storeReady ? root.filePath : ""
        atomicWrites: true
        watchChanges: false
        onLoaded: {
            if (root.ready)
                return;
            const history = AppOrder.decodeHistory(usageFile.text());
            if (history === null)
                console.warn("SpotlightAppUsage: invalid history; preserving file and using session history");
            root.finishLoad(history || {}, history !== null);
        }
        onLoadFailed: error => {
            if (!root.storeReady || root.ready)
                return;
            const missing = error === FileViewError.FileNotFound;
            if (!missing)
                console.warn("SpotlightAppUsage: cannot read history:", error);
            root.finishLoad({}, missing);
        }
        onSaveFailed: error => console.warn("SpotlightAppUsage: cannot save history:", error)
    }

    Component.onDestruction: {
        if (ensureStateDir)
            ensureStateDir.running = false;
    }
}

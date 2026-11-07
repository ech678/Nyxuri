pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property string stageInit: "INIT"
    readonly property string stageFirstFrame: "FIRST_FRAME"
    readonly property string stageReady: "READY"
    readonly property string stageIpcReady: "IPC_READY"
    readonly property string stageFailed: "FAILED"

    property string currentStage: stageInit
    property double initTimestampMs: Date.now()
    property double firstFrameTimestampMs: 0
    property double readyTimestampMs: 0
    property double ipcReadyTimestampMs: 0
    property string failureReason: ""

    // Background startup work is deliberately serialized.  A singleton's
    // Component.onCompleted may run while the shell is assembling, so work
    // that is not needed for the first frame is queued here and receives one
    // event-loop turn at a time.  The queue is also the cancellation boundary
    // used during teardown or a failed startup.
    property var _backgroundQueue: []
    property bool backgroundRunning: false
    property var backgroundMetrics: []
    property bool _backgroundPumpScheduled: false
    property bool _destroyed: false

    // Live QML census.  The host registers one record per Loader/delegate;
    // records are removed when the delegate is destroyed so the snapshot
    // reflects the current object tree rather than a startup estimate.
    property var _qmlLoaderRecords: ({})
    property var _qmlResourceRecords: []

    function _loaderKey(unitId, kind) {
        return String(unitId || "") + "::" + String(kind || "");
    }

    function registerQmlLoader(unitId, kind, loader) {
        if (!loader)
            return;
        const next = Object.assign({}, root._qmlLoaderRecords);
        next[root._loaderKey(unitId, kind)] = {
            "unit": String(unitId || ""),
            "kind": String(kind || ""),
            "active": !!loader.active,
            "loaded": !!loader.item,
            "status": String(loader.statusName || "unknown")
        };
        root._qmlLoaderRecords = next;
    }

    function updateQmlLoader(unitId, kind, loader) {
        if (!loader)
            return;
        const key = root._loaderKey(unitId, kind);
        if (root._qmlLoaderRecords[key] === undefined) {
            root.registerQmlLoader(unitId, kind, loader);
            return;
        }
        const next = Object.assign({}, root._qmlLoaderRecords);
        next[key] = {
            "unit": String(unitId || ""),
            "kind": String(kind || ""),
            "active": !!loader.active,
            "loaded": !!loader.item,
            "status": String(loader.statusName || "unknown")
        };
        root._qmlLoaderRecords = next;
    }

    function unregisterQmlLoader(unitId, kind) {
        const key = root._loaderKey(unitId, kind);
        if (root._qmlLoaderRecords[key] === undefined)
            return;
        const next = Object.assign({}, root._qmlLoaderRecords);
        delete next[key];
        root._qmlLoaderRecords = next;
    }

    // Resource records hold the QObject reference so a service can unregister
    // exactly the instance it registered. This avoids static estimates while
    // keeping the census safe for singleton teardown.
    function registerQmlResource(owner, kind, object) {
        if (!object)
            return;
        const next = root._qmlResourceRecords.filter(record => record.object !== object);
        next.push({"owner": String(owner || "unknown"), "kind": String(kind || "unknown"), "object": object});
        root._qmlResourceRecords = next;
    }

    function unregisterQmlResource(owner, kind, object) {
        root._qmlResourceRecords = root._qmlResourceRecords.filter(record => {
            return record.object !== object || record.owner !== String(owner || "unknown")
                    || record.kind !== String(kind || "unknown");
        });
    }

    function unregisterQmlResources(owner, entries) {
        const name = String(owner || "unknown");
        const objects = (entries || []).map(entry => entry.object);
        root._qmlResourceRecords = root._qmlResourceRecords.filter(record => {
            return record.owner !== name || objects.indexOf(record.object) < 0;
        });
    }

    function qmlCensus(): var {
        const records = Object.keys(root._qmlLoaderRecords).map(key => root._qmlLoaderRecords[key]);
        const active = records.filter(record => record.active);
        const loaded = records.filter(record => record.loaded);
        const loading = records.filter(record => record.status === "loading");
        const errors = records.filter(record => record.status === "error");
        const units = {};
        const loadedUnits = {};
        records.forEach(record => units[record.unit] = true);
        loaded.forEach(record => loadedUnits[record.unit] = true);
        const unitIds = Object.keys(units).sort();
        const loadedUnitIds = Object.keys(loadedUnits).sort();
        const resourceCounts = {};
        const resourceOwners = {};
        root._qmlResourceRecords.forEach(record => {
            resourceCounts[record.kind] = (resourceCounts[record.kind] || 0) + 1;
            const owner = String(record.owner || "unknown");
            if (!resourceOwners[owner])
                resourceOwners[owner] = {};
            resourceOwners[owner][record.kind] = (resourceOwners[owner][record.kind] || 0) + 1;
        });
        const counts = {
            "loaders": records.length,
            "timers": resourceCounts.timer || 0,
            "processes": resourceCounts.process || 0,
            "fileviews": resourceCounts.fileview || 0,
            "connections": resourceCounts.connections || 0,
            "delegates": loaded.length,
            "canvas": null,
            "layers": null,
            "windows": resourceCounts.window || 0
        };
        return {
            "schema": 1,
            "status": "partial",
            "reason": "SlotHost and explicitly registered service resources are live; Canvas/layer remain unsupported",
            "loaders": {
                "declared": records.length,
                "active": active.length,
                "loaded": loaded.length,
                "loading": loading.length,
                "errors": errors.length
            },
            "units": {
                "declared": unitIds.length,
                "active": active.map(record => record.unit)
                    .filter((value, index, values) => values.indexOf(value) === index).sort().length,
                "loaded": loadedUnitIds.length,
                "ids": unitIds,
                "loaded_ids": loadedUnitIds
            },
            "resources": counts,
            "resource_owners": resourceOwners,
            "qml_resources": {
                "status": "partial",
                "reason": "loaders plus explicitly registered service resources; Canvas/layer remain unsupported",
                "counts": counts,
                "owners": resourceOwners
            }
        };
    }

    signal stageChanged(string stage)

    function scheduleBackground(name, callback): void {
        const taskName = String(name || "background");
        if (typeof callback !== "function")
            return;
        const queue = root._backgroundQueue.slice();
        queue.push({"name": taskName, "callback": callback});
        root._backgroundQueue = queue;
        if (root.backgroundRunning)
            return;
        root.backgroundRunning = true;
        root._scheduleBackgroundPump();
    }

    function cancelBackground(): void {
        root._backgroundQueue = [];
        root.backgroundRunning = false;
        root._backgroundPumpScheduled = false;
        root._destroyed = true;
    }

    function _scheduleBackgroundPump(): void {
        if (root._destroyed || root._backgroundPumpScheduled)
            return;
        root._backgroundPumpScheduled = true;
        Qt.callLater(() => {
            root._backgroundPumpScheduled = false;
            root._runBackgroundTask();
        });
    }

    function _runBackgroundTask(): void {
        if (root._destroyed)
            return;
        if (root._backgroundQueue.length === 0) {
            root.backgroundRunning = false;
            return;
        }

        const queue = root._backgroundQueue.slice();
        const task = queue.shift();
        root._backgroundQueue = queue;
        const started = Date.now();
        let error = "";
        try {
            task.callback();
        } catch (exception) {
            error = String(exception);
            console.warn("[ShellStartup] background task failed", task.name, error);
        }
        const metrics = root.backgroundMetrics.slice();
        metrics.push({
                           "name": task.name,
                           "elapsed_ms": Date.now() - started,
                           "error": error
                       });
        root.backgroundMetrics = metrics;
        root._scheduleBackgroundPump();
    }

    function recordFirstFrame(): void {
        if (root.firstFrameTimestampMs === 0) {
            root.firstFrameTimestampMs = Date.now();
            root.setStage(stageFirstFrame);
        }
    }

    function recordCoreReady(): void {
        if (root.readyTimestampMs === 0) {
            root.readyTimestampMs = Date.now();
            root.setStage(stageReady);
        }
    }

    function recordIpcReady(): void {
        if (root.ipcReadyTimestampMs === 0) {
            root.ipcReadyTimestampMs = Date.now();
            root.setStage(stageIpcReady);
        }
    }

    function recordFailure(reason: string): void {
        root.failureReason = reason || "unknown";
        root.setStage(stageFailed);
    }

    function setStage(stage: string): void {
        if (root.currentStage !== stage) {
            root.currentStage = stage;
            console.log("[ShellStartup] Stage transition ->", stage, "(elapsed:", (Date.now() - root.initTimestampMs) + "ms)");
            root.stageChanged(stage);
        }
    }

    function startupMetrics(): var {
        const census = root.qmlCensus();
        return {
            "stage": root.currentStage,
            "elapsed_ms": Date.now() - root.initTimestampMs,
            "first_frame_ms": root.firstFrameTimestampMs > 0 ? (root.firstFrameTimestampMs - root.initTimestampMs) : -1,
            "ready_ms": root.readyTimestampMs > 0 ? (root.readyTimestampMs - root.initTimestampMs) : -1,
            "ipc_ready_ms": root.ipcReadyTimestampMs > 0 ? (root.ipcReadyTimestampMs - root.initTimestampMs) : -1,
            "failure_reason": root.failureReason,
            "background_running": root.backgroundRunning,
            "background_queue": root._backgroundQueue.length,
            "background_tasks": root.backgroundMetrics,
            "qml_census": census,
            "qml_resources": census.qml_resources
        };
    }

    Component.onDestruction: root.cancelBackground()
}

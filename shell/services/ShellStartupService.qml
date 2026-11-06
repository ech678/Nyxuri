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
        return {
            "stage": root.currentStage,
            "elapsed_ms": Date.now() - root.initTimestampMs,
            "first_frame_ms": root.firstFrameTimestampMs > 0 ? (root.firstFrameTimestampMs - root.initTimestampMs) : -1,
            "ready_ms": root.readyTimestampMs > 0 ? (root.readyTimestampMs - root.initTimestampMs) : -1,
            "ipc_ready_ms": root.ipcReadyTimestampMs > 0 ? (root.ipcReadyTimestampMs - root.initTimestampMs) : -1,
            "failure_reason": root.failureReason,
            "background_running": root.backgroundRunning,
            "background_queue": root._backgroundQueue.length,
            "background_tasks": root.backgroundMetrics
        };
    }

    Component.onDestruction: root.cancelBackground()
}

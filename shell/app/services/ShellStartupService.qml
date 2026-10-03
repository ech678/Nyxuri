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

    signal stageChanged(string stage)

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
            "failure_reason": root.failureReason
        };
    }
}

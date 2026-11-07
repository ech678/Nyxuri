pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.services

// UnitControl — the only route settings surfaces may take to flip a Shell
// unit: dispatch `nyxuri on/off <unitId>` (the full ledger key: "shell.<domain>"
// first-party, the reverse-DNS id third-party) and let the kernel
// transaction land the ledger record (unit-model.md §6 single switch
// truth). The UI never flips optimistically; switches re-project when the
// kernel's unit-changed event arrives via StateProjection.
Singleton {
    id: root

    readonly property bool busy: proc.running
    property string lastError: ""
    property string pendingUnitId: ""
    property bool _pendingEnable: false

    // A held session lock refuses to be turned off (shell AGENTS: 锁屏中
    // 禁止停用 lock); the switch disables itself instead. `unitId` is the
    // full ledger key ("shell.<domain>" first-party, reverse-DNS third-party).
    function canToggle(unitId) {
        return !(unitId === "shell.lock" && ActionGateway.lockEngaged);
    }

    function setUnit(unitId, enable) {
        if (root.busy || !root.canToggle(unitId))
            return false;
        root.lastError = "";
        root.pendingUnitId = unitId;
        root._pendingEnable = enable;
        // Parameter array, never a shell string (LIFE004).
        proc.command = [Paths.binHome + "/nyxuri", enable ? "on" : "off", unitId];
        proc.running = true;
        watchdog.restart();
        LogService.info("units", "dispatch: nyxuri " + (enable ? "on" : "off") + " " + unitId);
        return true;
    }

    function _finish(code) {
        watchdog.stop();
        if (code !== 0) {
            root.lastError = "nyxuri " + (root._pendingEnable ? "on" : "off") + " " + root.pendingUnitId
                    + " failed (exit " + code + ")";
            LogService.error("units", root.lastError);
        } else {
            LogService.info("units", "unit switch done: " + root.pendingUnitId);
        }
        root.pendingUnitId = "";
    }

    Process {
        id: proc

        stdout: StdioCollector {}
        stderr: StdioCollector {}
        onExited: (code, status) => root._finish(code)
    }

    // Bounded: a hung CLI must not pin the busy state forever.
    Timer {
        id: watchdog

        interval: 15000
        onTriggered: {
            if (!proc.running)
                return;
            proc.running = false;
            root.lastError = "nyxuri unit switch timed out";
            root.pendingUnitId = "";
        }
    }

    Component.onDestruction: {
        watchdog.stop();
        proc.running = false;
    }
}

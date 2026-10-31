pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.app

// StateProjection — the running shell is a read-only projection of the unit
// ledger (unit-model.md §6). state.json is the single switch truth; the
// shell never writes it. Units flip only through kernel transactions
// (`nyxuri on/off shell.<domain>`), and this projection re-reads the ledger
// when the kernel fires its ONE unit-changed event, delivered over the
// existing Quickshell IPC channel (`ipc call unit reload`).
//
// No ledger record means enabled: the default desktop is fully alive until
// an explicit `off` lands a record.
Singleton {
    id: root

    readonly property string ledgerPath: Paths.stateHome + "/state.json"

    // A ledger that exists but cannot be parsed is degraded: every unit
    // stays enabled and the control plane surfaces the failure. Blanking
    // the desktop over a corrupt file would be the wrong failure mode.
    property bool degraded: false

    property var _units: ({})

    function isEnabled(id) {
        const record = root._units["shell." + id];
        if (!record)
            return true;
        return record.state === "enabled";
    }

    function reload() {
        configFile.reload();
    }

    function _absorb(text) {
        root.degraded = false;
        try {
            const parsed = JSON.parse(String(text || "").trim() || "{}");
            root._units = parsed.units && typeof parsed.units === "object" ? parsed.units : {};
        } catch (error) {
            root.degraded = true;
            console.warn("[StateProjection] ledger unreadable; projecting every unit as enabled:", error);
        }
    }

    FileView {
        id: configFile

        path: root.ledgerPath
        blockLoading: true
        // watchChanges stays off on purpose: the unit-changed IPC event is
        // the single notification channel (bridge: nyxuri/desktop/bridge.py).
        watchChanges: false
        onLoaded: root._absorb(configFile.text())
        onLoadFailed: error => {
            if (error === FileViewError.FileNotFound) {
                // Fresh machine, no records yet — the all-enabled default.
                root._absorb("");
                return;
            }
            root.degraded = true;
            console.warn("[StateProjection] ledger could not be read:", error);
        }
    }

    Component.onCompleted: root.reload()
}

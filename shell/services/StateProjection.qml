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

    // True once the first absorb landed (records, not-found or degraded).
    // SlotHost gates assembly on this: a disabled unit must never
    // flash-mount in the window before the ledger read completes
    // (冷启动未启用域零实例化, shell AGENTS).
    property bool primed: false

    property var _units: ({})

    // Full-ledger-key lookup: first-party units key as "shell.<domain>",
    // third-party plugins key as their reverse-DNS id (S1-3).
    function isEnabledUnit(unitId) {
        const record = root._units[unitId];
        if (!record)
            return true;
        return record.state === "enabled";
    }

    function isEnabled(id) {
        return root.isEnabledUnit("shell." + id);
    }

    function reload() {
        configFile.reload();
    }

    function _absorb(text) {
        root.degraded = false;
        try {
            const parsed = JSON.parse(String(text || "").trim() || "{}");
            // The ledger's top-level key is `plugins` (R0-1: units.* retired).
            // Reading the retired key silently blanked the projection — every
            // unit projected as enabled no matter what the ledger said (found
            // by the S1-3 third-party probe).
            root._units = parsed.plugins && typeof parsed.plugins === "object" ? parsed.plugins : {};
        } catch (error) {
            root.degraded = true;
            console.warn("[StateProjection] ledger unreadable; projecting every unit as enabled:", error);
        }
        root.primed = true;
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

    Component.onCompleted: {
        ShellStartupService.registerQmlResource("StateProjection", "fileview", configFile);
        root.reload();
    }

    Component.onDestruction: {
        ShellStartupService.unregisterQmlResource("StateProjection", "fileview", configFile);
    }
}

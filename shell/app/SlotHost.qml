import QtQuick
import qs.app
import qs.services

// SlotHost — the microkernel's geometric slot host (plugin-model.md §6).
//
// Data-driven off the PluginRegistry: every mount row (one per declared ui
// kind) loads through exactly one Loader keyed by StateProjection; no unit is
// ever instantiated here by name. Entry points load as absolute file:// URLs
// (loader-form.md): relative Loader sources fall into the Quickshell 0.3.2
// qs: interception defect and die compiled empty. A disabled unit keeps
// Loader.active false — zero file reads, zero instantiation, zero retained
// memory; re-enabling rebuilds the domain fresh.
//
// Slot arbitration (host-owned; the only place units may conflict):
// - lock: a held session lock is never torn down mid-lock. An `off` that
//   arrives while locked keeps the unit loaded until the lock releases
//   (shell AGENTS: 锁屏中禁止销毁安全锁).
// - notifications: the popup:notification slot belongs to the keystone
//   island whenever keystone is enabled; the standalone popup host loads
//   only when keystone is off.
Item {
    id: root

    // Cross-unit dependency bridge point (four-layer rule: 跨模块协调由 app
    // 的窄接口完成). Emitted whenever a unit's root item comes alive.
    signal unitLoaded(string unitId, var item)

    function slotActive(unit) {
        if (!StateProjection.isEnabledUnit(unit.unitId)) {
            return unit.id === "lock" && ActionGateway.lockEngaged;
        }
        // Slot contract: keystone owns popup:notification while enabled.
        // The rule is kind-keyed, so a third-party popup host yields exactly
        // like the first-party one (S1-3 seating rule).
        if (unit.kind === "popup:notification" && StateProjection.isEnabled("keystone"))
            return false;
        return true;
    }

    Repeater {
        id: slotRepeater

        model: PluginRegistry.units

        delegate: Loader {
            id: delegate

            required property var modelData
            // Self-heal gate (Quickshell 0.3.2): a unit can fail its cold
            // compile and come up as a silent null item. The host retries
            // such units at most twice, then gives up until the ledger flips
            // the unit (unit-changed resets the counter and re-arms the heal
            // timer).
            property bool suppressed: false
            property int failedHeals: 0

            active: StateProjection.primed && root.slotActive(modelData) && !suppressed
            source: modelData.entryUrl
            onLoaded: {
                failedHeals = 0;
                root.unitLoaded(modelData.id, item);
            }
        }
    }

    // Compile-failure self-heal: "the ledger says loaded but the item is
    // null" means the unit's QML died in compilation. Two bounded retry
    // passes (fresh compile, cache already cleared at launch); after the
    // second failure the unit stays dark — an unbounded retry would spam
    // the log every 4s forever. Every retry and the final give-up are logged
    // loudly — silent missing UI is the failure mode that ate a debugging
    // afternoon. A later unit-changed (off → on) resets failedHeals and
    // re-arms the heal timer.
    readonly property int healPassLimit: 2
    property int _healPasses: 0

    function noteUnitChanged() {
        _healPasses = 0;
        for (let i = 0; i < PluginRegistry.units.length; i++) {
            const loader = slotRepeater.itemAt(i);
            if (loader)
                loader.failedHeals = 0;
        }
        healTimer.restart();
    }

    Timer {
        id: healTimer

        interval: 4000
        repeat: true
        running: true

        onTriggered: {
            root._healPasses += 1;
            let retried = 0;
            for (let i = 0; i < PluginRegistry.units.length; i++) {
                const unit = PluginRegistry.units[i];
                const loader = slotRepeater.itemAt(i);
                if (!loader || loader.suppressed)
                    continue;
                if (!root.slotActive(unit) || loader.item !== null)
                    continue;
                if (loader.failedHeals >= root.healPassLimit)
                    continue; // given up — stays dark until unit-changed
                loader.failedHeals += 1;
                retried += 1;
                if (loader.failedHeals >= root.healPassLimit)
                    LogService.error("host", "unit " + unit.unitId + " still compiled empty after "
                                     + root.healPassLimit
                                     + " heal passes — giving up; toggle the unit to retry");
                else
                    LogService.error("host", "unit " + unit.unitId
                                     + " enabled but compiled empty — reloading (pass " + loader.failedHeals
                                     + "/" + root.healPassLimit + ")");
                loader.suppressed = true;
            }
            if (retried > 0) {
                releaseSuppressed.restart();
            } else {
                stop();
            }
        }
    }

    Timer {
        id: releaseSuppressed

        interval: 250
        repeat: false
        onTriggered: {
            for (let i = 0; i < PluginRegistry.units.length; i++) {
                const loader = slotRepeater.itemAt(i);
                if (loader)
                    loader.suppressed = false;
            }
        }
    }

    Component.onDestruction: {
        healTimer.stop();
        releaseSuppressed.stop();
    }
}

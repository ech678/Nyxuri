import QtQuick
import qs.app
import qs.services
// Unit module warm-up (see note below): registers every synthesized
// qs.plugins.* import graph at engine startup, before any Loader fires.
// qs.commons.cards joins the warm-up for the same reason — it is a synthesized
// pool consumed by unit components (desktopcards); a pool that nothing at
// the top level imports would otherwise get its FIRST resolution inside a
// Loader-loaded component, which is exactly the 0.3.2 defect documented
// below (KM4.6 实机验收案例：shell.desktopcards 永久 compiled empty).
// qs.ui (T3 preference atoms) joins for the same
// reason: consumed only by settings pages inside the unit's Loader tree.
import qs.commons.cards
import qs.plugins.bar
import qs.plugins.desktopcards
import qs.plugins.dock
import qs.plugins.keystone
import qs.plugins.launcher
import qs.plugins.lock
import qs.plugins.notifications
import qs.plugins.regionselector
import qs.plugins.session
import qs.plugins.settings
import qs.ui
import qs.plugins.sidebars
import qs.plugins.wallpaper

// SlotHost — the microkernel's geometric slot host (unit-model.md §6).
//
// WHY THE STATIC IMPORTS: Quickshell 0.3.2's qs-import resolution is
// unreliable for imports processed inside Loader-loaded components at cold
// start — losers report nondeterministic "module not installed" /
// "X is not a type" and their whole unit dies (run-to-run shifting failure
// sets, cache-clearing does not help). Registering the module graphs
// statically here restores the deterministic import order the pre-KM4
// static AppShell had, while instantiation stays purely Loader-driven:
// these imports never create a unit component. Disabled units still get
// Loader.active = false — zero instantiation, zero windows, zero retained
// memory; the parse-only cost of warm registration is a documented 0.3.2
// constraint, revisited on quickshell upgrade.
// Data-driven: every Shell unit loads through exactly one Loader keyed by
// StateProjection; no unit is ever instantiated here by name. A disabled
// unit keeps Loader.active false — zero file reads, zero instantiation,
// zero retained memory; re-enabling rebuilds the domain fresh.
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
        if (!StateProjection.isEnabled(unit.id)) {
            return unit.id === "lock" && ActionGateway.lockEngaged;
        }
        if (unit.id === "notifications" && StateProjection.isEnabled("keystone"))
            return false;
        return true;
    }

    Repeater {
        id: slotRepeater

        model: UnitCatalog.units

        delegate: Loader {
            id: delegate

            required property var modelData
            // Self-heal gate (Quickshell 0.3.2): a unit can fail its cold
            // compile nondeterministically and come up as a silent null
            // item. The host retries such units at most twice, then gives
            // up until the ledger flips the unit (unit-changed resets the
            // counter and re-arms the heal timer).
            property bool suppressed: false
            property int failedHeals: 0

            active: root.slotActive(modelData) && !suppressed
            source: modelData.source
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
    // the log every 4s forever (KM4.6 实机验收案例：desktopcards 因未预热
    // 的 qs.commons.cards 池永久 compiled empty，pass 计数刷到 11/2). Every
    // retry and the final give-up are logged loudly — silent missing UI is
    // the failure mode that ate a debugging afternoon. A later unit-changed
    // (off → on) resets failedHeals and re-arms the heal timer.
    readonly property int healPassLimit: 2
    property int _healPasses: 0

    function noteUnitChanged() {
        _healPasses = 0;
        for (let i = 0; i < UnitCatalog.units.length; i++) {
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
            for (let i = 0; i < UnitCatalog.units.length; i++) {
                const unit = UnitCatalog.units[i];
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
                    LogService.error("host", "unit shell." + unit.id + " still compiled empty after "
                                     + root.healPassLimit
                                     + " heal passes — giving up; toggle the unit to retry");
                else
                    LogService.error("host", "unit shell." + unit.id
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
            for (let i = 0; i < UnitCatalog.units.length; i++) {
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

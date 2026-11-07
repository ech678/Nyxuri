//@ pragma UseQApplication
//@ pragma Env QT_QUICK_FLICKABLE_WHEEL_DECELERATION=10000
//@ pragma Env QT_WAYLAND_DISABLE_WINDOWDECORATION=1

// Pragmas must stay contiguous at the top of the file: a plain comment between
// two //@ lines ends the block and silently drops the rest. The wheel pragma
// matches end4-pC's feel; the dashboard's long lists and wallpaper grid crawl at
// Qt's default deceleration.

import QtQuick
import Quickshell
import Quickshell.Io

// Shared layers, imported here on purpose (loader-form.md rule 3): the
// startup scan closure synthesises a qmldir per imported directory, and this
// top-level import list is the guarantee that the pools dynamically loaded
// plugins import (qs.commons / qs.commons.cards / qs.commons.i18n / qs.ui /
// qs.services) exist before the first plugin resolves one.
import qs.commons
import qs.commons.cards
import qs.commons.i18n
import qs.services
import qs.ui

import "plugins/settings"
import "plugins/sidebars/dashboard/infotools"
import "plugins/wallpaper"

// ShellRoot — the Omarchy microkernel host skeleton (P0 / lain-connect).
// It owns assembly (slot Repeater), host-level intent sources (corner gestures),
// generic IPC surfaces (unit / shell / theme / shortcut-map / wallpaper) and
// lifecycle guards. Zero unit components are instantiated here by name: every
// unit loads through data-driven Loaders keyed by StateProjection.
ShellRoot {
    id: shellRoot

    Item {
        id: root

        // Search-catalog executor: the host bridges module-level capabilities
        // the singletons must not import; gateway-owned intents delegate
        // to ActionGateway.executeIntent (unit-model.md §6).
        function executeSearchAction(action) {
            switch (action.target) {
            case "wallpaper":
                return WallpaperService.runCatalogAction(action.method);
            case "shortcut-map":
                ShortcutMapService.open();
                return true;
            default:
                return ActionGateway.executeIntent(action);
            }
        }

        Component.onCompleted: {
            SpotlightCatalog.actionExecutor = root.executeSearchAction;
            SpotlightCatalog.keystoneAvailable = Qt.binding(() => ActionGateway.keystoneHost
                                                                  ? ActionGateway.keystoneHost.searchActionsAvailable :
                                                                    false);
            ThemeService.reloadColors();
            FontService.refresh();
            I18nService.initialize();
            SystemIdentityService.initialize();
            ShellStartupService.recordCoreReady();
            Qt.callLater(() => {
                ShellStartupService.recordFirstFrame();
                ShellStartupService.recordIpcReady();
            });
        }

        Component.onDestruction: {
            healTimer.stop();
            releaseSuppressed.stop();
        }

        // ------------------------------------------------------------- Slot assembly
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
                    if (item) {
                        if (modelData.id === "settings")
                            item.todoService = TodoService;
                        if (modelData.id === "sidebars")
                            ActionGateway.sidebarHost = item;
                    }
                }
            }
        }

        // Compile-failure self-heal: "the ledger says loaded but the item is
        // null" means the unit's QML died in compilation. Two bounded retry
        // passes (fresh compile, cache already cleared at launch); after the
        // second failure the unit stays dark — an unbounded retry would spam
        // the log every 4s forever. Every retry and the final give-up are logged
        // loudly. A later unit-changed (off → on) resets failedHeals and
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

        // Host-level intent source (corner gestures translate to gateway intents)
        HotCorners {
            locked: ActionGateway.lockEngaged
            onTriggered: (action, screenName) => {
                if (action === "overview") {
                    WidgetState.closeAllPopups();
                    CompositorDriver.toggleOverview();
                    return;
                }
                const target = action.split(":");
                if (target.length === 2) {
                    if (CompositorDriver.inOverview)
                        CompositorDriver.toggleOverview();
                    ActionGateway.requestSidebarOpenOnScreen(target[0], target[1], screenName);
                }
            }
        }

        // Freeze file watching for the duration of the lock
        Binding {
            target: Quickshell
            property: "watchFiles"
            value: !ActionGateway.lockEngaged
        }

        // Idle daemon requests degrade honestly when their owning unit is off:
        // no lock unit → the lock request reports failure (the idle banner
        // surfaces it); suspend runs directly (no lock handshake is needed).
        Connections {
            target: IdleService
            function onLockRequested() {
                IdleService.reportLockResult(ActionGateway.sessionLocker ? ActionGateway.sessionLocker.open() :
                                                                           "shell.lock is off");
            }
            function onSuspendRequested() {
                IdleService.reportSuspendResult(ActionGateway.powerAction("suspend", "idle"));
            }
        }

        Loader {
            active: ShortcutMapService.visible
            source: Qt.resolvedUrl("plugins/settings/ShortcutMap.qml")
            onLoaded: {
                if (item) {
                    item.targetScreen = ShortcutMapService.targetScreen;
                    if (item.dismissed)
                        item.dismissed.connect(ShortcutMapService.close);
                }
            }
        }

        // The kernel's unit-changed event lands here (nyxuri/desktop/bridge.py
        // delivers `qs ipc call unit reload`): re-read the ledger, re-project.
        IpcHandler {
            target: "unit"

            function reload(): string {
                StateProjection.reload();
                TemplateService.refresh();
                root.noteUnitChanged();
                return StateProjection.degraded ? "DEGRADED" : "OK";
            }
        }

        IpcHandler {
            target: "shortcut-map"

            function open(): void {
                ShortcutMapService.open();
            }

            function close(): void {
                ShortcutMapService.close();
            }

            function toggle(): void {
                ShortcutMapService.toggle();
            }
        }

        IpcHandler {
            target: "theme"

            function set(mode: string): string {
                if (mode !== "dark" && mode !== "light")
                    return "INVALID_MODE";
                ThemeService.setThemeMode(mode);
                return "OK";
            }

            function toggle(): string {
                ThemeService.toggleThemeMode();
                return "OK";
            }

            function status(): string {
                return PersonalizationConfig.themeMode;
            }
        }

        IpcHandler {
            target: "shell"

            function status(): string {
                return JSON.stringify(ShellStartupService.startupMetrics());
            }

            function stage(): string {
                return ShellStartupService.currentStage;
            }

            function isReady(): bool {
                return ShellStartupService.currentStage === ShellStartupService.stageIpcReady
                        || ShellStartupService.currentStage === ShellStartupService.stageReady;
            }

            function metrics(): string {
                return JSON.stringify(ShellStartupService.startupMetrics());
            }

            // Sanitized diagnostics (no env, no config contents, home paths masked)
            function diagnostics(): string {
                return ShellControlService.diagnosticsJson();
            }

            // Structured session log (LogService ring)
            function log(): string {
                return LogService.text();
            }
        }

        // Wallpaper capability IPC stays host-level on purpose: the unit switch
        // owns the wallpaper visual, while set/random/cycle remain meaningful
        // against the wallpaper state (and the theme pipeline reads it).
        IpcHandler {
            target: "wallpaper"

            function set(path: string): string {
                return WallpaperService.setWallpaper(path || "", "") ? "OK" : "INVALID";
            }

            function setForScreen(path: string, screenName: string): string {
                return WallpaperService.setWallpaper(path || "", screenName || "") ? "OK" : "INVALID";
            }

            function clear(): string {
                return WallpaperService.clearWallpaper("") ? "OK" : "INVALID";
            }

            function clearForScreen(screenName: string): string {
                return WallpaperService.clearWallpaper(screenName || "") ? "OK" : "INVALID";
            }

            function previous(): string {
                return WallpaperService.cyclePrevious() ? "OK" : "PENDING";
            }

            function next(): string {
                return WallpaperService.cycleNext() ? "OK" : "PENDING";
            }

            function random(): string {
                return WallpaperService.cycleRandom() ? "OK" : "PENDING";
            }

            function setFolder(path: string): string {
                return WallpaperService.setWallpaperFolder(path || "") ? "OK" : "INVALID";
            }
        }
    }
}

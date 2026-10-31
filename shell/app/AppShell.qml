import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import qs.services
import qs.plugins.settings
import qs.plugins.sidebars.dashboard.infotools
import qs.plugins.wallpaper
import qs.commons

// AppShell — the microkernel host (unit-model.md §6). It owns assembly
// (SlotHost), host-level intent sources (corner gestures), the generic IPC
// surface (unit / shell / theme / shortcut-map / wallpaper) and lifecycle
// guards. Zero unit components are instantiated here by name: every unit
// loads through SlotHost's data-driven Loaders keyed by StateProjection,
// the read-only projection of the ledger. Hosts (lock, session, settings,
// launcher, keystone, sidebars) self-register on ActionGateway when they
// load and unregister on destruction.
Item {
    id: root

    // Search-catalog executor: the host bridges module-level capabilities
    // the app singletons must not import; gateway-owned intents delegate
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

    // All twelve Shell units, slot-driven (surface:desktop → overlay).
    SlotHost {
        id: slotHost

        // Cross-unit dependency bridge (four-layer rule): the settings
        // unit's dashboard consumes the todo domain service that lives in
        // the sidebars module; the host wires it explicitly instead of a
        // hidden module-to-module import.
        onUnitLoaded: (unitId, item) => {
            if (unitId === "settings" && item)
                item.todoService = TodoService;
        }
    }

    // Host-level intent source (app layer, not a unit): corner gestures
    // translate to gateway intents exactly like keybinds do.
    HotCorners {
        locked: ActionGateway.lockEngaged
        onTriggered: (action, screenName) => {
            if (action === "overview") {
                WidgetState.closeAllPopups();
                NiriService.toggleOverview();
                return;
            }
            const target = action.split(":");
            if (target.length === 2) {
                if (NiriService.inOverview)
                    NiriService.toggleOverview();
                ActionGateway.requestSidebarOpenOnScreen(target[0], target[1], screenName);
            }
        }
    }

    // Hot reloading rebuilds the object tree, which would destroy the session
    // lock while it is held. Niri treats that as a protocol violation and kills
    // the client, then paints its red CLEAR_COLOR_LOCKED where the lock surface
    // used to be. Freeze file watching for the duration of the lock.
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
        source: Qt.resolvedUrl("../plugins/settings/ShortcutMap.qml")
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
            slotHost.noteUnitChanged();
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

        // R11: sanitized diagnostics (no env, no config contents,
        // home paths masked) — same payload the settings page exports.
        function diagnostics(): string {
            return ShellControlService.diagnosticsJson();
        }

        // Structured session log (LogService ring) — the feedback surface
        // for "why did X not happen": read via qs ipc or the settings page.
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

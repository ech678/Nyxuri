import QtQuick
import Quickshell
import Quickshell.Io
import qs.modules.bar
import qs.modules.launcher
import qs.modules.lock
import qs.app
import qs.modules.session
import qs.modules.settings
import qs.modules.keystone
import qs.modules.wallpaper
import qs.modules.desktopcards
import qs.modules.dock
import qs.modules.regionselector
import qs.modules.hotcorners
import qs.modules.sidebars
import qs.modules.sidebars.dashboard.infotools
import qs.shared.theme
import qs.app.services

Item {
    id: root

    // The catalog only supplies fixed, build-validated calls. Both IPC and
    // Search use the same existing business functions, without self-IPC.
    function executeSearchAction(action) {
        switch (action.target) {
        case "lock":
            return ActionGateway.powerAction("lock", "launcher:search");
        case "wallpaper":
            switch (action.method) {
            case "clear":
                return WallpaperService.clearWallpaper("");
            case "previous":
                return WallpaperService.cyclePrevious() || WallpaperService.pendingCycleAction === "previous";
            case "next":
                return WallpaperService.cycleNext() || WallpaperService.pendingCycleAction === "next";
            case "random":
                return WallpaperService.cycleRandom() || WallpaperService.pendingCycleAction === "random";
            }
            return false;
        case "keystone":
            return keystone ? (keystone.invoke(action.method) !== "KEYSTONE_UNAVAILABLE") : false;
        case "sidebar":
            if (sidebarHost) {
                return sidebarHost.toggleSidebar(action.argument || "dashboard") !== "INVALID_SIDE";
            }
            return false;
        case "shortcut-map":
            ShortcutMapService.open();
            return true;
        case "power-menu":
            return ActionGateway.requestSessionOpen();
        default:
            return false;
        }
    }

    Component.onCompleted: {
        ActionGateway.sessionLocker = sessionLocker;
        ActionGateway.settingsHost = settingsHost;
        ActionGateway.sidebarHost = sidebarHost;
        SpotlightCatalog.actionExecutor = root.executeSearchAction;
        SpotlightCatalog.keystoneAvailable = Qt.binding(() => keystone ? keystone.searchActionsAvailable :
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

    Loader {
        active: DisplayConfigService.identify || DisplayConfigService.confirming
        source: Qt.resolvedUrl("../modules/settings/DisplayOverlays.qml")
    }

    WallpaperBackground {}

    Loader {
        active: SystemCardService.desktopCardIds.length > 0
        source: Qt.resolvedUrl("../modules/desktopcards/DesktopCardHost.qml")
    }

    Loader {
        active: PersonalizationConfig.barEnabled
        source: Qt.resolvedUrl("../modules/bar/Bar.qml")
    }

    Loader {
        active: DockService.enabled
        source: Qt.resolvedUrl("../modules/dock/DockHost.qml")
    }

    Keystone {
        id: keystone
    }

    Loader {
        id: notificationFallbackLoader
        active: !PersonalizationConfig.keystoneEnabled
        source: Qt.resolvedUrl("../modules/notifications/NotificationPopupHost.qml")
    }

    RegionSelector {}

    SidebarHostWindow {
        id: sidebarHost
    }

    HotCorners {
        locked: sessionLocker.active
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
                sidebarHost.openOnScreen(target[0], target[1], screenName);
            }
        }
    }

    Lock {
        id: sessionLocker
    }

    SessionHost {
        id: sessionHost
    }

    SettingsHost {
        id: settingsHost
        todoService: TodoService
    }

    Connections {
        target: IdleService
        function onLockRequested() {
            IdleService.reportLockResult(sessionLocker.open());
        }
        function onSuspendRequested() {
            IdleService.reportSuspendResult(ActionGateway.powerAction("suspend", "idle"));
        }
    }

    Loader {
        active: ShortcutMapService.visible
        source: Qt.resolvedUrl("../modules/settings/ShortcutMap.qml")
        onLoaded: {
            if (item) {
                item.targetScreen = ShortcutMapService.targetScreen;
                if (item.dismissed)
                    item.dismissed.connect(ShortcutMapService.close);
            }
        }
    }

    IpcHandler {
        target: "power-menu"

        function open(): void {
        ActionGateway.requestSessionOpen();
    }

        function close(): void {
                              ActionGateway.requestSessionClose();
                          }

        function toggle(): void {
        ActionGateway.requestSessionToggle();
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
                target: "lock"

                function open() {
                    return sessionLocker.open();
                }

                function isLocked() {
                    return sessionLocker.isLocked();
                }
            }

            LauncherHost {
                id: spotlightLauncher
            }

            IpcHandler {
                target: "spotlight"

                function toggle(): string {
                    spotlightLauncher.toggleWindow();
                    return spotlightLauncher.windowPhase.toUpperCase();
                }

                function open(): string {
                    spotlightLauncher.openSpotlight();
                    return spotlightLauncher.windowPhase.toUpperCase();
                }

                function search(): string {
                    spotlightLauncher.openSpotlight("search");
                    return "SEARCH";
                }

                function close(): string {
                    spotlightLauncher.requestClose();
                    return spotlightLauncher.windowPhase.toUpperCase();
                }

                function web(): string {
                    spotlightLauncher.openWebMode();
                    return "WEB";
                }

                function command(name: string): string {
                    return spotlightLauncher.runCommand(name);
                }

                function commands(): string {
                    return openMode("commands");
                }

                function files(): string {
                    return openMode("files");
                }

                function openMode(mode: string): string {
                    if (spotlightLauncher.normalizedMode(mode || "") === "")
                        return "INVALID_MODE";

                    spotlightLauncher.openSpotlight(mode);
                    return String(mode).toUpperCase();
                }
            }

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

            IpcHandler {
                target: "control-center"

                function open(pageId: string): string {
                    return ActionGateway.requestSettingsOpen(pageId || "") ? "OK" : "UNAVAILABLE";
                }

                function close(): string {
                    return ActionGateway.requestSettingsClose() ? "OK" : "CLOSED";
                }

                function toggle(pageId: string): string {
                    return ActionGateway.requestSettingsToggle(pageId || "") ? "OPENING" : "CLOSING";
                }
            }

            IpcHandler {
                target: "settings"

                function open(pageId: string): string {
                    return ActionGateway.requestSettingsOpen(pageId || "") ? "OK" : "UNAVAILABLE";
                }

                function close(): string {
                    return ActionGateway.requestSettingsClose() ? "OK" : "CLOSED";
                }

                function toggle(pageId: string): string {
                    return ActionGateway.requestSettingsToggle(pageId || "") ? "OPENING" : "CLOSING";
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
            }
        }

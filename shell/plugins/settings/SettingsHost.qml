pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Io
import qs.services
import "dashwindow"

Scope {
    id: root

    property bool active: false
    property string pendingPage: ""
    property string pendingSearchId: ""
    property var todoService: null

    // "dashboard" gets end4-pC's card-grid window; every other style keeps the
    // rail + page window. The switch is at window granularity, not a body swap,
    // so each style owns its own chrome and geometry.
    readonly property bool dashboardStyle: PersonalizationConfig.settingsPanelStyle === "dashboard"
    readonly property var activeWindow: root.dashboardStyle ? dashboardLoader.item : controlCenterLoader.item
    property bool _inOpen: false

    function pageKnown(pageId) {
        const wanted = String(pageId || "");
        if (wanted === "")
            return true;
        if (typeof SpotlightCatalog.route === "function" && SpotlightCatalog.route(wanted) !== null)
            return true;
        if (typeof SpotlightCatalog.setting === "function" && SpotlightCatalog.setting(wanted) !== null)
            return true;
        if (root.activeWindow && typeof root.activeWindow.knowsPage === "function")
            return root.activeWindow.knowsPage(wanted);
        return typeof SpotlightCatalog.route !== "function";
    }

    function open(pageId) {
        if (root._inOpen)
            return false;
        root._inOpen = true;
        try {
            if (root.active && root.activeWindow) {
                const result = SettingsBackend.open(pageId || "");
                return result !== false;
            }
            root.pendingPage = pageId || "";
            root.pendingSearchId = "";
            root.active = true;
            return true;
        } finally {
            root._inOpen = false;
        }
    }

    function close() {
        if (!root.active)
            return false;
        if (root.activeWindow && typeof root.activeWindow.closeChildWindows === "function")
            root.activeWindow.closeChildWindows();
        SettingsBackend.close();
        root.active = false;
        root.pendingPage = "";
        root.pendingSearchId = "";
        return true;
    }

    function toggle(pageId) {
        if (root.active) {
            root.close();
            return false;
        }
        return root.open(pageId);
    }

    function openSearch(searchId) {
        if (root.active && root.activeWindow) {
            SettingsBackend.openSearch(searchId || "");
            return true;
        }
        root.pendingSearchId = searchId || "";
        root.pendingPage = "";
        root.active = true;
        return true;
    }

    function handleWindowLoaded(item) {
        if (!item)
            return;
        SettingsBackend.registerWindow(item);
        if (root.pendingSearchId !== "") {
            SettingsBackend.openSearch(root.pendingSearchId);
            root.pendingSearchId = "";
        } else if (root.pendingPage !== "") {
            SettingsBackend.open(root.pendingPage);
            root.pendingPage = "";
        } else {
            SettingsBackend.presentWindow(item);
        }
    }

    // Route-preserving hot-switching
    Connections {
        target: PersonalizationConfig

        function onSettingsPanelStyleChanged() {
            if (!root.active || !root.activeWindow)
                return;

            const currentRoute = root.activeWindow.currentRouteId || "";
            if (typeof root.activeWindow.closeChildWindows === "function")
                root.activeWindow.closeChildWindows();

            root.pendingPage = currentRoute;
            root.pendingSearchId = "";
        }
    }

    Connections {
        target: ActionGateway

        function onSettingsOpenRequested(pageId) {
            root.open(pageId);
        }

        function onSettingsCloseRequested() {
            root.close();
        }

        function onSettingsToggleRequested(pageId) {
            root.toggle(pageId);
        }

        function onSettingsSearchRequested(searchId) {
            root.openSearch(searchId);
        }
    }

    // Unit self-registration (unit-model.md §6): the settings unit owns its
    // gateway presence and its IPC surface; both exist exactly while the
    // unit is loaded.
    Component.onCompleted: ActionGateway.settingsHost = root
    Component.onDestruction: {
        if (ActionGateway.settingsHost === root)
            ActionGateway.settingsHost = null;
    }

    function diagnosticsJson(): string {
        return ShellControlService.diagnosticsJson();
    }

    IpcHandler {
        target: "control-center"

        function open(pageId: string): string {
            if (!root.pageKnown(pageId))
                return "UNKNOWN_PAGE";
            return ActionGateway.requestSettingsOpen(pageId || "") ? "OK" : "UNAVAILABLE";
        }

        function close(): string {
            return ActionGateway.requestSettingsClose() ? "OK" : "CLOSED";
        }

        function toggle(pageId: string): string {
            if (!root.pageKnown(pageId))
                return "UNKNOWN_PAGE";
            return ActionGateway.requestSettingsToggle(pageId || "") ? "OPENING" : "CLOSING";
        }
    }

    IpcHandler {
        target: "settings"

        function open(pageId: string): string {
            if (!root.pageKnown(pageId))
                return "UNKNOWN_PAGE";
            return ActionGateway.requestSettingsOpen(pageId || "") ? "OK" : "UNAVAILABLE";
        }

        function close(): string {
            return ActionGateway.requestSettingsClose() ? "OK" : "CLOSED";
        }

        function toggle(pageId: string): string {
            if (!root.pageKnown(pageId))
                return "UNKNOWN_PAGE";
            return ActionGateway.requestSettingsToggle(pageId || "") ? "OPENING" : "CLOSING";
        }
    }

    LazyLoader {
        id: controlCenterLoader
        active: root.active && !root.dashboardStyle

        onItemChanged: {
            if (item)
                root.handleWindowLoaded(item);
        }

        ControlCenterWindow {
            id: controlCenterWindow

            onPopoutClosed: {
                root.active = false;
                SettingsBackend.windowClosed(controlCenterWindow);
            }
        }
    }

    LazyLoader {
        id: dashboardLoader
        active: root.active && root.dashboardStyle

        onItemChanged: {
            if (item)
                root.handleWindowLoaded(item);
        }

        Dashboard {
            id: dashboardWindow
            todoService: root.todoService

            onPopoutClosed: {
                root.active = false;
                SettingsBackend.windowClosed(dashboardWindow);
            }
        }
    }
}

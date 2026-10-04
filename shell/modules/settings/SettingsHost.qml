pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import qs.app
import qs.app.services
import qs.modules.settings.dashboard

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

    function open(pageId) {
        if (root._inOpen)
            return false;
        root._inOpen = true;
        try {
            if (root.active && root.activeWindow) {
                SettingsBackend.open(pageId || "");
                return true;
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
        } else {
            root.open(pageId);
            return true;
        }
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

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
    readonly property Component panelComponent: root.dashboardStyle ? dashboardWindowComponent :
                                                                      controlCenterWindowComponent

    function open(pageId) {
        if (root.active && settingsLoader.item) {
            SettingsBackend.open(pageId || "");
            return true;
        }
        root.pendingPage = pageId || "";
        root.pendingSearchId = "";
        root.active = true;
        return true;
    }

    function close() {
        if (!root.active)
            return false;
        if (settingsLoader.item && typeof settingsLoader.item.closeChildWindows === "function")
            settingsLoader.item.closeChildWindows();
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
        if (root.active && settingsLoader.item) {
            SettingsBackend.openSearch(searchId || "");
            return true;
        }
        root.pendingSearchId = searchId || "";
        root.pendingPage = "";
        root.active = true;
        return true;
    }

    // Route-preserving hot-switching
    Connections {
        target: PersonalizationConfig

        function onSettingsPanelStyleChanged() {
            if (!root.active || !settingsLoader.item)
                return;

            const currentRoute = settingsLoader.item.currentRouteId || "";
            if (typeof settingsLoader.item.closeChildWindows === "function")
                settingsLoader.item.closeChildWindows();

            root.pendingPage = currentRoute;
            root.pendingSearchId = "";

            // Tear down old window and cleanly recreate target window
            settingsLoader.active = false;
            Qt.callLater(() => {
                if (root.active)
                    settingsLoader.active = true;
            });
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

    // QtQuick Loader: destroys old item when sourceComponent or active changes
    Loader {
        id: settingsLoader
        active: root.active
        sourceComponent: root.panelComponent

        onItemChanged: {
            if (item) {
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
        }
    }

    Component {
        id: controlCenterWindowComponent

        ControlCenterWindow {
            onPopoutClosed: {
                root.active = false;
                SettingsBackend.windowClosed(this);
            }
        }
    }

    Component {
        id: dashboardWindowComponent

        Dashboard {
            todoService: root.todoService

            onPopoutClosed: {
                root.active = false;
                SettingsBackend.windowClosed(this);
            }
        }
    }
}

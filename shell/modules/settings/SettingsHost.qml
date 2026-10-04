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

    // QtQuick Loader, not Quickshell's LazyLoader: LazyLoader keeps the old item
    // alive while active, so changing `component` (i.e. switching the panel
    // style) would leave the previous window on screen until close/reopen.
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
            onPopoutClosed: {
                root.active = false;
                SettingsBackend.windowClosed(this);
            }
        }
    }
}

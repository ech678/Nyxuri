import QtQuick
import Quickshell
import qs.app

Scope {
    id: root

    property bool active: false
    property string pendingPage: ""
    property string pendingSearchId: ""

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

    LazyLoader {
        id: settingsLoader
        active: root.active

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

        ControlCenterWindow {
            id: controlCenterWindow

            onPopoutClosed: {
                root.active = false;
                SettingsBackend.windowClosed(controlCenterWindow);
            }
        }
    }
}

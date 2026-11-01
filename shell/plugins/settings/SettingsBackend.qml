pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.services
import qs.app
import qs.commons.i18n

// SettingsBackend — the settings window lifecycle (S0-3a slimmed): open /
// close / focus / pending-page orchestration for whichever window style is
// active. The deep-search state machine and the runtime anchor registry
// live on the SettingsSearch service so pages owned by other plugins never
// import this aggregator plugin.
Singleton {
    id: root

    property var controlCenterWindow: null

    property bool _openRequested: false
    property string _pendingPage: ""

    readonly property bool loaded: controlCenterWindow !== null
    readonly property bool visible: loaded && controlCenterWindow.visible

    function registerWindow(window) {
        if (!window)
            return;

        root.controlCenterWindow = window;
        SettingsSearch.searchWindow = window;
        if (root._openRequested)
            root.presentWindow(window);
    }

    function presentWindow(window) {
        if (!window)
            return;

        SettingsSearch.applyingSearch = true;
        const page = root._pendingPage;
        root._pendingPage = "";
        if (page !== "" && window.openPage)
            window.openPage(page);

        if (window.showWindow)
            window.showWindow();
        else
            window.visible = true;
        if (SettingsSearch.searchTarget)
            window.prepareSearchTarget(SettingsSearch.searchTarget, SettingsSearch.searchSerial);
        SettingsSearch.applyingSearch = false;
        SettingsSearch.retrySearch();
        root.focusWindow();
    }

    property bool _inOpen: false

    function open(pageId, preserveSearch) {
        if (root._inOpen)
            return false;
        root._inOpen = true;
        try {
            WidgetState.closeAllPopups();
            if (!preserveSearch) {
                SettingsSearch.cancelSearch();
                SettingsSearch.searchError = "";
            }
            root._openRequested = true;
            if (pageId !== undefined && pageId !== null && String(pageId) !== "") {
                root._pendingPage = String(pageId);
            }

            if (root.controlCenterWindow) {
                root.presentWindow(root.controlCenterWindow);
                return true;
            }

            ActionGateway.requestSettingsOpen(pageId);
            return true;
        } finally {
            root._inOpen = false;
        }
    }

    function openSearch(id) {
        const entry = SpotlightCatalog.setting(id);
        SettingsSearch.cancelSearch();
        SettingsSearch.searchError = "";
        if (!SpotlightCatalog.available(entry)) {
            SettingsSearch.reportSearchError(I18n.tr("This setting is currently unavailable"));
            return false;
        }
        SettingsSearch.beginSearch(entry);
        const accepted = root.open(entry.path[0], true);
        if (!accepted) {
            SettingsSearch.cancelSearch();
            SettingsSearch.reportSearchError(I18n.tr("Settings could not be opened"));
        }
        SettingsSearch.retrySearch();
        return accepted;
    }

    function focusWindow() {
        if (!root.visible || !root.controlCenterWindow)
            return;
        const target = ToplevelManager.toplevels.values.find(window => window.title
                                                                       === root.controlCenterWindow.title);
        if (target)
            target.activate();
    }

    function openOrFocus() {
        WidgetState.closeAllPopups();
        if (root.visible && root.controlCenterWindow) {
            const target = ToplevelManager.toplevels.values.find(window => window.title
                                                                           === root.controlCenterWindow.title);
            if (target) {
                target.activate();
                return true;
            }
        }
        return root.open();
    }

    function close() {
        SettingsSearch.cancelSearch();
        root._openRequested = false;
        root._pendingPage = "";

        const window = root.controlCenterWindow;
        if (window) {
            if (window.hideWindow)
                window.hideWindow();
            else
                window.visible = false;
            return true;
        }
        return false;
    }

    function toggle(pageId) {
        if (root._openRequested || root.visible) {
            root.close();
            return false;
        }
        return root.open(pageId);
    }

    function windowClosed(window) {
        SettingsSearch.cancelSearch();
        if (root.controlCenterWindow && root.controlCenterWindow !== window)
            return;

        root.controlCenterWindow = null;
        if (SettingsSearch.searchWindow === window)
            SettingsSearch.searchWindow = null;
        root._openRequested = false;
        root._pendingPage = "";
    }

    Component.onDestruction: {
        SettingsSearch.cancelSearch();
    }
}

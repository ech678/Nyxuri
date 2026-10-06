pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.app
import qs.shared.i18n

Singleton {
    id: root

    property var controlCenterWindow: null

    property bool applyingSearch: false
    property int searchSerial: 0
    property var searchTarget: null
    property var searchAnchors: ({})
    property string searchError: ""
    property string settledGeometry: ""

    function registerSearchAnchor(anchor) {
        const next = Object.assign({}, searchAnchors);
        next[anchor.entry.id] = anchor;
        searchAnchors = next;
        retrySearch();
    }

    function unregisterSearchAnchor(anchor) {
        if (searchAnchors[anchor.entry.id] !== anchor)
            return;
        const next = Object.assign({}, searchAnchors);
        delete next[anchor.entry.id];
        searchAnchors = next;
    }

    function cancelSearch() {
        searchSerial += 1;
        searchTarget = null;
        settledGeometry = "";
        searchDeadline.stop();
    }

    function reportSearchError(message) {
        searchError = message;
        if (!visible) {
            ActionGateway.execute(["notify-send", "-a", "Nyxuri Shell", I18n.tr("Settings",
                                                                                "ControlCenterWindow"),
                                   message], "settings");
        }
    }

    function openSearch(id) {
        const entry = SpotlightCatalog.setting(id);
        cancelSearch();
        searchError = "";
        if (!SpotlightCatalog.available(entry)) {
            reportSearchError(I18n.tr("This setting is currently unavailable"));
            return false;
        }
        searchTarget = entry;
        searchDeadline.restart();
        const accepted = open(entry.path[0], true);
        if (!accepted) {
            cancelSearch();
            reportSearchError(I18n.tr("Settings could not be opened"));
        }
        retrySearch();
        return accepted;
    }

    function retrySearch() {
        if (searchTarget)
            Qt.callLater(trySearch);
    }

    function trySearch() {
        if (!searchTarget || !visible || !controlCenterWindow)
            return;
        applyingSearch = true;
        const state = controlCenterWindow.advanceSearchTarget(searchTarget, searchSerial);
        applyingSearch = false;
        if (state === "cancelled") {
            cancelSearch();
            return;
        }
        if (state !== "ready")
            return;
        const anchor = searchTarget.anchor ? searchAnchors[searchTarget.id] :
                                             controlCenterWindow.searchPageAnchor;
        if (anchor)
            anchor.polishTarget();
        if (!anchor || !anchor.target || !anchor.target.visible || anchor.target.width <= 0
                || anchor.target.height <= 0)
            return;
        const geometry = [searchSerial, anchor.target.x, anchor.target.y, anchor.target.width,
                          anchor.target.height].join(":");
        if (settledGeometry !== geometry) {
            settledGeometry = geometry;
            Qt.callLater(trySearch);
            return;
        }
        if (anchor.reveal(searchSerial)) {
            searchTarget = null;
            searchDeadline.stop();
        }
    }

    Timer {
        id: searchDeadline
        interval: 4000
        onTriggered: {
            if (!root.searchTarget)
                return;
            root.cancelSearch();
            root.reportSearchError(I18n.tr("This setting is currently unavailable"));
        }
    }

    property bool _openRequested: false
    property string _pendingPage: ""

    readonly property bool loaded: controlCenterWindow !== null
    readonly property bool visible: loaded && controlCenterWindow.visible

    function registerWindow(window) {
        if (!window)
            return;

        root.controlCenterWindow = window;
        if (root._openRequested)
            root.presentWindow(window);
    }

    function presentWindow(window) {
        if (!window)
            return;

        root.applyingSearch = true;
        const page = root._pendingPage;
        root._pendingPage = "";
        if (page !== "" && window.openPage)
            window.openPage(page);

        if (window.showWindow)
            window.showWindow();
        else
            window.visible = true;
        if (root.searchTarget)
            window.prepareSearchTarget(root.searchTarget, root.searchSerial);
        root.applyingSearch = false;
        root.retrySearch();
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
                cancelSearch();
                searchError = "";
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
        root.cancelSearch();
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
        root.cancelSearch();
        if (root.controlCenterWindow && root.controlCenterWindow !== window)
            return;

        root.controlCenterWindow = null;
        root._openRequested = false;
        root._pendingPage = "";
    }

    Component.onDestruction: {
        root.cancelSearch();
    }
}

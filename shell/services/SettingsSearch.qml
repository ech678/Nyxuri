pragma Singleton

import QtQuick
import Quickshell
import qs.commons.i18n

// SettingsSearch — the settings deep-search state machine (S0-3a): the
// runtime anchor registry plus the reveal loop that drives the active
// settings window to the searched control. Split out of SettingsBackend so
// settings pages owned by other plugins register anchors through this
// service instead of reaching into the aggregator plugin; window lifecycle
// (open / close / focus / pending pages) stays on SettingsBackend, which
// also owns registering the window adapter here.
Singleton {
    id: root

    // The active settings window adapter (advanceSearchTarget /
    // searchPageAnchor), registered by SettingsBackend.registerWindow().
    property var searchWindow: null

    property var searchAnchors: ({})
    property bool applyingSearch: false
    property int searchSerial: 0
    property var searchTarget: null
    property string searchError: ""
    property string settledGeometry: ""

    function registerSearchAnchor(anchor) {
        const next = Object.assign({}, searchAnchors);
        next[anchor.anchorId] = anchor;
        searchAnchors = next;
        retrySearch();
    }

    function unregisterSearchAnchor(anchor) {
        if (searchAnchors[anchor.anchorId] !== anchor)
            return;
        const next = Object.assign({}, searchAnchors);
        delete next[anchor.anchorId];
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
        if (!searchWindow || !searchWindow.visible) {
            ActionGateway.execute(["notify-send", "-a", "Nyxuri Shell", I18n.tr("Settings",
                                                                                "ControlCenterWindow"),
                                   message], "settings");
        }
    }

    // Adopt a resolved SpotlightCatalog entry as the live search target and
    // arm the deadline; the caller orchestrates opening the window.
    function beginSearch(entry) {
        searchTarget = entry;
        searchDeadline.restart();
    }

    function retrySearch() {
        if (searchTarget)
            Qt.callLater(trySearch);
    }

    function trySearch() {
        if (!searchTarget || !searchWindow || !searchWindow.visible)
            return;
        applyingSearch = true;
        const state = searchWindow.advanceSearchTarget(searchTarget, searchSerial);
        applyingSearch = false;
        if (state === "cancelled") {
            cancelSearch();
            return;
        }
        if (state !== "ready")
            return;
        const anchor = searchTarget.anchor ? searchAnchors[searchTarget.id] : searchWindow.searchPageAnchor;
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
}

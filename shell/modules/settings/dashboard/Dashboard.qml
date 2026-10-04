pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Material
import Quickshell
import qs.shared.theme
import qs.shared.controls
import qs.app
import qs.app.services

// Dashboard-style settings window. Ported from end4-pC's
// modules/ii/settings/Dashboard.qml.
//
// end4-pC keeps this as a second top-level window: when the panel style is
// "dashboard" the overlay panel is hidden and this FloatingWindow takes over.
// Nyxuri does the same, but as a direct FloatingWindow rather than a Scope +
// Loader, because SettingsBackend registers whichever window is on screen and
// drives it through showWindow/hideWindow/openPage. SettingsHost picks this
// component instead of ControlCenterWindow when the style is "dashboard".
FloatingWindow {
    id: root

    signal popoutClosed

    property bool _wasShown: false
    property var todoService: null

    // SettingsBackend.presentWindow() calls openPage() before showWindow(), which
    // is also before the settle timer lets the content Loader build. Stash the
    // request and replay it once the content exists, otherwise the first
    // navigation after the window opens is silently dropped.
    property string pendingPage: ""
    readonly property string currentRouteId: dashboardLoader.item ? dashboardLoader.item.currentRouteId : ""

    function openPage(pageId) {
        if (dashboardLoader.item)
            return dashboardLoader.item.openPage(pageId);
        root.pendingPage = String(pageId ?? "");
        return true;
    }

    function showWindow() {
        root._wasShown = true;
        root.visible = true;
    }

    function hideWindow() {
        if (root.visible)
            root.visible = false;
    }

    function closeChildWindows() {
        if (dashboardLoader.item)
            dashboardLoader.item.closeChildWindows();
    }

    function prepareSearchTarget(entry, serial) {
        return "cancelled";
    }

    // Distinct from ControlCenterWindow's "nyxuri-settings" on purpose.
    // SettingsBackend.focusWindow() resolves the window to raise by matching
    // ToplevelManager titles, so two settings windows sharing one title would
    // make focus ambiguous the moment both are mapped.
    title: "nyxuri-settings-dashboard"

    // Opaque layer-0 fill, no rounded rectangle and no compositor blur region.
    // This is what end4-pC's Dashboard.qml does: upstream lets the compositor
    // round the window (niri's `geometry-corner-radius`) instead of painting its
    // own corners, and has no behind-window blur. Keeping nyxuri's own rounded
    // surface here would be an invented style on top of the reference.
    color: Appearance.colors.colLayer0

    // Fixed design size, same numbers as end4-pC's Dashboard.qml. Anything else
    // — the compositor's placement, whether it floats, what size it actually
    // ends up — is the compositor's call, so the shell asks for the design size
    // and stops there.
    implicitWidth: 1100
    implicitHeight: 680

    visible: false
    Material.theme: PersonalizationConfig.themeMode === "light" ? Material.Light : Material.Dark

    // The card grid animates from its own geometry; creating it before the
    // window has settled makes the first stagger read as a jump.
    property bool settled: false

    onWidthChanged: settleTimer.restart()
    onHeightChanged: settleTimer.restart()
    onVisibleChanged: {
        if (!root.visible && root._wasShown) {
            root._wasShown = false;
            root.popoutClosed();
        }
    }

    Timer {
        id: settleTimer

        interval: 70
        running: true
        onTriggered: root.settled = true
    }

    Loader {
        id: dashboardLoader

        anchors.fill: parent
        active: root.settled

        sourceComponent: DashboardContent {
            todoService: root.todoService
            onCloseRequested: root.hideWindow()
            onSidebarToggleRequested: ActionGateway.requestSidebarToggle("dashboard")
        }

        onItemChanged: {
            if (item && root.pendingPage !== "") {
                item.openPage(root.pendingPage);
                root.pendingPage = "";
            }
        }
    }
}

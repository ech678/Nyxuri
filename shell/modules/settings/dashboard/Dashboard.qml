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

    // SettingsBackend.presentWindow() calls openPage() before showWindow(), which
    // is also before the settle timer lets the content Loader build. Stash the
    // request and replay it once the content exists, otherwise the first
    // navigation after the window opens is silently dropped.
    property string pendingPage: ""

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

    title: "nyxuri-settings"
    // Every other FloatingWindow in this shell paints a rounded surface and asks
    // the compositor to blur behind it; without this the dashboard was the one
    // window with square corners.
    color: "transparent"
    implicitWidth: 1100
    implicitHeight: 680
    minimumSize: Qt.size(900, 600)
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

    Rectangle {
        id: outerBackground

        anchors.fill: parent
        radius: Appearance.rounding.large
        color: BlurService.backgroundColor(Appearance.m3colors.m3background)
        border.width: 1
        border.color: Appearance.colors.colOutlineVariant
    }

    CompositorBlurRegion {
        targetWindow: root
        backgroundItem: outerBackground
        radius: outerBackground.radius
    }

    Loader {
        id: dashboardLoader

        anchors.fill: parent
        active: root.settled

        sourceComponent: DashboardContent {
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

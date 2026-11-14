pragma Singleton

import QtQuick
import Quickshell
import qs.services

// Bridge singleton adapting upstream iNiR/end4 state access to Nyxuri services
Singleton {
    id: root

    property bool barOpen: true
    property bool screenLocked: false
    property bool startupLockPending: false
    property bool superDown: false
    property bool overviewOpen: false
    property bool sidebarLeftOpen: WidgetState.quickSettingsOpen
    property string sidebarLeftPresentationOutput: ""
    property bool sidebarRightOpen: WidgetState.dashboardSidebarOpen
    property string sidebarRightPresentationOutput: ""
    property bool mediaControlsOpen: false
    property bool controlPanelOpen: false
    // Single island OSD channel (B8.4): "" | "volume" | "brightness" | "caps" | "num".
    // The island owns the producer; the bar's scroll-away hint clears it.
    property string osdKind: ""
    property bool diSessionOpen: false
    property bool barCenterOnly: false
    property bool barStyleEditorOpen: false
    property int activeContextMenuCount: 0

    readonly property ShellScreen primaryScreen: Quickshell.screens[0] ?? null
    readonly property ShellScreen focusedScreen: Quickshell.screens[0] ?? null

    function toggleSidebarRight(outputName: string): void {
        ActionGateway.requestSidebarToggle("dashboard");
    }

    function toggleSidebarLeft(outputName: string): void {
        ActionGateway.requestSidebarToggle("quicksettings");
    }

    function requestSessionOpen(): void {
        ActionGateway.requestSessionOpen();
    }

    function isFrameHovered(screenName: string, edge: string): bool {
        return false;
    }
}

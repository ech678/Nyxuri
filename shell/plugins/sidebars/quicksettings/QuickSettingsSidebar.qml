import QtQuick
import qs.commons
import qs.services
import qs.ui

Item {
    id: root

    property var panelScreen: null
    readonly property bool onLeft: PersonalizationConfig.quickSettingsSidebarSide === "left"
    // D4g 批四b avoidance insets (ScreenBarLayout projection): the
    // same-edge rail reserves the x span; top/bottom bands reserve y.
    readonly property real railInset: ScreenBarLayout.reservation(panelScreen, root.onLeft ? "left" : "right")
    readonly property real topInset: ScreenBarLayout.reservation(panelScreen, "top")
    readonly property real bottomInset: ScreenBarLayout.reservation(panelScreen, "bottom")
    property real sidebarWidth: Math.min(PersonalizationConfig.sidebarWidth, Math.max(0, width))
    readonly property alias blurBackgroundItem: revealSurface.blurBackgroundItem
    readonly property bool requestedOpen: WidgetState.quickSettingsOpen
    property bool presentationAllowed: true
    property bool panelPresented: false
    property bool contentRetained: false
    property bool presentationOpen: false
    readonly property bool contentReady: quickSettingsLoader.status === Loader.Ready && quickSettingsLoader.item !== null && quickSettingsLoader.item.readyForPresentation
    // A presented surface is only created after contentReady. It remains
    // operational until the closing reveal has fully covered its contents.
    readonly property bool contentOperational: panelPresented

    function preparePresentation() {
        contentRetained = true;
        startPresentation();
    }

    function startPresentation() {
        if (!requestedOpen || !contentReady || !presentationAllowed)
            return;
        panelPresented = true;
        presentationOpen = true;
    }

    function beginClosing() {
        presentationOpen = false;
        if (panelPresented)
            return;
        if (!PersonalizationConfig.keepSidebarsLoaded)
            contentRetained = false;
    }

    function finishClosing() {
        if (requestedOpen)
            return;

        // Finish hiding the surface before releasing its layout tree.
        revealSurface.reset();
        panelPresented = false;
        if (!PersonalizationConfig.keepSidebarsLoaded)
            contentRetained = false;
    }

    Component.onCompleted: {
        // Retain after the first open, without preloading QuickSettings
        // and its services during shell startup.
        if (requestedOpen)
            preparePresentation();
    }

    onRequestedOpenChanged: {
        if (requestedOpen)
            preparePresentation();
        else
            beginClosing();
    }

    onPresentationAllowedChanged: {
        if (presentationAllowed)
            startPresentation();
    }

    onContentReadyChanged: {
        if (contentReady)
            startPresentation();
    }

    Connections {
        target: PersonalizationConfig

        function onKeepSidebarsLoadedChanged() {
            if (!PersonalizationConfig.keepSidebarsLoaded && !root.requestedOpen && !root.panelPresented) {
                root.contentRetained = false;
            }
        }
    }

    function containsPoint(hostX, hostY) {
        const localPosition = revealSurface.mapFromItem(root, hostX, hostY);
        return revealSurface.containsVisiblePoint(localPosition.x, localPosition.y);
    }

    EdgeRevealSurface {
        id: revealSurface

        visible: root.panelPresented
        // D4g 批四b: the drawer insets by the topology projection — the
        // same-edge rail reserves the x span, top/bottom bands reserve the
        // y span (Overlay would otherwise paint over the Top-layer bars).
        x: root.onLeft ? root.railInset : root.width - root.sidebarWidth - root.railInset
        y: root.topInset
        width: root.sidebarWidth
        height: Math.max(0, root.height - root.topInset - root.bottomInset)
        open: root.presentationOpen
        onLeft: root.onLeft
        backgroundColor: Appearance.applyAlpha(Appearance.colors.colLayer0Base, PersonalizationConfig.sidebarOpacity >= 0 ? PersonalizationConfig.sidebarOpacity : PersonalizationConfig.shellBackgroundOpacity)
        onClosed: root.finishClosing()

        Loader {
            id: quickSettingsLoader

            anchors.fill: parent
            active: root.contentRetained
            asynchronous: true
            sourceComponent: quickSettingsComponent
        }
    }

    Component {
        id: quickSettingsComponent

        QuickSettings {
            anchors.fill: parent
            screen: root.panelScreen
            foreground: root.contentOperational
        }
    }
}

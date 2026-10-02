import QtQuick
import qs.app
import qs.shared.theme
import qs.app.services
import qs.shared.controls

Item {
    id: root

    property var panelScreen: null
    readonly property bool onLeft: PersonalizationConfig.quickSettingsSidebarSide === "left"
    property real sidebarWidth: Math.min(Metrics.sidebarWidthComfortable, Math.max(0, width))
    readonly property alias blurBackgroundItem: revealSurface.blurBackgroundItem
    readonly property bool requestedOpen: WidgetState.quickSettingsOpen
    property bool presentationAllowed: true
    property bool panelPresented: false
    property bool contentRetained: false
    property bool presentationOpen: false
    readonly property bool contentReady: quickSettingsLoader.status === Loader.Ready
                                         && quickSettingsLoader.item !== null
                                         && quickSettingsLoader.item.readyForPresentation
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
        x: root.onLeft ? 0 : root.width - root.sidebarWidth
        y: 0
        width: root.sidebarWidth
        height: root.height
        open: root.presentationOpen
        onLeft: root.onLeft
        backgroundColor: BlurService.backgroundColor(Appearance.colors.colLayer0)
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

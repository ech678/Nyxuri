import QtQuick
import qs.Modules.ControlCenter
import qs.Modules.FilePicker
import qs.Common
import qs.Services
import qs.Widgets.common

Item {
    id: root

    signal presentationClosed

    property var panelScreen: null
    readonly property bool onLeft: PersonalizationConfig.dashboardSidebarSide === "left"
    property real sidebarWidth: Math.min(Metrics.sidebarWidthComfortable, Math.max(0, width))
    readonly property alias blurBackgroundItem: revealSurface.blurBackgroundItem
    readonly property bool requestedOpen: WidgetState.dashboardSidebarOpen
    property bool presentationAllowed: true
    property bool panelPresented: false
    property bool contentRetained: false
    property bool presentationOpen: false
    property bool keepLoaded: PersonalizationConfig.keepSidebarsLoaded
    property var weatherSourceOverride: null
    readonly property bool contentReady: sidebarContentLoader.status === Loader.Ready
                                         && sidebarContentLoader.item !== null
                                         && sidebarContentLoader.item.readyForPresentation
    // A presented surface is only created after contentReady. It remains
    // operational until the closing reveal has fully covered its contents.
    readonly property bool contentOperational: panelPresented
    readonly property string activeView: WidgetState.dashboardSidebarView
    readonly property int instantiatedViewCount: sidebarContentLoader.item
                                                 ? sidebarContentLoader.item.instantiatedViewCount : 0
    readonly property var weatherView: sidebarContentLoader.item ? sidebarContentLoader.item.weatherView :
                                                                   null
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
        if (!keepLoaded)
            contentRetained = false;
        root.presentationClosed();
    }

    function finishClosing() {
        if (requestedOpen)
            return;

        // Finish hiding the surface before releasing its layout tree.
        revealSurface.reset();
        panelPresented = false;
        if (!root.keepLoaded)
            contentRetained = false;
        root.presentationClosed();
    }

    Component.onCompleted: {
        // Retain after the first open; keeping content warm must not
        // instantiate the entire sidebar during shell startup.
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

    onKeepLoadedChanged: {
        if (!root.keepLoaded && !requestedOpen && !root.panelPresented) {
            root.contentRetained = false;
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
            id: sidebarContentLoader

            anchors.fill: parent
            active: root.contentRetained
            asynchronous: true
            sourceComponent: dashboardSidebarContentComponent
        }
    }

    // Keep file selection alive when the sidebar content is unloaded. This is
    // an independent window, so hiding the sidebar host cannot hide the picker.
    FilePickerWindow {
        id: profileImagePicker

        property bool forAvatar: true

        dialogTitle: forAvatar ? qsTranslate("AccountPage", "Choose avatar") : qsTranslate(
                                     "AccountProfileHeader", "Choose banner image")
        description: forAvatar ? qsTranslate("FilePickerWindow", "Choose an image for your user avatar") : ""
        selectionPrompt: forAvatar ? qsTranslate("FilePickerWindow", "Choose an image") : dialogTitle
        windowIconName: forAvatar ? "add_photo_alternate" : "wallpaper"

        function chooseImage(avatar) {
            forAvatar = avatar;
            // Capture the output rather than follow subsequent sidebar moves.
            targetScreen = root.panelScreen;
            WidgetState.closeAllPopups();
            const banner = WallpaperPaletteSession.previewForScreen("banner", "")
                  || PersonalizationConfig.bannerSource || WallpaperService.currentWallpaper;
            openAt(avatar ? picturesDir : WallpaperService.isImagePath(banner) ? WallpaperService.parentFolder(
                                                                                     banner) : PersonalizationConfig.wallpaperFolder);
        }

        onAccepted: (path, isDirectory) => {
            if (isDirectory)
                return;
            if (forAvatar)
                AvatarService.setAvatar(path);
            else
                PersonalizationConfig.setBannerSource(path);
        }
    }

    // The palette session must survive unloading the information page as well.
    WallpaperColorPicker {
        id: bannerColorPicker
        requiresParentWindow: false
    }

    Component {
        id: dashboardSidebarContentComponent

        DashboardSidebarContent {
            anchors.fill: parent
            screenName: root.panelScreen ? root.panelScreen.name : ""
            onImageSelectionRequested: forAvatar => profileImagePicker.chooseImage(forAvatar)
            onBannerColorRequested: {
                WidgetState.closeAllPopups();
                bannerColorPicker.showFor("banner", "");
            }
            weatherSourceOverride: root.weatherSourceOverride
            foreground: root.contentOperational
            presentationActive: root.contentOperational
        }
    }
}

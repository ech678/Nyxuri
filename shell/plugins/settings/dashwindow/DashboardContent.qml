pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell.Widgets
import qs.commons
import qs.ui
import qs.services
import qs.commons.i18n

// Dashboard surface: toolbar, five-page nav, search, and the per-page
// loaders. Ported from end4-pC's modules/ii/settings/DashboardContent.qml;
// the port keeps the window chrome, toolbar, nav and the entry/exit
// choreography, while every page renders its own real implementation.
Item {
    id: root

    // The window has no chrome of its own — the host owns open/close.
    signal closeRequested
    signal sidebarToggleRequested

    property var todoService: null

    property int currentPage: 0
    property int pendingPage: 0
    property int staggerMs: 45
    property bool searchOpen: false
    property string searchQuery: ""

    readonly property int homePage: 0
    readonly property int wallpapersPage: 1
    readonly property int presetsPage: 2
    readonly property int mediaPage: 3
    readonly property int settingsPage: 4

    // Page selectors: exactly one page component is active per currentPage.
    readonly property bool homeImplemented: root.currentPage === root.homePage
    readonly property bool settingsImplemented: root.currentPage === root.settingsPage
    readonly property bool wallpapersImplemented: root.currentPage === root.wallpapersPage
    readonly property bool mediaImplemented: root.currentPage === root.mediaPage
    // The third tab used to be Presets; nyxuri has no preset system, so it
    // now hosts the matugen scheme gallery (see DashboardThemesPage).
    readonly property bool themesImplemented: root.currentPage === root.presetsPage

    // ── Cover-art theming ───────────────────────────────────────────────────
    // While the media page is up and a palette was extracted, the page is
    // painted from the album art instead of the wallpaper theme. Ported from
    // end4-pC's DashboardContent, where `mediaColors` is what makes that page
    // look like the record rather than like the settings panel.
    //
    // Gated on `pendingPage` as well as `currentPage`: the page transition
    // animates the outgoing cards out while the incoming ones fly in, and
    // flipping the whole surface at the start of that overlap makes the
    // crossfade read as a colour glitch.
    readonly property bool mediaVisible: mediaState.active && root.currentPage === root.mediaPage
                                         && root.pendingPage === root.mediaPage

    // The resolved palette, in the same shape end4-pC passes to its media page:
    // either the cover-derived scheme or a plain Appearance.colors. Both expose
    // the same colour names, so consumers read `mediaColors.colOnLayer0` with
    // no ternary and a non-media page tracks theme changes as before.
    readonly property var mediaColors: root.mediaVisible ? mediaState.blendedColors : Appearance.colors

    // Named aliases for the shell chrome around the page. The ternary lives
    // here rather than at each call site because two of the names differ
    // between the two objects (the toolbar uses a surface container, and the
    // hover state comes from the layer rather than the secondary container).
    readonly property QtObject ui: QtObject {
        readonly property color surface: root.mediaColors.colLayer1
        readonly property color toolbar: root.mediaVisible ? root.mediaColors.colLayer1 :
                                                             Appearance.m3colors.m3surfaceContainer

        readonly property color fgSurface: root.mediaColors.colOnLayer1
        readonly property color subtext: root.mediaColors.colSubtext
        readonly property color hover: root.mediaVisible ? root.mediaColors.colSecondaryContainerHover :
                                                           Appearance.colors.colLayer1Hover
        readonly property color accent: root.mediaColors.colPrimary
        readonly property color accentHover: root.mediaColors.colPrimaryHover
        readonly property color accentActive: root.mediaColors.colPrimaryActive
        readonly property color fgAccent: root.mediaColors.colOnPrimary
        readonly property color container: root.mediaVisible ? root.mediaColors.colSecondaryContainer :
                                                               Appearance.colors.colPrimaryContainer
        readonly property color fgContainer: root.mediaVisible ? root.mediaColors.colOnSecondaryContainer :
                                                                 Appearance.colors.colOnPrimaryContainer
    }

    DashboardMediaState {
        id: mediaState

        pageActive: root.mediaImplemented
    }

    readonly property var pageNames: [
        {
            "id": "home",
            "name": I18n.tr("Home", "DashboardContent"),
            "icon": "home"
        },
        {
            "id": "wallpapers",
            "name": I18n.tr("Wallpapers"),
            "icon": "wallpaper"
        },
        {
            "id": "themes",
            "name": I18n.tr("Themes"),
            "icon": "palette"
        },
        {
            "id": "media",
            "name": I18n.tr("Media"),
            "icon": "play_circle"
        },
        {
            "id": "settings",
            "name": I18n.tr("Settings"),
            "icon": "settings"
        }
    ]

    // The dashboard has no rail of its own, so external callers (the settings
    // IPC target) address pages by id. nyxuri route ids are accepted as aliases
    // so a route id like "theme" still lands somewhere sensible.
    readonly property var pageAliases: ({
                                            "wallpaper": "wallpapers",
                                            "preset": "themes",
                                            "account": "settings",
                                            "general": "settings",
                                            "theme": "themes",
                                            "keystone": "settings",
                                            "advanced": "settings",
                                            "shell": "settings"
                                        })

    readonly property string currentRouteId: pageNames[currentPage] ? pageNames[currentPage].id : "home"

    function closeChildWindows() {
        if (root.homeImplemented && homeLoader.item && typeof homeLoader.item.closeChildWindows
                === "function")
            homeLoader.item.closeChildWindows();
    }

    function openPage(pageId) {
        const wanted = root.pageAliases[pageId] ?? pageId;
        const index = root.pageNames.findIndex(page => page.id === wanted);
        if (index < 0)
            return false;
        if (index !== root.currentPage) {
            root.pendingPage = index;
            root.currentPage = index;
        }
        return true;
    }

    // Nerd Font distro mark. Nyxuri renders these as glyphs (same map as
    // UserCard) instead of end4-pC's themed icon lookup, so the pill keeps its
    // 22px slot without depending on an icon theme shipping distro logos.
    readonly property var distroGlyphs: ({
                                             "arch": "󰣇",
                                             "archlinux": "󰣇",
                                             "endeavouros": "",
                                             "manjaro": "",
                                             "fedora": "",
                                             "ubuntu": "",
                                             "debian": "",
                                             "opensuse": "",
                                             "nixos": "",
                                             "gentoo": "",
                                             "void": ""
                                         })

    readonly property string distroGlyph: root.distroGlyphs[String(SystemIdentityService.distroId
                                                                   || "").toLowerCase()] || ""


    function goToPage(index) {
        if (index === currentPage || switchTimer.running)
            return;
        pendingPage = index;
        pageExitRequested();
        forceActiveFocus();
        switchTimer.restart();
    }

    function openSearch() {
        searchOpen = true;
        Qt.callLater(() => searchInput.forceActiveFocus());
    }

    function closeSearch() {
        searchInput.text = "";
        searchOpen = false;
        forceActiveFocus();
    }

    function typedCharacter(event) {
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))
            return false;
        return event.text.length === 1 && event.text.charCodeAt(0) >= 32 && event.text.charCodeAt(0) !== 127;
    }

    function typeIntoSearch(character) {
        const previous = searchOpen ? searchInput.text : "";
        searchOpen = true;
        searchInput.text = previous + character;
        searchInput.cursorPosition = searchInput.text.length;
        Qt.callLater(() => searchInput.forceActiveFocus());
    }

    signal pageExitRequested

    focus: true

    Component.onCompleted: forceActiveFocus()

    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (searchOpen)
                closeSearch();
            else
                root.closeRequested();
        } else if (event.key === Qt.Key_F && (event.modifiers & Qt.ControlModifier)) {
            if (searchOpen)
                closeSearch();
            else
                openSearch();
        } else if (event.key === Qt.Key_Tab) {
            goToPage((pendingPage + 1) % pageNames.length);
        } else if (event.key === Qt.Key_Backtab) {
            goToPage((pendingPage - 1 + pageNames.length) % pageNames.length);
        } else if (!searchOpen && typedCharacter(event)) {
            typeIntoSearch(event.text);
        } else {
            return;
        }
        event.accepted = true;
    }

    Timer {
        id: switchTimer

        interval: 320 + 6 * (root.staggerMs - 4)
        onTriggered: {
            root.currentPage = root.pendingPage;
        }
    }

    // Album-art backdrop for the media page. Three stacked pieces, matching
    // end4-pC:
    //
    //   1. the cover itself, hidden — it exists only as the blur's source, so
    //      it must be laid out but not painted;
    //   2. a heavily blurred copy of it, faded in with the media page;
    //   3. a translucent layer tinted with the derived colLayer0, which is
    //      what keeps the cards and text legible over an arbitrary photograph.
    //      Blur alone is not enough: a bright cover blurs into a bright wash and
    //      the label text disappears into it.
    //
    // All three sit before the ColumnLayout, so the page content draws on top
    // without needing a z index.
    Image {
        id: dashboardArtSource

        anchors.fill: parent
        source: mediaState.displayedArtFilePath
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        // The same cover is decoded again inside the media page's own art card,
        // at a different size. Sharing the cache would make whichever asks
        // first win the dimensions and scale the other one.
        cache: false
        sourceSize: Qt.size(800, 800)
        visible: false
    }

    FastBlur {
        id: dashboardArt

        anchors.fill: parent
        source: dashboardArtSource
        radius: 64
        opacity: root.mediaVisible ? 1 : 0
        visible: opacity > 0

        Behavior on opacity {
            NumberAnimation {
                duration: 300
                easing.type: Easing.OutCubic
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: mediaState.blendedColors.colLayer0
        opacity: root.mediaVisible ? 0.6 : 0

        Behavior on opacity {
            NumberAnimation {
                duration: 300
                easing.type: Easing.OutCubic
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Item {
            Layout.fillWidth: true
            implicitHeight: 56

            Rectangle {
                id: distroPill

                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                implicitHeight: 44
                implicitWidth: distroPillRow.implicitWidth + 28
                radius: height / 2
                color: root.ui.surface
                border.width: 2
                border.color: root.ui.accent

                RowLayout {
                    id: distroPillRow

                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        Layout.preferredWidth: 22
                        Layout.preferredHeight: 22
                        text: root.distroGlyph
                        color: root.ui.fgSurface
                        font.family: Fonts.ui
                        font.pixelSize: 20
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    StyledText {
                        text: SystemIdentityService.distroName
                        font.pixelSize: Typography.bodyLarge.pixelSize
                        font.weight: Font.Medium
                        color: root.ui.fgSurface
                    }
                }
            }

            Toolbar {
                anchors.centerIn: parent
                colBackground: root.ui.surface

                Repeater {
                    model: root.pageNames

                    delegate: RippleButton {
                        id: navBtn

                        required property int index
                        required property var modelData

                        implicitHeight: 38
                        leftPadding: 14
                        rightPadding: 14
                        buttonRadius: height / 2
                        toggled: root.pendingPage === index
                        onClicked: root.goToPage(index)
                        containerColor: navBtn.toggled ? root.ui.accent : "transparent"
                        rippleColor: navBtn.toggled ? root.ui.fgAccent : root.ui.fgSurface
                        stateLayerColor: navBtn.toggled ? root.ui.fgAccent : root.ui.fgSurface
                        // RippleButton draws its state layer at full opacity by
                        // default, which over a transparent container floods the
                        // button and swallows the label. Use the M3 hover/focus/
                        // pressed opacities like the rest of the shell.
                        stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                        hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                        focusStateLayerOpacity: Appearance.interaction.focusStateLayerOpacity
                        pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity

                        contentItem: Item {
                            implicitWidth: navContentRow.implicitWidth
                            implicitHeight: navContentRow.implicitHeight

                            RowLayout {
                                id: navContentRow

                                anchors.centerIn: parent
                                spacing: 6

                                MaterialSymbol {
                                    text: navBtn.modelData.icon
                                    iconSize: Typography.titleLarge.pixelSize
                                    color: navBtn.toggled ? root.ui.fgAccent : root.ui.fgSurface
                                    fill: navBtn.toggled ? 1 : 0
                                }

                                StyledText {
                                    text: navBtn.modelData.name
                                    color: navBtn.toggled ? root.ui.fgAccent : root.ui.fgSurface
                                    visible: navBtn.toggled
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                ClippingRectangle {
                    id: searchPill

                    implicitHeight: 44
                    implicitWidth: root.searchOpen ? 280 : 44
                    radius: height / 2
                    color: root.ui.surface
                    border.width: searchInput.activeFocus ? 2 : 0
                    border.color: root.ui.accent

                    Behavior on implicitWidth {
                        NumberAnimation {
                            duration: 220
                            easing.type: Easing.OutCubic
                        }
                    }

                    RippleButton {
                        id: searchButton

                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        implicitWidth: 44
                        implicitHeight: 44
                        buttonRadius: 22
                        containerColor: "transparent"
                        stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                        hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                        focusStateLayerOpacity: Appearance.interaction.focusStateLayerOpacity
                        pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                        onClicked: root.searchOpen ? root.closeSearch() : root.openSearch()

                        contentItem: Item {
                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: "search"
                                iconSize: Typography.titleLarge.pixelSize
                                color: root.ui.fgSurface
                            }
                        }
                    }

                    TextInput {
                        id: searchInput

                        anchors.left: searchButton.right
                        anchors.right: parent.right
                        anchors.rightMargin: 14
                        anchors.verticalCenter: parent.verticalCenter
                        visible: root.searchOpen
                        clip: true
                        font.pixelSize: Typography.bodyLarge.pixelSize
                        font.family: Fonts.ui
                        color: root.ui.fgSurface
                        selectionColor: root.ui.accent
                        onTextChanged: root.searchQuery = text
                        Keys.onEscapePressed: {
                            if (text !== "")
                                text = "";
                            else
                                root.closeSearch();
                        }

                        StyledText {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: searchInput.text === ""
                            text: I18n.tr("Search settings")
                            color: root.ui.subtext
                        }
                    }
                }

                RippleButton {
                    id: notificationsButton

                    implicitWidth: 44
                    implicitHeight: 44
                    buttonRadius: height / 2
                    containerColor: root.ui.surface
                    stateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    hoverStateLayerOpacity: Appearance.interaction.hoverStateLayerOpacity
                    focusStateLayerOpacity: Appearance.interaction.focusStateLayerOpacity
                    pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                    onClicked: root.sidebarToggleRequested()

                    contentItem: Item {
                        MaterialSymbol {
                            anchors.centerIn: parent
                            text: "notifications"
                            iconSize: Typography.titleLarge.pixelSize
                            color: root.ui.fgSurface
                        }

                        Rectangle {
                            visible: NotificationService.list.length > 0
                            anchors.top: parent.top
                            anchors.right: parent.right
                            anchors.topMargin: -2
                            anchors.rightMargin: -4
                            implicitHeight: 16
                            implicitWidth: Math.max(16, badgeText.implicitWidth + 8)
                            radius: height / 2
                            color: Appearance.colors.colError

                            StyledText {
                                id: badgeText

                                anchors.centerIn: parent
                                text: NotificationService.list.length > 9 ? "9+" :
                                                                            NotificationService.list.length
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                color: Appearance.colors.colOnError
                            }
                        }
                    }
                }

                Rectangle {
                    id: avatarRect

                    implicitWidth: 44
                    implicitHeight: 44
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 44
                    radius: width / 2
                    color: root.ui.container

                    Image {
                        id: avatarImage

                        anchors.fill: parent
                        source: AvatarService.avatarUrl
                        sourceSize.width: avatarImage.width * 2
                        sourceSize.height: avatarImage.height * 2
                        fillMode: Image.PreserveAspectCrop
                        visible: status === Image.Ready
                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: avatarRect.width
                                height: avatarRect.height
                                radius: avatarRect.radius
                            }
                        }
                    }

                    MaterialSymbol {
                        anchors.centerIn: parent
                        visible: avatarImage.status !== Image.Ready
                        text: "account_circle"
                        iconSize: 30
                        color: root.ui.fgContainer
                    }
                }
            }
        }

        Loader {
            id: themesPageLoader

            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: active
            active: root.themesImplemented
            asynchronous: true

            sourceComponent: DashboardThemesPage {
                pager: root
                staggerMs: root.staggerMs
            }
        }

        Loader {
            id: mediaPageLoader

            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: active
            active: root.mediaImplemented

            sourceComponent: DashboardMediaPage {
                pager: root
                staggerMs: root.staggerMs
                // Drives the cava lifecycle. The item's own `visible` reads
                // false at creation inside a Loader, so the wave must key off
                // the page state instead.
                pageActive: root.mediaImplemented
                // Wave data comes from the shared state object; the page must
                // not own the cava process (invalid-context trap in Loaders).
                mediaState: mediaState
                // The cover-derived scheme, or the theme's own colours when no
                // palette is available. Same shape either way, so the page
                // never branches on it.
                colors: root.mediaColors
                blurSource: dashboardArt
            }
        }

        Loader {
            id: wallpapersPageLoader

            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: active
            active: root.wallpapersImplemented
            asynchronous: true

            sourceComponent: DashboardWallpapersPage {
                pager: root
                staggerMs: root.staggerMs
            }
        }

        Loader {
            id: settingsPageLoader

            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: active
            active: root.settingsImplemented
            asynchronous: true

            sourceComponent: DashboardSettingsPage {
                pager: root
                staggerMs: root.staggerMs
            }
        }

        Loader {
            id: homeLoader

            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: active
            active: root.homeImplemented

            sourceComponent: DashboardHomePage {
                todoService: root.todoService
                pager: root
                staggerMs: root.staggerMs
            }
        }
    }
}

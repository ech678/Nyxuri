pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import Quickshell.Widgets
import qs.shared.theme
import qs.shared.controls
import qs.app.services

// Dashboard surface: toolbar, five-page nav, search, and the card grid.
// Ported from end4-pC's modules/ii/settings/DashboardContent.qml.
//
// Scope note: this port covers the shell only — window chrome, toolbar, nav,
// grid geometry and the entry/exit choreography. end4-pC's five pages (Home,
// Wallpapers, Presets, Media, Settings) are separate 4-8k line trees bound to
// its own config schema; here every page renders the same card grid built by
// buildPage(), so the layout is identical while the content stays a placeholder
// until each page is ported.
Item {
    id: root

    // The window has no chrome of its own — the host owns open/close.
    signal closeRequested
    signal sidebarToggleRequested

    property int currentPage: 0
    property int pendingPage: 0
    property int staggerMs: 45
    property var pageBoxes: buildPage(0)
    property int selectedIndex: 0
    property bool searchOpen: false
    property string searchQuery: ""

    readonly property int homePage: 0
    readonly property int wallpapersPage: 1
    readonly property int presetsPage: 2
    readonly property int mediaPage: 3
    readonly property int settingsPage: 4

    // Pages that have a real implementation instead of the placeholder grid.
    // Extend this as each page lands.
    readonly property bool homeImplemented: root.currentPage === root.homePage
    readonly property bool settingsImplemented: root.currentPage === root.settingsPage
    readonly property bool wallpapersImplemented: root.currentPage === root.wallpapersPage
    readonly property bool mediaImplemented: root.currentPage === root.mediaPage
    // The third tab used to be Presets; nyxuri has no preset system, so it
    // now hosts the matugen scheme gallery (see DashboardThemesPage).
    readonly property bool themesImplemented: root.currentPage === root.presetsPage

    readonly property var pageNames: [
        {
            "id": "home",
            "name": qsTr("Home"),
            "icon": "home"
        },
        {
            "id": "wallpapers",
            "name": qsTr("Wallpapers"),
            "icon": "wallpaper"
        },
        {
            "id": "themes",
            "name": qsTr("Themes"),
            "icon": "palette"
        },
        {
            "id": "media",
            "name": qsTr("Media"),
            "icon": "play_circle"
        },
        {
            "id": "settings",
            "name": qsTr("Settings"),
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
                                            "theme": "settings",
                                            "keystone": "settings",
                                            "advanced": "settings"
                                        })

    function openPage(pageId) {
        const wanted = root.pageAliases[pageId] ?? pageId;
        const index = root.pageNames.findIndex(page => page.id === wanted);
        if (index < 0)
            return false;
        if (index !== root.currentPage) {
            root.pendingPage = index;
            root.currentPage = index;
            root.selectedIndex = 0;
            root.pageBoxes = root.buildPage(index);
        }
        return true;
    }

    // Card spans per page, in units of a 4-column grid. Copied verbatim from
    // end4-pC so the grid silhouette matches.
    readonly property var layouts: [[[2, 2], [1, 1], [1, 1], [1, 1], [1, 1], [2, 1], [1, 1], [1, 1]], [[1, 1], [1, 1], [2, 1], [1, 2], [2, 1], [1, 2], [1, 1], [1, 1]], [[4, 1], [2, 1], [2, 1], [1, 1], [1, 1], [1, 1], [1, 1]], [[2, 2], [2, 1], [2, 1], [2, 1], [1, 1], [1, 1]], [[1, 1], [1, 1], [1, 1], [1, 1], [2, 2], [2, 1], [2,
                                                                                                                                                                                                                                                                                                                                      1]]]

    readonly property var cardPalette: [
        {
            "bg": Appearance.colors.colPrimaryContainer,
            "fg": Appearance.colors.colOnPrimaryContainer
        },
        {
            "bg": Appearance.colors.colSecondaryContainer,
            "fg": Appearance.colors.colOnSecondaryContainer
        },
        {
            "bg": Appearance.colors.colTertiaryContainer,
            "fg": Appearance.colors.colOnTertiaryContainer
        },
        {
            "bg": Appearance.colors.colLayer1,
            "fg": Appearance.colors.colOnLayer1
        },
        {
            "bg": Appearance.colors.colSurfaceContainerHigh,
            "fg": Appearance.colors.colOnLayer1
        }
    ]

    readonly property var icons: ["wallpaper", "palette", "style", "download", "upload", "favorite", "tune",
        "widgets", "auto_awesome", "dark_mode"]

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

    function shuffled(list) {
        const copy = list.slice();
        for (let i = copy.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            const t = copy[i];
            copy[i] = copy[j];
            copy[j] = t;
        }
        return copy;
    }

    // Builds one page of placeholder cards. end4-pC returns [] for its five real
    // pages and only uses this for pages it has no content for; here it backs
    // every page, which is what keeps the grid geometry identical.
    function buildPage(page) {
        const spans = layouts[page % layouts.length];
        return spans.map((s, i) => {
            const c = cardPalette[Math.floor(Math.random() * cardPalette.length)];
            return {
                "colSpan": s[0],
                "rowSpan": s[1],
                "bg": c.bg,
                "fg": c.fg,
                "icon": icons[Math.floor(Math.random() * icons.length)],
                "travelX": (Math.random() - 0.5) * 500,
                "travelY": (Math.random() - 0.5) * 400
            };
        });
    }

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

    function moveSelection(dx, dy) {
        const cur = boxRepeater.itemAt(selectedIndex);
        if (!cur)
            return;
        const cx = cur.x + cur.width / 2;
        const cy = cur.y + cur.height / 2;
        let best = -1;
        let bestScore = Infinity;
        for (let i = 0; i < boxRepeater.count; i++) {
            if (i === selectedIndex)
                continue;
            const it = boxRepeater.itemAt(i);
            if (!it)
                continue;
            const ox = it.x + it.width / 2 - cx;
            const oy = it.y + it.height / 2 - cy;
            const along = dx !== 0 ? ox * dx : oy * dy;
            const across = dx !== 0 ? Math.abs(oy) : Math.abs(ox);
            if (along <= 1)
                continue;
            const score = along + across * 2;
            if (score < bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best >= 0)
            selectedIndex = best;
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
        } else if (event.key === Qt.Key_Left) {
            moveSelection(-1, 0);
        } else if (event.key === Qt.Key_Right) {
            moveSelection(1, 0);
        } else if (event.key === Qt.Key_Up) {
            moveSelection(0, -1);
        } else if (event.key === Qt.Key_Down) {
            moveSelection(0, 1);
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

        interval: 320 + Math.max(root.pageBoxes.length, 6) * (root.staggerMs - 4)
        onTriggered: {
            root.currentPage = root.pendingPage;
            root.selectedIndex = 0;
            root.pageBoxes = root.buildPage(root.currentPage);
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
                color: Appearance.colors.colLayer1
                border.width: 2
                border.color: Appearance.colors.colPrimary

                RowLayout {
                    id: distroPillRow

                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        Layout.preferredWidth: 22
                        Layout.preferredHeight: 22
                        text: root.distroGlyph
                        color: Appearance.colors.colOnLayer1
                        font.family: Fonts.ui
                        font.pixelSize: 20
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    StyledText {
                        text: SystemIdentityService.distroName
                        font.pixelSize: Typography.bodyLarge.pixelSize
                        font.weight: Font.Medium
                        color: Appearance.colors.colOnLayer1
                    }
                }
            }

            Toolbar {
                anchors.centerIn: parent
                colBackground: Appearance.colors.colLayer1

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
                        containerColor: navBtn.toggled ? Appearance.colors.colPrimary : "transparent"
                        rippleColor: navBtn.toggled ? Appearance.colors.colOnPrimary :
                                                      Appearance.colors.colOnSurface
                        stateLayerColor: navBtn.toggled ? Appearance.colors.colOnPrimary :
                                                          Appearance.colors.colOnSurface
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
                                    color: navBtn.toggled ? Appearance.colors.colOnPrimary :
                                                            Appearance.colors.colOnLayer1
                                    fill: navBtn.toggled ? 1 : 0
                                }

                                StyledText {
                                    text: navBtn.modelData.name
                                    color: navBtn.toggled ? Appearance.colors.colOnPrimary :
                                                            Appearance.colors.colOnLayer1
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
                    color: Appearance.colors.colLayer1
                    border.width: searchInput.activeFocus ? 2 : 0
                    border.color: Appearance.colors.colPrimary

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
                                color: Appearance.colors.colOnLayer1
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
                        color: Appearance.colors.colOnLayer1
                        selectionColor: Appearance.colors.colPrimary
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
                            text: qsTr("Search settings")
                            color: Appearance.colors.colSubtext
                        }
                    }
                }

                RippleButton {
                    id: notificationsButton

                    implicitWidth: 44
                    implicitHeight: 44
                    buttonRadius: height / 2
                    containerColor: Appearance.colors.colLayer1
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
                            color: Appearance.colors.colOnLayer1
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
                    color: Appearance.colors.colPrimaryContainer

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
                        color: Appearance.colors.colOnPrimaryContainer
                    }
                }
            }
        }

        GridLayout {
            id: boxGrid

            Layout.fillWidth: true
            Layout.fillHeight: true
            // Only the pages that have not been ported yet fall back to the
            // placeholder grid; ported pages render through their own Loader.
            visible: !root.homeImplemented && !root.settingsImplemented && !root.wallpapersImplemented &&
                     !root.mediaImplemented && !root.themesImplemented
            columns: 4
            rowSpacing: 12
            columnSpacing: 12

            Repeater {
                id: boxRepeater

                model: root.pageBoxes

                delegate: DashboardCard {
                    id: boxDelegate

                    required property int index
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 1
                    Layout.rowSpan: boxDelegate.modelData.rowSpan
                    Layout.columnSpan: boxDelegate.modelData.colSpan

                    tint: boxDelegate.modelData.bg
                    pager: root
                    animIndex: boxDelegate.index
                    staggerMs: root.staggerMs
                    travelX: boxDelegate.modelData.travelX
                    travelY: boxDelegate.modelData.travelY

                    readonly property bool selected: root.selectedIndex === boxDelegate.index

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 4

                        MaterialSymbol {
                            Layout.alignment: Qt.AlignHCenter
                            text: boxDelegate.modelData.icon
                            iconSize: 32
                            color: boxDelegate.modelData.fg
                        }

                        StyledText {
                            Layout.alignment: Qt.AlignHCenter
                            text: qsTr("Card") + " " + (boxDelegate.index + 1)
                            color: boxDelegate.modelData.fg
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        radius: boxDelegate.cardRadius
                        color: "transparent"
                        border.width: boxDelegate.selected ? 3 : 0
                        border.color: Appearance.colors.colPrimary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.selectedIndex = boxDelegate.index;
                            root.forceActiveFocus();
                        }
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
            }
        }

        Loader {
            id: wallpapersPageLoader

            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: active
            active: root.wallpapersImplemented

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
                pager: root
                staggerMs: root.staggerMs
            }
        }
    }
}

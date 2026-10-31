import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window
import Quickshell
import Quickshell.Wayland
import qs.commons
import qs.services
import qs.ui
import qs.app

// Caelestia-flavoured master-detail shell (Nexus.qml, window mode): a
// two-zone frame — the left nav panel plus a 12px frame band share the
// surface-container-low fill, the centre stays clear for pages — with the
// close chip fused into the top-right corner exactly like the original
// blob chrome (same colour, so the fusion needs no blobs). Chrome only —
// routing, deep search and child windows stay on the API surface pinned
// by tests.
FloatingWindow {
    id: root

    property bool _wasShown: false
    property int currentPage: 0
    property int _lastPage: 0
    property real _animOffset: 0
    property string pendingPageSection: ""
    readonly property var pages: SpotlightCatalog.routes.filter(entry => entry.path.length === 1).map(entry
                                                                                                      => Object.assign(
                                                                                                             {}, entry,
                                                                                                             {
                                                                                                                 title: SpotlightCatalog.title(
                                                                                                                            entry.id),
                                                                                                                 sourceTitle:
                                                                                                                 entry.title,
                                                                                                                 description:
                                                                                                                 SpotlightCatalog.description(
                                                                                                                     entry.id)
                                                                                                             }))
    readonly property string currentRouteId: pages && pages[currentPage] ? pages[currentPage].id : ""
    property int searchRequestSerial: -1
    property var searchLeaf: null
    readonly property var searchPageAnchor: pageSearchAnchor
    readonly property real navPaneWidth: Math.min(NexusStyle.maxNavWidth, Math.round(root.width / 4))
    // A loaded page that renders its own NexusPageBase title takes over the
    // detail header; the interim route-title shim hides.
    readonly property bool pageRendersTitle: pageLoader.item && pageLoader.item.rendersPageTitle === true

    function prepareSearchTarget(entry, serial) {
        searchRequestSerial = serial;
        root.openPage(entry.path[0]);
        root.advanceSearchTarget(entry, serial);
    }

    function advanceSearchTarget(entry, serial) {
        if (searchRequestSerial !== serial)
            return "cancelled";
        if (pages[currentPage].id !== entry.path[0])
            return "cancelled";
        if (!pageLoader.ready || !pageLoader.item)
            return "loading";
        const page = pageLoader.item;
        const state = typeof page.openSearchPath === "function" ? page.openSearchPath(entry.path.slice(1),
                                                                                      serial) : "ready";
        searchLeaf = page.searchLeaf || page;
        return state;
    }

    SettingsSearchAnchor {
        id: pageSearchAnchor
        registerAnchor: false
        declaration: JSON.stringify({
                                        id: "page"
                                    })
        target: root.searchLeaf
        wholePage: true
    }

    signal popoutClosed

    function updatePageSource() {
        const target = root.pageSource(root.currentPage);
        if (pageLoader.source.toString() !== target.toString())
            pageLoader.source = target;
    }

    function showWindow() {
        switchAnim.stop();
        pageContainer.opacity = 1;
        pageContainer.anchors.topMargin = 0;
        pageContainer.anchors.bottomMargin = 0;
        root.updatePageSource();
        root._wasShown = true;
        root.visible = true;
    }

    function hideWindow() {
        if (root.visible) {
            switchAnim.stop();
            root.closeChildWindows();
            root.visible = false;
        }
    }

    function toggleWindow() {
        if (root.visible)
            root.hideWindow();
        else
            root.showWindow();
    }

    function pageSource(index) {
        if (index < 0 || index >= pages.length)
            return Qt.resolvedUrl("AccountPage.qml");

        return Qt.resolvedUrl(pages[index].source);
    }

    function openPage(pageId) {
        if (!pageId)
            return false;

        for (let index = 0; index < pages.length; ++index) {
            const p = pages[index];
            if (p.id === pageId || (p.aliases && p.aliases.includes(pageId))) {
                currentPage = index;
                return true;
            }
        }

        const targetRoute = SpotlightCatalog.route(pageId);
        if (targetRoute && targetRoute.path && targetRoute.path.length > 0) {
            const topId = targetRoute.path[0];
            for (let index = 0; index < pages.length; ++index) {
                if (pages[index].id === topId) {
                    currentPage = index;
                    return true;
                }
            }
        }

        if (pageId === "general") {
            const target = pages.findIndex(p => p.id === "bar");
            if (target >= 0) {
                currentPage = target;
                return true;
            }
        }
        return false;
    }

    function openPageSection(pageId, section) {
        root.pendingPageSection = section;
        if (!root.openPage(pageId)) {
            root.pendingPageSection = "";
            return false;
        }
        root.applyPendingPageSection();
        return true;
    }

    function applyPendingPageSection() {
        if (!root.pendingPageSection || !pageLoader.item)
            return;

        if (typeof pageLoader.item.openSection === "function") {
            const section = root.pendingPageSection;
            root.pendingPageSection = "";
            pageLoader.item.openSection(section);
        }
    }

    function closeChildWindows() {
        const page = pageLoader.item;
        if (page && typeof page.closeChildWindows === "function")
            page.closeChildWindows();
    }

    visible: false
    // Focused by name through ToplevelManager — SettingsBackend.focusWindow()
    // matches this exact title; keep it stable.
    title: "nyxuri-settings"
    // Caelestia Nexus proportions: 70% of the screen height at 16:9, floored
    // at 800x500 via the Math.max guards. (Never assign explicit size
    // minimums: Quickshell 0.3.2 collapses the window to the floor when they
    // are set — the 2026-10-25 width incident.)
    implicitHeight: Math.max(NexusStyle.minHeight, Math.round((root.screen ? root.screen.height : 900)
                                                              * NexusStyle.heightMult))
    implicitWidth: Math.max(NexusStyle.minWidth, Math.round(root.implicitHeight * NexusStyle.ratio))
    color: "transparent"
    Material.theme: PersonalizationConfig.themeMode === "light" ? Material.Light : Material.Dark
    Material.accent: Appearance.colors.colPrimary
    onVisibleChanged: {
        if (!root.visible && root._wasShown) {
            SettingsBackend.cancelSearch();
            root.closeChildWindows();
            root._wasShown = false;
            root.popoutClosed();
        }
    }
    onCurrentPageChanged: {
        if (SettingsBackend.searchTarget && !SettingsBackend.applyingSearch && searchRequestSerial
                === SettingsBackend.searchSerial)
            SettingsBackend.cancelSearch();
        root.closeChildWindows();
        SettingsBackend.retrySearch();
        if (root.visible && root._wasShown) {
            switchAnim.complete();
            // Direction-aware vertical slide (Caelestia Pages.qml): navigating
            // further down the list enters from below, going up enters from
            // above.
            root._animOffset = NexusStyle.padding.extraLarge * (root.currentPage > root._lastPage ? 1 : -1);
            switchAnim.restart();
        } else {
            root.updatePageSource();
        }
        root._lastPage = root.currentPage;
    }
    Component.onDestruction: root.closeChildWindows()

    Rectangle {
        id: outerBackground

        anchors.fill: parent
        radius: NexusStyle.rounding.large
        color: BlurService.backgroundColor(Appearance.m3colors.m3background)
    }

    CompositorBlurRegion {
        targetWindow: root
        backgroundItem: outerBackground
        radius: outerBackground.radius
    }

    Item {
        id: focusBoundary
        anchors.fill: parent

        function releaseInputFocus(position) {
            const input = focusBoundary.Window.activeFocusItem;
            if (!(input instanceof TextInput) && !(input instanceof TextEdit))
                return;
            if (input.contains(input.mapFromItem(focusBoundary, position)))
                return;
            // Clear the field's local focus as well as the window's active focus:
            // otherwise a nested FocusScope can restore the field immediately.
            input.focus = false;
            focusBoundary.forceActiveFocus(Qt.MouseFocusReason);
        }

        MouseArea {
            anchors.fill: parent
            z: 1000
            acceptedButtons: Qt.AllButtons
            // Inspect presses before page controls handle them, then let the
            // original press through for text selection, buttons and dragging.
            onPressed: mouse => {
                focusBoundary.releaseInputFocus(Qt.point(mouse.x, mouse.y));
                mouse.accepted = false;
            }
            onWheel: wheel => wheel.accepted = false
        }

        // Left nav zone: nav pane width plus its 16px margins, full height,
        // sharing the window's left corner rounding. Same fill as the frame
        // band and the close chip — the original fuses all three from one
        // blob colour.
        Rectangle {
            id: navZone

            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: root.navPaneWidth + NexusStyle.navMargin * 2
            topLeftRadius: NexusStyle.rounding.large
            bottomLeftRadius: NexusStyle.rounding.large
            color: Appearance.colors.colSurfaceContainerLow

            DragHandler {
                target: null
                acceptedButtons: Qt.LeftButton
                onActiveChanged: {
                    if (active)
                        root.startSystemMove();
                }
            }
        }

        NexusNavPane {
            id: navPane

            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: NexusStyle.navMargin
            width: root.navPaneWidth
            currentIndex: root.currentPage
            routes: root.pages
            onRouteActivated: index => root.currentPage = index
        }

        // Pages region: 16px clear of the frame band (28px from the window
        // edge) and 28px clear of the nav zone, exactly the original Pages
        // anchors. No close chip: the author dropped the original window
        // button (2026-10-25) — closing rides the mod+i toggle and the
        // compositor.
        Item {
            id: detailPane

            anchors.left: navZone.right
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: NexusStyle.frameBand + NexusStyle.chromeInset
            anchors.rightMargin: NexusStyle.frameBand + NexusStyle.chromeInset
            anchors.topMargin: NexusStyle.frameBand + NexusStyle.chromeInset
            anchors.bottomMargin: NexusStyle.frameBand + NexusStyle.chromeInset

            InlineStatusBanner {
                z: 200
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: Metrics.spacingM
                visible: SettingsBackend.searchError !== ""
                tone: "error"
                message: SettingsBackend.searchError
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: NexusStyle.spacing.large

                // Route-responsive detail title — the interim shim for old
                // pre-M3 pages. Pages built on NexusPageBase render their own
                // title and the shim steps aside. Doubles as the drag grip
                // the frameless window needs.
                Item {
                    Layout.fillWidth: true
                    visible: !root.pageRendersTitle
                    implicitHeight: root.pageRendersTitle ? 0 : routeTitle.implicitHeight

                    DragHandler {
                        target: null
                        acceptedButtons: Qt.LeftButton
                        onActiveChanged: {
                            if (active)
                                root.startSystemMove();
                        }
                    }

                    StyledText {
                        id: routeTitle

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.pages && root.pages[root.currentPage] ? root.pages[root.currentPage].title :
                                                                           ""
                        color: Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.titleLarge
                        font.weight: NexusStyle.font.titleWeight
                        elide: Text.ElideRight
                    }
                }

                // Page container: the whole pane swaps with the
                // direction-aware fade-and-settle animation below, the host
                // itself swaps layers instantly. The inner container is
                // anchor-managed so margins animate.
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Item {
                        id: pageContainer

                        anchors.fill: parent

                        SettingsPageHost {
                            id: pageLoader

                            anchors.fill: parent
                            animationsEnabled: false

                            property var parentModal: root

                            presentationActive: root.visible
                            Component.onCompleted: root.updatePageSource()
                            onLoaded: {
                                if (item && "parentModal" in item)
                                    item.parentModal = parentModal;

                                const page = item;
                                if (page && "presentationActive" in page)
                                    page.presentationActive = Qt.binding(function () {
                                        return root.visible && pageLoader.item === page;
                                    });

                                root.applyPendingPageSection();
                                SettingsBackend.retrySearch();
                            }
                        }

                        Connections {
                            function onNavigateRequested(pageId) {
                                root.openPage(pageId);
                            }

                            target: pageLoader.item
                            ignoreUnknownSignals: true
                        }
                    }
                }
            }
        }
    }

    SequentialAnimation {
        id: switchAnim

        alwaysRunToEnd: false

        NumberAnimation {
            target: pageContainer
            property: "opacity"
            to: 0
            duration: 80
            easing.type: Easing.OutCubic
        }
        ScriptAction {
            script: root.updatePageSource()
        }
        PropertyAction {
            target: pageContainer.anchors
            property: "topMargin"
            value: root._animOffset
        }
        PropertyAction {
            target: pageContainer.anchors
            property: "bottomMargin"
            value: -root._animOffset
        }
        ParallelAnimation {
            NumberAnimation {
                target: pageContainer
                property: "opacity"
                to: 1
                duration: 140
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: pageContainer.anchors
                property: "topMargin"
                to: 0
                duration: 140
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: pageContainer.anchors
                property: "bottomMargin"
                to: 0
                duration: 140
                easing.type: Easing.OutCubic
            }
        }
    }
}

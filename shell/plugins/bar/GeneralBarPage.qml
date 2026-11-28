import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Bar page (T3 M4 + B1 tab merge, restructured into the appearance/modules
// tab split): NexusPageBase scaffold + a thin composition of two
// self-contained sections (BarAppearanceSection = the bar's frame,
// BarModulesSection = what lives in it) and the routed island subpage.
// The island is a bar layout part, so its settings ride this page as the
// bar.island routed subpage. The drag-to-reorder machinery lives inside
// BarModulesSection (BarLaneSection + BarWidgetPickerPopup +
// QuickSettingsListCard + drag overlay); the overlay must not be a child of
// the scrolling content — NexusPageBase takes a single content child.
Item {
    id: root

    readonly property bool rendersPageTitle: true

    property int searchRequestSerial: -1
    readonly property var searchLeaf: currentSection === "overview" ? barPage.flickable : islandLoader.item ? (islandLoader.item.searchLeaf || islandLoader.item) : root

    property var parentModal: null
    property bool presentationActive: false
    property string currentSection: "overview"
    property string barTab: "appearance"
    // D4b: the per-instance widget editor targets one entry uid; the
    // subpage is internal (not a manifest route — it is meaningless
    // without a uid).
    property string widgetEditorUid: ""
    property string pendingIslandSection: ""

    function openSection(section) {
        const target = String(section || "overview");
        if (target === "island" || target === "island-clock") {
            root.pendingIslandSection = target === "island-clock" ? "island-clock" : "";
            root.currentSection = "island";
            if (root.pendingIslandSection.length > 0 && islandLoader.item && typeof islandLoader.item.openSection === "function") {
                const sub = root.pendingIslandSection;
                root.pendingIslandSection = "";
                islandLoader.item.openSection(sub);
            }
        } else {
            root.pendingIslandSection = "";
            root.currentSection = "overview";
        }
    }

    function openWidgetEditor(uid) {
        if (!uid)
            return;
        root.pendingIslandSection = "";
        root.widgetEditorUid = uid;
        root.currentSection = "widget";
    }

    function openSearchPath(path, serial) {
        const section = path.length ? path[0] : "";
        const island = section === "island" || section === "island-clock";
        if (searchRequestSerial !== serial) {
            searchRequestSerial = serial;
            // Anchor entries carry only the parent route path, so the tab
            // comes from the search target's id prefix; an island target
            // replaces the view outright.
            const targetId = SettingsSearch.searchTarget ? String(SettingsSearch.searchTarget.id) : "";
            root.barTab = targetId.indexOf("bar.modules.") === 0 ? "modules" : "appearance";
            root.currentSection = island ? "island" : "overview";
        }
        if (island !== (root.currentSection === "island"))
            return "cancelled";
        if (!island)
            return "ready";
        if (!(islandLoader.status === Loader.Ready) || !islandLoader.item)
            return "loading";
        return typeof islandLoader.item.openSearchPath === "function" ? islandLoader.item.openSearchPath(section === "island-clock" ? ["island-clock"] : [], serial) : "ready";
    }

    function showOverview() {
        root.pendingIslandSection = "";
        root.currentSection = "overview";
    }

    function showTab(tab) {
        const target = tab === "modules" ? "modules" : "appearance";
        if (root.barTab === target)
            return;
        root.barTab = target;
        barPage.flickable.contentY = barPage.flickable.originY;
    }

    function closeChildWindows() {
        if (islandLoader.item && typeof islandLoader.item.closeChildWindows === "function")
            islandLoader.item.closeChildWindows();
        root.showOverview();
    }

    onCurrentSectionChanged: {
        if (SettingsSearch.searchTarget && !SettingsSearch.applyingSearch && searchRequestSerial === SettingsSearch.searchSerial)
            SettingsSearch.cancelSearch();
        SettingsSearch.retrySearch();
    }

    Connections {
        target: PersonalizationConfig
        function onSelectedBarIdChanged() {
            if (root.currentSection === "widget" && !PersonalizationConfig.barEntryByUid(root.widgetEditorUid))
                root.showOverview();
        }
    }

    NexusPageBase {
        id: barPage

        anchors.fill: parent
        visible: root.currentSection === "overview"
        title: SpotlightCatalog.title("bar")

        Item {
            id: content

            width: parent.width
            implicitHeight: contentColumn.implicitHeight

            ColumnLayout {
                id: contentColumn

                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                width: barPage.cappedWidth
                spacing: NexusStyle.padding.extraSmall / 2

                BarManagerCard {
                    Layout.fillWidth: true
                    Layout.bottomMargin: NexusStyle.padding.small
                }

                StyledButtonGroup {
                    Layout.alignment: Qt.AlignLeft
                    Layout.bottomMargin: NexusStyle.padding.small
                    model: [
                        {
                            "label": I18n.tr("Appearance"),
                            "value": "appearance"
                        },
                        {
                            "label": I18n.tr("Modules"),
                            "value": "modules"
                        }
                    ]
                    currentValue: root.barTab
                    buttonHeight: 36
                    horizontalPadding: 16
                    textPixelSize: NexusStyle.font.bodyMedium
                    onValueSelected: value => root.showTab(String(value))
                }

                // Single stable layout child for the two tabs. The sections
                // themselves must NOT be layout children: this runtime never
                // assigns fill width to a layout child that was hidden at
                // first layout and revealed later (probe-verified), so the
                // tabs flip by visibility under a plain host — the same
                // shape the island subpage uses one level up. z keeps the
                // whole tab subtree above the page tail rows.
                Item {
                    id: tabHost

                    Layout.fillWidth: true
                    implicitHeight: root.barTab === "appearance" ? appearanceSection.implicitHeight : modulesSection.implicitHeight
                    z: 1

                    BarAppearanceSection {
                        id: appearanceSection

                        anchors.top: parent.top
                        width: parent.width
                        visible: root.barTab === "appearance"
                    }

                    BarModulesSection {
                        id: modulesSection

                        anchors.top: parent.top
                        width: parent.width
                        visible: root.barTab === "modules"
                        onIslandRequested: root.openSection("island")
                        onWidgetEditorRequested: entryUid => root.openWidgetEditor(entryUid)
                    }
                }
            }
        }
    }

    Loader {
        id: islandLoader

        onLoaded: {
            SettingsSearch.retrySearch();
            if (item && "parentModal" in item)
                item.parentModal = Qt.binding(() => root.parentModal);
            if (item && "presentationActive" in item)
                item.presentationActive = Qt.binding(() => root.presentationActive);
            if (item && item.backRequested !== undefined)
                item.backRequested.connect(root.showOverview);
            if (item && root.pendingIslandSection.length > 0 && typeof item.openSection === "function") {
                const sub = root.pendingIslandSection;
                root.pendingIslandSection = "";
                item.openSection(sub);
            }
        }

        anchors.fill: parent
        visible: root.currentSection === "island"
        source: {
            const route = SpotlightCatalog.route("bar.island");
            return root.currentSection === "island" && route && route.sourceUrl ? route.sourceUrl : "";
        }
    }

    // D4b per-instance widget editor: inline (same directory), instantiated
    // only while its section is active.
    BarWidgetPage {
        id: widgetEditor

        anchors.fill: parent
        visible: root.currentSection === "widget"
        widgetUid: root.currentSection === "widget" ? root.widgetEditorUid : ""
        onBackRequested: root.showOverview()
        onRouteRequested: section => root.openSection(section)
    }
}

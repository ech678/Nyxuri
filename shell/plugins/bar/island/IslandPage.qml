pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Island page shell (T3 M4 + B8.4): overview renders as a NexusPageBase over
// the M1 atom suite; the horizontal-clock subpage loads through the routed
// Loader and renders its own subpage title + back arrow. B8.4 retired the
// zero-consumer style/overlay/position/mouse/media/keyhole controls; what is
// left is the component gate, the optional idle satellite, the keyboard OSD
// toggles (now wired to KeyboardIndicators) and the horizontal clock editor.
Item {
    id: root

    readonly property bool rendersPageTitle: true

    // B1 tab merge: the island rides the Bar tab as a subpage, so the
    // scaffold's back arrow (isSubPage) must reach the hosting page through
    // this re-exposed signal — GeneralBarPage connects it to its overview.
    signal backRequested

    property int searchRequestSerial: -1
    readonly property var searchLeaf: currentSection === "overview" ? overviewPage.flickable : pageLoader.item ? (pageLoader.item.searchLeaf || pageLoader.item) : root
    function openSearchPath(path, serial) {
        const section = path.length ? path[0] : "overview";
        if (searchRequestSerial !== serial) {
            searchRequestSerial = serial;
            root.currentSection = section;
        }
        if (root.currentSection !== section)
            return "cancelled";
        if (section === "overview")
            return "ready";
        if (!(pageLoader.status === Loader.Ready) || !pageLoader.item)
            return "loading";
        return typeof pageLoader.item.openSearchPath === "function" ? pageLoader.item.openSearchPath(path.slice(1), serial) : "ready";
    }

    property var parentModal: null
    onCurrentSectionChanged: {
        if (SettingsSearch.searchTarget && !SettingsSearch.applyingSearch && searchRequestSerial === SettingsSearch.searchSerial)
            SettingsSearch.cancelSearch();
        SettingsSearch.retrySearch();
    }
    property string currentSection: "overview"

    function openSection(section) {
        root.currentSection = String(section || "overview");
    }

    function showOverview() {
        root.currentSection = "overview";
    }

    function closeChildWindows() {
        root.showOverview();
    }

    NexusPageBase {
        id: overviewPage

        anchors.fill: parent
        visible: root.currentSection === "overview"
        isSubPage: true
        title: SpotlightCatalog.title("bar.island")
        onBackRequested: root.backRequested()

        Item {
            id: overviewContent

            width: parent.width
            implicitHeight: overviewColumn.implicitHeight

            ColumnLayout {
                id: overviewColumn

                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                width: overviewPage.cappedWidth
                spacing: NexusStyle.padding.extraSmall / 2

                // Island visibility & idle satellite
                PreferenceHeader {
                    first: true
                    text: I18n.tr("Island")
                }

                PreferenceToggle {
                    id: enabledToggle

                    first: true
                    text: I18n.tr("Show Island")
                    checked: PersonalizationConfig.islandEnabled
                    onToggled: PersonalizationConfig.setIslandEnabled(checked)

                    SettingsSearchAnchor {
                        id: searchAnchor0
                        target: enabledToggle
                        anchorId: "bar.island.section.island-style"
                    }
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Satellite")
                    model: PersonalizationConfig.islandSatelliteOptions
                    currentValue: PersonalizationConfig.islandSatellite
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandSatellite(String(value))
                }

                // Keyboard indicators (iNiR panel/popup split)
                PreferenceHeader {
                    visible: KeyboardIndicators.ready
                    text: I18n.tr("Keyboard indicators")
                }

                PreferenceToggle {
                    id: panelMasterToggle

                    visible: KeyboardIndicators.ready
                    first: true
                    text: I18n.tr("Show panel indicators")
                    checked: PersonalizationConfig.keyboardShowPanel
                    onToggled: PersonalizationConfig.setKeyboardShowPanel(checked)

                    SettingsSearchAnchor {
                        id: searchAnchor1
                        target: panelMasterToggle
                        anchorId: "bar.island.section.keyboard-indicators"
                    }
                }

                PreferenceToggle {
                    visible: KeyboardIndicators.ready
                    enabled: PersonalizationConfig.keyboardShowPanel
                    text: I18n.tr("Show layout")
                    checked: PersonalizationConfig.keyboardPanelLayout
                    onToggled: PersonalizationConfig.setKeyboardPanelLayout(checked)
                }

                PreferenceToggle {
                    visible: KeyboardIndicators.ready
                    enabled: PersonalizationConfig.keyboardShowPanel
                    text: I18n.tr("Show Caps Lock")
                    checked: PersonalizationConfig.keyboardPanelCaps
                    onToggled: PersonalizationConfig.setKeyboardPanelCaps(checked)
                }

                PreferenceToggle {
                    visible: KeyboardIndicators.ready
                    enabled: PersonalizationConfig.keyboardShowPanel
                    text: I18n.tr("Show Num Lock")
                    checked: PersonalizationConfig.keyboardPanelNum
                    onToggled: PersonalizationConfig.setKeyboardPanelNum(checked)
                }

                PreferenceToggle {
                    visible: KeyboardIndicators.ready
                    text: I18n.tr("Show popup notifications")
                    checked: PersonalizationConfig.keyboardShowPopup
                    onToggled: PersonalizationConfig.setKeyboardShowPopup(checked)
                }

                PreferenceToggle {
                    visible: KeyboardIndicators.ready
                    enabled: PersonalizationConfig.keyboardShowPopup
                    text: I18n.tr("Layout changes")
                    checked: PersonalizationConfig.keyboardPopupLayout
                    onToggled: PersonalizationConfig.setKeyboardPopupLayout(checked)
                }

                PreferenceToggle {
                    visible: KeyboardIndicators.ready
                    enabled: PersonalizationConfig.keyboardShowPopup
                    text: I18n.tr("Caps Lock changes")
                    checked: PersonalizationConfig.keyboardPopupCaps
                    onToggled: PersonalizationConfig.setKeyboardPopupCaps(checked)
                }

                PreferenceToggle {
                    visible: KeyboardIndicators.ready
                    enabled: PersonalizationConfig.keyboardShowPopup
                    last: true
                    text: I18n.tr("Num Lock changes")
                    checked: PersonalizationConfig.keyboardPopupNum
                    onToggled: PersonalizationConfig.setKeyboardPopupNum(checked)
                }

                // Horizontal clock
                PreferenceHeader {
                    text: I18n.tr("Horizontal clock")
                }

                ConnectedRect {
                    id: clockPreviewCard

                    first: true
                    Layout.fillWidth: true
                    implicitHeight: clockPreview.implicitHeight + NexusStyle.padding.medium * 2

                    HorizontalClockPreview {
                        id: clockPreview

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.small
                        anchors.rightMargin: NexusStyle.padding.small
                        implicitHeight: Math.max(42, width * 42 / 220)
                    }

                    SettingsSearchAnchor {
                        id: searchAnchor2
                        target: clockPreviewCard
                        anchorId: "bar.island.section.horizontal-clock"
                    }
                }

                PreferenceToggle {
                    text: I18n.tr("Hide date")
                    checked: PersonalizationConfig.islandHideDate
                    onToggled: PersonalizationConfig.setIslandHideDate(checked)
                }

                PreferenceAction {
                    last: true
                    icon: "tune"
                    text: I18n.tr("Horizontal clock style")
                    subtext: I18n.tr("Font, digit positions, and colors")
                    onClicked: root.openSection("island-clock")
                }
            }
        }
    }

    Loader {
        id: pageLoader

        onLoaded: {
            SettingsSearch.retrySearch();
            if (item && "parentModal" in item)
                item.parentModal = Qt.binding(() => root.parentModal);
            if (item && item.backRequested !== undefined)
                item.backRequested.connect(root.showOverview);
        }

        anchors.fill: parent
        visible: root.currentSection !== "overview"
        source: {
            const route = SpotlightCatalog.route("bar." + root.currentSection);
            return route && route.sourceUrl ? route.sourceUrl : "";
        }
    }
}

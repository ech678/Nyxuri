pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.ui

// Island page shell (T3 M4): overview renders as a NexusPageBase over the
// M1 atom suite; the horizontal-clock subpage loads through the routed Loader
// and renders its own subpage title + back arrow, so the pre-M4 external
// subpage header is gone. Directory pickers and the long-bar drag overlay
// ride inside the page content — a root-level child would break the
// single-content-child contract of the Nexus scaffold.
Item {
    id: root

    readonly property bool rendersPageTitle: true

    // B1 tab merge: the island rides the Bar tab as a subpage, so the
    // scaffold's back arrow (isSubPage) must reach the hosting page through
    // this re-exposed signal — GeneralBarPage connects it to its overview.
    signal backRequested

    property int searchRequestSerial: -1
    readonly property var searchLeaf: currentSection === "overview" ? overviewPage.flickable :
                                                                      pageLoader.item ? (
                                                                                            pageLoader.item.searchLeaf
                                                                                            || pageLoader.item) :
                                                                                        root
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
        return typeof pageLoader.item.openSearchPath === "function" ? pageLoader.item.openSearchPath(
                                                                          path.slice(1), serial) : "ready";
    }

    property var parentModal: null
    onCurrentSectionChanged: {
        if (SettingsSearch.searchTarget && !SettingsSearch.applyingSearch && searchRequestSerial
                === SettingsSearch.searchSerial)
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

                // Island style
                PreferenceHeader {
                    first: true
                    text: I18n.tr("Island style")
                }

                PreferenceToggle {
                    id: floatingToggle

                    first: true
                    text: I18n.tr("Floating")
                    checked: PersonalizationConfig.islandOverlay
                    onToggled: PersonalizationConfig.setValue("islandOverlay", checked)

                    SettingsSearchAnchor {
                        id: searchAnchor0
                        target: floatingToggle
                        anchorId: "bar.island.section.island-style"
                    }
                }

                PreferenceSelect {
                    label: I18n.tr("Style")
                    model: PersonalizationConfig.islandStyles
                    currentValue: PersonalizationConfig.islandStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandStyle(value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Screen edge")
                    model: PersonalizationConfig.edgePositions
                    currentValue: PersonalizationConfig.islandPosition
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandPosition(String(value))
                }

                // Mouse actions
                PreferenceHeader {
                    text: I18n.tr("Mouse actions")
                }

                PreferenceSelect {
                    id: hoverSelect

                    first: true
                    label: I18n.tr("Hover")
                    model: PersonalizationConfig.availableIslandHoverActionOptions
                    currentValue: PersonalizationConfig.effectiveIslandHoverAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandAction("hover", value)

                    SettingsSearchAnchor {
                        id: searchAnchor1
                        target: hoverSelect
                        anchorId: "bar.island.section.mouse-actions"
                    }
                }

                PreferenceSlider {
                    label: I18n.tr("Hover open delay")
                    enabled: PersonalizationConfig.effectiveIslandHoverAction !== "none"
                    valueLabel: Math.round(PersonalizationConfig.islandHoverOpenDelay) + I18n.tr(" ms")
                    value: PersonalizationConfig.islandHoverOpenDelay
                    from: 0
                    to: 500
                    stepSize: 25
                    onMoved: value => PersonalizationConfig.setIslandHoverOpenDelay(Math.round(value))
                }

                PreferenceSlider {
                    label: I18n.tr("Hover close delay")
                    enabled: PersonalizationConfig.effectiveIslandHoverAction !== "none"
                    valueLabel: Math.round(PersonalizationConfig.islandHoverCloseDelay) + I18n.tr(" ms")
                    value: PersonalizationConfig.islandHoverCloseDelay
                    from: 0
                    to: 600
                    stepSize: 25
                    onMoved: value => PersonalizationConfig.setIslandHoverCloseDelay(Math.round(value))
                }

                PreferenceSelect {
                    label: I18n.tr("Left click")
                    model: PersonalizationConfig.islandActionOptions
                    currentValue: PersonalizationConfig.islandLeftClickAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandAction("left", value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Middle click")
                    model: PersonalizationConfig.islandActionOptions
                    currentValue: PersonalizationConfig.islandMiddleClickAction
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandAction("middle", value)
                }

                // Media controls
                PreferenceHeader {
                    text: I18n.tr("Media controls")
                }

                PreferenceSelect {
                    id: progressSelect

                    first: true
                    label: I18n.tr("Progress bar")
                    model: PersonalizationConfig.islandMediaProgressOptions
                    currentValue: PersonalizationConfig.islandMediaProgressStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandMediaProgressStyle(value)

                    SettingsSearchAnchor {
                        id: mediaSearchAnchor
                        target: progressSelect
                        anchorId: "bar.island.section.media-controls"
                    }
                }

                PreferenceSelect {
                    label: I18n.tr("Cover style")
                    model: PersonalizationConfig.islandMediaCoverOptions
                    currentValue: PersonalizationConfig.islandMediaCoverStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandMediaCoverStyle(value)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Colors")
                    model: PersonalizationConfig.islandMediaColorOptions
                    currentValue: PersonalizationConfig.islandMediaColorStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandMediaColorStyle(value)
                }

                // Keyboard indicators
                PreferenceHeader {
                    visible: KeyboardLockService.available
                    text: I18n.tr("Keyboard indicators")
                }

                PreferenceToggle {
                    id: capsLockToggle

                    visible: KeyboardLockService.available
                    first: true
                    text: I18n.tr("Caps Lock changes")
                    checked: PersonalizationConfig.islandCapsLockOsd
                    onToggled: PersonalizationConfig.setIslandCapsLockOsd(checked)

                    SettingsSearchAnchor {
                        id: extraSearchAnchor0
                        target: capsLockToggle
                        anchorId: "bar.island.section.keyboard-indicators"
                    }
                }

                PreferenceToggle {
                    visible: KeyboardLockService.available
                    last: true
                    text: I18n.tr("Num Lock changes")
                    checked: PersonalizationConfig.islandNumLockOsd
                    onToggled: PersonalizationConfig.setIslandNumLockOsd(checked)
                }

                // Keyhole
                PreferenceHeader {
                    text: I18n.tr("Keyhole")
                }

                PreferenceSelect {
                    id: keyholeCardSelect

                    first: true
                    last: true
                    label: I18n.tr("Card")
                    model: PersonalizationConfig.islandKeyholeCardOptions
                    currentValue: PersonalizationConfig.islandKeyholeCard
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setIslandKeyholeCard(value)

                    SettingsSearchAnchor {
                        id: extraSearchAnchor1
                        target: keyholeCardSelect
                        anchorId: "bar.island.section.keyhole"
                    }
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

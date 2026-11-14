import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Bar page (T3 M4 + B1 tab merge): NexusPageBase scaffold + M1 atom rows.
// B1: the island is a bar layout part, so its settings ride this tab as the
// bar.island routed subpage — the same switcher shape the island page itself
// uses for its horizontal-clock subpage. The drag-to-reorder component fields
// stay the sanctioned custom shape (SortableMultiSelectField +
// LayoutDragCoordinator overlay); the drag overlay must not be a child of the
// scrolling content — NexusPageBase takes a single content child.
Item {
    id: root

    readonly property bool rendersPageTitle: true

    property int searchRequestSerial: -1
    readonly property var searchLeaf: currentSection === "overview" ? barPage.flickable : islandLoader.item ? (islandLoader.item.searchLeaf || islandLoader.item) : root

    property var parentModal: null
    property bool presentationActive: false
    property string currentSection: "overview"

    function openSection(section) {
        const target = String(section || "overview");
        if (target === "island" || target === "island-clock") {
            root.currentSection = "island";
            if (target === "island-clock" && islandLoader.item && typeof islandLoader.item.openSection === "function")
                islandLoader.item.openSection("island-clock");
        } else {
            root.currentSection = "overview";
        }
    }

    function openSearchPath(path, serial) {
        const section = path.length ? path[0] : "overview";
        const island = section === "island" || section === "island-clock";
        if (searchRequestSerial !== serial) {
            searchRequestSerial = serial;
            // Both island routes land on the island section; the clock editor
            // is forwarded one level deeper by the island page itself.
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
        root.currentSection = "overview";
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

    readonly property bool horizontalBar: PersonalizationConfig.barPosition === "top" || PersonalizationConfig.barPosition === "bottom"

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

                // Position
                PreferenceHeader {
                    first: true
                    text: I18n.tr("Position")
                }

                PreferenceToggle {
                    id: floatingToggle

                    first: true
                    text: I18n.tr("Floating")
                    checked: PersonalizationConfig.barOverlay
                    onToggled: PersonalizationConfig.setValue("barOverlay", checked)

                    SettingsSearchAnchor {
                        id: searchAnchor0
                        target: floatingToggle
                        anchorId: "bar.section.position"
                    }
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Screen edge")
                    model: PersonalizationConfig.edgePositions
                    currentValue: PersonalizationConfig.barPosition
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarPosition(String(value))
                }

                // Style & Corner
                PreferenceHeader {
                    text: I18n.tr("Style")
                }

                PreferenceSelect {
                    first: true
                    label: I18n.tr("Corner style")
                    model: PersonalizationConfig.barCornerStyles
                    currentValue: PersonalizationConfig.barCornerStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarCornerStyle(Number(value))
                }

                PreferenceSelect {
                    label: I18n.tr("Borderless mode")
                    model: PersonalizationConfig.barBorderlessModes
                    currentValue: PersonalizationConfig.barBorderless
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarBorderless(String(value))
                }

                PreferenceSelect {
                    label: I18n.tr("Divider style")
                    model: PersonalizationConfig.barDividerStyles
                    currentValue: PersonalizationConfig.barDividerStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarDividerStyle(String(value))
                }

                PreferenceSelect {
                    label: I18n.tr("Group color")
                    model: PersonalizationConfig.barGroupColorOptions
                    currentValue: PersonalizationConfig.barGroupColor
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarGroupColor(String(value))
                }

                PreferenceSlider {
                    last: true
                    label: I18n.tr("Bar thickness")
                    value: PersonalizationConfig.barThickness
                    valueLabel: Math.round(PersonalizationConfig.barThickness) + " px"
                    from: 28
                    to: 56
                    stepSize: 2
                    onMoved: value => PersonalizationConfig.setBarThickness(Math.round(value))
                }

                // Workspaces
                PreferenceHeader {
                    text: I18n.tr("Workspaces")
                }

                PreferenceToggle {
                    first: true
                    text: I18n.tr("Show app icons")
                    checked: PersonalizationConfig.barShowAppIcons
                    onToggled: PersonalizationConfig.setBarShowAppIcons(checked)
                }

                PreferenceToggle {
                    text: I18n.tr("Always show numbers")
                    checked: PersonalizationConfig.barAlwaysShowNumbers
                    onToggled: PersonalizationConfig.setBarAlwaysShowNumbers(checked)
                }

                PreferenceSelect {
                    last: true
                    label: I18n.tr("Indicator style")
                    model: PersonalizationConfig.barWorkspaceIndicatorStyles
                    currentValue: PersonalizationConfig.barWorkspaceIndicatorStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarWorkspaceIndicatorStyle(String(value))
                }

                // Components
                PreferenceHeader {
                    text: I18n.tr("Components")
                }

                StyledText {
                    Layout.fillWidth: true
                    Layout.leftMargin: NexusStyle.padding.extraSmall
                    Layout.rightMargin: NexusStyle.padding.extraSmall
                    Layout.bottomMargin: NexusStyle.padding.extraSmall
                    text: I18n.tr("Drag widgets between lanes to arrange the bar")
                    color: Appearance.m3colors.m3onSurfaceVariant
                    font.pixelSize: NexusStyle.font.bodySmall
                    wrapMode: Text.Wrap
                }

                PreferenceToggle {
                    id: namesToggle

                    first: true
                    text: I18n.tr("Show device names")
                    checked: PersonalizationConfig.barShowNames
                    onToggled: PersonalizationConfig.setBarShowNames(checked)

                    SettingsSearchAnchor {
                        id: searchAnchor1
                        target: namesToggle
                        anchorId: "bar.section.components"
                    }
                }

                PreferenceToggle {
                    text: I18n.tr("Show numeric values")
                    checked: PersonalizationConfig.barShowValues
                    onToggled: PersonalizationConfig.setBarShowValues(checked)
                }

                ConnectedRect {
                    id: leadingZoneRow

                    Layout.fillWidth: true
                    implicitHeight: Math.max(zoneLeadingLabel.implicitHeight, leadingField.implicitHeight) + NexusStyle.padding.medium * 2

                    RowLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.largeIncreased
                        anchors.rightMargin: NexusStyle.padding.largeIncreased
                        spacing: NexusStyle.padding.small

                        StyledText {
                            id: zoneLeadingLabel

                            text: root.horizontalBar ? I18n.tr("Left") : I18n.tr("Top")
                            color: Appearance.m3colors.m3onSurface
                            font.pixelSize: NexusStyle.font.bodyMedium
                        }

                        SortableMultiSelectField {
                            id: leadingField

                            Layout.fillWidth: true
                            values: PersonalizationConfig.barLayoutLeft
                            options: PersonalizationConfig.barComponentOptions
                            zone: "left"
                            dragCoordinator: dragCoordinator
                            onToggled: componentId => PersonalizationConfig.toggleBarComponent(componentId, zone)
                            onRemoved: componentId => PersonalizationConfig.removeBarComponent(componentId)
                        }
                    }
                }

                ConnectedRect {
                    id: middleZoneRow

                    Layout.fillWidth: true
                    implicitHeight: Math.max(zoneMiddleLabel.implicitHeight, middleField.implicitHeight) + NexusStyle.padding.medium * 2

                    RowLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.largeIncreased
                        anchors.rightMargin: NexusStyle.padding.largeIncreased
                        spacing: NexusStyle.padding.small

                        StyledText {
                            id: zoneMiddleLabel

                            text: I18n.tr("Center")
                            color: Appearance.m3colors.m3onSurface
                            font.pixelSize: NexusStyle.font.bodyMedium
                        }

                        SortableMultiSelectField {
                            id: middleField

                            Layout.fillWidth: true
                            values: PersonalizationConfig.barLayoutMiddle
                            options: PersonalizationConfig.barComponentOptions
                            zone: "middle"
                            dragCoordinator: dragCoordinator
                            onToggled: componentId => PersonalizationConfig.toggleBarComponent(componentId, zone)
                            onRemoved: componentId => PersonalizationConfig.removeBarComponent(componentId)
                        }
                    }
                }

                ConnectedRect {
                    id: trailingZoneRow

                    Layout.fillWidth: true
                    implicitHeight: Math.max(zoneTrailingLabel.implicitHeight, trailingField.implicitHeight) + NexusStyle.padding.medium * 2

                    RowLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.largeIncreased
                        anchors.rightMargin: NexusStyle.padding.largeIncreased
                        spacing: NexusStyle.padding.small

                        StyledText {
                            id: zoneTrailingLabel

                            text: root.horizontalBar ? I18n.tr("Right") : I18n.tr("Bottom")
                            color: Appearance.m3colors.m3onSurface
                            font.pixelSize: NexusStyle.font.bodyMedium
                        }

                        SortableMultiSelectField {
                            id: trailingField

                            Layout.fillWidth: true
                            values: PersonalizationConfig.barLayoutRight
                            options: PersonalizationConfig.barComponentOptions
                            zone: "right"
                            dragCoordinator: dragCoordinator
                            onToggled: componentId => PersonalizationConfig.toggleBarComponent(componentId, zone)
                            onRemoved: componentId => PersonalizationConfig.removeBarComponent(componentId)
                        }
                    }
                }

                ConnectedRect {
                    id: quickSettingsCard

                    Layout.fillWidth: true
                    implicitHeight: quickSettingsColumn.implicitHeight + NexusStyle.padding.medium * 2

                    ColumnLayout {
                        id: quickSettingsColumn

                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: NexusStyle.padding.largeIncreased
                        anchors.rightMargin: NexusStyle.padding.largeIncreased
                        spacing: NexusStyle.padding.small

                        StyledText {
                            Layout.fillWidth: true
                            text: I18n.tr("Quick settings widgets")
                            color: Appearance.m3colors.m3onSurface
                            font.pixelSize: NexusStyle.font.bodyMedium
                            elide: Text.ElideRight
                        }

                        SortableMultiSelectField {
                            id: quickSettingsField

                            Layout.fillWidth: true
                            values: PersonalizationConfig.quickSettingsComponents
                            options: PersonalizationConfig.quickSettingsComponentOptions
                            zone: "quickSettings"
                            dragCoordinator: quickSettingsDragCoordinator
                            onToggled: componentId => PersonalizationConfig.toggleQuickSettingsComponent(componentId)
                            onRemoved: componentId => PersonalizationConfig.removeQuickSettingsComponent(componentId)
                        }
                    }
                }

                // Island (B1: the island is a bar layout part — one tab)
                PreferenceHeader {
                    text: I18n.tr("Island")
                }

                PreferenceAction {
                    last: true
                    icon: "toggle_off"
                    text: I18n.tr("Island settings")
                    subtext: I18n.tr("Style, clock, and media controls")
                    onClicked: root.openSection("island")
                }
            }

            LayoutDragCoordinator {
                id: dragCoordinator

                anchors.fill: parent
                z: 1000
                fields: [leadingField, middleField, trailingField]
                onDropped: (componentId, targetZone, targetIndex) => PersonalizationConfig.moveBarComponent(componentId, targetZone, targetIndex)
            }

            LayoutDragCoordinator {
                id: quickSettingsDragCoordinator

                anchors.fill: parent
                z: 1001
                fields: [quickSettingsField]
                onDropped: (componentId, targetZone, targetIndex) => PersonalizationConfig.moveQuickSettingsComponent(componentId, targetIndex)
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
        }

        anchors.fill: parent
        visible: root.currentSection === "island"
        source: {
            const route = SpotlightCatalog.route("bar.island");
            return root.currentSection === "island" && route && route.sourceUrl ? route.sourceUrl : "";
        }
    }
}

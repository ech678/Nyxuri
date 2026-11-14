import QtQuick
import QtQuick.Layouts
import Quickshell
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
    readonly property var detectedScreens: Quickshell.screens

    // B9.7 screen filter toggle with end4's collapse rule: when every known
    // screen is selected, the list collapses to empty (= all screens).
    function toggleBarScreen(screenName, on) {
        const allNames = root.detectedScreens.map(screen => screen?.name ?? "").filter(name => name.length > 0);
        let list = PersonalizationConfig.barScreenList.length === 0 ? allNames.slice() : PersonalizationConfig.barScreenList.slice();
        if (on) {
            if (!list.includes(screenName))
                list.push(screenName);
        } else {
            list = list.filter(name => name !== screenName);
        }
        PersonalizationConfig.setValue("barScreenList", list.length === allNames.length ? [] : list);
    }

    // end4 `isUsed`: widget-scoped setting rows only render while their
    // widget actually sits in a lane.
    function layoutUses(componentId) {
        return PersonalizationConfig.barLayoutLeft.includes(componentId) || PersonalizationConfig.barLayoutMiddle.includes(componentId) || PersonalizationConfig.barLayoutRight.includes(componentId);
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

                // Position
                PreferenceHeader {
                    first: true
                    text: I18n.tr("Position")
                }

                PreferenceSelect {
                    id: edgeSelect

                    first: true
                    last: true
                    label: I18n.tr("Screen edge")
                    model: PersonalizationConfig.edgePositions
                    currentValue: PersonalizationConfig.barPosition
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarPosition(String(value))

                    SettingsSearchAnchor {
                        id: searchAnchor0
                        target: edgeSelect
                        anchorId: "bar.section.position"
                    }
                }

                // B9.5 outer margins: separate from the internal lane inset
                // (ROADMAP B-9). 0 keeps end4's edge-flush baseline.
                PreferenceHeader {
                    text: I18n.tr("Outer margins")
                }

                PreferenceSlider {
                    first: true
                    label: I18n.tr("Screen edge margin")
                    value: PersonalizationConfig.barEdgeMargin
                    valueLabel: Math.round(PersonalizationConfig.barEdgeMargin) + " px"
                    from: 0
                    to: 48
                    stepSize: 2
                    onMoved: value => PersonalizationConfig.setBarEdgeMargin(Math.round(value))
                }

                PreferenceSlider {
                    last: true
                    label: I18n.tr("Bar end margin")
                    value: PersonalizationConfig.barSideMargin
                    valueLabel: Math.round(PersonalizationConfig.barSideMargin) + " px"
                    from: 0
                    to: 96
                    stepSize: 2
                    onMoved: value => PersonalizationConfig.setBarSideMargin(Math.round(value))
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

                // end4 BarConfig: the space divider's width only exists for
                // that style, so the row hides instead of idling.
                PreferenceSlider {
                    visible: PersonalizationConfig.barDividerStyle === "space"
                    label: I18n.tr("Space width")
                    value: PersonalizationConfig.barDividerSpacing
                    valueLabel: Math.round(PersonalizationConfig.barDividerSpacing) + " px"
                    from: 4
                    to: 400
                    stepSize: 2
                    onMoved: value => PersonalizationConfig.setValue("barDividerSpacing", Math.round(value / 2) * 2)
                }

                // end4 `bar.showBackground`: the frame/pill background of
                // Hug and Float. Other styles decide their own background
                // downstream, so the row idles there (end4 disables it too).
                PreferenceToggle {
                    text: I18n.tr("Show background")
                    enabled: PersonalizationConfig.barCornerStyle === 0 || PersonalizationConfig.barCornerStyle === 1
                    checked: PersonalizationConfig.barShowBackground
                    onToggled: PersonalizationConfig.setValue("barShowBackground", checked)
                }

                PreferenceToggle {
                    text: I18n.tr("Autohide")
                    checked: PersonalizationConfig.barAutoHide
                    onToggled: PersonalizationConfig.setValue("barAutoHide", checked)
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
                    visible: root.horizontalBar
                    label: I18n.tr("Bar thickness")
                    value: PersonalizationConfig.barThickness
                    valueLabel: Math.round(PersonalizationConfig.barThickness) + " px"
                    from: 28
                    to: 56
                    stepSize: 2
                    onMoved: value => PersonalizationConfig.setBarThickness(Math.round(value))
                }

                // B9.4: the vertical thickness is its own axis. Only the one
                // that matches the active screen edge is offered, so neither
                // slider can become a dead key.
                PreferenceSlider {
                    last: true
                    visible: !root.horizontalBar
                    label: I18n.tr("Vertical bar thickness")
                    value: PersonalizationConfig.barVerticalThickness
                    valueLabel: Math.round(PersonalizationConfig.barVerticalThickness) + " px"
                    from: 28
                    to: 64
                    stepSize: 2
                    onMoved: value => PersonalizationConfig.setBarVerticalThickness(Math.round(value))
                }

                // B9.7 screen filter (end4 BarConfig "Screens"): an empty
                // list means every screen; the collapse rule lives in the
                // page because it needs the live screen set.
                PreferenceHeader {
                    visible: root.detectedScreens.length > 1
                    text: I18n.tr("Screens")
                }

                PreferenceToggle {
                    visible: root.detectedScreens.length > 1
                    first: true
                    text: I18n.tr("All screens")
                    checked: PersonalizationConfig.barScreenList.length === 0
                    onToggled: PersonalizationConfig.setValue("barScreenList", [])
                }

                Repeater {
                    visible: root.detectedScreens.length > 1
                    model: root.detectedScreens

                    PreferenceToggle {
                        required property var modelData
                        required property int index

                        readonly property string screenName: modelData?.name ?? ""

                        visible: root.detectedScreens.length > 1 && screenName.length > 0
                        last: index === root.detectedScreens.length - 1
                        text: screenName
                        checked: PersonalizationConfig.barScreenList.length === 0 || PersonalizationConfig.barScreenList.includes(screenName)
                        onToggled: root.toggleBarScreen(screenName, !checked)
                    }
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
                    label: I18n.tr("Indicator style")
                    model: PersonalizationConfig.barWorkspaceIndicatorStyles
                    currentValue: PersonalizationConfig.barWorkspaceIndicatorStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarWorkspaceIndicatorStyle(String(value))
                }

                PreferenceSelect {
                    label: I18n.tr("Workspace style")
                    model: PersonalizationConfig.barWorkspaceStyles
                    currentValue: PersonalizationConfig.barWorkspaceStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarWorkspaceStyle(String(value))
                }

                // end4 "Numbers style" (B9.7): only the default skin renders
                // number labels, so the preset hides elsewhere.
                PreferenceSelect {
                    visible: PersonalizationConfig.barWorkspaceStyle === "default"
                    label: I18n.tr("Numbers style")
                    model: PersonalizationConfig.barWorkspaceNumberStyles
                    currentValue: PersonalizationConfig.barWorkspaceNumberStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setBarWorkspaceNumberStyle(String(value))
                }

                PreferenceSlider {
                    last: true
                    label: I18n.tr("Shown workspaces")
                    value: PersonalizationConfig.barWorkspaceShown
                    valueLabel: Math.round(PersonalizationConfig.barWorkspaceShown) + ""
                    from: 1
                    to: 50
                    stepSize: 1
                    onMoved: value => PersonalizationConfig.setBarWorkspaceShown(Math.round(value))
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

                StyledText {
                    Layout.fillWidth: true
                    Layout.leftMargin: NexusStyle.padding.extraSmall
                    Layout.rightMargin: NexusStyle.padding.extraSmall
                    Layout.bottomMargin: NexusStyle.padding.extraSmall
                    visible: !root.horizontalBar
                    text: I18n.tr("The island stays hidden on a vertical bar for now")
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

                // end4 widget-scoped sections (B9.7): the Utility buttons and
                // Resources rows only exist while their widget is in a lane —
                // otherwise they would be honest-looking dead switches.
                PreferenceHeader {
                    visible: root.layoutUses("utilButtons")
                    text: I18n.tr("Utility buttons")
                }

                PreferenceToggle {
                    visible: root.layoutUses("utilButtons")
                    first: true
                    text: I18n.tr("Screen snip")
                    checked: PersonalizationConfig.barShowScreenSnip
                    onToggled: PersonalizationConfig.setValue("barShowScreenSnip", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("utilButtons")
                    text: I18n.tr("Color picker")
                    checked: PersonalizationConfig.barShowColorPicker
                    onToggled: PersonalizationConfig.setValue("barShowColorPicker", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("utilButtons")
                    text: I18n.tr("On-screen keyboard")
                    checked: PersonalizationConfig.barShowKeyboardToggle
                    onToggled: PersonalizationConfig.setValue("barShowKeyboardToggle", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("utilButtons")
                    text: I18n.tr("Mic toggle")
                    checked: PersonalizationConfig.barShowMicToggle
                    onToggled: PersonalizationConfig.setValue("barShowMicToggle", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("utilButtons")
                    text: I18n.tr("Wallpaper toggle")
                    checked: PersonalizationConfig.barShowWallpaperToggle
                    onToggled: PersonalizationConfig.setValue("barShowWallpaperToggle", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("utilButtons")
                    text: I18n.tr("Dark/Light toggle")
                    checked: PersonalizationConfig.barShowDarkModeToggle
                    onToggled: PersonalizationConfig.setValue("barShowDarkModeToggle", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("utilButtons")
                    last: true
                    text: I18n.tr("Performance profile")
                    checked: PersonalizationConfig.barShowPerformanceProfile
                    onToggled: PersonalizationConfig.setValue("barShowPerformanceProfile", checked)
                }

                PreferenceHeader {
                    visible: root.layoutUses("systemMonitor")
                    text: I18n.tr("Resources")
                }

                PreferenceToggle {
                    visible: root.layoutUses("systemMonitor")
                    first: true
                    text: I18n.tr("CPU")
                    checked: PersonalizationConfig.barShowCpu
                    onToggled: PersonalizationConfig.setValue("barShowCpu", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("systemMonitor")
                    text: I18n.tr("CPU temperature")
                    checked: PersonalizationConfig.barShowCpuTemp
                    onToggled: PersonalizationConfig.setValue("barShowCpuTemp", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("systemMonitor")
                    text: I18n.tr("RAM")
                    checked: PersonalizationConfig.barShowRam
                    onToggled: PersonalizationConfig.setValue("barShowRam", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("systemMonitor")
                    text: I18n.tr("Disk")
                    checked: PersonalizationConfig.barShowDisk
                    onToggled: PersonalizationConfig.setValue("barShowDisk", checked)
                }

                PreferenceToggle {
                    visible: root.layoutUses("systemMonitor")
                    text: I18n.tr("Swap")
                    checked: PersonalizationConfig.barShowSwap
                    onToggled: PersonalizationConfig.setValue("barShowSwap", checked)
                }

                PreferenceSelect {
                    visible: root.layoutUses("systemMonitor")
                    label: I18n.tr("Icon style")
                    model: PersonalizationConfig.barResourceStyles
                    currentValue: PersonalizationConfig.barResourceStyle
                    inputRegionService: PopupInputRegionService
                    onSelected: value => PersonalizationConfig.setValue("barResourceStyle", String(value))
                }

                PreferenceToggle {
                    visible: root.layoutUses("systemMonitor")
                    last: true
                    text: I18n.tr("Show percentage")
                    checked: PersonalizationConfig.barResourceShowValue
                    onToggled: PersonalizationConfig.setValue("barResourceShowValue", checked)
                }

                // Tray (B9.1): the tray widget's own contract — pinned items
                // keep a slot, everything else lives behind the overflow arrow.
                PreferenceHeader {
                    text: I18n.tr("Tray")
                }

                PreferenceToggle {
                    id: trayTintToggle

                    first: true
                    text: I18n.tr("Tint icons")
                    checked: PersonalizationConfig.barTrayMonochromeIcons
                    onToggled: PersonalizationConfig.setValue("barTrayMonochromeIcons", checked)

                    SettingsSearchAnchor {
                        id: searchAnchorTray
                        target: trayTintToggle
                        anchorId: "bar.section.tray"
                    }
                }

                PreferenceToggle {
                    text: I18n.tr("Hide passive items")
                    checked: PersonalizationConfig.barTrayFilterPassive
                    onToggled: PersonalizationConfig.setValue("barTrayFilterPassive", checked)
                }

                PreferenceToggle {
                    text: I18n.tr("Show item id in tooltip")
                    checked: PersonalizationConfig.barTrayShowItemId
                    onToggled: PersonalizationConfig.setValue("barTrayShowItemId", checked)
                }

                PreferenceToggle {
                    text: I18n.tr("Pin new items by default")
                    checked: PersonalizationConfig.barTrayInvertPinnedItems
                    onToggled: PersonalizationConfig.setValue("barTrayInvertPinnedItems", checked)
                }

                PreferenceAction {
                    last: true
                    icon: "restart_alt"
                    text: I18n.tr("Reset pin list")
                    subtext: I18n.tr("Every item returns to the bar")
                    onClicked: PersonalizationConfig.setBarTrayPinnedItems([])
                }

                // Island (B1: the island is a bar layout part — one tab)
                PreferenceHeader {
                    text: I18n.tr("Island")
                }

                PreferenceAction {
                    last: true
                    icon: "toggle_off"
                    text: I18n.tr("Island settings")
                    subtext: I18n.tr("Visibility, satellite, indicators, and clock")
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

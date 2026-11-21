import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Modules tab of the Bar page: what lives IN the bar. Wraps the drag card
// (BarComponentsCard) plus the widget-scoped groups; the two drag
// coordinators anchor to this wrapper so the drag ghost paints above the
// groups below the card. Widget-scoped rows follow end4's `isUsed` gate —
// they only render while their widget actually sits in a lane. Split out
// of the pre-tab GeneralBarPage monolith; anchors ride with their rows
// (bar.modules.*).
Item {
    id: root

    // The island is a bar layout part, so its entry row rides this tab; the
    // page owns the bar.island route, so the button asks instead of routing.
    signal islandRequested

    // end4 `isUsed`: widget-scoped setting rows only render while their
    // widget actually sits in a lane.
    function layoutUses(componentId) {
        return PersonalizationConfig.barLayoutLeft.includes(componentId) || PersonalizationConfig.barLayoutMiddle.includes(componentId) || PersonalizationConfig.barLayoutRight.includes(componentId);
    }

    // Above the tab-host default so the coordinator ghosts paint over the
    // island entry rows one level up (the tab host itself carries the z).
    z: 1
    implicitHeight: modulesColumn.implicitHeight

    ColumnLayout {
        id: modulesColumn

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: parent.width
        spacing: NexusStyle.padding.extraSmall / 2

        BarComponentsCard {
            id: componentsCard

            zoneCoordinator: dragCoordinator
            quickSettingsCoordinator: quickSettingsDragCoordinator
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
                anchorId: "bar.modules.tray"
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

        // Island (B1: the island is a bar layout part — one page). Rides the
        // Modules tab because it is content of the bar, not its frame.
        PreferenceHeader {
            text: I18n.tr("Island")
        }

        PreferenceAction {
            first: true
            last: true
            icon: "toggle_off"
            text: I18n.tr("Island settings")
            subtext: I18n.tr("Visibility, satellite, indicators, and clock")
            onClicked: root.islandRequested()
        }
    }

    LayoutDragCoordinator {
        id: dragCoordinator

        anchors.fill: parent
        z: 1000
        fields: [componentsCard.leadingField, componentsCard.middleField, componentsCard.trailingField]
        onDropped: (componentId, targetZone, targetIndex) => PersonalizationConfig.moveBarComponent(componentId, targetZone, targetIndex)
    }

    LayoutDragCoordinator {
        id: quickSettingsDragCoordinator

        anchors.fill: parent
        z: 1001
        fields: [componentsCard.quickSettingsField]
        onDropped: (componentId, targetZone, targetIndex) => PersonalizationConfig.moveQuickSettingsComponent(componentId, targetIndex)
    }
}

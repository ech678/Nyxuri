import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import "../../services/BarDefaults.js" as BarDefaults
import "../../services/DensityPresets.js" as DensityPresets

// Appearance tab of the Bar page: the bar's frame — position, outer
// margins, the screen filter, style, and the D4c fine-grained axes
// (spacing/padding/scale/shape/surface effects). Wrapped in PreferenceGroup
// for dynamic first/last rounding across conditional rows, with row-level and
// page-level reset affordances (D4e e4).
ColumnLayout {
    id: root

    readonly property bool horizontalBar: PersonalizationConfig.barPosition === "top" || PersonalizationConfig.barPosition === "bottom"
    readonly property var detectedScreens: Quickshell.screens
    readonly property var axes: PersonalizationConfig.barAxes
    readonly property bool axesModified: PersonalizationConfig.barAxesModified(root.axes)

    readonly property string densityLevel: DensityPresets.currentLevel("bar", root.axes)
    readonly property var densityOptions: [
        {
            "value": "spacious",
            "label": I18n.tr("Spacious")
        },
        {
            "value": "comfortable",
            "label": I18n.tr("Comfortable")
        },
        {
            "value": "compact",
            "label": I18n.tr("Compact")
        },
        {
            "value": "dense",
            "label": I18n.tr("Dense")
        }
    ]

    readonly property var edgeChoices: [
        {
            key: "top",
            label: I18n.tr("Top"),
            preview: "top"
        },
        {
            key: "bottom",
            label: I18n.tr("Bottom"),
            preview: "bottom"
        },
        {
            key: "left",
            label: I18n.tr("Left"),
            preview: "left"
        },
        {
            key: "right",
            label: I18n.tr("Right"),
            preview: "right"
        }
    ]

    readonly property var surfaceColorOptions: [
        {
            "value": "default",
            "label": I18n.tr("Default")
        },
        {
            "value": "layer0",
            "label": I18n.tr("Background")
        },
        {
            "value": "layer1",
            "label": I18n.tr("Surface layer")
        },
        {
            "value": "surfaceContainer",
            "label": I18n.tr("Surface container")
        },
        {
            "value": "primaryContainer",
            "label": I18n.tr("Primary container")
        },
        {
            "value": "secondaryContainer",
            "label": I18n.tr("Secondary container")
        }
    ]

    function sentinelLabel(value): string {
        return value < 0 ? I18n.tr("Auto") : Math.round(value) + " px";
    }

    function toggleBarScreen(screenName, on) {
        const allNames = root.detectedScreens.map(screen => screen?.name ?? "").filter(name => name.length > 0);
        let list = PersonalizationConfig.barScreenList.length === 0 ? allNames.slice() : PersonalizationConfig.barScreenList.slice();
        if (on) {
            if (!list.includes(screenName))
                list.push(screenName);
        } else {
            list = list.filter(name => name !== screenName);
        }
        PersonalizationConfig.setBarScreenList(list.length === allNames.length ? [] : list);
    }

    spacing: NexusStyle.padding.extraSmall / 2

    // Layout
    PreferenceHeader {
        first: true
        text: I18n.tr("Layout")
        showReset: root.axesModified
        resetText: I18n.tr("Reset bar appearance")
        onResetRequested: PersonalizationConfig.resetBarAxes()
    }

    PreferenceGroup {
        PreferenceVisualPicker {
            id: edgePicker

            previewMode: "edge"
            choices: root.edgeChoices
            selectedKey: PersonalizationConfig.barPosition
            onSelected: key => PersonalizationConfig.setBarPosition(key)

            SettingsSearchAnchor {
                id: searchAnchorPosition

                target: edgePicker
                anchorId: "bar.appearance.position"
            }
        }

        PreferenceSlider {
            label: I18n.tr("Screen edge margin")
            value: PersonalizationConfig.barEdgeMargin
            valueLabel: Math.round(PersonalizationConfig.barEdgeMargin) + " px"
            from: 0
            to: 48
            stepSize: 2
            modified: PersonalizationConfig.barEdgeMargin !== BarDefaults.DEFAULTS.edgeMargin
            onMoved: value => PersonalizationConfig.setBarEdgeMargin(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarEdgeMargin(BarDefaults.DEFAULTS.edgeMargin)
        }

        PreferenceSlider {
            label: I18n.tr("Bar end margin")
            value: PersonalizationConfig.barSideMargin
            valueLabel: Math.round(PersonalizationConfig.barSideMargin) + " px"
            from: 0
            to: 96
            stepSize: 2
            modified: PersonalizationConfig.barSideMargin !== BarDefaults.DEFAULTS.sideMargin
            onMoved: value => PersonalizationConfig.setBarSideMargin(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarSideMargin(BarDefaults.DEFAULTS.sideMargin)
        }

        PreferenceSlider {
            label: I18n.tr("Bar end margin (%)")
            value: root.axes.sideMarginPercent
            valueLabel: root.axes.sideMarginPercent <= 0 ? I18n.tr("Off") : root.axes.sideMarginPercent + " %"
            from: 0
            to: 49
            stepSize: 1
            modified: root.axes.sideMarginPercent !== BarDefaults.DEFAULTS.sideMarginPercent
            onMoved: value => PersonalizationConfig.setBarSideMarginPercent(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarSideMarginPercent(BarDefaults.DEFAULTS.sideMarginPercent)
        }

        PreferenceSlider {
            label: I18n.tr("Widget spacing")
            value: root.axes.spacing
            valueLabel: root.sentinelLabel(root.axes.spacing)
            from: -1
            to: 64
            stepSize: 1
            modified: root.axes.spacing !== BarDefaults.DEFAULTS.spacing
            onMoved: value => PersonalizationConfig.setBarSpacing(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarSpacing(-1)
        }

        PreferenceSlider {
            label: I18n.tr("Lane inset")
            value: root.axes.innerPadding
            valueLabel: root.sentinelLabel(root.axes.innerPadding)
            from: -1
            to: 64
            stepSize: 1
            modified: root.axes.innerPadding !== BarDefaults.DEFAULTS.innerPadding
            onMoved: value => PersonalizationConfig.setBarInnerPadding(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarInnerPadding(-1)
        }

        PreferenceSlider {
            label: I18n.tr("Widget padding")
            value: root.axes.widgetPadding
            valueLabel: root.sentinelLabel(root.axes.widgetPadding)
            from: -1
            to: 32
            stepSize: 1
            modified: root.axes.widgetPadding !== BarDefaults.DEFAULTS.widgetPadding
            onMoved: value => PersonalizationConfig.setBarWidgetPadding(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarWidgetPadding(-1)
        }

        PreferenceSlider {
            label: I18n.tr("Content scale")
            value: root.axes.fontScale
            valueLabel: Math.round(root.axes.fontScale * 100) + " %"
            from: 0.8
            to: 1.5
            stepSize: 0.05
            modified: Math.abs(root.axes.fontScale - BarDefaults.DEFAULTS.fontScale) > 0.001
            onMoved: value => PersonalizationConfig.setBarFontScale(value)
            onResetRequested: PersonalizationConfig.setBarFontScale(BarDefaults.DEFAULTS.fontScale)
        }

        PreferenceSlider {
            label: I18n.tr("Icon scale")
            value: root.axes.iconScale
            valueLabel: Math.round(root.axes.iconScale * 100) + " %"
            from: 0.8
            to: 1.5
            stepSize: 0.05
            modified: Math.abs(root.axes.iconScale - BarDefaults.DEFAULTS.iconScale) > 0.001
            onMoved: value => PersonalizationConfig.setBarIconScale(value)
            onResetRequested: PersonalizationConfig.setBarIconScale(BarDefaults.DEFAULTS.iconScale)
        }

        PreferenceSelect {
            label: I18n.tr("Density")
            model: root.densityOptions
            currentValue: root.densityLevel
            fallbackText: I18n.tr("Custom")
            inputRegionService: PopupInputRegionService
            modified: root.densityLevel !== "comfortable"
            onSelected: value => PersonalizationConfig.applyBarDensityPreset(String(value))
            onResetRequested: PersonalizationConfig.applyBarDensityPreset("comfortable")
        }

        PreferenceControlledBy {
            visible: root.densityLevel === "compact" || root.densityLevel === "spacious"
            icon: "density_medium"
            title: root.densityLevel === "compact" ? I18n.tr("Compact density active") : I18n.tr("Spacious density active")
            reason: I18n.tr("Drives bar thickness, margins, font scale, and icon scale")
            actionLabel: I18n.tr("Reset")
            onActionClicked: PersonalizationConfig.applyBarDensityPreset("comfortable")
        }
    }

    // Screens
    PreferenceHeader {
        visible: root.detectedScreens.length > 1
        text: I18n.tr("Screens")
    }

    PreferenceGroup {
        visible: root.detectedScreens.length > 1

        PreferenceToggle {
            text: I18n.tr("All screens")
            checked: PersonalizationConfig.barScreenList.length === 0
            onToggled: PersonalizationConfig.setBarScreenList([])
        }

        Repeater {
            model: root.detectedScreens

            PreferenceToggle {
                required property var modelData

                readonly property string screenName: modelData?.name ?? ""

                visible: screenName.length > 0
                text: screenName
                checked: PersonalizationConfig.barScreenList.length === 0 || PersonalizationConfig.barScreenList.includes(screenName)
                onToggled: root.toggleBarScreen(screenName, !(PersonalizationConfig.barScreenList.length === 0 || PersonalizationConfig.barScreenList.includes(screenName)))
            }
        }
    }

    // Style & Corner
    PreferenceHeader {
        text: I18n.tr("Style")
    }

    PreferenceGroup {
        PreferenceSelect {
            label: I18n.tr("Corner style")
            model: PersonalizationConfig.barCornerStyles
            currentValue: PersonalizationConfig.barCornerStyle
            inputRegionService: PopupInputRegionService
            modified: PersonalizationConfig.barCornerStyle !== BarDefaults.DEFAULTS.cornerStyle
            onSelected: value => PersonalizationConfig.setBarCornerStyle(Number(value))
            onResetRequested: PersonalizationConfig.setBarCornerStyle(BarDefaults.DEFAULTS.cornerStyle)
        }

        PreferenceSelect {
            label: I18n.tr("Borderless mode")
            model: PersonalizationConfig.barBorderlessModes
            currentValue: PersonalizationConfig.barBorderless
            inputRegionService: PopupInputRegionService
            modified: PersonalizationConfig.barBorderless !== BarDefaults.DEFAULTS.borderless
            onSelected: value => PersonalizationConfig.setBarBorderless(String(value))
            onResetRequested: PersonalizationConfig.setBarBorderless(BarDefaults.DEFAULTS.borderless)
        }

        PreferenceToggle {
            text: I18n.tr("Square corners")
            checked: root.axes.squareCorners
            modified: root.axes.squareCorners !== BarDefaults.DEFAULTS.squareCorners
            onToggled: PersonalizationConfig.setBarSquareCorners(checked)
            onResetRequested: PersonalizationConfig.setBarSquareCorners(BarDefaults.DEFAULTS.squareCorners)
        }

        PreferenceSlider {
            label: I18n.tr("Corner radius")
            value: root.axes.radius
            valueLabel: root.axes.radius < 0 ? I18n.tr("Auto") : Math.round(root.axes.radius) + " px"
            from: -1
            to: 32
            stepSize: 1
            modified: root.axes.radius !== BarDefaults.DEFAULTS.radius
            onMoved: value => PersonalizationConfig.setBarRadius(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarRadius(-1)
        }

        PreferenceToggle {
            text: I18n.tr("Show background")
            enabled: PersonalizationConfig.barCornerStyle === 0 || PersonalizationConfig.barCornerStyle === 1
            checked: PersonalizationConfig.barShowBackground
            modified: PersonalizationConfig.barShowBackground !== BarDefaults.DEFAULTS.showBackground
            onToggled: PersonalizationConfig.setBarShowBackground(checked)
            onResetRequested: PersonalizationConfig.setBarShowBackground(BarDefaults.DEFAULTS.showBackground)
        }

        PreferenceSelect {
            label: I18n.tr("Group color")
            model: PersonalizationConfig.barGroupColorOptions
            currentValue: PersonalizationConfig.barGroupColor
            inputRegionService: PopupInputRegionService
            modified: PersonalizationConfig.barGroupColor !== BarDefaults.DEFAULTS.groupColor
            onSelected: value => PersonalizationConfig.setBarGroupColor(String(value))
            onResetRequested: PersonalizationConfig.setBarGroupColor(BarDefaults.DEFAULTS.groupColor)
        }

        PreferenceSlider {
            visible: root.horizontalBar
            label: I18n.tr("Bar thickness")
            value: PersonalizationConfig.barThickness
            valueLabel: Math.round(PersonalizationConfig.barThickness) + " px"
            from: 28
            to: 56
            stepSize: 2
            modified: PersonalizationConfig.barThickness !== BarDefaults.DEFAULTS.barThickness
            onMoved: value => PersonalizationConfig.setBarThickness(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarThickness(BarDefaults.DEFAULTS.barThickness)
        }

        PreferenceSlider {
            visible: !root.horizontalBar
            label: I18n.tr("Vertical bar thickness")
            value: PersonalizationConfig.barVerticalThickness
            valueLabel: Math.round(PersonalizationConfig.barVerticalThickness) + " px"
            from: 28
            to: 64
            stepSize: 2
            modified: PersonalizationConfig.barVerticalThickness !== BarDefaults.DEFAULTS.verticalThickness
            onMoved: value => PersonalizationConfig.setBarVerticalThickness(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarVerticalThickness(BarDefaults.DEFAULTS.verticalThickness)
        }
    }

    // Effects (bar surface)
    PreferenceHeader {
        text: I18n.tr("Effects")
    }

    PreferenceGroup {
        PreferenceSelect {
            label: I18n.tr("Surface color")
            model: root.surfaceColorOptions
            currentValue: root.axes.surfaceColor
            inputRegionService: PopupInputRegionService
            modified: root.axes.surfaceColor !== BarDefaults.DEFAULTS.surfaceColor
            onSelected: value => PersonalizationConfig.setBarSurfaceColor(String(value))
            onResetRequested: PersonalizationConfig.setBarSurfaceColor(BarDefaults.DEFAULTS.surfaceColor)
        }

        PreferenceSlider {
            label: I18n.tr("Surface opacity")
            value: root.axes.surfaceTransparency < 0 ? 1 : root.axes.surfaceTransparency
            valueLabel: root.axes.surfaceTransparency < 0 ? I18n.tr("Auto") : Math.round(root.axes.surfaceTransparency * 100) + " %"
            from: 0.3
            to: 1
            stepSize: 0.05
            modified: root.axes.surfaceTransparency !== BarDefaults.DEFAULTS.surfaceTransparency
            onMoved: value => PersonalizationConfig.setBarSurfaceTransparency(value)
            onResetRequested: PersonalizationConfig.setBarSurfaceTransparency(-1)
        }

        PreferenceToggle {
            text: I18n.tr("Surface border")
            checked: root.axes.borderEnabled
            modified: root.axes.borderEnabled !== BarDefaults.DEFAULTS.borderEnabled
            onToggled: PersonalizationConfig.setBarBorderEnabled(checked)
            onResetRequested: PersonalizationConfig.setBarBorderEnabled(BarDefaults.DEFAULTS.borderEnabled)
        }

        PreferenceSelect {
            visible: root.axes.borderEnabled
            label: I18n.tr("Border color")
            model: root.surfaceColorOptions
            currentValue: root.axes.borderColor
            inputRegionService: PopupInputRegionService
            modified: root.axes.borderColor !== BarDefaults.DEFAULTS.borderColor
            onSelected: value => PersonalizationConfig.setBarBorderColor(String(value))
            onResetRequested: PersonalizationConfig.setBarBorderColor(BarDefaults.DEFAULTS.borderColor)
        }

        PreferenceSlider {
            visible: root.axes.borderEnabled
            label: I18n.tr("Border opacity")
            value: root.axes.borderOpacity
            valueLabel: Math.round(root.axes.borderOpacity * 100) + " %"
            from: 0.1
            to: 1
            stepSize: 0.05
            modified: Math.abs(root.axes.borderOpacity - BarDefaults.DEFAULTS.borderOpacity) > 0.001
            onMoved: value => PersonalizationConfig.setBarBorderOpacity(value)
            onResetRequested: PersonalizationConfig.setBarBorderOpacity(BarDefaults.DEFAULTS.borderOpacity)
        }

        PreferenceSlider {
            visible: root.axes.borderEnabled
            label: I18n.tr("Border width")
            value: root.axes.borderThickness
            valueLabel: Math.round(root.axes.borderThickness) + " px"
            from: 0
            to: 4
            stepSize: 1
            modified: root.axes.borderThickness !== BarDefaults.DEFAULTS.borderThickness
            onMoved: value => PersonalizationConfig.setBarBorderThickness(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarBorderThickness(BarDefaults.DEFAULTS.borderThickness)
        }
    }

    // Widget layer (group capsule chrome)
    PreferenceCollapsibleGroup {
        title: I18n.tr("Widget layer")
        subtitle: I18n.tr("Capsule opacity and outline")
        icon: "layers"
        expanded: root.axes.widgetOutlineEnabled || Math.abs(root.axes.widgetTransparency - BarDefaults.DEFAULTS.widgetTransparency) > 0.001

        PreferenceSlider {
            label: I18n.tr("Widget opacity")
            value: root.axes.widgetTransparency
            valueLabel: Math.round(root.axes.widgetTransparency * 100) + " %"
            from: 0.3
            to: 1
            stepSize: 0.05
            modified: Math.abs(root.axes.widgetTransparency - BarDefaults.DEFAULTS.widgetTransparency) > 0.001
            onMoved: value => PersonalizationConfig.setBarWidgetTransparency(value)
            onResetRequested: PersonalizationConfig.setBarWidgetTransparency(BarDefaults.DEFAULTS.widgetTransparency)
        }

        PreferenceToggle {
            text: I18n.tr("Widget outline")
            checked: root.axes.widgetOutlineEnabled
            modified: root.axes.widgetOutlineEnabled !== BarDefaults.DEFAULTS.widgetOutlineEnabled
            onToggled: PersonalizationConfig.setBarWidgetOutlineEnabled(checked)
            onResetRequested: PersonalizationConfig.setBarWidgetOutlineEnabled(BarDefaults.DEFAULTS.widgetOutlineEnabled)
        }

        PreferenceSelect {
            visible: root.axes.widgetOutlineEnabled
            label: I18n.tr("Outline color")
            model: root.surfaceColorOptions
            currentValue: root.axes.widgetOutlineColor
            inputRegionService: PopupInputRegionService
            modified: root.axes.widgetOutlineColor !== BarDefaults.DEFAULTS.widgetOutlineColor
            onSelected: value => PersonalizationConfig.setBarWidgetOutlineColor(String(value))
            onResetRequested: PersonalizationConfig.setBarWidgetOutlineColor(BarDefaults.DEFAULTS.widgetOutlineColor)
        }

        PreferenceSlider {
            visible: root.axes.widgetOutlineEnabled
            label: I18n.tr("Outline opacity")
            value: root.axes.widgetOutlineOpacity
            valueLabel: Math.round(root.axes.widgetOutlineOpacity * 100) + " %"
            from: 0.1
            to: 1
            stepSize: 0.05
            modified: Math.abs(root.axes.widgetOutlineOpacity - BarDefaults.DEFAULTS.widgetOutlineOpacity) > 0.001
            onMoved: value => PersonalizationConfig.setBarWidgetOutlineOpacity(value)
            onResetRequested: PersonalizationConfig.setBarWidgetOutlineOpacity(BarDefaults.DEFAULTS.widgetOutlineOpacity)
        }

        PreferenceSlider {
            visible: root.axes.widgetOutlineEnabled
            label: I18n.tr("Outline width")
            value: root.axes.widgetOutlineThickness
            valueLabel: Math.round(root.axes.widgetOutlineThickness) + " px"
            from: 0
            to: 4
            stepSize: 1
            modified: root.axes.widgetOutlineThickness !== BarDefaults.DEFAULTS.widgetOutlineThickness
            onMoved: value => PersonalizationConfig.setBarWidgetOutlineThickness(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarWidgetOutlineThickness(BarDefaults.DEFAULTS.widgetOutlineThickness)
        }
    }

    // Behavior (D4d)
    PreferenceHeader {
        text: I18n.tr("Behavior")
    }

    PreferenceGroup {
        PreferenceToggle {
            text: I18n.tr("Autohide")
            checked: PersonalizationConfig.barAutoHide
            modified: PersonalizationConfig.barAutoHide !== BarDefaults.DEFAULTS.autoHide
            onToggled: PersonalizationConfig.setBarAutoHide(checked)
            onResetRequested: PersonalizationConfig.setBarAutoHide(BarDefaults.DEFAULTS.autoHide)
        }

        PreferenceSlider {
            visible: PersonalizationConfig.barAutoHide
            label: I18n.tr("Autohide delay")
            value: root.axes.autoHideDelay
            valueLabel: root.axes.autoHideDelay <= 0 ? I18n.tr("Off") : Math.round(root.axes.autoHideDelay) + " ms"
            from: 0
            to: 1000
            stepSize: 50
            modified: root.axes.autoHideDelay !== BarDefaults.DEFAULTS.autoHideDelay
            onMoved: value => PersonalizationConfig.setBarAutoHideDelay(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarAutoHideDelay(BarDefaults.DEFAULTS.autoHideDelay)
        }

        PreferenceToggle {
            visible: PersonalizationConfig.barAutoHide
            text: I18n.tr("Strict autohide")
            checked: root.axes.autoHideStrict
            modified: root.axes.autoHideStrict !== BarDefaults.DEFAULTS.autoHideStrict
            onToggled: PersonalizationConfig.setBarAutoHideStrict(checked)
            onResetRequested: PersonalizationConfig.setBarAutoHideStrict(BarDefaults.DEFAULTS.autoHideStrict)
        }

        PreferenceToggle {
            text: I18n.tr("Hide over fullscreen")
            checked: root.axes.hideOnFullscreen
            modified: root.axes.hideOnFullscreen !== BarDefaults.DEFAULTS.hideOnFullscreen
            onToggled: PersonalizationConfig.setBarHideOnFullscreen(checked)
            onResetRequested: PersonalizationConfig.setBarHideOnFullscreen(BarDefaults.DEFAULTS.hideOnFullscreen)
        }

        PreferenceToggle {
            text: I18n.tr("Click-through")
            checked: root.axes.clickThrough
            modified: root.axes.clickThrough !== BarDefaults.DEFAULTS.clickThrough
            onToggled: PersonalizationConfig.setBarClickThrough(checked)
            onResetRequested: PersonalizationConfig.setBarClickThrough(BarDefaults.DEFAULTS.clickThrough)
        }

        PreferenceToggle {
            text: I18n.tr("Hover popouts")
            checked: root.axes.hoverPopouts
            modified: root.axes.hoverPopouts !== BarDefaults.DEFAULTS.hoverPopouts
            onToggled: PersonalizationConfig.setBarHoverPopouts(checked)
            onResetRequested: PersonalizationConfig.setBarHoverPopouts(BarDefaults.DEFAULTS.hoverPopouts)
        }

        PreferenceSlider {
            visible: root.axes.hoverPopouts
            label: I18n.tr("Hover popout delay")
            value: root.axes.hoverPopoutDelay
            valueLabel: Math.round(root.axes.hoverPopoutDelay) + " ms"
            from: 0
            to: 800
            stepSize: 50
            modified: root.axes.hoverPopoutDelay !== BarDefaults.DEFAULTS.hoverPopoutDelay
            onMoved: value => PersonalizationConfig.setBarHoverPopoutDelay(Math.round(value))
            onResetRequested: PersonalizationConfig.setBarHoverPopoutDelay(BarDefaults.DEFAULTS.hoverPopoutDelay)
        }
    }
}

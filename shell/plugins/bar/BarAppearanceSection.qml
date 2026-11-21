import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Appearance tab of the Bar page: the bar's frame — position, outer
// margins, the screen filter, style, and the D4c fine-grained axes
// (spacing/padding/scale/shape/surface effects). Split out of the pre-tab
// GeneralBarPage monolith; reads PersonalizationConfig directly and the
// search anchors ride with their rows (bar.appearance.*). The Layout
// header merges the old singleton-row Position group with the margins;
// Screens stays its own group because its rows vanish on single-screen
// setups and a conditional tail would break the connected-card rounding.
//
// D4c sentinel rows: a -1 value renders as "Auto" (the per-style
// baseline); dragging off -1 writes the explicit value. Resetting is
// dragging back to Auto — a dedicated reset affordance is D4e material.
ColumnLayout {
    id: root

    readonly property bool horizontalBar: PersonalizationConfig.barPosition === "top" || PersonalizationConfig.barPosition === "bottom"
    readonly property var detectedScreens: Quickshell.screens
    readonly property var axes: PersonalizationConfig.barAxes

    // Color-axis vocabulary (roles resolvable as Appearance.colors.col*;
    // hexes are accepted by the store, the popup's "custom" flow is the
    // per-instance one).
    readonly property var surfaceColorOptions: [{
        "value": "default",
        "label": I18n.tr("Default")
    }, {
        "value": "layer0",
        "label": I18n.tr("Background")
    }, {
        "value": "layer1",
        "label": I18n.tr("Surface layer")
    }, {
        "value": "surfaceContainer",
        "label": I18n.tr("Surface container")
    }, {
        "value": "primaryContainer",
        "label": I18n.tr("Primary container")
    }, {
        "value": "secondaryContainer",
        "label": I18n.tr("Secondary container")
    }]

    function sentinelLabel(value): string {
        return value < 0 ? I18n.tr("Auto") : Math.round(value) + " px";
    }

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
        PersonalizationConfig.setBarScreenList(list.length === allNames.length ? [] : list);
    }

    spacing: NexusStyle.padding.extraSmall / 2

    // Layout
    PreferenceHeader {
        text: I18n.tr("Layout")
    }

    PreferenceSelect {
        id: edgeSelect

        first: true
        label: I18n.tr("Screen edge")
        model: PersonalizationConfig.edgePositions
        currentValue: PersonalizationConfig.barPosition
        inputRegionService: PopupInputRegionService
        onSelected: value => PersonalizationConfig.setBarPosition(String(value))

        SettingsSearchAnchor {
            id: searchAnchorPosition

            target: edgeSelect
            anchorId: "bar.appearance.position"
        }
    }

    // B9.5 outer margins: separate from the internal lane inset
    // (ROADMAP B-9). 0 keeps end4's edge-flush baseline.
    PreferenceSlider {
        label: I18n.tr("Screen edge margin")
        value: PersonalizationConfig.barEdgeMargin
        valueLabel: Math.round(PersonalizationConfig.barEdgeMargin) + " px"
        from: 0
        to: 48
        stepSize: 2
        onMoved: value => PersonalizationConfig.setBarEdgeMargin(Math.round(value))
    }

    PreferenceSlider {
        label: I18n.tr("Bar end margin")
        value: PersonalizationConfig.barSideMargin
        valueLabel: Math.round(PersonalizationConfig.barSideMargin) + " px"
        from: 0
        to: 96
        stepSize: 2
        onMoved: value => PersonalizationConfig.setBarSideMargin(Math.round(value))
    }

    // D4c percent length: each-side margin in % of the screen; 0 keeps the
    // full-width bar (absorbs dux barLengthMode/Percent).
    PreferenceSlider {
        label: I18n.tr("Bar end margin (%)")
        value: root.axes.sideMarginPercent
        valueLabel: root.axes.sideMarginPercent <= 0 ? I18n.tr("Off") : root.axes.sideMarginPercent + " %"
        from: 0
        to: 49
        stepSize: 1
        onMoved: value => PersonalizationConfig.setBarSideMarginPercent(Math.round(value))
    }

    // D4c geometry axes (sentinel -1 = the per-style baseline).
    PreferenceSlider {
        label: I18n.tr("Widget spacing")
        value: root.axes.spacing
        valueLabel: root.sentinelLabel(root.axes.spacing)
        from: -1
        to: 64
        stepSize: 1
        onMoved: value => PersonalizationConfig.setBarSpacing(Math.round(value))
    }

    PreferenceSlider {
        label: I18n.tr("Lane inset")
        value: root.axes.innerPadding
        valueLabel: root.sentinelLabel(root.axes.innerPadding)
        from: -1
        to: 64
        stepSize: 1
        onMoved: value => PersonalizationConfig.setBarInnerPadding(Math.round(value))
    }

    PreferenceSlider {
        label: I18n.tr("Widget padding")
        value: root.axes.widgetPadding
        valueLabel: root.sentinelLabel(root.axes.widgetPadding)
        from: -1
        to: 32
        stepSize: 1
        onMoved: value => PersonalizationConfig.setBarWidgetPadding(Math.round(value))
    }

    PreferenceSlider {
        label: I18n.tr("Content scale")
        value: root.axes.fontScale
        valueLabel: Math.round(root.axes.fontScale * 100) + " %"
        from: 0.8
        to: 1.5
        stepSize: 0.05
        onMoved: value => PersonalizationConfig.setBarFontScale(value)
    }

    // Screens
    PreferenceHeader {
        visible: root.detectedScreens.length > 1
        text: I18n.tr("Screens")
    }

    PreferenceToggle {
        visible: root.detectedScreens.length > 1
        first: true
        text: I18n.tr("All screens")
        checked: PersonalizationConfig.barScreenList.length === 0
        onToggled: PersonalizationConfig.setBarScreenList([])
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

    // D4c shape axes: square corners flatten the shell radius; the radius
    // override beats the theme's screen rounding (-1 keeps it).
    PreferenceToggle {
        text: I18n.tr("Square corners")
        checked: root.axes.squareCorners
        onToggled: PersonalizationConfig.setBarSquareCorners(checked)
    }

    PreferenceSlider {
        label: I18n.tr("Corner radius")
        value: root.axes.radius
        valueLabel: root.axes.radius < 0 ? I18n.tr("Auto") : Math.round(root.axes.radius) + " px"
        from: -1
        to: 32
        stepSize: 1
        onMoved: value => PersonalizationConfig.setBarRadius(Math.round(value))
    }

    // end4 `bar.showBackground`: the frame/pill background of
    // Hug and Float. Other styles decide their own background
    // downstream, so the row idles there (end4 disables it too).
    PreferenceToggle {
        text: I18n.tr("Show background")
        enabled: PersonalizationConfig.barCornerStyle === 0 || PersonalizationConfig.barCornerStyle === 1
        checked: PersonalizationConfig.barShowBackground
        onToggled: PersonalizationConfig.setBarShowBackground(checked)
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

    // Effects (bar surface)
    PreferenceHeader {
        text: I18n.tr("Effects")
    }

    PreferenceSelect {
        first: true
        label: I18n.tr("Surface color")
        model: root.surfaceColorOptions
        currentValue: root.axes.surfaceColor
        inputRegionService: PopupInputRegionService
        onSelected: value => PersonalizationConfig.setBarSurfaceColor(String(value))
    }

    PreferenceSlider {
        label: I18n.tr("Surface opacity")
        value: root.axes.surfaceTransparency < 0 ? 1 : root.axes.surfaceTransparency
        valueLabel: root.axes.surfaceTransparency < 0 ? I18n.tr("Auto") : Math.round(root.axes.surfaceTransparency * 100) + " %"
        from: 0.3
        to: 1
        stepSize: 0.05
        onMoved: value => PersonalizationConfig.setBarSurfaceTransparency(value)
    }

    PreferenceToggle {
        text: I18n.tr("Surface border")
        checked: root.axes.borderEnabled
        onToggled: PersonalizationConfig.setBarBorderEnabled(checked)
    }

    PreferenceSelect {
        label: I18n.tr("Border color")
        model: root.surfaceColorOptions
        currentValue: root.axes.borderColor
        enabled: root.axes.borderEnabled
        inputRegionService: PopupInputRegionService
        onSelected: value => PersonalizationConfig.setBarBorderColor(String(value))
    }

    PreferenceSlider {
        label: I18n.tr("Border opacity")
        value: root.axes.borderOpacity
        valueLabel: Math.round(root.axes.borderOpacity * 100) + " %"
        from: 0.1
        to: 1
        stepSize: 0.05
        enabled: root.axes.borderEnabled
        onMoved: value => PersonalizationConfig.setBarBorderOpacity(value)
    }

    PreferenceSlider {
        last: true
        label: I18n.tr("Border width")
        value: root.axes.borderThickness
        valueLabel: Math.round(root.axes.borderThickness) + " px"
        from: 0
        to: 4
        stepSize: 1
        enabled: root.axes.borderEnabled
        onMoved: value => PersonalizationConfig.setBarBorderThickness(Math.round(value))
    }

    // Widget layer (group capsule chrome)
    PreferenceHeader {
        text: I18n.tr("Widget layer")
    }

    PreferenceSlider {
        first: true
        label: I18n.tr("Widget opacity")
        value: root.axes.widgetTransparency
        valueLabel: Math.round(root.axes.widgetTransparency * 100) + " %"
        from: 0.3
        to: 1
        stepSize: 0.05
        onMoved: value => PersonalizationConfig.setBarWidgetTransparency(value)
    }

    PreferenceToggle {
        text: I18n.tr("Widget outline")
        checked: root.axes.widgetOutlineEnabled
        onToggled: PersonalizationConfig.setBarWidgetOutlineEnabled(checked)
    }

    PreferenceSelect {
        label: I18n.tr("Outline color")
        model: root.surfaceColorOptions
        currentValue: root.axes.widgetOutlineColor
        enabled: root.axes.widgetOutlineEnabled
        inputRegionService: PopupInputRegionService
        onSelected: value => PersonalizationConfig.setBarWidgetOutlineColor(String(value))
    }

    PreferenceSlider {
        label: I18n.tr("Outline opacity")
        value: root.axes.widgetOutlineOpacity
        valueLabel: Math.round(root.axes.widgetOutlineOpacity * 100) + " %"
        from: 0.1
        to: 1
        stepSize: 0.05
        enabled: root.axes.widgetOutlineEnabled
        onMoved: value => PersonalizationConfig.setBarWidgetOutlineOpacity(value)
    }

    PreferenceSlider {
        last: true
        label: I18n.tr("Outline width")
        value: root.axes.widgetOutlineThickness
        valueLabel: Math.round(root.axes.widgetOutlineThickness) + " px"
        from: 0
        to: 4
        stepSize: 1
        enabled: root.axes.widgetOutlineEnabled
        onMoved: value => PersonalizationConfig.setBarWidgetOutlineThickness(Math.round(value))
    }

    // D4b: the clock's Date format row moved to the clock entry's own
    // options page (BarWidgetPage) — the pattern is a per-instance axis.
    // D4c: per-widget backgrounds live on the right-click style popup
    // (per instance); the shadow axes are D4e material (they need the
    // window-growth infrastructure).

    // Behavior (D4d): the reveal/hide channel, input pass-through and the
    // popup intent. The auto-hide toggle moved here from Style & Corner.
    PreferenceHeader {
        text: I18n.tr("Behavior")
    }

    PreferenceToggle {
        first: true
        text: I18n.tr("Autohide")
        checked: PersonalizationConfig.barAutoHide
        onToggled: PersonalizationConfig.setBarAutoHide(checked)
    }

    PreferenceSlider {
        label: I18n.tr("Autohide delay")
        value: root.axes.autoHideDelay
        valueLabel: root.axes.autoHideDelay <= 0 ? I18n.tr("Off") : Math.round(root.axes.autoHideDelay) + " ms"
        from: 0
        to: 1000
        stepSize: 50
        enabled: PersonalizationConfig.barAutoHide
        onMoved: value => PersonalizationConfig.setBarAutoHideDelay(Math.round(value))
    }

    PreferenceToggle {
        text: I18n.tr("Strict autohide")
        checked: root.axes.autoHideStrict
        enabled: PersonalizationConfig.barAutoHide
        onToggled: PersonalizationConfig.setBarAutoHideStrict(checked)
    }

    PreferenceToggle {
        text: I18n.tr("Hide over fullscreen")
        checked: root.axes.hideOnFullscreen
        onToggled: PersonalizationConfig.setBarHideOnFullscreen(checked)
    }

    PreferenceToggle {
        text: I18n.tr("Click-through")
        checked: root.axes.clickThrough
        onToggled: PersonalizationConfig.setBarClickThrough(checked)
    }

    PreferenceToggle {
        text: I18n.tr("Hover popouts")
        checked: root.axes.hoverPopouts
        onToggled: PersonalizationConfig.setBarHoverPopouts(checked)
    }

    PreferenceSlider {
        last: true
        label: I18n.tr("Hover popout delay")
        value: root.axes.hoverPopoutDelay
        valueLabel: Math.round(root.axes.hoverPopoutDelay) + " ms"
        from: 0
        to: 800
        stepSize: 50
        enabled: root.axes.hoverPopouts
        onMoved: value => PersonalizationConfig.setBarHoverPopoutDelay(Math.round(value))
    }
}

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Appearance tab of the Bar page: the bar's frame — position, outer
// margins, the screen filter, and style. Split out of the pre-tab
// GeneralBarPage monolith; reads PersonalizationConfig directly and the
// search anchors ride with their rows (bar.appearance.*). The Layout
// header merges the old singleton-row Position group with the margins;
// Screens stays its own group because its rows vanish on single-screen
// setups and a conditional tail would break the connected-card rounding.
ColumnLayout {
    id: root

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
        last: true
        label: I18n.tr("Bar end margin")
        value: PersonalizationConfig.barSideMargin
        valueLabel: Math.round(PersonalizationConfig.barSideMargin) + " px"
        from: 0
        to: 96
        stepSize: 2
        onMoved: value => PersonalizationConfig.setBarSideMargin(Math.round(value))
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
}

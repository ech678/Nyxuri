import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Workspaces entry options (D4b): the six B9.6/B9.7 axes moved off the
// flat [bar] keys plus the default-skin state colors (dux
// workspaceColorMode family trimmed to the two states this skin paints).
ColumnLayout {
    id: root

    property var page: null

    readonly property bool defaultSkin: root.page.value("style") === "default"
    readonly property var styles: [
        {
            value: "default",
            label: I18n.tr("Default")
        },
        {
            value: "gnome",
            label: I18n.tr("Gnome")
        },
        {
            value: "dots",
            label: I18n.tr("Dots")
        },
        {
            value: "ticks",
            label: I18n.tr("Ticks")
        }
    ]
    readonly property var indicatorStyles: [
        {
            value: "dot",
            label: I18n.tr("Dot")
        },
        {
            value: "icon",
            label: I18n.tr("Icon")
        }
    ]
    readonly property var numberStyles: [
        {
            value: "normal",
            label: I18n.tr("Normal")
        },
        {
            value: "han",
            label: I18n.tr("Han chars")
        },
        {
            value: "roman",
            label: I18n.tr("Roman")
        }
    ]
    readonly property var colorModes: [
        {
            value: "theme",
            label: I18n.tr("Theme color")
        },
        {
            value: "none",
            label: I18n.tr("None")
        },
        {
            value: "custom",
            label: I18n.tr("Custom color")
        }
    ]
    readonly property var activeColorModes: [
        {
            value: "theme",
            label: I18n.tr("Theme color")
        },
        {
            value: "custom",
            label: I18n.tr("Custom color")
        }
    ]

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Workspaces")
    }

    PreferenceToggle {
        first: true
        text: I18n.tr("Show app icons")
        checked: root.page.value("showAppIcons")
        onToggled: checked => root.page.set("showAppIcons", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("Monochrome app icons")
        visible: root.page.value("showAppIcons")
        checked: root.page.value("monochromeIcons")
        onToggled: checked => root.page.set("monochromeIcons", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("Always show numbers")
        checked: root.page.value("alwaysShowNumbers")
        onToggled: checked => root.page.set("alwaysShowNumbers", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("Hide empty workspaces")
        checked: root.page.value("hideEmpty")
        onToggled: checked => root.page.set("hideEmpty", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("Invert scroll direction")
        checked: root.page.value("invertScroll")
        onToggled: checked => root.page.set("invertScroll", checked || undefined)
    }

    PreferenceSelect {
        label: I18n.tr("Indicator style")
        model: root.indicatorStyles
        currentValue: root.page.value("indicatorStyle")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("indicatorStyle", String(value) === "dot" ? undefined : String(value))
    }

    PreferenceSelect {
        label: I18n.tr("Workspace style")
        model: root.styles
        currentValue: root.page.value("style")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("style", String(value) === "default" ? undefined : String(value))
    }

    // Only the default skin renders number labels (B9.7).
    PreferenceSelect {
        visible: root.defaultSkin
        label: I18n.tr("Numbers style")
        model: root.numberStyles
        currentValue: root.page.value("numberStyle")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("numberStyle", String(value) === "normal" ? undefined : String(value))
    }

    PreferenceSlider {
        last: true
        label: I18n.tr("Shown workspaces")
        value: root.page.value("shown")
        valueLabel: Math.round(root.page.value("shown")) + ""
        from: 1
        to: 50
        stepSize: 1
        onMoved: value => root.page.set("shown", Math.round(value) === 10 ? undefined : Math.round(value))
    }

    PreferenceHeader {
        visible: root.defaultSkin
        text: I18n.tr("State colors")
    }

    StyledText {
        Layout.fillWidth: true
        Layout.leftMargin: NexusStyle.padding.extraSmall
        visible: root.defaultSkin
        text: I18n.tr("Only the default skin carries state colors")
        color: Appearance.m3colors.m3onSurfaceVariant
        font.pixelSize: NexusStyle.font.bodySmall
        wrapMode: Text.Wrap
    }

    PreferenceSelect {
        visible: root.defaultSkin
        first: true
        label: I18n.tr("Active color")
        model: root.activeColorModes
        currentValue: root.page.value("activeColorMode")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("activeColorMode", String(value) === "theme" ? undefined : String(value))
    }

    PreferenceInput {
        visible: root.defaultSkin && root.page.value("activeColorMode") === "custom"
        label: I18n.tr("Active custom color")
        placeholderText: "#6750A4"
        value: root.page.value("activeCustomColor") ?? ""
        validate: /^#[0-9a-fA-F]{6}$/
        errorText: I18n.tr("Hex color, e.g. #6750A4")
        onEditingFinished: value => root.page.set("activeCustomColor", String(value || "").trim() || undefined)
    }

    PreferenceSelect {
        visible: root.defaultSkin
        label: I18n.tr("Occupied color")
        model: root.colorModes
        currentValue: root.page.value("occupiedColorMode")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("occupiedColorMode", String(value) === "theme" ? undefined : String(value))
    }

    PreferenceInput {
        visible: root.defaultSkin && root.page.value("occupiedColorMode") === "custom"
        last: true
        label: I18n.tr("Occupied custom color")
        placeholderText: "#625B71"
        value: root.page.value("occupiedCustomColor") ?? ""
        validate: /^#[0-9a-fA-F]{6}$/
        errorText: I18n.tr("Hex color, e.g. #6750A4")
        onEditingFinished: value => root.page.set("occupiedCustomColor", String(value || "").trim() || undefined)
    }
}

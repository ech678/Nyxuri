import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// System monitor entry options (D4b): the five meters, icon skin and the
// percentage readout (the old flat [bar.resources] table folded by the v4
// migration).
ColumnLayout {
    id: root

    property var page: null

    readonly property var iconStyles: [
        {
            value: "outline",
            label: I18n.tr("Outline")
        },
        {
            value: "filled",
            label: I18n.tr("Filled")
        }
    ]

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Resources")
    }

    PreferenceToggle {
        first: true
        text: I18n.tr("CPU")
        checked: root.page.value("cpu")
        onToggled: checked => root.page.set("cpu", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("CPU temperature")
        checked: root.page.value("cpuTemp")
        onToggled: checked => root.page.set("cpuTemp", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("RAM")
        checked: root.page.value("ram")
        onToggled: checked => root.page.set("ram", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("Disk")
        checked: root.page.value("disk")
        onToggled: checked => root.page.set("disk", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("Swap")
        checked: root.page.value("swap")
        onToggled: checked => root.page.set("swap", checked || undefined)
    }

    PreferenceSelect {
        label: I18n.tr("Icon style")
        model: root.iconStyles
        currentValue: root.page.value("iconStyle")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("iconStyle", String(value) === "outline" ? undefined : String(value))
    }

    PreferenceToggle {
        last: true
        text: I18n.tr("Show percentage")
        checked: root.page.value("showValue")
        onToggled: checked => root.page.set("showValue", checked || undefined)
    }
}

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import "../../../services/BarWidgetDefaults.js" as BarWidgetDefaults

// Island entry options (D4e e5): the island's five per-entry appearance
// axes (folded from [island] in v6) plus navigation shortcuts to the shared
// horizontal clock style subpage and keyboard indicators page.
ColumnLayout {
    id: root

    property var page: null

    spacing: NexusStyle.padding.extraSmall / 2

    PreferenceHeader {
        first: true
        text: I18n.tr("Island")
    }

    PreferenceGroup {
        PreferenceToggle {
            text: I18n.tr("Show avatar")
            checked: root.page.value("showAvatar")
            modified: root.page.value("showAvatar") !== BarWidgetDefaults.DEFAULTS.island.showAvatar
            onToggled: root.page.set("showAvatar", checked === true ? undefined : checked)
            onResetRequested: root.page.set("showAvatar", undefined)
        }

        PreferenceSelect {
            label: I18n.tr("Satellite")
            model: PersonalizationConfig.islandSatelliteOptions
            currentValue: root.page.value("satellite")
            inputRegionService: PopupInputRegionService
            modified: root.page.value("satellite") !== BarWidgetDefaults.DEFAULTS.island.satellite
            onSelected: value => root.page.set("satellite", String(value) === "clock" ? undefined : String(value))
            onResetRequested: root.page.set("satellite", undefined)
        }

        PreferenceToggle {
            text: I18n.tr("Show media controls")
            checked: root.page.value("showMediaControls")
            modified: root.page.value("showMediaControls") !== BarWidgetDefaults.DEFAULTS.island.showMediaControls
            onToggled: root.page.set("showMediaControls", checked || undefined)
            onResetRequested: root.page.set("showMediaControls", undefined)
        }

        PreferenceSelect {
            label: I18n.tr("Visualizer")
            model: PersonalizationConfig.islandVisualizerStyleOptions
            currentValue: root.page.value("visualizerStyle")
            inputRegionService: PopupInputRegionService
            modified: root.page.value("visualizerStyle") !== BarWidgetDefaults.DEFAULTS.island.visualizerStyle
            onSelected: value => root.page.set("visualizerStyle", String(value) === "dots" ? undefined : String(value))
            onResetRequested: root.page.set("visualizerStyle", undefined)
        }

        PreferenceToggle {
            text: I18n.tr("Hide date")
            checked: root.page.value("hideDate")
            modified: root.page.value("hideDate") !== BarWidgetDefaults.DEFAULTS.island.hideDate
            onToggled: root.page.set("hideDate", checked || undefined)
            onResetRequested: root.page.set("hideDate", undefined)
        }
    }

    PreferenceHeader {
        text: I18n.tr("Related")
    }

    PreferenceGroup {
        PreferenceAction {
            icon: "schedule"
            text: I18n.tr("Horizontal clock style")
            subtext: I18n.tr("Font, digit positions, and colors")
            onClicked: root.page.openRoute("island-clock")
        }

        PreferenceAction {
            icon: "keyboard"
            text: I18n.tr("Keyboard indicators")
            subtext: I18n.tr("Panel and popup notifications")
            onClicked: root.page.openRoute("island")
        }
    }
}

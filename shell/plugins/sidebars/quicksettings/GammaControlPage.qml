pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Gamma control page (M3 rebuild): the whole form moves onto the M1 atoms —
// gamma/contrast/dimming/temperature sliders, night mode and IP-location
// toggles, fixed/time/location schedule select, time and coordinate inputs
// (with regex/range validation), read-only status rows as info atoms. Truth
// stays with DisplayColor (app service); the page only calls setPreference.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("displays.gamma")

    property real contentPadding: 0
    property bool searchAnchorsEnabled: true

    readonly property Item searchLeaf: root.flickable

    readonly property var preferences: DisplayColor.preferences
    readonly property var timePattern: /^([01][0-9]|2[0-3]):[0-5][0-9]$/

                                       function timeText(minutes) {
                                           return Math.floor(minutes / 60).toString().padStart(2, "0") + ":" + (
                                                       minutes % 60).toString().padStart(2, "0");
                                       }

    function setTime(key, text) {
        const parts = text.split(":").map(Number);
        if (parts.length === 2 && parts[0] >= 0 && parts[0] < 24 && parts[1] >= 0 && parts[1] < 60)
            DisplayColor.setPreference(key, parts[0] * 60 + parts[1]);
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: !DisplayColor.available
            message: I18n.tr("The compositor does not provide Gamma control")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DisplayColor.error !== ""
            tone: "error"
            message: DisplayColor.error
        }

        // Color
        PreferenceHeader {
            text: I18n.tr("Color")
        }

        PreferenceSlider {
            id: gammaSlider

            first: true
            label: I18n.tr("Gamma")
            valueLabel: Math.round(root.preferences.gamma * 100) + "%"
            value: root.preferences.gamma * 100
            from: 50
            to: 200
            stepSize: 1
            enabled: DisplayColor.ready
            onMoved: value => DisplayColor.setPreference("gamma", value / 100)

            SettingsSearchAnchor {
                target: gammaSlider
                declaration:
                    '{"id":"displays.gamma.section.color","route":"displays.gamma","title":"Color","context":"GammaControlPage","icon":"brightness_6","aliases":["general.displays.gamma.section.color"]}'
            }
        }

        PreferenceSlider {
            label: I18n.tr("Contrast")
            valueLabel: Math.round(root.preferences.contrast * 100) + "%"
            value: root.preferences.contrast * 100
            from: 50
            to: 200
            stepSize: 1
            enabled: DisplayColor.ready
            onMoved: value => DisplayColor.setPreference("contrast", value / 100)
        }

        PreferenceSlider {
            last: true
            label: I18n.tr("Software dimming")
            valueLabel: Math.round(root.preferences.dimming * 100) + "%"
            value: root.preferences.dimming * 100
            from: 25
            to: 100
            stepSize: 1
            enabled: DisplayColor.ready
            onMoved: value => DisplayColor.setDimming(value / 100)
        }

        // Night Mode
        PreferenceHeader {
            text: I18n.tr("Night Mode")
        }

        PreferenceToggle {
            id: nightModeToggle

            first: true
            last: !root.preferences.nightEnabled
            text: I18n.tr("Night Mode")
            checked: root.preferences.nightEnabled
            onToggled: DisplayColor.setPreference("nightEnabled", checked)
        }

        PreferenceSlider {
            last: true
            visible: root.preferences.nightEnabled
            label: I18n.tr("Night temperature")
            valueLabel: Math.round(root.preferences.nightTemperature) + " K"
            value: root.preferences.nightTemperature
            from: 1000
            to: 6500
            stepSize: 100
            onMoved: value => DisplayColor.setPreference("nightTemperature", value)
        }

        // Schedule
        PreferenceHeader {
            visible: root.preferences.nightEnabled
            text: I18n.tr("Schedule")
        }

        PreferenceSelect {
            id: modeSelect

            first: true
            last: root.preferences.mode === "fixed"
            visible: root.preferences.nightEnabled
            label: I18n.tr("Automatic control")
            model: [
                {
                    "value": "fixed",
                    "label": I18n.tr("Fixed temperature")
                },
                {
                    "value": "time",
                    "label": I18n.tr("Time")
                },
                {
                    "value": "location",
                    "label": I18n.tr("Sunrise and sunset")
                }
            ]
            currentValue: root.preferences.mode
            inputRegionService: PopupInputRegionService
            onSelected: value => DisplayColor.setPreference("mode", value)

            SettingsSearchAnchor {
                target: modeSelect
                declaration:
                    '{"id":"displays.gamma.section.schedule","route":"displays.gamma","title":"Schedule","context":"GammaControlPage","icon":"brightness_6","aliases":["general.displays.gamma.section.schedule"]}'
            }
        }

        PreferenceInput {
            id: nightStartsInput

            visible: root.preferences.nightEnabled && root.preferences.mode === "time"
            label: I18n.tr("Night starts")
            value: root.timeText(root.preferences.start)
            fieldWidth: 140
            validate: root.timePattern
            onEditingFinished: value => root.setTime("start", value)
        }

        PreferenceInput {
            id: dayStartsInput

            visible: root.preferences.nightEnabled && root.preferences.mode === "time"
            label: I18n.tr("Day starts")
            value: root.timeText(root.preferences.end)
            fieldWidth: 140
            validate: root.timePattern
            onEditingFinished: value => root.setTime("end", value)
        }

        PreferenceInput {
            id: latitudeInput

            visible: root.preferences.nightEnabled && root.preferences.mode === "location"
            label: I18n.tr("Latitude")
            value: root.preferences.latitude === null ? "" : String(root.preferences.latitude)
            fieldWidth: 140
            validate: text => text.trim() === "" || (!isNaN(Number(text)) && Number(text) >= -90 && Number(
                                                         text) <= 90)
            onEditingFinished: value => {
                if (latitudeInput.valid)
                    DisplayColor.setPreference("latitude", value.trim() === "" ? null : Number(value));
            }
        }

        PreferenceInput {
            id: longitudeInput

            visible: root.preferences.nightEnabled && root.preferences.mode === "location"
            label: I18n.tr("Longitude")
            value: root.preferences.longitude === null ? "" : String(root.preferences.longitude)
            fieldWidth: 140
            validate: text => text.trim() === "" || (!isNaN(Number(text)) && Number(text) >= -180 && Number(
                                                         text) <= 180)
            onEditingFinished: value => {
                if (longitudeInput.valid)
                    DisplayColor.setPreference("longitude", value.trim() === "" ? null : Number(value));
            }
        }

        PreferenceToggle {
            visible: root.preferences.nightEnabled && root.preferences.mode === "location"
            text: I18n.tr("Automatic IP location")
            checked: root.preferences.useIP
            onToggled: DisplayColor.setPreference("useIP", checked)
        }

        PreferenceAction {
            visible: root.preferences.nightEnabled && root.preferences.mode === "location"
                     && root.preferences.useIP
            icon: "refresh"
            text: I18n.tr("Refresh location")
            trailingIcon: ""
            enabled: !DisplayColor.locating
            onClicked: DisplayColor.locate()
        }

        PreferenceAction {
            visible: root.preferences.nightEnabled && root.preferences.mode === "location"
            icon: "cloud"
            text: I18n.tr("Use weather location")
            trailingIcon: ""
            enabled: DisplayColor.ready
            onClicked: DisplayColor.useWeatherLocation()
        }

        PreferenceSlider {
            visible: root.preferences.nightEnabled && root.preferences.mode !== "fixed"
            label: I18n.tr("Day temperature")
            valueLabel: Math.round(root.preferences.dayTemperature) + " K"
            value: root.preferences.dayTemperature
            from: 1000
            to: 10000
            stepSize: 100
            onMoved: value => DisplayColor.setPreference("dayTemperature", value)
        }

        PreferenceSlider {
            last: true
            visible: root.preferences.nightEnabled && root.preferences.mode !== "fixed"
            label: I18n.tr("Transition duration")
            valueLabel: Math.round(root.preferences.transition) + I18n.tr(" min")
            value: root.preferences.transition
            from: 0
            to: 180
            stepSize: 1
            onMoved: value => DisplayColor.setPreference("transition", value)
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DisplayColor.locationError !== ""
            message: DisplayColor.locationError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: DisplayColor.scheduleWarning !== ""
            message: DisplayColor.scheduleWarning
        }

        // Current status
        PreferenceHeader {
            visible: root.preferences.nightEnabled && root.preferences.mode !== "fixed"
            text: I18n.tr("Current status")
        }

        PreferenceInfo {
            id: scheduledTemperatureInfo

            first: true
            visible: root.preferences.nightEnabled && root.preferences.mode !== "fixed"
            label: I18n.tr("Scheduled temperature")
            value: I18n.tr("%1 K").arg(DisplayColor.schedule.temperature)

            SettingsSearchAnchor {
                target: scheduledTemperatureInfo
                declaration:
                    '{"id":"displays.gamma.section.current-status","route":"displays.gamma","title":"Current status","context":"GammaControlPage","icon":"brightness_6","aliases":["general.displays.gamma.section.current-status"]}'
            }
        }

        PreferenceInfo {
            visible: root.preferences.nightEnabled && root.preferences.mode !== "fixed"
            label: I18n.tr("Period")
            value: DisplayColor.schedule.period === "day" ? I18n.tr("Daytime") : I18n.tr("Nighttime")
            subtext: DisplayColor.schedule.transitioning ? I18n.tr("Transitioning") : ""
            last: !(DisplayColor.schedule.next > 0)
        }

        PreferenceInfo {
            last: true
            visible: DisplayColor.schedule.next > 0
            label: DisplayColor.schedule.transitioning ? I18n.tr("Transition ends") : I18n.tr(
                                                             "Next transition")
            value: Qt.formatDateTime(new Date(DisplayColor.schedule.next), "ddd hh:mm")
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            readonly property var failedOutputs: DisplayColor.outputs.filter(o => o.state === "failed"
                                                                                  || o.state
                                                                                  === "unavailable")
            visible: DisplayColor.available && failedOutputs.length > 0
            tone: "error"
            message: I18n.tr("Gamma control unavailable: %1").arg(failedOutputs.map(o => o.name).join(", "))
        }
    }
}

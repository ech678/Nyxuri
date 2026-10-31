import QtQuick
import QtQuick.Layouts
import qs.services
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Language & region page (T3 M4): NexusPageBase scaffold + M1 atom rows.
// The functional location picker stays a custom editor inside a connected
// card — Caelestia ships only a placeholder there, Nyxuri has the real thing.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("language-region")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false

    signal navigateRequested(string pageId)

    function closeChildWindows() {
        locationPicker.closeChildWindows();
    }

    readonly property var languageOptions: I18nService.supportedLanguages.map(lang => ({
        "label": lang.label,
        "value": lang.code
    }))
    readonly property var temperatureOptions: [
        {
            "label": "°C",
            "value": "celsius"
        },
        {
            "label": "°F",
            "value": "fahrenheit"
        }
    ]
    readonly property var clockOptions: [
        {
            "label": I18n.tr("24-hour"),
            "value": "24"
        },
        {
            "label": I18n.tr("12-hour"),
            "value": "12"
        }
    ]

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Language
        PreferenceHeader {
            first: true
            text: I18n.tr("Language")
        }

        PreferenceSelect {
            id: languageSelect

            first: true
            last: true
            icon: "language"
            label: I18n.tr("Interface language")
            subtext: I18n.tr("The language used in the shell UI")
            model: root.languageOptions
            currentValue: UiPreferences.language
            inputRegionService: PopupInputRegionService
            onSelected: value => {
                return UiPreferences.setLanguage(value);
            }

            SettingsSearchAnchor {
                id: searchAnchor0
                target: languageSelect
                declaration:
                    '{"id":"language-region.section.language","route":"language-region","title":"Language","context":"LanguageAndRegionPage","icon":"language","aliases":["general.language-region.section.language"]}'
            }
        }

        // Region & weather location
        PreferenceHeader {
            text: I18n.tr("Region & weather location")
        }

        ConnectedRect {
            id: locationCard

            first: true
            last: true
            Layout.fillWidth: true
            implicitHeight: locationPicker.implicitHeight + NexusStyle.padding.medium * 2

            LocationPicker {
                id: locationPicker

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                parentModal: root.parentModal
                active: root.presentationActive && root.visible
            }

            SettingsSearchAnchor {
                id: searchAnchor1
                target: locationCard
                declaration:
                    '{"id":"language-region.section.region-weather-location","route":"language-region","title":"Region & weather location","context":"LanguageAndRegionPage","icon":"language","aliases":["general.language-region.section.region-weather-location"]}'
            }
        }

        // Units
        PreferenceHeader {
            text: I18n.tr("Units")
        }

        PreferenceSelect {
            id: weatherUnitsSelect

            first: true
            icon: "thermostat"
            label: I18n.tr("Weather temperature")
            subtext: I18n.tr("Units for weather temperatures")
            model: root.temperatureOptions
            currentValue: UiPreferences.weatherTemperatureUnit
            inputRegionService: PopupInputRegionService
            onSelected: value => {
                return UiPreferences.setWeatherTemperatureUnit(value);
            }

            SettingsSearchAnchor {
                id: searchAnchor3
                target: weatherUnitsSelect
                declaration:
                    '{"id":"language-region.section.units","route":"language-region","title":"Units","context":"LanguageAndRegionPage","icon":"language","aliases":["general.language-region.section.units"]}'
            }
        }

        PreferenceSelect {
            last: true
            icon: "device_thermostat"
            label: I18n.tr("Hardware temperature")
            subtext: I18n.tr("Units for CPU and GPU temperatures")
            model: root.temperatureOptions
            currentValue: UiPreferences.systemTemperatureUnit
            inputRegionService: PopupInputRegionService
            onSelected: value => {
                return UiPreferences.setSystemTemperatureUnit(value);
            }
        }

        // Time & date
        PreferenceHeader {
            text: I18n.tr("Time & date")
        }

        PreferenceSelect {
            id: clockSelect

            first: true
            last: true
            icon: "schedule"
            label: I18n.tr("Clock format")
            subtext: I18n.tr("How times are shown across the shell")
            model: root.clockOptions
            currentValue: UiPreferences.useTwelveHourClock ? "12" : "24"
            inputRegionService: PopupInputRegionService
            onSelected: value => {
                return UiPreferences.setUseTwelveHourClock(value === "12");
            }

            SettingsSearchAnchor {
                id: searchAnchor4
                target: clockSelect
                declaration:
                    '{"id":"language-region.section.time-date","route":"language-region","title":"Time & date","context":"LanguageAndRegionPage","icon":"language","aliases":["general.language-region.section.time-date"]}'
            }
        }
    }
}

import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

StyledFlickable {
    id: root

    property var parentModal: null
    property bool presentationActive: false

    signal navigateRequested(string pageId)

    function closeChildWindows() {
        locationPicker.closeChildWindows();
    }

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingXL

        SettingsSection {
            id: searchSection0
            Layout.fillWidth: true
            flat: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                target: searchSection0
                declaration:
                    '{"id":"general.language-region.section.language","route":"general.language-region","title":"Language","context":"LanguageAndRegionPage","icon":"language","aliases":[]}'
            }
            iconName: "translate"

            SettingsRow {
                Layout.fillWidth: true
                iconName: "language"
                title: I18n.tr("Interface language")

                trailing: SearchSelectMenuField {
                    Layout.preferredWidth: 190
                    options: I18nService.supportedLanguages
                    value: UiPreferences.language
                    placeholder: I18n.tr("Select language")
                    textRole: "label"
                    valueRole: "code"
                    closeOnAccept: true
                    onAccepted: value => {
                        return UiPreferences.setLanguage(value);
                    }
                }
            }
        }

        SettingsSection {
            id: searchSection1
            Layout.fillWidth: true
            flat: true
            title: searchAnchor1.title
            SettingsSearchAnchor {
                id: searchAnchor1
                target: searchSection1
                declaration:
                    '{"id":"general.language-region.section.region-weather-location","route":"general.language-region","title":"Region & weather location","context":"LanguageAndRegionPage","icon":"language","aliases":[]}'
            }
            iconName: "map"

            LocationPicker {
                id: locationPicker

                Layout.fillWidth: true
                parentModal: root.parentModal
                active: root.presentationActive && root.visible
            }
        }

        SettingsSection {
            id: searchSection3
            Layout.fillWidth: true
            flat: true
            title: searchAnchor3.title
            SettingsSearchAnchor {
                id: searchAnchor3
                target: searchSection3
                declaration:
                    '{"id":"general.language-region.section.units","route":"general.language-region","title":"Units","context":"LanguageAndRegionPage","icon":"language","aliases":[]}'
            }
            iconName: "thermostat"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Weather temperature")

                trailing: StyledButtonGroup {
                    model: [({
                                 "value": "celsius",
                                 "label": "°C"
                             }), ({
                                      "value": "fahrenheit",
                                      "label": "°F"
                                  })]
                    currentValue: UiPreferences.weatherTemperatureUnit
                    buttonMinWidth: 56
                    onValueSelected: value => {
                        return UiPreferences.setWeatherTemperatureUnit(value);
                    }
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Hardware temperature")

                trailing: StyledButtonGroup {
                    model: [({
                                 "value": "celsius",
                                 "label": "°C"
                             }), ({
                                      "value": "fahrenheit",
                                      "label": "°F"
                                  })]
                    currentValue: UiPreferences.systemTemperatureUnit
                    buttonMinWidth: 56
                    onValueSelected: value => {
                        return UiPreferences.setSystemTemperatureUnit(value);
                    }
                }
            }
        }

        SettingsSection {
            id: searchSection4
            Layout.fillWidth: true
            flat: true
            title: searchAnchor4.title
            SettingsSearchAnchor {
                id: searchAnchor4
                target: searchSection4
                declaration:
                    '{"id":"general.language-region.section.time-date","route":"general.language-region","title":"Time & date","context":"LanguageAndRegionPage","icon":"language","aliases":[]}'
            }
            iconName: "schedule"

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Clock format")

                trailing: StyledButtonGroup {
                    model: [({
                                 "value": "24",
                                 "label": I18n.tr("24-hour")
                             }), ({
                                      "value": "12",
                                      "label": I18n.tr("12-hour")
                                  })]
                    currentValue: UiPreferences.useTwelveHourClock ? "12" : "24"
                    buttonMinWidth: 78
                    onValueSelected: value => {
                        return UiPreferences.setUseTwelveHourClock(value === "12");
                    }
                }
            }
        }
    }
}

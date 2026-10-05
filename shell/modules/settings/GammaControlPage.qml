import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

SidebarFlickable {
    id: root
    motionEnabled: !searchAnchorsEnabled
    property real contentPadding: Metrics.pageMargin
    property bool searchAnchorsEnabled: true
    readonly property var preferences: DisplayColor.preferences
    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + root.contentPadding * 2 + root.contentTopInset
    function timeText(minutes) {
        return Math.floor(minutes / 60).toString().padStart(2, "0") + ":" + (minutes % 60).toString().padStart(
                    2, "0");
    }
    function setTime(key, text) {
        const parts = text.split(":").map(Number);
        if (parts.length === 2 && parts[0] >= 0 && parts[0] < 24 && parts[1] >= 0 && parts[1] < 60)
            DisplayColor.setPreference(key, parts[0] * 60 + parts[1]);
    }
    ColumnLayout {
        id: content
        width: Math.min(640, Math.max(0, root.width - root.contentPadding * 2))
        x: Math.max(root.contentPadding, (root.width - width) / 2)
        y: root.contentPadding + root.contentTopInset
        spacing: Metrics.spacingXL
        InlineStatusBanner {
            Layout.topMargin: root.gapFor(0, 1)

            Layout.fillWidth: true
            visible: !DisplayColor.available
            message: I18n.tr("The compositor does not provide Gamma control")
        }
        InlineStatusBanner {
            Layout.topMargin: root.gapFor(1, 1)

            Layout.fillWidth: true
            visible: DisplayColor.error !== ""
            tone: "error"
            message: DisplayColor.error
        }
        SettingsSection {
            id: searchSection0
            pullExpansion: root.detailExpansion
            Layout.topMargin: root.gapFor(2, 1)
            Layout.fillWidth: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                registerAnchor: root.searchAnchorsEnabled
                target: searchSection0
                declaration:
                    '{"id":"displays.gamma.section.color","route":"displays.gamma","title":"Color","context":"GammaControlPage","icon":"brightness_6","aliases":["general.displays.gamma.section.color"]}'
            }
            iconName: "contrast"
            flat: true
            enabled: DisplayColor.ready
            GeneralSliderSetting {
                title: I18n.tr("Gamma")
                from: 50
                to: 200
                stepSize: 1
                suffix: "%"
                value: root.preferences.gamma * 100
                onMoved: value => DisplayColor.setPreference("gamma", value / 100)
            }
            GeneralSliderSetting {
                title: I18n.tr("Contrast")
                from: 50
                to: 200
                stepSize: 1
                suffix: "%"
                value: root.preferences.contrast * 100
                onMoved: value => DisplayColor.setPreference("contrast", value / 100)
            }
            GeneralSliderSetting {
                title: I18n.tr("Software dimming")
                from: 25
                to: 100
                stepSize: 1
                suffix: "%"
                value: root.preferences.dimming * 100
                onMoved: value => DisplayColor.setDimming(value / 100)
            }
        }
        SettingsSection {
            pullExpansion: root.detailExpansion
            Layout.topMargin: root.gapFor(3, 1)

            Layout.fillWidth: true
            flat: true
            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Night Mode")
                iconName: "nightlight"
                trailing: StyledSwitch {
                    checked: root.preferences.nightEnabled
                    Accessible.name: I18n.tr("Night Mode")
                    onToggled: DisplayColor.setPreference("nightEnabled", checked)
                }
            }
            GeneralSliderSetting {
                visible: root.preferences.nightEnabled
                title: I18n.tr("Night temperature")
                from: 1000
                to: 6500
                stepSize: 100
                suffix: " K"
                value: root.preferences.nightTemperature
                onMoved: value => DisplayColor.setPreference("nightTemperature", value)
            }
        }
        SettingsSection {
            id: searchSection1
            pullExpansion: root.detailExpansion
            Layout.topMargin: root.gapFor(4, 1)
            Layout.fillWidth: true
            visible: root.preferences.nightEnabled
            title: searchAnchor1.title
            SettingsSearchAnchor {
                id: searchAnchor1
                registerAnchor: root.searchAnchorsEnabled
                target: searchSection1
                declaration:
                    '{"id":"displays.gamma.section.schedule","route":"displays.gamma","title":"Schedule","context":"GammaControlPage","icon":"brightness_6","aliases":["general.displays.gamma.section.schedule"]}'
            }
            iconName: "schedule"
            flat: true
            DisplayChoice {
                Layout.fillWidth: true
                title: I18n.tr("Automatic control")
                options: [
                    {
                        value: "fixed",
                        label: I18n.tr("Fixed temperature")
                    },
                    {
                        value: "time",
                        label: I18n.tr("Time")
                    },
                    {
                        value: "location",
                        label: I18n.tr("Sunrise and sunset")
                    }
                ]
                value: root.preferences.mode
                onSelected: value => DisplayColor.setPreference("mode", value)
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: root.preferences.mode === "time"
                title: I18n.tr("Night starts")
                iconName: "nightlight"
                trailing: OutlinedTextField {
                    Layout.preferredWidth: 140
                    Layout.minimumWidth: 140
                    Layout.maximumWidth: 140
                    Layout.fillWidth: false
                    Accessible.name: I18n.tr("Night starts")
                    text: root.timeText(root.preferences.start)
                    validator: RegularExpressionValidator {
                        regularExpression: /([01][0-9]|2[0-3]):[0-5][0-9]/
                    }
                    onEditingFinished: root.setTime("start", text)
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: root.preferences.mode === "time"
                title: I18n.tr("Day starts")
                iconName: "light_mode"
                trailing: OutlinedTextField {
                    Layout.preferredWidth: 140
                    Layout.minimumWidth: 140
                    Layout.maximumWidth: 140
                    Layout.fillWidth: false
                    Accessible.name: I18n.tr("Day starts")
                    text: root.timeText(root.preferences.end)
                    validator: RegularExpressionValidator {
                        regularExpression: /([01][0-9]|2[0-3]):[0-5][0-9]/
                    }
                    onEditingFinished: root.setTime("end", text)
                }
            }
            GridLayout {
                Layout.fillWidth: true
                columns: width > 400 ? 2 : 1
                visible: root.preferences.mode === "location"
                Repeater {
                    model: [
                        {
                            key: "latitude",
                            label: I18n.tr("Latitude"),
                            limit: 90
                        },
                        {
                            key: "longitude",
                            label: I18n.tr("Longitude"),
                            limit: 180
                        }
                    ]
                    OutlinedTextField {
                        required property var modelData
                        Layout.fillWidth: true
                        labelText: modelData.label
                        text: root.preferences[modelData.key] === null ? "" : String(
                                                                             root.preferences[modelData.key])
                        validator: DoubleValidator {
                            bottom: -modelData.limit
                            top: modelData.limit
                            locale: "C"
                        }
                        onEditingFinished: DisplayColor.setPreference(modelData.key, text.trim() === "" ? null :
                                                                                                          Number(text))
                    }
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: root.preferences.mode === "location"
                title: I18n.tr("Automatic IP location")

                trailing: StyledSwitch {
                    checked: root.preferences.useIP
                    Accessible.name: I18n.tr("Automatic IP location")
                    onToggled: DisplayColor.setPreference("useIP", checked)
                    InlineBusyIndicator {
                        anchors.centerIn: parent
                        busy: DisplayColor.locating
                    }
                }
            }
            InlineStatusBanner {
                Layout.fillWidth: true
                visible: DisplayColor.locationError !== ""
                message: DisplayColor.locationError
            }
            ActionButton {
                visible: root.preferences.mode === "location" && root.preferences.useIP
                text: I18n.tr("Refresh location")
                enabled: !DisplayColor.locating
                onClicked: DisplayColor.locate()
            }
            ActionButton {
                visible: root.preferences.mode === "location"
                enabled: DisplayColor.ready
                Layout.alignment: Qt.AlignRight
                text: I18n.tr("Use weather location")
                onClicked: DisplayColor.useWeatherLocation()
            }
            GeneralSliderSetting {
                visible: root.preferences.mode !== "fixed"
                title: I18n.tr("Day temperature")
                from: 1000
                to: 10000
                stepSize: 100
                suffix: " K"
                value: root.preferences.dayTemperature
                onMoved: value => DisplayColor.setPreference("dayTemperature", value)
            }
            GeneralSliderSetting {
                visible: root.preferences.mode !== "fixed"
                title: I18n.tr("Transition duration")
                from: 0
                to: 180
                stepSize: 1
                suffix: I18n.tr(" min")
                value: root.preferences.transition
                onMoved: value => DisplayColor.setPreference("transition", value)
            }
            InlineStatusBanner {
                Layout.fillWidth: true
                visible: DisplayColor.scheduleWarning !== ""
                message: DisplayColor.scheduleWarning
            }
        }

        SettingsSection {
            id: searchSection2
            pullExpansion: root.detailExpansion
            Layout.topMargin: root.gapFor(5, 1)
            Layout.fillWidth: true
            visible: root.preferences.nightEnabled && root.preferences.mode !== "fixed"
            title: searchAnchor2.title
            SettingsSearchAnchor {
                id: searchAnchor2
                registerAnchor: root.searchAnchorsEnabled
                target: searchSection2
                declaration:
                    '{"id":"displays.gamma.section.current-status","route":"displays.gamma","title":"Current status","context":"GammaControlPage","icon":"brightness_6","aliases":["general.displays.gamma.section.current-status"]}'
            }
            iconName: DisplayColor.schedule.period === "day" ? "light_mode" : "nightlight"
            flat: true
            SettingsRow {
                Layout.fillWidth: true
                visible: true
                title: I18n.tr("Scheduled temperature")
                iconName: "thermostat"
                supportingText: ""
                trailing: Text {
                    text: I18n.tr("%1 K").arg(DisplayColor.schedule.temperature)
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Typography.bodyLarge.family
                    font.pixelSize: Typography.bodyLarge.pixelSize
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: true
                title: I18n.tr("Period")
                iconName: DisplayColor.schedule.period === "day" ? "light_mode" : "nightlight"
                supportingText: DisplayColor.schedule.transitioning ? I18n.tr("Transitioning") : ""
                trailing: Text {
                    text: DisplayColor.schedule.period === "day" ? I18n.tr("Daytime") : I18n.tr("Nighttime")
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Typography.bodyLarge.family
                    font.pixelSize: Typography.bodyLarge.pixelSize
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: DisplayColor.schedule.next > 0
                title: DisplayColor.schedule.transitioning ? I18n.tr("Transition ends") : I18n.tr(
                                                                 "Next transition")
                iconName: "schedule"
                supportingText: ""
                trailing: Text {
                    text: Qt.formatDateTime(new Date(DisplayColor.schedule.next), "ddd hh:mm")
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Typography.bodyLarge.family
                    font.pixelSize: Typography.bodyLarge.pixelSize
                }
            }
        }

        InlineStatusBanner {
            Layout.topMargin: root.gapFor(6, 1)

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

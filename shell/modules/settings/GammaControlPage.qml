import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

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
            message: qsTr("The compositor does not provide Gamma control")
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
                    '{"id":"general.displays.gamma.section.color","route":"general.displays.gamma","title":"Color","context":"GammaControlPage","icon":"brightness_6","aliases":[]}'
            }
            iconName: "contrast"
            flat: true
            enabled: DisplayColor.ready
            GeneralSliderSetting {
                title: qsTr("Gamma")
                from: 50
                to: 200
                stepSize: 1
                suffix: "%"
                value: root.preferences.gamma * 100
                onMoved: value => DisplayColor.setPreference("gamma", value / 100)
            }
            GeneralSliderSetting {
                title: qsTr("Contrast")
                from: 50
                to: 200
                stepSize: 1
                suffix: "%"
                value: root.preferences.contrast * 100
                onMoved: value => DisplayColor.setPreference("contrast", value / 100)
            }
            GeneralSliderSetting {
                title: qsTr("Software dimming")
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
                title: qsTr("Night Mode")
                iconName: "nightlight"
                trailing: StyledSwitch {
                    checked: root.preferences.nightEnabled
                    Accessible.name: qsTr("Night Mode")
                    onToggled: DisplayColor.setPreference("nightEnabled", checked)
                }
            }
            GeneralSliderSetting {
                visible: root.preferences.nightEnabled
                title: qsTr("Night temperature")
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
                    '{"id":"general.displays.gamma.section.schedule","route":"general.displays.gamma","title":"Schedule","context":"GammaControlPage","icon":"brightness_6","aliases":[]}'
            }
            iconName: "schedule"
            flat: true
            DisplayChoice {
                Layout.fillWidth: true
                title: qsTr("Automatic control")
                options: [
                    {
                        value: "fixed",
                        label: qsTr("Fixed temperature")
                    },
                    {
                        value: "time",
                        label: qsTr("Time")
                    },
                    {
                        value: "location",
                        label: qsTr("Sunrise and sunset")
                    }
                ]
                value: root.preferences.mode
                onSelected: value => DisplayColor.setPreference("mode", value)
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: root.preferences.mode === "time"
                title: qsTr("Night starts")
                iconName: "nightlight"
                trailing: OutlinedTextField {
                    Layout.preferredWidth: 140
                    Layout.minimumWidth: 140
                    Layout.maximumWidth: 140
                    Layout.fillWidth: false
                    Accessible.name: qsTr("Night starts")
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
                title: qsTr("Day starts")
                iconName: "light_mode"
                trailing: OutlinedTextField {
                    Layout.preferredWidth: 140
                    Layout.minimumWidth: 140
                    Layout.maximumWidth: 140
                    Layout.fillWidth: false
                    Accessible.name: qsTr("Day starts")
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
                            label: qsTr("Latitude"),
                            limit: 90
                        },
                        {
                            key: "longitude",
                            label: qsTr("Longitude"),
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
                title: qsTr("Automatic IP location")

                trailing: StyledSwitch {
                    checked: root.preferences.useIP
                    Accessible.name: qsTr("Automatic IP location")
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
                text: qsTr("Refresh location")
                enabled: !DisplayColor.locating
                onClicked: DisplayColor.locate()
            }
            ActionButton {
                visible: root.preferences.mode === "location"
                enabled: DisplayColor.ready
                Layout.alignment: Qt.AlignRight
                text: qsTr("Use weather location")
                onClicked: DisplayColor.useWeatherLocation()
            }
            GeneralSliderSetting {
                visible: root.preferences.mode !== "fixed"
                title: qsTr("Day temperature")
                from: 1000
                to: 10000
                stepSize: 100
                suffix: " K"
                value: root.preferences.dayTemperature
                onMoved: value => DisplayColor.setPreference("dayTemperature", value)
            }
            GeneralSliderSetting {
                visible: root.preferences.mode !== "fixed"
                title: qsTr("Transition duration")
                from: 0
                to: 180
                stepSize: 1
                suffix: qsTr(" min")
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
                    '{"id":"general.displays.gamma.section.current-status","route":"general.displays.gamma","title":"Current status","context":"GammaControlPage","icon":"brightness_6","aliases":[]}'
            }
            iconName: DisplayColor.schedule.period === "day" ? "light_mode" : "nightlight"
            flat: true
            SettingsRow {
                Layout.fillWidth: true
                visible: true
                title: qsTr("Scheduled temperature")
                iconName: "thermostat"
                supportingText: ""
                trailing: Text {
                    text: qsTr("%1 K").arg(DisplayColor.schedule.temperature)
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Typography.bodyLarge.family
                    font.pixelSize: Typography.bodyLarge.pixelSize
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: true
                title: qsTr("Period")
                iconName: DisplayColor.schedule.period === "day" ? "light_mode" : "nightlight"
                supportingText: DisplayColor.schedule.transitioning ? qsTr("Transitioning") : ""
                trailing: Text {
                    text: DisplayColor.schedule.period === "day" ? qsTr("Daytime") : qsTr("Nighttime")
                    color: Appearance.colors.colOnSurfaceVariant
                    font.family: Typography.bodyLarge.family
                    font.pixelSize: Typography.bodyLarge.pixelSize
                }
            }
            SettingsRow {
                Layout.fillWidth: true
                visible: DisplayColor.schedule.next > 0
                title: DisplayColor.schedule.transitioning ? qsTr("Transition ends") : qsTr("Next transition")
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
            message: qsTr("Gamma control unavailable: %1").arg(failedOutputs.map(o => o.name).join(", "))
        }
    }
}

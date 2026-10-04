import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.app.services
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    property string uv: "--"
    property string feelsLike: "--"
    property string humidity: "--"
    property string wind: "--"
    property string pressure: "--"
    property string visibility: "--"

    function syncParams() {
        if (!WeatherService.hasValidData) {
            root.uv = "--";
            root.feelsLike = "--";
            root.humidity = "--";
            root.wind = "--";
            root.pressure = "--";
            root.visibility = "--";
            return;
        }
        root.uv = Math.round(WeatherService.currentUvIndex || 0).toString();
        root.feelsLike = Math.round(UiPreferences.weatherTemperature(WeatherService.currentFeelsLikeC || 0))
                + UiPreferences.weatherTemperatureSymbol();
        root.humidity = Math.round(WeatherService.currentRelativeHumidity || 0) + "%";
        root.wind = Math.round((WeatherService.currentWindSpeedMs || 0) * 3.6) + " km/h";
        root.pressure = Math.round(WeatherService.currentPressureHpa || 0) + " hPa";
        root.visibility = Math.round((WeatherService.currentVisibilityM || 0) / 1000) + " km";
    }

    implicitHeight: grid.implicitHeight
    implicitWidth: 300
    Component.onCompleted: syncParams()

    Connections {
        function onDataChanged() {
            syncParams();
        }

        target: WeatherService
    }

    Connections {
        function onWeatherTemperatureUnitChanged() {
            root.syncData();
        }

        target: UiPreferences
    }

    GridLayout {
        id: grid

        anchors.fill: parent
        columns: 3
        rowSpacing: 12
        columnSpacing: 24

        Repeater {
            model: [
                {
                    "icon": "sunny",
                    "label": I18n.tr("UV index"),
                    "value": root.uv
                },
                {
                    "icon": "thermostat",
                    "label": I18n.tr("Feels like"),
                    "value": root.feelsLike
                },
                {
                    "icon": "water_drop",
                    "label": I18n.tr("Humidity"),
                    "value": root.humidity
                },
                {
                    "icon": "air",
                    "label": I18n.tr("Wind speed"),
                    "value": root.wind
                },
                {
                    "icon": "compress",
                    "label": I18n.tr("Pressure"),
                    "value": root.pressure
                },
                {
                    "icon": "visibility",
                    "label": I18n.tr("Visibility"),
                    "value": root.visibility
                }
            ]

            delegate: ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    MaterialSymbol {
                        text: modelData.icon
                        iconSize: 26
                        color: Appearance.applyAlpha(Appearance.colors.colOnSurfaceVariant, 0.7)
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Text {
                        Layout.fillWidth: true
                        text: modelData.label
                        color: Appearance.colors.colOnSurfaceVariant
                        font.family: Fonts.ui
                        font.pixelSize: 16
                        elide: Text.ElideRight
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: modelData.value
                    color: Appearance.colors.colOnSurface
                    font.family: Fonts.numeric
                    font.pixelSize: 24
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }
            }
        }
    }
}

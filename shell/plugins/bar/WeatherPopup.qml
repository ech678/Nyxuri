// Fork & Trim: end4-pC modules/ii/bar/WeatherPopup.qml (D1 weather wiring)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// D1: rebound from the never-existing iNiR `Weather` singleton to
// WeatherService. Values format from the backend's SI fields; sunrise/sunset
// and chance-of-rain come from the first daily/hourly forecast entries.
// Missing data renders dashes, never fake numbers.

import qs.services
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

StyledPopup {
    id: root

    readonly property var todayDaily: WeatherService.hasValidData && WeatherService.dailyForecast.length > 0 ? WeatherService.dailyForecast[0] : null
    readonly property var nowHourly: WeatherService.hasValidData && WeatherService.hourlyForecast.length > 0 ? WeatherService.hourlyForecast[0] : null
    readonly property string tempText: WeatherService.hasValidData ? (Math.round(WeatherService.currentTemperatureC) + "°") : "--°"

    function epochToClock(seconds): string {
        if (!seconds || isNaN(seconds))
            return "--:--";
        const d = new Date(seconds * 1000);
        return Qt.formatDateTime(d, "HH:mm");
    }

    ColumnLayout {
        id: mainLayout
        implicitWidth: Math.max(370, Math.round(390 * Appearance.fontSizeScale))
        spacing: Appearance.sizes.spacingSmall

        Layout.topMargin: -8
        Layout.leftMargin: -8
        Layout.rightMargin: -8

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(128, Math.round(132 * Appearance.fontSizeScale))

            topLeftRadius: Appearance.rounding.normal - 2
            topRightRadius: Appearance.rounding.normal - 2
            bottomLeftRadius: Appearance.rounding.normal
            bottomRightRadius: Appearance.rounding.normal

            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: Appearance.colors.colPrimaryContainer
                }
                GradientStop {
                    position: 1.0
                    color: Appearance.colors.colSurfaceContainerLow
                }
            }

            Item {
                anchors.fill: parent
                anchors.margins: Math.max(16, Appearance.sizes.spacingLarge)

                ColumnLayout {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.topMargin: -6
                    spacing: -2

                    StyledText {
                        visible: WeatherService.locationName.length > 0
                        text: WeatherService.locationName
                        font.pixelSize: NexusStyle.font.bodyLarge * BarScale.font
                        font.weight: Font.DemiBold
                        color: Appearance.colors.colOnLayer0
                    }

                    StyledText {
                        text: WeatherService.hasValidData ? WeatherService.currentWeatherText : Translation.tr("No data")
                        font.pixelSize: NexusStyle.font.bodySmall * BarScale.font
                        color: Appearance.colors.colOnLayer0
                        opacity: 0.6
                    }
                }

                RowLayout {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: -8
                    spacing: 4

                    StyledText {
                        text: root.tempText
                        font.pixelSize: NexusStyle.font.displayMedium * BarScale.font
                        font.weight: Font.Light
                        color: Appearance.colors.colOnLayer0
                    }
                }

                MaterialShapeWrappedMaterialSymbol {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.topMargin: -3
                    shape: MaterialShapeCanvas.Shape.Sunny
                    text: WeatherService.hasValidData ? WeatherService.currentIconName : "cloud"
                    iconSize: 40
                    implicitSize: 64
                    color: Qt.alpha(Appearance.colors.colOnLayer0, 0.15)
                    colSymbol: Appearance.colors.colPrimary
                }

                ColumnLayout {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.rightMargin: 6
                    anchors.bottomMargin: -1
                    spacing: -2

                    RowLayout {
                        spacing: 4
                        Layout.alignment: Qt.AlignRight
                        MaterialSymbol {
                            text: "wb_twilight"
                            iconSize: NexusStyle.font.bodySmall * BarScale.font
                            color: Appearance.colors.colPrimary
                        }
                        StyledText {
                            text: root.todayDaily ? root.epochToClock(root.todayDaily.sunrise) : "--:--"
                            font.pixelSize: NexusStyle.font.labelSmall * BarScale.font
                            color: Appearance.colors.colOnLayer0
                            opacity: 0.8
                        }
                    }

                    RowLayout {
                        spacing: 4
                        Layout.alignment: Qt.AlignRight
                        MaterialSymbol {
                            text: "bedtime"
                            iconSize: NexusStyle.font.bodySmall * BarScale.font
                            color: Appearance.colors.colPrimary
                        }
                        StyledText {
                            text: root.todayDaily ? root.epochToClock(root.todayDaily.sunset) : "--:--"
                            font.pixelSize: NexusStyle.font.labelSmall * BarScale.font
                            color: Appearance.colors.colOnLayer0
                            opacity: 0.8
                        }
                    }
                }
            }
        }

        GridLayout {
            id: gridLayout
            columns: 2
            rowSpacing: 6
            columnSpacing: 6
            uniformCellWidths: true

            Layout.leftMargin: 2
            Layout.rightMargin: 2
            Layout.bottomMargin: 2
            Layout.fillWidth: true

            WeatherCard {
                title: Translation.tr("Rain?")
                symbol: "rainy"
                value: root.nowHourly ? `${Math.round(root.nowHourly.precipitationProbability)}%` : "--"
            }
            WeatherCard {
                title: Translation.tr("Wind")
                symbol: "air"
                value: WeatherService.hasValidData ? `${(WeatherService.currentWindSpeedMs * 3.6).toFixed(1)} km/h` : "--"
            }
            WeatherCard {
                title: Translation.tr("Precipitation")
                symbol: "rainy_light"
                value: root.nowHourly ? `${root.nowHourly.precipitationMm.toFixed(1)} mm` : "--"
            }
            WeatherCard {
                title: Translation.tr("Humidity")
                symbol: "humidity_low"
                value: WeatherService.hasValidData ? `${Math.round(WeatherService.currentRelativeHumidity)}%` : "--"
            }
            WeatherCard {
                title: Translation.tr("Visibility")
                symbol: "visibility"
                value: WeatherService.hasValidData ? `${(WeatherService.currentVisibilityM / 1000).toFixed(1)} km` : "--"
            }
            WeatherCard {
                title: Translation.tr("Pressure")
                symbol: "readiness_score"
                value: WeatherService.hasValidData ? `${Math.round(WeatherService.currentPressureHpa)} hPa` : "--"
            }
        }
    }
}

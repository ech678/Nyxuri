import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.app.services
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    property string locationName: I18n.tr("Weather")
    property string currentTemp: "--"
    property string currentIcon: "cloud"
    property string currentDesc: "--"
    property string highTemp: "--"
    property string lowTemp: "--"

    signal refreshRequested

    function syncData() {
        if (!WeatherService.hasValidData) {
            root.locationName = WeatherService.locationName || I18n.tr("Weather");
            root.currentTemp = "--";
            root.currentIcon = "cloud";
            root.currentDesc = "--";
            root.highTemp = "--";
            root.lowTemp = "--";
            return;
        }
        root.locationName = WeatherService.locationName || I18n.tr("Unknown");
        root.currentTemp = Math.round(UiPreferences.weatherTemperature(WeatherService.currentTemperatureC || 0)) + "°";
        root.currentIcon = WeatherService.currentIconName || "cloud";
        root.currentDesc = WeatherService.currentWeatherText || I18n.tr("Unknown");
        if (WeatherService.dailyForecast.count() > 0) {
            const today = WeatherService.dailyForecast.get(0);
            const dayPart = today.day || {};
            root.highTemp = Math.round(UiPreferences.weatherTemperature(Number(today.temperatureMaxC || dayPart.temperatureC || 0))) + "°";
            root.lowTemp = Math.round(UiPreferences.weatherTemperature(Number(today.temperatureMinC || 0))) + "°";
        } else {
            root.highTemp = "--";
            root.lowTemp = "--";
        }
    }

    implicitHeight: layout.implicitHeight
    implicitWidth: 300
    Component.onCompleted: syncData()

    Connections {
        function onDataChanged() {
            syncData();
        }

        target: WeatherService
    }

    Connections {
        function onWeatherTemperatureUnitChanged() {
            root.syncData();
        }

        target: UiPreferences
    }

    RowLayout {
        id: layout

        anchors.fill: parent
        spacing: 8

        MaterialSymbol {
            Layout.alignment: Qt.AlignVCenter
            text: root.currentIcon
            iconSize: 64
            fill: 1
            color: Appearance.colors.colPrimary
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignVCenter
            spacing: -4

            Text {
                text: root.locationName
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.ui
                font.pixelSize: Appearance.scaledFont(14)
                font.weight: Font.Medium
                elide: Text.ElideRight
                Layout.maximumWidth: 120
            }

            Text {
                text: root.currentTemp
                color: Appearance.colors.colOnSurface
                font.family: Fonts.numeric
                font.pixelSize: Appearance.scaledFont(42)
                font.weight: Font.Light
                lineHeight: 0.95
            }

            Text {
                text: "↑" + root.highTemp + "  ↓" + root.lowTemp
                color: Appearance.colors.colOnSurfaceVariant
                font.family: Fonts.numeric
                font.pixelSize: Appearance.scaledFont(12)
            }
        }

        Item {
            Layout.fillWidth: true
        }

        IconButton {
            Layout.alignment: Qt.AlignVCenter
            controlSize: 42
            enabled: !WeatherService.loading
            iconName: "refresh"
            iconSize: 26
            iconColor: Appearance.colors.colOnSurface
            iconRotation: WeatherService.loading ? 360 : 0
            accessibleName: I18n.tr("Refresh weather")
            onClicked: root.refreshRequested()

            RotationAnimation on iconRotation {
                from: 0
                to: 360
                duration: Appearance.motionLoopDuration(800)
                loops: Animation.Infinite
                running: root.visible && WeatherService.loading
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import qs.app.services
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    property bool active: false
    property real latitude: 0
    property real longitude: 0
    property string locationName: I18n.tr("Weather")
    property string currentTemp: "--"
    property string currentIcon: "cloud"
    property string currentDesc: "--"
    property string feelsLike: "--"
    property string humidity: "--"
    property string windSpeed: "--"
    property string pressure: "--"
    property bool isHourly: true
    property var hourlyData: []
    property var dailyData: []
    readonly property bool hasWeather: WeatherService.hasValidData

    function validNumber(value) {
        return value !== undefined && value !== null && !isNaN(Number(value));
    }

    function hasCoordinates() {
        return root.hasWeather && root.validNumber(root.latitude) && root.validNumber(root.longitude);
    }

    function cssColor(colorValue, alphaMultiplier) {
        const alpha = alphaMultiplier === undefined ? colorValue.a : colorValue.a * alphaMultiplier;
        return "rgba(" + Math.round(colorValue.r * 255) + "," + Math.round(colorValue.g * 255) + "," + Math.round(
                    colorValue.b * 255) + "," + Math.max(0, Math.min(1, alpha)).toFixed(3) + ")";
    }

    function updatedText() {
        if (WeatherService.loading)
            return root.hasWeather ? I18n.tr("Refreshing") : I18n.tr("Locating");

        if (WeatherService.status === "stale")
            return I18n.tr("Data may be stale");

        if (WeatherService.status === "partial")
            return I18n.tr("Partially updated");

        if (WeatherService.status === "error")
            return I18n.tr("Update failed");

        if (WeatherService.lastUpdated) {
            const updated = new Date(WeatherService.lastUpdated);
            if (!isNaN(updated.getTime()))
                return I18n.tr("Updated %1").arg(UiPreferences.shortTime(updated));
        }
        return I18n.tr("Live weather");
    }

    function weatherErrorText() {
        return WeatherService.errorMessage || I18n.tr("Weather data unavailable");
    }

    function hourlyTemperatureBound(findMaximum) {
        if (!root.hourlyData || root.hourlyData.length === 0)
            return 0;

        let bound = Number(root.hourlyData[0].temp);
        for (let index = 1; index < root.hourlyData.length; ++index) {
            const value = Number(root.hourlyData[index].temp);
            bound = findMaximum ? Math.max(bound, value) : Math.min(bound, value);
        }
        return bound;
    }

    function hourlyPointY(temperature, top, bottom) {
        let minimum = root.hourlyTemperatureBound(false);
        let maximum = root.hourlyTemperatureBound(true);
        if (Math.abs(maximum - minimum) < 0.1) {
            maximum += 1;
            minimum -= 1;
        }
        const normalized = (Number(temperature) - minimum) / (maximum - minimum);
        return bottom - normalized * (bottom - top);
    }

    function fetchData() {
        if (WeatherService.loading)
            return;

        WeatherService.refresh();
        if (weatherMapLoader.status === Loader.Ready && weatherMapLoader.item)
            weatherMapLoader.item.refreshMap();
    }

    function syncWeatherData() {
        if (!WeatherService.hasValidData) {
            root.locationName = WeatherService.locationName || I18n.tr("Weather");
            root.currentTemp = "--";
            root.currentIcon = "cloud";
            root.currentDesc = "--";
            root.feelsLike = "--";
            root.humidity = "--";
            root.windSpeed = "--";
            root.pressure = "--";
            root.hourlyData = [];
            root.dailyData = [];
            return;
        }
        root.latitude = Number(WeatherService.latitude);
        root.longitude = Number(WeatherService.longitude);
        root.locationName = WeatherService.locationName || I18n.tr("Unknown");
        root.currentTemp = Math.round(UiPreferences.weatherTemperature(WeatherService.currentTemperatureC))
                + "°";
        root.currentIcon = WeatherService.currentIconName || "cloud";
        root.currentDesc = WeatherService.currentWeatherText || I18n.tr("Unknown");
        root.feelsLike = Math.round(UiPreferences.weatherTemperature(WeatherService.currentFeelsLikeC))
                + UiPreferences.weatherTemperatureSymbol();
        root.humidity = Math.round(WeatherService.currentRelativeHumidity) + "%";
        root.windSpeed = Math.round(WeatherService.currentWindSpeedMs * 3.6) + " km/h";
        root.pressure = Math.round(WeatherService.currentPressureHpa) + " hPa";
        const nextHourly = [];
        const hourlyCount = Math.min(8, WeatherService.hourlyForecast.count());
        for (let hourIndex = 0; hourIndex < hourlyCount; ++hourIndex) {
            const item = WeatherService.hourlyForecast.get(hourIndex);
            const timeObject = new Date(Number(item.time || 0) * 1000);
            nextHourly.push({
                                "time": UiPreferences.hourTime(timeObject),
                                "temp": Math.round(UiPreferences.weatherTemperature(Number(item.temperatureC
                                                                                           || 0))),
                                "icon": item.iconName || "cloud",
                                "description": item.weatherText || I18n.tr("Unknown"),
                                "isDaylight": item.isDaylight === undefined ? true : item.isDaylight
                            });
        }
        root.hourlyData = nextHourly;
        const nextDaily = [];
        const dailyCount = Math.min(5, WeatherService.dailyForecast.count());
        for (let dayIndex = 0; dayIndex < dailyCount; ++dayIndex) {
            const item = WeatherService.dailyForecast.get(dayIndex);
            const dateObject = item.date ? new Date(item.date + "T00:00:00") : new Date(Number(item.time
                                                                                               || 0) * 1000);
            const dayPart = item.day || ({});
            nextDaily.push({
                               "day": dayIndex === 0 ? I18n.tr("Today") : Qt.formatDate(dateObject, "ddd"),
                               "date": Qt.formatDate(dateObject, "MMM d"),
                               "icon": dayPart.iconName || item.iconName || "cloud",
                               "description": dayPart.weatherText || item.weatherText || I18n.tr("Unknown"),
                               "maxTemp": Math.round(UiPreferences.weatherTemperature(Number(
                                                                                          item.temperatureMaxC
                                                                                          || dayPart.temperatureC
                                                                                          || 0))) + "°",
                               "minTemp": Math.round(UiPreferences.weatherTemperature(Number(
                                                                                          item.temperatureMinC
                                                                                          || 0))) + "°"
                           });
        }
        root.dailyData = nextDaily;
    }

    width: 960
    height: 570
    Material.theme: Appearance.m3colors.darkmode ? Material.Dark : Material.Light
    Material.accent: Appearance.colors.colPrimary
    Component.onCompleted: {
        root.syncWeatherData();
        if (!WeatherService.hasValidData && !WeatherService.loading)
            WeatherService.refresh();
    }

    Connections {
        function onDataChanged() {
            root.syncWeatherData();
        }

        target: WeatherService
    }

    Connections {
        function onWeatherTemperatureUnitChanged() {
            root.syncWeatherData();
        }

        function onUseTwelveHourClockChanged() {
            root.syncWeatherData();
        }

        target: UiPreferences
    }

    Timer {
        interval: 1.8e+06
        running: root.active
        repeat: true
        onTriggered: {
            if (!WeatherService.loading)
                WeatherService.refresh();
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 24

        // Left Column (Master)
        ColumnLayout {
            Layout.preferredWidth: 380
            Layout.fillHeight: true
            spacing: 16

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: root.hasWeather ? 0 : 1

                // Normal Weather Content
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: 24

                        WeatherCurrent {
                            Layout.fillWidth: true
                            onRefreshRequested: root.fetchData()
                        }

                        WeatherFiveDayForecast {
                            Layout.fillWidth: true
                        }

                        WeatherAQIIndicator {
                            Layout.fillWidth: true
                        }

                        WeatherSunriseSunset {
                            Layout.fillWidth: true
                        }
                    }
                }

                // Error / Loading State
                Item {
                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 10

                        BusyIndicator {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: 42
                            Layout.preferredHeight: 42
                            running: WeatherService.loading
                            visible: running
                            Material.accent: Appearance.colors.colPrimary
                        }

                        MaterialSymbol {
                            Layout.alignment: Qt.AlignHCenter
                            text: "cloud_off"
                            iconSize: 38
                            color: Appearance.colors.colError
                            visible: !WeatherService.loading
                        }

                        Text {
                            Layout.fillWidth: true
                            text: WeatherService.loading ? I18n.tr("Loading weather") : I18n.tr(
                                                               "Weather unavailable")
                            color: Appearance.colors.colOnSurface
                            font.family: Fonts.ui
                            font.pixelSize: 16
                            font.weight: Font.Medium
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Text {
                            Layout.fillWidth: true
                            text: WeatherService.loading ? I18n.tr("Finding your local forecast…") :
                                                           root.weatherErrorText()
                            color: Appearance.colors.colOnSurfaceVariant
                            font.family: Fonts.ui
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        // Right Column (Stack 1, 2, 3)
        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            spacing: 20

            // Parameters (Stack 2)
            WeatherParameters {
                Layout.fillWidth: true
                visible: root.hasWeather
            }
        }
    }

    component MetricTile: Rectangle {
        property string iconName: ""
        property string label: ""
        property string value: "--"
        property color containerColor: Appearance.colors.colPrimary
        property color contentColor: Appearance.colors.colOnPrimary
        property color accentColor: Appearance.colors.colOnPrimary

        implicitHeight: 32
        radius: Appearance.rounding.small
        color: containerColor

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 6
            anchors.rightMargin: 6
            spacing: 4

            MaterialSymbol {
                text: parent.parent.iconName
                iconSize: 15
                color: parent.parent.accentColor
                Layout.alignment: Qt.AlignVCenter
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: -2

                Text {
                    Layout.fillWidth: true
                    text: parent.parent.parent.label
                    color: Appearance.applyAlpha(parent.parent.parent.contentColor, 0.72)
                    font.family: Fonts.ui
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }

                Text {
                    Layout.fillWidth: true
                    text: parent.parent.parent.value
                    color: parent.parent.parent.contentColor
                    font.family: Fonts.numeric
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
            }
        }
    }
}

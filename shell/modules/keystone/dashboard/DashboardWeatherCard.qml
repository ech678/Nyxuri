import QtQuick
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects
import qs.app.services
import qs.shared.theme
import qs.shared.controls

Rectangle {
    id: root

    property bool active: false
    property real currentEpoch: Math.floor(Date.now() / 1000)
    property var today: ({})
    readonly property bool hasWeather: WeatherService.hasValidData
    readonly property bool night: currentIsNight()

    function validNumber(value) {
        return value !== undefined && value !== null && !isNaN(value);
    }

    function fmtTemp(value) {
        return hasWeather && validNumber(value) ? Math.round(UiPreferences.weatherTemperature(value)) + "°" :
                                                  "--";
    }

    function fmtTempPlain(value) {
        return hasWeather && validNumber(value) ? Math.round(UiPreferences.weatherTemperature(value)).toString(
                                                      ) : "--";
    }

    function currentIsNight() {
        const sunrise = Number(today.sunrise || 0);
        const sunset = Number(today.sunset || 0);
        if (sunrise > 0 && sunset > 0)
            return currentEpoch < sunrise || currentEpoch >= sunset;

        const current = WeatherService.current();
        if (current && current.isDaylight !== undefined)
            return !current.isDaylight;

        const hourly = (WeatherService.hourlyForecast && typeof WeatherService.hourlyForecast.count
                        === "function" && WeatherService.hourlyForecast.count() > 0)
              ? WeatherService.hourlyForecast.get(0) : ({});
        if (hourly.isDaylight !== undefined)
            return !hourly.isDaylight;

        const iconName = String(WeatherService.currentIconName || "").toLowerCase();
        return iconName.indexOf("night") >= 0 || iconName.indexOf("_night") >= 0;
    }

    function conditionText() {
        if (hasWeather)
            return WeatherService.currentWeatherText || qsTr("Unknown");

        if (WeatherService.loading)
            return qsTr("Getting weather");

        return qsTr("Weather is unavailable");
    }

    function updatedText() {
        if (WeatherService.loading)
            return qsTr("Refreshing");

        if (WeatherService.status === "stale")
            return qsTr("Data is old");

        if (WeatherService.status === "error")
            return qsTr("Update failed");

        if (WeatherService.lastUpdated) {
            const updated = new Date(WeatherService.lastUpdated);
            return UiPreferences.shortTime(updated);
        }
        return qsTr("Update pending");
    }

    function syncWeatherData() {
        today = (WeatherService.dailyForecast && typeof WeatherService.dailyForecast.count === "function"
                 && WeatherService.dailyForecast.count() > 0) ? WeatherService.dailyForecast.get(0) : ({});
        currentEpoch = Math.floor(Date.now() / 1000);
    }

    radius: 20
    color: "transparent"
    clip: true
    layer.enabled: true
    Component.onCompleted: {
        syncWeatherData();
        if (!WeatherService.hasValidData && !WeatherService.loading)
            WeatherService.refresh();
    }

    Connections {
        function onDataChanged() {
            root.syncWeatherData();
        }

        target: WeatherService
    }

    Timer {
        interval: 60000
        repeat: true
        running: root.active
        onTriggered: root.currentEpoch = Math.floor(Date.now() / 1000)
    }

    WeatherBackground {
        anchors.fill: parent
        weatherCode: WeatherService.currentWeatherCode
        iconName: WeatherService.currentIconName
        windSpeedMs: WeatherService.currentWindSpeedMs
        windGustsMs: WeatherService.currentWindGustsMs
        night: root.night
        rainBounceY: height
        scrollProgress: 0
        animate: root.active
        fullCardParticleBounds: true
    }

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        anchors.topMargin: 16
        spacing: 7

        MaterialSymbol {
            text: "location_on"
            iconSize: 18
            fill: 1
            color: root.night ? Qt.rgba(0.87, 0.91, 0.98, 0.78) : Qt.rgba(0.2, 0.28, 0.38, 0.66)
        }

        Text {
            Layout.fillWidth: true
            text: WeatherService.locationName || qsTr("Weather")
            color: root.night ? Qt.rgba(0.96, 0.98, 1, 0.96) : Qt.rgba(0.09, 0.14, 0.2, 0.9)
            font.family: Fonts.ui
            font.pixelSize: 15
            font.bold: true
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }

        Text {
            text: root.updatedText()
            color: root.night ? Qt.rgba(0.87, 0.91, 0.98, 0.74) : Qt.rgba(0.2, 0.28, 0.38, 0.62)
            font.family: Fonts.numeric
            font.pixelSize: 10
        }
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 15
        width: parent.width - 36
        spacing: 8

        Text {
            width: parent.width
            text: root.conditionText()
            color: Appearance.colors.colOnImage
            font.family: Fonts.ui
            font.pixelSize: 24
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            textFormat: Text.PlainText
        }

        Item {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width, temperatureText.implicitWidth + weatherIcon.width - 14)
            height: Math.max(temperatureText.implicitHeight, weatherIcon.height + 10)

            Text {
                id: temperatureText

                anchors.left: parent.left
                anchors.bottom: parent.bottom
                text: root.fmtTempPlain(WeatherService.currentTemperatureC)
                color: Appearance.colors.colOnImage
                font.family: Fonts.numeric
                font.pixelSize: 92
                font.bold: true
                font.letterSpacing: 0
            }

            MeteoIcon {
                id: weatherIcon

                anchors.right: parent.right
                anchors.top: parent.top
                width: 88
                height: 88
                weatherCode: WeatherService.currentWeatherCode
                iconName: WeatherService.currentIconName
                night: root.night
                animated: true
                playing: root.active
            }
        }

        Text {
            width: parent.width
            text: qsTr("Feels like: ") + root.fmtTemp(WeatherService.currentFeelsLikeC)
            color: Appearance.colors.colOnImage
            font.family: Fonts.ui
            font.pixelSize: 16
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        Text {
            width: parent.width
            text: qsTr("High ") + root.fmtTemp(root.today.temperatureMaxC) + qsTr(" · Low ") + root.fmtTemp(
                      root.today.temperatureMinC)
            color: Appearance.colors.colOnImage
            font.family: Fonts.ui
            font.pixelSize: 16
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }

    layer.effect: OpacityMask {

        maskSource: Rectangle {
            width: root.width
            height: root.height
            radius: root.radius
        }
    }
}

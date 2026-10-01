pragma Singleton
import QtQuick

Item {
    id: root

    readonly property bool available: backendLoader.status === Loader.Ready && backendLoader.item !== null
    readonly property var backend: backendLoader.item ? backendLoader.item.backend : null
    readonly property bool loading: backend ? backend.loading : false
    readonly property bool normalsAvailable: backend ? backend.normalsAvailable : false
    readonly property bool normalsLoading: backend ? backend.normalsLoading : false
    readonly property int normalsPeriodStartYear: backend ? backend.normalsPeriodStartYear : 0
    readonly property int normalsPeriodEndYear: backend ? backend.normalsPeriodEndYear : 0
    readonly property string normalsModel: backend ? backend.normalsModel : ""
    readonly property bool hasValidData: backend ? backend.hasValidData : false
    readonly property bool hasManualLocation: backend ? backend.hasManualLocation : false
    readonly property string status: backend ? backend.status : "unavailable"
    readonly property string errorMessage: backend ? backend.errorMessage : ""
    readonly property string locationName: backend ? backend.locationName : ""
    readonly property real latitude: backend ? backend.latitude : 0.0
    readonly property real longitude: backend ? backend.longitude : 0.0
    readonly property string lastUpdated: backend ? backend.lastUpdated : ""
    readonly property string nextRefreshAt: backend ? backend.nextRefreshAt : ""
    readonly property real currentTemperatureC: backend ? backend.currentTemperatureC : 0.0
    readonly property real currentFeelsLikeC: backend ? backend.currentFeelsLikeC : 0.0
    readonly property int currentWeatherCode: backend ? backend.currentWeatherCode : 0
    readonly property string currentWeatherText: backend ? backend.currentWeatherText : ""
    readonly property string currentIconName: backend ? backend.currentIconName : ""
    readonly property real currentWindSpeedMs: backend ? backend.currentWindSpeedMs : 0.0
    readonly property real currentWindDirection: backend ? backend.currentWindDirection : 0.0
    readonly property real currentWindGustsMs: backend ? backend.currentWindGustsMs : 0.0
    readonly property real currentUvIndex: backend ? backend.currentUvIndex : 0.0
    readonly property real currentRelativeHumidity: backend ? backend.currentRelativeHumidity : 0.0
    readonly property real currentDewPointC: backend ? backend.currentDewPointC : 0.0
    readonly property real currentPressureHpa: backend ? backend.currentPressureHpa : 0.0
    readonly property real currentCloudCover: backend ? backend.currentCloudCover : 0.0
    readonly property real currentVisibilityM: backend ? backend.currentVisibilityM : 0.0
    readonly property var currentAirQuality: backend ? backend.currentAirQuality : null
    readonly property var hourlyForecast: backend ? backend.hourlyForecast : []
    readonly property var dailyForecast: backend ? backend.dailyForecast : []
    readonly property var dailyTrendForecast: backend ? backend.dailyTrendForecast : []
    readonly property var minutelyForecast: backend ? backend.minutelyForecast : []

    readonly property Connections backendConnections: Connections {
        function onDataChanged() {
            root.dataChanged();
        }

        function onNormalsChanged() {
            root.normalsChanged();
        }

        target: root.backend
        ignoreUnknownSignals: true
    }

    signal dataChanged()
    signal normalsChanged()

    function refresh() {
        return backend ? backend.refresh() : false;
    }

    function setManualLocation(latitudeValue, longitudeValue, name) {
        return backend ? backend.setManualLocation(latitudeValue, longitudeValue, name) : false;
    }

    function clearManualLocation() {
        return backend ? backend.clearManualLocation() : false;
    }

    function current() {
        return backend ? backend.current() : null;
    }

    function normalDaytimeTemperatureC(month) {
        return backend ? backend.normalDaytimeTemperatureC(month) : 0.0;
    }

    function normalNighttimeTemperatureC(month) {
        return backend ? backend.normalNighttimeTemperatureC(month) : 0.0;
    }

    Loader {
        id: backendLoader
        source: "weather/WeatherBackend.qml"
    }
}

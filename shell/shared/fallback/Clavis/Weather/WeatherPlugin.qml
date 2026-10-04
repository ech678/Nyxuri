pragma Singleton
import QtQuick

QtObject {
    readonly property bool loading: false
    readonly property bool normalsAvailable: false
    readonly property bool normalsLoading: false
    readonly property int normalsPeriodStartYear: 0
    readonly property int normalsPeriodEndYear: 0
    readonly property string normalsModel: ""
    readonly property bool hasValidData: false
    readonly property bool hasManualLocation: false
    readonly property string status: "unavailable"
    readonly property string errorMessage: ""
    readonly property string locationName: ""
    readonly property double latitude: 0.0
    readonly property double longitude: 0.0
    readonly property string lastUpdated: ""
    readonly property string nextRefreshAt: ""
    readonly property double currentTemperatureC: 0.0
    readonly property double currentFeelsLikeC: 0.0
    readonly property int currentWeatherCode: 0
    readonly property string currentWeatherText: ""
    readonly property string currentIconName: "weather-cloudy"
    readonly property double currentWindSpeedMs: 0.0
    readonly property double currentWindDirection: 0.0
    readonly property double currentWindGustsMs: 0.0
    readonly property double currentUvIndex: 0.0
    readonly property double currentRelativeHumidity: 0.0
    readonly property double currentDewPointC: 0.0
    readonly property double currentPressureHpa: 0.0
    readonly property double currentCloudCover: 0.0
    readonly property double currentVisibilityM: 0.0
    readonly property var hourlyForecast: ({ count: () => 0, get: () => ({}) })
    readonly property var dailyForecast: ({ count: () => 0, get: () => ({}) })
    readonly property var dailyTrendForecast: ({ count: () => 0, get: () => ({}) })
    readonly property var minutelyForecast: ({ count: () => 0, get: () => ({}) })

    signal dataChanged()
    signal normalsChanged()

    function refresh() { return false; }
    function setManualLocation(lat, lon, name) { return false; }
    function clearManualLocation() { return false; }
    function current() { return null; }
    function normalDaytimeTemperatureC(month) { return 0.0; }
    function normalNighttimeTemperatureC(month) { return 0.0; }
}

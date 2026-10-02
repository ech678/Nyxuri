import QtQuick
import Clavis.WeatherMap as NativeWeatherMap

Item {
    id: root

    readonly property var plugin: NativeWeatherMap.WeatherMapPlugin
}

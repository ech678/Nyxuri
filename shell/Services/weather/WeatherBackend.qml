import QtQuick
import Clavis.Weather as NativeWeather

Item {
    id: root

    readonly property var backend: NativeWeather.WeatherPlugin
}

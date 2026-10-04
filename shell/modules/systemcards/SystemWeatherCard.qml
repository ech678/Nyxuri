import QtQuick
import QtQuick.Effects
import M3Shapes
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

Item {
    id: root

    readonly property bool dataAvailable: WeatherService.hasValidData
    readonly property string temperature: root.dataAvailable && isFinite(Number(
                                                                             WeatherService.currentTemperatureC))
                                          ? Math.round(UiPreferences.weatherTemperature(
                                                           WeatherService.currentTemperatureC)) + "°" : "--°"
    readonly property string weatherIcon: root.dataAvailable && String(WeatherService.currentIconName
                                                                       || "").length > 0
                                          ? WeatherService.currentIconName : "cloud"

    implicitWidth: backgroundShape.implicitWidth
    implicitHeight: backgroundShape.implicitHeight
    Accessible.name: I18n.tr("Weather,") + root.temperature + "，" + (root.dataAvailable
                                                                     ? WeatherService.currentWeatherText :
                                                                       I18n.tr("Weather unavailable"))

    MaterialShape {
        id: backgroundShape

        anchors.centerIn: parent
        width: implicitWidth
        height: implicitHeight
        shape: MaterialShape.Pill
        color: Appearance.colors.colPrimaryContainer
        implicitSize: 200
        layer.enabled: true

        Text {
            text: root.temperature
            color: Appearance.colors.colPrimary
            renderType: Text.NativeRendering

            anchors {
                top: parent.top
                right: parent.right
                topMargin: 20
                rightMargin: 16
            }

            font {
                family: Fonts.expressive
                pixelSize: 80
                weight: Font.Medium
            }
        }

        MaterialSymbol {
            text: root.weatherIcon
            iconSize: 80
            color: Appearance.colors.colOnPrimaryContainer

            anchors {
                left: parent.left
                bottom: parent.bottom
                leftMargin: 16
                bottomMargin: 20
            }
        }

        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Appearance.colors.colShadow
            shadowBlur: 0.8
            shadowVerticalOffset: 4
            shadowHorizontalOffset: 0
            autoPaddingEnabled: true
        }
    }
}

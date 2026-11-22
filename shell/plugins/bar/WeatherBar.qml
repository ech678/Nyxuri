// Fork & Trim: end4-pC modules/ii/bar/WeatherBar.qml (D1 weather wiring)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// D1: the iNiR `Weather` singleton never existed in this tree (22 dead
// bindings, ReferenceError on load) and `Icons.getWeatherIcon` is gone with
// it. The widget now consumes WeatherService directly — no forwarding alias —
// and holds a consumer lease so the backend (timer, network, cache) exists
// only while the widget is in a lane. No data degrades to "--°" and a cloud
// glyph instead of placeholder fiction.
pragma ComponentBehavior: Bound
import qs.services
import Quickshell
import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

MouseArea {
    id: root
    property bool hovered: false
    property bool vertical: Config.options.bar.vertical
    property bool isMaterial: PersonalizationConfig.barIsMaterial
    // D4b click axes: "default" keeps the built-in behavior (popup on
    // clickForDetails, right-press refresh).
    property var widgetEntry: null

    property string weatherLeaseId: ""
    Component.onCompleted: {
        weatherLeaseId = WeatherService.allocateLeaseId("bar-weather");
        WeatherService.acquire(weatherLeaseId);
    }
    Component.onDestruction: {
        if (weatherLeaseId !== "")
            WeatherService.release(weatherLeaseId);
    }

    readonly property bool hasData: WeatherService.hasValidData
    readonly property string tempText: root.hasData ? (Math.round(WeatherService.currentTemperatureC) + "°") : "--°"
    readonly property string iconName: root.hasData ? WeatherService.currentIconName : "cloud"

    implicitWidth: vertical ? 32 : (contentLoader.item?.implicitWidth ?? 0)
    implicitHeight: vertical ? (contentLoader.item?.implicitHeight ?? 0) : Appearance.sizes.barHeight

    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    readonly property bool clickForDetails: !root.barAxes.hoverPopouts
    hoverEnabled: true

    onClicked: mouse => {
        if (BarWidgetActions.dispatchMouse("weather", root.widgetEntry, mouse.button)) {
            mouse.accepted = true;
            return;
        }
        if (mouse.button === Qt.LeftButton && root.clickForDetails)
            weatherPopup.active = !weatherPopup.active;
    }

    onPressed: mouse => {
        if (mouse.button === Qt.RightButton) {
            WeatherService.refresh();
            ActionGateway.execute(["notify-send", Translation.tr("Weather"), Translation.tr("Refreshing (manually triggered)"), "-a", "Shell"], "bar.weather");
            mouse.accepted = false;
        }
    }

    Loader {
        id: contentLoader
        anchors.centerIn: parent
        sourceComponent: root.vertical ? colContent : rowContent
    }

    Component {
        id: rowContent
        RowLayout {
            spacing: 6

            MaterialSymbol {
                visible: !root.isMaterial
                fill: 0
                text: root.iconName
                iconSize: NexusStyle.font.bodyLarge * BarScale.font
                color: Appearance.colors.colOnLayer1
                Layout.alignment: Qt.AlignVCenter
            }

            StyledText {
                visible: !root.isMaterial
                font.pixelSize: NexusStyle.font.bodyMedium * BarScale.font
                color: Appearance.colors.colOnLayer1
                text: root.tempText
                Layout.alignment: Qt.AlignVCenter
            }

            StyledText {
                visible: root.isMaterial
                font.pixelSize: NexusStyle.font.bodyMedium * BarScale.font
                color: M3Palette.pillAccent("weatherBar", M3Palette.primary)
                text: root.tempText
                Layout.alignment: Qt.AlignVCenter
                leftPadding: 5
            }

            Rectangle {
                visible: root.isMaterial
                width: 25
                height: 25
                radius: Appearance.rounding.full
                color: M3Palette.primary

                MaterialSymbol {
                    anchors.centerIn: parent
                    fill: 0
                    text: root.iconName
                    iconSize: NexusStyle.font.bodyLarge * BarScale.font
                    color: M3Palette.primaryForeground
                }
            }
        }
    }

    Component {
        id: colContent
        ColumnLayout {
            spacing: root.isMaterial ? 2 : 0

            MaterialSymbol {
                visible: !root.isMaterial
                fill: 0
                text: root.iconName
                iconSize: NexusStyle.font.bodyLarge * BarScale.font
                color: Appearance.colors.colOnLayer1
                Layout.alignment: Qt.AlignHCenter
            }

            StyledText {
                visible: !root.isMaterial
                font.pixelSize: NexusStyle.font.bodyMedium * BarScale.font
                color: Appearance.colors.colOnLayer1
                text: root.tempText.replace(/[CF]$/, "")
                Layout.alignment: Qt.AlignHCenter
            }

            StyledText {
                visible: root.isMaterial
                font.pixelSize: NexusStyle.font.bodyMedium * BarScale.font
                color: M3Palette.pillAccent("weatherBar", M3Palette.primary)
                text: root.tempText.replace(/[CF]$/, "")
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 3
            }

            Rectangle {
                visible: root.isMaterial
                width: 25
                height: 25
                radius: Appearance.rounding.full
                color: M3Palette.primary
                Layout.alignment: Qt.AlignHCenter

                MaterialSymbol {
                    anchors.centerIn: parent
                    fill: 0
                    text: root.iconName
                    iconSize: NexusStyle.font.bodyLarge * BarScale.font
                    color: M3Palette.primaryForeground
                }
            }
        }
    }

    WeatherPopup {
        id: weatherPopup
        widgetBar: root.widgetBar
        hoverTarget: root
        hoverActivates: !root.clickForDetails
        closeOnOutsideClick: root.clickForDetails
        onRequestClose: active = false
    }
}

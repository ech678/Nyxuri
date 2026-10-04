import QtQuick
import qs.app
import QtQuick.Layouts
import qs.app.services
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    property bool vertical: false
    readonly property bool showValue: PersonalizationConfig.barShowValues
    readonly property string temperatureText: WeatherService.hasValidData ? Math.round(
                                                                                UiPreferences.weatherTemperature(
                                                                                    WeatherService.currentTemperatureC))
                                                                            + "°" : "--°"
    readonly property int iconSize: Sizes.barIconSize
    readonly property int temperatureSize: 12
    readonly property real contentSpacing: Sizes.barLabelSpacing
    readonly property bool active: WidgetState.dashboardSidebarOpen && WidgetState.dashboardSidebarView
                                   === "weather"

    function toggleView() {
        if (root.active) {
            WidgetState.dashboardSidebarOpen = false;
            return;
        }
        WidgetState.dashboardSidebarView = "weather";
        WidgetState.dashboardSidebarOpen = true;
    }

    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    BarActionButton {
        id: button

        anchors.fill: parent
        vertical: root.vertical
        expandedContent: root.showValue
        buttonRadius: height / 2
        containerColor: "transparent"
        rippleColor: Appearance.colors.colOnSurface
        releaseAction: () => {
            return root.toggleView();
        }

        contentItem: Item {
            implicitWidth: content.implicitWidth
            implicitHeight: content.implicitHeight

            GridLayout {
                id: content
                anchors.centerIn: parent
                columns: root.vertical ? 1 : 2
                rowSpacing: Sizes.barItemSpacing
                columnSpacing: root.contentSpacing

                MaterialSymbol {
                    Layout.preferredWidth: root.iconSize
                    Layout.preferredHeight: root.iconSize
                    Layout.alignment: Qt.AlignCenter
                    text: WeatherService.currentIconName || "cloud"
                    iconSize: root.iconSize
                    fill: 0
                    color: Appearance.colors.colOnSurface
                }

                Text {
                    visible: root.showValue
                    Layout.alignment: Qt.AlignCenter
                    text: root.temperatureText
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.family: Fonts.numeric
                    font.pixelSize: root.temperatureSize
                    font.bold: true
                    color: Appearance.colors.colOnSurface
                }
            }
        }
    }

    PopupToolTip {
        extraVisibleCondition: button.pointerHovered
        text: I18n.tr("Weather")
    }
}

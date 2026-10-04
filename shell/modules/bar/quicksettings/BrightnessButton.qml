import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.app.services
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

Item {
    id: root

    property var screen: null
    property bool vertical: false
    readonly property bool showValue: PersonalizationConfig.barShowValues
    readonly property var monitor: BrightnessService.getMonitorForScreen(screen)
    readonly property real brightnessValue: monitor ? monitor.brightness : BrightnessService.brightnessValue

    implicitWidth: mouseArea.implicitWidth
    implicitHeight: mouseArea.implicitHeight

    BarActionButton {
        id: mouseArea
        anchors.fill: parent
        vertical: root.vertical
        expandedContent: root.showValue
        contentItem: Item {
            implicitWidth: content.implicitWidth
            implicitHeight: content.implicitHeight
            GridLayout {
                id: content
                anchors.centerIn: parent
                columns: root.vertical ? 1 : 2
                rowSpacing: Sizes.barItemSpacing
                columnSpacing: Sizes.barLabelSpacing
                ArcGauge {
                    id: gauge
                    Layout.preferredWidth: Sizes.barControlCircleSize
                    Layout.preferredHeight: Sizes.barControlCircleSize
                    Layout.alignment: Qt.AlignCenter

                    value: root.brightnessValue
                    progressColor: Appearance.colors.colPrimary
                    trackColor: Appearance.colors.colLayer2Hover
                    handleColor: Appearance.colors.colOnSurface
                    iconColor: Appearance.colors.colOnSurface
                    icon: "brightness_medium"
                }

                Text {
                    id: valueText
                    visible: root.showValue
                    text: Math.round(root.brightnessValue * 100) + "%"
                    font.family: Fonts.numeric
                    font.pixelSize: 12
                    color: Appearance.colors.colOnSurface
                    Layout.alignment: Qt.AlignCenter
                }
            }
        }
        Accessible.name: tooltip.text

        wheelAction: wheel => {
            const delta = wheel.angleDelta.y || wheel.angleDelta.x || wheel.pixelDelta.y
                  || wheel.pixelDelta.x;


            if (!delta)
                return;
            const step = delta > 0 ? 0.05 : -0.05;
            BrightnessService.setBrightnessForScreen(root.screen, root.brightnessValue + step);
            wheel.accepted = true;
        }
    }

    PopupToolTip {
        id: tooltip
        extraVisibleCondition: mouseArea.pointerHovered
        text: I18n.tr("Brightness: ") + Math.round(root.brightnessValue * 100) + I18n.tr(
                  "%\nScroll to adjust")

    }
}

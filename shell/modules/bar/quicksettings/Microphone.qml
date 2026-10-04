import QtQuick
import qs.app
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

                    value: VolumeService.sourceMuted ? 0 : VolumeService.sourceVolume
                    progressColor: (VolumeService.sourceMuted || VolumeService.sourceVolume <= 0)
                                   ? Appearance.colors.colError : Appearance.colors.colPrimary
                    trackColor: Appearance.colors.colLayer2Hover
                    handleColor: Appearance.colors.colOnSurface
                    iconColor: (VolumeService.sourceMuted || VolumeService.sourceVolume <= 0)
                               ? Appearance.colors.colError : Appearance.colors.colOnSurface
                    icon: (VolumeService.sourceMuted || VolumeService.sourceVolume <= 0) ? "mic_off" : "mic"
                }

                Text {
                    id: valueText
                    visible: root.showValue
                    text: Math.round(VolumeService.sourceVolume * 100) + "%"
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
            VolumeService.setSourceVolume(VolumeService.sourceVolume + step);
            wheel.accepted = true;
        }
        onClicked: {
            if (root.screen && root.screen.name)
                WidgetState.quickSettingsScreenName = root.screen.name;
            if (WidgetState.quickSettingsOpen && WidgetState.quickSettingsView === "microphone") {
                WidgetState.quickSettingsOpen = false;
            } else {
                WidgetState.quickSettingsView = "microphone";
                WidgetState.quickSettingsOpen = true;
            }
        }
    }

    PopupToolTip {
        id: tooltip
        extraVisibleCondition: mouseArea.pointerHovered
        text: (VolumeService.sourceMuted ? I18n.tr("Microphone: muted") : I18n.tr("Microphone: ") + Math.round(
                                               VolumeService.sourceVolume * 100) + "%") + I18n.tr(
                  "\nScroll to adjust; click to open microphone controls")
    }
}

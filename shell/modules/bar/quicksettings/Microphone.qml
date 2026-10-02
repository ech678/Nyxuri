import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.app.services
import qs.shared.theme
import qs.shared.controls

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

                    value: Volume.sourceMuted ? 0 : Volume.sourceVolume
                    progressColor: (Volume.sourceMuted || Volume.sourceVolume <= 0)
                                   ? Appearance.colors.colError : Appearance.colors.colPrimary
                    trackColor: Appearance.colors.colLayer2Hover
                    handleColor: Appearance.colors.colOnSurface
                    iconColor: (Volume.sourceMuted || Volume.sourceVolume <= 0) ? Appearance.colors.colError :
                                                                                  Appearance.colors.colOnSurface
                    icon: (Volume.sourceMuted || Volume.sourceVolume <= 0) ? "mic_off" : "mic"
                }

                Text {
                    id: valueText
                    visible: root.showValue
                    text: Math.round(Volume.sourceVolume * 100) + "%"
                    font.family: Fonts.numeric
                    font.pixelSize: 12
                    color: Appearance.colors.colOnSurface
                    Layout.alignment: Qt.AlignCenter
                }
            }
        }
        Accessible.name: tooltip.text

        WheelHandler {
            onWheel: wheel => {
                const step = 0.05;
                let newVol = Volume.sourceVolume;
                if (wheel.angleDelta.y > 0)
                    newVol += step;
                else
                    newVol -= step;
                Volume.setSourceVolume(newVol);
                wheel.accepted = true;
            }
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
        text: (Volume.sourceMuted ? qsTr("Microphone: muted") : qsTr("Microphone: ") + Math.round(
                                        Volume.sourceVolume * 100) + "%") + qsTr(
                  "\nScroll to adjust; click to open microphone controls")
    }
}

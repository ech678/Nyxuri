import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

Rectangle {
    id: root

    readonly property real gammaCutoff: 0.3
    property var screen: null
    property bool detailed: false
    property real pullExpansion: 0
    readonly property var brightnessMonitor: Brightness.getMonitorForScreen(screen)
    readonly property real brightnessValue: brightnessMonitor ? brightnessMonitor.brightness :
                                                                Brightness.brightnessValue
    property real verticalPadding: detailed ? Metrics.spacingL : 4
    property real horizontalPadding: detailed ? Metrics.spacingL : 12

    Layout.fillWidth: true
    implicitWidth: contentItem.implicitWidth + horizontalPadding * 2
    implicitHeight: contentItem.implicitHeight + verticalPadding * 2
    radius: Appearance.rounding.normal
    color: Appearance.colors.colLayer1

    ColumnLayout {
        id: contentItem

        anchors {
            fill: parent
            leftMargin: root.horizontalPadding
            rightMargin: root.horizontalPadding
            topMargin: root.verticalPadding
            bottomMargin: root.verticalPadding
        }
        spacing: (root.detailed ? Metrics.spacingS : 0) + root.pullExpansion

        SliderHeading {
            visible: root.detailed
            title: qsTr("Brightness")
            detail: root.screen ? root.screen.name : ""
        }

        QuickMaterialSlider {
            Accessible.name: qsTr("Brightness")
            materialSymbol: "light_mode"
            secondaryMaterialSymbol: "wb_twilight"
            secondaryIconLocation: root.gammaCutoff
            stopIndicatorValues: (DisplayColor.dimming * 100) !== 100 && root.brightnessValue > 0 ? [root.gammaCutoff
                                                                                                     + root.brightnessValue
                                                                                                     * (1 - root.gammaCutoff)] :
                                                                                                    []
            value: (DisplayColor.dimming * 100) === 100 ? root.gammaCutoff + root.brightnessValue * (1
                                                                                                     - root.gammaCutoff) :
                                                          ((DisplayColor.dimming * 100) - (
                                                               DisplayColor.dimmingLowerLimit * 100)) / (100
                                                                                                         - (DisplayColor.dimmingLowerLimit
                                                                                                            * 100)) * root.gammaCutoff
            percentText: (DisplayColor.dimming * 100) === 100 ? `${Math.round(root.brightnessValue * 100)}%` :
                                                                `${Math.round(DisplayColor.dimming * 100)}%`
            tooltipContent: (DisplayColor.dimming * 100) === 100 ? `${Math.round(root.brightnessValue * 100)}%` :
                                                                   qsTr("Software dimming: %1%").arg(
                                                                       Math.round(DisplayColor.dimming * 100))
            onMoved: {
                if (value >= root.gammaCutoff) {
                    Brightness.setBrightnessForScreen(root.screen, (value - root.gammaCutoff) / (1
                                                                                                 - root.gammaCutoff));
                    if ((DisplayColor.dimming * 100) !== 100)
                        DisplayColor.setDimming(1);
                } else {
                    if (root.brightnessValue > 0)
                        Brightness.setBrightnessForScreen(root.screen, 0, true);
                    DisplayColor.setDimming(value / root.gammaCutoff * (1 - DisplayColor.dimmingLowerLimit)
                                            + DisplayColor.dimmingLowerLimit);
                }
            }
        }

        SliderHeading {
            visible: root.detailed
            Layout.topMargin: (root.detailed ? Metrics.spacingS : 0) + root.pullExpansion * 1.5
            title: qsTr("Sound")
            detail: Volume.sinkName
        }

        QuickMaterialSlider {
            Accessible.name: qsTr("Sound")
            enabled: Volume.outputAvailable
            materialSymbol: Volume.sinkMuted ? "volume_off" : "volume_up"
            value: Volume.sinkVolume
            percentText: Volume.sinkMuted ? qsTr("Muted") : Math.round(value * 100) + "%"
            onMoved: Volume.setSinkVolume(value)
        }

        SliderHeading {
            visible: root.detailed
            Layout.topMargin: (root.detailed ? Metrics.spacingS : 0) + root.pullExpansion * 1.5
            title: qsTr("Microphone")
            detail: Volume.sourceName
        }

        QuickMaterialSlider {
            Accessible.name: qsTr("Microphone")
            enabled: Volume.inputAvailable
            materialSymbol: Volume.sourceMuted ? "mic_off" : "mic"
            value: Volume.sourceVolume
            percentText: Volume.sourceMuted ? qsTr("Muted") : Math.round(value * 100) + "%"
            onMoved: Volume.setSourceVolume(value)
        }
    }

    component SliderHeading: ColumnLayout {
        id: heading
        property string title: ""
        property string detail: ""
        Layout.fillWidth: true
        spacing: Metrics.spacingXXS + root.pullExpansion * 0.5
        Text {
            Layout.fillWidth: true
            text: heading.title
            color: Appearance.colors.colOnSurface
            font.family: Typography.titleSmall.family
            font.pixelSize: Typography.titleSmall.pixelSize
            font.weight: Typography.titleSmall.weight
        }
        Text {
            Layout.fillWidth: true
            text: heading.detail
            visible: text.length > 0
            elide: Text.ElideRight
            color: Appearance.colors.colOnSurfaceVariant
            font.family: Typography.bodySmall.family
            font.pixelSize: Typography.bodySmall.pixelSize
        }
    }
}

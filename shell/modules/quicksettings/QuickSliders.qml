import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

Rectangle {
    id: root

    readonly property real gammaCutoff: 0.3
    property var screen: null
    property bool detailed: false
    property real pullExpansion: 0
    readonly property var brightnessMonitor: BrightnessService.getMonitorForScreen(screen)
    readonly property real brightnessValue: brightnessMonitor ? brightnessMonitor.brightness :
                                                                BrightnessService.brightnessValue
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
            title: I18n.tr("Brightness")
            detail: root.screen ? root.screen.name : ""
        }

        QuickMaterialSlider {
            Accessible.name: I18n.tr("Brightness")
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
                                                                   I18n.tr("Software dimming: %1%").arg(
                                                                       Math.round(DisplayColor.dimming * 100))
            onMoved: {
                if (value >= root.gammaCutoff) {
                    BrightnessService.setBrightnessForScreen(root.screen, (value - root.gammaCutoff) / (1
                                                                                                        - root.gammaCutoff));


                    if ((DisplayColor.dimming * 100) !== 100)
                        DisplayColor.setDimming(1);
                } else {
                    if (root.brightnessValue > 0)
                        BrightnessService.setBrightnessForScreen(root.screen, 0, true);
                    DisplayColor.setDimming(value / root.gammaCutoff * (1 - DisplayColor.dimmingLowerLimit)
                                            + DisplayColor.dimmingLowerLimit);
                }
            }
        }

        SliderHeading {
            visible: root.detailed
            Layout.topMargin: (root.detailed ? Metrics.spacingS : 0) + root.pullExpansion * 1.5
            title: I18n.tr("Sound")
            detail: VolumeService.sinkName
        }

        QuickMaterialSlider {
            Accessible.name: I18n.tr("Sound")
            enabled: VolumeService.outputAvailable
            materialSymbol: VolumeService.sinkMuted ? "volume_off" : "volume_up"
            value: VolumeService.sinkVolume
            percentText: VolumeService.sinkMuted ? I18n.tr("Muted") : Math.round(value * 100) + "%"
            onMoved: VolumeService.setSinkVolume(value)
        }

        SliderHeading {
            visible: root.detailed
            Layout.topMargin: (root.detailed ? Metrics.spacingS : 0) + root.pullExpansion * 1.5
            title: I18n.tr("Microphone")
            detail: VolumeService.sourceName
        }

        QuickMaterialSlider {
            Accessible.name: I18n.tr("Microphone")
            enabled: VolumeService.inputAvailable
            materialSymbol: VolumeService.sourceMuted ? "mic_off" : "mic"
            value: VolumeService.sourceVolume
            percentText: VolumeService.sourceMuted ? I18n.tr("Muted") : Math.round(value * 100) + "%"
            onMoved: VolumeService.setSourceVolume(value)
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

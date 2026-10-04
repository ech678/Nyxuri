import QtQuick
import qs.app
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

WidgetPanel {
    id: root

    property bool foreground: false
    readonly property string stateMessage: {
        if (VolumeService.lastError.length > 0)
            return VolumeService.lastError;
        if (!VolumeService.ready)
            return I18n.tr("Connecting to the PipeWire audio service");
        if (VolumeService.inputDevices.length === 0 && !VolumeService.inputAvailable)
            return I18n.tr("No microphone devices detected");
        return "";
    }

    title: I18n.tr("Microphone")
    icon: "mic"
    showBackButton: true
    backAction: () => WidgetState.quickSettingsView = "settings"

    headerTools: IconButton {
        controlSize: 40
        iconName: "open_in_new"
        iconSize: 20
        iconColor: Appearance.colors.colOnLayer2
        accessibleName: I18n.tr("Open advanced sound settings")
        hoverStateLayerColor: Appearance.colors.colLayer2Hover
        pressedStateLayerColor: Appearance.colors.colLayer2Active
        onClicked: {
            WidgetState.closeAllPopups();
            VolumeService.openMixer();
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Metrics.spacingL

        SidebarFlickable {
            id: sidebarScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: content.implicitHeight + sidebarScroll.contentTopInset

            ColumnLayout {
                id: content
                y: sidebarScroll.contentTopInset
                width: parent.width
                spacing: Metrics.spacingL
                InlineStatusBanner {
                    Layout.topMargin: sidebarScroll.gapFor(0, 1)
                    Layout.fillWidth: true
                    visible: root.stateMessage.length > 0
                    tone: VolumeService.lastError.length > 0 ? "error" : "info"
                    message: root.stateMessage
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(1, 1)

                    Layout.fillWidth: true
                    visible: VolumeService.ready && VolumeService.inputAvailable
                    title: I18n.tr("Input")
                    iconName: "mic"

                    VolumeSlider {
                        Layout.fillWidth: true
                        title: VolumeService.sourceName || I18n.tr("Default input")
                        supportingText: VolumeService.nodeSupportingText(VolumeService.source)
                        iconName: VolumeService.nodeIconName(VolumeService.source)
                        volume: VolumeService.sourceVolume
                        muted: VolumeService.sourceMuted
                        available: VolumeService.inputAvailable
                        showMuteButton: true
                        onVolumeMoved: value => VolumeService.setSourceVolume(value)
                        onMuteRequested: VolumeService.toggleSourceMute()
                    }
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(2, 1)

                    Layout.fillWidth: true
                    visible: VolumeService.ready && VolumeService.inputDevices.length > 0
                    title: I18n.tr("Input devices")
                    iconName: "settings_voice"
                    contentSpacing: Metrics.spacingL

                    Repeater {
                        model: VolumeService.inputDevices

                        ColumnLayout {
                            id: device
                            required property var modelData
                            required property int index
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.16)

                            Layout.fillWidth: true
                            spacing: Metrics.spacingXS + sidebarScroll.detailExpansion

                            SettingsRow {
                                Layout.fillWidth: true
                                title: VolumeService.nodeDisplayName(device.modelData)
                                supportingText: VolumeService.nodeSupportingText(device.modelData)
                                iconName: VolumeService.nodeIconName(device.modelData)
                                highlighted: VolumeService.isDefaultInput(device.modelData)
                                interactive: !highlighted
                                onClicked: VolumeService.setDefaultInput(device.modelData)
                                trailing: MaterialSymbol {
                                    visible: VolumeService.isDefaultInput(device.modelData)
                                    text: "check_circle"
                                    iconSize: Metrics.iconM
                                    color: Appearance.colors.colPrimary
                                }
                            }

                            VolumeSlider {
                                Layout.fillWidth: true
                                visible: !VolumeService.isDefaultInput(device.modelData)
                                title: I18n.tr("Volume")
                                iconName: VolumeService.nodeIconName(device.modelData)
                                volume: VolumeService.nodeVolume(device.modelData)
                                muted: VolumeService.nodeMuted(device.modelData)
                                showMuteButton: true
                                onVolumeMoved: value => VolumeService.setNodeVolume(device.modelData, value)
                                onMuteRequested: VolumeService.toggleNodeMute(device.modelData)
                            }
                        }
                    }
                }
            }
        }
    }
}

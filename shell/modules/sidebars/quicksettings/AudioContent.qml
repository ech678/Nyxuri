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
        if (VolumeService.outputDevices.length === 0 && !VolumeService.outputAvailable)
            return I18n.tr("No audio output devices detected");
        return "";
    }

    title: I18n.tr("Sound")
    icon: "volume_up"
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
                    visible: VolumeService.ready && VolumeService.outputAvailable
                    title: I18n.tr("Output")
                    iconName: "volume_up"

                    VolumeSlider {
                        Layout.fillWidth: true
                        title: VolumeService.sinkName || I18n.tr("Default output")
                        supportingText: VolumeService.nodeSupportingText(VolumeService.sink)
                        iconName: VolumeService.nodeIconName(VolumeService.sink)
                        volume: VolumeService.sinkVolume
                        muted: VolumeService.sinkMuted
                        available: VolumeService.outputAvailable
                        showMuteButton: true
                        onVolumeMoved: value => VolumeService.setSinkVolume(value)
                        onMuteRequested: VolumeService.toggleSinkMute()
                    }
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(2, 1)

                    Layout.fillWidth: true
                    visible: VolumeService.ready && VolumeService.outputDevices.length > 0
                    title: I18n.tr("Output devices")
                    iconName: "speaker_group"
                    contentSpacing: Metrics.spacingL

                    Repeater {
                        model: VolumeService.outputDevices

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
                                highlighted: VolumeService.isDefaultOutput(device.modelData)
                                interactive: !highlighted
                                onClicked: VolumeService.setDefaultOutput(device.modelData)
                                trailing: MaterialSymbol {
                                    visible: VolumeService.isDefaultOutput(device.modelData)
                                    text: "check_circle"
                                    iconSize: Metrics.iconM
                                    color: Appearance.colors.colPrimary
                                }
                            }

                            VolumeSlider {
                                Layout.fillWidth: true
                                visible: !VolumeService.isDefaultOutput(device.modelData)
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

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(3, 1)

                    Layout.fillWidth: true
                    visible: VolumeService.ready && VolumeService.outputAvailable
                    title: I18n.tr("Application volume")
                    iconName: "apps"
                    contentSpacing: Metrics.spacingL

                    Repeater {
                        model: VolumeService.playbackStreams

                        VolumeSlider {
                            required property var modelData
                            required property int index
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.16)

                            Layout.fillWidth: true
                            title: VolumeService.applicationDisplayName(modelData)
                            supportingText: VolumeService.nodeSupportingText(modelData)
                            iconSource: VolumeService.applicationIconSource(modelData)
                            volume: VolumeService.nodeVolume(modelData)
                            muted: VolumeService.nodeMuted(modelData)
                            showMuteButton: true
                            onVolumeMoved: value => VolumeService.setNodeVolume(modelData, value)
                            onMuteRequested: VolumeService.toggleNodeMute(modelData)
                        }
                    }

                    SettingsRow {
                        Layout.fillWidth: true
                        visible: VolumeService.playbackStreams.length === 0
                        iconName: "music_off"
                        title: I18n.tr("No active application audio")
                    }
                }
            }
        }
    }
}

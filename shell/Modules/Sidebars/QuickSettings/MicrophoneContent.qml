import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Components
import qs.Services
import qs.Widgets.audio
import qs.Widgets.common

WidgetPanel {
    id: root

    property bool foreground: false
    readonly property string stateMessage: {
        if (Volume.lastError.length > 0)
            return Volume.lastError;
        if (!Volume.ready)
            return qsTr("Connecting to the PipeWire audio service");
        if (Volume.inputDevices.length === 0 && !Volume.inputAvailable)
            return qsTr("No microphone devices detected");
        return "";
    }

    title: qsTr("Microphone")
    icon: "mic"
    showBackButton: true
    backAction: () => WidgetState.quickSettingsView = "settings"

    headerTools: IconButton {
        controlSize: 40
        iconName: "open_in_new"
        iconSize: 20
        iconColor: Appearance.colors.colOnLayer2
        accessibleName: qsTr("Open advanced sound settings")
        hoverStateLayerColor: Appearance.colors.colLayer2Hover
        pressedStateLayerColor: Appearance.colors.colLayer2Active
        onClicked: {
            WidgetState.closeAllPopups();
            Volume.openMixer();
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
                    tone: Volume.lastError.length > 0 ? "error" : "info"
                    message: root.stateMessage
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(1, 1)

                    Layout.fillWidth: true
                    visible: Volume.ready && Volume.inputAvailable
                    title: qsTr("Input")
                    iconName: "mic"

                    VolumeSlider {
                        Layout.fillWidth: true
                        title: Volume.sourceName || qsTr("Default input")
                        supportingText: Volume.nodeSupportingText(Volume.source)
                        iconName: Volume.nodeIconName(Volume.source)
                        volume: Volume.sourceVolume
                        muted: Volume.sourceMuted
                        available: Volume.inputAvailable
                        showMuteButton: true
                        onVolumeMoved: value => Volume.setSourceVolume(value)
                        onMuteRequested: Volume.toggleSourceMute()
                    }
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(2, 1)

                    Layout.fillWidth: true
                    visible: Volume.ready && Volume.inputDevices.length > 0
                    title: qsTr("Input devices")
                    iconName: "settings_voice"
                    contentSpacing: Metrics.spacingL

                    Repeater {
                        model: Volume.inputDevices

                        ColumnLayout {
                            id: device
                            required property var modelData
                            required property int index
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.16)

                            Layout.fillWidth: true
                            spacing: Metrics.spacingXS + sidebarScroll.detailExpansion

                            SettingsRow {
                                Layout.fillWidth: true
                                title: Volume.nodeDisplayName(device.modelData)
                                supportingText: Volume.nodeSupportingText(device.modelData)
                                iconName: Volume.nodeIconName(device.modelData)
                                highlighted: Volume.isDefaultInput(device.modelData)
                                interactive: !highlighted
                                onClicked: Volume.setDefaultInput(device.modelData)
                                trailing: MaterialSymbol {
                                    visible: Volume.isDefaultInput(device.modelData)
                                    text: "check_circle"
                                    iconSize: Metrics.iconM
                                    color: Appearance.colors.colPrimary
                                }
                            }

                            VolumeSlider {
                                Layout.fillWidth: true
                                visible: !Volume.isDefaultInput(device.modelData)
                                title: qsTr("Volume")
                                iconName: Volume.nodeIconName(device.modelData)
                                volume: Volume.nodeVolume(device.modelData)
                                muted: Volume.nodeMuted(device.modelData)
                                showMuteButton: true
                                onVolumeMoved: value => Volume.setNodeVolume(device.modelData, value)
                                onMuteRequested: Volume.toggleNodeMute(device.modelData)
                            }
                        }
                    }
                }
            }
        }
    }
}

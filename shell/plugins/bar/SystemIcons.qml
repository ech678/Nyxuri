// Fork & Trim: iNiR modules/ii/barM3/SystemIcons.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri:
//   - Audio/Network/BluetoothStatus/Notifications become the owning Nyxuri
//     services (VolumeService/NetworkService/BluetoothService/NotificationService);
//   - KeyboardIndicators is the ported iNiR service in this tree;
//   - the 22px Nyxuri `larger` token is replaced by the end4/iNiR 19px bar
//     baseline (`Appearance.sizes.barIconSize`) so the cluster matches the
//     util buttons and resource rings;
//   - contentColor/contentColorOverridden stay for BarGroup's per-widget style
//     override.

import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.commons
import qs.ui

Item {
    id: root

    property color contentColor: Appearance.colors.colOnLayer1
    property bool contentColorOverridden: false
    property bool vertical: Config.options.bar.vertical
    property bool isMaterial: PersonalizationConfig.barIsMaterial

    readonly property color iconColor: root.contentColorOverridden ? root.contentColor : (root.isMaterial ? M3Palette.pillInk("systemIcons") : Appearance.colors.colOnLayer1)

    function wifiIcon(): string {
        if (!NetworkService.available)
            return "signal_wifi_off";
        if (NetworkService.wiredConnected)
            return "settings_ethernet";
        if (!NetworkService.wifiConnected)
            return "signal_wifi_0_bar";
        const strength = NetworkService.signalStrength;
        if (strength >= 75)
            return "signal_wifi_4_bar";
        if (strength >= 50)
            return "signal_wifi_3_bar";
        if (strength >= 25)
            return "signal_wifi_2_bar";
        return "signal_wifi_1_bar";
    }

    implicitWidth: root.vertical ? 32 : flow.implicitWidth + 4
    implicitHeight: root.vertical ? flow.implicitHeight + 4 : 32

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        onPressed: mouse => {
            if (mouse.button === Qt.MiddleButton) {
                if (VolumeService.sink?.audio)
                    VolumeService.sink.audio.muted = !VolumeService.sink.audio.muted;
            } else {
                ActionGateway.requestSidebarToggle("quicksettings");
            }
        }

        property real wheelAccum: 0
        onWheel: event => {
            wheelAccum += event.angleDelta.y;
            while (wheelAccum >= 120) {
                wheelAccum -= 120;
                VolumeService.setSinkVolume(VolumeService.sinkVolume + 0.05);
            }
            while (wheelAccum <= -120) {
                wheelAccum += 120;
                VolumeService.setSinkVolume(VolumeService.sinkVolume - 0.05);
            }
            event.accepted = true;
        }
    }

    Flow {
        id: flow

        anchors.centerIn: parent
        flow: root.vertical ? Flow.TopToBottom : Flow.LeftToRight
        spacing: root.isMaterial ? 2 : 10

        Revealer {
            reveal: true

            MaterialSymbol {
                text: VolumeService.sinkMuted ? "volume_off" : "volume_up"
                iconSize: Appearance.sizes.barIconSize
                color: root.iconColor
            }
        }

        Revealer {
            reveal: VolumeService.sourceMuted

            MaterialSymbol {
                text: "mic_off"
                iconSize: Appearance.sizes.barIconSize
                color: root.iconColor
            }
        }

        Loader {
            id: xkbLoader

            // Inside a Flow the nested indicator's Layout.preferredWidth does
            // nothing, so the loader owns the released width.
            active: KeyboardIndicators.hasPanelIndicators
            visible: active
            width: active ? item?.implicitWidth ?? 0 : 0
            height: active ? item?.implicitHeight ?? 0 : 0
            source: "HyprlandXkbIndicator.qml"
            onLoaded: {
                if (item)
                    item.color = Qt.binding(() => root.iconColor);
            }
        }

        MaterialSymbol {
            text: root.wifiIcon()
            iconSize: Appearance.sizes.barIconSize
            color: root.iconColor
        }

        MaterialSymbol {
            visible: BluetoothService.available
            text: BluetoothService.connected ? "bluetooth_connected" : BluetoothService.enabled ? "bluetooth" : "bluetooth_disabled"
            iconSize: Appearance.sizes.barIconSize
            color: root.iconColor
        }

        Loader {
            id: notifLoader

            active: NotificationService.silent || NotificationService.unread > 0
            visible: active
            width: active ? item?.implicitWidth ?? 0 : 0
            height: active ? item?.implicitHeight ?? 0 : 0
            source: "NotificationUnreadCount.qml"
            onLoaded: {
                if (item)
                    item.embeddedInSystemIcons = true;
            }
        }
    }
}

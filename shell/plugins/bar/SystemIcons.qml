// Fork & Trim: end4-pC modules/ii/bar/SystemIcons.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri: the upstream singletons (Audio, Network,
// BluetoothStatus, Notifications, KeyboardIndicators, PeripheralBattery) do
// not exist here. Each icon now reads its owning Nyxuri service directly —
// no forwarding aliases, no eval fallbacks. The peripheral-battery block is
// dropped (no UPower peripheral source in this tree) and the island-specific
// colour branch is gone because the island is a middle-lane widget now.

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

    readonly property color iconColor: root.contentColorOverridden ? root.contentColor : (root.isMaterial ? Appearance.colors.colOnPrimary : Appearance.colors.colOnLayer1)

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

    implicitWidth: root.vertical ? 32 : flow.implicitWidth + (root.isMaterial ? 12 : 4)
    implicitHeight: root.vertical ? flow.implicitHeight + 4 : 32

    MouseArea {
        anchors.fill: parent
        onPressed: ActionGateway.requestSidebarToggle("quicksettings")
    }

    Flow {
        id: flow
        anchors.centerIn: parent
        flow: root.vertical ? Flow.TopToBottom : Flow.LeftToRight
        spacing: isMaterial ? 2 : root.vertical ? 6 : 10

        Revealer {
            reveal: true
            MaterialSymbol {
                text: VolumeService.sinkMuted ? "volume_off" : "volume_up"
                iconSize: Appearance.font.pixelSize.larger
                color: root.iconColor
            }
        }
        Revealer {
            reveal: VolumeService.sourceMuted
            MaterialSymbol {
                text: "mic_off"
                iconSize: Appearance.font.pixelSize.larger
                color: root.iconColor
            }
        }
        MaterialSymbol {
            visible: KeyboardLockService.available && (KeyboardLockService.capsLock ?? false)
            text: "keyboard_capslock"
            iconSize: Appearance.font.pixelSize.larger
            fill: 1
            color: root.iconColor
        }
        MaterialSymbol {
            visible: KeyboardLockService.available && (KeyboardLockService.numLock ?? false)
            text: "numbers"
            iconSize: Appearance.font.pixelSize.larger
            fill: 1
            color: root.iconColor
        }
        MaterialSymbol {
            text: root.wifiIcon()
            iconSize: Appearance.font.pixelSize.larger
            color: root.iconColor
        }
        MaterialSymbol {
            visible: BluetoothService.available
            text: BluetoothService.connected ? "bluetooth_connected" : BluetoothService.enabled ? "bluetooth" : "bluetooth_disabled"
            iconSize: Appearance.font.pixelSize.larger
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

    // Wheel over the icon cluster steps the sink volume. The bar's own edge
    // scroll only covers the bare bar around the lanes.
    WheelHandler {
        onWheel: event => {
            const step = event.angleDelta.y > 0 ? 0.05 : -0.05;
            VolumeService.setSinkVolume(VolumeService.sinkVolume + step);
        }
    }
}

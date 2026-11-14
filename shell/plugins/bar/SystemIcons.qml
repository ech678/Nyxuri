// Fork & Trim: iNiR modules/ii/barM3/SystemIcons.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// B9.2 trim (ROADMAP B-8):
//   - the bare Flow is gone. Every status is a fixed 26px SystemIconSlot with
//     its own hover capsule, tooltip and click target, so a conditional icon
//     no longer changes its neighbours' width;
//   - Audio/Network/Bluetooth/Notifications stay the owning Nyxuri services
//     (VolumeService/NetworkService/BluetoothService/NotificationService);
//     the mic route is VolumeService.toggleSourceMute();
//   - peripheral low/critical batteries come from PeripheralBattery (the end4
//     service, forked in services/), with the end4 UPowerDeviceType glyph map;
//   - the 22px Nyxuri `larger` token is replaced by the 17px bar baseline
//     (`Appearance.sizes.barUtilIconSize`), matching the util buttons;
//   - contentColor/contentColorOverridden stay for BarGroup's per-widget style
//     override.

import QtQuick
import Quickshell
import Quickshell.Services.UPower
import qs.services
import qs.commons
import qs.commons.i18n
import qs.ui

Item {
    id: root

    property color contentColor: Appearance.colors.colOnLayer1
    property bool contentColorOverridden: false
    property bool vertical: Config.options.bar.vertical
    property bool isMaterial: PersonalizationConfig.barIsMaterial

    readonly property color iconColor: root.contentColorOverridden ? root.contentColor : (root.isMaterial ? M3Palette.pillInk("systemIcons") : Appearance.colors.colOnLayer1)

    // Probe surface (scripts/dev/probe-bar.sh): the probe walks this container
    // to read every slot's fixed geometry and visibility without duplicating
    // the layout.
    readonly property Item slotContainer: flow

    implicitWidth: root.vertical ? 32 : flow.implicitWidth + (root.isMaterial ? 12 : 4)
    implicitHeight: root.vertical ? flow.implicitHeight + 4 : 32

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

    function peripheralIcon(type): string {
        switch (type) {
        case UPowerDeviceType.Mouse:
            return "mouse";
        case UPowerDeviceType.Keyboard:
            return "keyboard";
        case UPowerDeviceType.Headset:
        case UPowerDeviceType.Headphones:
            return "headphones";
        case UPowerDeviceType.GamingInput:
            return "sports_esports";
        case UPowerDeviceType.Phone:
            return "smartphone";
        default:
            return "battery_alert";
        }
    }

    // Independent click language: open the owning quick-settings view on this
    // bar's screen; a second click on the same view closes the panel again.
    function openQuickSettings(view) {
        if (WidgetState.quickSettingsOpen && WidgetState.quickSettingsView === view) {
            ActionGateway.requestSidebarToggle("quicksettings");
            return;
        }
        const screenName = root.QsWindow.window?.screen?.name ?? "";
        if (!ActionGateway.requestSidebarOpenOnScreen("quicksettings", view, screenName))
            ActionGateway.requestSidebarToggle("quicksettings");
    }

    Flow {
        id: flow

        anchors.centerIn: parent
        flow: root.vertical ? Flow.TopToBottom : Flow.LeftToRight
        spacing: root.isMaterial ? 2 : 4

        SystemIconSlot {
            id: volumeSlot

            slotKey: "volume"

            isMaterial: root.isMaterial
            vertical: root.vertical
            contentColor: root.iconColor
            contentColorOverridden: true
            iconText: VolumeService.sinkMuted ? "volume_off" : "volume_up"
            toolTipText: VolumeService.sinkMuted ? I18n.tr("Muted") : `${I18n.tr("Volume")} ${Math.round((VolumeService.sinkVolume ?? 0) * 100)}%`
            onClicked: event => {
                if (event.button === Qt.MiddleButton)
                    VolumeService.toggleSinkMute();
                else
                    root.openQuickSettings("audio");
            }
            onWheeled: delta => {
                if (delta > 0)
                    VolumeService.setSinkVolume(VolumeService.sinkVolume + 0.05);
                else if (delta < 0)
                    VolumeService.setSinkVolume(VolumeService.sinkVolume - 0.05);
            }
        }

        SystemIconSlot {
            slotKey: "mic"
            isMaterial: root.isMaterial
            vertical: root.vertical
            visible: VolumeService.sourceMuted
            contentColor: root.iconColor
            contentColorOverridden: true
            iconText: "mic_off"
            toolTipText: I18n.tr("Microphone is muted")
            onClicked: VolumeService.toggleSourceMute()
        }

        SystemIconSlot {
            slotKey: "keyboard"
            isMaterial: root.isMaterial
            vertical: root.vertical
            visible: KeyboardIndicators.hasPanelIndicators
            clickable: false
            contentColor: root.iconColor
            contentColorOverridden: true
            toolTipText: KeyboardIndicators.currentLayoutName.length > 0 ? KeyboardIndicators.currentLayoutName : I18n.tr("Keyboard indicators")

            HyprlandXkbIndicator {
                vertical: root.vertical
                color: root.iconColor
            }
        }

        SystemIconSlot {
            slotKey: "wifi"
            isMaterial: root.isMaterial
            vertical: root.vertical
            contentColor: root.iconColor
            contentColorOverridden: true
            iconText: root.wifiIcon()
            toolTipText: NetworkService.connected ? (NetworkService.activeSsid || I18n.tr("Wi-Fi")) : I18n.tr("Wi-Fi")
            onClicked: root.openQuickSettings("network")
        }

        SystemIconSlot {
            slotKey: "bluetooth"
            isMaterial: root.isMaterial
            vertical: root.vertical
            visible: BluetoothService.available
            contentColor: root.iconColor
            contentColorOverridden: true
            iconText: BluetoothService.connected ? "bluetooth_connected" : BluetoothService.enabled ? "bluetooth" : "bluetooth_disabled"
            toolTipText: BluetoothService.connected ? (BluetoothService.connectedName || I18n.tr("Bluetooth")) : I18n.tr("Bluetooth")
            onClicked: root.openQuickSettings("bluetooth")
        }

        Repeater {
            model: PeripheralBattery.lowDevices

            delegate: SystemIconSlot {
                required property var modelData

                readonly property bool critical: PeripheralBattery.isCritical(modelData)

                slotKey: "peripheral"
                isMaterial: root.isMaterial
                vertical: root.vertical
                clickable: false
                isActive: true
                iconText: root.peripheralIcon(modelData.type)
                contentColor: critical ? Appearance.colors.colError : root.iconColor
                contentColorOverridden: true
                toolTipText: `${modelData.model || I18n.tr("Device")} • ${Math.round(modelData.percentage * 100)}%`
            }
        }

        SystemIconSlot {
            id: notificationSlot

            slotKey: "notifications"

            isMaterial: root.isMaterial
            vertical: root.vertical
            visible: NotificationService.silent || NotificationService.unread > 0
            contentColor: root.iconColor
            contentColorOverridden: true
            toolTipText: I18n.tr("Notifications")
            onClicked: root.openQuickSettings("settings")

            Item {
                width: 26
                height: 26

                MaterialSymbol {
                    anchors.centerIn: parent
                    text: NotificationService.silent ? "notifications_paused" : "notifications"
                    iconSize: Appearance.sizes.barUtilIconSize
                    color: notificationSlot.hovered && root.isMaterial ? M3Palette.primaryForeground : root.iconColor
                }

                Rectangle {
                    readonly property bool showCount: Config.options.bar.m3.indicators.notifications.showUnreadCount

                    visible: !NotificationService.silent && NotificationService.unread > 0
                    anchors {
                        right: parent.right
                        top: parent.top
                        rightMargin: 0
                        topMargin: 1
                    }
                    radius: Appearance.rounding.full
                    color: root.isMaterial ? M3Palette.primaryForeground : Appearance.colors.colOnLayer0
                    implicitHeight: showCount ? Math.max(countLabel.implicitWidth, countLabel.implicitHeight) : 8
                    implicitWidth: implicitHeight

                    StyledText {
                        id: countLabel

                        visible: parent.showCount
                        anchors.centerIn: parent
                        font.pixelSize: Appearance.font.pixelSize.smallest
                        color: root.isMaterial ? M3Palette.primary : Appearance.colors.colLayer0
                        text: NotificationService.unread
                    }
                }
            }
        }
    }
}

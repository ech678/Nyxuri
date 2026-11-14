// Fork & Trim: end4-pC services/PeripheralBattery.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri:
//   - the upstream translation helper becomes I18n.tr; the upstream common
//     module import is dropped;
//   - notify-send leaves through ActionGateway.execute(args,
//     "bar:peripheral-battery") with an owner instead of a bare detached exec;
//   - `deviceSource` is the injected device list (live UPower by default).
//     scripts/dev/probe-bar.sh swaps plain objects in so the bar slots have
//     runtime evidence without real peripherals.

pragma Singleton

import qs.services
import qs.commons.i18n
import Quickshell
import Quickshell.Services.UPower
import QtQuick

Singleton {
    id: root

    readonly property var kinds: [UPowerDeviceType.Mouse, UPowerDeviceType.Keyboard, UPowerDeviceType.Headset, UPowerDeviceType.Headphones, UPowerDeviceType.GamingInput, UPowerDeviceType.Touchpad, UPowerDeviceType.Tablet, UPowerDeviceType.Phone]

    // Probe seam: the bar probe injects plain objects with the same shape as
    // UPowerDevice (nativePath/model/type/percentage/state/isPresent).
    property var deviceSource: UPower.devices.values

    readonly property var devices: Array.from(root.deviceSource || []).filter(dev => dev.isPresent && root.kinds.includes(dev.type))

    function isDraining(dev) {
        return dev.state !== UPowerDeviceState.Charging && dev.state !== UPowerDeviceState.FullyCharged;
    }

    function isLow(dev) {
        return dev.percentage > 0 && dev.percentage <= Config.options.battery.peripheralLow / 100 && root.isDraining(dev);
    }

    function isCritical(dev) {
        return dev.percentage > 0 && dev.percentage <= Config.options.battery.peripheralCritical / 100 && root.isDraining(dev);
    }

    readonly property var lowDevices: root.devices.filter(dev => root.isLow(dev))

    Instantiator {
        model: ScriptModel {
            values: root.devices
            objectProp: "nativePath"
        }
        delegate: QtObject {
            id: tracker
            required property var modelData
            readonly property string name: modelData.model || I18n.tr("Device")
            readonly property bool low: root.isLow(modelData)
            readonly property bool critical: root.isCritical(modelData)

            onLowChanged: {
                if (!low || critical || !Config.options.battery.peripheralNotify)
                    return;
                ActionGateway.execute(["notify-send", I18n.tr("%1 battery low").arg(tracker.name), I18n.tr("%1% remaining").arg(Math.round(modelData.percentage * 100)), "-a", "Shell", "--hint=int:transient:1",], "bar:peripheral-battery");
            }

            onCriticalChanged: {
                if (!critical || !Config.options.battery.peripheralNotify)
                    return;
                ActionGateway.execute(["notify-send", I18n.tr("%1 battery critically low").arg(tracker.name), I18n.tr("%1% remaining, please charge it").arg(Math.round(modelData.percentage * 100)), "-u", "critical", "-a", "Shell", "--hint=int:transient:1",], "bar:peripheral-battery");
            }
        }
    }
}

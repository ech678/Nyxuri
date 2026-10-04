import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

StyledFlickable {
    id: root

    readonly property var savedDevices: BluetoothService.devices.filter(device => {
        return device.paired || device.bonded || device.trusted;
    })
    readonly property string statusMessage: {
        if (BluetoothService.lastError.length > 0)
            return BluetoothService.lastError;

        if (!BluetoothService.available)
            return I18n.tr("No Bluetooth adapter detected or BlueZ is unavailable");

        if (BluetoothService.blocked)
            return I18n.tr("The Bluetooth adapter is blocked by rfkill");

        return "";
    }

    signal pairingRequested
    signal deviceRequested(string address, string adapterId)

    function deviceStatus(device) {
        if (device.blocked)
            return I18n.tr("Blocked");

        if (device.connected)
            return device.batteryAvailable ? I18n.tr("Connected · %1%").arg(device.batteryLevel) : I18n.tr(
                                                 "Connected");

        return "";
    }

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingL

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: root.statusMessage.length > 0
            tone: BluetoothService.lastError.length > 0 || !BluetoothService.available ? "error" : "warning"
            message: root.statusMessage
        }

        SettingsSection {
            Layout.fillWidth: true

            SettingsRow {
                Layout.fillWidth: true
                iconName: BluetoothService.enabled ? "bluetooth" : "bluetooth_disabled"
                title: I18n.tr("Bluetooth")

                trailing: StyledSwitch {
                    checked: BluetoothService.enabled
                    enabled: BluetoothService.available && !BluetoothService.blocked && !BluetoothService.busy
                    Accessible.name: I18n.tr("Bluetooth switch")
                    onToggled: BluetoothService.setBluetoothEnabled(checked)
                }
            }
        }

        SettingsSection {
            id: searchSection0
            Layout.fillWidth: true
            title: searchAnchor0.title
            SettingsSearchAnchor {
                id: searchAnchor0
                target: searchSection0
                declaration:
                    '{"id":"general.connected-devices.section.saved-devices","route":"general.connected-devices","title":"Saved devices","context":"ConnectedDevicesPage","icon":"devices_other","aliases":[]}'
            }
            iconName: "devices_other"

            Repeater {
                model: root.savedDevices

                SettingsRow {
                    id: savedDeviceRow

                    required property var modelData

                    Layout.fillWidth: true
                    iconName: BluetoothDeviceIcon.iconName(savedDeviceRow.modelData)
                    title: savedDeviceRow.modelData.name
                    supportingText: root.deviceStatus(savedDeviceRow.modelData)
                    interactive: BluetoothService.enabled
                    highlighted: savedDeviceRow.modelData.connected
                    onClicked: root.deviceRequested(savedDeviceRow.modelData.address,
                                                    savedDeviceRow.modelData.adapterId)

                    trailing: MaterialSymbol {
                        text: "chevron_right"
                        iconSize: Metrics.iconS
                        color: Appearance.colors.colOnSurfaceVariant
                    }
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                visible: root.savedDevices.length === 0
                iconName: "devices_other"
                title: I18n.tr("No saved devices")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                enabled: BluetoothService.available && BluetoothService.enabled && !BluetoothService.blocked
                         && !BluetoothService.busy
                iconName: "add"
                text: I18n.tr("Pair new device")
                trailingIconName: "chevron_right"
                onClicked: root.pairingRequested()
            }
        }

        SettingsSection {
            id: searchSection1
            Layout.fillWidth: true
            visible: BluetoothService.adapters.length > 1
            title: searchAnchor1.title
            SettingsSearchAnchor {
                id: searchAnchor1
                target: searchSection1
                declaration:
                    '{"id":"general.connected-devices.section.bluetooth-adapter","route":"general.connected-devices","title":"Bluetooth adapter","context":"ConnectedDevicesPage","icon":"devices_other","aliases":[]}'
            }
            iconName: "settings_bluetooth"

            Repeater {
                model: BluetoothService.adapters

                SettingsRow {
                    id: adapterRow

                    required property var modelData

                    Layout.fillWidth: true
                    iconName: adapterRow.modelData.blocked ? "bluetooth_disabled" : "settings_bluetooth"
                    title: adapterRow.modelData.name || adapterRow.modelData.id || I18n.tr(
                               "Bluetooth adapter")
                    supportingText: adapterRow.modelData.blocked ? I18n.tr("%1 · Blocked by rfkill").arg(
                                                                       adapterRow.modelData.id) :
                                                                   adapterRow.modelData.id

                    trailing: StyledSwitch {
                        checked: adapterRow.modelData.enabled
                        enabled: !adapterRow.modelData.blocked && !BluetoothService.busy
                        Accessible.name: I18n.tr("Toggle adapter %1").arg(adapterRow.modelData.name
                                                                          || adapterRow.modelData.id)
                        onToggled: BluetoothService.setAdapterEnabled(adapterRow.modelData, checked)
                    }
                }
            }
        }

        SettingsSection {
            id: searchSection2
            Layout.fillWidth: true
            title: searchAnchor2.title
            SettingsSearchAnchor {
                id: searchAnchor2
                target: searchSection2
                declaration:
                    '{"id":"general.connected-devices.section.advanced-settings","route":"general.connected-devices","title":"Advanced settings","context":"ConnectedDevicesPage","icon":"devices_other","aliases":[]}'
            }
            iconName: "tune"

            SettingsRow {
                Layout.fillWidth: true
                iconName: "visibility"
                title: I18n.tr("Allow discovery")

                trailing: StyledSwitch {
                    checked: BluetoothService.discoverable
                    enabled: BluetoothService.enabled && !BluetoothService.busy
                    Accessible.name: I18n.tr("Allow discovery")
                    onToggled: BluetoothService.setDiscoverable(checked)
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "handshake"
                title: I18n.tr("Allow pairing")

                trailing: StyledSwitch {
                    checked: BluetoothService.pairable
                    enabled: BluetoothService.enabled && !BluetoothService.busy
                    Accessible.name: I18n.tr("Allow pairing")
                    onToggled: BluetoothService.setPairable(checked)
                }
            }
        }
    }
}

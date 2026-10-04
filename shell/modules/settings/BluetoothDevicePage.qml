import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

StyledFlickable {
    id: root

    property string deviceAddress: ""
    property string deviceAdapterId: ""
    property bool pageReady: false
    readonly property var device: BluetoothService.devices.find(candidate => {
        return candidate.address === root.deviceAddress && (root.deviceAdapterId.length === 0
                                                            || candidate.adapterId === root.deviceAdapterId);
    }) || null
    readonly property string pageTitle: root.device ? root.device.name : I18n.tr("Bluetooth device")
    readonly property bool deviceChanging: root.device && (root.device.connecting
                                                           || root.device.disconnecting
                                                           || root.device.pairing)

    signal returnRequested

    function statusText() {
        if (!root.device)
            return "";

        if (root.device.blocked)
            return I18n.tr("Blocked");

        if (root.device.connecting)
            return I18n.tr("Connecting…");

        if (root.device.disconnecting)
            return I18n.tr("Disconnecting…");

        if (root.device.connected)
            return root.device.batteryAvailable ? I18n.tr("Connected · %1%").arg(root.device.batteryLevel) :
                                                  I18n.tr("Connected");

        return I18n.tr("Saved");
    }

    function ensureDeviceAvailable() {
        if (root.pageReady && !root.device)
            root.returnRequested();
    }

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2
    onDeviceChanged: root.ensureDeviceAvailable()
    Component.onCompleted: {
        root.pageReady = true;
        root.ensureDeviceAvailable();
    }

    Connections {
        function onEnabledChanged() {
            if (!BluetoothService.enabled)
                root.returnRequested();
        }

        function onOperationSucceeded(operation) {
            if (operation === "forget")
                root.returnRequested();
        }

        target: BluetoothService
    }

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingL

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: BluetoothService.lastError.length > 0
            tone: "error"
            message: BluetoothService.lastError
        }

        SettingsSection {
            Layout.fillWidth: true

            SettingsRow {
                Layout.fillWidth: true
                iconName: BluetoothDeviceIcon.iconName(root.device)
                title: root.statusText()
                highlighted: root.device ? root.device.connected : false

                trailing: ActionButton {
                    visible: root.device !== null
                    enabled: root.device && BluetoothService.enabled && !BluetoothService.busy &&
                             !root.deviceChanging && (!root.device.blocked || root.device.connected)
                    filled: root.device ? !root.device.connected : false
                    iconName: root.device && root.device.connected ? "link_off" : "link"
                    text: root.device && root.device.connected ? I18n.tr("Disconnect") : I18n.tr("Connect")
                    onClicked: {
                        if (!root.device)
                            return;

                        if (root.device.connected)
                            BluetoothService.disconnectDevice(root.device);
                        else
                            BluetoothService.connectDevice(root.device);
                    }
                }
            }

            SettingsActionRow {
                Layout.fillWidth: true
                enabled: root.device !== null && !BluetoothService.busy
                iconName: "delete"
                text: I18n.tr("Forget device")
                trailingIconName: ""
                onClicked: forgetDialog.open()
            }
        }

        SettingsSection {
            Layout.fillWidth: true
            title: I18n.tr("Connection", "Bluetooth settings section")
            iconName: "link"

            SettingsRow {
                Layout.fillWidth: true
                iconName: "verified_user"
                title: I18n.tr("Trusted device")

                trailing: StyledSwitch {
                    checked: root.device ? root.device.trusted : false
                    enabled: root.device !== null && !BluetoothService.busy
                    Accessible.name: I18n.tr("Trusted device")
                    onToggled: {
                        if (root.device)
                            BluetoothService.setDeviceTrusted(root.device, checked);
                    }
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "block"
                title: I18n.tr("Block device")

                trailing: StyledSwitch {
                    checked: root.device ? root.device.blocked : false
                    enabled: root.device !== null && !BluetoothService.busy
                    Accessible.name: I18n.tr("Block device")
                    onToggled: {
                        if (root.device)
                            BluetoothService.setDeviceBlocked(root.device, checked);
                    }
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "power_settings_new"
                title: I18n.tr("Allow wake")

                trailing: StyledSwitch {
                    checked: root.device ? root.device.wakeAllowed : false
                    enabled: root.device !== null && !BluetoothService.busy
                    Accessible.name: I18n.tr("Allow device to wake the system")
                    onToggled: {
                        if (root.device)
                            BluetoothService.setDeviceWakeAllowed(root.device, checked);
                    }
                }
            }
        }

        SettingsSection {
            Layout.fillWidth: true
            title: I18n.tr("Device information")
            iconName: "info"

            SettingsRow {
                Layout.fillWidth: true
                iconName: "battery_full"
                title: I18n.tr("Battery")
                supportingText: root.device && root.device.batteryAvailable ? I18n.tr("%1%").arg(root.device.batteryLevel) :
                                                                              I18n.tr("Unavailable")

                trailing: ThinReadOnlySlider {
                    visible: root.device && root.device.batteryAvailable
                    Layout.preferredWidth: visible ? Math.min(180, Math.max(80, root.width * 0.28)) : 0
                    value: root.device && root.device.batteryAvailable ? root.device.battery : 0
                    Accessible.name: root.device && root.device.batteryAvailable ? I18n.tr(
                                                                                       "Device battery %1%").arg(
                                                                                       root.device.batteryLevel) :
                                                                                   I18n.tr("Device battery unavailable")
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "fingerprint"
                title: I18n.tr("Address")
                supportingText: root.device ? root.device.address : ""
            }

            SettingsRow {
                Layout.fillWidth: true
                iconName: "settings_bluetooth"
                title: I18n.tr("Adapter")
                supportingText: root.device ? root.device.adapterId : ""
            }
        }
    }

    MaterialDialog {
        id: forgetDialog

        anchors.centerIn: Overlay.overlay
        width: Math.min(420, root.width - Metrics.spacingL * 2)
        dialogTitle: root.device ? I18n.tr("Forget “%1”?").arg(root.device.name) : I18n.tr("Forget device?")
        messageText: I18n.tr("This removes the saved Bluetooth pairing information for this device.")

        actionsComponent: Component {
            RowLayout {
                spacing: Metrics.spacingS

                Item {
                    Layout.fillWidth: true
                }

                ActionButton {
                    text: I18n.tr("Cancel")
                    onClicked: forgetDialog.close()
                }

                ActionButton {
                    enabled: root.device !== null && !BluetoothService.busy
                    text: I18n.tr("Forget")
                    onClicked: {
                        const target = root.device;
                        forgetDialog.close();
                        if (target)
                            BluetoothService.forgetDevice(target);
                    }
                }
            }
        }
    }
}

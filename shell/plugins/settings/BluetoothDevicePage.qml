pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Bluetooth device subpage (T3 M4): NexusPageBase subpage titled by the
// device itself. The connect/disconnect and battery rows carry trailing
// controls no atom holds (action button, read-only meter) and stay custom
// connected rows; trust/block/wake ride the toggle atom.
NexusPageBase {
    id: root

    title: root.device ? root.device.name : I18n.tr("Bluetooth device")
    isSubPage: true

    // Window contract surface — consumed by the ConnectedDevices shell.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property string deviceAddress: ""
    property string deviceAdapterId: ""
    property bool pageReady: false
    readonly property var device: BluetoothService.devices.find(candidate => {
        return candidate.address === root.deviceAddress && (root.deviceAdapterId.length === 0
                                                            || candidate.adapterId === root.deviceAdapterId);
    }) || null
    readonly property bool deviceChanging: root.device && (root.device.connecting
                                                           || root.device.disconnecting
                                                           || root.device.pairing)

    signal returnRequested

    onBackRequested: root.returnRequested()

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
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: BluetoothService.lastError.length > 0
            tone: "error"
            message: BluetoothService.lastError
        }

        // Status + connect/disconnect action
        ConnectedRect {
            first: true
            Layout.fillWidth: true
            implicitHeight: statusRowLayout.implicitHeight + NexusStyle.padding.medium * 2

            RowLayout {
                id: statusRowLayout

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                MaterialSymbol {
                    text: BluetoothDeviceIcon.iconName(root.device)
                    iconSize: NexusStyle.icon.medium
                    fill: 1
                    color: Appearance.m3colors.m3onSurfaceVariant
                }

                StyledText {
                    Layout.fillWidth: true
                    text: root.statusText()
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    elide: Text.ElideRight
                }

                ActionButton {
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
        }

        PreferenceAction {
            last: true
            enabled: root.device !== null && !BluetoothService.busy
            icon: "delete"
            text: I18n.tr("Forget device")
            trailingIcon: ""
            onClicked: forgetDialog.open()
        }

        // Connection
        PreferenceHeader {
            text: I18n.tr("Connection", "Bluetooth settings section")
        }

        PreferenceToggle {
            first: true
            icon: "verified_user"
            text: I18n.tr("Trusted device")
            checked: root.device ? root.device.trusted : false
            enabled: root.device !== null && !BluetoothService.busy
            onToggled: {
                if (root.device)
                    BluetoothService.setDeviceTrusted(root.device, checked);
            }
        }

        PreferenceToggle {
            icon: "block"
            text: I18n.tr("Block device")
            checked: root.device ? root.device.blocked : false
            enabled: root.device !== null && !BluetoothService.busy
            onToggled: {
                if (root.device)
                    BluetoothService.setDeviceBlocked(root.device, checked);
            }
        }

        PreferenceToggle {
            last: true
            icon: "power_settings_new"
            text: I18n.tr("Allow wake")
            checked: root.device ? root.device.wakeAllowed : false
            enabled: root.device !== null && !BluetoothService.busy
            onToggled: {
                if (root.device)
                    BluetoothService.setDeviceWakeAllowed(root.device, checked);
            }
        }

        // Device information
        PreferenceHeader {
            text: I18n.tr("Device information")
        }

        ConnectedRect {
            first: true
            Layout.fillWidth: true
            implicitHeight: batteryRowLayout.implicitHeight + NexusStyle.padding.medium * 2

            RowLayout {
                id: batteryRowLayout

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                MaterialSymbol {
                    text: "battery_full"
                    iconSize: NexusStyle.icon.medium
                    fill: 1
                    color: Appearance.m3colors.m3onSurfaceVariant
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    StyledText {
                        Layout.fillWidth: true
                        text: I18n.tr("Battery")
                        color: Appearance.m3colors.m3onSurface
                        font.pixelSize: NexusStyle.font.bodyMedium
                        elide: Text.ElideRight
                    }

                    StyledText {
                        Layout.fillWidth: true
                        text: root.device && root.device.batteryAvailable ? I18n.tr("%1%").arg(
                                                                                root.device.batteryLevel) :
                                                                            I18n.tr("Unavailable")
                        color: Appearance.m3colors.m3outline
                        font.pixelSize: NexusStyle.font.labelSmall
                        elide: Text.ElideRight
                    }
                }

                ThinReadOnlySlider {
                    visible: root.device && root.device.batteryAvailable
                    Layout.preferredWidth: visible ? Math.min(180, Math.max(80, root.width * 0.28)) : 0
                    value: root.device && root.device.batteryAvailable ? root.device.battery : 0
                    Accessible.name: root.device && root.device.batteryAvailable ? I18n.tr(
                                                                                       "Device battery %1%").arg(
                                                                                       root.device.batteryLevel) :
                                                                                   I18n.tr("Device battery unavailable")
                }
            }
        }

        PreferenceInfo {
            icon: "fingerprint"
            label: I18n.tr("Address")
            subtext: root.device ? root.device.address : ""
        }

        PreferenceInfo {
            last: true
            icon: "settings_bluetooth"
            label: I18n.tr("Adapter")
            subtext: root.device ? root.device.adapterId : ""
        }

        // Popups ride inside the content column — the scaffold takes exactly
        // one root-level content child.
        MaterialDialog {
            id: forgetDialog

            anchors.centerIn: Overlay.overlay
            width: Math.min(420, root.width - NexusStyle.padding.large * 2)
            dialogTitle: root.device ? I18n.tr("Forget “%1”?").arg(root.device.name) : I18n.tr(
                                           "Forget device?")
            messageText: I18n.tr("This removes the saved Bluetooth pairing information for this device.")

            actionsComponent: Component {
                RowLayout {
                    spacing: NexusStyle.padding.small

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
}

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

Item {
    id: root

    property int searchRequestSerial: -1
    property string currentView: "overview" // "overview", "pairing", "device"
    property string selectedAddress: ""
    property string selectedAdapterId: ""
    property bool presentationActive: false
    property var parentModal: null

    readonly property var searchLeaf: currentView === "overview" ? overviewFlickable : subpageLoader.item ? (subpageLoader.item.searchLeaf || subpageLoader.item) : root

    function openSearchPath(path, serial) {
        const section = path.length ? path[0] : "overview";
        if (searchRequestSerial !== serial) {
            searchRequestSerial = serial;
            if (section === "bluetooth-pairing") {
                root.currentView = "pairing";
            } else {
                root.currentView = "overview";
            }
        }
        if (section === "bluetooth-pairing" && root.currentView !== "pairing")
            return "cancelled";
        if (section === "overview" && root.currentView !== "overview")
            return "cancelled";
        if (root.currentView === "overview")
            return "ready";
        if (!subpageLoader.ready || !subpageLoader.item)
            return "loading";
        return typeof subpageLoader.item.openSearchPath === "function"
            ? subpageLoader.item.openSearchPath(path.slice(1), serial)
            : "ready";
    }

    onCurrentViewChanged: {
        if (SettingsBackend.searchTarget && !SettingsBackend.applyingSearch && searchRequestSerial === SettingsBackend.searchSerial)
            SettingsBackend.cancelSearch();
        SettingsBackend.retrySearch();
    }

    function closeChildWindows() {
        if (subpageLoader.item && typeof subpageLoader.item.closeChildWindows === "function")
            subpageLoader.item.closeChildWindows();
        root.currentView = "overview";
    }

    readonly property var selectedDevice: BluetoothService.devices.find(device => {
        return device.address === root.selectedAddress && (root.selectedAdapterId.length === 0 || device.adapterId === root.selectedAdapterId);
    }) || null

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

    function deviceStatus(device) {
        if (device.blocked)
            return I18n.tr("Blocked");
        if (device.connected)
            return device.batteryAvailable ? I18n.tr("Connected · %1%").arg(device.batteryLevel) : I18n.tr("Connected");
        return "";
    }

    GeneralSubpageHeader {
        id: subpageHeader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        visible: root.currentView !== "overview"
        z: 2
        title: {
            if (root.currentView === "pairing")
                return I18n.tr("Pair new device");
            if (root.currentView === "device")
                return root.selectedDevice ? root.selectedDevice.name : I18n.tr("Bluetooth device");
            return I18n.tr("Connected devices");
        }
        iconName: {
            if (root.currentView === "pairing")
                return "bluetooth_searching";
            if (root.currentView === "device")
                return BluetoothDeviceIcon.iconName(root.selectedDevice);
            return "devices_other";
        }
        backAccessibleName: I18n.tr("Back to connected devices")
        onBackRequested: root.currentView = "overview"
    }

    SettingsPageHost {
        id: subpageLoader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: subpageHeader.bottom
        anchors.bottom: parent.bottom
        visible: root.currentView !== "overview"
        presentationActive: root.presentationActive && root.currentView !== "overview"
        source: {
            if (root.currentView === "pairing")
                return Qt.resolvedUrl("BluetoothPairingPage.qml");
            if (root.currentView === "device")
                return Qt.resolvedUrl("BluetoothDevicePage.qml");
            return "";
        }
        onLoaded: {
            SettingsBackend.retrySearch();
            if (!item)
                return;
            if ("parentModal" in item)
                item.parentModal = root.parentModal;
            if ("deviceAddress" in item)
                item.deviceAddress = root.selectedAddress;
            if ("deviceAdapterId" in item)
                item.deviceAdapterId = root.selectedAdapterId;
        }

        Connections {
            target: subpageLoader.item
            ignoreUnknownSignals: true
            function onReturnRequested() {
                root.currentView = "overview";
            }
        }
    }

    StyledFlickable {
        id: overviewFlickable
        anchors.fill: parent
        visible: root.currentView === "overview"
        clip: true
        contentWidth: width
        contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

        ColumnLayout {
            id: contentColumn

            width: Math.min(640, Math.max(0, overviewFlickable.width - Metrics.pageMargin * 2))
            x: Math.max(Metrics.pageMargin, (overviewFlickable.width - width) / 2)
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
                        '{"id":"connected-devices.section.saved-devices","route":"connected-devices","title":"Saved devices","context":"ConnectedDevicesPage","icon":"devices_other","aliases":["general.connected-devices.section.saved-devices"]}'
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
                        onClicked: {
                            root.selectedAddress = savedDeviceRow.modelData.address;
                            root.selectedAdapterId = savedDeviceRow.modelData.adapterId;
                            root.currentView = "device";
                        }

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
                    onClicked: root.currentView = "pairing"
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
                        '{"id":"connected-devices.section.bluetooth-adapter","route":"connected-devices","title":"Bluetooth adapter","context":"ConnectedDevicesPage","icon":"devices_other","aliases":["general.connected-devices.section.bluetooth-adapter"]}'
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
                        '{"id":"connected-devices.section.advanced-settings","route":"connected-devices","title":"Advanced settings","context":"ConnectedDevicesPage","icon":"devices_other","aliases":["general.connected-devices.section.advanced-settings"]}'
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
}

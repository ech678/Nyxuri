pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Connected devices shell (T3 M4): overview on the Nexus scaffold, Bluetooth
// subpages load through SettingsPageHost and render their own subpage titles
// + back arrows (the pre-M4 external subpage header is retired). Discovery
// and device leases stay with their owning pages.
Item {
    id: root

    property int searchRequestSerial: -1
    property string currentView: "overview" // "overview", "pairing", "device"
    property string selectedAddress: ""
    property string selectedAdapterId: ""
    property bool presentationActive: false
    property var parentModal: null

    readonly property var searchLeaf: currentView === "overview" ? overviewPage.flickable :
                                                                   subpageLoader.item ? (
                                                                                            subpageLoader.item.searchLeaf
                                                                                            || subpageLoader.item) :
                                                                                        root

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
        return typeof subpageLoader.item.openSearchPath === "function" ? subpageLoader.item.openSearchPath(
                                                                             path.slice(1), serial) : "ready";
    }

    onCurrentViewChanged: {
        if (SettingsBackend.searchTarget && !SettingsBackend.applyingSearch && searchRequestSerial
                === SettingsBackend.searchSerial)
            SettingsBackend.cancelSearch();
        SettingsBackend.retrySearch();
    }

    function closeChildWindows() {
        if (subpageLoader.item && typeof subpageLoader.item.closeChildWindows === "function")
            subpageLoader.item.closeChildWindows();
        root.currentView = "overview";
    }

    readonly property var selectedDevice: BluetoothService.devices.find(device => {
        return device.address === root.selectedAddress && (root.selectedAdapterId.length === 0
                                                           || device.adapterId === root.selectedAdapterId);
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
            return device.batteryAvailable ? I18n.tr("Connected · %1%").arg(device.batteryLevel) : I18n.tr(
                                                 "Connected");
        return "";
    }

    SettingsPageHost {
        id: subpageLoader

        anchors.fill: parent
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

    NexusPageBase {
        id: overviewPage

        anchors.fill: parent
        visible: root.currentView === "overview"
        title: SpotlightCatalog.title("connected-devices")

        ColumnLayout {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            width: overviewPage.cappedWidth
            spacing: NexusStyle.padding.extraSmall / 2

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: root.statusMessage.length > 0
                tone: BluetoothService.lastError.length > 0 || !BluetoothService.available ? "error" :
                                                                                             "warning"

                message: root.statusMessage
            }

            // The Bluetooth master switch leads the page bare, exactly like
            // the Caelestia Connected devices original.
            PreferenceToggle {
                first: true
                last: true
                icon: BluetoothService.enabled ? "bluetooth" : "bluetooth_disabled"
                text: I18n.tr("Bluetooth")
                checked: BluetoothService.enabled
                enabled: BluetoothService.available && !BluetoothService.blocked && !BluetoothService.busy
                onToggled: BluetoothService.setBluetoothEnabled(checked)
            }

            // Saved devices
            PreferenceHeader {
                id: savedHeader

                text: I18n.tr("Saved devices")

                SettingsSearchAnchor {
                    id: searchAnchor0
                    target: savedHeader
                    declaration:
                        '{"id":"connected-devices.section.saved-devices","route":"connected-devices","title":"Saved devices","context":"ConnectedDevicesPage","icon":"devices_other","aliases":["general.connected-devices.section.saved-devices"]}'
                }
            }

            Repeater {
                id: savedList

                model: root.savedDevices

                delegate: PreferenceAction {
                    id: savedDeviceRow

                    required property var modelData
                    required property int index

                    first: savedDeviceRow.index === 0
                    icon: BluetoothDeviceIcon.iconName(savedDeviceRow.modelData)
                    text: savedDeviceRow.modelData.name
                    subtext: root.deviceStatus(savedDeviceRow.modelData)
                    enabled: BluetoothService.enabled
                    onClicked: {
                        root.selectedAddress = savedDeviceRow.modelData.address;
                        root.selectedAdapterId = savedDeviceRow.modelData.adapterId;
                        root.currentView = "device";
                    }
                }
            }

            PreferenceInfo {
                first: root.savedDevices.length === 0
                icon: "devices_other"
                label: I18n.tr("No saved devices")
            }

            PreferenceAction {
                last: true
                enabled: BluetoothService.available && BluetoothService.enabled && !BluetoothService.blocked
                         && !BluetoothService.busy
                icon: "add"
                text: I18n.tr("Pair new device")
                onClicked: root.currentView = "pairing"
            }

            // Bluetooth adapter
            PreferenceHeader {
                id: adapterHeader

                visible: BluetoothService.adapters.length > 1
                text: I18n.tr("Bluetooth adapter")

                SettingsSearchAnchor {
                    id: searchAnchor1
                    target: adapterHeader
                    declaration:
                        '{"id":"connected-devices.section.bluetooth-adapter","route":"connected-devices","title":"Bluetooth adapter","context":"ConnectedDevicesPage","icon":"devices_other","aliases":["general.connected-devices.section.bluetooth-adapter"]}'
                }
            }

            Repeater {
                id: adapterList

                model: BluetoothService.adapters

                delegate: PreferenceToggle {
                    id: adapterRow

                    required property var modelData
                    required property int index

                    first: adapterRow.index === 0
                    last: adapterRow.index === adapterList.count - 1
                    icon: adapterRow.modelData.blocked ? "bluetooth_disabled" : "settings_bluetooth"
                    text: adapterRow.modelData.name || adapterRow.modelData.id || I18n.tr("Bluetooth adapter")
                    subtext: adapterRow.modelData.blocked ? I18n.tr("%1 · Blocked by rfkill").arg(
                                                                adapterRow.modelData.id) :
                                                            adapterRow.modelData.id
                    checked: adapterRow.modelData.enabled
                    enabled: !adapterRow.modelData.blocked && !BluetoothService.busy
                    onToggled: BluetoothService.setAdapterEnabled(adapterRow.modelData, checked)
                }
            }

            // Advanced settings
            PreferenceHeader {
                id: advancedHeader

                text: I18n.tr("Advanced settings")

                SettingsSearchAnchor {
                    id: searchAnchor2
                    target: advancedHeader
                    declaration:
                        '{"id":"connected-devices.section.advanced-settings","route":"connected-devices","title":"Advanced settings","context":"ConnectedDevicesPage","icon":"devices_other","aliases":["general.connected-devices.section.advanced-settings"]}'
                }
            }

            PreferenceToggle {
                first: true
                icon: "visibility"
                text: I18n.tr("Allow discovery")
                checked: BluetoothService.discoverable
                enabled: BluetoothService.enabled && !BluetoothService.busy
                onToggled: BluetoothService.setDiscoverable(checked)
            }

            PreferenceToggle {
                last: true
                icon: "handshake"
                text: I18n.tr("Allow pairing")
                checked: BluetoothService.pairable
                enabled: BluetoothService.enabled && !BluetoothService.busy
                onToggled: BluetoothService.setPairable(checked)
            }
        }
    }
}

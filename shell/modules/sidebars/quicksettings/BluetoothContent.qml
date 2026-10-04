import QtQuick
import qs.app
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.app.services
import qs.shared.i18n

WidgetPanel {
    id: root

    property bool foreground: false
    readonly property bool isActive: root.foreground && WidgetState.quickSettingsView === "bluetooth"
    property bool discoveryLeaseAcquired: false
    property bool initialLoadAttempted: false
    property bool initialLoading: false
    property bool refreshLoading: false
    property var pendingForgetDevice: null
    readonly property bool linearLoading: BluetoothService.busy && !refreshLoading
    readonly property string stateMessage: {
        if (BluetoothService.lastError.length > 0)
            return BluetoothService.lastError;

        if (!BluetoothService.available)
            return I18n.tr("No Bluetooth adapter detected or BlueZ is unavailable");

        if (!BluetoothService.enabled)
            return I18n.tr("Bluetooth is off");

        if (!root.initialLoading && !root.refreshLoading && BluetoothService.devices.length === 0)
            return I18n.tr("No Bluetooth devices discovered yet");

        return "";
    }

    function beginInitialLoad() {
        if (!root.isActive || !BluetoothService.available || !BluetoothService.enabled
                || root.initialLoadAttempted)
            return;

        initialLoadTimer.stop();
        root.initialLoadAttempted = true;
        root.initialLoading = BluetoothService.availableDevices.length === 0;
        if (root.initialLoading)
            initialLoadTimer.restart();
    }

    function finishInitialLoad() {
        initialLoading = false;
        initialLoadTimer.stop();
    }

    function finishTransientLoading() {
        finishInitialLoad();
        refreshLoading = false;
        refreshTimer.stop();
    }

    function updateDiscoveryLease() {
        if (isActive && !discoveryLeaseAcquired) {
            BluetoothService.acquireDiscovery("right-sidebar-bluetooth");
            discoveryLeaseAcquired = true;
            Qt.callLater(root.beginInitialLoad);
        } else if (!isActive && discoveryLeaseAcquired) {
            BluetoothService.releaseDiscovery("right-sidebar-bluetooth");
            discoveryLeaseAcquired = false;
            finishTransientLoading();
        }
    }

    function restartDiscoveryLease() {
        if (!root.discoveryLeaseAcquired || !BluetoothService.enabled || root.refreshLoading)
            return;

        finishInitialLoad();
        BluetoothService.releaseDiscovery("right-sidebar-bluetooth");
        BluetoothService.acquireDiscovery("right-sidebar-bluetooth");
        refreshLoading = true;
        refreshTimer.restart();
    }

    function deviceSupportingText(device) {
        const states = [];
        if (device.blocked)
            states.push(I18n.tr("Blocked"));
        else if (device.pairing)
            states.push(I18n.tr("Pairing"));
        else if (device.connected)
            states.push(I18n.tr("Connected"));
        else if (device.paired || device.bonded)
            states.push(I18n.tr("Paired"));
        else
            states.push(I18n.tr("Available devices"));
        if (device.batteryAvailable)
            states.push(I18n.tr("Battery %1%").arg(device.batteryLevel));

        return states.join(" · ");
    }

    title: I18n.tr("Bluetooth")
    icon: "bluetooth"
    showBackButton: true
    backAction: () => {
        return WidgetState.quickSettingsView = "settings";
    }
    onIsActiveChanged: updateDiscoveryLease()
    Component.onCompleted: updateDiscoveryLease()
    Component.onDestruction: {
        if (discoveryLeaseAcquired)
            BluetoothService.releaseDiscovery("right-sidebar-bluetooth");
    }

    Connections {
        function onAvailableDevicesChanged() {
            if (BluetoothService.availableDevices.length > 0)
                root.finishInitialLoad();
        }

        function onEnabledChanged() {
            if (!BluetoothService.enabled)
                root.finishTransientLoading();
            else if (root.isActive)
                Qt.callLater(root.beginInitialLoad);
        }

        function onOperationFailed(operation, message) {
            if (operation === "discovery") {
                root.refreshLoading = false;
                refreshTimer.stop();
            }
        }

        target: BluetoothService
    }

    Timer {
        id: initialLoadTimer

        interval: 4000
        repeat: false
        onTriggered: root.initialLoading = false
    }

    Timer {
        id: refreshTimer

        interval: 1600
        repeat: false
        onTriggered: root.refreshLoading = false
    }

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Appearance.spacing.small

        ProgressBar {
            Layout.fillWidth: true
            Layout.preferredHeight: root.linearLoading ? 4 : 0
            opacity: root.linearLoading ? 1 : 0
            indeterminate: true
            Material.accent: Appearance.colors.colPrimary

            Behavior on Layout.preferredHeight {
                ElementMoveAnimation {}
            }

            Behavior on opacity {
                ElementMoveAnimation {}
            }
        }

        SidebarFlickable {
            id: sidebarScroll
            refreshEnabled: root.isActive && BluetoothService.available && BluetoothService.enabled &&
                            !BluetoothService.busy
            refreshing: root.refreshLoading
            onRefreshRequested: root.restartDiscoveryLease()

            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: bluetoothContent.implicitHeight + sidebarScroll.contentTopInset

            ColumnLayout {
                id: bluetoothContent
                y: sidebarScroll.contentTopInset

                width: parent.width
                spacing: Metrics.spacingL
                InlineStatusBanner {
                    Layout.topMargin: sidebarScroll.gapFor(0, 1)
                    Layout.fillWidth: true
                    visible: root.stateMessage.length > 0
                    tone: BluetoothService.lastError.length > 0 ? "error" : "info"
                    message: root.stateMessage
                }

                DeviceSection {
                    Layout.topMargin: sidebarScroll.gapFor(1, 1)

                    Layout.fillWidth: true
                    visible: BluetoothService.enabled && BluetoothService.connectedDevices.length > 0
                    sectionTitle: I18n.tr("Connected")
                    devicesModel: BluetoothService.connectedDevices
                    category: "connected"
                }

                DeviceSection {
                    Layout.topMargin: sidebarScroll.gapFor(2, 1)

                    Layout.fillWidth: true
                    visible: BluetoothService.enabled && BluetoothService.pairedDevices.length > 0
                    sectionTitle: I18n.tr("Paired")
                    devicesModel: BluetoothService.pairedDevices
                    category: "paired"
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(3, 1)

                    Layout.fillWidth: true
                    visible: BluetoothService.enabled
                    title: I18n.tr("Available devices")

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.initialLoading
                                                && BluetoothService.availableDevices.length === 0 ? 116 : 0
                        opacity: root.initialLoading ? 1 : 0
                        clip: true

                        Column {
                            anchors.centerIn: parent
                            spacing: Metrics.spacingL

                            MaterialLoadingIndicator {
                                anchors.horizontalCenter: parent.horizontalCenter
                                running: root.initialLoading
                                accessibleName: I18n.tr("Searching for available Bluetooth devices")
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: I18n.tr("Searching for nearby devices")
                                color: Appearance.colors.colOnLayer1
                                font.family: Fonts.ui
                                font.pixelSize: 12
                            }
                        }

                        Behavior on Layout.preferredHeight {
                            ElementMoveAnimation {}
                        }

                        Behavior on opacity {
                            ElementMoveAnimation {}
                        }
                    }

                    Repeater {
                        model: availablePages.items
                        BluetoothDeviceRow {
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.18)
                            deviceData: modelData
                            deviceCategory: "available"
                        }
                    }
                    ListPagination {
                        id: availablePages
                        model: BluetoothService.availableDevices
                    }

                    SettingsRow {
                        Layout.fillWidth: true
                        visible: !root.initialLoading && !root.refreshLoading
                                 && BluetoothService.availableDevices.length === 0
                        iconName: "search_off"
                        title: I18n.tr("No available devices found")
                    }
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(4, 1)

                    Layout.fillWidth: true
                    title: I18n.tr("Adapters")
                    supportingText: BluetoothService.discovering ? I18n.tr("Searching for nearby devices") :
                                                                   BluetoothService.enabled ? I18n.tr(
                                                                                                  "Device discovery is paused") :
                                                                                              I18n.tr("Turn on Bluetooth to start discovery")

                    Repeater {
                        model: adapterPages.items

                        SettingsRow {
                            required property var modelData
                            required property int index
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.16)

                            Layout.fillWidth: true
                            iconName: modelData.blocked ? "bluetooth_disabled" : "settings_bluetooth"
                            title: modelData.name || modelData.id || I18n.tr("Bluetooth adapter")
                            supportingText: modelData.blocked ? I18n.tr("Blocked by rfkill") :
                                                                modelData.enabled ? modelData.state : I18n.tr(
                                                                                        "Off")
                            highlighted: modelData.enabled

                            trailing: StyledSwitch {
                                scale: 0.72
                                checked: modelData.enabled
                                enabled: !modelData.blocked && !BluetoothService.busy
                                Accessible.name: I18n.tr("Toggle adapter ") + (modelData.name || modelData.id)
                                onToggled: BluetoothService.setAdapterEnabled(modelData, checked)
                            }
                        }
                    }
                    ListPagination {
                        id: adapterPages
                        model: BluetoothService.adapters
                    }

                    SettingsRow {
                        Layout.fillWidth: true
                        visible: BluetoothService.available
                        iconName: "visibility"
                        title: I18n.tr("Allow discovery")
                        supportingText: I18n.tr("Let nearby devices find this computer")
                        enabled: BluetoothService.enabled

                        trailing: StyledSwitch {
                            scale: 0.72
                            checked: BluetoothService.discoverable
                            enabled: BluetoothService.enabled && !BluetoothService.busy
                            Accessible.name: I18n.tr("Bluetooth discoverability")
                            onToggled: BluetoothService.setDiscoverable(checked)
                        }
                    }

                    SettingsRow {
                        Layout.fillWidth: true
                        visible: BluetoothService.available
                        iconName: "handshake"
                        title: I18n.tr("Allow pairing")
                        supportingText: ""
                        enabled: BluetoothService.enabled

                        trailing: StyledSwitch {
                            scale: 0.72
                            checked: BluetoothService.pairable
                            enabled: BluetoothService.enabled && !BluetoothService.busy
                            Accessible.name: I18n.tr("Bluetooth pairing")
                            onToggled: BluetoothService.setPairable(checked)
                        }
                    }
                }

                Item {
                    Layout.topMargin: sidebarScroll.gapFor(5, 1)

                    Layout.fillWidth: true
                    Layout.preferredHeight: Appearance.spacing.small
                }
            }
        }
    }

    MaterialDialog {
        id: forgetDialog

        width: Math.min(320, root.width - 48)
        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - height) / 2)
        dialogTitle: I18n.tr("Forget Bluetooth device")
        messageText: root.pendingForgetDevice ? I18n.tr(
                                                    "This will delete the pairing information for “%1”.").arg(
                                                    root.pendingForgetDevice.name) : ""

        actionsComponent: Component {
            RowLayout {
                spacing: Metrics.spacingS

                Item {
                    Layout.fillWidth: true
                }

                ActionButton {
                    text: I18n.tr("Cancel")
                    onClicked: {
                        forgetDialog.close();
                        root.pendingForgetDevice = null;
                    }
                }

                ActionButton {
                    text: I18n.tr("Forget")
                    onClicked: {
                        const target = root.pendingForgetDevice;
                        forgetDialog.close();
                        root.pendingForgetDevice = null;
                        if (target)
                            BluetoothService.forgetDevice(target);
                    }
                }
            }
        }
    }

    headerTools: RowLayout {
        spacing: Appearance.spacing.xSmall

        IconButton {
            enabled: BluetoothService.available && BluetoothService.enabled && !BluetoothService.busy &&
                     !root.refreshLoading
            iconName: "refresh"
            iconSize: 21
            iconColor: Appearance.colors.colOnLayer2
            accessibleName: I18n.tr("Scan for Bluetooth devices again")
            hoverStateLayerColor: Appearance.colors.colLayer2Hover
            pressedStateLayerColor: Appearance.colors.colLayer2Active
            onClicked: root.restartDiscoveryLease()
        }

        StyledSwitch {
            scale: 0.8
            checked: BluetoothService.enabled
            enabled: BluetoothService.available && !BluetoothService.busy
            Accessible.name: I18n.tr("Bluetooth switch")
            onToggled: BluetoothService.setBluetoothEnabled(checked)
        }
    }

    component DeviceSection: SettingsSection {
        id: deviceSection
        pullExpansion: sidebarScroll.detailExpansion

        property string sectionTitle: ""
        property var devicesModel: []
        property string category: ""

        title: sectionTitle
        contentSpacing: Metrics.spacingL

        Repeater {
            model: devicePages.items

            ColumnLayout {
                id: deviceDetails
                required property var modelData
                required property int index
                Layout.topMargin: sidebarScroll.gapFor(index, 0.16)

                Layout.fillWidth: true
                spacing: Metrics.spacingXS + sidebarScroll.detailExpansion

                BluetoothDeviceRow {
                    Layout.fillWidth: true
                    deviceData: deviceDetails.modelData
                    deviceCategory: deviceSection.category
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Trust device")
                    iconName: "verified_user"
                    trailing: StyledSwitch {
                        checked: deviceDetails.modelData.trusted
                        enabled: !BluetoothService.busy
                        Accessible.name: I18n.tr("Trust %1").arg(deviceDetails.modelData.name)
                        onToggled: BluetoothService.setDeviceTrusted(deviceDetails.modelData, checked)
                    }
                }

                SettingsRow {
                    Layout.fillWidth: true
                    title: I18n.tr("Wake computer")
                    iconName: "power_settings_new"
                    trailing: StyledSwitch {
                        checked: deviceDetails.modelData.wakeAllowed
                        enabled: !BluetoothService.busy
                        Accessible.name: I18n.tr("Allow %1 to wake the computer").arg(
                                             deviceDetails.modelData.name)
                        onToggled: BluetoothService.setDeviceWakeAllowed(deviceDetails.modelData, checked)
                    }
                }
            }
        }
        ListPagination {
            id: devicePages
            model: deviceSection.devicesModel
        }
    }

    component BluetoothDeviceRow: SettingsRow {
        id: deviceRow

        required property var deviceData
        property string deviceCategory: ""

        iconName: BluetoothDeviceIcon.iconName(deviceData)
        title: deviceData.name
        supportingText: root.deviceSupportingText(deviceData)
        highlighted: deviceData.connected
        enabled: !deviceData.blocked

        trailing: RowLayout {
            spacing: Appearance.spacing.xSmall

            MaterialSymbol {
                visible: deviceRow.deviceData.batteryAvailable
                text: deviceRow.deviceData.batteryLevel > 80 ? "battery_full" :
                                                               deviceRow.deviceData.batteryLevel > 30
                                                               ? "battery_4_bar" : "battery_1_bar"
                iconSize: 18
                color: Appearance.colors.colOnLayer1
            }

            ActionButton {
                visible: !deviceRow.deviceData.blocked
                enabled: !BluetoothService.busy
                text: deviceRow.deviceCategory === "connected" ? I18n.tr("Disconnect") :
                                                                 deviceRow.deviceCategory === "paired"
                                                                 ? I18n.tr("Connect") : I18n.tr("Pair")
                filled: false
                onClicked: {
                    if (deviceRow.deviceCategory === "connected")
                        BluetoothService.disconnectDevice(deviceRow.deviceData);
                    else if (deviceRow.deviceCategory === "paired")
                        BluetoothService.connectDevice(deviceRow.deviceData);
                    else
                        BluetoothService.pairDevice(deviceRow.deviceData);
                }
            }

            IconButton {
                visible: deviceRow.deviceData.paired || deviceRow.deviceData.bonded
                         || deviceRow.deviceData.trusted
                controlSize: 34
                enabled: !BluetoothService.busy
                iconName: "more_vert"
                iconSize: 18
                iconColor: Appearance.colors.colOnLayer2
                accessibleName: I18n.tr("Bluetooth device action")
                hoverStateLayerColor: Appearance.colors.colLayer3Hover
                pressedStateLayerColor: Appearance.colors.colLayer3Active
                onClicked: deviceMenu.open()

                StyledMenu {
                    id: deviceMenu

                    StyledMenuItem {
                        iconName: "delete"
                        destructive: true
                        text: I18n.tr("Forget device")
                        onTriggered: {
                            root.pendingForgetDevice = deviceRow.deviceData;
                            forgetDialog.open();
                        }
                    }
                }
            }
        }
    }
}

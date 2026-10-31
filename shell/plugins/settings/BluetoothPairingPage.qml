pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Pair new device subpage (T3 M4): NexusPageBase subpage with its own back
// arrow; the discovery lease follows page-readiness, presentation and radio
// state exactly as before. Available-device rows carry a per-row pairing
// spinner — a trailing-state no atom holds — so they stay custom connected
// rows in the Caelestia list shape.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("connected-devices.bluetooth-pairing")
    isSubPage: true

    // Window contract surface — consumed by the ConnectedDevices shell.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false
    property bool pageReady: false
    property bool discoveryLeaseAcquired: false
    property string pendingAddress: ""

    signal returnRequested

    onBackRequested: root.returnRequested()

    function updateDiscoveryLease() {
        const requested = root.pageReady && root.presentationActive && BluetoothService.available
              && BluetoothService.enabled;
        if (requested && !root.discoveryLeaseAcquired) {
            BluetoothService.acquireDiscovery("control-center-bluetooth-pairing");
            root.discoveryLeaseAcquired = true;
        } else if (!requested && root.discoveryLeaseAcquired) {
            BluetoothService.releaseDiscovery("control-center-bluetooth-pairing");
            root.discoveryLeaseAcquired = false;
        }
    }

    function closeChildWindows() {
        if (root.discoveryLeaseAcquired) {
            BluetoothService.releaseDiscovery("control-center-bluetooth-pairing");
            root.discoveryLeaseAcquired = false;
        }
    }

    onPresentationActiveChanged: root.updateDiscoveryLease()
    Component.onCompleted: {
        root.pageReady = true;
        root.updateDiscoveryLease();
    }
    Component.onDestruction: root.closeChildWindows()

    Connections {
        function onAvailableChanged() {
            root.updateDiscoveryLease();
            if (!BluetoothService.available)
                root.returnRequested();
        }

        function onEnabledChanged() {
            root.updateDiscoveryLease();
            if (!BluetoothService.enabled)
                root.returnRequested();
        }

        function onOperationSucceeded(operation) {
            if (operation === "pair" && root.pendingAddress.length > 0) {
                root.pendingAddress = "";
                root.returnRequested();
            }
        }

        function onOperationFailed(operation, message) {
            if (operation === "pair")
                root.pendingAddress = "";
        }

        target: BluetoothService
    }

    component NearbyDeviceRow: ConnectedRect {
        id: nearbyRow

        required property var modelData
        required property int index

        Layout.fillWidth: true
        implicitHeight: nearbyRowLayout.implicitHeight + NexusStyle.padding.medium * 2
        first: nearbyRow.index === 0
        last: nearbyRow.index === nearbyList.count - 1

        StateLayer {
            anchors.fill: parent
            layerRadius: (nearbyRow.first || nearbyRow.last) ? NexusStyle.rounding.extraLarge :
                                                               NexusStyle.rounding.extraSmall
            disabled: !rowPress.enabled
            color: Appearance.m3colors.m3onSurface
            hovered: rowPress.containsMouse
            pressed: rowPress.pressed
        }

        MouseArea {
            id: rowPress

            anchors.fill: parent
            enabled: !BluetoothService.busy && !nearbyRow.modelData.blocked
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.pendingAddress = nearbyRow.modelData.address;
                BluetoothService.pairDevice(nearbyRow.modelData);
            }
        }

        RowLayout {
            id: nearbyRowLayout

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            MaterialSymbol {
                text: BluetoothDeviceIcon.iconName(nearbyRow.modelData)
                iconSize: NexusStyle.icon.medium
                fill: 1
                color: Appearance.m3colors.m3onSurfaceVariant
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                StyledText {
                    Layout.fillWidth: true
                    text: nearbyRow.modelData.name
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    elide: Text.ElideRight
                }

                StyledText {
                    Layout.fillWidth: true
                    text: nearbyRow.modelData.pairing ? I18n.tr("Pairing…") : nearbyRow.modelData.address
                    color: Appearance.m3colors.m3outline
                    font.pixelSize: NexusStyle.font.labelSmall
                    elide: Text.ElideRight
                }
            }

            MaterialLoadingIndicator {
                visible: nearbyRow.modelData.pairing
                Layout.preferredWidth: visible ? NexusStyle.icon.medium : 0
                Layout.preferredHeight: visible ? NexusStyle.icon.medium : 0
                running: visible
                contained: false
                accessibleName: I18n.tr("Pairing %1").arg(nearbyRow.modelData.name)
            }
        }
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

        PreferenceHeader {
            id: nearbyHeader

            first: true
            text: I18n.tr("Nearby devices")

            SettingsSearchAnchor {
                id: searchAnchor0
                target: nearbyHeader
                declaration:
                    '{"id":"connected-devices.bluetooth-pairing.section.nearby-devices","route":"connected-devices.bluetooth-pairing","title":"Nearby devices","context":"BluetoothPairingPage","icon":"bluetooth_searching","aliases":["general.bluetooth-pairing.section.nearby-devices"]}'
            }
        }

        PreferenceInfo {
            first: true
            icon: BluetoothService.discovering ? "radar" : "search_off"
            label: BluetoothService.discovering ? I18n.tr("Searching for nearby devices") : I18n.tr(
                                                      "Waiting for Bluetooth scan")

            MaterialLoadingIndicator {
                anchors.right: parent.right
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                anchors.verticalCenter: parent.verticalCenter
                visible: BluetoothService.discovering
                implicitWidth: visible ? NexusStyle.icon.medium : 0
                implicitHeight: visible ? NexusStyle.icon.medium : 0
                running: visible
                contained: false
                accessibleName: I18n.tr("Searching for nearby Bluetooth devices")
            }
        }

        Repeater {
            id: nearbyList

            model: BluetoothService.availableDevices

            delegate: NearbyDeviceRow {}
        }

        PreferenceInfo {
            first: BluetoothService.availableDevices.length === 0
            last: true
            visible: BluetoothService.availableDevices.length === 0
            icon: "devices_other"
            label: I18n.tr("No nearby devices found yet")
        }
    }
}

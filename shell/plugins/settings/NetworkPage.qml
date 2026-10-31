pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Network page (T3 M4): NexusPageBase scaffold + M1 atom rows. Wired and
// active rows ride the action/info atoms; the nearby list keeps its fixed
// viewport with custom connected-card rows (trailing lock/bookmark glyphs a
// chevron atom cannot carry); scan/lease lifecycle stays byte-for-byte.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("network")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false
    property var passwordTarget: null
    property bool initialLoadAttempted: false
    property bool initialLoading: false
    readonly property var nearbyNetworks: NetworkService.nearbyWifiNetworks.filter(network => {
        return !network.active;
    })
    readonly property var activeNetwork: NetworkService.activeNetwork
    readonly property string activeConnectionKey: activeNetwork ? [activeNetwork.type,
                                                                   activeNetwork.deviceName,
                                                                   activeNetwork.name].join(":") : ""
    readonly property bool runtimeMatchesActive: activeNetwork !== null
                                                 && NetworkService.runtimeDetails.interfaceName === String(
                                                     activeNetwork.deviceName || "")
    readonly property bool multipleWifiDevices: NetworkService.wifiDevices.length > 1

    function beginInitialLoad() {
        if (root.initialLoadAttempted || !NetworkService.available || !NetworkService.wifiAvailable ||
                !NetworkService.wifiEnabled)
            return;

        root.initialLoadAttempted = true;
        root.initialLoading = root.nearbyNetworks.length === 0;
        if (root.initialLoading)
            initialLoadTimer.restart();
    }

    function finishInitialLoad() {
        root.initialLoading = false;
        initialLoadTimer.stop();
    }

    function connectivityException() {
        if (NetworkService.captivePortal)
            return I18n.tr("Sign-in required");

        if (NetworkService.limitedConnectivity)
            return I18n.tr("Limited connection");

        if (NetworkService.connected && NetworkService.connectivityKnown && !NetworkService.internetAvailable)
            return I18n.tr("No internet connection");

        return "";
    }

    function activeWifiDetails() {
        const details = [I18n.tr("Signal %1%").arg(NetworkService.signalStrength)];
        const exception = root.activeNetwork && root.activeNetwork.type === "wifi"
              ? root.connectivityException() : "";
        if (exception.length > 0)
            details.push(exception);

        return details.join(" · ");
    }

    function nearbyWifiDetails(network) {
        const details = [I18n.tr("Signal %1%").arg(network.strength)];
        if (root.multipleWifiDevices)
            details.push(network.deviceName);

        return details.join(" · ");
    }

    function profileForTarget(target) {
        if (!target)
            return null;

        let profiles = [];
        if (target.nativeSettings) {
            profiles = target.type === "wired" ? NetworkService.wiredProfiles :
                                                 NetworkService.savedWifiProfiles;
            return profiles.find(profile => {
                return profile.uuid === target.uuid;
            }) || null;
        }
        if (target.type === "wired") {
            const interfaceName = String(target.deviceName || target.name || "");
            profiles = NetworkService.wiredProfiles.filter(profile => {
                return profile.deviceName === interfaceName;
            });
        } else {
            profiles = target.profiles || [];
        }
        if (profiles.length === 0)
            return null;

        const activeUuid = root.runtimeMatchesActive ? String(NetworkService.runtimeDetails.connectionUuid
                                                              || "") : "";
        const activeProfile = profiles.find(profile => {
            return activeUuid.length > 0 && profile.uuid === activeUuid;
        }) || null;
        if (activeProfile)
            return activeProfile;

        return profiles.length === 1 || !target.connected ? profiles[0] : null;
    }

    function wiredDeviceForProfile(profile) {
        if (!profile)
            return null;

        return NetworkService.wiredDevices.find(device => {
            return device.deviceName === profile.deviceName;
        }) || null;
    }

    function refreshRuntimeDetails() {
        if (root.activeNetwork && String(root.activeNetwork.deviceName || "").length > 0)
            NetworkService.requestRuntimeDetails(root.activeNetwork);
        else
            NetworkService.releaseRuntimeDetails();
    }

    function openProfile(target) {
        const profile = root.profileForTarget(target);
        if (profile)
            configWindow.openProfile(profile, "");
    }

    function closeChildWindows() {
        configWindow.dismiss();
    }

    onActiveConnectionKeyChanged: root.refreshRuntimeDetails()
    onNearbyNetworksChanged: {
        if (root.nearbyNetworks.length > 0)
            root.finishInitialLoad();
    }
    Component.onCompleted: {
        NetworkService.acquireScan("control-center-network");
        root.refreshRuntimeDetails();
        Qt.callLater(root.beginInitialLoad);
    }
    Component.onDestruction: {
        nearbyPassword.text = "";
        root.passwordTarget = null;
        initialLoadTimer.stop();
        NetworkService.releaseRuntimeDetails();
        NetworkService.releaseScan("control-center-network");
    }

    // Nearby network row — a connected-card list row with two trailing
    // glyphs (saved bookmark, secure lock); no atom carries that shape.
    component WifiListRow: ConnectedRect {
        id: wifiListRow

        required property var modelData
        required property int index

        width: ListView.view.width
        height: nearbyViewport.rowHeight
        first: wifiListRow.index === 0
        last: wifiListRow.index === root.nearbyNetworks.length - 1

        StateLayer {
            anchors.fill: parent
            layerRadius: (wifiListRow.first || wifiListRow.last) ? NexusStyle.rounding.extraLarge :
                                                                   NexusStyle.rounding.extraSmall
            color: Appearance.m3colors.m3onSurface
            hovered: rowPress.containsMouse
            pressed: rowPress.pressed
        }

        MouseArea {
            id: rowPress

            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (wifiListRow.modelData.isSecure && !wifiListRow.modelData.known)
                    root.passwordTarget = wifiListRow.modelData;
                else
                    NetworkService.connectToWifiNetwork(wifiListRow.modelData);
            }
        }

        RowLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            MaterialSymbol {
                text: wifiListRow.modelData.strength >= 70 ? "signal_wifi_4_bar" :
                                                             wifiListRow.modelData.strength >= 35
                                                             ? "network_wifi_2_bar" : "network_wifi_1_bar"
                iconSize: NexusStyle.icon.medium
                fill: 1
                color: Appearance.m3colors.m3onSurfaceVariant
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                StyledText {
                    Layout.fillWidth: true
                    text: wifiListRow.modelData.ssid
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    elide: Text.ElideRight
                }

                StyledText {
                    Layout.fillWidth: true
                    text: root.nearbyWifiDetails(wifiListRow.modelData)
                    color: Appearance.m3colors.m3outline
                    font.pixelSize: NexusStyle.font.labelSmall
                    elide: Text.ElideRight
                }
            }

            MaterialSymbol {
                visible: wifiListRow.modelData.known
                text: "bookmark"
                iconSize: NexusStyle.icon.small
                fill: 1
                color: Appearance.m3colors.m3onSurfaceVariant
            }

            MaterialSymbol {
                visible: wifiListRow.modelData.isSecure
                text: "lock"
                iconSize: NexusStyle.icon.small
                fill: 1
                color: Appearance.m3colors.m3onSurfaceVariant
            }
        }
    }

    // The scaffold takes a single content child; the column, the scan lease
    // timer and the config window all ride inside it (2026-10-25 lesson:
    // extra root children kill the whole page).
    Item {
        id: content

        width: parent.width
        implicitHeight: contentColumn.implicitHeight

        Connections {
            function onOperationSucceeded(operation) {
                if (operation === "connect" || operation === "disconnect")
                    root.refreshRuntimeDetails();
            }

            function onProfileWriteSucceeded(uuid) {
                root.refreshRuntimeDetails();
            }

            function onWifiEnabledChanged() {
                if (!NetworkService.wifiEnabled) {
                    root.finishInitialLoad();
                    root.initialLoadAttempted = false;
                    nearbyPassword.text = "";
                    root.passwordTarget = null;
                } else {
                    Qt.callLater(root.beginInitialLoad);
                }
            }

            target: NetworkService
        }

        Timer {
            id: initialLoadTimer

            interval: 4000
            repeat: false
            onTriggered: root.initialLoading = false
        }

        ColumnLayout {
            id: contentColumn

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            width: root.cappedWidth
            spacing: NexusStyle.padding.extraSmall / 2

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: !NetworkService.available || NetworkService.lastError.length > 0
                tone: "error"
                message: NetworkService.lastError.length > 0 ? NetworkService.lastError : I18n.tr(
                                                                   "Network service unavailable")
            }

            // Wired connections
            PreferenceHeader {
                id: wiredHeader

                visible: NetworkService.wiredDevices.length > 0
                text: I18n.tr("Wired connections")

                SettingsSearchAnchor {
                    id: searchAnchor0
                    target: wiredHeader
                    declaration:
                        '{"id":"network.section.wired-connections","route":"network","title":"Wired connections","context":"NetworkPage","icon":"wifi","aliases":["general.network.section.wired-connections"]}'
                }
            }

            Repeater {
                id: wiredList

                model: NetworkService.wiredProfiles

                delegate: PreferenceAction {
                    id: wiredRow

                    required property var modelData
                    required property int index

                    readonly property var device: root.wiredDeviceForProfile(wiredRow.modelData)
                    readonly property string detailText: {
                        const details = [];
                        const interfaceName = String(wiredRow.modelData.deviceName || "");
                        if (interfaceName.length > 0)
                            details.push(interfaceName);

                        if (!wiredRow.device)
                            return details.join(" · ");

                        if (!wiredRow.device.hasLink) {
                            details.push(I18n.tr("Network cable unplugged"));
                            return details.join(" · ");
                        }
                        if (wiredRow.device.connected && wiredRow.device.linkSpeed > 0)
                            details.push(I18n.tr("%1 Mbps").arg(wiredRow.device.linkSpeed));

                        if (wiredRow.device.connected && root.activeNetwork && root.activeNetwork.type
                                === "wired" && root.activeNetwork.deviceName === wiredRow.device.deviceName) {
                            const exception = root.connectivityException();
                            if (exception.length > 0)
                                details.push(exception);
                        }
                        return details.join(" · ");
                    }

                    first: wiredRow.index === 0
                    last: wiredRow.index === wiredList.count - 1 && unconfiguredWiredList.count === 0
                    icon: wiredRow.device && wiredRow.device.connected ? "link" : "link_off"
                    text: wiredRow.modelData.name || wiredRow.modelData.deviceName || I18n.tr("Wired network")
                    subtext: wiredRow.detailText
                    onClicked: configWindow.openProfile(wiredRow.modelData, "")
                }
            }

            Repeater {
                id: unconfiguredWiredList

                model: NetworkService.wiredDevices.filter(device => {
                    return !NetworkService.wiredProfiles.some(profile => {
                        return profile.deviceName === device.deviceName;
                    });
                })

                delegate: PreferenceInfo {
                    id: unconfiguredWiredRow

                    required property var modelData
                    required property int index

                    first: wiredList.count === 0 && unconfiguredWiredRow.index === 0
                    last: unconfiguredWiredRow.index === unconfiguredWiredList.count - 1
                    icon: unconfiguredWiredRow.modelData.connected ? "link" : "link_off"
                    label: unconfiguredWiredRow.modelData.name || I18n.tr("Wired network")
                    subtext: unconfiguredWiredRow.modelData.hasLink ? I18n.tr("No editable connection") :
                                                                      I18n.tr("Network cable unplugged")
                }
            }

            // Wi-Fi
            PreferenceHeader {
                id: wifiHeader

                text: I18n.tr("Wi-Fi")

                SettingsSearchAnchor {
                    id: searchAnchor1
                    target: wifiHeader
                    declaration:
                        '{"id":"network.section.wi-fi","route":"network","title":"Wi-Fi","context":"NetworkPage","icon":"wifi","aliases":["general.network.section.wi-fi"]}'
                }
            }

            PreferenceToggle {
                id: wifiToggle

                first: true
                last: true
                text: I18n.tr("Wi-Fi")
                subtext: !NetworkService.available ? "" : !NetworkService.wifiAvailable ? I18n.tr(
                                                                                              "No wireless adapter detected") :
                                                                                          !NetworkService.wifiHardwareEnabled
                                                                                          ? I18n.tr(
                                                                                                "Disabled by a hardware switch or rfkill") :
                                                                                            ""
                checked: NetworkService.wifiEnabled
                enabled: NetworkService.available && NetworkService.wifiAvailable
                         && NetworkService.wifiHardwareEnabled && !NetworkService.busy
                onToggled: NetworkService.setWifiEnabled(checked)
            }

            Item {
                id: wifiExpandedRegion

                Layout.fillWidth: true
                Layout.preferredHeight: NetworkService.wifiEnabled ? expandedWifiContent.implicitHeight : 0
                opacity: NetworkService.wifiEnabled ? 1 : 0
                clip: true

                ColumnLayout {
                    id: expandedWifiContent

                    width: parent.width
                    spacing: NexusStyle.padding.small

                    PreferenceAction {
                        Layout.topMargin: NexusStyle.padding.extraSmall / 2
                        visible: NetworkService.activeWifi !== null
                        icon: "wifi"
                        text: NetworkService.activeWifi ? NetworkService.activeWifi.ssid : ""
                        subtext: root.activeWifiDetails()
                        enabled: root.profileForTarget(NetworkService.activeWifi) !== null
                        trailingIcon: root.profileForTarget(NetworkService.activeWifi) !== null ? "settings" :
                                                                                                  ""
                        onClicked: root.openProfile(NetworkService.activeWifi)
                    }

                    StyledText {
                        Layout.fillWidth: true
                        Layout.topMargin: NexusStyle.padding.extraSmall
                        Layout.leftMargin: NexusStyle.padding.extraSmall
                        text: I18n.tr("Nearby networks")
                        color: Appearance.m3colors.m3onSurfaceVariant
                        font.pixelSize: NexusStyle.font.labelMedium
                        font.weight: NexusStyle.font.labelMediumWeight
                        elide: Text.ElideRight
                    }

                    Item {
                        id: nearbyViewport

                        readonly property real rowHeight: NexusStyle.padding.medium * 2
                                                          + NexusStyle.font.bodyMedium
                                                          + NexusStyle.font.labelSmall
                                                          + NexusStyle.padding.extraSmall
                        readonly property real rowSpacing: NexusStyle.padding.extraSmall / 2
                        readonly property real viewportHeight: rowHeight * 5 + rowSpacing * 4

                        Layout.fillWidth: true
                        Layout.preferredHeight: viewportHeight
                        clip: true

                        StyledListView {
                            id: nearbyList

                            anchors.fill: parent
                            visible: !root.initialLoading && count > 0
                            opacity: visible ? 1 : 0
                            model: root.nearbyNetworks
                            spacing: nearbyViewport.rowSpacing
                            boundsBehavior: Flickable.StopAtBounds
                            fasterTouchpadScroll: true
                            showVerticalScrollBar: true
                            animateMovement: true

                            delegate: WifiListRow {}

                            Behavior on opacity {
                                ElementMoveAnimation {}
                            }
                        }

                        Column {
                            anchors.centerIn: parent
                            visible: root.initialLoading
                            opacity: visible ? 1 : 0
                            spacing: NexusStyle.padding.small

                            MaterialLoadingIndicator {
                                anchors.horizontalCenter: parent.horizontalCenter
                                running: root.initialLoading
                                accessibleName: I18n.tr("Searching for nearby networks")
                            }

                            StyledText {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: I18n.tr("Searching for nearby networks")
                                color: Appearance.m3colors.m3onSurface
                                font.pixelSize: NexusStyle.font.bodyMedium
                            }

                            Behavior on opacity {
                                ElementMoveAnimation {}
                            }
                        }

                        Column {
                            anchors.centerIn: parent
                            visible: !root.initialLoading && root.nearbyNetworks.length === 0
                            spacing: NexusStyle.padding.small

                            MaterialSymbol {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "search_off"
                                iconSize: NexusStyle.icon.medium
                                fill: 1
                                color: Appearance.m3colors.m3onSurfaceVariant
                            }

                            StyledText {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: I18n.tr("No nearby networks found")
                                color: Appearance.m3colors.m3onSurfaceVariant
                                font.pixelSize: NexusStyle.font.bodyMedium
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root.passwordTarget !== null
                        spacing: NexusStyle.padding.extraSmall

                        OutlinedTextField {
                            id: nearbyPassword

                            Layout.fillWidth: true
                            labelText: root.passwordTarget ? I18n.tr("Password for %1").arg(
                                                                 root.passwordTarget.ssid) : I18n.tr(
                                                                 "Password")
                            passwordToggle: true
                            errorText: text.length > 0 && text.length < 8 ? I18n.tr(
                                                                                "Password must be at least 8 characters") :
                                                                            ""
                        }

                        RowLayout {
                            Layout.fillWidth: true

                            Item {
                                Layout.fillWidth: true
                            }

                            ActionButton {
                                text: I18n.tr("Cancel")
                                onClicked: {
                                    nearbyPassword.text = "";
                                    root.passwordTarget = null;
                                }
                            }

                            ActionButton {
                                text: I18n.tr("Connect")
                                filled: true
                                enabled: nearbyPassword.text.length >= 8 && !NetworkService.busy
                                onClicked: {
                                    NetworkService.changePassword(root.passwordTarget, nearbyPassword.text);
                                    nearbyPassword.text = "";
                                    root.passwordTarget = null;
                                }
                            }
                        }
                    }
                }

                Behavior on opacity {
                    ElementMoveAnimation {}
                }
            }

            // Other settings
            PreferenceHeader {
                text: I18n.tr("Other settings")
            }

            PreferenceAction {
                id: savedNetworksRow

                first: true
                icon: "bookmark"
                text: I18n.tr("Saved networks")
                onClicked: configWindow.openSavedNetworks()

                SettingsSearchAnchor {
                    id: searchAnchor2
                    target: savedNetworksRow
                    declaration:
                        '{"id":"network.section.other-settings","route":"network","title":"Other settings","context":"NetworkPage","icon":"wifi","aliases":["general.network.section.other-settings"]}'
                }
            }

            PreferenceAction {
                last: true
                icon: "add"
                text: I18n.tr("Add network")
                onClicked: configWindow.openAddNetwork()
            }

            // Connection information
            PreferenceHeader {
                text: I18n.tr("Connection information")
            }

            InlineStatusBanner {
                Layout.fillWidth: true
                visible: NetworkService.runtimeDetailsError.length > 0
                tone: "error"
                message: NetworkService.runtimeDetailsError
            }

            PreferenceInfo {
                id: interfaceRow

                first: true
                label: I18n.tr("Interface")
                subtext: root.activeNetwork ? root.activeNetwork.deviceName : "—"

                SettingsSearchAnchor {
                    id: searchAnchor3
                    target: interfaceRow
                    declaration:
                        '{"id":"network.section.connection-information","route":"network","title":"Connection information","context":"NetworkPage","icon":"wifi","aliases":["general.network.section.connection-information"]}'
                }
            }

            PreferenceInfo {
                label: I18n.tr("IP address")
                subtext: root.runtimeMatchesActive && NetworkService.runtimeDetails.addresses
                         ? NetworkService.runtimeDetails.addresses.join(", ") : "—"
            }

            PreferenceInfo {
                label: I18n.tr("Gateway")
                subtext: root.runtimeMatchesActive ? NetworkService.runtimeDetails.gateway || "—" : "—"
            }

            PreferenceInfo {
                label: I18n.tr("DNS")
                subtext: root.runtimeMatchesActive && NetworkService.runtimeDetails.dns
                         ? NetworkService.runtimeDetails.dns.join(", ") : "—"
            }

            PreferenceInfo {
                label: I18n.tr("MAC")
                subtext: root.activeNetwork ? root.activeNetwork.address || "—" : "—"
            }

            PreferenceInfo {
                visible: root.activeNetwork !== null && root.activeNetwork.type === "wifi"
                label: I18n.tr("Security type")
                subtext: root.activeNetwork ? root.activeNetwork.security || I18n.tr("Unknown") : "—"
            }

            PreferenceInfo {
                visible: root.activeNetwork !== null && root.activeNetwork.type === "wifi"
                label: I18n.tr("Frequency")
                subtext: root.runtimeMatchesActive ? NetworkService.runtimeDetails.frequency || "—" : "—"
            }

            PreferenceInfo {
                last: true
                visible: root.activeNetwork !== null && root.activeNetwork.type === "wired"
                label: I18n.tr("Link speed")
                subtext: root.activeNetwork && root.activeNetwork.linkSpeed > 0 ? I18n.tr("%1 Mbps").arg(
                                                                                      root.activeNetwork.linkSpeed) :
                                                                                  "—"
            }
        }

        NetworkConfigWindow {
            id: configWindow

            parentModal: root.parentModal
        }
    }
}

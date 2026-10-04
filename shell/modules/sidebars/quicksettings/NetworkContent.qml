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
    readonly property bool isActive: root.foreground && WidgetState.quickSettingsView === "network"
    property bool scanLeaseAcquired: false
    property bool initialLoadAttempted: false
    property bool initialLoading: false
    property bool refreshLoading: false
    property var pendingForgetNetwork: null
    readonly property bool networkUsable: NetworkService.available && NetworkService.wifiAvailable
                                          && NetworkService.wifiEnabled
    readonly property var savedWifiProfiles: NetworkService.savedWifiProfiles
    readonly property var availableWifiNetworks: NetworkService.availableWifiNetworks
    readonly property bool linearLoading: NetworkService.busy && !refreshLoading
    readonly property string stateMessage: {
        if (NetworkService.lastError.length > 0)
            return NetworkService.lastError;

        if (!NetworkService.available)
            return I18n.tr("NetworkManager is currently unavailable");

        if (!NetworkService.wifiAvailable)
            return I18n.tr("No Wi-Fi device detected");

        if (!NetworkService.wifiHardwareEnabled)
            return I18n.tr("Wi-Fi is blocked by a hardware switch or rfkill");

        if (!NetworkService.wifiEnabled)
            return I18n.tr("Wi-Fi is off");

        return "";
    }

    function beginInitialLoad() {
        if (!root.isActive || !root.networkUsable || root.initialLoadAttempted)
            return;

        initialLoadTimer.stop();
        root.initialLoadAttempted = true;
        initialLoading = NetworkService.availableWifiNetworks.length === 0;
        if (initialLoading)
            initialLoadTimer.restart();
    }

    function finishTransientLoading() {
        initialLoading = false;
        refreshLoading = false;
        initialLoadTimer.stop();
        refreshTimer.stop();
    }

    function updateScanLease() {
        if (isActive && !scanLeaseAcquired) {
            NetworkService.acquireScan("right-sidebar-network");
            scanLeaseAcquired = true;
            Qt.callLater(root.beginInitialLoad);
        } else if (!isActive && scanLeaseAcquired) {
            NetworkService.releaseScan("right-sidebar-network");
            scanLeaseAcquired = false;
            finishTransientLoading();
            NetworkService.cancelPasswordRequest(null);
        }
    }

    function requestRefresh() {
        if (!root.networkUsable || root.refreshLoading)
            return;

        initialLoading = false;
        initialLoadTimer.stop();
        refreshLoading = true;
        refreshTimer.restart();
        NetworkService.requestScan();
    }

    function connectivityText() {
        if (NetworkService.captivePortal)
            return I18n.tr("Network sign-in required");

        if (NetworkService.limitedConnectivity)
            return I18n.tr("Network connectivity is limited");

        if (NetworkService.internetAvailable)
            return I18n.tr("Internet is available");

        if (NetworkService.connected)
            return I18n.tr("Connected; internet access could not be confirmed");

        return I18n.tr("No active connection");
    }

    function savedProfileDetails(profile) {
        const details = [];
        const profileName = String(profile.name || "");
        const ssid = String(profile.ssid || "");
        if (profileName.length > 0 && profileName !== ssid)
            details.push(ssid);

        if (profile.ipv4Method === "manual")
            details.push(I18n.tr("Manual IPv4"));
        else if (profile.customDns)
            details.push(I18n.tr("DHCP + custom DNS"));
        else
            details.push(I18n.tr("Automatic (DHCP)"));
        if (profile.autoconnect)
            details.push(I18n.tr("Connect automatically"));

        return details.join(" · ");
    }

    function forgetTargetLabel(target) {
        if (!target)
            return "";

        const name = String(target.name || target.ssid || "");
        if (!target.uuid)
            return name;

        const details = root.savedProfileDetails(target);
        return details.length > 0 ? name + " · " + details : name;
    }

    title: I18n.tr("Network")
    icon: "wifi"
    showBackButton: true
    backAction: () => {
        return WidgetState.quickSettingsView = "settings";
    }
    onIsActiveChanged: updateScanLease()
    onAvailableWifiNetworksChanged: {
        if (NetworkService.availableWifiNetworks.length > 0)
            root.finishTransientLoading();
    }
    Component.onCompleted: updateScanLease()
    Component.onDestruction: {
        if (scanLeaseAcquired)
            NetworkService.releaseScan("right-sidebar-network");

        NetworkService.cancelPasswordRequest(null);
    }

    Connections {
        function onWifiEnabledChanged() {
            if (!NetworkService.wifiEnabled)
                root.finishTransientLoading();
            else if (root.isActive)
                Qt.callLater(root.beginInitialLoad);
        }

        function onOperationFailed(operation, message) {
            if (operation === "scan") {
                root.refreshLoading = false;
                refreshTimer.stop();
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

    Timer {
        id: refreshTimer

        interval: 4000
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
            refreshEnabled: root.isActive && root.networkUsable && !NetworkService.busy
            refreshing: root.refreshLoading
            onRefreshRequested: root.requestRefresh()

            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: networkContent.implicitHeight + sidebarScroll.contentTopInset

            ColumnLayout {
                id: networkContent
                y: sidebarScroll.contentTopInset

                width: parent.width
                spacing: Metrics.spacingL
                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(0, 1)
                    Layout.fillWidth: true

                    SettingsRow {
                        Layout.fillWidth: true
                        iconName: NetworkService.activeNetwork && NetworkService.activeNetwork.type
                                  === "wired" ? "lan" : NetworkService.wifiConnected ? "wifi" : "wifi_off"
                        title: NetworkService.activeNetwork ? NetworkService.activeConnection : I18n.tr(
                                                                  "Not connected")
                        supportingText: root.connectivityText()
                        highlighted: NetworkService.connected

                        trailing: RowLayout {
                            spacing: Appearance.spacing.xSmall

                            Text {
                                visible: NetworkService.wifiConnected
                                text: NetworkService.signalStrength + "%"
                                color: Appearance.colors.colOnLayer1
                                font.family: Fonts.numeric
                                font.pixelSize: 12
                            }

                            MaterialSymbol {
                                text: NetworkService.internetAvailable ? "language" :
                                                                         NetworkService.captivePortal
                                                                         ? "captive_portal" : "public_off"
                                iconSize: 19
                                color: NetworkService.internetAvailable ? Appearance.colors.colPrimary :
                                                                          Appearance.colors.colOnLayer1
                            }
                        }
                    }

                    ActionButton {
                        Layout.fillWidth: true
                        visible: NetworkService.captivePortal
                        text: I18n.tr("Open network portal")
                        filled: true
                        onClicked: {
                            WidgetState.closeAllPopups();
                            NetworkService.openPublicWifiPortal();
                        }
                    }
                }
                InlineStatusBanner {
                    Layout.topMargin: sidebarScroll.gapFor(1, 1)
                    Layout.fillWidth: true
                    visible: root.stateMessage.length > 0
                    tone: NetworkService.lastError.length > 0 ? "error" : "info"
                    message: root.stateMessage
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(2, 1)

                    Layout.fillWidth: true
                    visible: NetworkService.wiredDevices.length > 0
                    title: I18n.tr("Wired connections")
                    iconName: "lan"

                    Repeater {
                        model: wiredPages.items

                        SettingsRow {
                            required property var modelData
                            required property int index
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.16)

                            Layout.fillWidth: true
                            title: modelData.name
                            iconName: "lan"
                            highlighted: modelData.connected
                            supportingText: !modelData.hasLink ? I18n.tr("Network cable unplugged") :
                                                                 modelData.linkSpeed > 0 ? I18n.tr(
                                                                                               "%1 Mbps").arg(
                                                                                               modelData.linkSpeed) :
                                                                                           ""
                            trailing: ActionButton {
                                text: modelData.connected ? I18n.tr("Disconnect") : I18n.tr("Connect")
                                enabled: modelData.hasLink && !NetworkService.busy
                                onClicked: {
                                    if (modelData.connected)
                                        NetworkService.disconnectNetwork(modelData);
                                    else
                                        NetworkService.connectNetwork(modelData);
                                }
                            }
                        }
                    }
                    ListPagination {
                        id: wiredPages
                        model: NetworkService.wiredDevices
                    }
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(3, 1)

                    Layout.fillWidth: true
                    visible: NetworkService.activeWifi !== null
                    title: I18n.tr("Connection details")
                    iconName: "wifi"

                    SettingsRow {
                        Layout.fillWidth: true
                        title: I18n.tr("Signal strength")
                        supportingText: I18n.tr("%1%").arg(NetworkService.signalStrength)
                    }
                    SettingsRow {
                        Layout.fillWidth: true
                        title: I18n.tr("Security")
                        supportingText: NetworkService.activeWifi && NetworkService.activeWifi.isSecure
                                        ? I18n.tr("Protected network") : I18n.tr("Open network")
                    }
                    SettingsRow {
                        Layout.fillWidth: true
                        title: I18n.tr("Network adapter")
                        supportingText: NetworkService.activeWifi ? NetworkService.activeWifi.deviceName : ""
                    }
                    ActionButton {
                        text: I18n.tr("Disconnect")
                        enabled: !NetworkService.busy
                        onClicked: NetworkService.disconnectWifiNetwork()
                    }
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(4, 1)

                    Layout.fillWidth: true
                    visible: root.networkUsable && root.savedWifiProfiles.length > 0
                    title: I18n.tr("Saved networks")

                    Repeater {
                        model: savedPages.items

                        SavedWifiProfileItem {
                            required property var modelData
                            required property int index
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.16)

                            Layout.fillWidth: true
                            profile: modelData
                        }
                    }
                    ListPagination {
                        id: savedPages
                        model: root.savedWifiProfiles
                    }
                }

                SettingsSection {
                    pullExpansion: sidebarScroll.detailExpansion
                    Layout.topMargin: sidebarScroll.gapFor(5, 1)

                    Layout.fillWidth: true
                    title: I18n.tr("Available networks")
                    visible: root.networkUsable
                    supportingText: I18n.tr("%n network(s)", NetworkService.availableWifiNetworks.length)

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.initialLoading ? 116 : 0
                        visible: root.initialLoading
                        opacity: root.initialLoading ? 1 : 0
                        clip: true

                        Column {
                            anchors.centerIn: parent
                            spacing: Metrics.spacingL

                            MaterialLoadingIndicator {
                                anchors.horizontalCenter: parent.horizontalCenter
                                running: root.initialLoading
                                accessibleName: I18n.tr("Searching for available networks")
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: I18n.tr("Searching for available networks")
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
                        WifiNetworkItem {
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            Layout.topMargin: sidebarScroll.gapFor(index, 0.18)
                            wifiNetwork: modelData
                        }
                    }
                    ListPagination {
                        id: availablePages
                        model: NetworkService.availableWifiNetworks
                    }

                    SettingsRow {
                        Layout.fillWidth: true
                        visible: !root.initialLoading && !root.refreshLoading
                                 && NetworkService.availableWifiNetworks.length === 0
                        iconName: "search_off"
                        title: I18n.tr("No available networks found")
                    }
                }

                Item {
                    Layout.topMargin: sidebarScroll.gapFor(6, 1)

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
        dialogTitle: I18n.tr("Forget network")
        messageText: root.pendingForgetNetwork ? I18n.tr(
                                                     "This will delete the saved connection for “%1”.").arg(
                                                     root.forgetTargetLabel(root.pendingForgetNetwork)) : ""

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
                        root.pendingForgetNetwork = null;
                    }
                }

                ActionButton {
                    text: I18n.tr("Forget")
                    onClicked: {
                        const target = root.pendingForgetNetwork;
                        forgetDialog.close();
                        root.pendingForgetNetwork = null;
                        if (target) {
                            if (target.uuid && target.nativeSettings)
                                NetworkService.forgetProfile(target);
                            else
                                NetworkService.forgetNetwork(target);
                        }
                    }
                }
            }
        }
    }

    headerTools: RowLayout {
        spacing: Appearance.spacing.xSmall

        IconButton {
            enabled: root.networkUsable && !root.refreshLoading
            iconName: "refresh"
            iconSize: 21
            iconColor: Appearance.colors.colOnLayer2
            accessibleName: I18n.tr("Refresh network list")
            hoverStateLayerColor: Appearance.colors.colLayer2Hover
            pressedStateLayerColor: Appearance.colors.colLayer2Active
            onClicked: root.requestRefresh()
        }

        StyledSwitch {
            scale: 0.8
            checked: NetworkService.wifiEnabled
            enabled: NetworkService.available && NetworkService.wifiAvailable
                     && NetworkService.wifiHardwareEnabled && !NetworkService.busy
            Accessible.name: I18n.tr("Wi-Fi switch")
            onToggled: NetworkService.setWifiEnabled(checked)
        }
    }

    component SavedWifiProfileItem: Rectangle {
        id: profileRoot

        required property var profile
        readonly property bool targetBusy: NetworkService.connectTargetUuid.length > 0
                                           && NetworkService.connectTargetUuid === String(profile.uuid || "")

        implicitHeight: 64
        radius: Appearance.rounding.normal
        color: "transparent"

        SettingsRow {
            anchors.fill: parent
            iconName: profile.strength > 75 ? "signal_wifi_4_bar" : profile.strength > 50
                                              ? "network_wifi_3_bar" : profile.strength > 25
                                                ? "network_wifi_2_bar" : "signal_wifi_0_bar"
            title: profile.name || profile.ssid
            supportingText: root.savedProfileDetails(profile)
            interactive: !NetworkService.busy
            onClicked: NetworkService.connectProfile(profileRoot.profile)

            trailing: RowLayout {
                spacing: Appearance.spacing.xSmall

                MaterialSymbol {
                    visible: profileRoot.targetBusy
                    text: "progress_activity"
                    iconSize: 19
                    color: Appearance.colors.colPrimary

                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: 850
                        loops: Animation.Infinite
                        running: profileRoot.targetBusy
                    }
                }

                IconButton {
                    controlSize: 36
                    enabled: !NetworkService.busy
                    iconName: "more_vert"
                    iconSize: 19
                    iconColor: Appearance.colors.colOnLayer2
                    accessibleName: I18n.tr("Network action")
                    hoverStateLayerColor: Appearance.colors.colLayer3Hover
                    pressedStateLayerColor: Appearance.colors.colLayer3Active
                    onClicked: profileMenu.open()

                    StyledMenu {
                        id: profileMenu

                        StyledMenuItem {
                            iconName: "delete"
                            destructive: true
                            text: I18n.tr("Forget network")
                            onTriggered: {
                                root.pendingForgetNetwork = profileRoot.profile;
                                forgetDialog.open();
                            }
                        }
                    }
                }
            }
        }
    }

    component WifiNetworkItem: Rectangle {
        id: itemRoot

        required property var wifiNetwork
        property bool showPassword: false
        readonly property bool networkActive: !!wifiNetwork.active
        readonly property bool networkSecure: !!wifiNetwork.isSecure
        readonly property bool networkKnown: !!wifiNetwork.known
        readonly property bool networkAskingPassword: !!wifiNetwork.askingPassword
        readonly property bool targetBusy: NetworkService.wifiConnectTarget
                                           && NetworkService.wifiConnectTarget.ssid === wifiNetwork.ssid
        readonly property real promptHeight: networkAskingPassword ? passwordContent.implicitHeight
                                                                     + Appearance.spacing.medium : 0

        function submitPassword() {
            const password = passwordField.text;
            if (password.length === 0)
                return;

            passwordField.text = "";
            passwordField.focus = false;
            showPassword = false;
            NetworkService.changePassword(wifiNetwork, password);
        }

        implicitHeight: 64 + promptHeight
        height: implicitHeight
        radius: Appearance.rounding.normal
        clip: true
        color: networkActive || networkAskingPassword ? Appearance.colors.colLayer2 : "transparent"
        onNetworkAskingPasswordChanged: {
            if (!networkAskingPassword) {
                passwordField.text = "";
                passwordField.focus = false;
                showPassword = false;
            }
        }

        SettingsRow {
            height: 64
            iconName: wifiNetwork.strength > 75 ? "signal_wifi_4_bar" : wifiNetwork.strength > 50
                                                  ? "network_wifi_3_bar" : wifiNetwork.strength > 25
                                                    ? "network_wifi_2_bar" : "signal_wifi_0_bar"
            title: wifiNetwork.ssid
            supportingText: networkActive ? I18n.tr("Connected · ") + wifiNetwork.strength + "%" : (
                                                networkKnown ? I18n.tr("Saved · ") : "") + (networkSecure
                                                                                            ? wifiNetwork.security :
                                                                                              I18n.tr("Open network"))
                                            + " · " + wifiNetwork.strength + "%"
            interactive: !NetworkService.busy && !networkAskingPassword
            highlighted: networkActive
            onClicked: NetworkService.connectToWifiNetwork(itemRoot.wifiNetwork)

            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
            }

            trailing: RowLayout {
                spacing: Appearance.spacing.xSmall

                MaterialSymbol {
                    visible: itemRoot.networkSecure && !itemRoot.networkActive
                    text: "lock"
                    iconSize: 18
                    color: Appearance.colors.colOnLayer1
                }

                MaterialSymbol {
                    visible: itemRoot.targetBusy
                    text: "progress_activity"
                    iconSize: 19
                    color: Appearance.colors.colPrimary

                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: 850
                        loops: Animation.Infinite
                        running: itemRoot.targetBusy
                    }
                }

                IconButton {
                    visible: itemRoot.networkKnown
                    controlSize: 36
                    enabled: !NetworkService.busy
                    iconName: "more_vert"
                    iconSize: 19
                    iconColor: Appearance.colors.colOnLayer2
                    accessibleName: I18n.tr("Network action")
                    hoverStateLayerColor: Appearance.colors.colLayer3Hover
                    pressedStateLayerColor: Appearance.colors.colLayer3Active
                    onClicked: networkMenu.open()

                    StyledMenu {
                        id: networkMenu

                        StyledMenuItem {
                            visible: itemRoot.networkActive
                            iconName: "link_off"
                            text: I18n.tr("Disconnect")
                            onTriggered: NetworkService.disconnectNetwork(itemRoot.wifiNetwork)
                        }

                        StyledMenuItem {
                            iconName: "delete"
                            destructive: true
                            text: I18n.tr("Forget network")
                            onTriggered: {
                                root.pendingForgetNetwork = itemRoot.wifiNetwork;
                                forgetDialog.open();
                            }
                        }
                    }
                }
            }
        }

        Item {
            height: itemRoot.promptHeight
            opacity: itemRoot.networkAskingPassword ? 1 : 0
            clip: true

            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                topMargin: 64
            }

            ColumnLayout {
                id: passwordContent

                spacing: Metrics.spacingL

                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    leftMargin: Appearance.spacing.medium
                    rightMargin: Appearance.spacing.medium
                    topMargin: Appearance.spacing.small
                }

                MaterialTextField {
                    id: passwordField

                    Layout.fillWidth: true
                    placeholderText: I18n.tr("Network password")
                    echoMode: itemRoot.showPassword ? TextInput.Normal : TextInput.Password
                    inputMethodHints: Qt.ImhSensitiveData
                    enabled: !NetworkService.busy
                    onAccepted: itemRoot.submitPassword()

                    trailingContent: Component {
                        IconButton {
                            anchors.fill: parent
                            enabled: !NetworkService.busy
                            iconName: itemRoot.showPassword ? "visibility_off" : "visibility"
                            iconSize: 20
                            iconColor: Appearance.colors.colOnLayer1
                            accessibleName: itemRoot.showPassword ? I18n.tr("Hide password") : I18n.tr(
                                                                        "Show password")
                            hoverStateLayerColor: Appearance.colors.colLayer1Hover
                            pressedStateLayerColor: Appearance.colors.colLayer1Active
                            onClicked: itemRoot.showPassword = !itemRoot.showPassword
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Metrics.spacingL

                    Item {
                        Layout.fillWidth: true
                    }

                    ActionButton {
                        text: I18n.tr("Cancel")
                        onClicked: NetworkService.cancelPasswordRequest(itemRoot.wifiNetwork)
                    }

                    ActionButton {
                        text: I18n.tr("Connect")
                        filled: true
                        onClicked: itemRoot.submitPassword()
                    }
                }
            }

            Behavior on height {
                ElementMoveAnimation {}
            }

            Behavior on opacity {
                ElementMoveAnimation {}
            }
        }

        Behavior on height {
            ElementMoveAnimation {}
        }

        Behavior on color {
            ColorAnimation {
                duration: Appearance.animation.expressiveFastEffects.duration
            }
        }
    }
}

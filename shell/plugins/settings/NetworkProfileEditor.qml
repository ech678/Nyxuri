pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Connection profile editor (T3 M4): atom rows inside the network config
// modal. Basic information rides the info atom, IPv4 method the toggle +
// select atoms; the manual address/gateway/DNS fields stay full-width
// labeled fields and the dirty-tracking/apply flow is untouched.
StyledFlickable {
    id: root

    property var target: null
    readonly property bool isWired: target && target.type === "wired"
    property bool profileRemoved: false
    readonly property var profile: {
        if (!target || profileRemoved)
            return null;

        if (target.nativeSettings) {
            const profiles = isWired ? NetworkService.wiredProfiles : NetworkService.savedWifiProfiles;
            return profiles.find(item => {
                return item.uuid === target.uuid;
            }) || null;
        }
        const currentNetwork = !isWired ? NetworkService.allWifiNetworks.find(item => {
            return item.deviceName === target.deviceName && item.ssid === target.ssid;
        }) : null;
        const currentProfiles = currentNetwork ? currentNetwork.profiles : target.profiles;
        if (currentProfiles && currentProfiles.length > 0)
            return currentProfiles[0];

        if (isWired) {
            const interfaceName = String(target.deviceName || target.name || "");
            for (const wiredProfile of NetworkService.wiredProfiles) {
                if (wiredProfile.deviceName === interfaceName)
                    return wiredProfile;
            }
        }
        return null;
    }
    readonly property var nativeNetwork: target && target.nativeNetwork ? target.nativeNetwork : profile
                                                                          ? profile.nativeNetwork : null
    readonly property bool connectionIsActive: !!(nativeNetwork && nativeNetwork.connected)
    readonly property var wiredDevice: isWired && profile ? NetworkService.wiredDevices.find(device => {
        return device.deviceName === profile.deviceName;
    }) || null : null
    property var original: null
    property string loadedProfileUuid: ""
    property string mode: "auto"
    property string address: ""
    property string gateway: ""
    property string dns: ""
    property bool autoconnect: true
    property bool addressTouched: false
    property bool gatewayTouched: false
    property bool dnsTouched: false
    property bool saving: false
    property string errorMessage: ""
    property string successMessage: ""
    readonly property bool dirty: original && (mode !== original.method || address.trim()
                                               !== original.address || gateway.trim() !== original.gateway
                                               || normalizeDns(dns) !== normalizeDns(original.dns)
                                               || autoconnect !== original.autoconnect)
    readonly property bool addressValid: mode !== "manual" || validCidr(address)
    readonly property bool gatewayValid: mode !== "manual" || gateway.trim() === "" || validIpv4(gateway.trim(
                                                                                                     ))

    readonly property bool dnsValid: mode === "auto" || (mode === "manual" && normalizeDns(dns).length === 0)
                                     || (normalizeDns(dns).length > 0 && normalizeDns(dns).split(",").every(
                                             value => {
                                                 return validIpv4(value);
                                             }))
    readonly property bool formValid: addressValid && gatewayValid && dnsValid

    signal profileForgotten

    function validIpv4(value) {
        const parts = String(value || "").split(".");
        if (parts.length !== 4)
            return false;

        return parts.every(part => {
            return /^\d{1,3}$/.test(part) && Number(part) >= 0 && Number(part) <= 255;
        });
    }

    function validCidr(value) {
        const pieces = String(value || "").trim().split("/");
        return pieces.length === 2 && validIpv4(pieces[0]) && /^\d{1,2}$/.test(pieces[1]) && Number(pieces[1])
                >= 0 && Number(pieces[1]) <= 32;
    }

    function normalizeDns(value) {
        return String(value || "").trim().split(/[\s,]+/).filter(item => {
            return item.length > 0;
        }).join(",");
    }

    function loadProfile() {
        root.addressTouched = false;
        root.gatewayTouched = false;
        root.dnsTouched = false;
        const snapshot = NetworkService.profileSnapshot(root.profile);
        if (!snapshot) {
            root.original = null;
            root.loadedProfileUuid = "";
            return;
        }
        root.loadedProfileUuid = String(root.profile.uuid || "");
        root.original = snapshot;
        root.mode = snapshot.method;
        root.address = snapshot.address;
        root.gateway = snapshot.gateway;
        root.dns = snapshot.dns;
        root.autoconnect = snapshot.autoconnect;
    }

    function resetEditor() {
        root.profileRemoved = false;
        root.saving = false;
        root.errorMessage = "";
        root.successMessage = "";
        root.loadProfile();
    }

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + NexusStyle.padding.large * 2
    Component.onCompleted: root.resetEditor()
    onTargetChanged: root.resetEditor()
    onProfileChanged: {
        const uuid = String(root.profile ? root.profile.uuid || "" : "");
        if (uuid === root.loadedProfileUuid)
            return;

        if (root.target && root.target.nativeSettings && uuid.length === 0 && root.loadedProfileUuid.length
                > 0) {
            root.profileRemoved = true;
            root.original = null;
            root.loadedProfileUuid = "";
            root.profileForgotten();
            return;
        }
        const discardedChanges = root.dirty;
        root.loadProfile();
        if (discardedChanges)
            root.errorMessage = I18n.tr(
                        "The active network profile changed; unapplied changes were discarded");
    }

    Connections {
        function onProfileWriteSucceeded(uuid) {
            if (!root.profile || uuid !== root.profile.uuid)
                return;

            root.saving = false;
            root.errorMessage = "";
            root.successMessage = root.nativeNetwork && root.nativeNetwork.connected ? I18n.tr(
                                                                                           "Profile saved; reconnect to fully apply the new IPv4 settings") :
                                                                                       I18n.tr("Profile saved");
            root.loadProfile();
        }

        function onProfileWriteFailed(uuid, message) {
            if (!root.profile || uuid !== root.profile.uuid)
                return;

            root.saving = false;
            root.successMessage = "";
            root.errorMessage = message;
        }

        function onProfileForgetSucceeded(uuid) {
            if (!root.target || uuid !== String(root.target.uuid || ""))
                return;

            root.profileRemoved = true;
            root.profileForgotten();
        }

        function onProfileForgetFailed(uuid, message) {
            if (!root.target || uuid !== String(root.target.uuid || ""))
                return;

            root.errorMessage = message;
        }

        target: NetworkService
    }

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - NexusStyle.padding.largeIncreased * 2))
        x: Math.max(NexusStyle.padding.largeIncreased, (root.width - width) / 2)
        y: NexusStyle.padding.largeIncreased
        spacing: NexusStyle.padding.extraSmall / 2

        RowLayout {
            Layout.fillWidth: true
            spacing: NexusStyle.padding.small

            ActionButton {
                visible: root.connectionIsActive
                text: I18n.tr("Disconnect")
                iconName: "link_off"
                enabled: !NetworkService.busy
                onClicked: NetworkService.disconnectNetwork(root.target)
            }

            ActionButton {
                visible: root.nativeNetwork && !root.connectionIsActive
                text: I18n.tr("Connect")
                iconName: "link"
                enabled: !NetworkService.busy && (!root.isWired || root.wiredDevice
                                                  && root.wiredDevice.hasLink)
                onClicked: {
                    if (root.profile)
                        NetworkService.connectProfile(root.profile);
                    else
                        NetworkService.connectNetwork(root.target, null);
                }
            }

            ActionButton {
                visible: root.profile !== null && !root.isWired
                text: I18n.tr("Forget")
                iconName: "delete"
                enabled: !NetworkService.busy && !root.saving
                onClicked: {
                    root.errorMessage = "";
                    NetworkService.forgetProfile(root.profile);
                }
            }

            Item {
                Layout.fillWidth: true
            }
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: root.errorMessage.length > 0
            tone: "error"
            message: root.errorMessage
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: root.successMessage.length > 0
            tone: "info"
            iconName: "check_circle"
            message: root.successMessage
        }

        // Basic information
        PreferenceHeader {
            first: true
            text: I18n.tr("Basic information")
        }

        PreferenceInfo {
            first: true
            label: I18n.tr("Profile name")
            subtext: root.profile ? root.profile.name : I18n.tr("No editable profile")
        }

        PreferenceInfo {
            visible: !root.isWired
            label: I18n.tr("SSID")
            subtext: root.profile ? root.profile.ssid : "—"
        }

        PreferenceInfo {
            last: true
            label: I18n.tr("Interface")
            subtext: root.profile ? root.profile.deviceName : root.target ? root.target.deviceName
                                                                            || root.target.name : "—"
        }

        // IPv4
        PreferenceHeader {
            visible: root.profile !== null
            text: I18n.tr("IPv4")
        }

        PreferenceToggle {
            visible: root.profile !== null
            first: true
            text: I18n.tr("Connect automatically")
            checked: root.autoconnect
            onToggled: root.autoconnect = checked
        }

        PreferenceSelect {
            visible: root.profile !== null
            last: true
            label: I18n.tr("IP assignment")
            model: [
                {
                    "label": I18n.tr("Automatic (DHCP)"),
                    "value": "auto"
                },
                {
                    "label": I18n.tr("DHCP + custom DNS"),
                    "value": "auto-dns"
                },
                {
                    "label": I18n.tr("Manual"),
                    "value": "manual"
                }
            ]
            currentValue: root.mode
            inputRegionService: PopupInputRegionService
            onSelected: value => {
                root.mode = value;
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: manualColumn.implicitHeight
            visible: root.mode === "manual"

            ColumnLayout {
                id: manualColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: NexusStyle.padding.small

                OutlinedTextField {
                    Layout.fillWidth: true
                    labelText: I18n.tr("IPv4 address / CIDR")
                    text: root.address
                    errorText: root.addressTouched && !root.addressValid ? I18n.tr(
                                                                               "Enter a valid IPv4 CIDR, such as 192.168.1.50/24") :
                                                                           ""
                    onTextChanged: root.address = text
                    onEditingFinished: root.addressTouched = true
                }

                OutlinedTextField {
                    Layout.fillWidth: true
                    labelText: I18n.tr("Gateway")
                    text: root.gateway
                    errorText: root.gatewayTouched && !root.gatewayValid ? I18n.tr(
                                                                               "Enter a valid IPv4 gateway") :
                                                                           ""
                    onTextChanged: root.gateway = text
                    onEditingFinished: root.gatewayTouched = true
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: dnsField.implicitHeight
            visible: root.mode !== "auto"

            OutlinedTextField {
                id: dnsField

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                labelText: I18n.tr("DNS")
                text: root.dns
                errorText: root.dnsTouched && !root.dnsValid ? I18n.tr(
                                                                   "Enter at least one valid IPv4 DNS address") :
                                                               ""
                onTextChanged: root.dns = text
                onEditingFinished: root.dnsTouched = true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.profile && (root.dirty || root.saving)

            Item {
                Layout.fillWidth: true
            }

            MaterialLoadingIndicator {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                contained: false
                visible: root.saving
            }

            ActionButton {
                text: I18n.tr("Apply")
                iconName: "save"
                filled: true
                enabled: root.dirty && root.formValid && !root.saving
                onClicked: {
                    root.errorMessage = "";
                    root.successMessage = "";
                    root.saving = NetworkService.writeProfile(root.profile, {
                                                                  "method": root.mode,
                                                                  "address": root.address.trim(),
                                                                  "gateway": root.gateway.trim(),
                                                                  "dns": root.normalizeDns(root.dns),
                                                                  "autoconnect": root.autoconnect
                                                              });
                }
            }
        }
    }
}

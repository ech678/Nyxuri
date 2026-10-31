pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Add network page (T3 M4): atom rows inside the network config modal. The
// SSID and password stay full-width labeled fields (the Caelestia Add network
// original uses full-width fields, not row-embedded ones); hidden/security
// ride the toggle and select atoms.
StyledFlickable {
    id: root

    property bool submitting: false
    property string errorMessage: ""
    readonly property bool secure: securitySelect.currentValue === "personal"
    readonly property int ssidBytes: utf8Length(ssidField.text)
    readonly property bool validPassword: !secure || (passwordField.text.length >= 8
                                                      && passwordField.text.length <= 63) ||
                                          /^[0-9A-Fa-f]{64}$/.test(passwordField.text)
    readonly property bool valid: ssidBytes > 0 && ssidBytes <= 32 && validPassword

    signal completed

    function utf8Length(value) {
        try {
            return encodeURIComponent(String(value || "")).replace(/%[0-9A-Fa-f]{2}|./g, "x").length;
        } catch (error) {
            return 33;
        }
    }

    function clearSensitiveData() {
        passwordField.text = "";
    }

    function resetForm() {
        root.submitting = false;
        root.errorMessage = "";
        ssidField.text = "";
        hiddenSwitch.checked = false;
        securitySelect.currentValue = "personal";
        root.clearSensitiveData();
    }

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + NexusStyle.padding.large * 2
    Component.onDestruction: root.clearSensitiveData()

    Connections {
        function onAddWifiFinished(success, result, errorMessage) {
            if (!root.submitting)
                return;

            root.submitting = false;
            if (success) {
                root.resetForm();
                root.completed();
            } else {
                root.errorMessage = errorMessage;
            }
        }

        target: NetworkService
    }

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - NexusStyle.padding.largeIncreased * 2))
        x: Math.max(NexusStyle.padding.largeIncreased, (root.width - width) / 2)
        y: NexusStyle.padding.largeIncreased
        spacing: NexusStyle.padding.extraSmall / 2

        PreferenceHeader {
            first: true
            text: I18n.tr("Network information")
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: ssidField.implicitHeight

            OutlinedTextField {
                id: ssidField

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                labelText: I18n.tr("SSID")
                errorText: root.ssidBytes > 32 ? I18n.tr("SSID can be at most 32 UTF-8 bytes") : ""
            }
        }

        PreferenceToggle {
            id: hiddenSwitch

            first: true
            text: I18n.tr("Hidden network")
            subtext: I18n.tr("Try to connect even when this SSID is not in the scan results")
        }

        PreferenceSelect {
            id: securitySelect

            last: true
            label: I18n.tr("Security type")
            model: [
                {
                    "label": I18n.tr("WPA/WPA2 Personal"),
                    "value": "personal"
                },
                {
                    "label": I18n.tr("None / Open"),
                    "value": "open"
                }
            ]
            currentValue: "personal"
            inputRegionService: PopupInputRegionService
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root.secure ? passwordField.implicitHeight : 0
            opacity: root.secure ? 1 : 0
            clip: true

            Behavior on Layout.preferredHeight {
                NumberAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                }
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                }
            }

            OutlinedTextField {
                id: passwordField

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                labelText: I18n.tr("Password")
                passwordToggle: true
                errorText: text.length > 0 && !root.validPassword ? I18n.tr(
                                                                        "Password must be 8–63 characters or a 64-digit hexadecimal PSK") :
                                                                    ""
            }
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            visible: root.errorMessage.length > 0
            tone: "error"
            message: root.errorMessage
        }

        RowLayout {
            Layout.fillWidth: true

            Item {
                Layout.fillWidth: true
            }

            MaterialLoadingIndicator {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                contained: false
                visible: root.submitting
            }

            ActionButton {
                text: I18n.tr("Connect and add")
                iconName: "add_link"
                filled: true
                enabled: root.valid && !root.submitting
                onClicked: {
                    root.errorMessage = "";
                    root.submitting = true;
                    NetworkService.addWifiNetwork(ssidField.text, hiddenSwitch.checked, root.secure,
                                                  passwordField.text);
                }
            }
        }
    }
}

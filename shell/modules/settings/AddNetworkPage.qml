import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.shared.i18n

StyledFlickable {
    id: root

    property bool submitting: false
    property string errorMessage: ""
    readonly property bool secure: securitySelect.value === "personal"
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
        securitySelect.value = "personal";
        root.clearSensitiveData();
    }

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2
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

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingL

        SettingsSection {
            Layout.fillWidth: true
            title: I18n.tr("Network information")
            iconName: "add_link"
            contentSpacing: Metrics.spacingL

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Metrics.spacingXS

                OutlinedTextField {
                    id: ssidField

                    Layout.fillWidth: true
                    labelText: I18n.tr("SSID")
                    errorText: root.ssidBytes > 32 ? I18n.tr("SSID can be at most 32 UTF-8 bytes") : ""
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Hidden network")
                supportingText: I18n.tr("Try to connect even when this SSID is not in the scan results")

                trailing: StyledSwitch {
                    id: hiddenSwitch
                }
            }

            SettingsRow {
                Layout.fillWidth: true
                title: I18n.tr("Security type")

                trailing: SearchSelectMenuField {
                    id: securitySelect

                    Layout.preferredWidth: 240
                    value: "personal"
                    closeOnAccept: true
                    options: [
                        {
                            "value": "personal",
                            "label": I18n.tr("WPA/WPA2 Personal")
                        },
                        {
                            "value": "open",
                            "label": I18n.tr("None / Open")
                        }
                    ]
                    onAccepted: value => {
                        return securitySelect.value = value;
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: root.secure
                spacing: Metrics.spacingXS

                OutlinedTextField {
                    id: passwordField

                    Layout.fillWidth: true
                    labelText: I18n.tr("Password")
                    passwordToggle: true
                    errorText: text.length > 0 && !root.validPassword ? I18n.tr(
                                                                            "Password must be 8–63 characters or a 64-digit hexadecimal PSK") :
                                                                        ""
                }
            }
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            radius: Metrics.cornerM
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

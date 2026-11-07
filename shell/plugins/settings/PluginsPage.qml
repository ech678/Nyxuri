pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Plugins control plane (P1 / lain-connect).
// Provides an independent management surface for built-in and third-party plugins:
// - Built-in plugins: enable/disable toggle, reset to default configuration,
//   with explicit notice that they cannot be physically uninstalled.
// - Third-party plugins: Git URL installation (with --enable option),
//   online update check, complete uninstallation, and open source directory.
// Follows Caelestia NexusPageBase scaffold and M1 atom suite.
NexusPageBase {
    id: root

    title: SpotlightCatalog.title("plugins")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable
    property var parentModal: null
    property bool presentationActive: false

    property string confirmingUninstallId: ""
    property string confirmingResetId: ""
    property bool installExpanded: false
    property string installSourceUrl: ""
    property bool enableOnInstall: true

    readonly property var builtinPlugins: PluginRegistry.toggles.filter(p => !p.isThirdParty)
    readonly property var thirdPartyPlugins: PluginRegistry.toggles.filter(p => p.isThirdParty)

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // ── Built-in Plugins Section ──────────────────────────────────────────
        PreferenceHeader {
            first: true
            text: I18n.tr("Built-in plugins", "PluginsPage")
        }

        ConnectedRect {
            id: builtinNoticeCard

            first: true
            last: root.builtinPlugins.length === 0
            Layout.fillWidth: true
            implicitHeight: builtinNoticeRow.implicitHeight + NexusStyle.padding.medium * 2

            RowLayout {
                id: builtinNoticeRow

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                MaterialSymbol {
                    text: "verified_user"
                    iconSize: NexusStyle.icon.medium
                    color: Appearance.m3colors.m3primary
                }

                StyledText {
                    Layout.fillWidth: true
                    text: I18n.tr("System built-in plugins provide core desktop capabilities. They can be disabled but cannot be uninstalled.", "PluginsPage")
                    color: Appearance.m3colors.m3onSurfaceVariant
                    font.pixelSize: NexusStyle.font.bodySmall
                    wrapMode: Text.Wrap
                }
            }

            SettingsSearchAnchor {
                id: builtinAnchor
                target: builtinNoticeCard
                anchorId: "plugins.section.builtin"
            }
        }

        Repeater {
            model: root.builtinPlugins

            delegate: ColumnLayout {
                id: builtinItem

                required property var modelData
                required property int index

                Layout.fillWidth: true
                spacing: 0

                readonly property bool isPending: UnitControlService.pendingUnitId === builtinItem.modelData.unitId
                                                  || (PluginManagerService.busy && PluginManagerService.targetPluginId === builtinItem.modelData.unitId)
                readonly property bool isEnabled: StateProjection.isEnabledUnit(builtinItem.modelData.unitId)
                readonly property bool isResetConfirm: root.confirmingResetId === builtinItem.modelData.unitId

                PreferenceToggle {
                    first: false
                    last: false
                    text: I18n.tr(builtinItem.modelData.label)
                    subtext: builtinItem.isPending ? I18n.tr("Applying…") :
                             builtinItem.isEnabled ? I18n.tr("Enabled") : I18n.tr("Disabled")
                    checked: builtinItem.isEnabled
                    enabled: !builtinItem.isPending && UnitControlService.canToggle(builtinItem.modelData.unitId)
                    onToggled: UnitControlService.setUnit(builtinItem.modelData.unitId, checked)
                }

                PreferenceAction {
                    last: builtinItem.index === root.builtinPlugins.length - 1
                    icon: "restart_alt"
                    text: builtinItem.isResetConfirm ? I18n.tr("Confirm reset to default configuration?") : I18n.tr("Reset to default configuration")
                    subtext: builtinItem.isResetConfirm ? I18n.tr("Click again to clear custom options and revert to upstream defaults") :
                             I18n.tr("Built-in system plugin · Cannot be uninstalled")
                    trailingIcon: builtinItem.isResetConfirm ? "check" : "chevron_right"
                    enabled: !builtinItem.isPending
                    onClicked: {
                        if (builtinItem.isResetConfirm) {
                            root.confirmingResetId = "";
                            PluginManagerService.resetPlugin(builtinItem.modelData.unitId, builtinItem.modelData.id);
                        } else {
                            root.confirmingResetId = builtinItem.modelData.unitId;
                        }
                    }
                }
            }
        }

        // ── Third-party Plugins Section ───────────────────────────────────────
        PreferenceHeader {
            Layout.topMargin: NexusStyle.spacing.medium
            text: I18n.tr("Third-party plugins", "PluginsPage")
        }

        PreferenceAction {
            id: installHeaderAction

            first: true
            last: !root.installExpanded && root.thirdPartyPlugins.length === 0
            icon: "add"
            text: I18n.tr("Install plugin from Git URL", "PluginsPage")
            subtext: root.installExpanded ? I18n.tr("Enter repository Git URL or local directory below") :
                     I18n.tr("Clone and register a community plugin")
            trailingIcon: root.installExpanded ? "expand_less" : "expand_more"
            onClicked: root.installExpanded = !root.installExpanded

            SettingsSearchAnchor {
                id: installAnchor
                target: installHeaderAction
                anchorId: "plugins.section.install"
            }
        }

        ConnectedRect {
            id: installFormCard

            visible: root.installExpanded
            Layout.fillWidth: true
            first: false
            last: root.thirdPartyPlugins.length === 0
            implicitHeight: installLayout.implicitHeight + NexusStyle.padding.medium * 2

            ColumnLayout {
                id: installLayout

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                spacing: NexusStyle.padding.small

                StyledText {
                    Layout.fillWidth: true
                    text: I18n.tr("Git repository URL or local directory path:")
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                }

                PreferenceInput {
                    id: urlInputField

                    first: true
                    last: false
                    label: I18n.tr("Source")
                    placeholderText: "https://github.com/… or local path"
                    onEditingFinished: value => root.installSourceUrl = value
                }

                PreferenceToggle {
                    first: false
                    last: false
                    text: I18n.tr("Enable on install")
                    checked: root.enableOnInstall
                    onToggled: root.enableOnInstall = checked
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: NexusStyle.padding.small

                    Item {
                        Layout.fillWidth: true
                    }

                    ActionButton {
                        text: I18n.tr("Cancel")
                        onClicked: {
                            root.installExpanded = false;
                            urlInputField.clear();
                        }
                    }

                    ActionButton {
                        filled: true
                        iconName: "download"
                        text: PluginManagerService.busy && PluginManagerService.activeOp === "install" ?
                              I18n.tr("Installing…") : I18n.tr("Install")
                        enabled: !PluginManagerService.busy && (urlInputField.field.text.trim().length > 0 || root.installSourceUrl.trim().length > 0)
                        onClicked: {
                            const src = (urlInputField.field.text || root.installSourceUrl).trim();
                            if (src.length > 0) {
                                PluginManagerService.installPlugin(src, root.enableOnInstall);
                                urlInputField.clear();
                                root.installSourceUrl = "";
                                root.installExpanded = false;
                            }
                        }
                    }
                }
            }
        }

        PreferenceInfo {
            id: emptyThirdPartyNotice

            visible: root.thirdPartyPlugins.length === 0 && !root.installExpanded
            first: false
            last: true
            icon: "info"
            label: I18n.tr("No third-party plugins installed yet")
            subtext: I18n.tr("Plugins installed from Git or data directory will appear here.")

            SettingsSearchAnchor {
                id: thirdPartyAnchor
                target: emptyThirdPartyNotice
                anchorId: "plugins.section.thirdparty"
            }
        }

        Repeater {
            model: root.thirdPartyPlugins

            delegate: ColumnLayout {
                id: thirdPartyItem

                required property var modelData
                required property int index

                Layout.fillWidth: true
                spacing: 0

                readonly property bool isPending: UnitControlService.pendingUnitId === thirdPartyItem.modelData.unitId
                                                  || (PluginManagerService.busy && PluginManagerService.targetPluginId === thirdPartyItem.modelData.unitId)
                readonly property bool isEnabled: StateProjection.isEnabledUnit(thirdPartyItem.modelData.unitId)
                readonly property bool isUninstallConfirm: root.confirmingUninstallId === thirdPartyItem.modelData.unitId

                PreferenceToggle {
                    first: !root.installExpanded && thirdPartyItem.index === 0
                    last: false
                    text: I18n.tr(thirdPartyItem.modelData.label)
                    subtext: thirdPartyItem.isPending ? I18n.tr("Applying…") :
                             thirdPartyItem.isEnabled ? I18n.tr("Enabled") : I18n.tr("Disabled")
                    checked: thirdPartyItem.isEnabled
                    enabled: !thirdPartyItem.isPending && UnitControlService.canToggle(thirdPartyItem.modelData.unitId)
                    onToggled: UnitControlService.setUnit(thirdPartyItem.modelData.unitId, checked)
                }

                PreferenceAction {
                    icon: "sync"
                    text: I18n.tr("Check for updates")
                    subtext: I18n.tr("Pull fast-forward updates from origin Git repository")
                    trailingIcon: "chevron_right"
                    enabled: !thirdPartyItem.isPending
                    onClicked: PluginManagerService.updatePlugin(thirdPartyItem.modelData.unitId)
                }

                PreferenceAction {
                    icon: "folder_open"
                    text: I18n.tr("Open source directory")
                    subtext: thirdPartyItem.modelData.dir
                    trailingIcon: "open_in_new"
                    onClicked: PluginManagerService.openPluginDir(thirdPartyItem.modelData.dir)
                }

                PreferenceAction {
                    last: thirdPartyItem.index === root.thirdPartyPlugins.length - 1
                    icon: "delete"
                    text: thirdPartyItem.isUninstallConfirm ? I18n.tr("Confirm permanent uninstallation?") : I18n.tr("Uninstall plugin")
                    subtext: thirdPartyItem.isUninstallConfirm ? I18n.tr("Click again to remove plugin files from disk and erase from ledger") :
                             I18n.tr("Safely disable and remove this third-party plugin")
                    trailingIcon: thirdPartyItem.isUninstallConfirm ? "warning" : "chevron_right"
                    enabled: !thirdPartyItem.isPending
                    onClicked: {
                        if (thirdPartyItem.isUninstallConfirm) {
                            root.confirmingUninstallId = "";
                            PluginManagerService.removePlugin(thirdPartyItem.modelData.unitId);
                        } else {
                            root.confirmingUninstallId = thirdPartyItem.modelData.unitId;
                        }
                    }
                }
            }
        }

        // ── Status & Feedback Banners ─────────────────────────────────────────
        InlineStatusBanner {
            Layout.fillWidth: true
            Layout.topMargin: NexusStyle.spacing.small
            visible: PluginManagerService.lastError.length > 0
            tone: "error"
            message: PluginManagerService.lastError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            Layout.topMargin: NexusStyle.spacing.small
            visible: PluginManagerService.lastOutput.length > 0 && PluginManagerService.lastError.length === 0
            tone: "info"
            message: PluginManagerService.lastOutput
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            Layout.topMargin: NexusStyle.spacing.small
            visible: UnitControlService.lastError.length > 0
            tone: "error"
            message: UnitControlService.lastError
        }

        InlineStatusBanner {
            Layout.fillWidth: true
            Layout.topMargin: NexusStyle.spacing.small
            visible: StateProjection.degraded
            tone: "error"
            message: I18n.tr("The unit ledger is unreadable; every unit is shown as enabled.")
        }
    }
}

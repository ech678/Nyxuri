pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Window
import qs.plugins.wallpaper
import "../../commons/WallpaperSource.js" as WallpaperSource
import qs.commons
import qs.ui
import qs.services
import qs.app
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Account page (M3 rebuild): NexusPageBase scaffold + AccountProfileHeader
// hero, then Language / Bluetooth / Keyboard shortcuts / Personalization
// connected groups built from the M1 atom suite. Business truths (identity,
// avatar, wallpaper, bluetooth, network, shortcuts, language) keep their
// owners; only the presentation changed. Custom rows survive where the atom
// suite has no shape: paired-device rows and the wallpaper quick grid.
NexusPageBase {
    id: root

    title: I18n.tr("Account")

    // Window contract surface — consumed by ControlCenterWindow.
    readonly property Item searchLeaf: root.flickable

    property var parentModal: null
    property bool presentationActive: false
    signal navigateRequested(string pageId)

    onPresentationActiveChanged: SystemIdentityService.setUptimeConsumer("account-page",
                                                                         root.presentationActive)
    Component.onDestruction: SystemIdentityService.setUptimeConsumer("account-page", false)

    function closeChildWindows() {
        bannerEditor.close();
        avatarPicker.dismiss();
    }

    readonly property var languageOptions: I18nService.supportedLanguages.map(lang => ({
        "label": lang.label,
        "value": lang.code
    }))
    readonly property var colorModeOptions: [
        {
            "label": I18n.tr("Light"),
            "value": "light"
        },
        {
            "label": I18n.tr("Dark"),
            "value": "dark"
        }
    ]
    // Quick-pick tiles always tile the full row: 6 items divide exactly into
    // 6 columns (wide) or 2 rows of 3 (narrow), so there is never a ragged
    // trailing cell or dead side space. The tile width is derived from the
    // row, never capped — the old 152px cap was tuned for a ~450px card and
    // broke apart inside the 800px Nexus column.
    readonly property int wallpaperColumns: wallpaperGrid.width >= 640 ? 6 : 3
    readonly property real wallpaperPreviewWidth: (wallpaperGrid.width - (wallpaperColumns - 1)
                                                   * NexusStyle.padding.small) / wallpaperColumns
    readonly property real wallpaperPreviewHeight: Math.round(root.wallpaperPreviewWidth / 1.25)
    readonly property var pairedBluetoothDevices: {
        const result = [];
        const seen = {};
        const groups = [BluetoothService.connectedDevices.filter(device => device.paired || device.bonded
                                                                           || device.trusted),
                        BluetoothService.pairedDevices];
        for (const group of groups) {
            for (const device of group) {
                const key = String(device.address || device.id || device.name || "");
                if (seen[key])
                    continue;
                seen[key] = true;
                result.push(device);
            }
        }
        return result;
    }
    readonly property var wallpaperChoices: {
        const values = [];
        const current = WallpaperService.currentWallpaper;
        if (current)
            values.push(current);
        for (const path of WallpaperService.wallpapers) {
            if (values.indexOf(path) < 0)
                values.push(path);
            if (values.length >= 6)
                break;
        }
        return values;
    }

    function bluetoothIcon(device) {
        const icon = String(device && device.icon || "").toLowerCase();
        if (icon.indexOf("head") >= 0 || icon.indexOf("audio") >= 0)
            return "headphones";
        if (icon.indexOf("keyboard") >= 0)
            return "keyboard";
        if (icon.indexOf("mouse") >= 0)
            return "mouse";
        if (icon.indexOf("phone") >= 0)
            return "smartphone";
        return "bluetooth";
    }

    function bluetoothState(device) {
        if (device.connected)
            return I18n.tr("Connected");
        return I18n.tr("Paired");
    }

    function bluetoothAction(device) {
        if (device.connected)
            BluetoothService.disconnectDevice(device);
        else
            BluetoothService.connectDevice(device);
    }

    function bluetoothActionText(device) {
        if (device.connected)
            return I18n.tr("Disconnect");
        return I18n.tr("Connect");
    }

    function networkStatusIcon() {
        if (NetworkService.wifiConnecting)
            return "wifi_find";
        if (!NetworkService.available || !NetworkService.connected)
            return "wifi_off";
        if (NetworkService.activeNetwork && NetworkService.activeNetwork.type === "wired")
            return "settings_ethernet";
        if (NetworkService.signalStrength >= 70)
            return "signal_wifi_4_bar";
        if (NetworkService.signalStrength >= 35)
            return "network_wifi_2_bar";
        return "network_wifi_1_bar";
    }

    function networkStatusText() {
        if (!NetworkService.available)
            return I18n.tr("Network unavailable");
        if (NetworkService.wifiConnecting)
            return NetworkService.connectTargetSsid || I18n.tr("Connecting");
        if (NetworkService.connected)
            return NetworkService.activeConnection;
        return I18n.tr("Not connected");
    }

    function networkStatusDetail() {
        if (NetworkService.wifiConnecting)
            return NetworkService.connectTargetSsid ? I18n.tr("Connecting") : "";
        if (!NetworkService.connected)
            return "";
        if (NetworkService.activeNetwork && NetworkService.activeNetwork.type === "wired")
            return I18n.tr("Connected, wired");
        return NetworkService.activeWifi && NetworkService.activeWifi.isSecure ? I18n.tr("Connected, secure") :
                                                                                 I18n.tr("Connected, open");
    }

    // Connected group row for one paired device — the atom suite has no
    // device-row shape (trailing action button + overflow menu).
    component DeviceRow: ConnectedRect {
        id: deviceRow

        required property var modelData

        Layout.fillWidth: true
        implicitHeight: deviceContent.implicitHeight + NexusStyle.padding.medium * 2

        RowLayout {
            id: deviceContent

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            MaterialSymbol {
                iconSize: NexusStyle.icon.medium
                fill: 1
                text: root.bluetoothIcon(deviceRow.modelData)
                color: Appearance.m3colors.m3primary
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                StyledText {
                    Layout.fillWidth: true
                    text: deviceRow.modelData.name || I18n.tr("Unnamed device")
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    elide: Text.ElideRight
                }

                StyledText {
                    Layout.fillWidth: true
                    text: root.bluetoothState(deviceRow.modelData)
                    color: Appearance.m3colors.m3outline
                    font.pixelSize: NexusStyle.font.labelSmall
                    elide: Text.ElideRight
                }
            }

            ActionButton {
                text: root.bluetoothActionText(deviceRow.modelData)
                enabled: BluetoothService.enabled && !BluetoothService.busy
                onClicked: root.bluetoothAction(deviceRow.modelData)
            }

            Item {
                Layout.preferredWidth: moreButton.implicitWidth
                Layout.preferredHeight: moreButton.implicitHeight

                IconButton {
                    id: moreButton

                    anchors.fill: parent
                    enabled: !BluetoothService.busy
                    iconName: "more_horiz"
                    iconSize: NexusStyle.icon.medium
                    iconColor: Appearance.m3colors.m3onSurfaceVariant
                    accessibleName: I18n.tr("More options for %1").arg(deviceRow.modelData.name || I18n.tr(
                                                                           "Unnamed device"))
                    onClicked: forgetMenu.open()
                }

                StyledMenu {
                    id: forgetMenu

                    parent: moreButton
                    x: moreButton.width - width
                    y: moreButton.height

                    StyledMenuItem {
                        iconName: "delete"
                        destructive: true
                        text: I18n.tr("Forget device")
                        onTriggered: BluetoothService.forgetDevice(deviceRow.modelData)
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        SystemIdentityService.setUptimeConsumer("account-page", root.presentationActive);
        if (WallpaperService.wallpapers.length === 0 && !WallpaperService.scanning)
            WallpaperService.scan();
    }

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: NexusStyle.padding.extraSmall / 2

        // Hero — profile banner, avatar, identity and network status.
        AccountProfileHeader {
            id: accountHeader

            Layout.fillWidth: true
            wallpaperIsImage: WallpaperSource.isImage(wallpaperPath)
            wallpaperComponent: ProfileWallpaper {
                sourcePath: accountHeader.wallpaperPath
                previewPath: accountHeader.previewWallpaperPath
            }
            wallpaperPath: bannerEditor.source
            previewWallpaperPath: bannerEditor.previewSource
            colorWallpaper: WallpaperService.isColorSource(wallpaperPath)
            avatarUrl: AvatarService.avatarUrl
            fallbackAvatarUrl: Paths.fileUrl(Paths.defaultAvatar)
            accountIdentity: SystemIdentityService.accountIdentity
            distroId: SystemIdentityService.distroId
            distroName: SystemIdentityService.distroName
            uptimeText: SystemIdentityService.uptimeText
            showNetworkStatus: true
            networkIconName: root.networkStatusIcon()
            networkStatusText: root.networkStatusText()
            networkStatusDetail: root.networkStatusDetail()
            onBannerFileActivated: bannerEditor.chooseFile()
            onBannerColorActivated: bannerEditor.chooseColor()
            onBannerCleared: bannerEditor.clear()
            onAvatarActivated: avatarPicker.openAt(avatarPicker.picturesDir)
            onNetworkActivated: root.navigateRequested("network")
        }

        // Language
        PreferenceHeader {
            text: I18n.tr("Language")
        }

        PreferenceSelect {
            id: languageSelect

            first: true
            last: true
            label: I18n.tr("Display language")
            model: root.languageOptions
            currentValue: UiPreferences.language
            inputRegionService: PopupInputRegionService
            onSelected: value => UiPreferences.setLanguage(value)

            SettingsSearchAnchor {
                target: languageSelect
                declaration:
                    '{"id":"account.section.language","route":"account","title":"Language","context":"AccountPage","icon":"settings","aliases":[]}'
            }
        }

        // Bluetooth
        PreferenceHeader {
            text: I18n.tr("Bluetooth")
        }

        PreferenceToggle {
            id: bluetoothToggle

            first: true
            text: BluetoothService.enabled ? I18n.tr("Bluetooth") : I18n.tr(
                                                 "Turn on Bluetooth to connect devices")
            checked: BluetoothService.enabled
            enabled: BluetoothService.available && !BluetoothService.busy
            onToggled: BluetoothService.setBluetoothEnabled(checked)

            SettingsSearchAnchor {
                target: bluetoothToggle
                declaration:
                    '{"id":"account.section.bluetooth-devices","route":"account","title":"Bluetooth devices","context":"AccountPage","icon":"settings","aliases":[]}'
            }
        }

        Repeater {
            model: root.pairedBluetoothDevices

            delegate: DeviceRow {}
        }

        ConnectedRect {
            Layout.fillWidth: true
            visible: BluetoothService.enabled && root.pairedBluetoothDevices.length === 0
            implicitHeight: noDevicesLabel.implicitHeight + NexusStyle.padding.medium * 2

            StyledText {
                id: noDevicesLabel

                anchors.centerIn: parent
                width: parent.width - NexusStyle.padding.largeIncreased * 2
                text: I18n.tr("No paired devices")
                color: Appearance.m3colors.m3onSurfaceVariant
                font.pixelSize: NexusStyle.font.bodyMedium
                horizontalAlignment: Text.AlignHCenter
            }
        }

        PreferenceAction {
            last: true
            text: I18n.tr("More Bluetooth settings")
            onClicked: root.navigateRequested("connected-devices")
        }

        // Keyboard shortcuts
        PreferenceHeader {
            text: I18n.tr("Keyboard shortcuts")
        }

        PreferenceAction {
            id: shortcutsRow

            first: true
            text: I18n.tr("Configure shortcuts")
            onClicked: root.navigateRequested("shortcuts")

            SettingsSearchAnchor {
                target: shortcutsRow
                declaration:
                    '{"id":"account.section.keyboard-shortcuts","route":"account","title":"Keyboard shortcuts","context":"AccountPage","icon":"settings","aliases":[]}'
            }
        }

        PreferenceAction {
            last: true
            text: I18n.tr("Shortcut map")
            trailingIcon: "open_in_new"
            onClicked: ShortcutMapService.open(root.parentModal ? root.parentModal.screen : null)
        }

        // Personalization
        PreferenceHeader {
            text: I18n.tr("Personalization")
        }

        ConnectedRect {
            id: wallpaperGridRow

            first: true
            Layout.fillWidth: true
            implicitHeight: wallpaperGrid.implicitHeight + NexusStyle.padding.medium * 2

            SettingsSearchAnchor {
                target: wallpaperGridRow
                declaration:
                    '{"id":"account.section.personalization","route":"account","title":"Personalization","context":"AccountPage","icon":"settings","aliases":[]}'
            }

            GridLayout {
                id: wallpaperGrid

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: NexusStyle.padding.largeIncreased
                anchors.rightMargin: NexusStyle.padding.largeIncreased
                columns: root.wallpaperColumns
                columnSpacing: NexusStyle.padding.small
                rowSpacing: NexusStyle.padding.small

                Repeater {
                    model: root.wallpaperChoices

                    delegate: RippleButton {
                        id: wallpaperChoice

                        required property string modelData

                        Layout.preferredWidth: root.wallpaperPreviewWidth
                        Layout.preferredHeight: root.wallpaperPreviewHeight
                        padding: 0
                        buttonRadius: NexusStyle.rounding.medium
                        containerColor: Appearance.m3colors.m3surfaceContainer
                        hoverStateLayerOpacity: 0
                        pressedStateLayerOpacity: Appearance.interaction.pressedStateLayerOpacity
                        rippleColor: Appearance.m3colors.m3onSurface
                        Accessible.name: I18n.tr("Use wallpaper %1").arg(WallpaperService.basename(modelData))
                        onClicked: WallpaperService.setWallpaper(modelData)

                        backgroundContent: Rectangle {
                            anchors.fill: parent
                            radius: NexusStyle.rounding.medium
                            color: WallpaperService.isColorSource(wallpaperChoice.modelData)
                                   ? wallpaperChoice.modelData : Appearance.m3colors.m3surfaceContainer

                            Image {
                                id: wallpaperImage

                                anchors.fill: parent
                                source: WallpaperService.isImagePath(wallpaperChoice.modelData)
                                        ? Paths.fileUrl(wallpaperChoice.modelData) : ""
                                sourceSize: Qt.size(Math.max(1, Math.ceil(width * Screen.devicePixelRatio * 2)),
                                                    Math.max(1, Math.ceil(height * Screen.devicePixelRatio
                                                                          * 2)))
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                cache: true
                                smooth: false
                                mipmap: false
                                visible: source !== ""
                                layer.enabled: true
                                layer.effect: MultiEffect {
                                    maskEnabled: true
                                    maskSource: wallpaperMask
                                    maskThresholdMin: 0.5
                                    maskSpreadAtMin: 1
                                }
                            }

                            Rectangle {
                                id: wallpaperMask

                                anchors.fill: parent
                                radius: NexusStyle.rounding.medium
                                color: Appearance.m3colors.m3scrim
                                visible: false
                                layer.enabled: true
                            }

                            // Current-wallpaper selection ring: a 2px inset
                            // primary stroke that rides above the tile.
                            Rectangle {
                                anchors.fill: parent
                                radius: NexusStyle.rounding.medium
                                color: "transparent"
                                border.width: 2
                                border.color: Appearance.m3colors.m3primary
                                visible: WallpaperService.currentWallpaper === wallpaperChoice.modelData
                            }
                        }

                        contentItem: Item {}
                    }
                }

                Rectangle {
                    Layout.columnSpan: root.wallpaperColumns
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.wallpaperPreviewHeight
                    visible: root.wallpaperChoices.length === 0
                    radius: NexusStyle.rounding.medium
                    color: Appearance.m3colors.m3surfaceContainerHighest

                    MaterialSymbol {
                        anchors.centerIn: parent
                        text: WallpaperService.scanning ? "progress_activity" : "wallpaper"
                        iconSize: NexusStyle.icon.medium
                        color: Appearance.m3colors.m3onSurfaceVariant
                    }
                }
            }
        }

        PreferenceSelect {
            label: I18n.tr("Color mode")
            model: root.colorModeOptions
            currentValue: PersonalizationConfig.themeMode
            inputRegionService: PopupInputRegionService
            onSelected: value => ThemeService.setThemeMode(value)
        }

        PreferenceAction {
            icon: "wallpaper"
            text: I18n.tr("Wallpaper")
            onClicked: root.navigateRequested("wallpaper")
        }

        PreferenceAction {
            last: true
            icon: "palette"
            text: I18n.tr("Theme")
            onClicked: root.navigateRequested("theme")
        }

        // Non-visual children live inside the content column (NexusPageBase
        // takes a single Item; a page-level child on the root is a type
        // error that kills the whole page — 2026-10-25 lesson).
        ProfileBannerEditor {
            id: bannerEditor

            parentModal: root.parentModal
        }

        FilePickerWindow {
            id: avatarPicker

            parentModal: root.parentModal
            requiresParentWindow: true
            dialogTitle: I18n.tr("Choose avatar")
            onAccepted: (path, isDirectory) => {
                if (!isDirectory)
                    AvatarService.setAvatar(path);
            }
        }
    }
}

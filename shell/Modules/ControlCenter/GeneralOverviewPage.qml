import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

StyledFlickable {
    id: root

    signal sectionRequested(string section)

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + Metrics.pageMargin * 2

    ColumnLayout {
        id: contentColumn

        width: Math.min(640, Math.max(0, root.width - Metrics.pageMargin * 2))
        x: Math.max(Metrics.pageMargin, (root.width - width) / 2)
        y: Metrics.pageMargin
        spacing: Metrics.spacingL

        SettingsSection {
            id: searchSection0

            Layout.fillWidth: true
            title: searchAnchor0.title
            iconName: "dashboard"

            SettingsSearchAnchor {
                id: searchAnchor0

                target: searchSection0
                declaration:
                    '{"id":"general.section.interface","route":"general","title":"Interface","context":"GeneralOverviewPage","icon":"settings","aliases":[],"source":"GeneralOverviewPage.qml"}'
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "dock_to_bottom"
                text: SpotlightCatalog.title("general.bar")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("bar")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "dock_to_bottom"
                text: SpotlightCatalog.title("general.dock")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("dock")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "side_navigation"
                text: SpotlightCatalog.title("general.sidebar")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("sidebar")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "search"
                text: "Spotlight"
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("spotlight")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "blur_on"
                text: SpotlightCatalog.title("general.effects")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("effects")
            }
        }

        SettingsSection {
            id: searchSection1

            Layout.fillWidth: true
            title: searchAnchor1.title
            iconName: "settings_suggest"

            SettingsSearchAnchor {
                id: searchAnchor1

                target: searchSection1
                declaration:
                    '{"id":"general.section.system","route":"general","title":"System","context":"GeneralOverviewPage","icon":"settings","aliases":[],"source":"GeneralOverviewPage.qml"}'
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "monitor"
                text: SpotlightCatalog.title("general.displays")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("displays")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "keyboard"
                text: SpotlightCatalog.title("general.shortcuts")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("shortcuts")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "language"
                text: SpotlightCatalog.title("general.language-region")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("language-region")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "wifi"
                text: SpotlightCatalog.title("general.network")
                description: NetworkService.available ? NetworkService.activeConnection : qsTr(
                                                            "Network unavailable")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("network")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "devices_other"
                text: SpotlightCatalog.title("general.connected-devices")
                description: {
                    if (!BluetoothService.available)
                        return qsTr("Bluetooth unavailable");

                    if (!BluetoothService.enabled)
                        return qsTr("Bluetooth is off");

                    if (BluetoothService.connectedDevices.length === 1)
                        return BluetoothService.connectedDevices[0].name;

                    if (BluetoothService.connectedDevices.length > 1)
                        return qsTr("%1 devices connected").arg(BluetoothService.connectedDevices.length);

                    return "";
                }
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("connected-devices")
            }
        }

        SettingsSection {
            id: searchSection2

            Layout.fillWidth: true
            title: searchAnchor2.title
            iconName: "apps"

            SettingsSearchAnchor {
                id: searchAnchor2

                target: searchSection2
                declaration:
                    '{"id":"general.section.applications","route":"general","title":"Applications","context":"GeneralOverviewPage","icon":"settings","aliases":[],"source":"GeneralOverviewPage.qml"}'
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "rocket_launch"
                text: SpotlightCatalog.title("general.autostart")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("autostart")
            }

            SettingsActionRow {
                Layout.fillWidth: true
                iconName: "apps"
                text: SpotlightCatalog.title("general.default-apps")
                trailingIconName: "chevron_right"
                onClicked: root.sectionRequested("default-apps")
            }
        }
    }
}

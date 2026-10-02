import QtQuick
import qs.app.services
import qs.shared.theme
import qs.shared.controls

BarLabelButton {
    id: root

    property var screen: null
    readonly property bool active: WidgetState.quickSettingsOpen && WidgetState.quickSettingsView
                                   === "network"
    tooltipText: NetworkService.connected ? ((NetworkService.activeConnection || qsTr("Network connected"))
                                             + qsTr("\nClick to open network settings")) : qsTr(
                                                "Network disconnected\nClick to open network settings")
    readonly property string networkIcon: {
        if (NetworkService.activeConnectionType === "ETHERNET")
            return "settings_ethernet";

        if (!NetworkService.connected)
            return "wifi_off";

        const strength = Number(NetworkService.signalStrength || 0);
        if (strength >= 80)
            return "signal_wifi_4_bar";

        if (strength >= 60)
            return "network_wifi_3_bar";

        if (strength >= 40)
            return "network_wifi_2_bar";

        if (strength >= 20)
            return "network_wifi_1_bar";

        return "signal_wifi_0_bar";
    }

    function toggleNetworkView() {
        if (root.screen && root.screen.name)
            WidgetState.quickSettingsScreenName = root.screen.name;

        if (root.active) {
            WidgetState.quickSettingsOpen = false;
        } else {
            WidgetState.quickSettingsView = "network";
            WidgetState.quickSettingsOpen = true;
        }
    }

    iconName: root.networkIcon
    label: NetworkService.connected ? NetworkService.activeConnection : ""
    showLabel: PersonalizationConfig.barShowNames
    selected: root.active
    onClicked: root.toggleNetworkView()
}

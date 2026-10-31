import QtQuick
import qs.app
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

BarLabelButton {
    id: root
    barEdge: PersonalizationConfig.barPosition

    property var screen: null
    readonly property bool active: WidgetState.quickSettingsOpen && WidgetState.quickSettingsView
                                   === "bluetooth"

    iconName: BluetoothService.connected ? "bluetooth_connected" : BluetoothService.enabled ? "bluetooth" :
                                                                                              "bluetooth_disabled"
    selected: root.active
    enabled: BluetoothService.available
    label: BluetoothService.connectedName || ""
    showLabel: PersonalizationConfig.barShowNames
    tooltipText: BluetoothService.connected ? (BluetoothService.connectedName || I18n.tr(
                                                   "Bluetooth connected")) : BluetoothService.enabled
                                              ? I18n.tr("Bluetooth on") : I18n.tr("Bluetooth off")
    onClicked: {
        if (root.screen && root.screen.name)
            WidgetState.quickSettingsScreenName = root.screen.name;

        if (root.active) {
            WidgetState.quickSettingsOpen = false;
        } else {
            WidgetState.quickSettingsView = "bluetooth";
            WidgetState.quickSettingsOpen = true;
        }
    }
}

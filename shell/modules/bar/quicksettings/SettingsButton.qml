import QtQuick
import qs.shared.theme
import qs.app.services
import qs.shared.controls
import qs.app
import qs.shared.i18n

BarCircularButton {
    id: root

    property var screen: null
    readonly property bool active: WidgetState.quickSettingsOpen && WidgetState.quickSettingsView
                                   === "settings"

    iconName: "settings"
    selected: root.active
    containerColor: "transparent"
    rippleColor: Appearance.colors.colOnSurface
    iconColor: Appearance.colors.colOnSurface
    tooltipText: I18n.tr("Left click: Quick Settings\nRight click: Control Center")
    onClicked: {
        if (root.screen && root.screen.name)
            WidgetState.quickSettingsScreenName = root.screen.name;

        if (root.active) {
            WidgetState.quickSettingsOpen = false;
        } else {
            WidgetState.quickSettingsView = "settings";
            WidgetState.quickSettingsOpen = true;
        }
    }
    onAltClicked: ActionGateway.requestSettingsOpen()
}

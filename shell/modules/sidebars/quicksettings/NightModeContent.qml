import QtQuick
import qs.app
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.modules.settings

WidgetPanel {
    title: qsTr("Night Mode")
    icon: "nightlight"
    showBackButton: true
    backAction: () => WidgetState.quickSettingsView = "settings"

    GammaControlPage {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentPadding: 0
        searchAnchorsEnabled: false
    }
}

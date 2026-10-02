import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Widgets.common
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

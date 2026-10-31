import QtQuick
import qs.app
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.plugins.settings
import qs.commons.i18n

WidgetPanel {
    title: I18n.tr("Night Mode")
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

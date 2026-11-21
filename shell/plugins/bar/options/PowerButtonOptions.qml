import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Power button entry options (D4b): "default" keeps the session toggle
// (Mod+X parity).
ColumnLayout {
    id: root

    property var page: null

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Actions")
    }

    WidgetClickRows {
        Layout.fillWidth: true
        page: root.page
        includeDefault: true
    }
}

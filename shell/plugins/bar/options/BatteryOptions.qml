import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Battery entry options (D4b, dux BatteryOptions trimmed to the axes this
// widget paints): the percent readout, the wattage line and click actions.
ColumnLayout {
    id: root

    property var page: null

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Battery")
    }

    PreferenceToggle {
        first: true
        text: I18n.tr("Show percentage")
        checked: root.page.value("showPercent")
        onToggled: checked => root.page.set("showPercent", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("Show power draw")
        subtext: I18n.tr("Wattage while plugged in")
        checked: root.page.value("showPower")
        onToggled: checked => root.page.set("showPower", checked || undefined)
    }

    PreferenceHeader {
        text: I18n.tr("Actions")
    }

    WidgetClickRows {
        Layout.fillWidth: true
        page: root.page
        includeDefault: false
    }
}

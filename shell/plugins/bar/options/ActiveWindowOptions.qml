import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Active window entry options (D4b): the end4 280px title clamp and click
// actions.
ColumnLayout {
    id: root

    property var page: null

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Active Window")
    }

    PreferenceSlider {
        first: true
        label: I18n.tr("Maximum width")
        value: root.page.value("maxWidth")
        valueLabel: Math.round(root.page.value("maxWidth")) + " px"
        from: 120
        to: 600
        stepSize: 4
        onMoved: value => root.page.set("maxWidth", Math.round(value) === 280 ? undefined : Math.round(value))
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

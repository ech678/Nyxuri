import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Clock entry options (D4b): date line, the per-instance long-date
// pattern (the old [time].dateFormat key) and the click actions.
ColumnLayout {
    id: root

    property var page: null

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Clock")
    }

    PreferenceToggle {
        first: true
        text: I18n.tr("Show date")
        checked: root.page.value("showDate")
        onToggled: checked => root.page.set("showDate", checked || undefined)
    }

    PreferenceInput {
        label: I18n.tr("Date format")
        subtext: I18n.tr("Qt date pattern, e.g. ddd, dd/MM")
        placeholderText: "dddd, dd/MM"
        value: root.page.value("dateFormat") ?? ""
        emptyIsValid: true
        onEditingFinished: value => root.page.set("dateFormat", String(value || "").trim() || undefined)
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

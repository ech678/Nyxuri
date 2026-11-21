import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Media entry options (D4b): the D1 width clamp (160/300 defaults, author
// decision), the title line and the wheel behavior.
ColumnLayout {
    id: root

    property var page: null

    readonly property var scrollActions: [
        {
            value: "none",
            label: I18n.tr("None")
        },
        {
            value: "volume",
            label: I18n.tr("Volume")
        }
    ]

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Media")
    }

    PreferenceToggle {
        first: true
        text: I18n.tr("Show title")
        checked: root.page.value("showTitle")
        onToggled: checked => root.page.set("showTitle", checked === true ? undefined : checked)
    }

    PreferenceSlider {
        label: I18n.tr("Minimum width")
        value: root.page.value("minWidth")
        valueLabel: Math.round(root.page.value("minWidth")) + " px"
        from: 80
        to: 400
        stepSize: 4
        onMoved: value => root.page.set("minWidth", Math.round(value) === 160 ? undefined : Math.round(value))
    }

    PreferenceSlider {
        label: I18n.tr("Maximum width")
        value: root.page.value("maxWidth")
        valueLabel: Math.round(root.page.value("maxWidth")) + " px"
        from: 120
        to: 600
        stepSize: 4
        onMoved: value => root.page.set("maxWidth", Math.round(value) === 300 ? undefined : Math.round(value))
    }

    PreferenceSelect {
        last: true
        label: I18n.tr("Scroll action")
        model: root.scrollActions
        currentValue: root.page.value("scrollAction")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("scrollAction", String(value) === "none" ? undefined : String(value))
    }
}

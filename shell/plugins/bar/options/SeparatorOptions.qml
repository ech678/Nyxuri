import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Divider entry options (D4b): the end4 rect/dot/space skins; the space
// width only exists for that skin.
ColumnLayout {
    id: root

    property var page: null

    readonly property var styles: [
        {
            value: "rect",
            label: I18n.tr("Line")
        },
        {
            value: "dot",
            label: I18n.tr("Dot")
        },
        {
            value: "space",
            label: I18n.tr("Space")
        }
    ]

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Divider")
    }

    PreferenceSelect {
        first: true
        label: I18n.tr("Divider style")
        model: root.styles
        currentValue: root.page.value("style")
        inputRegionService: PopupInputRegionService
        onSelected: value => root.page.set("style", String(value) === "rect" ? undefined : String(value))
    }

    PreferenceSlider {
        last: true
        visible: root.page.value("style") === "space"
        label: I18n.tr("Space width")
        value: root.page.value("spacing")
        valueLabel: Math.round(root.page.value("spacing")) + " px"
        from: 4
        to: 400
        stepSize: 2
        onMoved: value => root.page.set("spacing", Math.round(value / 2) * 2 === 4 ? undefined : Math.round(value / 2) * 2)
    }
}

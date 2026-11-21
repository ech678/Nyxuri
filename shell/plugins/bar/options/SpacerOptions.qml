import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Spacer entry options (D4b): the slot's fixed size (default 20 =
// design-system spacing.largeIncreased).
ColumnLayout {
    id: root

    property var page: null

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Spacer")
    }

    PreferenceSlider {
        first: true
        last: true
        label: I18n.tr("Size")
        value: root.page.value("size")
        valueLabel: Math.round(root.page.value("size")) + " px"
        from: 4
        to: 200
        stepSize: 2
        onMoved: value => root.page.set("size", Math.round(value) === 20 ? undefined : Math.round(value))
    }
}

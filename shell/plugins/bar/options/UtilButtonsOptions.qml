import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Utility buttons entry options (D4b, utilButtons == quickSettings — both
// ids load UtilButtons.qml and share one axes table).
ColumnLayout {
    id: root

    property var page: null

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Utility buttons")
    }

    PreferenceToggle {
        first: true
        text: I18n.tr("Screen snip")
        checked: root.page.value("screenSnip")
        onToggled: checked => root.page.set("screenSnip", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("Color picker")
        checked: root.page.value("colorPicker")
        onToggled: checked => root.page.set("colorPicker", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("On-screen keyboard")
        checked: root.page.value("keyboardToggle")
        onToggled: checked => root.page.set("keyboardToggle", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("Mic toggle")
        checked: root.page.value("micToggle")
        onToggled: checked => root.page.set("micToggle", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("Wallpaper toggle")
        checked: root.page.value("wallpaperToggle")
        onToggled: checked => root.page.set("wallpaperToggle", checked || undefined)
    }

    PreferenceToggle {
        text: I18n.tr("Dark/Light toggle")
        checked: root.page.value("darkModeToggle")
        onToggled: checked => root.page.set("darkModeToggle", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("Performance profile")
        checked: root.page.value("performanceProfile")
        onToggled: checked => root.page.set("performanceProfile", checked || undefined)
    }

    PreferenceHeader {
        text: I18n.tr("Hover popouts")
    }

    // Shared data-shape keys (one shape across every button popout), so
    // they write the flat [bar] keys rather than the entry.
    PreferenceToggle {
        first: true
        text: I18n.tr("Show numeric values")
        checked: PersonalizationConfig.barShowValues
        onToggled: checked => PersonalizationConfig.setBarShowValues(checked)
    }

    PreferenceToggle {
        last: true
        text: I18n.tr("Show device names")
        checked: PersonalizationConfig.barShowNames
        onToggled: checked => PersonalizationConfig.setBarShowNames(checked)
    }
}

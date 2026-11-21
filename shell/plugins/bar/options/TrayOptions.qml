import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Tray entry options (D4b): tint/hidePassive/showItemId are per-instance
// axes; pinning stays tray-domain shared state (one pin list across
// instances, B9.1) and its rows write the shared keys directly.
ColumnLayout {
    id: root

    property var page: null

    spacing: 0

    PreferenceHeader {
        first: true
        text: I18n.tr("Tray")
    }

    PreferenceToggle {
        id: trayTintToggle

        first: true
        text: I18n.tr("Tint icons")
        checked: root.page.value("tintIcons")
        onToggled: checked => root.page.set("tintIcons", checked === true ? undefined : checked)

        SettingsSearchAnchor {
            target: trayTintToggle
            anchorId: "bar.modules.tray"
        }
    }

    PreferenceToggle {
        text: I18n.tr("Hide passive items")
        checked: root.page.value("hidePassive")
        onToggled: checked => root.page.set("hidePassive", checked === true ? undefined : checked)
    }

    PreferenceToggle {
        text: I18n.tr("Show item id in tooltip")
        checked: root.page.value("showItemId")
        onToggled: checked => root.page.set("showItemId", checked || undefined)
    }

    PreferenceHeader {
        text: I18n.tr("Pinning")
    }

    PreferenceToggle {
        text: I18n.tr("Pin new items by default")
        checked: PersonalizationConfig.barTrayInvertPinnedItems
        onToggled: checked => PersonalizationConfig.setValue("barTrayInvertPinnedItems", checked)
    }

    PreferenceAction {
        last: true
        icon: "restart_alt"
        text: I18n.tr("Reset pin list")
        subtext: I18n.tr("Every item returns to the bar")
        onClicked: PersonalizationConfig.setBarTrayPinnedItems([])
    }
}

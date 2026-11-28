import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n

// Shared click-action section for per-widget options pages (D4b). The
// page facade (BarWidgetPage) supplies value()/set() and the preset
// vocabulary — pages stay storage-blind (dux `page.*` precedent). The
// command field stores an argv array split on whitespace; quoting is not
// supported (the gateway runs argument arrays, never shell strings).
ColumnLayout {
    id: root

    required property var page
    // Show the "default" preset only for widgets with a built-in click
    // behavior worth keeping (the host trims it for passive widgets).
    property bool includeDefault: false

    readonly property bool commandVisible: root.page.value("clickAction") === "command" || root.page.value("middleClickAction") === "command" || root.page.value("rightClickAction") === "command"
    readonly property var actions: root.includeDefault ? root.page.clickActionOptions : root.page.clickActionOptions.filter(option => option.value !== "default")

    spacing: 0

    function setAction(key, value) {
        root.page.set(key, value === (root.includeDefault ? "default" : "none") ? undefined : value);
    }

    PreferenceSelect {
        label: I18n.tr("Left click")
        model: root.actions
        currentValue: root.page.value("clickAction") ?? "none"
        inputRegionService: PopupInputRegionService
        onSelected: value => root.setAction("clickAction", String(value))
    }

    PreferenceSelect {
        label: I18n.tr("Middle click")
        model: root.actions
        currentValue: root.page.value("middleClickAction") ?? "none"
        inputRegionService: PopupInputRegionService
        onSelected: value => root.setAction("middleClickAction", String(value))
    }

    PreferenceSelect {
        last: !root.commandVisible
        label: I18n.tr("Right click")
        model: root.actions
        currentValue: root.page.value("rightClickAction") ?? "none"
        inputRegionService: PopupInputRegionService
        onSelected: value => root.setAction("rightClickAction", String(value))
    }

    PreferenceInput {
        last: true
        visible: root.commandVisible
        label: I18n.tr("Command")
        subtext: I18n.tr("Run as a command, arguments split by spaces")
        placeholderText: "gnome-clocks"
        value: (root.page.value("clickCommand") ?? []).join(" ")
        emptyIsValid: true
        onEditingFinished: value => {
            const argv = String(value || "").split(/\s+/).filter(part => part.length > 0);
            root.page.set("clickCommand", argv.length > 0 ? argv : undefined);
        }
    }
}

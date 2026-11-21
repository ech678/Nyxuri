pragma Singleton

import QtQuick
import qs.services
import qs.commons.i18n
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

// Click-action vocabulary for bar widget entries (D4b, dux
// ClockOptions/BatteryOptions pattern widened to L/M/R axes). Widgets
// with a clickAction/middleClickAction/rightClickAction entry axis
// resolve the id here; "default" keeps the widget's built-in behavior
// (dispatch returns false and the caller runs its own handling), and
// "command" runs the entry's argv array through the gateway — never a
// shell string (shell/AGENTS.md red line).
QtObject {
    id: root

    readonly property var ids: ["default", "none", "dashboard", "quicksettings", "launcher", "overview", "power-menu", "lock", "command"]

    // Labels resolve lazily: the dictionary loads after singleton
    // construction (BarWidgetCatalog.displayName precedent).
    function label(id) {
        switch (id) {
        case "default":
            return I18n.tr("Default action");
        case "none":
            return I18n.tr("None");
        case "dashboard":
            return I18n.tr("Dashboard");
        case "quicksettings":
            return I18n.tr("Quick settings");
        case "launcher":
            return I18n.tr("Launcher");
        case "overview":
            return I18n.tr("Overview");
        case "power-menu":
            return I18n.tr("Power menu");
        case "lock":
            return I18n.tr("Lock");
        case "command":
            return I18n.tr("Custom command");
        }
        return String(id);
    }

    function axisForButton(button) {
        if (button === Qt.LeftButton)
            return "clickAction";
        if (button === Qt.MiddleButton)
            return "middleClickAction";
        if (button === Qt.RightButton)
            return "rightClickAction";
        return "";
    }

    // Returns true when the action was consumed here; false means the
    // caller should run its built-in behavior ("default", unknown ids or
    // an empty command).
    function dispatch(action, command, owner) {
        switch (action) {
        case undefined:
        case null:
        case "":
        case "default":
            return false;
        case "none":
            return true;
        case "dashboard":
            return ActionGateway.requestSidebarToggle("dashboard");
        case "quicksettings":
            return ActionGateway.requestSidebarToggle("quicksettings");
        case "launcher":
            ActionGateway.executeIntent({
                "target": "launcher"
            });
            return true;
        case "overview":
            WidgetState.closeAllPopups();
            CompositorDriver.toggleOverview();
            return true;
        case "power-menu":
            ActionGateway.executeIntent({
                "target": "power-menu"
            });
            return true;
        case "lock":
            ActionGateway.executeIntent({
                "target": "lock"
            });
            return true;
        case "command":
            if (Array.isArray(command) && command.length > 0 && command.every(part => typeof part === "string" && part !== ""))
                return ActionGateway.execute(command, owner);
            return false;
        default:
            console.warn("[BarWidgetActions] unknown click action:", action);
            return false;
        }
    }

    // One-line consumption for widget MouseAreas: resolves the axis for
    // the button, dispatches, and reports whether the click was consumed.
    function dispatchMouse(widgetId, entry, button) {
        const axis = root.axisForButton(button);
        if (axis === "")
            return false;
        return root.dispatch(BarWidgetDefaults.option(widgetId, entry, axis), BarWidgetDefaults.option(widgetId, entry, "clickCommand"), "bar-widget:" + widgetId);
    }
}

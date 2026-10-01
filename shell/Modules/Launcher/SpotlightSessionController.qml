import QtQuick
import qs.Services
import "../../Common/functions/SpotlightSession.js" as Session
import "../../Common/functions/SpotlightCommands.js" as Commands

QtObject {
    id: root
    property var state: Session.create("search")
    property string query: ""
    property bool applying: false
    property string error: ""
    readonly property string baseMode: state.mode
    readonly property string tool: state.tool
    readonly property string viewMode: tool || baseMode
    readonly property bool literalQuery: state.literal
    readonly property var route: Session.route({
                                                   tool: tool,
                                                   mode: baseMode,
                                                   literal: literalQuery
                                               }, query)
    readonly property bool slashDraft: route.kind === "slash"
    readonly property string appsLayout: Session.effective(state, "appsLayout",
                                                           UiPreferences.spotlightAppStyle)
    readonly property string appsOrder: Session.effective(state, "appsOrder", UiPreferences.spotlightAppOrder)
    readonly property string clipboardLayout: Session.effective(state, "clipboardLayout",
                                                                UiPreferences.spotlightClipboardStyle)
    readonly property var visiblePills: tool ? [Commands.byId("tool." + tool)] : state.overrides.map(override
                                                                                                     => Commands.entries.find(
                                                                                                            entry => entry.key
                                                                                                                     === override.key
                                                                                                                     && entry.value
                                                                                                                     === override.value))
    signal actionRequested(string id)
    signal baseNavigationRequested(string mode)
    signal commandRejected
    signal contextRestored
    signal selectionRestored(string id)

    function apply(next) {
        applying = true;
        state = next;
        query = next.query;
        error = "";
        applying = false;
        selectionRestored(next.selectionId);
    }
    function reset(mode) {
        apply(Session.create(mode || "search", state.serial + 1));
    }
    function switchMode(mode, preserveQuery) {
        if (Session.modes.indexOf(mode) < 0)
            return;
        apply(Session.switchMode(state, mode, preserveQuery));
        baseNavigationRequested(mode);
    }
    function rememberSelection(id) {
        if (state.selectionId !== id)
            state = Object.assign({}, state, {
                                      selectionId: id
                                  });
    }
    function enterTool(tool, query, consumeCommand) {
        apply(Session.enterTool(state, tool, query, consumeCommand));
    }
    function pop() {
        const next = Session.pop(state);
        if (next === state)
            return false;
        apply(next);
        contextRestored();
        return true;
    }
    function canBackspace(event) {
        return Session.canBackspace(state, event);
    }
    function activate(id, args, consumeCommand) {
        const entry = Commands.byId(id);
        if (!entry)
            return false;
        const resolved = Commands.resolve(entry.slashName, args || "", state);
        if (resolved.error) {
            error = resolved.error === "scope" ? qsTr("Available in %1 only").arg(entry.scope === "apps"
                                                                                  ? qsTr("Apps") : qsTr(
                                                                                        "Clipboard")) : qsTr(
                                                     "This command does not accept arguments");
            commandRejected();
            return false;
        }
        if (entry.kind === "mode")
            switchMode(entry.value, false);
        else if (entry.kind === "tool")
            enterTool(entry.value, args || "", consumeCommand);
        else if (entry.kind === "override") {
            const saved = entry.key === "appsLayout" ? UiPreferences.spotlightAppStyle : entry.key === "appsOrder"
                                                       ? UiPreferences.spotlightAppOrder :
                                                         UiPreferences.spotlightClipboardStyle;
            apply(Session.setOverride(state, entry.key, entry.value, saved));
        } else {
            // Consuming text is session state; the actual action is never on the undo stack.
            if (consumeCommand)
                apply(Session.input(state, "", false));
            actionRequested(entry.id);
        }
        return true;
    }
    function executeSlash() {
        if (!slashDraft)
            return false;
        const entry = Commands.exact(route.name);
        if (!entry) {
            error = qsTr("Unknown command. Open Commands to browse available commands.");
            commandRejected();
            return false;
        }
        return activate(entry.id, route.arguments, true);
    }
    onQueryChanged: {
        if (applying)
            return;
        error = "";
        const next = Session.input(state, query, query.length > 0 && state.literal, state.selectionId);
        const inputRoute = Session.route(next, query);
        if (inputRoute.kind === "commands") {
            apply(Session.enterCommands(state, inputRoute.query));
        } else if (inputRoute.kind === "literal") {
            apply(Session.input(next, inputRoute.query, true));
        } else
            state = next;
    }
}

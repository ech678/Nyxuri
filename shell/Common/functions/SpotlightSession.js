// Session-only navigation. These functions never mutate preferences or execute actions.
var modes = ["search", "apps", "wallpapers", "clipboard", "files", "commands"];
var tools = ["web", "settings", "actions", "calculator", "currency", "time"];
var overrideValues = {
    appsLayout: ["list", "grid"],
    appsOrder: ["smart", "most-used", "recently-used", "name"],
    clipboardLayout: ["default", "details"]
};

function create(mode, serial) {
    return { mode: modes.indexOf(mode) >= 0 ? mode : "search", tool: "",
        query: "", literal: false, selectionId: "", overrides: [], parent: null,
        completion: null, serial: serial || 0 };
}

function input(state, text, literal, selectionId) {
    return Object.assign({}, state, { query: String(text), literal: !!literal,
        selectionId: selectionId || "", completion: null });
}

function switchMode(state, mode, preserveQuery) {
    if (modes.indexOf(mode) < 0) return state;
    const next = create(mode, state.serial + 1);
    // Tool parameters and command drafts never escape into a content provider.
    if (preserveQuery && !state.tool && (state.literal || !/^[/>]/.test(state.query))
            && state.mode !== "commands") {
        next.query = state.query;
        next.literal = state.literal;
    }
    return next;
}

function enterCommands(state, query) {
    const next = input(switchMode(state, "commands", false), query, false);
    next.parent = Object.assign({}, state, { completion: null });
    return next;
}

function enterTool(state, tool, query, consumeCommand) {
    if (tools.indexOf(tool) < 0) return state;
    // Replacing a tool reuses its one parent, bounding depth independently of input.
    let parent = state.tool ? (state.parent || state) : state;
    parent = Object.assign({}, parent, { completion: null });
    if (consumeCommand && !state.tool)
        parent = input(parent, "", false, parent.selectionId);
    return Object.assign({}, parent, { tool: tool, query: query || "", literal: false,
        selectionId: "", completion: null, parent: parent, serial: state.serial + 1 });
}

function effective(state, key, saved) {
    const override = state.overrides.find(entry => entry.key === key);
    return override ? override.value : saved;
}

function setOverride(state, key, value, saved) {
    const scope = key === "clipboardLayout" ? "clipboard" : "apps";
    if (state.tool || state.mode !== scope || !overrideValues[key]
            || overrideValues[key].indexOf(value) < 0) return state;
    const current = state.overrides.find(entry => entry.key === key);
    // Consume the slash draft even for a repeated/no-op override.
    const next = input(state, "", false, state.selectionId);
    if (current && current.value === value) return next;
    next.overrides = state.overrides.filter(entry => entry.key !== key);
    if (value !== saved) next.overrides.push({ key: key, value: value });
    return next;
}

function pop(state) {
    if (state.parent)
        return Object.assign({}, state.parent, { serial: state.serial + 1, completion: null });
    if (!state.overrides.length) return state;
    return Object.assign({}, state, { overrides: state.overrides.slice(0, -1),
        completion: null, serial: state.serial + 1 });
}

function canBackspace(state, event) {
    return state.query.length === 0 && !event.selection && !event.preedit
        && !event.modal && !state.completion && !event.repeat && event.searchFocus
        && (!!state.parent || state.overrides.length > 0);
}

function route(state, text) {
    if (state.tool || state.literal) return { kind: "query", query: text };
    if (/^\\[/>]/.test(text)) return { kind: "literal", query: text.slice(1) };
    if (state.mode !== "commands" && text.charAt(0) === ">")
        return { kind: "commands", query: text.slice(1) };
    if (text.charAt(0) === "/") {
        const match = /^\/([^\s]*)(?:\s+([\s\S]*))?$/.exec(text);
        return { kind: "slash", name: match[1].toLowerCase(), arguments: match[2] || "" };
    }
    return { kind: "query", query: text };
}

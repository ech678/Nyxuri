// One whitelist for palette navigation and slash dispatch. Existing settings and
// IPC catalogs remain the owners of their own search results and activation.
var entries = [
    { id: "mode.search", slashName: "default", title: "Default search", icon: "search", kind: "mode", value: "search" },
    { id: "mode.apps", slashName: "apps", title: "Apps", icon: "grid_view", kind: "mode", value: "apps" },
    { id: "mode.wallpapers", slashName: "wallpaper", aliases: ["wallpapers"], title: "Wallpapers", icon: "image", kind: "mode", value: "wallpapers" },
    { id: "mode.clipboard", slashName: "clipboard", title: "Clipboard", icon: "content_paste", kind: "mode", value: "clipboard" },
    { id: "mode.files", slashName: "files", title: "Files", icon: "draft", kind: "mode", value: "files" },
    { id: "mode.commands", slashName: "commands", title: "Commands", icon: "terminal", kind: "mode", value: "commands" },
    { id: "tool.web", slashName: "search", aliases: ["web"], title: "Web search", icon: "travel_explore", kind: "tool", value: "web" },
    { id: "tool.calculator", slashName: "calc", title: "Calculator", icon: "calculate", kind: "tool", value: "calculator" },
    { id: "tool.currency", slashName: "fx", aliases: ["currency"], title: "Currency", icon: "currency_exchange", kind: "tool", value: "currency" },
    { id: "tool.time", slashName: "time", aliases: ["tz"], title: "Time zone", icon: "schedule", kind: "tool", value: "time" },
    { id: "theme.light", slashName: "light", title: "Light theme", icon: "light_mode", kind: "action" },
    { id: "theme.dark", slashName: "dark", title: "Dark theme", icon: "dark_mode", kind: "action" },
    { id: "settings.open", slashName: "settings", title: "Open settings", icon: "settings", kind: "action" },
    { id: "tool.settings", slashName: "find-settings", title: "Search settings", icon: "settings", kind: "tool", value: "settings" },
    { id: "tool.actions", slashName: "actions", title: "Search IPC actions", icon: "bolt", kind: "tool", value: "actions" },
    { id: "location.open", slashName: "map", title: "Location picker", icon: "map", kind: "action" },
    { id: "apps.list", slashName: "list", title: "List", icon: "view_list", kind: "override", scope: "apps", key: "appsLayout", value: "list" },
    { id: "apps.grid", slashName: "grid", title: "Grid", icon: "grid_view", kind: "override", scope: "apps", key: "appsLayout", value: "grid" },
    { id: "apps.smart", slashName: "smart", title: "Smart", icon: "auto_awesome", kind: "override", scope: "apps", key: "appsOrder", value: "smart" },
    { id: "apps.most-used", slashName: "most-used", title: "Most used", icon: "trending_up", kind: "override", scope: "apps", key: "appsOrder", value: "most-used" },
    { id: "apps.recent", slashName: "recent", aliases: ["recently-used"], title: "Recently used", icon: "history", kind: "override", scope: "apps", key: "appsOrder", value: "recently-used" },
    { id: "apps.name", slashName: "name", title: "Name", icon: "sort_by_alpha", kind: "override", scope: "apps", key: "appsOrder", value: "name" },
    { id: "clipboard.compact", slashName: "compact", title: "Compact", icon: "view_list", kind: "override", scope: "clipboard", key: "clipboardLayout", value: "default" },
    { id: "clipboard.detail", slashName: "detail", aliases: ["details"], title: "Details", icon: "view_sidebar", kind: "override", scope: "clipboard", key: "clipboardLayout", value: "details" }
];

function available(entry, state) {
    return !!entry && (entry.kind !== "override" || (!state.tool && state.mode === entry.scope));
}

function exact(name) {
    name = String(name).toLowerCase();
    return entries.find(entry => entry.slashName === name || (entry.aliases || []).indexOf(name) >= 0) || null;
}

function byId(id) { return entries.find(entry => entry.id === id) || null; }

function match(query, palette, titleFor) {
    const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    return entries.filter(entry => (!palette || entry.kind !== "override") && words.every(word =>
        [entry.slashName, entry.title, titleFor ? titleFor(entry) : ""].concat(entry.aliases || [])
            .some(value => value.toLocaleLowerCase().indexOf(word) >= 0)));
}

function resolve(name, args, state) {
    const entry = exact(name);
    if (!entry) return { error: "unknown" };
    if (!available(entry, state)) return { error: "scope", scope: entry.scope };
    if (args.trim() && entry.kind !== "tool") return { error: "arguments" };
    return { entry: entry, arguments: args };
}

function title(entry) {
    if (!entry) return "";
    switch (entry.id) {
    case "mode.search": return qsTranslate("SpotlightCommands", "Default search");
    case "mode.apps": return qsTranslate("SpotlightCommands", "Apps");
    case "mode.wallpapers": return qsTranslate("SpotlightCommands", "Wallpapers");
    case "mode.clipboard": return qsTranslate("SpotlightCommands", "Clipboard");
    case "mode.files": return qsTranslate("SpotlightCommands", "Files");
    case "mode.commands": return qsTranslate("SpotlightCommands", "Commands");
    case "tool.web": return qsTranslate("SpotlightCommands", "Web search");
    case "tool.calculator": return qsTranslate("SpotlightCommands", "Calculator");
    case "tool.currency": return qsTranslate("SpotlightCommands", "Currency");
    case "tool.time": return qsTranslate("SpotlightCommands", "Time zone");
    case "theme.light": return qsTranslate("SpotlightCommands", "Light theme");
    case "theme.dark": return qsTranslate("SpotlightCommands", "Dark theme");
    case "settings.open": return qsTranslate("SpotlightCommands", "Open settings");
    case "tool.settings": return qsTranslate("SpotlightCommands", "Search settings");
    case "tool.actions": return qsTranslate("SpotlightCommands", "Search IPC actions");
    case "location.open": return qsTranslate("SpotlightCommands", "Location picker");
    case "apps.list": return qsTranslate("SpotlightCommands", "List");
    case "apps.grid": return qsTranslate("SpotlightCommands", "Grid");
    case "apps.smart": return qsTranslate("SpotlightCommands", "Smart");
    case "apps.most-used": return qsTranslate("SpotlightCommands", "Most used");
    case "apps.recent": return qsTranslate("SpotlightCommands", "Recently used");
    case "apps.name": return qsTranslate("SpotlightCommands", "Name");
    case "clipboard.compact": return qsTranslate("SpotlightCommands", "Compact");
    case "clipboard.detail": return qsTranslate("SpotlightCommands", "Details");
    default: return entry.title;
    }
}

.import "../../shared/i18n/Translations.js" as I18n
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
    case "mode.search": return I18n.tr("Default search", "SpotlightCommands");
    case "mode.apps": return I18n.tr("Apps", "SpotlightCommands");
    case "mode.wallpapers": return I18n.tr("Wallpapers", "SpotlightCommands");
    case "mode.clipboard": return I18n.tr("Clipboard", "SpotlightCommands");
    case "mode.files": return I18n.tr("Files", "SpotlightCommands");
    case "mode.commands": return I18n.tr("Commands", "SpotlightCommands");
    case "tool.web": return I18n.tr("Web search", "SpotlightCommands");
    case "tool.calculator": return I18n.tr("Calculator", "SpotlightCommands");
    case "tool.currency": return I18n.tr("Currency", "SpotlightCommands");
    case "tool.time": return I18n.tr("Time zone", "SpotlightCommands");
    case "theme.light": return I18n.tr("Light theme", "SpotlightCommands");
    case "theme.dark": return I18n.tr("Dark theme", "SpotlightCommands");
    case "settings.open": return I18n.tr("Open settings", "SpotlightCommands");
    case "tool.settings": return I18n.tr("Search settings", "SpotlightCommands");
    case "tool.actions": return I18n.tr("Search IPC actions", "SpotlightCommands");
    case "location.open": return I18n.tr("Location picker", "SpotlightCommands");
    case "apps.list": return I18n.tr("List", "SpotlightCommands");
    case "apps.grid": return I18n.tr("Grid", "SpotlightCommands");
    case "apps.smart": return I18n.tr("Smart", "SpotlightCommands");
    case "apps.most-used": return I18n.tr("Most used", "SpotlightCommands");
    case "apps.recent": return I18n.tr("Recently used", "SpotlightCommands");
    case "apps.name": return I18n.tr("Name", "SpotlightCommands");
    case "clipboard.compact": return I18n.tr("Compact", "SpotlightCommands");
    case "clipboard.detail": return I18n.tr("Details", "SpotlightCommands");
    default: return entry.title;
    }
}

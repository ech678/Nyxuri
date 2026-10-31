.pragma library

// PluginManifest — the manifest.toml vocabulary, validated in one place.
//
// Pure functions mirroring nyxuri/deploy/manifest.py (manifest-schema.md is
// the field authority): schemaVersion 1, root-derived id, closed kinds enum,
// entryPoints containment, settings routes/anchors and fixed actions. The
// registry feeds parsed TOML in and gets a normalised record or null back;
// every rejection is logged by the caller, never silently dropped.

var SCHEMA_VERSION = 1;

var KINDS = ["config", "edge", "island", "overlay", "drawer",
             "surface:desktop", "popup:notification", "service"];
var UI_KINDS = KINDS.filter(function (kind) {
    return kind !== "config";
});

var SETTINGS_KEYS = ["id", "title", "context", "icon", "source", "description",
                     "group", "order", "route", "aliases"];
var ACTION_KEYS = ["id", "target", "method", "args", "confirmation",
                   "availability", "search"];
var ACTION_SEARCH_KEYS = ["title", "description", "context", "icon", "aliases"];
var CONFIRMATIONS = ["none", "power-menu"];
var AVAILABILITY = ["always", "awww", "nyxuri-wallpaper", "wallpaper-idle",
                    "keystone", "keyboard-lock", "dock-previews"];

var _ID_RE = /^[a-zA-Z0-9][a-zA-Z0-9.:-]*$/;

function isString(value) {
    return typeof value === "string" && value.length > 0;
}

function isSafeRelPath(value) {
    // Mirrors the engine's is_safe_leaf_name per segment: inside the plugin
    // directory, no traversal, no absolute path, no control characters.
    if (typeof value !== "string" || !value || value.charAt(0) === "/")
        return false;
    var parts = value.replace(/\\/g, "/").split("/");
    for (var i = 0; i < parts.length; i++) {
        var part = parts[i];
        if (!part || part === "." || part === "..")
            return false;
        for (var j = 0; j < part.length; j++) {
            var code = part.charCodeAt(j);
            if (code < 32 || code === 127)
                return false;
        }
    }
    return true;
}

// Absolute file:// URL — Loader sources are never relative (loader-form.md):
// a relative source becomes a qs: URL and lands in the Quickshell 0.3.2
// dynamic-loading defect.
function fileUrl(path) {
    if (!path)
        return "";
    return "file://" + String(path).replace(/\\/g, "/").split("/").map(encodeURIComponent).join("/");
}

function _strList(value) {
    if (value === undefined || value === null)
        return [];
    if (typeof value === "string")
        return [value];
    if (Array.isArray(value))
        return value.filter(function (item) {
            return typeof item === "string";
        });
    return [];
}

function _validateKinds(raw, warn) {
    if (!Array.isArray(raw) || raw.length === 0) {
        warn("kinds must be a non-empty array");
        return null;
    }
    var seen = {};
    for (var i = 0; i < raw.length; i++) {
        if (KINDS.indexOf(raw[i]) === -1) {
            warn("unknown kind '" + raw[i] + "'");
            return null;
        }
        if (seen[raw[i]]) {
            warn("duplicate kind '" + raw[i] + "'");
            return null;
        }
        seen[raw[i]] = true;
    }
    return raw;
}

function _validateEntryPoints(raw, uiKinds, warn) {
    if (raw === undefined || raw === null)
        raw = {};
    if (typeof raw !== "object" || Array.isArray(raw)) {
        warn("entryPoints must be a table of kind = \"path\" entries");
        return null;
    }
    var keys = Object.keys(raw);
    if (keys.length !== uiKinds.length) {
        warn("entryPoints must declare exactly the ui kinds [" + uiKinds.join(", ") + "]");
        return null;
    }
    var out = {};
    for (var i = 0; i < uiKinds.length; i++) {
        var kind = uiKinds[i];
        var value = raw[kind];
        if (!isSafeRelPath(value)) {
            warn("unsafe entryPoint '" + kind + "'='" + value + "'");
            return null;
        }
        out[kind] = value;
    }
    return out;
}

function _validateSettings(raw, warn) {
    if (raw === undefined || raw === null)
        return [];
    if (!Array.isArray(raw)) {
        warn("settings must be an array of tables");
        return null;
    }
    var out = [];
    var seen = {};
    var routes = {};
    for (var i = 0; i < raw.length; i++) {
        var entry = raw[i];
        if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
            warn("each [[settings]] entry must be a table");
            return null;
        }
        var keys = Object.keys(entry);
        for (var k = 0; k < keys.length; k++) {
            if (SETTINGS_KEYS.indexOf(keys[k]) === -1) {
                warn("unknown [[settings]] key '" + keys[k] + "'");
                return null;
            }
        }
        var id = entry.id;
        if (!isString(id) || !_ID_RE.test(id)) {
            warn("invalid settings id '" + id + "'");
            return null;
        }
        if (seen[id]) {
            warn("duplicate settings id '" + id + "'");
            return null;
        }
        seen[id] = true;
        if (!isString(entry.title) || !isString(entry.context) || !isString(entry.icon)) {
            warn("settings '" + id + "' needs title, context and icon");
            return null;
        }
        var hasSource = entry.source !== undefined;
        if (hasSource === (entry.route !== undefined)) {
            warn("settings '" + id + "' must declare exactly one of source (route) or route (anchor)");
            return null;
        }
        var normalized = {
            id: id,
            title: entry.title,
            context: entry.context,
            icon: entry.icon,
            aliases: _strList(entry.aliases)
        };
        if (hasSource) {
            if (!isSafeRelPath(entry.source) || !/\.qml$/.test(entry.source)) {
                warn("settings '" + id + "' source must be a local QML filename");
                return null;
            }
            if (!isString(entry.description) || !isString(entry.group)) {
                warn("settings route '" + id + "' needs description and group");
                return null;
            }
            var order = entry.order === undefined ? 0 : entry.order;
            if (typeof order !== "number" || !isFinite(order)) {
                warn("settings '" + id + "' order must be an integer");
                return null;
            }
            normalized.source = entry.source;
            normalized.description = entry.description;
            normalized.group = entry.group;
            normalized.order = order;
            routes[id] = true;
        }
        out.push(normalized);
    }
    // Anchors weld to routes of the same manifest; nesting stays one deep.
    for (var j = 0; j < raw.length; j++) {
        var rawEntry = raw[j];
        if (rawEntry.route !== undefined) {
            if (!isString(rawEntry.route) || !routes[rawEntry.route]) {
                warn("settings '" + rawEntry.id + "' points at unknown route '" + rawEntry.route + "'");
                return null;
            }
            out[j].route = rawEntry.route;
        } else {
            var path = String(rawEntry.id).split(".");
            if (path.length > 2) {
                warn("settings '" + rawEntry.id + "' nests deeper than one level");
                return null;
            }
            if (path.length === 2 && !routes[path[0]]) {
                warn("settings '" + rawEntry.id + "' has no parent route '" + path[0] + "'");
                return null;
            }
            out[j].path = path;
        }
    }
    return out;
}

function _validateActions(raw, warn) {
    if (raw === undefined || raw === null)
        return [];
    if (!Array.isArray(raw)) {
        warn("actions must be an array of tables");
        return null;
    }
    var out = [];
    var seen = {};
    for (var i = 0; i < raw.length; i++) {
        var entry = raw[i];
        if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
            warn("each [[actions]] entry must be a table");
            return null;
        }
        var keys = Object.keys(entry);
        for (var k = 0; k < keys.length; k++) {
            if (ACTION_KEYS.indexOf(keys[k]) === -1) {
                warn("unknown [[actions]] key '" + keys[k] + "'");
                return null;
            }
        }
        var id = entry.id;
        if (!isString(id) || !_ID_RE.test(id)) {
            warn("invalid action id '" + id + "'");
            return null;
        }
        if (seen[id]) {
            warn("duplicate action id '" + id + "'");
            return null;
        }
        seen[id] = true;
        if (!isString(entry.target) || !isString(entry.method)) {
            warn("action '" + id + "' needs target and method");
            return null;
        }
        var confirmation = entry.confirmation === undefined ? "none" : entry.confirmation;
        if (CONFIRMATIONS.indexOf(confirmation) === -1) {
            warn("invalid confirmation for action '" + id + "'");
            return null;
        }
        if (entry.target === "power-menu" && confirmation !== "power-menu") {
            warn("power actions must open the existing confirmation UI: '" + id + "'");
            return null;
        }
        var availability = entry.availability === undefined ? "always" : entry.availability;
        if (AVAILABILITY.indexOf(availability) === -1) {
            warn("unknown availability for action '" + id + "'");
            return null;
        }
        var search = entry.search;
        if (!search || typeof search !== "object" || Array.isArray(search)) {
            warn("action '" + id + "' must declare a search table");
            return null;
        }
        var searchKeys = Object.keys(search);
        for (var s = 0; s < searchKeys.length; s++) {
            if (ACTION_SEARCH_KEYS.indexOf(searchKeys[s]) === -1) {
                warn("unknown action search key '" + searchKeys[s] + "': '" + id + "'");
                return null;
            }
        }
        if (!isString(search.title) || !isString(search.description)
                || !isString(search.context) || !isString(search.icon)) {
            warn("action '" + id + "' search needs title, description, context and icon");
            return null;
        }
        out.push({
            id: id,
            target: entry.target,
            method: entry.method,
            args: _strList(entry.args),
            confirmation: confirmation,
            availability: availability,
            search: {
                title: search.title,
                description: search.description,
                context: search.context,
                icon: search.icon,
                aliases: _strList(search.aliases)
            }
        });
    }
    return out;
}

// Normalise one parsed manifest into a record, or null when it fails any
// check. `expectedId` is the root-derived registry id; `sourceDir` is the
// plugin directory for entry point resolution.
function validate(raw, expectedId, sourceDir) {
    function warn(message) {
        console.warn("PluginManifest: " + message + " at " + sourceDir);
    }

    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        console.warn("PluginManifest: not a table at " + sourceDir);
        return null;
    }
    if (raw.schemaVersion !== SCHEMA_VERSION) {
        console.warn("PluginManifest: must declare schemaVersion = " + SCHEMA_VERSION
                     + " at " + sourceDir);
        return null;
    }
    if (raw.id !== expectedId) {
        console.warn("PluginManifest: id '" + raw.id + "' does not match the registry id '"
                     + expectedId + "' at " + sourceDir);
        return null;
    }
    var kinds = _validateKinds(raw.kinds, warn);
    if (!kinds)
        return null;
    var uiKinds = kinds.filter(function (kind) {
        return kind !== "config";
    });
    var entryPoints = _validateEntryPoints(raw.entryPoints, uiKinds, warn);
    if (!entryPoints)
        return null;
    var settings = _validateSettings(raw.settings, warn);
    if (!settings)
        return null;
    var actions = _validateActions(raw.actions, warn);
    if (!actions)
        return null;

    var order = raw.order === undefined ? 0 : raw.order;
    if (typeof order !== "number" || !isFinite(order)) {
        console.warn("PluginManifest: order must be an integer at " + sourceDir);
        return null;
    }
    var label = raw.label === undefined ? expectedId : raw.label;
    if (!isString(label)) {
        console.warn("PluginManifest: label must be a non-empty string at " + sourceDir);
        return null;
    }

    var entryUrls = {};
    for (var i = 0; i < uiKinds.length; i++)
        entryUrls[uiKinds[i]] = fileUrl(String(sourceDir).replace(/\/$/, "") + "/" + entryPoints[uiKinds[i]]);

    var settingsRoutes = [];
    var settingsAnchors = [];
    for (var j = 0; j < settings.length; j++) {
        var entry = settings[j];
        if (entry.source !== undefined) {
            entry.sourceUrl = fileUrl(String(sourceDir).replace(/\/$/, "") + "/" + entry.source);
            settingsRoutes.push(entry);
        } else {
            settingsAnchors.push(entry);
        }
    }

    return {
        id: expectedId,
        domain: String(sourceDir).replace(/\/$/, "").split("/").pop(),
        dir: String(sourceDir).replace(/\/$/, ""),
        label: label,
        kinds: kinds,
        order: order,
        entryPoints: entryPoints,
        entryUrls: entryUrls,
        settingsRoutes: settingsRoutes,
        settingsAnchors: settingsAnchors,
        actions: actions
    };
}

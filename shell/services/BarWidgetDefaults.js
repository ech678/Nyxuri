.pragma library

// Fork & Trim: dux-shell quickshell/Common/settings/BarWidgetDefaults.js
// (references/dux-shell, MIT, D4a). Kept: the per-widget DEFAULTS table and
// the option() fallback chain. Trimmed: the dux per-widget axes (island
// routing, workspace colors, tray expansion...) — Nyxuri widgets still read
// their flat bar.* axes through the Config bridge; D4b moves them into
// entry overrides one widget at a time, filling this table as it goes.
//
// This file is registration point 1 of 3 for a new bar widget (the others:
// shell/ui/BarWidgetCatalog.qml for label/icon, shell/plugins/bar/
// BarWidgetFiles.js for the component). IDS is also the storage-side
// whitelist: PersonalizationConfig normalizes lane entries against it, so
// an id missing here cannot be persisted, and an id missing from either of
// the other two registries fails the D4a contract test instead of silently
// rendering nothing.

// Canonical widget ids (the full renderable set, spacer/separator included).
var IDS = [
    "island",
    "clock",
    "tray",
    "systemMonitor",
    "weather",
    "visualizer",
    "battery",
    "systemIcons",
    "quickSettings",
    "utilButtons",
    "launcherButton",
    "powerButton",
    "workspaces",
    "activeWindow",
    "media",
    "separator",
    "spacer"
];

// Per-widget defaults. Every value must come from the design-system
// contract (llms-wiki/shell/design-system.md); the engine defines no
// aesthetics of its own.
var DEFAULTS = {
    // design-system spacing.largeIncreased
    spacer: {
        size: 20
    },
    separator: {},
    island: {},
    clock: {},
    tray: {},
    systemMonitor: {},
    weather: {},
    visualizer: {},
    battery: {},
    systemIcons: {},
    quickSettings: {},
    utilButtons: {},
    launcherButton: {},
    powerButton: {},
    workspaces: {},
    activeWindow: {},
    media: {}
};

// Third fallback layer for option(): keys valid for every widget.
var GLOBAL_DEFAULTS = {};

// Widgets that may appear at most once per bar. The island owns the
// notification-host slot; a second instance would steal islandHost and
// double its service consumers.
var SINGLETON_IDS = ["island"];

// Legacy widget ids (pre-D4a configs and end4 vendor names) -> canonical
// ids. Applied once at load/normalize time; never at render time.
var LEGACY_ID_ALIASES = {
    clockWidget: "clock",
    sysTray: "tray",
    resources: "systemMonitor",
    batteryIndicator: "battery",
    divider: "separator",
    divisor: "separator",
    dynamicIsland: "island"
};

function canonicalId(id) {
    const key = String(id || "");
    return LEGACY_ID_ALIASES[key] || key;
}

function isKnownId(id) {
    return IDS.indexOf(String(id || "")) !== -1;
}

// The single option entry point (D4a contract): widgets never read storage
// directly — the host injects their entry and every axis resolves through
// here. Layer order: entry override -> widget default -> global default.
function option(widgetId, entry, key) {
    if (entry && entry.overrides && entry.overrides[key] !== undefined)
        return entry.overrides[key];
    const defaults = DEFAULTS[widgetId];
    if (defaults && defaults[key] !== undefined)
        return defaults[key];
    return GLOBAL_DEFAULTS[key];
}

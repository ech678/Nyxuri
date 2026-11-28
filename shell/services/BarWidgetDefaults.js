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

// Per-widget defaults (D4b axes). Every default equals the pre-D4b
// behavior: migrated flat keys carry their shipped values, new axes
// default to the current visual (B-2/D-1 lineage). The engine defines no
// aesthetics of its own — changes here are config-visible and must ride
// a configVersion bump with a MIGRATED_GLOBALS entry.
var DEFAULTS = {
    // design-system spacing.largeIncreased
    spacer: {
        size: 20
    },
    // end4 divider contract: rect | dot | space; spacing is the
    // space-style width (even px, 4..400).
    separator: {
        style: "rect",
        spacing: 4
    },
    clock: {
        showDate: true,
        // Qt date pattern for the long form; empty keeps "dddd, dd/MM".
        dateFormat: "",
        clickAction: "none",
        middleClickAction: "none",
        rightClickAction: "none",
        // argv array — never a shell string (shell/AGENTS.md red line).
        clickCommand: []
    },
    // Tray-domain shared state (pinnedItems, invertPinnedItems) stays in
    // PersonalizationConfig [bar.tray]: pinning is one tray-wide fact, not
    // a per-instance aesthetic.
    tray: {
        tintIcons: true,
        hidePassive: true,
        showItemId: false
    },
    systemMonitor: {
        cpu: true,
        cpuTemp: false,
        ram: true,
        disk: false,
        swap: false,
        iconStyle: "outline",
        showValue: false
    },
    battery: {
        showPercent: true,
        showPower: false,
        clickAction: "none",
        middleClickAction: "none",
        rightClickAction: "none",
        clickCommand: []
    },
    media: {
        minWidth: 160,
        maxWidth: 300,
        showTitle: true,
        showArtist: true,
        showAlbumArt: true,
        alwaysVisible: false,
        scrollAction: "none"
    },
    activeWindow: {
        maxWidth: 280,
        showIcon: false,
        compactMode: false,
        hideWhenEmpty: false,
        clickAction: "none",
        middleClickAction: "none",
        rightClickAction: "none",
        clickCommand: []
    },
    weather: {
        // "default" keeps the built-in behavior (popup / right-refresh).
        clickAction: "default",
        middleClickAction: "default",
        rightClickAction: "default",
        clickCommand: []
    },
    launcherButton: {
        clickAction: "default",
        middleClickAction: "none",
        rightClickAction: "none",
        clickCommand: []
    },
    powerButton: {
        clickAction: "default",
        middleClickAction: "none",
        rightClickAction: "none",
        clickCommand: []
    },
    workspaces: {
        showAppIcons: false,
        alwaysShowNumbers: true,
        hideEmpty: false,
        invertScroll: false,
        monochromeIcons: false,
        indicatorStyle: "dot",
        style: "default",
        numberStyle: "normal",
        shown: 10,
        // State color modes (default skin only): theme | none | custom.
        // Custom hexes follow the M3 baseline palette (dux table values).
        activeColorMode: "theme",
        activeCustomColor: "#6750A4",
        occupiedColorMode: "theme",
        occupiedCustomColor: "#625B71"
    },
    island: {
        satellite: "clock",
        showAvatar: true,
        showMediaControls: false,
        visualizerStyle: "dots",
        hideDate: false
    },
    visualizer: {},
    systemIcons: {},
    utilButtons: {
        screenSnip: true,
        colorPicker: true,
        keyboardToggle: false,
        micToggle: false,
        wallpaperToggle: false,
        darkModeToggle: true,
        performanceProfile: false
    }
};

// quickSettings and utilButtons are one component (BarWidgetFiles maps
// both to UtilButtons.qml), so they share one axes table by reference —
// a change for one id is a change for both.
DEFAULTS.quickSettings = DEFAULTS.utilButtons;

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

// Workspace number glyphs (D4b, moved from PersonalizationConfig's derived
// property): numberStyle "han"/"roman" render 1-20 as their glyph maps;
// anything else falls back to plain digits.
var _NUMBER_HAN = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"];
var _NUMBER_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"];

function workspaceNumberMap(style) {
    if (style === "han")
        return _NUMBER_HAN;
    if (style === "roman")
        return _NUMBER_ROMAN;
    return [];
}

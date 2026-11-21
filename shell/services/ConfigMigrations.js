.pragma library

// config.toml version chain (D4a). The file carries its version in two
// places: the "# nyxuri-config-schema: N" header stamp (the fast-path
// probe in ConfigService) and the real configVersion key (added in v3).
// Every step receives the parsed file, mutates it in place and returns
// whether it changed anything. Steps must be idempotent and must preserve
// user keys they do not own.

// v2: the schema-2 file without a configVersion key (pre-D4a).
var LEGACY_VERSION = 2;
var CURRENT_VERSION = 4;

// Explicit key map for the v3 step (dux MIGRATED_GLOBALS pattern): the
// layout keys [[bar.configs]] supersedes. A key rename can never silently
// strand an old file — it has to be edited here.
var LEGACY_LAYOUT_KEYS = [
    "barLayoutLeft",
    "barLayoutMiddle",
    "barLayoutRight",
    "barLeadingComponents",
    "barTrailingComponents"
];

// v4 explicit key map (dux MIGRATED_GLOBALS pattern): per-widget axes
// move from the flat [bar] keys onto the lane entries themselves.
// Shape: widget id -> { entryKey: [section, flatKey] } with "" section
// meaning the key sits directly under [bar]. The clock dateFormat is the
// one axis that lived outside [bar] ([time]).
// A key rename can never silently strand an old file — it has to be
// edited here.
var MIGRATED_WIDGET_GLOBALS = {
    separator: {
        style: ["", "dividerStyle"],
        spacing: ["", "dividerSpacing"]
    },
    workspaces: {
        showAppIcons: ["", "showAppIcons"],
        alwaysShowNumbers: ["", "alwaysShowNumbers"],
        indicatorStyle: ["", "workspaceIndicatorStyle"],
        style: ["", "workspaceStyle"],
        numberStyle: ["", "numberStyle"],
        shown: ["", "workspaceShown"]
    },
    systemMonitor: {
        cpu: ["resources", "alwaysShowCpu"],
        cpuTemp: ["resources", "alwaysShowCpuTemp"],
        ram: ["resources", "alwaysShowRam"],
        disk: ["resources", "alwaysShowDisk"],
        swap: ["resources", "alwaysShowSwap"],
        iconStyle: ["resources", "style"],
        showValue: ["resources", "showValue"]
    },
    utilButtons: {
        screenSnip: ["utilButtons", "showScreenSnip"],
        colorPicker: ["utilButtons", "showColorPicker"],
        keyboardToggle: ["utilButtons", "showKeyboardToggle"],
        micToggle: ["utilButtons", "showMicToggle"],
        wallpaperToggle: ["utilButtons", "showWallpaperToggle"],
        darkModeToggle: ["utilButtons", "showDarkModeToggle"],
        performanceProfile: ["utilButtons", "showPerformanceProfile"]
    },
    tray: {
        tintIcons: ["tray", "monochromeIcons"],
        hidePassive: ["tray", "filterPassive"],
        showItemId: ["tray", "showItemId"]
    }
};

// quickSettings and utilButtons are one component (BarWidgetDefaults
// aliases their axes tables), so they share the migration map too — a
// quickSettings entry folds the utilButtons keys.
MIGRATED_WIDGET_GLOBALS.quickSettings = MIGRATED_WIDGET_GLOBALS.utilButtons;

// Runs every pending step. seed carries what the caller (who owns the pure
// resolve helpers and the widget whitelist) resolved from the legacy keys:
// { lanes: {left, middle, right}, allowedIds, defaults } — defaults is the
// BarWidgetDefaults.DEFAULTS table so the v4 step can skip default-equal
// values (a defaults-equal override would self-delete at write anyway).
function migrateConfig(parsed, seed) {
    const config = parsed && typeof parsed === "object" ? parsed : {};
    let version = Number(config.configVersion) || LEGACY_VERSION;
    let changed = false;
    if (version < 3) {
        changed = migrateBarConfigs(config, seed) || changed;
        version = 3;
        config.configVersion = version;
    }
    if (version < 4) {
        changed = migrateWidgetGlobals(config, seed) || changed;
        version = 4;
        config.configVersion = version;
    }
    return {
        config: config,
        changed: changed
    };
}

// v3: bar lane arrays become the [[bar.configs]] entry list. The caller
// already resolved the effective lanes (one-shot island seed, legacy
// leading/trailing zones); this step only reshapes them and strips the
// superseded keys. Entries serialize as plain strings: enabled/overrides
// did not exist pre-v3, so there is nothing else to carry.
function migrateBarConfigs(config, seed) {
    const bar = config.bar;
    if (!bar || typeof bar !== "object" || Array.isArray(bar))
        return false;

    let changed = false;
    if (Array.isArray(bar.configs)) {
        // Already v3-shaped (a stamped file that kept the key): only strip
        // any legacy layout keys that rode along.
        changed = stripLegacyLayoutKeys(bar);
    } else {
        const lanes = seed && seed.lanes ? seed.lanes : {};
        bar.configs = [{
            id: "default",
            name: "Bar",
            lanes: {
                left: strings(lanes.left),
                middle: strings(lanes.middle),
                right: strings(lanes.right)
            }
        }];
        // The configs key itself is the change; stripping any legacy keys
        // that rode along only adds to it.
        stripLegacyLayoutKeys(bar);
        changed = true;
    }
    return changed;
}

function stripLegacyLayoutKeys(bar) {
    let changed = false;
    for (let i = 0; i < LEGACY_LAYOUT_KEYS.length; i++) {
        const key = LEGACY_LAYOUT_KEYS[i];
        if (bar[key] !== undefined) {
            delete bar[key];
            changed = true;
        }
    }
    return changed;
}

function strings(values) {
    return Array.isArray(values) ? values.map(value => String(value)) : [];
}

// v4 (dux migrateBarWidgetGlobals semantics): per-widget flat keys fold
// onto every lane entry of that widget. Deviations copy onto the entry
// (default-equal values skip — the minimal writer would drop them); keys
// already present on an entry win; the superseded globals are stripped
// afterwards. Idempotent by construction: after one run the globals are
// gone, and entries only ever gain keys they did not have.
function migrateWidgetGlobals(config, seed) {
    const bar = config.bar;
    if (!bar || typeof bar !== "object" || Array.isArray(bar) || !Array.isArray(bar.configs))
        return false;
    const defaults = seed && seed.defaults ? seed.defaults : {};
    let touched = false;

    // [time].dateFormat is the one migrated axis outside [bar].
    const timeSection = config.time && typeof config.time === "object" ? config.time : null;
    const legacyDateFormat = timeSection && typeof timeSection.dateFormat === "string" ? timeSection.dateFormat : "";

    for (let b = 0; b < bar.configs.length; b++) {
        const lanes = bar.configs[b] && bar.configs[b].lanes;
        if (!lanes || typeof lanes !== "object")
            continue;
        for (const zone of ["left", "middle", "right"]) {
            const lane = lanes[zone];
            if (!Array.isArray(lane))
                continue;
            for (let i = 0; i < lane.length; i++) {
                const raw = lane[i];
                const id = typeof raw === "string" ? raw : (raw && typeof raw === "object" ? raw.id : null);
                const map = MIGRATED_WIDGET_GLOBALS[id];
                const wantsDateFormat = id === "clock" && legacyDateFormat !== "" && legacyDateFormat !== (defaults.clock ? defaults.clock.dateFormat : undefined);
                if (!map && !wantsDateFormat)
                    continue;
                const entry = typeof raw === "string" ? {
                    id: raw
                } : raw;
                let copied = false;
                for (const entryKey in map) {
                    const section = map[entryKey][0] === "" ? bar : (bar[map[entryKey][0]] && typeof bar[map[entryKey][0]] === "object" ? bar[map[entryKey][0]] : null);
                    if (!section)
                        continue;
                    const value = section[map[entryKey][1]];
                    if (value === undefined || entry[entryKey] !== undefined)
                        continue;
                    if (defaults[id] && defaults[id][entryKey] !== undefined && value === defaults[id][entryKey])
                        continue;
                    entry[entryKey] = value;
                    copied = true;
                }
                if (wantsDateFormat && entry.dateFormat === undefined) {
                    entry.dateFormat = legacyDateFormat;
                    copied = true;
                }
                if (copied) {
                    lane[i] = entry;
                    touched = true;
                }
            }
        }
    }

    // Strip the superseded globals (nested tables too — an emptied table
    // is left for the minimal writer to drop).
    for (const widgetId in MIGRATED_WIDGET_GLOBALS) {
        const map = MIGRATED_WIDGET_GLOBALS[widgetId];
        for (const entryKey in map) {
            const sectionKey = map[entryKey][0];
            const section = sectionKey === "" ? bar : (bar[sectionKey] && typeof bar[sectionKey] === "object" ? bar[sectionKey] : null);
            if (section && section[map[entryKey][1]] !== undefined) {
                delete section[map[entryKey][1]];
                touched = true;
            }
        }
    }
    if (timeSection && timeSection.dateFormat !== undefined) {
        delete timeSection.dateFormat;
        touched = true;
    }
    return touched;
}

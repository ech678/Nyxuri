.pragma library

// config.toml version chain (D4a). The file carries its version in two
// places: the "# nyxuri-config-schema: N" header stamp (the fast-path
// probe in ConfigService) and the real configVersion key (added in v3).
// Every step receives the parsed file, mutates it in place and returns
// whether it changed anything. Steps must be idempotent and must preserve
// user keys they do not own.

// v2: the schema-2 file without a configVersion key (pre-D4a).
var LEGACY_VERSION = 2;
var CURRENT_VERSION = 3;

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

// Runs every pending step. seed carries what the caller (who owns the pure
// resolve helpers and the widget whitelist) resolved from the legacy keys:
// { lanes: {left, middle, right}, allowedIds }.
function migrateConfig(parsed, seed) {
    const config = parsed && typeof parsed === "object" ? parsed : {};
    let version = Number(config.configVersion) || LEGACY_VERSION;
    let changed = false;
    if (version < 3) {
        changed = migrateBarConfigs(config, seed) || changed;
        version = 3;
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

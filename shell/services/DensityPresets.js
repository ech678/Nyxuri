.pragma library

// Fork & Trim: dux-shell quickshell/Common/settings/DensityPresets.js
// (references/dux-shell, MIT, D4e e6). Kept: LEVELS + value/values/
// transition. Adapted: surface keys mapped to Nyxuri's BarDefaults axes
// (barThickness, verticalThickness, innerPadding, widgetPadding, spacing,
// iconScale), with "comfortable" matching the shipped defaults 1:1.

var LEVELS = ["spacious", "comfortable", "compact", "dense"];

// Indexed in LEVELS order.
var PRESETS = {
    bar: {
        barThickness: [42, 36, 32, 28],
        verticalThickness: [42, 36, 32, 28],
        innerPadding: [10, -1, 4, 2],
        widgetPadding: [8, -1, 4, 2],
        spacing: [6, -1, 2, 0],
        iconScale: [1.15, 1.0, 0.9, 0.85]
    }
};

function value(surface, key, density) {
    var row = PRESETS[surface] && PRESETS[surface][key];
    var index = LEVELS.indexOf(density);
    return row && index >= 0 ? row[index] : undefined;
}

function values(surface, density) {
    var out = {};
    for (var key in PRESETS[surface] || {}) {
        var preset = value(surface, key, density);
        if (preset !== undefined)
            out[key] = preset;
    }
    return out;
}

// Returns the matching level name when every preset key equals that level,
// or "" when the user customized away from all presets.
function currentLevel(surface, axes) {
    if (!axes)
        return "";
    for (var i = 0; i < LEVELS.length; i++) {
        var level = LEVELS[i];
        var matched = true;
        for (var key in PRESETS[surface] || {}) {
            var expected = value(surface, key, level);
            if (axes[key] !== expected) {
                matched = false;
                break;
            }
        }
        if (matched)
            return level;
    }
    return "";
}

// Only fields missing or still on the outgoing preset move; anything else is user-set.
function transition(config, surface, from, to) {
    if (from === to || LEVELS.indexOf(from) < 0 || LEVELS.indexOf(to) < 0 || !config)
        return null;
    var out = null;
    for (var key in PRESETS[surface] || {}) {
        var current = config[key];
        if (current !== undefined && current !== value(surface, key, from))
            continue;
        out = out || Object.assign({}, config);
        out[key] = value(surface, key, to);
    }
    return out;
}

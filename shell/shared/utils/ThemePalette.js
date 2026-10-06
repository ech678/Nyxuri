/*
 * Nyxuri theme palette derivation — the single place that knows how the
 * internal 50-token M3 palette maps onto terminal tokens and the Noctalia
 * 16-role palette JSON. Pure computation: no I/O, no environment access.
 *
 * Derivation rules were reverse-engineered against Noctalia 5.2.1 golden
 * outputs (shell/tests/fixtures/theme/golden) and hold for tonal-spot,
 * fruit-salad, rainbow and monochrome schemes; m3-content diverges on the
 * three on_*_container keys (engine-internal post-processing, measured in
 * the color-diff harness). The two computed light-mode terminal variants
 * land within ΔE00 ≤ 1.0 of the reference (their HCT solver quantizes
 * slightly differently); every other token is byte-identical.
 */
.pragma library

.import "ThemeColor.js" as ThemeColor

// Terminal ANSI roles, expressed as internal palette token names.
// magenta/cyan bind to surface_tint/secondary_fixed_dim (they part ways
// from primary/secondary under the content scheme); green/blue carry
// Noctalia's role choice (primary/tertiary), not RGB hues.
var TERMINAL_ROLES = {
    "terminal_background": "surface",
    "terminal_foreground": "on_surface",
    "terminal_cursor": "on_surface",
    "terminal_cursor_text": "surface",
    "terminal_selection_bg": "surface_variant",
    "terminal_selection_fg": "on_surface_variant",
    "terminal_normal_black": "surface_variant",
    "terminal_normal_red": "error",
    "terminal_normal_green": "primary",
    "terminal_normal_yellow": "secondary",
    "terminal_normal_blue": "tertiary",
    "terminal_normal_magenta": "surface_tint",
    "terminal_normal_cyan": "secondary_fixed_dim",
    "terminal_normal_white": "on_surface",
    "terminal_bright_black": "outline",
    "terminal_bright_red": "error",
    "terminal_bright_green": "primary",
    "terminal_bright_yellow": "secondary",
    "terminal_bright_blue": "tertiary",
    "terminal_bright_magenta": "surface_tint",
    "terminal_bright_cyan": "secondary_fixed_dim",
    "terminal_bright_white": "on_surface"
};

// Light mode re-anchors magenta/cyan to the dark palette's surface tint /
// secondary fixed-dim at a fixed tone, so ANSI pink/teal stay readable on
// light backgrounds.
var LIGHT_TERMINAL_TONE = 48.4;
var LIGHT_TERMINAL_VARIANTS = {
    "terminal_normal_magenta": "surface_tint",
    "terminal_normal_cyan": "secondary_fixed_dim",
    "terminal_bright_magenta": "surface_tint",
    "terminal_bright_cyan": "secondary_fixed_dim"
};

// Noctalia custom-palette 16 roles in terms of internal token names.
var NOCTALIA_ROLES = {
    "mPrimary": "primary",
    "mOnPrimary": "on_primary",
    "mSecondary": "secondary",
    "mOnSecondary": "on_secondary",
    "mTertiary": "tertiary",
    "mOnTertiary": "on_tertiary",
    "mError": "error",
    "mOnError": "on_error",
    "mSurface": "surface",
    "mOnSurface": "on_surface",
    "mSurfaceVariant": "surface_variant",
    "mOnSurfaceVariant": "on_surface_variant",
    "mOutline": "outline",
    "mShadow": "shadow",
    "mHover": "tertiary",
    "mOnHover": "on_tertiary"
};

function isValidHex(value) {
    return typeof value === "string" && ThemeColor.argbFromHex(value) !== 0;
}

/**
 * Derives the 22 terminal tokens for one mode from the internal palette
 * (snake_case token → #rrggbb). Returns {} with no throw so callers can
 * decide how to surface an incomplete palette; missing tokens are skipped.
 */
function terminalTokens(palette, mode) {
    const result = {};
    for (const token in TERMINAL_ROLES) {
        const source = LIGHT_TERMINAL_VARIANTS[token];
        if (mode === "light" && source) {
            const darkValue = palette[source];
            if (!isValidHex(darkValue)) {
                continue;
            }
            const hct = ThemeColor.hueChromaOf(darkValue);
            result[token] = ThemeColor.hexFromHueChromaTone(hct.hue, hct.chroma,
                                                            LIGHT_TERMINAL_TONE);
            continue;
        }
        const value = palette[TERMINAL_ROLES[token]];
        if (isValidHex(value)) {
            result[token] = value;
        }
    }
    return result;
}

/**
 * Extends one mode palette with its 22 derived terminal tokens.
 */
function paletteWithTerminals(palette, mode) {
    const merged = {};
    for (const token in palette) {
        merged[token] = palette[token];
    }
    const terminals = terminalTokens(palette, mode);
    for (const token in terminals) {
        merged[token] = terminals[token];
    }
    return merged;
}

/**
 * Builds the Noctalia custom-palette JSON body from both mode palettes
 * (snake_case → #rrggbb). Emits the 16 roles plus the terminal section per
 * mode; missing tokens are skipped so a partial palette never renders as a
 * wrong color.
 */
function noctaliaPaletteJson(darkPalette, lightPalette) {
    const body = {};
    const modes = [{ "key": "dark", "palette": darkPalette },
                   { "key": "light", "palette": lightPalette }];
    for (let i = 0; i < modes.length; i++) {
        const mode = modes[i].key;
        const palette = modes[i].palette || {};
        const section = {};
        for (const role in NOCTALIA_ROLES) {
            const value = palette[NOCTALIA_ROLES[role]];
            if (isValidHex(value)) {
                section[role] = value;
            }
        }
        const terminals = terminalTokens(palette, mode);
        const terminalSection = {};
        for (const token in terminals) {
            const shortName = token.substring("terminal_".length);
            terminalSection[shortName] = terminals[token];
        }
        section["terminal"] = terminalSection;
        body[mode] = section;
    }
    return body;
}

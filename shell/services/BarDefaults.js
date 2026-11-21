.pragma library

// D4c bar-level axes (bar-config.md). The truth lives on the
// [[bar.configs]] entry (flat keys next to id/name/lanes); this table is
// the defaults source and the single sentinel-resolution point.
//
// Iron rule (ROADMAP D4c): every default preserves the pre-D4c visual.
// Geometry axes default to the sentinel -1 ("auto"), which resolves to the
// per-style baseline this file carries (the values that used to be
// hardcoded in BarContent/BarGroup). A fresh config writes zero axes; an
// explicit value overrides exactly one thing. Key renames ride the
// configVersion chain (ConfigMigrations MIGRATED_BAR_GLOBALS).

// Defaults table. Types are the storage truth: -1/"default" sentinels mean
// "follow the style baseline", 1.0 scales are multipliers, colors are role
// names or #rrggbb hexes.
var DEFAULTS = {
    // Migrated v5 keys (pre-D4c flat [bar] keys, same names, pure move).
    position: "top",
    autoHide: false,
    screenList: [],
    showBackground: true,
    cornerStyle: 1,
    borderless: "pills",
    groupColor: "layer1",
    barThickness: 36,
    verticalThickness: 36,
    edgeMargin: 0,
    sideMargin: 0,
    // D4c geometry axes (sentinel -1 = per-style baseline).
    spacing: -1,
    innerPadding: -1,
    widgetPadding: -1,
    // Percent length: 0 keeps the full-width bar (sideMargin px applies);
    // a nonzero value is the EACH-SIDE margin in percent of the screen
    // (bar = centered on the rest), absorbing dux barLengthMode/Percent.
    sideMarginPercent: 0,
    // Shape axes.
    squareCorners: false,
    radius: -1,
    // Content scaling (multiplier over the NexusStyle type scale). The
    // icon twin is D4e density material: bar icon slots are end4-baseline
    // literals (97 sites), not type-scale reads.
    fontScale: 1.0,
    // Bar surface (the bar's own background shell).
    surfaceColor: "default",
    surfaceTransparency: -1,
    // Bar surface border.
    borderEnabled: false,
    borderColor: "outlineVariant",
    borderOpacity: 1.0,
    borderThickness: 1,
    // Widget layer (the group capsule chrome).
    widgetTransparency: 1.0,
    widgetOutlineEnabled: false,
    widgetOutlineColor: "outline",
    widgetOutlineOpacity: 1.0,
    widgetOutlineThickness: 1,
    // D4d behavior axes (bar-config.md D4d). Defaults preserve the pre-D4d
    // behavior exactly: hide-on-leave is immediate (delay 0), popups pin
    // the reveal (strict off), the bar stays on the Top layer under
    // fullscreen windows, the whole bar eats input, and widget popouts
    // open on hover — the ONE deliberate change is the intent timing:
    // hoverPopoutDelay 150 per the D4d decision (the old 400ms was a
    // StyledPopup hardcode, not a ratified default).
    autoHideDelay: 0,
    autoHideStrict: false,
    hideOnFullscreen: false,
    clickThrough: false,
    hoverPopouts: true,
    hoverPopoutDelay: 150,
    // Per-lane overflow default (the "section" fallback of the per-widget
    // overflowMode entry axis): "auto" = widgets may leave the bar into the
    // lane's overflow popout when space runs out, "bar" = the lane never
    // overflows. Lane names follow the Nyxuri vocabulary (middle, not dux's
    // center).
    leftOverflowMode: "auto",
    middleOverflowMode: "auto",
    rightOverflowMode: "auto"
    // NOTE (registered boundary): the dux shadow axes (intensity/opacity/
    // color/direction) are D4e material — they ride dux's Frame wing
    // geometry (a window larger than the bar), which we do not have; a
    // shadow drawn inside today's window would clip against the screen
    // edge. They return with the window-growth infrastructure.
};

// Axis keys that are NOT style/geometry (behavior or screen routing) —
// kept on the entry for D4e multi-bar, but never resolved through the
// style math below.
var BEHAVIOR_KEYS = [
    "position",
    "autoHide",
    "autoHideDelay",
    "autoHideStrict",
    "hideOnFullscreen",
    "clickThrough",
    "hoverPopouts",
    "hoverPopoutDelay",
    "leftOverflowMode",
    "middleOverflowMode",
    "rightOverflowMode",
    "screenList"
];

// Lane overflow-mode vocabulary (D4d): the per-lane default the per-widget
// "section" overflowMode falls back to.
var LANE_OVERFLOW_MODES = ["auto", "bar"];

// borderless vocabulary gains "flat" in D4c: no capsule backgrounds at
// all (bare widgets on the bar surface — the old "transparent" keeps its
// capsule geometry with a transparent fill, a different look).
var BORDERLESS_MODES = ["pills", "separated", "segmented", "transparent", "flat"];

// Sentinel: the axis follows the per-style baseline.
function isAuto(value) {
    return value === -1 || value === "default" || value === undefined || value === null;
}

// Baseline helpers over the pre-D4c hardcoded geometry (end4 lineage,
// forked from BarContent/BarGroup). style = {cornerStyle, borderless,
// vertical} exactly as the consumers know it; gapsOut is the end4
// hyprland gap (Appearance.sizes.hyprlandGapsOut, 5).

// Widget-to-widget spacing inside a lane (BarContent.rowSpacing /
// VerticalBarContent.laneSpacing — the vertical bar pulls tighter).
function spacingBaseline(style) {
    const borderless = style.borderless;
    if (borderless === "transparent")
        return style.vertical ? -4 : -7;
    if (borderless === "segmented")
        return style.panel ? 3 : (style.vertical ? -2 : -1);
    if (style.panel)
        return 4;
    return 2;
}

// Lane inset from the bar ends (BarContent.laneMargin).
function innerPaddingBaseline(style) {
    if (style.materialHug)
        return 0;
    if (style.material)
        return style.gapsOut;
    if (style.cornerStyle === 1 || style.panel)
        return 4;
    return 8;
}

// Group capsule padding (BarGroup.padding). paintMaterialPill is the
// material per-widget pill flag (BarContent.shouldPaintMaterialPill).
function widgetPaddingBaseline(style, paintMaterialPill) {
    if (style.material && !paintMaterialPill)
        return 0;
    return 5;
}

// Resolved axis accessors: entry axes value or the baseline when the
// sentinel is stored. Consumers never branch on sentinels themselves.
function resolvedSpacing(axes, style) {
    const value = axes ? axes.spacing : undefined;
    return isAuto(value) ? spacingBaseline(style) : value;
}

function resolvedInnerPadding(axes, style) {
    const value = axes ? axes.innerPadding : undefined;
    return isAuto(value) ? innerPaddingBaseline(style) : value;
}

function resolvedWidgetPadding(axes, style, paintMaterialPill) {
    const value = axes ? axes.widgetPadding : undefined;
    return isAuto(value) ? widgetPaddingBaseline(style, paintMaterialPill) : value;
}

// Corner resolution: an explicit radius wins (the user set a number, they
// get the number), squareCorners flattens the style-derived value, -1
// keeps it (dux squareCorners semantics).
function resolvedRadius(axes, styleRadius) {
    if (axes && !isAuto(axes.radius))
        return axes.radius;
    if (axes && axes.squareCorners === true)
        return 0;
    return styleRadius;
}

// A color axis is either a palette role name or a hex; "default"/"" mean
// the consuming surface's own role chain.
function isCustomColor(value) {
    return typeof value === "string" && /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(value);
}

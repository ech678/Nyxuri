.pragma library

// D4c/D4f bar-level axes (bar-config.md). The truth lives on the
// [[bar.configs]] entry (flat keys next to id/name/lanes); this table is
// the defaults source and the single sentinel-resolution point.
//
// Iron rule (ROADMAP D4c/D4f): every default preserves the pre-D4c visual
// (Floating bar: 5px edgeMargin, Auto -1 sideMargin -> 5px, backplate on).
// Geometry axes default to the sentinel -1 ("auto"), which resolves to the
// derived baseline this file carries. A fresh config writes zero axes; an
// explicit value overrides exactly one thing. Key renames ride the
// configVersion chain (ConfigMigrations).

var WIDGET_STYLES = ["fused", "separate", "flat"];
var CAPSULE_RADII = ["pill", "rounded", "px"];
var GROUP_COLORS = ["primaryContainer", "secondaryContainer", "tertiaryContainer", "surfaceContainerLowest", "surfaceContainerLow", "surfaceContainer", "surfaceContainerHigh", "surfaceContainerHighest", "layer1", "layer0", "transparent"];
var LENGTH_MODES = ["full", "fit"];
var SCROLL_ACTIONS = ["brightness", "volume", "workspace", "none"];

// Defaults table. Types are the storage truth: -1/"default" sentinels mean
// "follow the derived baseline", 1.0 scales are multipliers, colors are role
// names or #rrggbb hexes.
var DEFAULTS = {
    // Routing & layout
    position: "top",
    autoHide: false,
    screenList: [],
    // D4f atomic style & composition axes (replaces cornerStyle/borderless/showBackground)
    backplate: true,
    lanePill: false,
    tint: false,
    widgetStyle: "fused",
    capsuleRadius: "pill",
    widgetRadius: -1,
    groupColor: "layer1",
    // Geometry & margins (edgeMargin 0 = edge-flush, > 0 = floating;
    // sideMargin -1 = Auto -> gapsOut on floating backplate, 0 otherwise).
    barThickness: 36,
    verticalThickness: 36,
    edgeMargin: 5,
    sideMargin: -1,
    // D4c geometry axes (sentinel -1 = derived baseline).
    spacing: -1,
    innerPadding: -1,
    widgetPadding: -1,
    // Percent length: 0 keeps the full-width/sideMargin bar; a nonzero value
    // is the EACH-SIDE margin in percent of the screen (centered bar).
    sideMarginPercent: 0,
    lengthMode: "full",
    // Shape axes.
    squareCorners: false,
    radius: -1,
    // Content scaling (multiplier over the NexusStyle type scale / icon baseline).
    fontScale: 1.0,
    iconScale: 1.0,
    // Bar overall opacity, blur, and surface (the bar's own background shell).
    barOpacity: 1.0,
    blurEnabled: true,
    surfaceColor: "default",
    surfaceTransparency: -1,
    // Bar surface border.
    borderEnabled: false,
    borderColor: "outlineVariant",
    borderOpacity: 1.0,
    borderThickness: 1,
    // Widget layer (the group capsule chrome & foreground text).
    widgetTransparency: 1.0,
    capsuleVerticalInset: 4,
    widgetTextColor: "default",
    widgetOutlineEnabled: false,
    widgetOutlineColor: "outline",
    widgetOutlineOpacity: 1.0,
    widgetOutlineThickness: 1,
    // Edge scroll actions & hints.
    leftScrollAction: "brightness",
    rightScrollAction: "volume",
    showScrollHints: true,
    // D4d behavior axes (bar-config.md D4d).
    autoHideDelay: 0,
    autoHideStrict: false,
    hideOnFullscreen: false,
    clickThrough: false,
    hoverPopouts: true,
    hoverPopoutDelay: 150,
    // D4h behavior additions (bar-config.md D4h). Every default is the
    // pre-D4h behavior: smart off, no reservation reveal, no super reveal,
    // no workspace-switch peek.
    autoHideSmart: false,
    pushWindows: false,
    superReveal: false,
    peekOnWorkspaceSwitch: false,
    // Per-lane overflow default ("auto" or "bar").
    leftOverflowMode: "auto",
    middleOverflowMode: "auto",
    rightOverflowMode: "auto"
    // NOTE (registered boundary): the dux shadow axes (intensity/opacity/
    // color/direction) are D5 window-growth material — they ride a window
    // larger than the bar and clip against the screen edge today.
};

// Axis keys that are NOT style/geometry (behavior or screen routing).
var BEHAVIOR_KEYS = [
    "position",
    "autoHide",
    "autoHideDelay",
    "autoHideStrict",
    "autoHideSmart",
    "pushWindows",
    "superReveal",
    "peekOnWorkspaceSwitch",
    "hideOnFullscreen",
    "clickThrough",
    "hoverPopouts",
    "hoverPopoutDelay",
    "leftOverflowMode",
    "middleOverflowMode",
    "rightOverflowMode",
    "screenList"
];

// D4h internal behavior timings (bar-config.md D4h). Deliberately not axes:
// one cadence for every bar, no settings rows. The super delay carries over
// the bridge's historical 100ms; the peek cadence follows the noctalia
// show_on_workspace_switch reference (80ms debounce / 450ms stay).
var SUPER_REVEAL_DELAY_MS = 100;
var PEEK_DEBOUNCE_MS = 80;
var PEEK_STAY_MS = 450;

var LANE_OVERFLOW_MODES = ["auto", "bar"];

// Sentinel: the axis follows the derived baseline.
function isAuto(value) {
    return value === -1 || value === "default" || value === undefined || value === null;
}

// Pure geometric derivation of bar style flags from the atomic axes.
// Used by PersonalizationConfig (services/) and BarStyle.js (plugins/bar/).
function deriveStyle(axes, gapsOut) {
    const a = axes || DEFAULTS;
    const gap = gapsOut !== undefined ? gapsOut : 5;
    const edgeMargin = typeof a.edgeMargin === "number" ? a.edgeMargin : DEFAULTS.edgeMargin;
    const backplate = a.backplate !== false;
    const lanePill = a.lanePill === true;
    const tint = a.tint === true;
    const widgetStyle = WIDGET_STYLES.indexOf(a.widgetStyle) !== -1 ? a.widgetStyle : DEFAULTS.widgetStyle;
    const capsuleRadius = CAPSULE_RADII.indexOf(a.capsuleRadius) !== -1 ? a.capsuleRadius : DEFAULTS.capsuleRadius;
    const groupColor = typeof a.groupColor === "string" && a.groupColor !== "" ? a.groupColor : DEFAULTS.groupColor;
    const squareCorners = a.squareCorners === true;
    const isFloating = edgeMargin > 0;
    const isEdgeFlush = !isFloating;
    const isLaneHug = lanePill && !backplate && isEdgeFlush;
    const isSeparated = widgetStyle === "separate";
    const isFlat = widgetStyle === "flat";
    const isTransparent = groupColor === "transparent";
    const isSegmented = widgetStyle === "fused" && a.widgetOutlineEnabled === true && !isTransparent && !tint;
    return {
        backplate: backplate,
        lanePill: lanePill,
        tint: tint,
        widgetStyle: widgetStyle,
        capsuleRadius: capsuleRadius,
        groupColor: groupColor,
        squareCorners: squareCorners,
        edgeMargin: edgeMargin,
        gapsOut: gap,
        isFloating: isFloating,
        isEdgeFlush: isEdgeFlush,
        isLaneHug: isLaneHug,
        isSeparated: isSeparated,
        isFlat: isFlat,
        isTransparent: isTransparent,
        isSegmented: isSegmented
    };
}

// D-8: Only edge-hugging lane pills keep the +4 boost for their internal
// outward RoundCorner decorators. Islands (-6) and Panel (+4) retired;
// Float's edge gap lives directly in edgeMargin/sideMargin (no double boost).
function styleBoost(style) {
    return style && style.isLaneHug ? 4 : 0;
}

function resolvedSideMargin(axes, style, gapsOut) {
    const value = axes ? axes.sideMargin : undefined;
    if (!isAuto(value))
        return value;
    const s = style || deriveStyle(axes, gapsOut);
    return (s.backplate && s.isFloating) ? s.gapsOut : 0;
}

// Widget-to-widget spacing inside a lane.
function spacingBaseline(style) {
    if (style.isTransparent)
        return style.vertical ? -4 : -7;
    if (style.isSegmented)
        return style.squareCorners ? 3 : (style.vertical ? -2 : -1);
    if (style.lanePill)
        return 3;
    if (style.squareCorners)
        return 4;
    return 2;
}

// Lane inset from the bar ends.
function innerPaddingBaseline(style) {
    if (style.isLaneHug)
        return 0;
    if (style.lanePill)
        return style.gapsOut;
    if (style.isFloating || style.squareCorners)
        return 4;
    return 8;
}

// Group capsule padding.
function widgetPaddingBaseline(style, paintMaterialPill) {
    if (style.tint && !paintMaterialPill)
        return 0;
    return 5;
}

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

// Corner resolution: explicit radius wins, squareCorners flattens, -1 keeps styleRadius.
function resolvedRadius(axes, styleRadius) {
    if (axes && !isAuto(axes.radius))
        return axes.radius;
    if (axes && axes.squareCorners === true)
        return 0;
    return styleRadius;
}

function capsuleFullRadius(style, height, panelRadius, customRadius) {
    const mode = style ? style.capsuleRadius : "pill";
    if (mode === "rounded")
        return panelRadius;
    if (mode === "px")
        return customRadius >= 0 ? customRadius : 8;
    return height / 2;
}

function capsuleMidRadius(style, unsharpenmore, panelRadius, customRadius) {
    if (!style)
        return unsharpenmore;
    if (style.isSegmented)
        return 0;
    if (style.capsuleRadius === "rounded")
        return style.squareCorners ? panelRadius : unsharpenmore;
    if (style.capsuleRadius === "px")
        return customRadius >= 0 ? customRadius : 8;
    return customRadius >= 0 ? customRadius : unsharpenmore;
}

function isCustomColor(value) {
    return typeof value === "string" && /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(value);
}

.pragma library

.import "../../services/BarDefaults.js" as BarDefaults

// Pure bar style resolver (D4f): derives all window, host, capsule,
// island and popup styling from the atomic axes via BarDefaults.deriveStyle.

function resolve(axes, env) {
    const a = axes || {};
    const e = env || {};
    const gapsOut = e.gapsOut !== undefined ? e.gapsOut : 5;
    const shellRadius = e.shellRadius !== undefined ? e.shellRadius : 0;
    const centerOnly = e.centerOnly === true;
    const d = BarDefaults.deriveStyle(a, gapsOut);

    const backplate = d.backplate;
    const lanePill = d.lanePill;
    const tint = d.tint;
    const isFloating = d.isFloating;
    const isEdgeFlush = d.isEdgeFlush;
    const isLaneHug = d.isLaneHug;
    const isSquare = d.squareCorners;

    // Screen-corner fusion decorators require edge-flush placement and a
    // nonzero shell corner radius (squareCorners / radius:0 turns them off).
    const canFuseScreen = isEdgeFlush && shellRadius > 0;

    return {
        backplate: backplate,
        lanePill: lanePill,
        tint: tint,
        widgetStyle: d.widgetStyle,
        capsuleRadius: d.capsuleRadius,
        groupColor: d.groupColor,
        isFloating: isFloating,
        isEdgeFlush: isEdgeFlush,
        isLaneHug: isLaneHug,
        isSquare: isSquare,
        isSeparated: d.isSeparated,
        isFlat: d.isFlat,
        isTransparent: d.isTransparent,
        isSegmented: d.isSegmented,
        boostExtra: BarDefaults.styleBoost(d),
        showBackplateFill: !centerOnly && backplate,
        showCenterPill: centerOnly && backplate && !lanePill,
        showScreenDecorators: canFuseScreen && ((backplate && !centerOnly) || isLaneHug),
        showCenterPillCorners: canFuseScreen && backplate && !lanePill && centerOnly,
        decoratorUsesBackplate: isLaneHug || backplate,
        showStartDecorator: canFuseScreen && backplate && !isLaneHug,
        showEndDecorator: canFuseScreen && backplate && !isLaneHug,
        defaultSurfaceBorderWidth: !centerOnly && backplate && isFloating ? 1 : 0,
        surfaceBorderTransparent: isFloating && !backplate,
        capsuleFlat: d.isFlat,
        capsuleSeparated: d.isSeparated,
        capsuleSegmented: d.isSegmented,
        capsuleTransparent: d.isTransparent,
        capsuleLayer0Fallback: (!backplate && !lanePill && d.groupColor === "layer0") || (d.isSegmented && !backplate),
        capsuleOutlineBaseline: d.isSegmented ? 1 : 0,
        islandTransparent: lanePill || (centerOnly && backplate && !lanePill && isEdgeFlush)
    };
}

function isTinted(axes) {
    return !!(axes && axes.tint === true);
}

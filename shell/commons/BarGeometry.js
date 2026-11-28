// Shared pure geometry for the bar window (B9.4/B9.5/D4f).
//
// Bar.qml binds these values; the runtime probe evaluates the same functions,
// so the outer-margin and exclusive-zone contract has evidence without a
// compositor round-trip and without a second copy of the math.

function margins(edge, vertical, edgeMargin, sideMargin, autoHide, deadPixel) {
    const normal = edgeMargin;
    const anchoredBottom = edge === "bottom" || vertical;
    const anchoredRight = edge === "right" || !vertical;
    return {
        "top": edge === "top" ? normal : (vertical ? sideMargin : 0),
        "bottom": (edge === "bottom" ? normal : (vertical ? sideMargin : 0)) + (anchoredBottom && deadPixel ? -1 : 0),
        "left": edge === "left" ? normal : (vertical ? 0 : sideMargin),
        "right": (edge === "right" ? normal : (vertical ? 0 : sideMargin)) + (anchoredRight && deadPixel ? -1 : 0)
    };
}

// D4f / D-8: boostExtra comes from geometric derivation (BarDefaults.styleBoost),
// never from cornerStyle enum branches (Islands -6 and Panel +4 retired).
function exclusiveZone(vertical, baseBarHeight, baseVerticalBarWidth, boostExtra, edgeMargin) {
    return (vertical ? baseVerticalBarWidth : baseBarHeight) + (boostExtra || 0) + edgeMargin;
}

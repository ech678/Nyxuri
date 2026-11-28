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

// PanelWindow.exclusiveZone is additive to margins[edge] in wlr-layer-shell (Niri),
// so only thickness + boostExtra + innerMargin belongs here (never edgeMargin,
// which is already in margins[edge] and would otherwise be counted twice).
function exclusiveZone(vertical, baseBarHeight, baseVerticalBarWidth, boostExtra, innerMargin) {
    return (vertical ? baseVerticalBarWidth : baseBarHeight) + (boostExtra || 0) + (innerMargin || 0);
}

// Total band distance from the screen edge (for ScreenBarLayout avoidance & corner tuck).
function screenReservation(vertical, baseBarHeight, baseVerticalBarWidth, boostExtra, edgeMargin, innerMargin) {
    return exclusiveZone(vertical, baseBarHeight, baseVerticalBarWidth, boostExtra, innerMargin) + (edgeMargin || 0);
}

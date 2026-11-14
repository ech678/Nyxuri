// Shared pure geometry for the bar window (B9.4/B9.5).
//
// Bar.qml binds these values; the runtime probe evaluates the same functions,
// so the outer-margin and exclusive-zone contract has evidence without a
// compositor round-trip and without a second copy of the math.

function margins(edge, vertical, edgeMargin, sideMargin, layerGap, autoHide, deadPixel) {
    const normal = edgeMargin + (autoHide ? 0 : layerGap);
    const anchoredBottom = edge === "bottom" || vertical;
    const anchoredRight = edge === "right" || !vertical;
    return {
        "top": edge === "top" ? normal : (vertical ? sideMargin : 0),
        "bottom": (edge === "bottom" ? normal : (vertical ? sideMargin : 0)) + (anchoredBottom && deadPixel ? -1 : 0),
        "left": edge === "left" ? normal : (vertical ? 0 : sideMargin),
        "right": (edge === "right" ? normal : (vertical ? 0 : sideMargin)) + (anchoredRight && deadPixel ? -1 : 0)
    };
}

function exclusiveZone(vertical, baseBarHeight, baseVerticalBarWidth, cornerStyle, gapsOut, edgeMargin) {
    return (vertical ? baseVerticalBarWidth : baseBarHeight) + (cornerStyle === 1 ? gapsOut : 0) + (cornerStyle === 2 ? -6 : 0) + ((cornerStyle === 4 || cornerStyle === 5) ? 4 : 0) + edgeMargin;
}

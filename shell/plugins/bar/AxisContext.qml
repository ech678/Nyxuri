// Fork & Trim: dux-shell quickshell/Modules/DBar/AxisContext.qml
// (references/dux-shell, MIT, D4g).
//
// Trimmed for Nyxuri (D4g 单宿主): the orientation context the single lane
// host (BarContent) consumes to lay the same tree out as a row or a rail.
// Dropped from dux: the per-edge / coalesced change signals (our bindings
// re-evaluate off the axes directly) and the position/anchor mutation
// helpers — the host uses explicit geometry everywhere, because a binding
// that yields `undefined` never clears a QML anchor (see Bar.qml's
// top->left->top regression note).

import QtQuick

QtObject {
    id: root

    // The bar's screen edge; "left"/"right" make the bar a rail.
    property string edge: "top"

    readonly property string orientation: isVertical ? "vertical" : "horizontal"
    readonly property bool isVertical: edge === "left" || edge === "right"
    readonly property bool isHorizontal: !isVertical

    // Primary axis = the direction lanes flow along (a row's x, a rail's
    // y); cross axis = the thickness direction.
    function primarySize(item) {
        return isVertical ? item.height : item.width;
    }

    function crossSize(item) {
        return isVertical ? item.width : item.height;
    }
}

import QtQuick
import qs.shared.theme

// Material symbol on a Material 3 shape. Ported 1:1 from end4-pC's
// MaterialShapeWrappedMaterialSymbol.
//
// One sizing adaptation: nyxuri's MaterialSymbol pins its own width/height to
// the rounded icon size, whereas end4-pC's relies on Text's implicit size. So
// the wrapper measures the explicit dimensions — same resulting geometry.
MaterialShapeCanvas {
    id: root

    property alias fill: symbol.fill
    property alias text: symbol.text
    property alias iconSize: symbol.iconSize
    property alias font: symbol.font
    property alias colSymbol: symbol.color
    property real padding: 6
    property var wrappedShape: MaterialShapeCanvas.Shape.Clover4Leaf

    color: Appearance.colors.colSecondaryContainer
    colSymbol: Appearance.colors.colOnSecondaryContainer
    shape: root.wrappedShape
    implicitSize: Math.max(symbol.width, symbol.height) + padding * 2

    MaterialSymbol {
        id: symbol

        anchors.centerIn: parent
        color: root.colSymbol
        fill: root.fill
    }
}

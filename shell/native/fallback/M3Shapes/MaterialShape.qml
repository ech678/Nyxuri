import QtQuick

Rectangle {
    id: root

    enum Shape {
        Circle,
        Square,
        Pill,
        Diamond,
        Gem,
        ClamShell,
        Slanted,
        Pentagon,
        Cookie4Sided,
        Cookie6Sided,
        Cookie7Sided,
        Cookie9Sided,
        Cookie12Sided,
        SoftBurst,
        Sunny,
        Ghostish,
        Custom
    }

    property int shape: MaterialShape.Shape.Square
    property real implicitSize: 0
    property color fillColor: color
    property var customShape: null
    property int sides: 0
    property int animationDuration: 0
    property var animationEasing: null

    implicitWidth: implicitSize > 0 ? implicitSize : 0
    implicitHeight: implicitSize > 0 ? implicitSize : 0
    radius: shape === MaterialShape.Shape.Pill || shape === MaterialShape.Shape.Circle ? Math.min(width, height) / 2 : 12

    function star(points, innerRatio, cornerRadius, rotation) { return null; }
    function regularPolygon(points) { return null; }
    function polygonShape(points) { return null; }
}

import QtQuick

QtObject {
    id: root

    property string edge: "top"

    readonly property bool isHorizontal:
        edge === "top" || edge === "bottom"
    readonly property bool isVertical: !isHorizontal
    readonly property bool isTop: edge === "top"
    readonly property bool isBottom: edge === "bottom"
    readonly property bool isLeft: edge === "left"
    readonly property bool isRight: edge === "right"
    readonly property string inward: isTop ? "down"
        : isBottom ? "up" : isLeft ? "right" : "left"
}

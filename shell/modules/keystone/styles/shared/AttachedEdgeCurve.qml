import QtQuick

Canvas {
    id: root

    property string edge: "top"
    property bool after: false
    property real along: 8
    property real depth: 14
    property color fillColor: "black"
    property real sideControl: 0.58
    property real edgeControl: 0.42

    readonly property bool horizontalEdge: edge === "top" || edge === "bottom"
    width: horizontalEdge ? along : depth
    height: horizontalEdge ? depth : along

    function configureTransform(context) {
        if (edge === "bottom") {
            context.translate(0, height);
            context.scale(1, -1);
        } else if (edge === "left") {
            context.transform(0, 1, 1, 0, 0, 0);
        } else if (edge === "right") {
            context.transform(0, 1, -1, 0, width, 0);
        }
    }

    onPaint: {
        const context = getContext("2d");
        context.reset();
        context.clearRect(0, 0, width, height);
        configureTransform(context);
        context.fillStyle = fillColor;
        context.beginPath();
        if (!after) {
            context.moveTo(0, 0);
            context.lineTo(along, 0);
            context.lineTo(along, depth);
            context.bezierCurveTo(along, depth * sideControl,
                along * edgeControl, 0, 0, 0);
        } else {
            context.moveTo(along, 0);
            context.lineTo(0, 0);
            context.lineTo(0, depth);
            context.bezierCurveTo(0, depth * sideControl,
                along * (1 - edgeControl), 0, along, 0);
        }
        context.fill();
    }

    onEdgeChanged: requestPaint()
    onAfterChanged: requestPaint()
    onAlongChanged: requestPaint()
    onDepthChanged: requestPaint()
    onFillColorChanged: requestPaint()
}

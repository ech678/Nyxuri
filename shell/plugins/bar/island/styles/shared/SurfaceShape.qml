import QtQuick

// Rounded island surface canvas shared by the island background and the
// anchored panel popup (B2-1). Draws a per-corner rounded fill with an
// optional keyhole cutout punched out destination-out.
Canvas {
    id: shape

    required property color surfaceColor
    required property real topLeftRadius
    required property real topRightRadius
    required property real bottomRightRadius
    required property real bottomLeftRadius
    property bool cutoutVisible: false
    property real cutoutX: 0
    property real cutoutY: 0
    property real cutoutWidth: 0
    property real cutoutHeight: 0
    property real cutoutRadius: 0

    function addRoundedRect(context, x, y, width, height, topLeft, topRight, bottomRight, bottomLeft) {
        const maxRadius = Math.min(width / 2, height / 2);
        const tl = Math.min(topLeft, maxRadius);
        const tr = Math.min(topRight, maxRadius);
        const br = Math.min(bottomRight, maxRadius);
        const bl = Math.min(bottomLeft, maxRadius);
        context.beginPath();
        context.moveTo(x + tl, y);
        context.lineTo(x + width - tr, y);
        context.quadraticCurveTo(x + width, y, x + width, y + tr);
        context.lineTo(x + width, y + height - br);
        context.quadraticCurveTo(x + width, y + height, x + width - br, y + height);
        context.lineTo(x + bl, y + height);
        context.quadraticCurveTo(x, y + height, x, y + height - bl);
        context.lineTo(x, y + tl);
        context.quadraticCurveTo(x, y, x + tl, y);
        context.closePath();
    }

    anchors.fill: parent
    antialiasing: true
    onPaint: {
        const context = getContext("2d");
        context.reset();
        context.clearRect(0, 0, width, height);
        addRoundedRect(context, 0, 0, width, height, topLeftRadius, topRightRadius, bottomRightRadius, bottomLeftRadius);
        context.fillStyle = surfaceColor;
        context.fill();
        if (cutoutVisible) {
            context.globalCompositeOperation = "destination-out";
            addRoundedRect(context, cutoutX, cutoutY, cutoutWidth, cutoutHeight, cutoutRadius, cutoutRadius, cutoutRadius, cutoutRadius);
            context.fillStyle = "white";
            context.fill();
            context.globalCompositeOperation = "source-over";
        }
    }
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onSurfaceColorChanged: requestPaint()
    onTopLeftRadiusChanged: requestPaint()
    onTopRightRadiusChanged: requestPaint()
    onBottomRightRadiusChanged: requestPaint()
    onBottomLeftRadiusChanged: requestPaint()
    onCutoutVisibleChanged: requestPaint()
    onCutoutXChanged: requestPaint()
    onCutoutYChanged: requestPaint()
    onCutoutWidthChanged: requestPaint()
    onCutoutHeightChanged: requestPaint()
    onCutoutRadiusChanged: requestPaint()
}

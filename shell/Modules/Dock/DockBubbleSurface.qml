import QtQuick
import qs.Common
import qs.Services
import "../../Common/functions/DockBubble.js" as DockBubble

Item {
    id: root
    property string edge: "bottom"
    property real anchorOffset: width / 2
    property real tailSize: 10
    readonly property real bodyX: edge === "left" ? tailSize : 0
    readonly property real bodyWidth: width - (edge === "bottom" ? 0 : tailSize)
    readonly property real bodyHeight: height - (edge === "bottom" ? tailSize : 0)
    readonly property var outline: DockBubble.outline(width, bodyHeight, edge, tailSize, anchorOffset)
    readonly property var rectangles: visible ? DockBubble.regionRects(outline, height) : []
    property var blurItems: []
    function updateItems() {
        const next = [];
        for (let i = 0; i < strips.count; ++i)
            if (strips.itemAt(i))
                next.push(strips.itemAt(i));
        blurItems = next;
    }
    Repeater {
        id: strips
        model: root.rectangles
        onItemAdded: Qt.callLater(root.updateItems)
        onItemRemoved: Qt.callLater(root.updateItems)
        Item {
            required property var modelData
            readonly property real radius: 0
            x: modelData.x
            y: modelData.y
            width: modelData.width
            height: modelData.height
        }
    }
    Canvas {
        anchors.fill: parent
        antialiasing: true
        readonly property var outline: root.outline
        readonly property color fillColor: BlurService.backgroundColor(Appearance.colors.colSurfaceContainer)
        readonly property color lineColor: Appearance.applyAlpha(Appearance.colors.colOnSurface, 0.18)
        onOutlineChanged: requestPaint()
        onFillColorChanged: requestPaint()
        onLineColorChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            DockBubble.paint(ctx, outline);
            ctx.fillStyle = fillColor;
            ctx.fill();
            ctx.strokeStyle = lineColor;
            ctx.lineWidth = 1;
            ctx.stroke();
        }
    }
}

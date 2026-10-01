pragma ComponentBehavior: Bound
import QtQuick
import QtQml.Models
import Quickshell
import qs.Services
import "../../Common/functions/DockBubble.js" as DockBubble

Region {
    id: root
    required property Item sourceItem
    property var rectangles: []
    property bool enabled: true
    readonly property Item scene: sourceItem.QsWindow.window ? sourceItem.QsWindow.window.contentItem : null
    readonly property bool active: enabled && scene && BlurService.enabled && sourceItem.visible
                                   && sourceItem.opacity > 0
    // Fan rotation is bounded by sixteen degrees. Keep scanline regions alive while
    // moving; changing the shape only updates their coordinates.
    readonly property int capacity: Math.ceil(sourceItem.height + sourceItem.width * 0.28) + 2
    function updateShape() {
        if (!active) {
            rectangles = [];
            return;
        }
        const points = DockBubble.polygon(DockBubble.outline(sourceItem.width, sourceItem.height, "bottom", 0, 0,
                                                             sourceItem.radius));
        rectangles = DockBubble.regionRows(points.map(point => sourceItem.mapToItem(scene, point.x,
                                                                                    point.y)));

    }
    function updateItems() {
        const next = [];
        for (let i = 0; i < strips.count; ++i)
            if (strips.objectAt(i))
                next.push(strips.objectAt(i));
        regions = next;
    }
    onActiveChanged: Qt.callLater(updateShape)
    Component.onCompleted: updateShape()
    property TransformWatcher watcher: TransformWatcher {
        a: root.scene
        b: root.sourceItem
        onTransformChanged: Qt.callLater(root.updateShape)
    }
    property Connections sizeWatcher: Connections {
        target: root.sourceItem
        function onWidthChanged() {
            Qt.callLater(root.updateShape);
        }
        function onHeightChanged() {
            Qt.callLater(root.updateShape);
        }
    }
    property Instantiator strips: Instantiator {
        id: strips
        model: root.active ? root.capacity : 0
        onObjectAdded: Qt.callLater(root.updateItems)
        onObjectRemoved: Qt.callLater(root.updateItems)
        delegate: Region {
            required property int index
            readonly property var span: root.rectangles[index]
            x: span ? span.x : 0
            y: span ? span.y : 0
            width: span ? span.width : 0
            height: span ? span.height : 0
        }
    }
}

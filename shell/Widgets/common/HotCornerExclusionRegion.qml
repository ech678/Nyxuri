import Quickshell
import qs.Common
import qs.Services

Region {
    id: root

    required property real surfaceWidth
    required property real surfaceHeight
    property bool topEdge: true
    property bool bottomEdge: true
    property bool leftEdge: true
    property bool rightEdge: true
    readonly property bool active: NiriConfigService.ready("hot-corners")

    function cornerSize(corner, onEdge) {
        return active && onEdge && PersonalizationConfig.hotCornerActions[corner] !== "disabled"
                ? Metrics.hotCornerSize : 0;
    }

    intersection: Intersection.Subtract

    Region {
        x: 0
        y: 0
        width: root.cornerSize("top-left", root.topEdge && root.leftEdge)
        height: width
    }

    Region {
        x: root.surfaceWidth - width
        y: 0
        width: root.cornerSize("top-right", root.topEdge && root.rightEdge)
        height: width
    }

    Region {
        x: 0
        y: root.surfaceHeight - height
        width: root.cornerSize("bottom-left", root.bottomEdge && root.leftEdge)
        height: width
    }

    Region {
        x: root.surfaceWidth - width
        y: root.surfaceHeight - height
        width: root.cornerSize("bottom-right", root.bottomEdge && root.rightEdge)
        height: width
    }
}

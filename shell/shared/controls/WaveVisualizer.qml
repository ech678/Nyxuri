import QtQuick
import QtQuick.Effects

// Canvas-based audio visualizer fed by cava's raw stdout ("1;2;3" frames).
// Frames arrive far faster than a repaint can afford, so pointsChanged
// coalesces through a ~30fps throttle instead of repainting every burst —
// the unthrottled version grows memory without bound while a track plays.
Canvas {
    id: root

    property list<var> points
    property real maxVisualizerValue: 1000
    property int smoothing: 2
    property bool live: true
    property color color: Appearance.m3colors.m3primary

    property bool paintPending: false
    onPointsChanged: {
        if (!paintThrottle.running) {
            paintThrottle.start();
            root.requestPaint();
        } else {
            root.paintPending = true;
        }
    }

    Timer {
        id: paintThrottle

        interval: 33
        onTriggered: {
            if (root.paintPending) {
                root.paintPending = false;
                root.requestPaint();
                paintThrottle.start();
            }
        }
    }

    onPaint: {
        var ctx = getContext("2d");
        ctx.clearRect(0, 0, width, height);
        var pts = root.points;
        var maxVal = root.maxVisualizerValue || 1;
        var h = height;
        var w = width;
        var n = pts.length;
        if (n < 2)
            return;

        var smoothWindow = root.smoothing;
        var smoothPoints = [];
        for (var i = 0; i < n; ++i) {
            var sum = 0;
            var count = 0;
            for (var j = -smoothWindow; j <= smoothWindow; ++j) {
                var idx = Math.max(0, Math.min(n - 1, i + j));
                sum += pts[idx];
                count++;
            }
            smoothPoints.push(sum / count);
        }
        if (!root.live)
            smoothPoints.fill(0);

        ctx.beginPath();
        ctx.moveTo(0, h);
        for (var k = 0; k < n; ++k) {
            var x = k * w / (n - 1);
            var y = h - (smoothPoints[k] / maxVal) * h;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fillStyle = Qt.rgba(root.color.r, root.color.g, root.color.b, 0.15);
        ctx.fill();
    }

    layer.enabled: true
    layer.effect: MultiEffect {
        saturation: 0.2
        blurEnabled: true
        blurMax: 7
        blur: 1
    }
}

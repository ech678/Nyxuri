import QtQuick
import Quickshell
import Quickshell.Wayland
import qs
import qs.core
import "core/Orbit.js" as Orbit

PanelWindow {
    id: root

    property var host: null
    property var targetScreen: null
    property bool open: false

    property int depth: 0
    property var stack: []
    property int hover: -1
    property int selected: -1
    property real bloom: 0.0
    property real bloomTarget: 0.0
    property real hoverT: 0.0
    property real subBloom: 0.0
    property bool aiming: false
    property real aimX: 0
    property real aimY: 0
    property bool animating: false

    property real ringRadius: 168
    property real hubRadius: 54
    property real deadzone: 46
    property real startAngle: -Math.PI / 2

    readonly property var rootItems: Apps.groups.length > 0 ? Apps.groups : Apps.apps

    readonly property var items: {
        if (root.depth === 0) return root.rootItems
        var f = root.stack[root.stack.length - 1]
        return f && f.children ? f.children : []
    }

    readonly property int count: root.items.length
    readonly property var currentFolder: root.depth > 0 ? root.stack[root.stack.length - 1] : null

    function reset() {
        depth = 0
        stack = []
        hover = -1
        selected = -1
        bloom = 0
        bloomTarget = 0
        hoverT = 0
        subBloom = 0
        aiming = false
        aimX = 0
        aimY = 0
        animating = false
    }

    function startAnim() {
        animating = true
        tick.restart()
    }

    function step(dt) {
        var kb = 1 - Math.exp(-14 * dt)
        bloom += (bloomTarget - bloom) * kb
        var kt = 1 - Math.exp(-18 * dt)
        var targetT = hover >= 0 ? 1.0 : 0.0
        hoverT += (targetT - hoverT) * kt
        var ks = 1 - Math.exp(-15 * dt)
        subBloom += (1.0 - subBloom) * ks
        if (Math.abs(bloom - bloomTarget) < 0.001
                && Math.abs(hoverT - targetT) < 0.001
                && Math.abs(subBloom - 1.0) < 0.001) {
            bloom = bloomTarget
            hoverT = targetT
            subBloom = 1.0
            animating = false
        }
        canvas.requestPaint()
    }

    function drill(i) {
        if (i < 0 || i >= items.length) return false
        var it = items[i]
        if (!it) return false
        if (it.kind === "group" && it.children && it.children.length > 0) {
            stack = stack.concat([it])
            depth = depth + 1
            hover = -1
            selected = -1
            subBloom = 0.0
            startAnim()
            return true
        }
        Apps.launch(it)
        if (root.host) root.host.closeAll()
        return true
    }

    function back() {
        if (depth === 0) return false
        var s = stack.slice()
        s.pop()
        stack = s
        depth = depth - 1
        hover = -1
        selected = -1
        subBloom = 0.0
        startAnim()
        return true
    }

    function move(d) {
        if (count === 0) return
        hover = Orbit.stepIndex(hover < 0 ? 0 : hover, d, count)
        startAnim()
    }

    function localX(px) { return px - width / 2 }
    function localY(py) { return py - height / 2 }

    function updateHover(px, py) {
        var lx = localX(px)
        var ly = localY(py)
        var d = Math.sqrt(lx * lx + ly * ly)
        if (d < deadzone) {
            if (hover !== -1) {
                hover = -1
                startAnim()
            }
            return
        }
        var idx = Orbit.hitTest(lx, ly, count, ringRadius, deadzone, startAngle)
        if (idx !== hover) {
            hover = idx
            startAnim()
        }
    }

    function beginAim(px, py) {
        aiming = true
        aimX = localX(px)
        aimY = localY(py)
        startAnim()
    }

    function endAim(px, py) {
        if (!aiming) return
        aiming = false
        var dx = localX(px) - aimX
        var dy = localY(py) - aimY
        var dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 40) {
            if (hover >= 0) drill(hover)
            startAnim()
            return
        }
        var idx = Orbit.flickIndex(dx, dy, count, startAngle)
        if (idx >= 0) {
            hover = idx
            drill(idx)
        }
        startAnim()
    }

    function onKey(event) {
        if (event.key === Qt.Key_Escape) {
            if (!back() && root.host) root.host.closeAll()
            return true
        }
        if (event.key === Qt.Key_Left) { move(-1); return true }
        if (event.key === Qt.Key_Right) { move(1); return true }
        if (event.key === Qt.Key_Up) { move(-1); return true }
        if (event.key === Qt.Key_Down) { move(1); return true }
        if (event.key === Qt.Key_Tab) { move(event.modifiers & Qt.ShiftModifier ? -1 : 1); return true }
        if (event.key === Qt.Key_Backtab) { move(-1); return true }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (hover >= 0) drill(hover)
            return true
        }
        if (event.key === Qt.Key_Backspace) { back(); return true }
        if (event.key >= Qt.Key_1 && event.key <= Qt.Key_9) {
            var d = Orbit.digitIndex(String(event.key - Qt.Key_0), count)
            if (d >= 0) { hover = d; startAnim() }
            return true
        }
        if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) {
            var ch = String.fromCharCode(event.key).toLowerCase()
            var li = Orbit.letterIndex(ch, Orbit.ringLabels(items))
            if (li >= 0) { hover = li; startAnim() }
            return true
        }
        return false
    }

    anchors {
        top: true
        left: true
        right: true
        bottom: true
    }
    exclusiveZone: 0
    exclusionMode: ExclusionMode.Ignore
    color: "transparent"
    screen: root.targetScreen
    visible: root.open
    WlrLayershell.keyboardFocus: root.open ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    WlrLayershell.layer: WlrLayer.Overlay

    Item {
        anchors.fill: parent
        focus: true

        Rectangle {
            anchors.fill: parent
            color: Theme.rgba("scrim", 0.55 * root.bloom)
        }

        Canvas {
            id: canvas
            anchors.fill: parent
            renderStrategy: Canvas.Cooperative
            opacity: root.bloom

            Component.onCompleted: requestPaint()

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var cx = width / 2
                var cy = height / 2
                var n = root.count
                if (n === 0) return

                ctx.save()
                ctx.translate(cx, cy)
                var s = 0.85 + 0.15 * root.bloom
                ctx.scale(s, s)

                var r = root.ringRadius * root.subBloom
                var step = (Math.PI * 2) / n

                ctx.beginPath()
                ctx.arc(0, 0, r, 0, Math.PI * 2)
                ctx.lineWidth = 1.5
                ctx.strokeStyle = Qt.rgba(
                    Qt.color(Theme.p("outlineVariant")).r,
                    Qt.color(Theme.p("outlineVariant")).g,
                    Qt.color(Theme.p("outlineVariant")).b,
                    0.55)
                ctx.stroke()

                var nodeR = 30
                for (var i = 0; i < n; i++) {
                    var a = root.startAngle + step * i
                    var x = Math.cos(a) * r
                    var y = Math.sin(a) * r
                    var isHover = (i === root.hover)
                    var grow = isHover ? (1.0 + 0.22 * root.hoverT) : 1.0
                    var nr = nodeR * grow
                    var item = root.items[i]

                    ctx.beginPath()
                    ctx.arc(x, y, nr, 0, Math.PI * 2)
                    if (isHover) {
                        ctx.fillStyle = Theme.p("primaryContainer")
                    } else if (item && item.kind === "group") {
                        ctx.fillStyle = Qt.rgba(
                            Qt.color(Theme.p("surfaceContainerHighest")).r,
                            Qt.color(Theme.p("surfaceContainerHighest")).g,
                            Qt.color(Theme.p("surfaceContainerHighest")).b,
                            0.94)
                    } else {
                        ctx.fillStyle = Qt.rgba(
                            Qt.color(Theme.p("surfaceContainerHigh")).r,
                            Qt.color(Theme.p("surfaceContainerHigh")).g,
                            Qt.color(Theme.p("surfaceContainerHigh")).b,
                            0.92)
                    }
                    ctx.fill()

                    ctx.beginPath()
                    ctx.arc(x, y, nr, 0, Math.PI * 2)
                    ctx.lineWidth = isHover ? 2 : 1
                    ctx.strokeStyle = isHover
                        ? Theme.p("primary")
                        : Qt.rgba(
                            Qt.color(Theme.p("outlineVariant")).r,
                            Qt.color(Theme.p("outlineVariant")).g,
                            Qt.color(Theme.p("outlineVariant")).b,
                            0.7)
                    ctx.stroke()

                    ctx.fillStyle = isHover ? Theme.p("onPrimaryContainer") : Theme.p("onSurface")
                    ctx.font = "600 11px sans-serif"
                    ctx.textAlign = "center"
                    ctx.textBaseline = "middle"
                    var label = item ? item.name : ""
                    if (item && item.kind === "group") {
                        label = Orbit.truncate(label, 11)
                    } else {
                        label = Orbit.truncate(label, 10)
                    }
                    ctx.fillText(label, x, y)

                    if (item && item.kind === "group") {
                        ctx.fillStyle = Theme.p("primary")
                        ctx.font = "700 9px sans-serif"
                        ctx.fillText(String(item.count), x, y + nr + 9)
                    }

                    if (i < 9) {
                        ctx.fillStyle = Qt.rgba(
                            Qt.color(Theme.p("onSurfaceVariant")).r,
                            Qt.color(Theme.p("onSurfaceVariant")).g,
                            Qt.color(Theme.p("onSurfaceVariant")).b,
                            0.85)
                        ctx.font = "600 10px sans-serif"
                        ctx.fillText(String(i + 1), x, y - nr - 8)
                    }
                }

                ctx.beginPath()
                ctx.arc(0, 0, root.hubRadius, 0, Math.PI * 2)
                ctx.fillStyle = Theme.p("surfaceContainerHighest")
                ctx.fill()
                ctx.lineWidth = 1.5
                ctx.strokeStyle = Theme.p("primary")
                ctx.stroke()

                ctx.fillStyle = Theme.p("onSurface")
                ctx.font = "700 20px sans-serif"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                ctx.fillText(String(root.depth), 0, -6)

                ctx.fillStyle = Theme.p("onSurfaceVariant")
                ctx.font = "500 9px sans-serif"
                var sub = root.currentFolder ? Orbit.truncate(root.currentFolder.name, 12) : "nyxuri"
                ctx.fillText(sub, 0, 12)

                if (root.aiming) {
                    ctx.beginPath()
                    ctx.moveTo(root.aimX, root.aimY)
                    ctx.lineTo(root.localX(root.width), root.localY(root.height))
                    ctx.strokeStyle = Theme.p("primary")
                    ctx.lineWidth = 2
                    ctx.globalAlpha = 0.6
                    ctx.stroke()
                    ctx.globalAlpha = 1.0
                }

                ctx.restore()
            }
        }

        Item {
            id: inputLayer
            anchors.fill: parent
            focus: true

            Keys.onPressed: function (event) {
                if (root.onKey(event)) event.accepted = true
            }

            HoverHandler {
                id: hoverHandler
                onPointChanged: root.updateHover(point.position.x, point.position.y)
            }

            DragHandler {
                id: drag
                target: null
                onActiveChanged: {
                    if (active) root.beginAim(centroid.position.x, centroid.position.y)
                    else root.endAim(centroid.position.x, centroid.position.y)
                }
            }

            TapHandler {
                onTapped: function (event) {
                    root.updateHover(event.position.x, event.position.y)
                    if (root.hover >= 0) root.drill(root.hover)
                }
            }

            WheelHandler {
                onWheel: function (event) {
                    root.move(event.angleDelta.y > 0 ? -1 : 1)
                }
            }
        }
    }

    Timer {
        id: tick
        interval: 16
        repeat: true
        running: false
        onTriggered: {
            root.step(0.016)
            if (!root.animating) stop()
        }
    }

    onOpenChanged: {
        if (open) {
            reset()
            bloomTarget = 1.0
            inputLayer.forceActiveFocus()
            startAnim()
        } else {
            bloomTarget = 0.0
            bloom = 0.0
            animating = false
            tick.stop()
            canvas.requestPaint()
        }
    }
}
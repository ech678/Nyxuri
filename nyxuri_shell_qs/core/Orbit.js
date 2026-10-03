.pragma library

var TAU = Math.PI * 2

function polar(index, count, radius, startAngle) {
    if (count <= 0) return { x: 0, y: 0, angle: 0 }
    var step = TAU / count
    var a = (startAngle || 0) + step * index
    return {
        x: Math.cos(a) * radius,
        y: Math.sin(a) * radius,
        angle: a
    }
}

function angles(count, startAngle) {
    var out = []
    if (count <= 0) return out
    var step = TAU / count
    for (var i = 0; i < count; i++) out.push((startAngle || 0) + step * i)
    return out
}

function hitTest(mx, my, count, radius, deadzone, startAngle) {
    if (count <= 0) return -1
    var d = Math.sqrt(mx * mx + my * my)
    if (d < (deadzone || 0)) return -1
    var a = Math.atan2(my, mx)
    var step = TAU / count
    var rel = a - (startAngle || 0)
    while (rel < 0) rel += TAU
    while (rel >= TAU) rel -= TAU
    var idx = Math.floor((rel + step / 2) / step) % count
    if (idx < 0) idx += count
    return idx
}

function nearestIndex(mx, my, count, radius, startAngle) {
    if (count <= 0) return -1
    var best = -1
    var bestD = 1e18
    for (var i = 0; i < count; i++) {
        var p = polar(i, count, radius, startAngle)
        var dx = mx - p.x
        var dy = my - p.y
        var d = dx * dx + dy * dy
        if (d < bestD) {
            bestD = d
            best = i
        }
    }
    return best
}

function flickIndex(dx, dy, count, startAngle) {
    if (count <= 0) return -1
    var d = Math.sqrt(dx * dx + dy * dy)
    if (d < 1) return -1
    var a = Math.atan2(dy, dx)
    var step = TAU / count
    var rel = a - (startAngle || 0)
    while (rel < 0) rel += TAU
    while (rel >= TAU) rel -= TAU
    var idx = Math.floor((rel + step / 2) / step) % count
    if (idx < 0) idx += count
    return idx
}

function wrap(i, count) {
    if (count <= 0) return -1
    return ((i % count) + count) % count
}

function stepIndex(current, delta, count) {
    if (count <= 0) return -1
    return wrap(current + delta, count)
}

function digitIndex(key, count) {
    var n = parseInt(key, 10)
    if (isNaN(n)) return -1
    if (n === 0) return count > 9 ? 9 : -1
    if (n >= 1 && n <= 9 && n <= count) return n - 1
    return -1
}

function letterIndex(key, labels) {
    if (!key || key.length === 0) return -1
    var k = key.toLowerCase()
    for (var i = 0; i < labels.length; i++) {
        var l = labels[i] || ""
        if (l.length > 0 && l.charAt(0).toLowerCase() === k) return i
    }
    return -1
}

function shouldHysteresis(prevAngle, nextAngle, hysteresisDeg) {
    var h = (hysteresisDeg || 0) * Math.PI / 180
    if (h <= 0) return true
    var d = Math.abs(nextAngle - prevAngle)
    while (d > Math.PI) d = Math.abs(d - TAU)
    return d >= h
}

function clamp(v, lo, hi) {
    return v < lo ? lo : (v > hi ? hi : v)
}

function easeOutCubic(t) {
    var u = 1 - clamp(t, 0, 1)
    return 1 - u * u * u
}

function ringLabels(items) {
    var out = []
    for (var i = 0; i < items.length; i++) {
        out.push(items[i] && items[i].name ? items[i].name : "")
    }
    return out
}

function visibleRing(items, maxCount) {
    if (!items) return []
    if (!maxCount || items.length <= maxCount) return items
    return items.slice(0, maxCount)
}

function truncate(s, n) {
    if (!s) return ""
    if (s.length <= n) return s
    return s.substring(0, n - 1) + "\u2026"
}
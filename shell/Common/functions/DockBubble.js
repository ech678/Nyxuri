.pragma library

// One outline drives both the painted bubble and the compositor's integer
// region. Coordinates include the half-pixel inset for its one-pixel border.
function outline(width, bodyHeight, edge, tail, offset, cornerRadius) {
    if (width <= 1 || bodyHeight <= 1) return [];
    const bodyX = edge === "left" ? tail : 0;
    const bodyWidth = width - (edge === "bottom" ? 0 : tail);
    const x = bodyX + 0.5, y = 0.5;
    const right = bodyX + bodyWidth - 0.5, bottom = bodyHeight - 0.5;
    const radius = Math.max(0, Math.min(cornerRadius === undefined ? 12 : cornerRadius,
                                     (right - x) / 2, (bottom - y) / 2));
    const extent = edge === "bottom" ? bodyWidth : bodyHeight;
    const tip = Math.max(26, Math.min(extent - 26, offset));
    const p = [["M", x + radius, y], ["L", right - radius, y],
               ["Q", right, y, right, y + radius]];
    if (tail > 0 && edge === "right") {
        p.push(["L", right, tip - 14],
               ["C", right, tip - 7, right + tail, tip - 5, right + tail, tip],
               ["C", right + tail, tip + 5, right, tip + 7, right, tip + 14]);
    }
    p.push(["L", right, bottom - radius], ["Q", right, bottom, right - radius, bottom]);
    if (tail > 0 && edge === "bottom") {
        p.push(["L", tip + 14, bottom],
               ["C", tip + 7, bottom, tip + 5, bottom + tail, tip, bottom + tail],
               ["C", tip - 5, bottom + tail, tip - 7, bottom, tip - 14, bottom]);
    }
    p.push(["L", x + radius, bottom], ["Q", x, bottom, x, bottom - radius]);
    if (tail > 0 && edge === "left") {
        p.push(["L", x, tip + 14],
               ["C", x, tip + 7, x - tail, tip + 5, x - tail, tip],
               ["C", x - tail, tip - 5, x, tip - 7, x, tip - 14]);
    }
    p.push(["L", x, y + radius], ["Q", x, y, x + radius, y]);
    return p;
}

function paint(ctx, commands) {
    ctx.beginPath();
    for (const c of commands) {
        switch (c[0]) {
        case "M": ctx.moveTo(c[1], c[2]); break;
        case "L": ctx.lineTo(c[1], c[2]); break;
        case "Q": ctx.quadraticCurveTo(c[1], c[2], c[3], c[4]); break;
        case "C": ctx.bezierCurveTo(c[1], c[2], c[3], c[4], c[5], c[6]); break;
        }
    }
    ctx.closePath();
}

function polygon(commands) {
    const points = [];
    for (const c of commands) {
        if (c[0] === "M" || c[0] === "L") {
            points.push({x: c[1], y: c[2]});
            continue;
        }
        const start = points[points.length - 1];
        // Curves are at most 28 logical pixels across. Sixteen segments keep
        // their approximation below a compositor pixel, including the tail.
        for (let step = 1; step <= 16; ++step) {
            const t = step / 16, u = 1 - t;
            if (c[0] === "Q") {
                points.push({x: u*u*start.x + 2*u*t*c[1] + t*t*c[3],
                             y: u*u*start.y + 2*u*t*c[2] + t*t*c[4]});
            } else {
                points.push({x: u*u*u*start.x + 3*u*u*t*c[1] + 3*u*t*t*c[3] + t*t*t*c[5],
                             y: u*u*u*start.y + 3*u*u*t*c[2] + 3*u*t*t*c[4] + t*t*t*c[6]});
            }
        }
    }
    return points;
}

function regionRects(commands, height) {
    return polygonRects(polygon(commands), 0, Math.ceil(height), true);
}

// Transformed labels need screen-aligned scanlines: Region.item only maps
// two opposite corners and cannot represent a rotated rounded rectangle.
function regionRows(points) {
    if (!points.length) return [];
    const ys = points.map(point => point.y);
    return polygonRects(points, Math.floor(Math.min.apply(null, ys)),
                        Math.ceil(Math.max.apply(null, ys)), false);
}

function polygonRects(points, top, bottom, merge) {
    const rects = [];
    for (let y = top; y < bottom; ++y) {
        const scanY = y + 0.5, crossings = [];
        for (let i = 0; i < points.length; ++i) {
            const a = points[i], b = points[(i + 1) % points.length];
            if ((a.y <= scanY && b.y > scanY) || (b.y <= scanY && a.y > scanY))
                crossings.push(a.x + (scanY - a.y) * (b.x - a.x) / (b.y - a.y));
        }
        crossings.sort((a, b) => a - b);
        for (let i = 0; i + 1 < crossings.length; i += 2) {
            const x = Math.ceil(crossings[i] - 0.5);
            const width = Math.floor(crossings[i + 1] - 0.5) + 1 - x;
            if (width <= 0) continue;
            const last = rects[rects.length - 1];
            if (merge && last && last.x === x && last.width === width && last.y + last.height === y)
                last.height++;
            else
                rects.push({x: x, y: y, width: width, height: 1});
        }
    }
    return rects;
}

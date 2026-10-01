import QtQuick
import QtTest
import "../../Common/functions/DockBubble.js" as DockBubble

TestCase {
    name: "DockBubble"

    function contains(rects, x, y) {
        return rects.some(rect => x >= rect.x && x < rect.x + rect.width && y >= rect.y && y < rect.y
                                  + rect.height);
    }

    function test_blurIncludesTailButExcludesEmptyBoundingBox() {
        for (const edge of ["bottom", "left", "right"]) {
            const rects = DockBubble.regionRects(DockBubble.outline(280, 120, edge, 10, 26), edge === "bottom"
                                                 ? 130 : 120);
            verify(contains(rects, 140, 60));
            verify(!contains(rects, 0, 0));
            if (edge === "bottom") {
                verify(contains(rects, 26, 125));
                verify(!contains(rects, 140, 125));
            } else if (edge === "left") {
                verify(contains(rects, 4, 26));
                verify(!contains(rects, 4, 75));
            } else {
                verify(contains(rects, 275, 26));
                verify(!contains(rects, 275, 75));
            }
            for (const rect of rects) {
                verify(rect.x >= 0 && rect.y >= 0);
                verify(rect.width > 0 && rect.height > 0);
                verify(rect.x + rect.width <= 280);
                verify(rect.y + rect.height <= (edge === "bottom" ? 130 : 120));
            }
        }
    }

    function test_tailFollowsClampedAnchor() {
        const left = DockBubble.regionRects(DockBubble.outline(280, 120, "bottom", 10, -50), 130);
        const right = DockBubble.regionRects(DockBubble.outline(280, 120, "bottom", 10, 500), 130);
        verify(contains(left, 26, 125));
        verify(!contains(left, 254, 125));
        verify(contains(right, 254, 125));
        verify(!contains(right, 26, 125));
    }

    function test_previewHasNoTailAndHandlesEmptyGeometry() {
        const rects = DockBubble.regionRects(DockBubble.outline(280, 120, "bottom", 0, 26), 130);
        verify(contains(rects, 140, 118));
        verify(!contains(rects, 26, 125));
        compare(DockBubble.regionRects(DockBubble.outline(0, 0, "bottom", 10, 26), 0).length, 0);
    }

    function test_rotatedLabelRegionFollowsItsOutline() {
        const width = 258, height = 28, radius = 7;
        for (const degrees of [-10, 0, 10]) {
            const angle = degrees * Math.PI / 180, cosine = Math.cos(angle), sine = Math.sin(angle);
            const points = DockBubble.polygon(DockBubble.outline(width, height, "bottom", 0, 0, radius)).map(
                      point => ({
                          x: point.x * cosine - point.y * sine,
                          y: point.x * sine + point.y * cosine
                      }));
            const rows = DockBubble.regionRows(points);
            verify(contains(rows, width / 2 * cosine - height / 2 * sine, width / 2 * sine + height / 2
                            * cosine));
            verify(!contains(rows, 0, 0));
            let area = 0;
            for (const row of rows) {
                area += row.width * row.height;
                for (const x of [row.x + 0.5, row.x + row.width - 0.5]) {
                    const y = row.y + 0.5;
                    const localX = x * cosine + y * sine, localY = -x * sine + y * cosine;
                    verify(localX >= 0 && localX <= width && localY >= 0 && localY <= height);
                }
            }
            const expectedArea = width * height - (4 - Math.PI) * radius * radius;
            verify(Math.abs(area - expectedArea) < expectedArea * 0.05);
        }
        compare(DockBubble.regionRows([]).length, 0);
    }
}

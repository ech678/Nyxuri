import QtQuick 2.15
import QtTest 1.3
import "../../shared/cards/SystemCardGeometry.js" as Geometry
import "../../shared/cards/SystemCardState.js" as CardState

// 通过 Qt6 QML 引擎加载共享卡片模块，覆盖模块内 .import 的实际依赖解析。
TestCase {
    name: "SystemCardImports"

    function test_geometry_resolves_catalog_import() {
        compare(Geometry.widthFor("time"), 312);
        compare(Geometry.heightFor("time"), 328);
        compare(Geometry.widthFor("unknown-card"), 152);
    }

    function test_card_state_resolves_catalog_and_placement_imports() {
        const initial = CardState.defaultState();
        compare(initial.cards.time.enabled, true);

        const placed = CardState.setPlacementSpace(initial, "time", "wallpaper");
        compare(placed.cards.time.desktop.placementSpace, "wallpaper");
        compare(initial.cards.time.desktop.placementSpace, "screen");

        const arranged = CardState.setGlobalMode(initial, "screenBottomLeft");
        compare(arranged.globalDesktopLayoutMode, "screenBottomLeft");
        const rejected = CardState.setGlobalMode(initial, "unsupported-mode");
        compare(rejected.globalDesktopLayoutMode, "free");
    }
}

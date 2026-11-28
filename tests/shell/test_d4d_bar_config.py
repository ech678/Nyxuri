"""D4d bar behavior & overflow engine contract tests.

Pins the D4d contract (shell/ROADMAP.md, D4d row; bar-config.md D4d):
- BarDefaults.DEFAULTS gains the behavior axes with pre-D4d-preserving
  defaults (the ONE deliberate change: hoverPopoutDelay 150 per the D4d-1
  decision) and the per-lane overflow default vocabulary;
- the store: normalizeBarAxes covers every new key, the named setters ride
  setBarAxis with the same clamps, and NO config version bump exists (new
  keys only — nothing to migrate);
- the overflow resolver is a verbatim dux fork (OverflowLayout.js +
  CenterLayout.js) and the relocation host exists (LaneOverflowHost);
- the lane engines live in both orientation hosts, measurement flattens
  entry overrides for dux's top-level placement/priority reads, and the
  hidden sets write back through BarGroup.inOverflow;
- BarGroup carries the measurement/relocation protocol; Media is the
  flexible widget (natural/min/allotted);
- hoverPopouts absorbs the retired clickToShow hardcode across every
  consumer; StyledPopup gains the explicit pinnedOpen path and the axis
  intent delay;
- Bar.qml: the autoHide delay grace + strict unpinning (popup holds only,
  never the sidebar holds), hideOnFullscreen raising to Overlay via the
  CompositorDriver fullscreen face, and the click-through lane mask with
  the dux edge-strip reveal semantics;
- the settings surfaces expose the rows through the named setters.
"""

from __future__ import annotations

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
SERVICES_DIR = os.path.join(SHELL, "services")
DUX_BAR = os.path.join(REPO_ROOT, "references", "dux-shell", "quickshell", "Modules", "DBar")

BEHAVIOR_AXES = {
    "autoHideDelay": 0,
    "autoHideStrict": False,
    "hideOnFullscreen": False,
    "clickThrough": False,
    "hoverPopouts": True,
    "hoverPopoutDelay": 150,
}

LANE_OVERFLOW_AXES = {
    "leftOverflowMode": "auto",
    "middleOverflowMode": "auto",
    "rightOverflowMode": "auto",
}


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def dux_original(name: str) -> str:
    """The dux original with our Fork & Trim header block stripped."""
    ours = read(os.path.join(BAR_DIR, name))
    lines = ours.split("\n")
    stripped = []
    in_header = False
    header_done = False
    for line in lines:
        if not header_done and line.startswith("// Fork & Trim:"):
            in_header = True
            continue
        if in_header:
            if line.startswith("//"):
                continue
            in_header = False
            header_done = True
            if line.strip() == "":
                continue
        stripped.append(line)
    ours_stripped = "\n".join(stripped).strip()
    upstream = read(os.path.join(DUX_BAR, name)).strip()
    return ours_stripped, upstream


class BarDefaultsTest(unittest.TestCase):
    """The D4d axes table: defaults preserve the pre-D4d behavior."""

    @classmethod
    def setUpClass(cls):
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))

    def test_behavior_axes_defaults(self):
        for key, value in BEHAVIOR_AXES.items():
            self.assertIn(f"{key}: {str(value).lower() if isinstance(value, bool) else value},", self.defaults, key)

    def test_lane_overflow_axes_and_vocabulary(self):
        for key, value in LANE_OVERFLOW_AXES.items():
            self.assertIn(f'{key}: "{value}"', self.defaults, key)
        self.assertIn('var LANE_OVERFLOW_MODES = ["auto", "bar"];', self.defaults)

    def test_behavior_keys_registry_covers_d4d(self):
        for key in list(BEHAVIOR_AXES) + list(LANE_OVERFLOW_AXES):
            self.assertIn(f'"{key}"', self.defaults)


class StoreTest(unittest.TestCase):
    """PersonalizationConfig: normalization, setters, and NO migration."""

    @classmethod
    def setUpClass(cls):
        cls.store = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))
        cls.migrations = read(os.path.join(SERVICES_DIR, "ConfigMigrations.js"))

    def test_normalize_covers_every_d4d_axis(self):
        for key in list(BEHAVIOR_AXES) + list(LANE_OVERFLOW_AXES):
            self.assertIn(f"{key}:", self.store, key)

    def test_named_setters_exist(self):
        setters = [
            "setBarAutoHideDelay", "setBarAutoHideStrict", "setBarHideOnFullscreen",
            "setBarClickThrough", "setBarHoverPopouts", "setBarHoverPopoutDelay",
            "setBarLaneOverflowMode",
        ]
        for setter in setters:
            self.assertIn(f"function {setter}(", self.store, setter)

    def test_no_config_version_bump(self):
        # New keys only: nothing was renamed or moved, so the version chain
        # must NOT have grown a v6 step (a bump here would be a regression
        # in minimal-change discipline, not a feature).
        self.assertNotIn('"6"', self.migrations)
        self.assertNotIn("=== 6", self.migrations)


class ForkTest(unittest.TestCase):
    """The dux resolver fork is verbatim (SegmentRoles precedent)."""

    def test_overflow_layout_fork_is_verbatim_dux(self):
        ours, upstream = dux_original("OverflowLayout.js")
        self.assertIn("Fork & Trim: dux-shell", read(os.path.join(BAR_DIR, "OverflowLayout.js")))
        self.assertEqual(ours, upstream)

    def test_center_layout_fork_is_verbatim_dux(self):
        ours, upstream = dux_original("CenterLayout.js")
        self.assertIn("Fork & Trim: dux-shell", read(os.path.join(BAR_DIR, "CenterLayout.js")))
        self.assertEqual(ours, upstream)


class EngineTest(unittest.TestCase):
    """Both orientation hosts carry the engine and the lane buttons."""

    @classmethod
    def setUpClass(cls):
        cls.content = read(os.path.join(BAR_DIR, "BarContent.qml"))
        cls.vertical = read(os.path.join(BAR_DIR, "VerticalBarContent.qml"))

    def test_engine_lives_in_both_hosts(self):
        for host in (self.content, self.vertical):
            self.assertIn('import "OverflowLayout.js" as OverflowLayout', host)
            self.assertIn("function overflowMeasure(entries, plainRepeater, materialRepeater, zone)", host)
            self.assertIn("function resolveOverflow()", host)
            self.assertIn("function applyOverflow(entries, plainRepeater, materialRepeater, hidden, sizes, zone)", host)
            self.assertIn("id: overflowTimer", host)
            self.assertIn("overflowPrevious", host)

    def test_measurement_flattens_overrides_for_dux_reads(self):
        # dux placement()/priority() read TOP-LEVEL entry keys; our storage
        # nests them in overrides — the flatten must stay at the boundary.
        for host in (self.content, self.vertical):
            self.assertIn("Object.assign({", host)
            self.assertIn("widgetId: entries[i].widgetId", host)
            self.assertIn("}, entries[i].overrides || {});", host)
            self.assertIn("OverflowLayout.placement(flat, fallback)", host)

    def test_lane_default_resolves_through_the_axes(self):
        # D4e: per-bar — the hosts resolve the lane default through their
        # own entry's axes (root.axes), never the settings-facing views.
        for host in (self.content, self.vertical):
            self.assertIn('root.axes[zone + "OverflowMode"]', host)

    def test_buttons_mount_in_all_six_rows(self):
        # Left/middle lanes host the button at the END (inner edge = towards
        # the screen centre), the right/bottom lane at index 0 — dux
        # defaultPosition semantics.
        self.assertEqual(self.content.count("LaneOverflowHost {"), 6)
        self.assertEqual(self.vertical.count("LaneOverflowHost {"), 6)
        for id_name in (
            "leftOverflowHost", "leftOverflowHostMaterial", "middleOverflowHost",
            "middleOverflowHostMaterial", "rightOverflowHost", "rightOverflowHostMaterial",
        ):
            self.assertIn(f"id: {id_name}", self.content)
        for id_name in (
            "topOverflowHost", "topOverflowHostMaterial", "middleOverflowHost",
            "centerOverflowHostMaterial", "bottomOverflowHost", "bottomOverflowHostMaterial",
        ):
            self.assertIn(f"id: {id_name}", self.vertical)

    def test_hidden_groups_feed_the_buttons(self):
        for host in (self.content, self.vertical):
            self.assertIn("overflowGroups: root.overflowHiddenGroups", host)
            self.assertIn("root.overflowHiddenGroupsLeft = hiddenGroups;", host)
            # Assignments are membership-guarded: a fresh array identity per
            # resolve would close an open popup on every widget resize.
            self.assertIn("function sameGroups(a, b)", host)
            self.assertIn("!root.sameGroups(hiddenGroups, root.overflowHiddenGroupsLeft)", host)

    def test_lane_mask_surfaces_exposed(self):
        self.assertIn("readonly property Item laneMaskLeft: leftLane", self.content)
        self.assertIn("readonly property Item laneMaskMiddle: absoluteCenter", self.content)
        self.assertIn("readonly property Item laneMaskRight: rightLane", self.content)
        self.assertIn("readonly property Item laneMaskLeft: topLane", self.vertical)
        self.assertIn("readonly property Item laneMaskRight: bottomLane", self.vertical)


class GroupProtocolTest(unittest.TestCase):
    """BarGroup: collapse + measurement + relocation; Media flexibility."""

    @classmethod
    def setUpClass(cls):
        cls.group = read(os.path.join(BAR_DIR, "BarGroup.qml"))
        cls.media = read(os.path.join(BAR_DIR, "Media.qml"))
        cls.host = read(os.path.join(BAR_DIR, "LaneOverflowHost.qml"))

    def test_overflow_collapse_folds_into_has_content(self):
        self.assertIn("property bool inOverflow: false", self.group)
        self.assertIn("root.inOverflow ? false :", self.group)

    def test_measurement_protocol(self):
        self.assertIn("readonly property real overflowEntrySize:", self.group)
        self.assertIn("readonly property real overflowEntryMin:", self.group)
        self.assertIn('"naturalPrimarySize" in widget ? widget.naturalPrimarySize', self.group)
        self.assertIn('return Math.min(widget.minimumPrimarySize + root.padding * 2, root.overflowEntrySize);', self.group)

    def test_relocation_api(self):
        self.assertIn("function setWidgetHost(host: Item): void", self.group)
        self.assertIn("function restoreWidget(): void", self.group)
        self.assertIn("function setOverflowAllotment(size: real): void", self.group)
        self.assertIn("loader.parent = host;", self.group)
        # The loader reference is captured ONCE at completion: a bound
        # children-lookup dies mid-relocation (nulls the moment the loader
        # leaves the layout, so restore would no-op and the loader would be
        # destroyed with the popup window — probe-caught).
        self.assertIn("property Item widgetLoader: null", self.group)
        self.assertIn("root.widgetLoader = gridLayout.children[0];", self.group)

    def test_media_flexible_protocol(self):
        self.assertIn("property real allottedPrimarySize: -1", self.media)
        self.assertIn("readonly property real naturalPrimarySize:", self.media)
        self.assertIn("readonly property real minimumPrimarySize:", self.media)
        self.assertIn("root.allottedPrimarySize > 0 ?", self.media)

    def test_lane_overflow_host_shape(self):
        self.assertIn("property var overflowGroups: []", self.host)
        self.assertIn("function toggle(): void", self.host)
        self.assertIn("OverflowLayout.expanderIcon(root.barAxes.position, root.open)", self.host)
        self.assertIn("hoverActivates: false", self.host)
        self.assertIn("closeOnOutsideClick: true", self.host)
        # Restore-before-deactivate: the popup window tree is destroyed on
        # deactivate, hosted loaders must never ride it down.
        self.assertIn("if (group.widgetLoader && group.widgetLoader.parent === popupColumn)", self.host)
        self.assertIn("popup.pinnedOpen = false;", self.host)


class HoverPopoutsTest(unittest.TestCase):
    """The axis absorbs the retired clickToShow hardcode."""

    CONSUMERS = (
        "ClockWidget.qml", "Resources.qml", "BatteryIndicator.qml",
        "NetworkSpeed.qml", "WeatherBar.qml", "Media.qml",
    )

    def test_no_click_to_show_survives(self):
        hits = []
        for root_dir in (BAR_DIR, SERVICES_DIR):
            for name in os.listdir(root_dir):
                if not name.endswith(".qml") and not name.endswith(".js"):
                    continue
                if "clickToShow" in read(os.path.join(root_dir, name)):
                    hits.append(name)
        self.assertEqual(hits, [], f"clickToShow survived in: {hits}")

    def test_consumers_bind_the_axis(self):
        # D4e: the read goes through the owning bar (widgetBar injection,
        # per-bar) with the settings-facing entry as the standalone
        # fallback — same axis, scoped.
        for name in self.CONSUMERS[:-1]:
            source = read(os.path.join(BAR_DIR, name))
            self.assertIn("property var widgetBar: null", source, name)
            self.assertIn("readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes", source, name)
            self.assertIn("!root.barAxes.hoverPopouts", source, name)
        self.assertIn("hoverEnabled: root.barAxes.hoverPopouts", read(os.path.join(BAR_DIR, "Media.qml")))

    def test_styled_popup_pinned_open_and_axis_delay(self):
        popup = read(os.path.join(BAR_DIR, "StyledPopup.qml"))
        self.assertIn("property bool pinnedOpen: false", popup)
        self.assertIn("active: root._hoverHold || root.pinnedOpen", popup)
        self.assertIn("property var widgetBar: null", popup)
        self.assertIn("readonly property var barAxes: widgetBar ? widgetBar.axes : PersonalizationConfig.barAxes", popup)
        self.assertIn("property int hoverOpenDelay: root.barAxes.hoverPopoutDelay", popup)
        self.assertNotIn("hoverOpenDelay: 400", popup)


class BarBehaviorTest(unittest.TestCase):
    """Bar.qml: delay grace, strict unpinning, fullscreen raise, mask."""

    @classmethod
    def setUpClass(cls):
        cls.bar = read(os.path.join(BAR_DIR, "Bar.qml"))
        cls.niri = read(os.path.join(SERVICES_DIR, "NiriDriver.qml"))
        cls.driver = read(os.path.join(SERVICES_DIR, "CompositorDriver.qml"))

    def test_delay_grace_wiring(self):
        self.assertIn("property bool hideHold: false", self.bar)
        self.assertIn("id: hideHoldTimer", self.bar)
        self.assertIn("barRoot.autoHideEnabled && barRoot.hideDelay > 0", self.bar)
        self.assertIn("!barRoot.mustShow && !barRoot.hideHold", self.bar)

    def test_strict_gates_only_popup_holds(self):
        # D4d-2: context menu + media popup unpin under strict; the sidebar
        # and control panel holds stay pinned (they grow from the bar edge).
        # D4e: the window body nests deeper under the per-bar host chain.
        self.assertIn("!barRoot.strictHide)\n                                                barRoot.contextMenuHold = true", self.bar)
        self.assertIn("!barRoot.strictHide)\n                                                barRoot.mediaControlsHold = true", self.bar)
        self.assertIn("GlobalStates.sidebarLeftPresentationOutput === barRoot.outputName)", self.bar)
        self.assertNotIn("!barRoot.strictHide)\n                                                barRoot.controlPanelHold = true", self.bar)

    def test_fullscreen_raise(self):
        self.assertIn("readonly property bool fullscreenAutoHide:", self.bar)
        self.assertIn("CompositorDriver.fullscreenToplevelOnScreen(barRoot.outputName)", self.bar)
        self.assertIn("barRoot.fullscreenAutoHide ? WlrLayer.Overlay : WlrLayer.Top", self.bar)
        # D4e: autoHide is a per-entry axis (barRoot.axes), not the bridge.
        self.assertIn("(barRoot.axes.autoHide === true) || barRoot.fullscreenAutoHide", self.bar)

    def test_fullscreen_state_face(self):
        self.assertIn("isFullscreen: !!rawWindow.is_fullscreen,", self.niri)
        self.assertIn("function fullscreenToplevelOnScreen(outputName)", self.niri)
        self.assertIn("return NiriDriver.fullscreenToplevelOnScreen(outputName);", self.driver)

    def test_click_through_mask_swaps_to_lanes(self):
        self.assertIn("item: barRoot.clickThroughEnabled ? null : hoverMaskRegion", self.bar)
        self.assertIn("item: barRoot.clickThroughEnabled ? barRoot.laneMaskLeft : null", self.bar)
        self.assertIn("item: barRoot.clickThroughEnabled ? barRoot.laneMaskMiddle : null", self.bar)
        self.assertIn("item: barRoot.clickThroughEnabled ? barRoot.laneMaskRight : null", self.bar)

    def test_dux_reveal_semantics_ported(self):
        self.assertIn("property bool gapEnterSuppressed: false", self.bar)
        self.assertIn("function inEdgeStrip(): bool", self.bar)
        self.assertIn("id: revealSettle", self.bar)
        self.assertIn("barRoot.gapEnterSuppressed = !barRoot.inEdgeStrip();", self.bar)


class SettingsPageTest(unittest.TestCase):
    """Behavior group + per-instance overflow rows."""

    @classmethod
    def setUpClass(cls):
        cls.appearance = read(os.path.join(BAR_DIR, "BarAppearanceSection.qml"))
        cls.widget_page = read(os.path.join(BAR_DIR, "BarWidgetPage.qml"))

    def test_behavior_group_rows(self):
        section = self.appearance[:self.appearance.index("Behavior") + 4000]
        for text in (
            "setBarAutoHideDelay", "setBarAutoHideStrict", "setBarHideOnFullscreen",
            "setBarClickThrough", "setBarHoverPopouts", "setBarHoverPopoutDelay",
        ):
            self.assertIn(text, section)
        # The auto-hide toggle moved here from Style & Corner (single home).
        self.assertLess(self.appearance.index("Behavior"), self.appearance.index('text: I18n.tr("Autohide")'))
        style_corner = self.appearance[self.appearance.index("Style & Corner"):self.appearance.index("Behavior")]
        self.assertNotIn("setBarAutoHide", style_corner)

    def test_widget_editor_overflow_group(self):
        self.assertIn('["spacer", "separator", "island"].indexOf(root.widgetId) === -1', self.widget_page)
        self.assertIn('"value": "section"', self.widget_page)
        self.assertIn('"value": "always"', self.widget_page)
        self.assertIn('root.set("overflowMode"', self.widget_page)
        self.assertIn('root.set("overflowPriority"', self.widget_page)


if __name__ == "__main__":
    unittest.main()

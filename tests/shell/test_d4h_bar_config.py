"""D4h bar behavior-additions contract tests.

Pins the D4h contract (shell/ROADMAP.md, D4h row; bar-config.md D4h):
- BarDefaults.DEFAULTS gains the four behavior axes with pre-D4h-preserving
  defaults (smart off, no reservation reveal, no super reveal, no peek) and
  the internal timing constants (super delay 100, peek debounce 80 / stay
  450 — deliberately not axes);
- the store: normalizeBarAxes covers every new key, the named setters ride
  setBarAxis, and the three-state mode writer (setBarAutoHideMode) maps
  off/on/smart onto the two storage keys; NO config version bump exists
  (new keys only — nothing to migrate, the chain stays at 7);
- Bar.qml: smart hide engages the autoHide channel only while the active
  workspace of the output has windows (the empty leg parks WITH its
  reservation), pushWindows and superReveal are read off the entry axes
  (per-bar truth, the bridge globals retired), and the workspace-switch
  peek rides the mustShow chain through the debounce/stay cadence;
- Workspaces.qml: the super-press icon face gates on the owning bar's
  superReveal axis, not the bridge;
- the Config bridge collapses to the selected-bar projection + the
  internal hoverRegionWidth — no live consumer reads the retired globals;
- BarContent.qml: the scroll strips are orientation-aware (row: either
  side of the middle lane; rail: start/end halves along the track, D-9 —
  the same axis pair serves both orientations) and expose the probe
  surface;
- the settings face: the three-state segmented picker writes both keys,
  and every follow-up row is gated on the active mode (the default view
  gains no rows); the search anchor is registered in the bar manifest;
- the i18n dictionary carries the three new rows.
"""

from __future__ import annotations

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
SERVICES_DIR = os.path.join(SHELL, "services")
UI_DIR = os.path.join(SHELL, "ui")

D4H_AXES = {
    "autoHideSmart": False,
    "pushWindows": False,
    "superReveal": False,
    "peekOnWorkspaceSwitch": False,
}

NEW_ROWS = {
    "Reserve space when hidden": "setBarPushWindows",
    "Reveal while holding Super": "setBarSuperReveal",
    "Peek on workspace switch": "setBarPeekOnWorkspaceSwitch",
}


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class BarDefaultsTest(unittest.TestCase):
    """The D4h axes table: defaults preserve the pre-D4h behavior."""

    @classmethod
    def setUpClass(cls):
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))

    def test_behavior_axes_defaults(self):
        for key, value in D4H_AXES.items():
            self.assertIn(f"{key}: false,", self.defaults, key)

    def test_behavior_keys_registry_covers_d4h(self):
        for key in D4H_AXES:
            self.assertIn(f'"{key}"', self.defaults)

    def test_internal_timing_constants(self):
        # One cadence for every bar, no settings rows: super delay carries
        # the bridge's historical 100ms, the peek cadence follows the
        # noctalia show_on_workspace_switch reference.
        self.assertIn("var SUPER_REVEAL_DELAY_MS = 100;", self.defaults)
        self.assertIn("var PEEK_DEBOUNCE_MS = 80;", self.defaults)
        self.assertIn("var PEEK_STAY_MS = 450;", self.defaults)


class StoreTest(unittest.TestCase):
    """PersonalizationConfig: normalization, setters, the mode writer."""

    @classmethod
    def setUpClass(cls):
        cls.store = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))
        cls.migrations = read(os.path.join(SERVICES_DIR, "ConfigMigrations.js"))

    def test_normalize_covers_every_d4h_axis(self):
        # Booleans normalize through the strict `=== true` door like every
        # other behavior axis.
        for key in D4H_AXES:
            self.assertIn(f"{key}: raw.{key} === true", self.store, key)

    def test_named_setters_exist(self):
        for setter in (
            "setBarAutoHideSmart", "setBarPushWindows", "setBarSuperReveal",
            "setBarPeekOnWorkspaceSwitch", "setBarAutoHideMode",
        ):
            self.assertIn(f"function {setter}(", self.store, setter)

    def test_mode_writer_maps_two_keys(self):
        # The segmented control writes both storage keys; each setter stays
        # single-key so the sparse writer sees one deviation per axis.
        self.assertIn('setBarAutoHide(mode === "on" || mode === "smart");', self.store)
        self.assertIn('setBarAutoHideSmart(mode === "smart");', self.store)

    def test_no_config_version_bump(self):
        # New keys only: nothing was renamed or moved, so the version chain
        # stays at 7 (a bump here would be a regression in minimal-change
        # discipline, not a feature).
        self.assertIn("var CURRENT_VERSION = 7;", self.migrations)
        for key in D4H_AXES:
            self.assertNotIn(key, self.migrations)


class BarWindowTest(unittest.TestCase):
    """Bar.qml: smart hide, per-entry pushWindows/superReveal, the peek."""

    @classmethod
    def setUpClass(cls):
        cls.bar = read(os.path.join(BAR_DIR, "Bar.qml"))

    def test_smart_hide_wiring(self):
        self.assertIn("readonly property bool smartHideAxis: barRoot.axes.autoHideSmart === true", self.bar)
        self.assertIn("CompositorDriver.activeWorkspaceForOutput(barRoot.outputName)", self.bar)
        self.assertIn("CompositorDriver.windowsForWorkspace(barRoot.activeWorkspace?.id ?? -1)", self.bar)
        # The autoHide channel extension: smart engages only while the
        # workspace has windows (empty workspace = parked with reservation).
        self.assertIn(
            "(barRoot.axes.autoHide === true) || barRoot.fullscreenAutoHide || (barRoot.smartHideAxis && barRoot.workspaceHasWindows)",
            self.bar,
        )
        # The driver-less guard: probes (no compositor) must read parked.
        self.assertIn("readonly property var activeWorkspace: CompositorDriver.available ?", self.bar)

    def test_push_windows_reads_the_entry_axis(self):
        self.assertIn("readonly property bool pushWindowsWhenShown: barRoot.axes.pushWindows === true", self.bar)
        self.assertNotIn("autoHide?.pushWindows", self.bar)

    def test_super_reveal_reads_the_entry_axis(self):
        self.assertIn("if (barRoot.axes.superReveal !== true)", self.bar)
        self.assertIn("interval: BarDefaults.SUPER_REVEAL_DELAY_MS", self.bar)
        self.assertNotIn("showWhenPressingSuper", self.bar.split("// global showWhenPressingSuper.enable.")[1])

    def test_peek_machinery(self):
        self.assertIn(
            "readonly property bool peekEnabled: (barRoot.axes.autoHide === true || barRoot.smartHideAxis) && barRoot.axes.peekOnWorkspaceSwitch === true",
            self.bar,
        )
        self.assertIn("property bool peekShow: false", self.bar)
        self.assertIn("function noteWorkspaceSwitch(): void", self.bar)
        self.assertIn("id: peekDebounce", self.bar)
        self.assertIn("interval: BarDefaults.PEEK_DEBOUNCE_MS", self.bar)
        self.assertIn("id: peekStay", self.bar)
        self.assertIn("interval: BarDefaults.PEEK_STAY_MS", self.bar)
        # A valid -> valid workspace-id transition is a real switch; the
        # first assignment (driver connecting, peek toggled on) is not.
        self.assertIn("barRoot.peekWorkspaceId >= 0 && barRoot.lastPeekWorkspaceId >= 0", self.bar)
        # The peek rides the mustShow chain (so hideHold and the reveal
        # machinery serve it — no second slide-out implementation).
        self.assertIn(
            "property bool mustShow: pointerShow || superShow || interactionHold || peekShow",
            self.bar,
        )
        # Toggling the axis off mid-peek must not strand the reveal.
        self.assertIn("onPeekEnabledChanged:", self.bar)


class WorkspacesTest(unittest.TestCase):
    """The super-press icon face gates on the owning bar's axis."""

    @classmethod
    def setUpClass(cls):
        cls.workspaces = read(os.path.join(BAR_DIR, "Workspaces.qml"))

    def test_super_gating_per_entry(self):
        self.assertIn("root.barAxes.superReveal !== true", self.workspaces)
        self.assertIn("interval: BarDefaults.SUPER_REVEAL_DELAY_MS", self.workspaces)
        self.assertNotIn("showWhenPressingSuper", self.workspaces)
        self.assertIn('import "../../services/BarDefaults.js" as BarDefaults', self.workspaces)


class BridgeTest(unittest.TestCase):
    """The bridge collapses to the selected-bar projection."""

    @classmethod
    def setUpClass(cls):
        cls.bridge = read(os.path.join(SERVICES_DIR, "Config.qml"))

    def test_auto_hide_object_keeps_only_projection_and_mask_width(self):
        self.assertIn("readonly property bool enable: PersonalizationConfig.barAutoHide", self.bridge)
        self.assertIn("readonly property int hoverRegionWidth: 2", self.bridge)
        # No retired property declarations (the comment may narrate the move).
        self.assertNotIn("property bool pushWindows", self.bridge)
        self.assertNotIn("showWhenPressingSuper", self.bridge)

    def test_no_live_consumer_reads_the_retired_globals(self):
        # vendor/ is the upstream reference tree — never runtime. Every
        # live consumer moved to the entry axes.
        hits = []
        for root_dir, subdirs, files in os.walk(SHELL):
            subdirs[:] = [d for d in subdirs if d != "vendor"]
            for name in files:
                if not name.endswith(".qml"):
                    continue
                source = read(os.path.join(root_dir, name))
                if "showWhenPressingSuper" in source or "autoHide?.pushWindows" in source or "autoHide.pushWindows" in source:
                    hits.append(os.path.relpath(os.path.join(root_dir, name), SHELL))
        # Bar.qml carries one historical note in a comment; strip comments
        # crudely and require nothing else.
        offenders = [h for h in hits if h != os.path.join("plugins", "bar", "Bar.qml")]
        self.assertEqual(offenders, [], f"retired bridge globals read in: {offenders}")


class ScrollZonesTest(unittest.TestCase):
    """BarContent: the strips serve both orientations (D-9)."""

    @classmethod
    def setUpClass(cls):
        cls.content = read(os.path.join(BAR_DIR, "BarContent.qml"))
        cls.hint = read(os.path.join(BAR_DIR, "ScrollHint.qml"))

    def test_row_strips_keep_lane_relative_split(self):
        self.assertIn("width: root.vertical ? parent.width : Math.max(0, absoluteCenter.x)", self.content)
        self.assertIn(
            "width: root.vertical ? parent.width : Math.max(0, parent.width - (absoluteCenter.x + absoluteCenter.width))",
            self.content,
        )

    def test_rail_halves_along_the_track(self):
        self.assertIn("height: root.vertical ? Math.max(0, absoluteCenter.y) : parent.height", self.content)
        self.assertIn(
            "height: root.vertical ? Math.max(0, parent.height - (absoluteCenter.y + absoluteCenter.height)) : parent.height",
            self.content,
        )

    def test_actions_reuse_the_start_end_axis_pair(self):
        # No new keys: the rail halves keep the start/end actions.
        self.assertIn("onScrollDown: root.performScrollAction(root.leftAction, false)", self.content)
        self.assertIn("onScrollDown: root.performScrollAction(root.rightAction, false)", self.content)

    def test_hints_get_seam_sides_on_the_rail(self):
        self.assertIn('side: root.vertical ? "top" : "left"', self.content)
        self.assertIn('side: root.vertical ? "bottom" : "right"', self.content)
        self.assertIn('anchors.bottom: root.side === "top" ? parent.bottom : undefined', self.hint)
        self.assertIn('anchors.top: root.side === "bottom" ? parent.top : undefined', self.hint)

    def test_probe_surface_exposed(self):
        self.assertIn("readonly property var scrollZones: ({", self.content)


class SettingsPageTest(unittest.TestCase):
    """Three-state picker + mode-gated follow-up rows."""

    @classmethod
    def setUpClass(cls):
        cls.appearance = read(os.path.join(BAR_DIR, "BarAppearanceSection.qml"))
        cls.manifest = read(os.path.join(BAR_DIR, "manifest.toml"))

    def test_mode_derivation_and_writer(self):
        self.assertIn(
            'readonly property string autoHideMode: root.axes.autoHideSmart ? "smart" : (root.axes.autoHide ? "on" : "off")',
            self.appearance,
        )
        self.assertIn("onSelected: key => PersonalizationConfig.setBarAutoHideMode(String(key))", self.appearance)

    def test_three_state_picker_choices(self):
        for key, icon in (("off", "visibility_off"), ("on", "auto_hide"), ("smart", "brightness_auto")):
            self.assertIn(f'key: "{key}"', self.appearance, key)
            self.assertIn(f'icon: "{icon}"', self.appearance, icon)

    def test_follow_up_rows_gated_on_active_mode(self):
        # The default view gains no rows: delay/strict keep their gate, and
        # the three D4h rows only show while the mode is active.
        self.assertEqual(self.appearance.count('visible: root.autoHideMode !== "off"'), 5)

    def test_new_rows_wire_the_named_setters(self):
        for text, setter in NEW_ROWS.items():
            # Concatenated so the i18n corpus regex (test_i18n_catalog) does
            # not mistake this loop for an unresolvable tr() call site.
            marker = "text: I18n." + 'tr("' + text + '")'
            row_idx = self.appearance.index(marker)
            row = self.appearance[row_idx:row_idx + 500]
            self.assertIn("checked: root.axes.", row, text)
            self.assertIn(f"PersonalizationConfig.{setter}(checked)", row, text)
            self.assertIn(f"PersonalizationConfig.{setter}(BarDefaults.DEFAULTS.", row, text)

    def test_search_anchor_registered_in_manifest(self):
        self.assertIn('anchorId: "bar.behavior.autohide"', self.appearance)
        self.assertIn('id = "bar.behavior.autohide"', self.manifest)


class I18nTest(unittest.TestCase):
    """The dictionary carries the new rows."""

    def test_zh_cn_entries(self):
        zh = read(os.path.join(SHELL, "commons", "i18n", "zh_CN.toml"))
        for source, translation in (
            ("Reserve space when hidden", "隐藏时保留空间"),
            ("Reveal while holding Super", "按住 Super 时显示"),
            ("Peek on workspace switch", "切换工作区时短暂显示"),
        ):
            self.assertIn(f'"{source}" = "{translation}"', zh, source)


if __name__ == "__main__":
    unittest.main()

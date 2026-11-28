"""D4c bar-level geometry & style engine contract tests.

Pins the D4c contract (shell/ROADMAP.md, D4c row):
- BarDefaults.DEFAULTS is the single bar-level axes table: geometry axes
  default to the -1 sentinel (= the pre-D4c per-style baselines, which the
  file carries), migrated keys keep the pre-D4c flat values, and the
  borderless vocabulary gains "flat";
- the v5 migration folds the flat [bar] globals onto the configs entry and
  the per-(mode, widget) widgetStyles onto the ACTIVE mode's entries
  (explicit key map, deviations only, idempotent);
- the store: normalizeBarAxes covers the whole table, the derived views
  never get assigned, setters write through withBarConfigs, and the retired
  [bar] flat keys / widgetStyles API are gone;
- consumers: lane hosts resolve through BarDefaults (no hardcoded
  spacing/inset), BarGroup consumes segmentRole (fusion radii from
  SegmentRoles), the shell radius flows through one alias per host, and
  the font scale multiplies bar-surface type reads only (BarScale);
- the settings page exposes the axes through the named setters.
"""

from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
SERVICES_DIR = os.path.join(SHELL, "services")

MIGRATED_BAR_KEYS = {
    "position", "autoHide", "screenList", "showBackground", "cornerStyle",
    "borderless", "groupColor", "barThickness", "verticalThickness",
    "edgeMargin", "sideMargin",
}

SENTINEL_AXES = {"spacing", "innerPadding", "widgetPadding", "radius"}


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def js_var_body(content: str, header: str) -> str:
    """The assignment body of `var <header> = { ... }` (brace-balanced)."""
    match = re.search(rf"var {header} = \{{", content)
    assert match, f"{header} table not found"
    depth = 1
    pos = match.end()
    start = pos
    while pos < len(content):
        char = content[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start:pos]
        pos += 1
    raise AssertionError(f"{header} table is unbalanced")


def js_object_keys(body: str) -> set[str]:
    return set(re.findall(r'^\s{4}([a-zA-Z_][a-zA-Z0-9_]*):', body, re.M))


class BarDefaultsTest(unittest.TestCase):
    """The bar-level axes table: sentinels preserve the pre-D4c visual."""

    @classmethod
    def setUpClass(cls):
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))

    def test_sentinel_geometry_axes(self):
        body = js_var_body(self.defaults, "DEFAULTS")
        for key in SENTINEL_AXES:
            self.assertIsNotNone(re.search(rf"^\s+{key}: -1,$", body, re.M), msg=key)

    def test_migrated_keys_keep_pre_d4c_values(self):
        body = js_var_body(self.defaults, "DEFAULTS")
        checks = {
            "position": '"top"',
            "autoHide": "false",
            "backplate": "true",
            "lanePill": "false",
            "tint": "false",
            "widgetStyle": '"fused"',
            "capsuleRadius": '"pill"',
            "groupColor": '"layer1"',
            "barThickness": "36",
            "verticalThickness": "36",
            "edgeMargin": "5",
            "sideMargin": "-1",
            "sideMarginPercent": "0",
            "squareCorners": "false",
            "fontScale": "1.0",
            "surfaceColor": '"default"',
            "surfaceTransparency": "-1",
            "borderEnabled": "false",
            "widgetTransparency": "1.0",
            "widgetOutlineEnabled": "false",
        }
        for key, value in checks.items():
            self.assertIn(f"\n    {key}: {value},", body, f"{key} default changed")

    def test_widget_style_vocabulary_includes_flat(self):
        match = re.search(r"var WIDGET_STYLES = \[(.*?)\];", self.defaults, re.S)
        self.assertIsNotNone(match)
        modes = set(re.findall(r'"([a-z]+)"', match.group(1)))
        self.assertEqual(modes, {"fused", "separate", "flat"})

    def test_baselines_carry_the_end4_values(self):
        self.assertIn("return style.vertical ? -4 : -7;", self.defaults)
        self.assertIn("return style.squareCorners ? 3 : (style.vertical ? -2 : -1);", self.defaults)
        self.assertIn("return style.gapsOut;", self.defaults)
        self.assertIn("return 5;", self.defaults)

    def test_shadow_axes_are_registered_out(self):
        body = js_var_body(self.defaults, "DEFAULTS")
        for key in ("shadowIntensity", "shadowOpacity"):
            self.assertNotIn(f"\n    {key}:", body, f"{key} must not ship as a live axis (D5 material)")
        self.assertIn("D5 window-growth material", self.defaults)

    def test_is_custom_color_guard(self):
        self.assertIn("function isCustomColor(value)", self.defaults)
        self.assertIn("function resolvedRadius(axes, styleRadius)", self.defaults)


class MigrationV5Test(unittest.TestCase):
    """v5: flat [bar] globals + widgetStyles fold onto the configs entry."""

    @classmethod
    def setUpClass(cls):
        cls.migrations = read(os.path.join(SERVICES_DIR, "ConfigMigrations.js"))
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_version_is_seven(self):
        self.assertIn("var CURRENT_VERSION = 7", self.migrations)
        self.assertIn("changed = migrateBarGlobals(config, seed) || changed;", self.migrations)
        self.assertIn("changed = migrateBarStyleAxes(config, seed) || changed;", self.migrations)

    def test_explicit_bar_globals_map(self):
        match = re.search(r"var MIGRATED_BAR_GLOBALS = \{(.*?)\};", self.migrations, re.S)
        self.assertIsNotNone(match)
        found = set(re.findall(r"^\s{4}([a-zA-Z_][a-zA-Z0-9_]*):", match.group(1), re.M))
        self.assertEqual(found, MIGRATED_BAR_KEYS)

    def test_every_mapped_key_is_a_real_axis_or_folded_in_v7(self):
        body = js_var_body(self.defaults, "DEFAULTS")
        axes = js_object_keys(body)
        retired_to_v7 = {"showBackground", "cornerStyle", "borderless"}
        self.assertTrue((MIGRATED_BAR_KEYS - retired_to_v7) <= axes,
                        (MIGRATED_BAR_KEYS - retired_to_v7) - axes)

    def test_widget_style_keys_match_the_popup_vocabulary(self):
        match = re.search(r"var WIDGET_STYLE_KEYS = \[(.*?)\];", self.migrations, re.S)
        self.assertIsNotNone(match)
        keys = set(re.findall(r'"([a-zA-Z]+)"', match.group(1)))
        self.assertEqual(keys, {"color", "borderColor", "radius", "borderWidth", "padding"})

    def test_widget_styles_fold_targets_the_active_mode(self):
        self.assertIn("style.mode === currentMode", self.migrations)
        self.assertIn("delete bar.widgetStyles;", self.migrations)

    def test_store_seeds_bar_defaults(self):
        self.assertIn("barDefaults: BarDefaults.DEFAULTS", self.pc)


class StoreShapeTest(unittest.TestCase):
    """The store: axes on the entry, derived views, no retired reads."""

    @classmethod
    def setUpClass(cls):
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_normalize_bar_axes_covers_the_whole_table(self):
        defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))
        table = js_object_keys(js_var_body(defaults, "DEFAULTS"))
        match = re.search(r"function normalizeBarAxes\(raw\) \{(.*?)\n    \}", self.pc, re.S)
        self.assertIsNotNone(match, "normalizeBarAxes not found")
        body = match.group(1)
        missing = [key for key in table if not re.search(rf"\b{key}:", body)]
        self.assertEqual(missing, [], f"normalizeBarAxes misses axes: {missing}")

    def test_bar_level_views_are_derived_not_assigned(self):
        for prop in ("barPosition", "barAutoHide", "barScreenList", "barBackplate",
                     "barLanePill", "barTint", "barWidgetStyle", "barCapsuleRadius",
                     "barGroupColor", "barThickness", "barVerticalThickness",
                     "barEdgeMargin", "barSideMargin"):
            self.assertRegex(
                self.pc,
                rf"readonly property \w+ {prop}: root\.activeBarConfig\(\)\.axes\.",
                msg=prop,
            )
        self.assertNotIn('setValue("barPosition"', self.pc)
        self.assertNotIn('setValue("barShowBackground"', self.pc)
        self.assertNotIn('setValue("barAutoHide"', self.pc)
        self.assertNotIn('setValue("barScreenList"', self.pc)

    def test_setters_write_through_the_entry(self):
        self.assertIn("function setBarAxis(key, value)", self.pc)
        for setter in ("setBarPosition", "setBarThickness", "setBarSideMarginPercent",
                       "setBarSpacing", "setBarInnerPadding", "setBarWidgetPadding",
                       "setBarSquareCorners", "setBarRadius", "setBarFontScale",
                       "setBarSurfaceColor", "setBarSurfaceTransparency",
                       "setBarBorderEnabled", "setBarWidgetOutlineEnabled",
                       "setBarWidgetTransparency"):
            self.assertIn(f"function {setter}(", self.pc)

    def test_widget_styles_api_retired(self):
        for gone in ("barWidgetStyleEntry", "setBarWidgetStyle(mode", "resetBarWidgetStyle",
                     "normalizedBarWidgetStyles", "property var barWidgetStyles"):
            self.assertNotIn(gone, self.pc, gone)
        for qml in os.listdir(BAR_DIR):
            if not qml.endswith(".qml"):
                continue
            content = read(os.path.join(BAR_DIR, qml))
            for gone in ("setBarWidgetStyle(mode", "resetBarWidgetStyle(", "barWidgetStyleEntry"):
                self.assertNotIn(gone, content, f"{qml} still reads {gone}")

    def test_entry_style_writers_are_uid_addressed(self):
        self.assertIn("function setBarEntryStyle(uid, key, value)", self.pc)
        self.assertIn("function resetBarEntryStyle(uid)", self.pc)

    def test_flat_bar_keys_left_the_section(self):
        match = re.search(r"function barSectionRaw\(\) \{(.*?)\n    \}", self.pc, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        for key in ("position", "autoHide", "screenList", "showBackground", "cornerStyle",
                    "borderless", "groupColor", "widgetStyles", "barThickness",
                    "verticalThickness", "edgeMargin", "sideMargin"):
            self.assertNotIn(f'"{key}":', body, f"[bar] section still writes {key}")

    def test_sparse_configs_emit_axes(self):
        # D4e: per-entry diff — sparseBarConfigs folds every entry through
        # sparseBarConfigEntry, which carries the axes emission loop.
        match = re.search(r"function sparseBarConfigs\(\) \{(.*?)\n    \}", self.pc, re.S)
        self.assertIsNotNone(match)
        self.assertIn("sparseBarConfigEntry", match.group(1))
        entry = re.search(r"function sparseBarConfigEntry\((.*?)\n    \}", self.pc, re.S)
        self.assertIsNotNone(entry)
        self.assertIn("Object.keys(BarDefaults.DEFAULTS)", entry.group(1))


class ConsumptionTest(unittest.TestCase):
    """Lane hosts and BarGroup consume the axes; the fusion is SegmentRoles."""

    BAR_SURFACE_FONT_FILES = (
        "ClockWidget.qml", "Workspaces.qml", "UtilButtons.qml", "Media.qml",
        "ActiveWindow.qml", "BatteryIndicator.qml", "WeatherBar.qml",
        "Resources.qml", "SystemIcons.qml", "SysTray.qml", "Divisor.qml",
        "LauncherButton.qml", "PowerButton.qml", "DynamicIsland.qml",
    )
    SETTINGS_SURFACE_FILES = (
        "BarManagerCard.qml", "BarLaneSection.qml", "BarWidgetPickerPopup.qml",
        "QuickSettingsListCard.qml", "BarModulesSection.qml",
        "BarAppearanceSection.qml", "GeneralBarPage.qml", "BarWidgetPage.qml",
    )

    @classmethod
    def setUpClass(cls):
        cls.content = read(os.path.join(BAR_DIR, "BarContent.qml"))
        cls.vertical = read(os.path.join(BAR_DIR, "VerticalBarContent.qml"))
        cls.group = read(os.path.join(BAR_DIR, "BarGroup.qml"))

    def test_lane_geometry_resolves_through_the_store(self):
        # D4e: the hosts resolve through their OWN entry's axes (per-bar);
        # the resolved* functions take the axes argument.
        self.assertIn("PersonalizationConfig.resolvedBarInnerPadding(root.axes)", self.content)
        self.assertIn("PersonalizationConfig.resolvedBarInnerPadding(root.axes)", self.vertical)
        self.assertIn("PersonalizationConfig.resolvedBarSpacing(false, root.axes)", self.content)
        self.assertIn("PersonalizationConfig.resolvedBarSpacing(true, root.axes)", self.vertical)
        for host in (self.content, self.vertical):
            self.assertIn("property var barConfig: PersonalizationConfig.activeBarConfig()", host)
            self.assertIn("readonly property var axes: root.barConfig ? root.barConfig.axes : BarDefaults.DEFAULTS", host)
            self.assertIn("filterLayout(root.barConfig ? root.barConfig.lanes.left : [])", host)
        self.assertNotIn('borderless === "transparent" ? -7', self.content)
        self.assertNotIn("? -4 :", self.vertical)

    def test_segment_roles_fork_is_verbatim_dux(self):
        roles = read(os.path.join(BAR_DIR, "SegmentRoles.js"))
        self.assertIn("Fork & Trim: dux-shell", roles)
        self.assertIn('id === "spacer" || id === "separator"', roles)
        self.assertIn('roles[run[0]] = "first"', roles)

    def test_bargroup_consumes_segment_role_not_indices(self):
        self.assertIn('property string segmentRole: "solo"', self.group)
        self.assertIn('root.segmentRole === "first"', self.group)
        self.assertNotIn("property int currentIndex", self.group)
        self.assertNotIn("property int totalCount", self.group)
        for host in (self.content, self.vertical):
            self.assertNotIn("totalCount:", host)
            self.assertRegex(host, r'segmentRole: root\.(left|middle|right)SegmentRoles\[index\] \?\? "solo"')

    def test_lane_roles_read_live_participation(self):
        for host in (self.content, self.vertical):
            self.assertIn("function laneSegmentRoles(entries, plainRepeater, materialRepeater)", host)
            self.assertIn("participating.push(item === null ? true : item.hasContent);", host)

    def test_shell_radius_flows_through_one_alias(self):
        for host in (self.content, self.vertical):
            self.assertIn("readonly property real shellRadius: PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding, root.axes)", host)
        bar = read(os.path.join(BAR_DIR, "Bar.qml"))
        self.assertIn("readonly property real shellRadius: PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding, barRoot.axes)", bar)
        self.assertIn("root.shellRadius", self.content)

    def test_flat_mode_capsule_chrome(self):
        self.assertIn("readonly property bool isFlat: root.styleContext.capsuleFlat", self.group)
        self.assertIn("if (root.isFlat)", self.group)

    def test_widget_layer_axes_reach_the_capsule(self):
        # D4e: the capsule resolves through the injected per-bar axes.
        self.assertIn("property var barAxes: PersonalizationConfig.activeBarConfig().axes", self.group)
        self.assertIn("PersonalizationConfig.resolvedBarWidgetColor(root.baseBackgroundColor, root.barAxes)", self.group)
        self.assertIn("PersonalizationConfig.resolvedBarWidgetPadding(root.paintMaterialPill, root.barAxes)", self.group)
        self.assertIn("PersonalizationConfig.barWidgetOutlineWidth(", self.group)
        self.assertIn("PersonalizationConfig.barWidgetOutlineColor(", self.group)

    def test_percent_margin_replaces_the_px_axis_in_geometry(self):
        bar = read(os.path.join(BAR_DIR, "Bar.qml"))
        self.assertIn("readonly property real sideMarginPx", bar)
        self.assertIn("barRoot.sideMarginPx", bar)

    def test_bar_scale_singleton_registered_and_font_only(self):
        qmldir = read(os.path.join(BAR_DIR, "qmldir"))
        self.assertIn("singleton BarScale 1.0 BarScale.qml", qmldir)
        scale = read(os.path.join(BAR_DIR, "BarScale.qml"))
        self.assertIn("function fontFor(widgetBar)", scale)
        self.assertIn("function iconFor(widgetBar)", scale)
        self.assertIn("axes.fontScale", scale)
        self.assertIn("axes.iconScale", scale)

    def test_bar_surface_files_scale_type_reads(self):
        # Every NexusStyle.font.* read on a bar surface scales through
        # BarScale.font / BarScale.fontFor(...) or BarScale.icon / BarScale.iconFor(...).
        unscaled = re.compile(r"NexusStyle\.font\.[a-zA-Z]+(?![a-zA-Z])(?![^\n]*BarScale\.(font|icon))")
        for name in self.BAR_SURFACE_FONT_FILES:
            content = read(os.path.join(BAR_DIR, name))
            reads = [m.group(0) for m in unscaled.finditer(content)
                     if not m.group(0).endswith("Weight")]
            self.assertEqual(reads, [], f"{name} has unscaled type reads: {reads}")

    def test_settings_surfaces_stay_unscaled(self):
        for name in self.SETTINGS_SURFACE_FILES:
            content = read(os.path.join(BAR_DIR, name))
            self.assertNotIn("BarScale.font", content, f"{name} is settings surface, never scaled")

    def test_options_pages_stay_unscaled(self):
        options_dir = os.path.join(BAR_DIR, "options")
        for name in os.listdir(options_dir):
            if not name.endswith(".qml"):
                continue
            content = read(os.path.join(options_dir, name))
            self.assertNotIn("BarScale.font", content, f"options/{name} is settings surface")


class SettingsPageTest(unittest.TestCase):
    """The appearance tab exposes the D4c axes through named setters."""

    @classmethod
    def setUpClass(cls):
        cls.page = read(os.path.join(BAR_DIR, "BarAppearanceSection.qml"))

    def test_d4c_rows_exist(self):
        for call in ('PersonalizationConfig.setBarSideMarginPercent(', 'PersonalizationConfig.setBarSpacing(',
                     'PersonalizationConfig.setBarInnerPadding(', 'PersonalizationConfig.setBarWidgetPadding(',
                     'PersonalizationConfig.setBarFontScale(', 'PersonalizationConfig.setBarSquareCorners(',
                     'PersonalizationConfig.setBarRadius(', 'PersonalizationConfig.setBarSurfaceColor(',
                     'PersonalizationConfig.setBarSurfaceTransparency(', 'PersonalizationConfig.setBarBorderEnabled(',
                     'PersonalizationConfig.setBarWidgetOutlineEnabled(', 'PersonalizationConfig.setBarWidgetTransparency(',
                     'PersonalizationConfig.setBarScreenList(', 'PersonalizationConfig.setBarBackplate(',
                     'PersonalizationConfig.setBarAutoHide('):
            self.assertIn(call, self.page, call)

    def test_sentinel_rows_render_auto(self):
        self.assertIn('I18n.tr("Auto")', self.page)

    def test_no_direct_setvalue_on_bar_axes(self):
        self.assertNotIn('setValue("bar', self.page)


if __name__ == "__main__":
    unittest.main()

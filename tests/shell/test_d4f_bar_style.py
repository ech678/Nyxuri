"""D4f bar style atomization contract tests.

Pins the D4f contract (shell/ROADMAP.md, D4f row; D-7 & D-8; bar-config.md D4f):
- BarDefaults.DEFAULTS retires cornerStyle / borderless / showBackground in
  favor of atomic axes (backplate, lanePill, tint, widgetStyle,
  capsuleRadius, widgetRadius, groupColor + "transparent", edgeMargin 0 vs >0,
  sideMargin -1 Auto sentinel);
- BarStylePresets.js carries the 6 write-only starter recipes (hug, floating,
  islands, material, materialHug, panel) with no persisted preset key;
- ConfigMigrations v7 folds cornerStyle/borderless/showBackground onto the
  atomic axes (explicit maps, defaults skipped, retired keys stripped,
  idempotent) and stamps schema 7;
- plugins/bar/BarStyle.js is the single pure style resolver in plugins/bar/ —
  no cornerStyle/borderless/showBackground references remain outside vendor/
  and probe/;
- D-8 dark bonuses retired: Islands -6 exclusiveZone, Islands inner radius 8,
  Panel +4 height boost;
- BarAppearanceSection reordered: Appearance presets -> Layout (Advanced
  collapsible) -> Structure -> Surface (Widget layer collapsible) -> Behavior.
"""

from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
SERVICES_DIR = os.path.join(SHELL, "services")
COMMONS_DIR = os.path.join(SHELL, "commons")
UI_DIR = os.path.join(SHELL, "ui")


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class AtomicAxesAndPresetsTest(unittest.TestCase):
    """D4f atomic axes & write-only starter presets."""

    @classmethod
    def setUpClass(cls):
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))
        cls.presets = read(os.path.join(SERVICES_DIR, "BarStylePresets.js"))
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_retired_enums_removed_from_bar_defaults(self):
        match = re.search(r"var DEFAULTS = \{(.*?)\n\};", self.defaults, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        for retired in ("cornerStyle:", "borderless:", "showBackground:"):
            self.assertNotIn(retired, body)
        self.assertNotIn("BORDERLESS_MODES", self.defaults)

    def test_atomic_axes_and_vocabularies(self):
        for axis in ("backplate: true,", "lanePill: false,", "tint: false,",
                     'widgetStyle: "fused",', 'capsuleRadius: "pill",',
                     "widgetRadius: -1,", 'groupColor: "layer1",',
                     "edgeMargin: 5,", "sideMargin: -1,"):
            self.assertIn(axis, self.defaults, f"missing axis default: {axis}")
        self.assertIn('var WIDGET_STYLES = ["fused", "separate", "flat"];', self.defaults)
        self.assertIn('var CAPSULE_RADII = ["pill", "rounded", "px"];', self.defaults)
        self.assertIn('"transparent"', self.defaults)
        self.assertIn("function deriveStyle(", self.defaults)
        self.assertIn("function resolvedSideMargin(", self.defaults)
        self.assertIn("function styleBoost(", self.defaults)
        self.assertIn("function capsuleFullRadius(", self.defaults)
        self.assertIn("function capsuleMidRadius(", self.defaults)

    def test_six_starter_presets_without_persisted_preset_key(self):
        self.assertIn('var ORDER = ["hug", "floating", "islands", "material", "materialHug", "panel"];', self.presets)
        for key in ("hug:", "floating:", "islands:", "material:", "materialHug:", "panel:"):
            self.assertIn(key, self.presets)
        self.assertIn("function currentPreset(axes)", self.presets)
        self.assertIn("function applyBarStylePreset(key)", self.pc)
        self.assertNotIn("stylePreset:", self.defaults)

    def test_d8_retired_dark_bonuses(self):
        geom = read(os.path.join(COMMONS_DIR, "BarGeometry.js"))
        self.assertNotRegex(geom, r"\?\s*-6")
        self.assertNotIn("cornerStyle === 2", geom)
        self.assertNotIn("cornerStyle === 5", geom)
        # Only isLaneHug keeps +4 boost.
        self.assertIn("return style && style.isLaneHug ? 4 : 0;", self.defaults)
        # Islands midRadius 8 retired (unified to Appearance.rounding.unsharpenmore = 6).
        group = read(os.path.join(BAR_DIR, "BarGroup.qml"))
        self.assertNotIn("unsharpenmore + 2", group)
        self.assertIn("BarDefaults.capsuleFullRadius(", group)
        self.assertIn("BarDefaults.capsuleMidRadius(", group)
        self.assertIn('return customRadius >= 0 ? customRadius : unsharpenmore;', self.defaults)
        self.assertNotIn('Math.min(customRadius >= 0 ? customRadius : DEFAULTS.widgetRadius, unsharpenmore)', self.defaults)


class MigrationV7Test(unittest.TestCase):
    """v7 migration folds cornerStyle/borderless/showBackground into atomic axes."""

    @classmethod
    def setUpClass(cls):
        cls.migrations = read(os.path.join(SERVICES_DIR, "ConfigMigrations.js"))
        cls.config_service = read(os.path.join(SERVICES_DIR, "ConfigService.qml"))

    def test_v7_step_and_explicit_maps(self):
        self.assertIn("var CURRENT_VERSION = 7", self.migrations)
        self.assertIn("if (version < 7)", self.migrations)
        self.assertIn("function migrateBarStyleAxes(config, seed)", self.migrations)
        self.assertIn('var MIGRATED_STYLE_KEYS = ["cornerStyle", "borderless", "showBackground"]', self.migrations)
        for mode in ("pills:", "separated:", "segmented:", "transparent:", "flat:"):
            self.assertIn(mode, self.migrations)
        self.assertIn("# nyxuri-config-schema: 7", self.config_service)


class SingleStyleResolverTest(unittest.TestCase):
    """BarStyle.js is the single style resolution surface in plugins/bar/."""

    def test_bar_style_resolver_exists_and_clean(self):
        style_js = read(os.path.join(BAR_DIR, "BarStyle.js"))
        self.assertIn("function resolve(axes, env)", style_js)
        self.assertIn("function isTinted(axes)", style_js)
        self.assertIn("BarDefaults.deriveStyle", style_js)

    def test_no_retired_enum_strings_in_bar_plugin(self):
        forbidden = re.compile(r"\b(cornerStyle|borderless|showBackground|barCornerStyle|barBorderless|barShowBackground|barIsMaterial)\b")
        for root_dir, dirs, files in os.walk(BAR_DIR):
            dirs[:] = [d for d in dirs if d != "vendor"]
            for name in files:
                if not (name.endswith(".qml") or name.endswith(".js")):
                    continue
                path = os.path.join(root_dir, name)
                text = read(path)
                for lineno, line in enumerate(text.splitlines(), 1):
                    if line.lstrip().startswith("//"):
                        continue
                    self.assertIsNone(
                        forbidden.search(line),
                        f"{os.path.relpath(path, REPO_ROOT)}:{lineno} still references retired enum: {line.strip()}",
                    )


class AppearanceUiStructureTest(unittest.TestCase):
    """D4f settings UI ordering, visual picker, and Advanced collapsible group."""

    @classmethod
    def setUpClass(cls):
        cls.appearance = read(os.path.join(BAR_DIR, "BarAppearanceSection.qml"))
        cls.picker = read(os.path.join(UI_DIR, "PreferenceVisualPicker.qml"))

    def test_section_order_and_advanced_group(self):
        idx_appearance = self.appearance.index('I18n.tr("Appearance")')
        idx_layout = self.appearance.index('I18n.tr("Layout")')
        idx_advanced = self.appearance.index('I18n.tr("Advanced")')
        idx_structure = self.appearance.index('I18n.tr("Structure")')
        idx_surface = self.appearance.index('I18n.tr("Surface")')
        idx_behavior = self.appearance.index('I18n.tr("Behavior")')
        self.assertLess(idx_appearance, idx_layout)
        self.assertLess(idx_layout, idx_advanced)
        self.assertLess(idx_advanced, idx_structure)
        self.assertLess(idx_structure, idx_surface)
        self.assertLess(idx_surface, idx_behavior)
        self.assertIn('previewMode: "barStyle"', self.appearance)
        self.assertIn('previewMode === "barStyle"', self.picker)
        self.assertIn('PersonalizationConfig.applyBarStylePreset(', self.appearance)
        self.assertIn('PersonalizationConfig.setBarCapsuleRadius(', self.appearance)
        self.assertIn('PersonalizationConfig.setBarWidgetRadius(', self.appearance)
        self.assertIn('PersonalizationConfig.setBarTint(', self.appearance)
        self.assertIn('PersonalizationConfig.setBarLanePill(', self.appearance)


class BarOpacityAndBlurTest(unittest.TestCase):
    """Dedicated 3-tier bar opacity, blur wiring, and surface color consistency."""

    def test_appearance_col_layer0_consumes_background_opacity(self):
        appearance = read(os.path.join(COMMONS_DIR, "Appearance.qml"))
        self.assertIn("root.backgroundOpacity", appearance)
        self.assertRegex(appearance, r"property color colLayer0:\s*root\.transparentize\(colLayer0Base,\s*1 - root\.backgroundOpacity")

    def test_bar_opacity_and_blur_axes_and_unclamped_range(self):
        defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))
        pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))
        for axis in ("barOpacity: 1.0,", "blurEnabled: true,", "capsuleVerticalInset: 4,",
                     'widgetTextColor: "default",', 'lengthMode: "full",',
                     'leftScrollAction: "brightness",', 'rightScrollAction: "volume",',
                     "showScrollHints: true,"):
            self.assertIn(axis, defaults)
        # Ensure 0.3 opacity floor is removed for both surface and widget transparency.
        self.assertNotIn("Math.max(0.3,", pc)
        self.assertIn("Math.max(0, Math.min(1,", pc)

    def test_bar_chrome_and_island_consume_resolved_surface_color_and_blur(self):
        bar = read(os.path.join(BAR_DIR, "Bar.qml"))
        content = read(os.path.join(BAR_DIR, "BarContent.qml"))
        island = read(os.path.join(BAR_DIR, "DynamicIsland.qml"))
        self.assertIn('WlrLayershell.namespace: "nyxuri-shell-bar"', bar)
        self.assertIn("CompositorBlurRegion {", bar)
        self.assertIn("color: barRoot.resolvedSurfaceColor", bar)
        self.assertIn("opacity: barRoot.barVisualOpacity", bar)
        self.assertIn("materialPillBgColor: PersonalizationConfig.resolvedBarSurfaceColor(", content)
        self.assertIn("PersonalizationConfig.resolvedBarSurfaceColor(Appearance.colors.colLayer0, root.barAxes)", island)


if __name__ == "__main__":
    unittest.main()

"""D4e multi-bar & editing experience contract tests.

Pins the D4e e1 contract (shell/ROADMAP.md, D4e row; bar-config.md D4e):
- the single-bar gate lifts: normalizeBarConfigs keeps every [[bar.configs]]
  entry (unique ids, deterministic generated ids, singleton island claimed
  once across the WHOLE array);
- uids embed the bar scope (widgetId@barId.zoneindex) — unique across every
  bar so per-entry mutation never crosses bars;
- the entry gains a root-level enabled flag (machinery key, not a style
  axis; hidden-not-deleted follows the dux shape);
- minimal write goes per-entry: every entry persists while multi (a pristine
  sibling persists as its id — dropping it would delete that bar), a single
  factory-default bar still writes nothing;
- mutation core is per-id (withBarConfig) and the settings face routes
  through the selected entry (selectedBarId session state, never persisted);
- store APIs: addBarConfig / deleteBarConfig (factory entry and last-bar
  protection) / setBarEnabled / renameBarConfig;
- islandInLayout scans every entry (slot arbitration truth for whichever
  bar owns the island);
- barLayoutStateJson is the window rebuild signature: id/enabled/position/
  screenList only, horizontal entries sorted first (stable exclusive-zone
  claim order).
"""

from __future__ import annotations

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
SERVICES_DIR = os.path.join(SHELL, "services")
PROBE = os.path.join(SHELL, "scripts", "dev", "probe-bar.qml")
PROBE_SH = os.path.join(SHELL, "scripts", "dev", "probe-bar.sh")


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class MultiBarStoreTest(unittest.TestCase):
    """normalizeBarConfigs / sparse write / store APIs."""

    @classmethod
    def setUpClass(cls):
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_normalize_keeps_every_entry(self):
        # The old gate read source[0] and dropped the rest; the D4e shape
        # iterates the whole array.
        body = self.fn("normalizeBarConfigs")
        self.assertIn("for (let index = 0; index < source.length", body)
        self.assertIn("out.push({", body)
        self.assertIn("return out.length > 0 ? out : root.defaultBarConfigs()", body)
        self.assertNotIn("source[0]", body)

    def test_normalize_id_dedupe_and_generation(self):
        body = self.fn("normalizeBarConfigs")
        self.assertIn("seenIds", body)
        # First wins; id-less/duplicate entries get a deterministic free id
        # (same file, same ids, every load).
        self.assertIn('let candidate = serial === 1 ? "default" : "bar" + serial;', body)
        self.assertIn("while (seenIds.indexOf(candidate) !== -1 || candidate === id)", body)

    def test_normalize_threads_shared_singleton_bucket(self):
        body = self.fn("normalizeBarConfigs")
        self.assertIn("const usedSingletons = [];", body)
        # D4g 批四: the lane defaults are orientation-aware, so the load
        # normalize threads the entry's resolved position through.
        self.assertIn("root.normalizeConfigLanes(rawLanes, usedSingletons, id, root.normalizedEdgePosition(bar.position))", body)
        lanes = self.fn("normalizeConfigLanes")
        self.assertIn("const usedSingletons = sharedSingletons || [];", lanes)
        self.assertIn("root.normalizeLaneEntries(raw, zone, usedSingletons, scope)", lanes)
        self.assertIn("const defaults = root.defaultBarLayoutsFor(position);", lanes)

    def test_entry_enabled_flag(self):
        body = self.fn("normalizeBarConfigs")
        self.assertIn("enabled: bar.enabled !== false,", body)
        sparse = self.fn("sparseBarConfigEntry")
        self.assertIn("truth.enabled !== false", sparse)
        self.assertIn("out.enabled = false", sparse)

    def test_uid_embeds_bar_scope(self):
        body = self.fn("normalizeLaneEntries")
        self.assertIn('uid: canonical + "@" + scope + "." + zone + index,', body)
        for fn in ("addBarEntry", "moveBarComponent", "setBarLaneEntries"):
            self.assertIn('"@" + config.id + "."', self.fn(fn), f"{fn} mints an unscoped uid")

    def test_sparse_write_per_entry(self):
        body = self.fn("sparseBarConfigs")
        self.assertIn("const keepPristine = configs.length > 1;", body)
        self.assertIn("sparseBarConfigEntry(truth, fallback, keepPristine)", body)
        entry = self.fn("sparseBarConfigEntry")
        self.assertIn('truth.id === "default"', entry)
        self.assertIn("if (pristine && !keepPristine)", entry)
        self.assertIn("return null;", entry)

    def test_per_id_mutation_core(self):
        self.assertIn("function withBarConfig(barId, mutator)", self.pc)
        self.assertIn("return root.withBarConfig(root.activeBarConfig().id, mutator);", self.pc)
        core = self.fn("withBarConfig")
        self.assertIn("const changed = mutator(next[index], next);", core)

    def test_selection_is_session_state(self):
        self.assertIn('property string selectedBarId: ""', self.pc)
        body = self.fn("activeBarConfig")
        self.assertIn("root.barConfigById(root.selectedBarId)", body)

    def test_store_apis_exist(self):
        for fn in ("function addBarConfig(name)",
                   "function deleteBarConfig(barId)",
                   "function setBarEnabled(barId, enabled)",
                   "function renameBarConfig(barId, name)",
                   "function singletonIdsInUse(configs, exceptConfig, exceptZone)"):
            self.assertIn(fn, self.pc)

    def test_delete_guards(self):
        body = self.fn("deleteBarConfig")
        self.assertIn('root.barConfigs.length <= 1 || barId === "default"', body)
        self.assertIn("return false;", body)

    def test_add_bar_keeps_island_with_owner(self):
        body = self.fn("addBarConfig")
        self.assertIn("const usedSingletons = [];", body)
        self.assertIn("root.normalizeConfigLanes({}, usedSingletons, id)", body)

    def test_island_scan_spans_every_bar(self):
        self.assertIn('readonly property bool islandInLayout: root.anyBarUsesWidget("island")', self.pc)
        body = self.fn("anyBarUsesWidget")
        self.assertIn("root.barConfigs", body)

    def test_rebuild_signature(self):
        body = self.fn("barLayoutStateJson")
        for key in ("id: config.id", "enabled: config.enabled !== false",
                    "position: config.axes.position", "screens: config.axes.screenList"):
            self.assertIn(key, body)
        # Horizontal entries claim exclusive zones first (dux ShellCore
        # order), then by id for determinism.
        self.assertIn("aVertical - bVertical || String(a.id).localeCompare(String(b.id))", body)

    def fn(self, name: str) -> str:
        import re
        match = re.search(rf"function {name}\(.*?\) \{{(.*?)\n    \}}", self.pc, re.S)
        assert match, f"function {name} not found"
        return match.group(1)


class ProbeCoverageTest(unittest.TestCase):
    """The behavioral evidence lives in the probe: store round-trip and
    signature stability are asserted by probe-bar.sh's d4e section."""

    @classmethod
    def setUpClass(cls):
        cls.qml = read(PROBE)
        cls.sh = read(PROBE_SH)

    def test_probe_store_section(self):
        self.assertIn("function d4eStore()", self.qml)
        for key in ("singleNull", "uidUnique", "bar1PristineIdentity", "roundTripIds",
                    "islandBlockedMove", "defaultPositionUntouched", "refusedLast"):
            self.assertIn(key, self.qml, f"d4eStore no longer reports {key}")

    def test_probe_signature_section(self):
        self.assertIn("function d4eSignature()", self.qml)
        for key in ("styleStable", "positionMoved", "disableMoved"):
            self.assertIn(key, self.qml, f"d4eSignature no longer reports {key}")

    def test_probe_migration_and_windows_e6_fields(self):
        self.assertIn("function d4eMigrationV6()", self.qml)
        for key in ("version", "foldedOnEntry", "defaultsSkipped", "clockKept",
                    "flatStripped", "emptyIslandDeleted", "idempotent"):
            self.assertIn(key, self.qml, f"d4eMigrationV6 no longer reports {key}")
        for key in ("firstHeight", "secondHeight", "firstIconScale", "secondIconScale"):
            self.assertIn(key, self.qml, f"d4eWindowsDump no longer reports {key}")

    def test_shell_assertions_wired(self):
        self.assertIn("d4e_store_state", self.sh)
        self.assertIn("d4e_migration_v6_state", self.sh)
        self.assertIn("d4e_migration_v6_ok", self.sh)
        self.assertIn("d4e_ok = d4e_store_ok and d4e_signature_ok", self.sh)
        self.assertIn("and d4d_ok and d4e_ok", self.sh)


class SettingsSurfaceE4Test(unittest.TestCase):
    """D4e e4: multi-bar manager, list-based widgets editor, shared atoms."""

    @classmethod
    def setUpClass(cls):
        cls.bar_dir = os.path.join(SHELL, "plugins", "bar")
        cls.ui_dir = os.path.join(SHELL, "ui")

    def test_shared_atoms_added_and_header_supports_reset(self):
        for name in ("PreferenceGroup.qml", "PreferenceCollapsibleGroup.qml",
                     "PreferenceControlledBy.qml", "PreferenceVisualPicker.qml"):
            self.assertTrue(os.path.isfile(os.path.join(self.ui_dir, name)), f"missing {name}")
        with open(os.path.join(self.ui_dir, "PreferenceHeader.qml"), encoding="utf-8") as f:
            hdr = f.read()
        self.assertIn("signal resetRequested", hdr)
        self.assertIn("property bool showReset", hdr)

    def test_retired_chip_cards_stay_deleted(self):
        for retired in ("BarComponentsCard.qml", "SortableMultiSelectField.qml",
                        "LayoutDragCoordinator.qml"):
            self.assertFalse(os.path.exists(os.path.join(self.bar_dir, retired)),
                             f"{retired} must remain retired")

    def test_e4_surfaces_wired_to_per_bar_store(self):
        for name in ("BarManagerCard.qml", "BarLaneSection.qml",
                     "BarWidgetPickerPopup.qml", "QuickSettingsListCard.qml"):
            self.assertTrue(os.path.isfile(os.path.join(self.bar_dir, name)), f"missing {name}")
        with open(os.path.join(self.bar_dir, "BarManagerCard.qml"), encoding="utf-8") as f:
            mgr = f.read()
        for token in ("PersonalizationConfig.selectBar", "PersonalizationConfig.addBarConfig",
                      "PersonalizationConfig.deleteBarConfig", "PersonalizationConfig.renameBarConfig",
                      "PersonalizationConfig.setBarEnabled"):
            self.assertIn(token, mgr)
        with open(os.path.join(self.bar_dir, "BarModulesSection.qml"), encoding="utf-8") as f:
            mods = f.read()
        for token in ("BarLaneSection", "BarWidgetPickerPopup", "QuickSettingsListCard",
                      "PersonalizationConfig.resetBarLanes", "PersonalizationConfig.moveBarEntry"):
            self.assertIn(token, mods)
        with open(os.path.join(self.bar_dir, "BarAppearanceSection.qml"), encoding="utf-8") as f:
            app = f.read()
        for token in ("PreferenceGroup", "PreferenceVisualPicker",
                      "PersonalizationConfig.resetBarAxes",
                      "PersonalizationConfig.setBarIconScale",
                      "PersonalizationConfig.applyBarDensityPreset"):
            self.assertIn(token, app)
        with open(os.path.join(self.bar_dir, "BarWidgetPage.qml"), encoding="utf-8") as f:
            page = f.read()
        for token in ("PersonalizationConfig.resetBarWidgetOverrides", "signal routeRequested"):
            self.assertIn(token, page)


class IslandFoldingE5Test(unittest.TestCase):
    """D4e e5: island appearance axes fold onto the singleton island entry + v6."""

    @classmethod
    def setUpClass(cls):
        cls.bar_dir = os.path.join(SHELL, "plugins", "bar")
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarWidgetDefaults.js"))
        cls.migrations = read(os.path.join(SERVICES_DIR, "ConfigMigrations.js"))
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_defaults_and_v6_migration(self):
        for key in ("satellite", "showAvatar", "showMediaControls", "visualizerStyle", "hideDate"):
            self.assertIn(f"{key}:", self.defaults)
            self.assertIn(f'{key}: "{key}"', self.migrations)
        self.assertIn("var CURRENT_VERSION = 7", self.migrations)
        self.assertIn("function migrateIslandGlobals(config, seed)", self.migrations)
        self.assertIn("if (version < 6)", self.migrations)

    def test_island_runtime_reads_entry_and_bar_lanes(self):
        self.assertIn("function islandEntry()", self.pc)
        self.assertIn("function setIslandEntryOverride(key, value)", self.pc)
        di = read(os.path.join(self.bar_dir, "DynamicIsland.qml"))
        self.assertIn("property var widgetEntry: null", di)
        self.assertIn("property var widgetBar: null", di)
        self.assertIn("function option(key)", di)
        idle = read(os.path.join(self.bar_dir, "DiIdle.qml"))
        media = read(os.path.join(self.bar_dir, "DiMedia.qml"))
        self.assertIn('di.option("satellite")', idle)
        self.assertIn('di.option("showAvatar")', idle)
        self.assertIn("di.widgetBar.lanes", idle)
        self.assertIn('di.option("visualizerStyle")', media)
        self.assertIn('di.option("showMediaControls")', media)

    def test_island_options_registered(self):
        opts = os.path.join(self.bar_dir, "options", "IslandOptions.qml")
        self.assertTrue(os.path.isfile(opts))
        cat = read(os.path.join(SHELL, "ui", "BarWidgetCatalog.qml"))
        self.assertIn('island: "IslandOptions.qml"', cat)


class DensityAndPerBarLeafE6Test(unittest.TestCase):
    """D4e e6: DensityPresets, iconScale axis, and per-bar widget leaf convergence."""

    @classmethod
    def setUpClass(cls):
        cls.bar_dir = os.path.join(SHELL, "plugins", "bar")
        cls.density = read(os.path.join(SERVICES_DIR, "DensityPresets.js"))
        cls.bar_defaults = read(os.path.join(SERVICES_DIR, "BarDefaults.js"))
        cls.scale = read(os.path.join(cls.bar_dir, "BarScale.qml"))
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_density_presets_and_icon_scale(self):
        for token in ("var LEVELS =", "var PRESETS =", "comfortable", "compact", "spacious"):
            self.assertIn(token, self.density)
        self.assertIn("iconScale: 1.0", self.bar_defaults)
        self.assertIn("function fontFor(widgetBar)", self.scale)
        self.assertIn("function iconFor(widgetBar)", self.scale)
        for token in ("function setBarIconScale(", "function applyBarDensityPreset(",
                      "function resolvedBarHeight(", "function resolvedVerticalBarWidth(",
                      "function barStyleBoostFor("):
            self.assertIn(token, self.pc)

    def test_per_bar_leaves_drop_global_bar_style_reads(self):
        for name in ("Media.qml", "BatteryIndicator.qml", "SysTray.qml",
                     "ClockWidget.qml", "UpdatesCount.qml", "DocktoPanel.qml",
                     "Divisor.qml", "Spacer.qml"):
            content = read(os.path.join(self.bar_dir, name))
            self.assertIn("widgetBar", content, f"{name} missing widgetBar")
            for forbidden in ("Config.options.bar.bottom",
                              "Config.options?.bar?.bottom",
                              "Config.options.bar.vertical",
                              "Config.options.bar.cornerStyle",
                              "Config.options?.bar?.m3?.cornerStyle"):
                self.assertNotIn(forbidden, content, f"{name} still reads global {forbidden}")
        group = read(os.path.join(self.bar_dir, "BarGroup.qml"))
        self.assertIn("barAxes", group)
        self.assertNotIn("Config.options.bar.", group)


if __name__ == "__main__":
    unittest.main()

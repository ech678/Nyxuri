"""D4a bar customization engine contract tests.

Pins the D4a contract (shell/ROADMAP.md, D4a row):
- barConfigs array schema (lanes mix "clock" strings and {id, enabled,
  ...overrides} objects, single bar first, multi-bar ready);
- three-layer default fallback with a single option() entry point (widgets
  never touch storage directly — the host injects the entry);
- minimal write: the [bar] section only carries non-default keys;
- configVersion version chain with an explicit legacy key map;
- the widget catalog / componentNames registration: adding a widget is a
  fixed three-file registration (services defaults, ui catalog, bar file
  map) with a contract test pinning the id sets equal;
- spacer/separator are first-class widgets (divisor stays a legacy alias).
"""

from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
SERVICES_DIR = os.path.join(SHELL, "services")
UI_DIR = os.path.join(SHELL, "ui")


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def js_ids(content: str, header: str) -> set[str]:
    """Extract the quoted ids under `var <header> = [ ... ]` in a .pragma
    library JS file (flat string list only)."""
    match = re.search(rf"var {header} = \[(.*?)\];", content, re.S)
    assert match, f"{header} list not found"
    return set(re.findall(r'"([a-zA-Z_][a-zA-Z0-9_]*)"', match.group(1)))


def js_object_keys(content: str, header: str) -> set[str]:
    """Extract top-level keys under `var <header> = { ... }` (one nesting
    level, brace-balanced scan starting inside the opening brace)."""
    match = re.search(rf"var {header} = \{{", content)
    assert match, f"{header} table not found"
    depth = 1
    keys: set[str] = set()
    pos = match.end()
    pattern = re.compile(r"^[ \t]*([a-zA-Z_][a-zA-Z0-9_]*):", re.M)
    while pos < len(content):
        char = content[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                break
        elif char == "\n" and depth == 1:
            line_match = pattern.match(content, pos + 1)
            if line_match:
                keys.add(line_match.group(1))
        pos += 1
    return keys


class RegistryAlignmentTest(unittest.TestCase):
    """Adding a widget is exactly three code registrations plus the D4b
    options-page map (four id-bearing surfaces), and the id sets cannot
    drift apart."""

    @classmethod
    def setUpClass(cls):
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarWidgetDefaults.js"))
        cls.catalog = read(os.path.join(UI_DIR, "BarWidgetCatalog.qml"))
        cls.files = read(os.path.join(BAR_DIR, "BarWidgetFiles.js"))
        cls.ids = js_ids(cls.defaults, "IDS")
        cls.defaults_keys = js_object_keys(cls.defaults, "DEFAULTS")
        cls.catalog_ids = set(re.findall(r'id: "([a-zA-Z_][a-zA-Z0-9_]*)"', cls.catalog))
        cls.files_keys = js_object_keys(cls.files, "FILES")

    def test_id_sets_identical(self):
        self.assertTrue(self.ids, "IDS list is empty")
        self.assertEqual(self.ids, self.catalog_ids,
                         "ui/BarWidgetCatalog.qml ids diverge from BarWidgetDefaults.IDS")
        self.assertEqual(self.ids, self.files_keys,
                         "plugins/bar/BarWidgetFiles.js ids diverge from BarWidgetDefaults.IDS")

    def test_defaults_cover_every_widget(self):
        # quickSettings is aliased to utilButtons outside the literal (one
        # component, one axes table — pinned by test_d4b).
        self.assertIn("DEFAULTS.quickSettings = DEFAULTS.utilButtons", self.defaults)
        self.assertEqual(self.ids - {"quickSettings"}, self.defaults_keys,
                         "every widget id needs a DEFAULTS entry (empty table is fine)")

    def test_whitelist_is_derived_not_duplicated(self):
        pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))
        self.assertIn("BarWidgetDefaults.IDS", pc,
                      "the storage whitelist must derive from BarWidgetDefaults.IDS")
        self.assertNotIn('property var barComponentIds: ["', pc,
                         "a literal whitelist would be a fourth registration point")

    def test_legacy_aliases_only_map_to_canonical_ids(self):
        aliases = js_object_keys(self.defaults, "LEGACY_ID_ALIASES")
        for value in re.findall(r':\s*"([a-zA-Z_][a-zA-Z0-9_]*)"',
                                re.search(r"var LEGACY_ID_ALIASES = \{(.*?)\};",
                                          self.defaults, re.S).group(1)):
            self.assertIn(value, self.ids, f"alias target {value} is not canonical")

    def test_divisor_is_separator_alias_and_spacer_exists(self):
        self.assertIn("divisor", js_object_keys(self.defaults, "LEGACY_ID_ALIASES"))
        self.assertEqual(
            re.search(r'divisor:\s*"([a-zA-Z_][a-zA-Z0-9_]*)"', self.defaults).group(1),
            "separator")
        self.assertIn("spacer", self.ids)
        self.assertIn('spacer: "Spacer.qml"', self.files)
        self.assertTrue(os.path.exists(os.path.join(BAR_DIR, "Spacer.qml")))

    def test_singleton_list_covers_island(self):
        singletons = js_ids(self.defaults, "SINGLETON_IDS")
        self.assertEqual(singletons, {"island"})


class FallbackChainTest(unittest.TestCase):
    """The single option() entry point and the injection protocol."""

    def test_option_implements_three_layers(self):
        defaults = read(os.path.join(SERVICES_DIR, "BarWidgetDefaults.js"))
        self.assertIn("function option(widgetId, entry, key)", defaults)
        # Layer order: entry overrides -> widget defaults -> global fallback.
        self.assertLess(defaults.index("entry.overrides[key] !== undefined"),
                        defaults.index("DEFAULTS[widgetId]"))
        self.assertLess(defaults.index("DEFAULTS[widgetId]"),
                        defaults.index("GLOBAL_DEFAULTS[key]"))

    def test_spacer_consumes_the_injection_protocol(self):
        spacer = read(os.path.join(BAR_DIR, "Spacer.qml"))
        self.assertIn("property var widgetEntry: null", spacer)
        self.assertIn('BarWidgetDefaults.option("spacer", root.widgetEntry, "size")', spacer)
        self.assertNotIn("PersonalizationConfig", spacer,
                         "a widget must not read the store directly")

    def test_hosts_inject_entries(self):
        for name in ("BarContent.qml", "VerticalBarContent.qml"):
            content = read(os.path.join(BAR_DIR, name))
            self.assertIn("function injectWidgetEntry(loader, entry)", content, name)
            self.assertIn("widgetEntry: modelData", content, name)
            self.assertIn("item.widgetEntry !== undefined", content, name)
            # Disabled entries are not instantiated at all.
            self.assertIn("entry.enabled !== false", content, name)

    def test_bar_group_carries_the_entry(self):
        group = read(os.path.join(BAR_DIR, "BarGroup.qml"))
        self.assertIn("property var widgetEntry: null", group)

    def test_bridge_serves_enabled_ids_only(self):
        bridge = read(os.path.join(SERVICES_DIR, "Config.qml"))
        self.assertIn('PersonalizationConfig.barLayoutEnabledIds("left")', bridge)
        self.assertIn('PersonalizationConfig.barLayoutEnabledIds("middle")', bridge)
        self.assertIn('PersonalizationConfig.barLayoutEnabledIds("right")', bridge)


class BarConfigsSchemaTest(unittest.TestCase):
    """barConfigs truth, derived views and entry-granular mutations."""

    @classmethod
    def setUpClass(cls):
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_single_truth_with_derived_views(self):
        self.assertIn("property var barConfigs: root.defaultBarConfigs()", self.pc)
        self.assertIn('readonly property var barLayoutLeft: root.laneIds("left")', self.pc)
        self.assertIn('readonly property var barLayoutEntriesLeft: root.laneEntries("left")', self.pc)
        # D4e: the island scan spans every bar entry (the island lives on
        # exactly one bar, whichever it is).
        self.assertIn('readonly property bool islandInLayout: root.anyBarUsesWidget("island")', self.pc)
        # Two-zone mirrors retired as properties (resolveBarLayouts still
        # reads the legacy FILE keys for pre-v3 migration).
        self.assertNotIn("property var barLeadingComponents", self.pc)
        self.assertNotIn("property var barTrailingComponents", self.pc)

    def test_normalize_accepts_strings_and_objects(self):
        self.assertIn("raw.widgetId !== undefined ? raw.widgetId : raw.id", self.pc)
        self.assertIn("raw.enabled !== false", self.pc)
        self.assertIn("overrides", self.pc)
        # Singleton dedupe during normalize, duplicates otherwise legal.
        self.assertIn("SINGLETON_IDS.indexOf(canonical) !== -1", self.pc)

    def test_entry_mutations_exist(self):
        for fn in ("function setBarLaneEntries(zone, entries)",
                   "function setBarEntryEnabled(uid, enabled)",
                   "function setBarEntryOverride(uid, key, value)",
                   "function addBarEntry(zone, widgetId, index)",
                   "function moveBarEntry(uid, zone, index)",
                   "function removeBarEntry(uid)",
                   "function toggleBarEntryEnabled(uid)"):
            self.assertIn(fn, self.pc)

    def test_mutations_clone_reassign_notify_once(self):
        self.assertIn("function withBarConfigs(mutator)", self.pc)
        self.assertIn("root.barConfigs = next", self.pc)

    def test_uid_session_scoped_never_persisted(self):
        # serializeBarEntry builds the persisted shape; the entry envelope
        # (uid) must not leak into it.
        body = self.pc[self.pc.index("function serializeBarEntry(entry)"):]
        body = body[:body.index("\n    function ")]
        self.assertNotIn("uid", body)


class MinimalWriteTest(unittest.TestCase):
    """The [bar] section only carries deviations."""

    @classmethod
    def setUpClass(cls):
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_diff_pipeline_present(self):
        for fn in ("function barSectionJson()",
                   "function barSectionRaw()",
                   "function barSectionDefaults()",
                   "function diffSparseSection(value, defaults)",
                   "function sparseBarConfigs()"):
            self.assertIn(fn, self.pc)

    def test_default_equal_entries_collapse_to_strings(self):
        body = self.pc[self.pc.index("function serializeBarEntry"):]
        body = body[:body.index("\n    function ")]
        self.assertIn("return entry.widgetId;", body)

    def test_all_default_bar_section_disappears(self):
        self.assertIn("if (json.bar && Object.keys(json.bar).length === 0)", self.pc)
        self.assertIn("delete json.bar", self.pc)

    def test_config_version_written(self):
        self.assertIn('"configVersion": ConfigMigrations.CURRENT_VERSION', self.pc)


class VersionChainTest(unittest.TestCase):
    """configVersion stepwise migration with an explicit key map."""

    @classmethod
    def setUpClass(cls):
        cls.migrations = read(os.path.join(SERVICES_DIR, "ConfigMigrations.js"))
        cls.config_service = read(os.path.join(SERVICES_DIR, "ConfigService.qml"))

    def test_version_constants(self):
        # D4e e5 bumped the chain to 6 (island axes on the lane entry);
        # the LEGACY floor stays 2.
        self.assertIn("var CURRENT_VERSION = 6", self.migrations)
        self.assertIn("var LEGACY_VERSION = 2", self.migrations)

    def test_explicit_legacy_layout_keys(self):
        keys = js_ids(self.migrations, "LEGACY_LAYOUT_KEYS")
        self.assertEqual(keys, {"barLayoutLeft", "barLayoutMiddle", "barLayoutRight",
                                "barLeadingComponents", "barTrailingComponents"})

    def test_chain_runs_pending_steps_and_stamps(self):
        self.assertIn("function migrateConfig(parsed, seed)", self.migrations)
        self.assertIn("config.configVersion = version", self.migrations)

    def test_load_path_runs_the_chain_before_section_reads(self):
        pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))
        self.assertIn("ConfigMigrations.migrateConfig(parsed,", pc)
        self.assertLess(pc.index("ConfigMigrations.migrateConfig(parsed,"),
                        pc.index("const source = configSection(migration.config)"))

    def test_stamp_bumped_and_fast_path_keeps_v2(self):
        # D4e e5 writes stamp 6; the fast path accepts 2..6.
        self.assertIn("# nyxuri-config-schema: 6\\n", self.config_service)
        self.assertIn('"# nyxuri-config-schema: 2"', self.config_service)
        self.assertIn('"# nyxuri-config-schema: 3"', self.config_service)
        self.assertIn('"# nyxuri-config-schema: 4"', self.config_service)
        self.assertIn('"# nyxuri-config-schema: 5"', self.config_service)
        self.assertIn('"# nyxuri-config-schema: 6"', self.config_service)


class CatalogConsumersTest(unittest.TestCase):
    """The settings surfaces consume the unified catalog (D4e e4 list editor)."""

    def test_card_uses_catalog_and_entries(self):
        modules = read(os.path.join(BAR_DIR, "BarModulesSection.qml"))
        self.assertIn("BarWidgetCatalog {", modules)
        self.assertIn("PersonalizationConfig.barLayoutEntriesLeft", modules)
        self.assertNotIn("PersonalizationConfig.barComponentOptions", modules)
        picker = read(os.path.join(BAR_DIR, "BarWidgetPickerPopup.qml"))
        self.assertIn("widgetCatalog.options()", picker)

    def test_field_supports_entries_and_enabled_toggle(self):
        section = read(os.path.join(BAR_DIR, "BarLaneSection.qml"))
        self.assertIn("signal configureRequested(string entryUid)", section)
        self.assertIn("PersonalizationConfig.setBarEntryEnabled(", section)
        self.assertIn("PersonalizationConfig.removeBarEntry(", section)

    def test_coordinator_drags_by_uid(self):
        modules = read(os.path.join(BAR_DIR, "BarModulesSection.qml"))
        self.assertIn("property string dragUid:", modules)
        self.assertIn("PersonalizationConfig.moveBarEntry(uid, zone, index)", modules)

    def test_dashboard_uses_shared_catalog(self):
        card = read(os.path.join(REPO_ROOT, "shell", "plugins", "settings",
                                 "dashwindow", "DashboardBarLayoutCard.qml"))
        self.assertIn("BarWidgetCatalog {", card)
        self.assertFalse(os.path.exists(os.path.join(UI_DIR, "DashboardBarWidgets.qml")),
                         "the dashboard-private catalog must stay retired")

    def test_catalog_labels_lazy_translated(self):
        catalog = read(os.path.join(UI_DIR, "BarWidgetCatalog.qml"))
        # Untranslated literals + displayName() resolution (dictionary loads
        # after construction).
        self.assertIn('label: "Clock"', catalog)
        self.assertIn("function displayName(entry)", catalog)
        self.assertIn("return I18n.tr(entry.label)", catalog)


class ProbeSurfaceTest(unittest.TestCase):
    """The runtime probe exposes the D4a evidence (drove by
    test_bar_runtime's full run; the global ok gate includes d4a)."""

    def test_probe_functions_registered(self):
        probe = read(os.path.join(SHELL, "scripts", "dev", "probe-bar.qml"))
        for fn in ("function d4aEntriesSet(scene: string): string",
                   "function d4aEntriesDump(): string",
                   "function d4aSingletons(): string",
                   "function d4aMigration(): string",
                   "function d4aPersistence(): string"):
            self.assertIn(fn, probe)
        self.assertIn('import "services/ConfigMigrations.js" as ConfigMigrations', probe)

    def test_probe_reports_widget_ids_in_lanes(self):
        probe = read(os.path.join(SHELL, "scripts", "dev", "probe-bar.sh"))
        self.assertIn('"d4a": {', probe)
        self.assertIn("d4a_ok ", probe, "the global ok gate must include the d4a evidence")


if __name__ == "__main__":
    unittest.main()

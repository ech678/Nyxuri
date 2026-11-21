"""D4b per-widget instance config contract tests.

Pins the D4b contract (shell/ROADMAP.md, D4b row):
- the DEFAULTS axes table (every value equals the pre-D4b behavior);
- the v4 migration folds the flat [bar] per-widget keys and [time]
  .dateFormat onto the lane entries (explicit key map, deviations only,
  idempotent);
- widgets consume the injection protocol (widgetEntry + option()) and the
  retired flat reads are gone from the store, the bridge and the settings
  surfaces;
- the click-action vocabulary is closed and argv-only (never a shell
  string), dispatched through ActionGateway;
- the fourth registration point: the catalog optionsFiles map, its pages
  exist and every page is storage-blind (page facade only).
"""

from __future__ import annotations

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL = os.path.join(REPO_ROOT, "shell")
BAR_DIR = os.path.join(SHELL, "plugins", "bar")
OPTIONS_DIR = os.path.join(BAR_DIR, "options")
SERVICES_DIR = os.path.join(SHELL, "services")
UI_DIR = os.path.join(SHELL, "ui")


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


def js_ids(content: str, header: str) -> set[str]:
    """The quoted ids of `var <header> = [ "a", "b", ... ];`."""
    match = re.search(rf"var {header} = \[(.*?)\];", content, re.S)
    assert match, f"{header} list not found"
    return set(re.findall(r'"([a-zA-Z_][a-zA-Z0-9_]*)"', match.group(1)))


def js_object_keys(body: str) -> set[str]:
    return set(re.findall(r'^\s{4}([a-zA-Z_][a-zA-Z0-9_]*):', body, re.M))


WIDGETS_WITH_ENTRY = (
    "Workspaces.qml", "ClockWidget.qml", "UtilButtons.qml", "Resources.qml",
    "Divisor.qml", "SysTray.qml", "BatteryIndicator.qml",
    "Media.qml", "ActiveWindow.qml", "WeatherBar.qml", "LauncherButton.qml",
    "PowerButton.qml",
)

# Flat keys the v4 migration folds away — nothing may read them anymore
# (store properties, bridge mappings, settings surfaces).
RETIRED_FLAT_READS = (
    "PersonalizationConfig.barShowAppIcons",
    "PersonalizationConfig.barAlwaysShowNumbers",
    "PersonalizationConfig.barWorkspaceIndicatorStyle",
    "PersonalizationConfig.barWorkspaceStyle",
    "PersonalizationConfig.barWorkspaceShown",
    "PersonalizationConfig.barWorkspaceNumberStyle",
    "PersonalizationConfig.barResourceStyle",
    "PersonalizationConfig.barShowCpu",
    "PersonalizationConfig.barShowCpuTemp",
    "PersonalizationConfig.barShowRam",
    "PersonalizationConfig.barShowDisk",
    "PersonalizationConfig.barShowSwap",
    "PersonalizationConfig.barShowScreenSnip",
    "PersonalizationConfig.barShowKeyboardToggle",
    "PersonalizationConfig.barShowMicToggle",
    "PersonalizationConfig.barShowWallpaperToggle",
    "PersonalizationConfig.barShowDarkModeToggle",
    "PersonalizationConfig.barShowPerformanceProfile",
    "PersonalizationConfig.barTrayFilterPassive",
    "PersonalizationConfig.barTrayShowItemId",
    "PersonalizationConfig.barTrayMonochromeIcons",
    "PersonalizationConfig.barDividerStyle",
    "PersonalizationConfig.barDividerSpacing",
    "PersonalizationConfig.timeDateFormat",
)


class DefaultsAxesTest(unittest.TestCase):
    """The per-widget axes table: defaults equal the pre-D4b behavior."""

    @classmethod
    def setUpClass(cls):
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarWidgetDefaults.js"))

    def axes(self, widget: str) -> dict:
        body = js_var_body(self.defaults, "DEFAULTS")
        match = re.search(rf"^\s{{4}}{widget}: \{{(.*?)^\s{{4}}\}}", body, re.M | re.S)
        assert match, f"{widget} axes not found"
        axes = {}
        for key, value in re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*):\s*("(?:[^"]*)"|[\d.]+|\[\]|true|false)', match.group(1)):
            axes[key] = value
        return axes

    def test_spacer_and_separator(self):
        self.assertEqual(self.axes("spacer"), {"size": "20"})
        self.assertEqual(self.axes("separator"), {"style": '"rect"', "spacing": "4"})

    def test_clock_axes(self):
        axes = self.axes("clock")
        self.assertEqual(axes["showDate"], "true")
        self.assertEqual(axes["dateFormat"], '""')
        self.assertEqual(axes["clickAction"], '"none"')
        self.assertEqual(axes["middleClickAction"], '"none"')
        self.assertEqual(axes["rightClickAction"], '"none"')
        self.assertEqual(axes["clickCommand"], "[]")

    def test_workspaces_axes(self):
        axes = self.axes("workspaces")
        self.assertEqual(axes["showAppIcons"], "false")
        self.assertEqual(axes["alwaysShowNumbers"], "true")
        self.assertEqual(axes["indicatorStyle"], '"dot"')
        self.assertEqual(axes["style"], '"default"')
        self.assertEqual(axes["numberStyle"], '"normal"')
        self.assertEqual(axes["shown"], "10")
        self.assertEqual(axes["activeColorMode"], '"theme"')
        self.assertEqual(axes["occupiedColorMode"], '"theme"')

    def test_system_monitor_axes(self):
        axes = self.axes("systemMonitor")
        self.assertEqual(axes["cpu"], "true")
        self.assertEqual(axes["cpuTemp"], "false")
        self.assertEqual(axes["ram"], "true")
        self.assertEqual(axes["disk"], "false")
        self.assertEqual(axes["swap"], "false")
        self.assertEqual(axes["iconStyle"], '"outline"')
        self.assertEqual(axes["showValue"], "false")

    def test_tray_battery_media_active_window(self):
        self.assertEqual(self.axes("tray"), {
            "tintIcons": "true", "hidePassive": "true", "showItemId": "false",
        })
        self.assertEqual(self.axes("battery"), {
            "showPercent": "true", "showPower": "false",
            "clickAction": '"none"', "middleClickAction": '"none"',
            "rightClickAction": '"none"', "clickCommand": "[]",
        })
        media = self.axes("media")
        self.assertEqual(media["minWidth"], "160")
        self.assertEqual(media["maxWidth"], "300")
        self.assertEqual(media["showTitle"], "true")
        self.assertEqual(media["scrollAction"], '"none"')
        self.assertEqual(self.axes("activeWindow")["maxWidth"], "280")

    def test_util_buttons_and_quick_settings_share_one_table(self):
        self.assertIn("DEFAULTS.quickSettings = DEFAULTS.utilButtons", self.defaults)
        files = read(os.path.join(BAR_DIR, "BarWidgetFiles.js"))
        self.assertIn('quickSettings: "UtilButtons.qml"', files)
        self.assertIn('utilButtons: "UtilButtons.qml"', files)

    def test_number_map_helper_moved(self):
        self.assertIn("function workspaceNumberMap(style)", self.defaults)
        pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))
        self.assertNotIn("_barWorkspaceNumberHanMaps", pc,
                         "the number glyph maps must live in BarWidgetDefaults, not the store")


class MigrationV4Test(unittest.TestCase):
    """The v4 step: explicit key map folding flat keys onto entries."""

    @classmethod
    def setUpClass(cls):
        cls.migrations = read(os.path.join(SERVICES_DIR, "ConfigMigrations.js"))
        cls.defaults = read(os.path.join(SERVICES_DIR, "BarWidgetDefaults.js"))
        cls.config_service = read(os.path.join(SERVICES_DIR, "ConfigService.qml"))
        cls.pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))

    def test_version_constants(self):
        # D4c bumped the chain to 5; the v4 step itself is unchanged.
        self.assertIn("var CURRENT_VERSION = 5", self.migrations)

    def test_stamp_bumped_and_fast_path_keeps_older(self):
        # D4c writes stamp 5; the fast path accepts 2..5.
        self.assertIn("# nyxuri-config-schema: 5\\n", self.config_service)
        for stamp in ("2", "3", "4", "5"):
            self.assertIn(f'"# nyxuri-config-schema: {stamp}"', self.config_service)

    def test_migration_map_targets_canonical_ids(self):
        ids = js_ids(self.defaults, "IDS")
        body = js_var_body(self.migrations, "MIGRATED_WIDGET_GLOBALS")
        for match in re.finditer(r"^\s{4}([a-zA-Z_][a-zA-Z0-9_]*): \{", body, re.M):
            self.assertIn(match.group(1), ids, f"migration targets unknown widget {match.group(1)}")

    def test_every_migration_entry_key_is_a_real_axis(self):
        defaults_body = js_var_body(self.defaults, "DEFAULTS")
        defaults_keys = js_object_keys(defaults_body)
        defaults_keys.add("quickSettings")  # aliased outside the literal
        body = js_var_body(self.migrations, "MIGRATED_WIDGET_GLOBALS")
        pairs = [m.groups() for m in re.finditer(r"^\s{4}([a-zA-Z_][a-zA-Z0-9_]*): \{(.*?)^\s{4}\}", body, re.M | re.S)]
        self.assertTrue(pairs)
        for widget, block in pairs:
            # quickSettings shares the utilButtons table (one component).
            axes_widget = "utilButtons" if widget == "quickSettings" else widget
            for entry_key in re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*): \[", block):
                self.assertIn(widget, defaults_keys)
                widget_axes = self.axes_of(defaults_body, axes_widget)
                self.assertIn(entry_key, widget_axes,
                              f"{widget}.{entry_key} migrates but is not a declared axis")

    @staticmethod
    def axes_of(defaults_body: str, widget: str) -> set:
        match = re.search(rf"^\s{{4}}{widget}: \{{(.*?)^\s{{4}}\}}", defaults_body, re.M | re.S)
        assert match, f"{widget} axes missing"
        return set(re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*):", match.group(1)))

    def test_clock_date_format_folds_from_time_section(self):
        self.assertIn('id === "clock"', self.migrations)
        self.assertIn("legacyDateFormat", self.migrations)
        self.assertIn("delete timeSection.dateFormat", self.migrations)

    def test_deviation_only_fold(self):
        # Default-equal globals skip (the minimal writer would drop them).
        self.assertIn("value === defaults[id][entryKey]", self.migrations)

    def test_store_passes_the_defaults_seed(self):
        self.assertIn("defaults: BarWidgetDefaults.DEFAULTS", self.pc)


class WidgetConsumptionTest(unittest.TestCase):
    """Widgets resolve axes through the injection protocol only."""

    def test_widgets_declare_entry_and_option(self):
        for name in WIDGETS_WITH_ENTRY:
            content = read(os.path.join(BAR_DIR, name))
            self.assertIn("property var widgetEntry", content, name)
            self.assertIn("widgetEntry", content.replace("property var widgetEntry", "", 1), name)
            self.assertTrue("BarWidgetDefaults.option(" in content or "BarWidgetActions.dispatchMouse(" in content,
                            f"{name} resolves no entry axis")

    def test_widgets_subcomponents_resolve_through_their_root(self):
        # Sub-components of the resources widget receive the axes from the
        # widget root, never from the bridge.
        resource = read(os.path.join(BAR_DIR, "Resource.qml"))
        self.assertIn('property string iconStyle: "outline"', resource)
        self.assertIn("property bool showValue: false", resource)
        self.assertNotIn("Config.options.bar.m3.resources.style", resource)
        resources = read(os.path.join(BAR_DIR, "Resources.qml"))
        self.assertIn("iconStyle: root.iconStyle", resources)

    def test_tray_filter_is_per_instance(self):
        systray = read(os.path.join(BAR_DIR, "SysTray.qml"))
        self.assertIn('BarWidgetDefaults.option("tray", root.widgetEntry, "hidePassive")', systray)
        self.assertIn("root.hidePassive", systray)
        service = read(os.path.join(BAR_DIR, "TrayService.qml"))
        self.assertNotIn("smartTray", service)
        self.assertNotIn("i.status !== Status.Passive", service,
                         "the service must never filter passive items (per-instance render concern)")

    def test_retired_flat_reads_are_gone_everywhere(self):
        for root_dir in (BAR_DIR, os.path.join(BAR_DIR, "options"), SERVICES_DIR, UI_DIR):
            for name in os.listdir(root_dir):
                if not name.endswith((".qml", ".js")):
                    continue
                content = read(os.path.join(root_dir, name))
                for needle in RETIRED_FLAT_READS:
                    self.assertNotIn(needle, content, f"{name} still reads {needle}")

    def test_bridge_dropped_the_migrated_mappings(self):
        bridge = read(os.path.join(SERVICES_DIR, "Config.qml"))
        for needle in ("barResourceStyle", "barShowRam", "barShowScreenSnip",
                       "barTrayMonochromeIcons", "barShowAppIcons", "barDividerStyle",
                       "timeDateFormat", "barWorkspaceNumberMap"):
            self.assertNotIn(needle, bridge)

    def test_date_time_singleton_lost_the_global_long_form(self):
        datetime_qml = read(os.path.join(SERVICES_DIR, "DateTime.qml"))
        self.assertNotIn("property string date:", datetime_qml)
        self.assertNotIn("longDate", datetime_qml)


class ClickActionsTest(unittest.TestCase):
    """The click vocabulary is closed and argv-only."""

    @classmethod
    def setUpClass(cls):
        cls.actions = read(os.path.join(BAR_DIR, "BarWidgetActions.qml"))
        cls.qmldir = read(os.path.join(BAR_DIR, "qmldir"))

    def test_singleton_registered(self):
        self.assertIn("singleton BarWidgetActions 1.0 BarWidgetActions.qml", self.qmldir)

    def test_closed_vocabulary(self):
        match = re.search(r"property var ids: \[(.*?)\]", self.actions, re.S)
        assert match
        ids = re.findall(r'"([a-z-]+)"', match.group(1))
        self.assertEqual(ids, ["default", "none", "dashboard", "quicksettings",
                               "launcher", "overview", "power-menu", "lock", "command"])

    def test_argv_only_never_a_shell_string(self):
        self.assertNotIn('"sh"', self.actions)
        self.assertNotIn('"bash"', self.actions)
        self.assertNotIn("-c", re.sub(r"--", "", self.actions.replace("Qt.MiddleButton", "")))
        self.assertIn("Array.isArray(command)", self.actions)
        self.assertIn("ActionGateway.execute(command, owner)", self.actions)

    def test_dispatch_goes_through_the_gateway(self):
        for target in ("dashboard", "quicksettings", "launcher", "overview", "power-menu", "lock"):
            self.assertIn(target, self.actions)

    def test_widgets_dispatch_via_the_shared_helper(self):
        for name in ("ClockWidget.qml", "BatteryIndicator.qml", "WeatherBar.qml",
                     "LauncherButton.qml", "PowerButton.qml", "ActiveWindow.qml"):
            content = read(os.path.join(BAR_DIR, name))
            self.assertIn("BarWidgetActions.dispatchMouse(", content, name)


class OptionsPagesTest(unittest.TestCase):
    """The fourth registration point and its storage-blind pages."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = read(os.path.join(UI_DIR, "BarWidgetCatalog.qml"))
        defaults = read(os.path.join(SERVICES_DIR, "BarWidgetDefaults.js"))
        cls.ids = js_ids(defaults, "IDS")
        match = re.search(r"property var optionsFiles: \(\{(.*?)\}\)", cls.catalog, re.S)
        assert match, "optionsFiles map not found"
        cls.files = dict(re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*):\s*"([A-Za-z]+\.qml)"', match.group(1)))

    def test_every_options_id_is_canonical(self):
        self.assertTrue(self.files)
        for widget in self.files:
            self.assertIn(widget, self.ids)

    def test_every_options_file_exists(self):
        for widget, file in self.files.items():
            self.assertTrue(os.path.exists(os.path.join(OPTIONS_DIR, file)),
                            f"{widget} -> options/{file} is missing")

    def test_quick_settings_shares_the_util_buttons_page(self):
        self.assertEqual(self.files["quickSettings"], self.files["utilButtons"])

    def test_pages_are_storage_blind(self):
        for widget, file in self.files.items():
            if file == "UtilButtonsOptions.qml":
                continue  # carries the shared quickpanel data-shape rows
            content = read(os.path.join(OPTIONS_DIR, file))
            self.assertIn("property var page: null", content, f"{file}")
            self.assertNotIn("PersonalizationConfig.setBarEntryOverride", content,
                             f"{file} must write through the page facade")

    def test_click_rows_are_the_single_canonical_section(self):
        for file in ("ClockOptions.qml", "BatteryOptions.qml", "ActiveWindowOptions.qml",
                     "LauncherButtonOptions.qml", "PowerButtonOptions.qml", "WeatherOptions.qml"):
            content = read(os.path.join(OPTIONS_DIR, file))
            self.assertIn("WidgetClickRows {", content, file)
            # No hand-rolled duplicates.
            self.assertNotIn('"clickAction"', content, f"{file} re-declares click rows")

    def test_options_loader_injects_the_facade(self):
        host = read(os.path.join(BAR_DIR, "BarWidgetPage.qml"))
        self.assertIn("property string widgetUid", host)
        self.assertIn("function value(key)", host)
        self.assertIn("function set(key, value)", host)
        self.assertIn("item.page = root", host)
        self.assertIn("optionsFile", host)


class SettingsSurfaceTest(unittest.TestCase):
    """The widget-scoped rows retired; the chip gear carries the entry."""

    def test_modules_section_retired_the_widget_groups(self):
        section = read(os.path.join(BAR_DIR, "BarModulesSection.qml"))
        for needle in RETIRED_FLAT_READS:
            self.assertNotIn(needle, section)
        self.assertIn("signal widgetEditorRequested(string entryUid)", section)

    def test_appearance_section_keeps_frame_axes_only(self):
        section = read(os.path.join(BAR_DIR, "BarAppearanceSection.qml"))
        self.assertNotIn("setBarDividerStyle", section)
        self.assertNotIn("setTimeDateFormat", section)

    def test_chip_field_has_the_gear(self):
        field = read(os.path.join(BAR_DIR, "SortableMultiSelectField.qml"))
        self.assertIn("signal configureRequested(string entryKey)", field)
        self.assertIn("configureButton", field)
        self.assertIn("root.configureRequested(chipDelegate.entryKey)", field)

    def test_card_and_page_route_the_editor(self):
        card = read(os.path.join(BAR_DIR, "BarComponentsCard.qml"))
        self.assertIn("signal widgetConfigureRequested(string entryUid)", card)
        page = read(os.path.join(BAR_DIR, "GeneralBarPage.qml"))
        self.assertIn("function openWidgetEditor(uid)", page)
        self.assertIn("onWidgetEditorRequested:", page)

    def test_store_keeps_tray_shared_state_only(self):
        pc = read(os.path.join(SERVICES_DIR, "PersonalizationConfig.qml"))
        self.assertIn("barTrayPinnedItems", pc)
        self.assertIn("barTrayInvertPinnedItems", pc)
        self.assertNotIn('"filterPassive"', pc)
        self.assertNotIn('"monochromeIcons"', pc)


class ProbeSurfaceTest(unittest.TestCase):
    """The runtime probe exposes the D4b evidence."""

    def test_probe_functions_registered(self):
        probe = read(os.path.join(SHELL, "scripts", "dev", "probe-bar.qml"))
        for fn in ("function d4bSet(widgetId: string, key: string, value: string): string",
                   "function d4bMigration(): string",
                   "function d4bInstances(): string",
                   "function d4bClickVocabulary(): string"):
            self.assertIn(fn, probe)
        self.assertIn('import "services/BarWidgetDefaults.js" as BarWidgetDefaults', probe)

    def test_probe_reports_d4b_and_gates_on_it(self):
        probe = read(os.path.join(SHELL, "scripts", "dev", "probe-bar.sh"))
        self.assertIn('"d4b": {', probe)
        self.assertIn("d4b_ok ", probe, "the global ok gate must include the d4b evidence")


if __name__ == "__main__":
    unittest.main()

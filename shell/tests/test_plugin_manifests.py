"""S0-2 plugin manifest & microkernel closure contracts.

The PluginRegistry reads every shell/plugins/<domain>/manifest.toml at runtime
and derives the mount rows, switch rows, settings schema and searchable
actions from it — the hand-written host mirror (UnitCatalog.qml) is retired.
These tests weld the declarations to the blueprint tree and to the kernel's
event loop:

  - manifest id == root-derived registry id (the engine validator is the one truth)
  - kinds stay inside the six geometric slots (+ service); ui kinds get entry points
  - every shell plugin keeps one explicit label and a unique stacking order
  - the host instantiates zero units by name (PluginRegistry.units is the model)
  - entry points load as file:// URLs; the qs.plugins.* preheat list is gone
  - the bridge's `unit reload` event lands on a real IpcHandler
  - StateProjection is a read-only projection defaulting to enabled
"""

import os
import unittest
from pathlib import Path

from nyxuri.deploy import manifest as engine_manifest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL_DIR = os.path.join(REPO_ROOT, "shell")
PLUGINS_DIR = os.path.join(SHELL_DIR, "plugins")

SIX_SLOTS = {"edge", "island", "overlay", "drawer", "surface:desktop", "popup:notification"}
SHELL_KINDS = SIX_SLOTS | {"service"}

UNIT_COMPONENTS = [
    "Bar {", "DockHost {", "Keystone {", "NotificationPopupHost {", "LauncherHost {",
    "Lock {", "SessionHost {", "SettingsHost {", "SidebarHostWindow {",
    "RegionSelector {", "WallpaperBackground {", "DesktopCardHost {",
]


def read(*parts):
    with open(os.path.join(SHELL_DIR, *parts), "r", encoding="utf-8") as f:
        return f.read()


def plugin_dirs():
    return sorted(d for d in os.listdir(PLUGINS_DIR)
                  if os.path.isdir(os.path.join(PLUGINS_DIR, d))
                  and d != "__pycache__")


class TestPluginManifestSync(unittest.TestCase):
    """Every blueprint declares itself; the engine parser is the one validator."""

    def test_every_plugin_ships_a_new_form_manifest(self):
        for domain in plugin_dirs():
            with self.subTest(plugin=domain):
                m = engine_manifest.load_manifest(
                    Path(PLUGINS_DIR) / domain, namespace="shell.")
                self.assertEqual(m.id, f"shell.{domain}")

    def test_kinds_stay_inside_the_slot_taxonomy(self):
        for domain in plugin_dirs():
            m = engine_manifest.load_manifest(
                Path(PLUGINS_DIR) / domain, namespace="shell.")
            for kind in m.kinds:
                self.assertIn(kind, SHELL_KINDS,
                              f"shell.{domain} declares unknown kind {kind}")

    def test_labels_and_stacking_orders_are_explicit(self):
        orders = {}
        for domain in plugin_dirs():
            m = engine_manifest.load_manifest(
                Path(PLUGINS_DIR) / domain, namespace="shell.")
            self.assertTrue(m.label, f"shell.{domain} must carry a label")
            self.assertNotIn(m.order, orders,
                             f"shell.{domain} and shell.{orders.get(m.order)} share order {m.order}")
            orders[m.order] = domain

    def test_entry_points_land_on_real_qml_roots(self):
        for domain in plugin_dirs():
            m = engine_manifest.load_manifest(
                Path(PLUGINS_DIR) / domain, namespace="shell.")
            self.assertTrue(m.entry_points, f"shell.{domain} declares no entry point")
            for kind, rel in m.entry_points.items():
                self.assertTrue(rel.endswith(".qml"))
                self.assertTrue(os.path.isfile(os.path.join(PLUGINS_DIR, domain, rel)),
                                f"missing entry point for shell.{domain}: {rel}")


class TestHostClosure(unittest.TestCase):
    """Microkernel closure: the host assembles, plugins own themselves."""

    def test_app_shell_instantiates_no_unit(self):
        app = read("app", "AppShell.qml")
        for component in UNIT_COMPONENTS:
            self.assertNotIn(component, app,
                             f"AppShell must not instantiate unit component: {component}")

    def test_slothost_is_the_only_loader_and_rides_the_registry(self):
        slot = read("app", "SlotHost.qml")
        self.assertIn("Repeater", slot)
        self.assertIn("PluginRegistry.units", slot)
        self.assertIn("StateProjection.isEnabled(unit.id)", slot)
        self.assertIn("source: modelData.entryUrl", slot)
        # The safety rule: a held session lock is never torn down mid-lock.
        self.assertIn('unit.id === "lock" && ActionGateway.lockEngaged', slot)

    def test_slothost_carries_no_preheat_imports(self):
        """loader-form.md: the preheat list retires with the registry. Plugin
        pools are never imported by the startup closure again — plugins speak
        relative imports (rules 2/3), shared layers are guaranteed by shell.qml."""
        slot = read("app", "SlotHost.qml")
        self.assertNotIn("import qs.plugins", slot)
        self.assertNotIn("import qs.commons.cards", slot)
        self.assertNotIn("import qs.ui", slot)

    def test_shell_root_guarantees_the_shared_layer_pools(self):
        root = read("shell.qml")
        for module in ("qs.commons", "qs.commons.cards", "qs.commons.i18n",
                       "qs.services", "qs.ui"):
            self.assertIn(f"import {module}", root,
                          f"shell.qml must import {module} (loader-form rule 3)")

    def test_registry_resolves_entry_points_as_file_urls(self):
        helper = read("services", "PluginManifest.js")
        self.assertIn('"file://"', helper)
        registry = read("services", "PluginRegistry.qml")
        self.assertIn("Manifest.validate", registry)
        self.assertIn("entryUrl: record.entryUrls[kind]", registry)

    def test_schema_routes_render_through_the_generic_page(self):
        # S0-3b: routes with `controls` carry no sourceUrl; the aggregator
        # loads its generic atom page and injects the route id.
        window = read("plugins", "settings", "ControlCenterWindow.qml")
        self.assertIn("SchemaSettingsPage.qml", window,
                      "schema routes must land on the generic renderer")
        host = read("plugins", "settings", "SettingsPageHost.qml")
        self.assertIn("item.settingsRoute = pageLayer.route", host,
                      "the page host must inject the route id")
        page = read("plugins", "settings", "SchemaSettingsPage.qml")
        for atom in ("PreferenceToggle", "PreferenceSelect", "PreferenceSlider",
                     "PreferenceStepper", "PreferenceInput"):
            self.assertIn(atom, page, f"the schema renderer must use {atom}")
        self.assertIn("PluginSettings.setValue", page,
                      "schema values persist through the host store")
        helper = read("services", "PluginManifest.js")
        self.assertIn('entry.controls !== undefined', helper,
                      "the registry must route controls entries as routes, not anchors")

    def test_unit_roots_self_register_on_gateway(self):
        expectations = {
            os.path.join("plugins", "lock", "Lock.qml"): "ActionGateway.sessionLocker = root",
            os.path.join("plugins", "settings", "SettingsHost.qml"):
                "ActionGateway.settingsHost = root",
            os.path.join("plugins", "keystone", "Keystone.qml"):
                "ActionGateway.keystoneHost = root",
        }
        for rel, marker in expectations.items():
            self.assertIn(marker, read(*rel.split(os.sep)),
                          f"unit root must self-register: {rel}")


class TestEventLoop(unittest.TestCase):
    """One event, one channel, one projection."""

    def test_bridge_delivers_over_quickshell_ipc(self):
        bridge = os.path.join(REPO_ROOT, "nyxuri", "desktop", "bridge.py")
        with open(bridge, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('"ipc", "call", "unit", "reload"', content)

    def test_shell_handles_the_unit_event(self):
        app = read("app", "AppShell.qml")
        self.assertIn('target: "unit"', app)
        self.assertIn("StateProjection.reload()", app)

    def test_projection_is_readonly_and_defaults_enabled(self):
        proj = read("services", "StateProjection.qml")
        self.assertIn('Paths.stateHome + "/state.json"', proj)
        self.assertIn("watchChanges: false", proj,
                      "reload happens on the unit-changed event only")
        self.assertIn('record.state === "enabled"', proj)
        self.assertIn("return true;", proj, "no ledger record must project as enabled")
        self.assertNotIn("setText", proj, "the shell never writes the ledger")

    def test_switches_route_through_the_kernel_verb(self):
        control = read("services", "UnitControlService.qml")
        self.assertIn('Paths.binHome + "/nyxuri"', control)
        self.assertIn('"shell." + unitId', control)
        self.assertNotIn("state.json", control,
                         "no shell-side ledger writes, ever")


class TestSingletonRegistration(unittest.TestCase):
    """qmldir is the singleton registry (loader-form rule 2 addendum, S0-2 实机教训).

    A `pragma Singleton` file resolved through implicit or relative types
    WITHOUT a qmldir `singleton` registration yields a husk object — every
    method call dies with "TypeError: Property 'x' of object Y is not a
    function". The registry form is the only supported singleton shape in
    plugin directories; the weld below keeps file and registry in lockstep.
    """

    def _singletons(self):
        found = {}
        for base, dirs, files in os.walk(PLUGINS_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if not name.endswith(".qml"):
                    continue
                path = os.path.join(base, name)
                with open(path, "r", encoding="utf-8") as f:
                    head = f.read(512)
                if "pragma Singleton" in head:
                    found.setdefault(base, []).append(name)
        return found

    def test_every_pragma_singleton_is_registered(self):
        for base, names in self._singletons().items():
            qmldir = os.path.join(base, "qmldir")
            with open(qmldir, "r", encoding="utf-8") as f:
                lines = {line.strip() for line in f if line.strip()}
            for name in names:
                stem = name[:-4]
                entry = f"singleton {stem} 1.0 {name}"
                self.assertIn(entry, lines,
                              f"{base} must register its singleton: {entry}")

    def test_qmldir_lists_only_real_singletons(self):
        singletons = self._singletons()
        for base, dirs, files in os.walk(PLUGINS_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            if "qmldir" not in files:
                continue
            with open(os.path.join(base, "qmldir"), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # the singleton registry is the qmldir's only job:
                    # plain types keep implicit resolution, no type lists
                    self.assertTrue(line.startswith("singleton "),
                                    f"{base}/qmldir must stay a singleton-only registry: {line}")
                    name = line.split()[3] if len(line.split()) >= 4 else ""
                    self.assertIn(name, singletons.get(base, []),
                                  f"{base}/qmldir registers a non-singleton file: {name}")


class TestRetiredMirrors(unittest.TestCase):
    """The host mirror is gone for good (S0-2 四件套之一)."""

    def test_unit_catalog_is_physically_gone(self):
        self.assertFalse(os.path.exists(os.path.join(SHELL_DIR, "app", "UnitCatalog.qml")))

    def test_no_code_references_the_unit_catalog(self):
        hits = []
        for base, dirs, files in os.walk(SHELL_DIR):
            dirs[:] = [d for d in dirs
                       if d not in ("references", "archive", "tests", "__pycache__")]
            for name in files:
                if not name.endswith((".qml", ".js", ".py")):
                    continue
                path = os.path.join(base, name)
                with open(path, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, 1):
                        if "UnitCatalog" in line:
                            hits.append(f"{os.path.relpath(path, SHELL_DIR)}:{lineno}")
        self.assertEqual(hits, [], f"UnitCatalog references left: {hits}")


class TestZeroHostChangesDiscovery(unittest.TestCase):
    """Adversarial gate (llms-wiki/testing.md): the "add a plugin = add a
    directory + manifest + code, zero host changes" claim must hold for a
    plugin the host has never seen — mount row, settings routes/anchors and
    searchable actions all discovered from the dropped-in manifest alone
    (PluginRegistry's find scan matches plugins/<domain>/manifest.toml at
    depth 2), and the tree carries no residue once it is removed."""

    TEMP_DOMAIN = "zz-adversarial"

    TEMP_MANIFEST = """schemaVersion = 1
id = "shell.zz-adversarial"
kinds = ["overlay"]
label = "Adversarial"
order = 999

[entryPoints]
overlay = "AdversarialHost.qml"

[[settings]]
id = "adversarial"
source = "AdversarialPage.qml"
title = "Adversarial"
description = "Round-trip probe"
context = "AdversarialHost"
icon = "science"
group = "system"
order = 999

[[settings]]
id = "adversarial.section.probe"
route = "adversarial"
title = "Probe"
context = "AdversarialPage"
icon = "science"

[[settings]]
id = "adversarial.tuning"
title = "Adversarial tuning"
description = "Schema-declared controls"
context = "AdversarialHost"
icon = "tune"
group = "system"
order = 998
controls = [
  { key = "probe-enabled", type = "switch", title = "Probe enabled", default = false },
  { key = "probe-depth", type = "spin", title = "Probe depth", min = 1, max = 9, default = 3 },
]

[[actions]]
id = "nyxuri:adversarial:ping"
target = "adversarial"
method = "ping"

[actions.search]
title = "Adversarial ping"
description = "Round-trip probe action"
context = "SpotlightActions"
icon = "network_ping"
"""

    def test_temp_plugin_round_trip(self):
        import shutil
        plugin = os.path.join(PLUGINS_DIR, self.TEMP_DOMAIN)
        self.assertFalse(os.path.exists(plugin), "fixture collision: temp plugin already exists")
        try:
            os.makedirs(plugin)
            for name in ("AdversarialHost.qml", "AdversarialPage.qml"):
                with open(os.path.join(plugin, name), "w", encoding="utf-8") as handle:
                    handle.write("import QtQuick\nItem {}\n")
            with open(os.path.join(plugin, "manifest.toml"), "w", encoding="utf-8") as handle:
                handle.write(self.TEMP_MANIFEST)
            m = engine_manifest.load_manifest(Path(plugin), namespace="shell.")
            self.assertEqual(m.id, "shell." + self.TEMP_DOMAIN)
            self.assertIn("overlay", m.entry_points)
            routes = [s for s in m.settings if "source" in s]
            schema_routes = [s for s in m.settings if "controls" in s]
            anchors = [s for s in m.settings if "route" in s]
            self.assertEqual(len(routes), 1, "settings route not discovered")
            self.assertEqual(len(anchors), 1, "search anchor not discovered")
            self.assertEqual(len(m.actions), 1, "searchable action not discovered")
            # S0-3b: schema routes (controls, no source) are discovered as
            # routes with their control descriptors normalised.
            self.assertEqual(len(schema_routes), 1, "schema route not discovered")
            self.assertEqual(schema_routes[0]["id"], "adversarial.tuning")
            self.assertEqual([c["key"] for c in schema_routes[0]["controls"]],
                             ["probe-enabled", "probe-depth"])
        finally:
            shutil.rmtree(plugin, ignore_errors=True)
        self.assertFalse(os.path.exists(plugin))
        # Zero host knowledge: no host file mentions the temp domain.
        for rel in (("app", "AppShell.qml"), ("app", "SlotHost.qml"),
                    ("services", "PluginRegistry.qml"), ("services", "PluginManifest.js")):
            self.assertNotIn(self.TEMP_DOMAIN, read(*rel),
                             f"host file knows the temp plugin: {'/'.join(rel)}")


if __name__ == "__main__":
    unittest.main()

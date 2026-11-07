"""S0-2 settings schema & searchable action contracts.

The plugin manifests are the only declaration surface left: settings routes
and search anchors live in each owning plugin's manifest.toml (S0-3a: domain
pages moved to their plugins; the settings aggregator keeps the host-level
pages), searchable fixed actions live in each owning plugin's manifest, and
the runtime registry reads them directly (SpotlightCatalog is a thin index
over PluginRegistry). The generated chain — settings-routes.json +
generate-search-catalog.py + generated/SearchCatalog.js — is retired for
good; these tests keep it that way and weld the manifest data to the page
registrations and the binds truth.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "shell"
sys.path.insert(0, str(REPO_ROOT))

from nyxuri.deploy import manifest as engine_manifest  # noqa: E402

PLUGINS_DIR = ROOT / "plugins"

# The nav pane is registry-sorted (order, id); this sequence is the visible
# contract (Caelestia fidelity) — a reshuffle must be a deliberate decision.
NAV_ORDER = [
    "account", "theme", "wallpaper",
    "bar", "dock", "sidebar", "keystone",
    "network", "connected-devices",
    "spotlight",
    "language-region", "shell",
    "about",
]

ANCHOR_ID_RE = re.compile(r"anchorId:\s*\"([^\"]+)\"")
RETIRED_FILES = [
    ROOT / "plugins/settings/settings-routes.json",
    ROOT / "plugins/settings/generated",
    ROOT / "scripts/dev/generate-search-catalog.py",
]


def plugin_domains():
    return sorted(d.name for d in PLUGINS_DIR.iterdir()
                  if d.is_dir() and d.name != "__pycache__")


def load_all_settings():
    """Every manifest's [[settings]] rows, tagged with the owning plugin."""
    rows = []
    for domain in plugin_domains():
        m = engine_manifest.load_manifest(PLUGINS_DIR / domain, namespace="shell.")
        for entry in m.settings:
            rows.append((f"shell.{domain}", entry))
    return rows


def load_all_actions():
    actions = []
    for domain in plugin_domains():
        m = engine_manifest.load_manifest(PLUGINS_DIR / domain, namespace="shell.")
        for action in m.actions:
            actions.append((f"shell.{domain}", action))
    return actions


class CatalogTests(unittest.TestCase):
    def test_generated_chain_stays_retired(self):
        for path in RETIRED_FILES:
            self.assertFalse(path.exists(), f"retired catalog artifact is back: {path}")
        for base, _dirs, files in os.walk(PLUGINS_DIR):
            for name in files:
                if not name.endswith(".qml"):
                    continue
                with open(Path(base) / name, encoding="utf-8") as handle:
                    self.assertNotIn("declaration:", handle.read(),
                                     f"page anchors register by anchorId now: {name}")

    def test_settings_routes_pin_the_nav_order_and_groups(self):
        rows = load_all_settings()
        routes = [entry for _plugin, entry in rows if "source" in entry]
        by_id = {s["id"]: s for s in routes}
        top = sorted((s for s in routes if "." not in s["id"]), key=lambda s: s["order"])
        self.assertEqual([s["id"] for s in top], NAV_ORDER)
        # Groups drive the nav pane's geometric clustering: when routes are in
        # nav order, a group must form one contiguous run (no interleaving).
        runs = []
        for entry in top:
            group = entry["group"]
            self.assertTrue(group, f"route {entry['id']} has no group")
            if not runs or runs[-1] != group:
                runs.append(group)
        self.assertEqual(len(runs), len(set(runs)), f"groups interleave in the nav order: {runs}")
        # Nested pages and anchors weld to a parent route of the same manifest.
        routes_by_plugin = {}
        for plugin, entry in rows:
            routes_by_plugin.setdefault(plugin, set()).add(entry["id"])
        for plugin, entry in rows:
            parent = entry["id"].split(".")[0]
            self.assertIn(parent, routes_by_plugin[plugin],
                          f"{entry['id']} has no parent route in {plugin}'s manifest")

    def test_page_anchor_registrations_match_manifest_anchors(self):
        anchors = {entry["id"]: entry for _plugin, entry in load_all_settings() if "route" in entry}
        self.assertGreater(len(anchors), 40)
        registered = set()
        for base, _dirs, files in os.walk(ROOT / "plugins"):
            if "__pycache__" in base:
                continue
            for name in files:
                if not name.endswith(".qml"):
                    continue
                text = (Path(base) / name).read_text(encoding="utf-8")
                for match in ANCHOR_ID_RE.finditer(text):
                    registered.add(match.group(1))
        # The ControlCenterWindow page-level reveal anchor is runtime-only.
        registered.discard("page")
        self.assertEqual(registered, set(anchors),
                         "page anchorId registrations and manifest [[settings]] anchors disagree")
        for anchor in anchors.values():
            self.assertTrue(anchor.get("title") and anchor.get("context") and anchor.get("icon"),
                            f"anchor {anchor['id']} lost its declaration data")

    def test_aggregator_loads_pages_from_registry_urls(self):
        # S0-3a: pages are owned by their plugins; the aggregator resolves
        # every route through the registry's absolute file:// sourceUrl
        # (PluginManifest computes it per plugin directory), never a URL
        # relative to the aggregator's own directory.
        window = (PLUGINS_DIR / "settings" / "ControlCenterWindow.qml").read_text(encoding="utf-8")
        self.assertIn("pages[index].sourceUrl", window,
                      "the settings window must load pages by registry sourceUrl")
        self.assertNotIn("Qt.resolvedUrl(pages[", window,
                         "page sources must not resolve against the aggregator directory")

    def test_route_sources_exist_in_their_owning_plugin(self):
        for plugin, entry in load_all_settings():
            if "source" not in entry:
                continue
            domain = plugin.removeprefix("shell.")
            path = PLUGINS_DIR / domain / entry["source"]
            self.assertTrue(path.is_file(),
                            f"{entry['id']}: source missing in its owning plugin at {path}")

    def test_domain_plugins_never_import_the_aggregator(self):
        # S0-3a: settings pages owned by domain plugins talk to the host
        # contract (the SettingsSearch service), never to the settings
        # aggregator plugin — the aggregator is a consumer, not a dependency.
        for domain in plugin_domains():
            if domain == "settings":
                continue
            for path in sorted((PLUGINS_DIR / domain).rglob("*.qml")):
                if "__pycache__" in path.parts:
                    continue
                with path.open(encoding="utf-8") as handle:
                    text = handle.read()
                self.assertNotIn("qs.plugins.settings", text,
                                 f"{path.name} imports the settings aggregator")
                self.assertNotRegex(text, r'"\.\.(/\.\.)*/settings"',
                                    f"{path.name} relatively imports the settings aggregator")

    def test_actions_weld_to_the_binds_truth(self):
        binds = json.loads((ROOT / "scripts/system/niri-actions.json").read_text())
        by_id = {entry["id"]: entry for entry in binds}
        self.assertTrue(by_id)
        # The search include set moved to the manifests: no bind carries
        # search metadata any more (single truth, no second vocabulary).
        self.assertFalse(any("search" in entry for entry in binds))
        actions = load_all_actions()
        self.assertGreaterEqual(len(actions), 20)
        for plugin_id, action in actions:
            with self.subTest(action=action["id"]):
                entry = by_id.get(action["id"])
                self.assertIsNotNone(entry, f"{action['id']} is not in the binds truth")
                self.assertEqual(entry["category"], "nyxuri")
                self.assertFalse(entry["parameters"], "catalog actions take fixed argv only")
                expected = "spawn " + " ".join(
                    json.dumps(v) for v in
                    ["nyxuri-shell", "--ipc", action["target"], action["method"], *action["args"]])
                self.assertEqual(entry["expression"], expected,
                                 f"{action['id']} disagrees with its bind expression")
                self.assertRegex(action["id"], r"^nyxuri:" + re.escape(action["target"]))


if __name__ == "__main__":
    unittest.main()

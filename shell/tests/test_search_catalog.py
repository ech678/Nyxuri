"""S0-2 settings schema & searchable action contracts.

The plugin manifests are the only declaration surface left: settings routes
and search anchors live in plugins/settings/manifest.toml, searchable fixed
actions live in each owning plugin's manifest, and the runtime registry reads
them directly (SpotlightCatalog is a thin index over PluginRegistry). The
generated chain — settings-routes.json + generate-search-catalog.py +
generated/SearchCatalog.js — is retired for good; these tests keep it that
way and weld the manifest data to the page registrations and the binds truth.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from nyxuri.deploy import manifest as engine_manifest  # noqa: E402

PLUGINS_DIR = ROOT / "plugins"

# The nav pane is registry-sorted (order, id); this sequence is the visible
# contract (Caelestia fidelity) — a reshuffle must be a deliberate decision.
NAV_ORDER = [
    "account", "theme", "wallpaper",
    "bar", "dock", "sidebar", "keystone",
    "network", "connected-devices",
    "shortcuts", "spotlight",
    "language-region", "shell",
    "about",
]

ANCHOR_ID_RE = re.compile(r"anchorId:\s*\"([^\"]+)\"")
RETIRED_FILES = [
    ROOT / "plugins/settings/settings-routes.json",
    ROOT / "plugins/settings/generated",
    ROOT / "scripts/dev/generate-search-catalog.py",
]


def load_settings_manifest():
    return engine_manifest.load_manifest(PLUGINS_DIR / "settings", namespace="shell.")


def load_all_actions():
    actions = []
    for domain in sorted(d.name for d in PLUGINS_DIR.iterdir()
                         if d.is_dir() and d.name != "__pycache__"):
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
        m = load_settings_manifest()
        routes = [s for s in m.settings if "source" in s]
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
        # Nested pages weld to a parent route of the same manifest.
        for entry in routes:
            if "." in entry["id"]:
                parent = entry["id"].split(".")[0]
                self.assertIn(parent, by_id, f"nested route {entry['id']} has no parent")

    def test_page_anchor_registrations_match_manifest_anchors(self):
        m = load_settings_manifest()
        anchors = {s["id"]: s for s in m.settings if "route" in s}
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

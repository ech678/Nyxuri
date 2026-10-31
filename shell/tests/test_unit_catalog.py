#!/usr/bin/env python3
"""KM4 Shell unit catalog & microkernel closure contracts.

The catalog (shell/app/UnitCatalog.qml) is the host-side declaration of the
twelve Shell units. These tests keep it welded to the physical blueprints
(shell/plugins/) and to the kernel's event loop:

  - catalog ids  == shell/plugins/ directory names (registry namespace root)
  - catalog labels == blueprint manifest labels
  - every slot is one of the six geometric slots (unit-model.md §6)
  - every component source exists on disk
  - the host instantiates zero units by name (SlotHost is the only loader)
  - the bridge's `unit reload` event lands on a real IpcHandler
  - StateProjection is a read-only projection defaulting to enabled
"""

import os
import re
import unittest

REPO_ROOT = Path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHELL_DIR = os.path.join(REPO_ROOT, "shell")
UNITS_DIR = os.path.join(SHELL_DIR, "plugins")

SIX_SLOTS = {"edge", "island", "overlay", "drawer", "surface:desktop", "popup:notification"}

UNIT_COMPONENTS = [
    "Bar {", "DockHost {", "Keystone {", "NotificationPopupHost {", "LauncherHost {",
    "Lock {", "SessionHost {", "SettingsHost {", "SidebarHostWindow {",
    "RegionSelector {", "WallpaperBackground {", "DesktopCardHost {",
]


def read(*parts):
    with open(os.path.join(SHELL_DIR, *parts), "r", encoding="utf-8") as f:
        return f.read()


def catalog_rows():
    """Parse the UnitCatalog.qml units array into dicts."""
    src = read("app", "UnitCatalog.qml")
    rows = []
    for match in re.finditer(r'\{\s*"id":\s*"([^"]+)",\s*"label":\s*"([^"]+)",'
                             r'\s*"slot":\s*"([^"]+)",\s*"source":\s*"([^"]+)"', src):
        rows.append({"id": match.group(1), "label": match.group(2),
                     "slot": match.group(3), "source": match.group(4)})
    return rows


class TestUnitCatalogSync(unittest.TestCase):
    """The catalog is the blueprint tree, mirrored — nothing more, nothing less."""

    def test_catalog_covers_every_blueprint(self):
        blueprints = sorted(d for d in os.listdir(UNITS_DIR)
                            if os.path.isdir(os.path.join(UNITS_DIR, d)))
        catalog_ids = sorted(row["id"] for row in catalog_rows())
        self.assertEqual(catalog_ids, blueprints,
                         "UnitCatalog.qml must declare exactly the shell/plugins/ blueprints")

    def test_labels_match_blueprints(self):
        for row in catalog_rows():
            manifest = os.path.join(UNITS_DIR, row["id"], "manifest.toml")
            with open(manifest, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(f'runtime = true', content,
                          f"shell.{row['id']} must stay a runtime unit")
            label = re.search(r'label\s*=\s*"([^"]+)"', content)
            self.assertIsNotNone(label, f"{manifest} must carry a label")
            self.assertEqual(row["label"], label.group(1),
                             f"catalog label out of sync for shell.{row['id']}")

    def test_slots_within_six_slot_taxonomy(self):
        for row in catalog_rows():
            self.assertIn(row["slot"], SIX_SLOTS,
                          f"shell.{row['id']} declares unknown slot {row['slot']}")

    def test_sources_exist(self):
        for row in catalog_rows():
            path = os.path.normpath(os.path.join(SHELL_DIR, "app", row["source"]))
            self.assertTrue(os.path.isfile(path), f"missing unit source: {row['source']}")


class TestHostClosure(unittest.TestCase):
    """Microkernel closure: the host assembles, units own themselves."""

    def test_app_shell_instantiates_no_unit(self):
        app = read("app", "AppShell.qml")
        for component in UNIT_COMPONENTS:
            self.assertNotIn(component, app,
                             f"AppShell must not instantiate unit component: {component}")

    def test_slothost_is_the_only_unit_loader(self):
        slot = read("app", "SlotHost.qml")
        self.assertIn("Repeater", slot)
        self.assertIn("UnitCatalog.units", slot)
        self.assertIn("StateProjection.isEnabled(unit.id)", slot)
        self.assertIn("source: modelData.source", slot)
        # The safety rule: a held session lock is never torn down mid-lock.
        self.assertIn('unit.id === "lock" && ActionGateway.lockEngaged', slot)

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


if __name__ == "__main__":
    unittest.main()

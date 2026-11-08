"""Focused tests for the static QML resource inventory."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "shell"
SCRIPT = ROOT / "scripts" / "dev" / "resource_inventory.py"
SPEC = importlib.util.spec_from_file_location("resource_inventory", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
inventory_module = importlib.util.module_from_spec(SPEC)
sys.modules["resource_inventory"] = inventory_module
SPEC.loader.exec_module(inventory_module)


class ResourceInventoryTests(unittest.TestCase):
    def test_inventory_extracts_top_level_properties_and_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "services" / "DemoService.qml"
            fixture.parent.mkdir()
            fixture.write_text(
                """Item {
    // Timer { fake: true }
    Timer {
        id: refreshTimer
        interval: 250
        running: root.active
        repeat: true
        Connections { target: root }
    }
    Process {
        id: worker
        running: false
    }
    FileView { path: \"/tmp/a{b}\" }
}
""",
                encoding="utf-8",
            )

            document = inventory_module.inventory(root)

        self.assertEqual(document["counts"], {"Timer": 1, "Process": 1, "FileView": 1, "Connections": 1})
        rows = document["resources"]
        timer = next(row for row in rows if row["kind"] == "Timer")
        self.assertEqual(timer["file"], "services/DemoService.qml")
        self.assertEqual(timer["line"], 3)
        self.assertEqual(timer["owner"], "DemoService")
        self.assertEqual(timer["identifier"], "refreshTimer")
        self.assertEqual(timer["interval"], 250)
        self.assertEqual(timer["default_running"], "root.active")
        self.assertTrue(timer["repeat"])

    def test_inventory_order_and_rendering_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "B.qml").write_text("Item { Timer { interval: root.delay } }\n", encoding="utf-8")
            (root / "A.qml").write_text("Item { Process { running: true } }\n", encoding="utf-8")
            first = inventory_module.inventory(root)
            second = inventory_module.inventory(root)

        self.assertEqual(first, second)
        self.assertEqual([row["file"] for row in first["resources"]], ["A.qml", "B.qml"])
        rendered = inventory_module.markdown(first)
        self.assertIn("Static source inventory only", rendered)
        self.assertLess(rendered.index("A.qml"), rendered.index("B.qml"))

    def test_cli_json_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "inventory.json"
            (root / "Demo.qml").write_text("Item { Timer { interval: 100 } }\n", encoding="utf-8")
            self.assertEqual(inventory_module.main([str(root), "--output", str(output)]), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertFalse(payload["runtime_claims"])
        self.assertEqual(payload["counts"]["Timer"], 1)


if __name__ == "__main__":
    unittest.main()

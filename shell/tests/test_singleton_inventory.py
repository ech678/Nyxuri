"""Focused tests for the static QML singleton/consumer inventory."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "singleton_inventory.py"
SPEC = importlib.util.spec_from_file_location("singleton_inventory", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
module = importlib.util.module_from_spec(SPEC)
sys.modules["singleton_inventory"] = module
SPEC.loader.exec_module(module)


class SingletonInventoryTests(unittest.TestCase):
    def test_extracts_singleton_imports_consumers_and_completed_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "services").mkdir()
            (root / "ui").mkdir()
            (root / "services" / "DemoService.qml").write_text(
                """pragma Singleton
import QtQuick
import Quickshell.Io

Singleton {
    id: root
    Timer { id: refreshTimer; interval: 1000 }
    Process { id: worker }
    FileView { id: stateFile }
    Socket { id: socket }
    Loader { id: childLoader }
    Component.onCompleted: {
        refreshTimer.start(); worker.running = true;
        stateFile.reload(); socket.connectToServer(); childLoader.active = true;
    }
}
""",
                encoding="utf-8",
            )
            (root / "ui" / "Consumer.qml").write_text(
                """import qs.services
Item { property string value: DemoService.someValue }
""",
                encoding="utf-8",
            )
            document = module.inventory(root)

        self.assertFalse(document["runtime_claims"])
        self.assertEqual(document["singleton_count"], 1)
        singleton = document["singletons"][0]
        self.assertEqual(singleton["name"], "DemoService")
        self.assertEqual([item["module"] for item in singleton["imports"]], ["QtQuick", "Quickshell.Io"])
        self.assertEqual(singleton["consumers"], [{"file": "ui/Consumer.qml", "line": 2, "reference": "DemoService"}])
        self.assertEqual(
            [(item["kind"], item["identifier"], item.get("operation")) for item in singleton["side_effects"]],
            [("FileView", "stateFile", "reload"), ("Loader", "childLoader", "active"),
             ("Process", "worker", "running"), ("Socket", "socket", "connectToServer"),
             ("Timer", "refreshTimer", "start")],
        )

    def test_qmldir_alias_and_output_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "module").mkdir()
            (root / "module" / "qmldir").write_text("module qs.module\nsingleton PublicName Service.qml\n", encoding="utf-8")
            (root / "module" / "Service.qml").write_text("pragma Singleton\nSingleton {}\n", encoding="utf-8")
            first = module.inventory(root)
            second = module.inventory(root)
            output = root / "inventory.json"
            self.assertEqual(module.main([str(root), "--output", str(output)]), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(first, second)
        self.assertFalse(payload["runtime_claims"])
        self.assertEqual(payload["qmldir_aliases"], [{"name": "PublicName", "file": "module/Service.qml"}])
        self.assertIn("Static source inventory only", module.markdown(first))


if __name__ == "__main__":
    unittest.main()

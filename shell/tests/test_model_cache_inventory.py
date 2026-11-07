"""Focused tests for the static model/image/cache inventory."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "model_cache_inventory.py"
SPEC = importlib.util.spec_from_file_location("model_cache_inventory", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
inventory_module = importlib.util.module_from_spec(SPEC)
sys.modules["model_cache_inventory"] = inventory_module
SPEC.loader.exec_module(inventory_module)


class ModelCacheInventoryTests(unittest.TestCase):
    def test_inventory_covers_models_images_limits_canvas_and_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Demo.qml").write_text(
                """Item {
    property int itemLimit: 20
    ListModel { id: entries }
    FolderListModel { id: files; folder: root.folder }
    Repeater { model: entries; cacheBuffer: 4 }
    ListView { model: entries; cacheBuffer: root.itemLimit; reuseItems: true }
    GridView { model: entries; maximumFlickVelocity: 1000 }
    Image { id: cover; source: root.coverUrl; cache: true }
    IconImage { source: modelData.icon; asynchronous: true }
    Canvas { id: chart; layer.enabled: true }
    function prune() { entries.removeAt(0); }
}
""",
                encoding="utf-8",
            )
            (root / "Ignored.qml").write_text(
                "// ListModel { }\n/* Image { source: \"ignored\" } */\nItem {}\n",
                encoding="utf-8",
            )

            document = inventory_module.inventory(root)

        self.assertFalse(document["runtime_claims"])
        self.assertEqual(document["counts"]["ListModel"], 1)
        self.assertEqual(document["counts"]["FolderListModel"], 1)
        self.assertEqual(document["counts"]["Repeater"], 1)
        self.assertEqual(document["counts"]["ListView"], 1)
        self.assertEqual(document["counts"]["GridView"], 1)
        self.assertEqual(document["counts"]["image_sources"], 2)
        self.assertGreaterEqual(document["counts"]["cache_hints"], 4)
        self.assertGreaterEqual(document["counts"]["max_limit_eviction_signals"], 2)
        self.assertEqual(document["counts"]["canvas"], 1)
        self.assertEqual(document["counts"]["layers"], 1)
        self.assertEqual(document["layers"][0]["name"], "layer.enabled")
        self.assertEqual(document["layers"][0]["expression"], "true")

        image = next(row for row in document["images"] if row["identifier"] == "cover")
        self.assertEqual(image["image_sources"][0]["value"], "root.coverUrl")
        self.assertEqual(image["cache_hints"][0]["value"], "true")
        signals = document["max_limit_eviction_signals"]
        self.assertTrue(any(row["name"] == "itemLimit" and row["category"] == "bound" for row in signals))
        self.assertTrue(any(row["name"] == "removeAt" and row["category"] == "eviction" for row in signals))

    def test_json_and_markdown_are_deterministic_and_explicitly_static(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "B.qml").write_text("Item { ListView { model: [] } }\n", encoding="utf-8")
            (root / "A.qml").write_text("Item { Image { source: \"a.png\" } }\n", encoding="utf-8")
            first = inventory_module.inventory(root)
            second = inventory_module.inventory(root)
            output = root / "inventory.json"
            self.assertEqual(inventory_module.main([str(root), "--output", str(output)]), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(first, second)
        self.assertEqual([row["file"] for row in first["declarations"]], ["A.qml", "B.qml"])
        self.assertEqual(payload, first)
        markdown = inventory_module.markdown(first)
        self.assertIn("Static source inventory only", markdown)
        self.assertIn("no runtime model size", markdown)
        self.assertLess(markdown.index("A.qml"), markdown.index("B.qml"))


if __name__ == "__main__":
    unittest.main()

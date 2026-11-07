"""Contract tests for shell/scripts/system/migrate_config.py (P3 legacy config absorption)."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_SCRIPT = REPO_ROOT / "shell" / "scripts" / "system" / "migrate_config.py"


class TestMigrateConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_script_exists_and_is_executable(self):
        self.assertTrue(MIGRATE_SCRIPT.is_file())
        self.assertTrue(os.access(MIGRATE_SCRIPT, os.X_OK))

    def test_check_flag(self):
        # When no legacy files exist, --check exits with code 1
        res = subprocess.run([str(MIGRATE_SCRIPT), "--config-dir", str(self.config_dir), "--check"])
        self.assertEqual(res.returncode, 1)

        # Create one legacy file
        (self.config_dir / "dock.json").write_text("{}", encoding="utf-8")
        res = subprocess.run([str(MIGRATE_SCRIPT), "--config-dir", str(self.config_dir), "--check"])
        self.assertEqual(res.returncode, 0)

    def test_absorb_all_7_legacy_files_and_cleanup(self):
        # 1. config.json
        (self.config_dir / "config.json").write_text(json.dumps({
            "theme": {"mode": "dark", "cursorSize": 24},
            "wallpaper": {"path": "/fake/wp.png", "fillMode": "Fill"}
        }), encoding="utf-8")

        # 2. dock.json
        (self.config_dir / "dock.json").write_text(json.dumps({
            "schemaVersion": 1,
            "options": {"position": "bottom", "iconSize": 52},
            "pinned": [{"kind": "app", "desktopId": "firefox"}]
        }), encoding="utf-8")

        # 3. tray.json
        (self.config_dir / "tray.json").write_text(json.dumps({
            "showItemId": True,
            "invertPinnedItems": False,
            "pinnedItems": ["Fcitx", "Steam"],
            "filterPassive": True
        }), encoding="utf-8")

        # 4. quick-toggles.json
        (self.config_dir / "quick-toggles.json").write_text(json.dumps({
            "toggles": [{"type": "network", "size": 2}, {"type": "bluetooth", "size": 2}]
        }), encoding="utf-8")

        # 5. display-color.json
        (self.config_dir / "display-color.json").write_text(json.dumps({
            "nightEnabled": True,
            "nightTemperature": 4500,
            "mode": "time",
            "start": 1200,
            "end": 420
        }), encoding="utf-8")

        # 6. idle-policy.json
        (self.config_dir / "idle-policy.json").write_text(json.dumps({
            "policyEnabled": True,
            "lockEnabled": True,
            "lockTimeout": 900
        }), encoding="utf-8")

        # 7. ui-preferences.json
        (self.config_dir / "ui-preferences.json").write_text(json.dumps({
            "language": "zh_CN",
            "spotlightSearchEngine": "duckduckgo",
            "weatherTemperatureUnit": "celsius"
        }), encoding="utf-8")

        # Run migration with --cleanup
        res = subprocess.run(
            [str(MIGRATE_SCRIPT), "--config-dir", str(self.config_dir), "--cleanup"],
            capture_output=True, text=True, check=True
        )

        merged = json.loads(res.stdout)

        # Assert merged content
        self.assertEqual(merged["theme"]["mode"], "dark")
        self.assertEqual(merged["wallpaper"]["path"], "/fake/wp.png")
        self.assertEqual(merged["dock"]["schemaVersion"], 1)
        self.assertEqual(merged["dock"]["options"]["iconSize"], 52)
        self.assertEqual(merged["dock"]["pinned"][0]["desktopId"], "firefox")
        self.assertEqual(merged["bar"]["tray"]["pinnedItems"], ["Fcitx", "Steam"])
        self.assertEqual(len(merged["bar"]["quickToggles"]), 2)
        self.assertTrue(merged["display"]["nightEnabled"])
        self.assertEqual(merged["display"]["nightTemperature"], 4500)
        self.assertEqual(merged["idle"]["lockTimeout"], 900)
        self.assertEqual(merged["preferences"]["language"], "zh_CN")
        self.assertEqual(merged["preferences"]["spotlightSearchEngine"], "duckduckgo")

        # Assert all 7 legacy JSON files are completely deleted (zero residue)
        for filename in (
            "config.json", "dock.json", "tray.json", "quick-toggles.json",
            "display-color.json", "idle-policy.json", "ui-preferences.json"
        ):
            self.assertFalse((self.config_dir / filename).exists(), f"{filename} must be cleaned up")


import os

if __name__ == "__main__":
    unittest.main()

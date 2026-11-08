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


class TestIslandSectionMigration(unittest.TestCase):
    """B1: config.toml [keystone] → [island], one-way and idempotent.

    The long* keys ride along untouched (D4 freeze); a disabled shell.keystone
    ledger entry folds into [island] enabled = false."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        self.config_file = self.config_dir / "config.toml"
        self.state_file = self.config_dir / "state.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, enabled_key: str = ""):
        self.config_file.write_text(
            "[theme]\nmode = \"dark\"\n\n"
            "[keystone]\n"
            + (f"{enabled_key}\n" if enabled_key else "")
            + "style = \"bangs\"\n"
            "longShowNames = false\n"
            "longLeading = [ \"workspaces\" ]\n\n"
            "[keystone.media]\nprogressStyle = \"material\"\n\n"
            "[bar]\nposition = \"top\"\n",
            encoding="utf-8",
        )

    def _run(self):
        return subprocess.run(
            [str(MIGRATE_SCRIPT), "--config-dir", str(self.config_dir),
             "--state-file", str(self.state_file), "--cleanup"],
            capture_output=True, text=True, check=True,
        )

    def _island_body(self):
        text = self.config_file.read_text(encoding="utf-8")
        start = text.index("[island]")
        end = text.index("\n[", start + 1) if "\n[" in text[start + 1:] else len(text)
        return text[start:end]

    def test_renames_section_and_preserves_frozen_long_keys(self):
        self._write_config()
        self.state_file.write_text("{}", encoding="utf-8")
        self._run()
        body = self._island_body()
        self.assertIn("style = \"bangs\"", body)
        self.assertIn("longShowNames = false", body)
        self.assertIn("longLeading = [ \"workspaces\" ]", body)
        self.assertIn("[island.media]", self.config_file.read_text(encoding="utf-8"))
        self.assertNotIn("[keystone", self.config_file.read_text(encoding="utf-8"))
        # No verdict without a disabled ledger entry: enabled stays unset
        # (defaults to true at load).
        self.assertNotIn("enabled", body)

    def test_disabled_ledger_entry_folds_into_enabled_false(self):
        self._write_config()
        self.state_file.write_text(
            json.dumps({"plugins": {"shell.keystone": "disabled"}}), encoding="utf-8")
        self._run()
        self.assertIn("enabled = false", self._island_body())
        # The physical ledger file is never written by the shell side.
        self.assertIn("shell.keystone",
                      json.loads(self.state_file.read_text(encoding="utf-8"))["plugins"])

    def test_idempotent_second_run_is_a_noop(self):
        self._write_config()
        self.state_file.write_text(
            json.dumps({"plugins": {"shell.keystone": "disabled"}}), encoding="utf-8")
        self._run()
        after_first = self.config_file.read_text(encoding="utf-8")
        self._run()
        self.assertEqual(after_first, self.config_file.read_text(encoding="utf-8"))

    def test_existing_island_section_blocks_the_rename(self):
        # A downgrade interleave must never produce duplicate TOML sections.
        self._write_config(enabled_key="enabled = true")
        text = self.config_file.read_text(encoding="utf-8")
        self.config_file.write_text(text + "\n[island]\nenabled = true\n", encoding="utf-8")
        self._run()
        # [keystone] left as-is; the load-time failure path owns the verdict.
        self.assertIn("[keystone]", self.config_file.read_text(encoding="utf-8"))


import os

if __name__ == "__main__":
    unittest.main()

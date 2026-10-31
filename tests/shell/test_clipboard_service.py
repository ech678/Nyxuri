"""Tests for clipboard service and key-cli clipboard contract."""

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from tests.utils import TempEnv

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL_DIR = REPO_ROOT / "shell"


class ClipboardContractTests(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def test_qml_error_codes_and_i18n(self):
        """Verify that ClipboardService.qml has all cliphist error codes mapped and localized in zh_CN.toml."""
        qml_path = SHELL_DIR / "services" / "ClipboardService.qml"
        self.assertTrue(qml_path.exists(), "ClipboardService.qml must exist")
        qml_content = qml_path.read_text(encoding="utf-8")

        expected_codes = [
            "cliphist_list_failed",
            "cliphist_store_failed",
            "cliphist_delete_failed",
            "cliphist_clear_failed",
            "cliphist_unavailable",
            "cliphist_watcher_inactive",
        ]
        for code in expected_codes:
            self.assertIn(
                code,
                qml_content,
                f"ClipboardService.qml must map error code {code}",
            )

        # Check zh_CN.toml translations
        zh_toml_path = SHELL_DIR / "commons" / "i18n" / "zh_CN.toml"
        self.assertTrue(zh_toml_path.exists(), "zh_CN.toml must exist")
        zh_toml_content = zh_toml_path.read_text(encoding="utf-8")

        expected_strings = [
            "Unable to read clipboard history",
            "Unable to store clipboard entry",
            "Unable to delete clipboard entry",
            "Unable to clear clipboard history",
        ]
        for text in expected_strings:
            self.assertIn(
                f'"{text}" =',
                zh_toml_content,
                f"zh_CN.toml must provide translation for '{text}'",
            )

    def test_qml_empty_db_fallback_logic(self):
        """Verify that ClipboardService.qml contains fallback handling for empty database."""
        qml_path = SHELL_DIR / "services" / "ClipboardService.qml"
        qml_content = qml_path.read_text(encoding="utf-8")
        self.assertIn("isEmptyDbFallback", qml_content)
        self.assertIn("cliphist_list_failed", qml_content)

    def test_key_cli_empty_cliphist_contract(self):
        """Verify key clipboard list handles empty database gracefully."""
        # Check if key is available
        key_bin = shutil.which("key")
        if not key_bin:
            self.skipTest("key command not found in PATH")

        # Create isolated fake cliphist that outputs 'opening db: please store something first' with exit code 1
        fake_bin_dir = self.ctx.home / "fake_bin"
        fake_bin_dir.mkdir(parents=True)
        fake_cliphist = fake_bin_dir / "cliphist"
        fake_cliphist.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"list\" ]; then\n"
            "  echo 'opening db: please store something first' >&2\n"
            "  exit 1\n"
            "fi\n"
            "exit 0\n"
        )
        fake_cliphist.chmod(0o755)

        # Add fake_bin to PATH
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin_dir}:{env.get('PATH', '')}"
        user_site = Path("/home/ray/.local/lib/python3.14/site-packages")
        if user_site.exists():
            env["PYTHONPATH"] = f"{user_site}:{env.get('PYTHONPATH', '')}"

        proc = subprocess.run(
            [key_bin, "clipboard", "list", "--format", "json"],
            capture_output=True,
            text=True,
            env=env,
        )

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"key clipboard list did not output valid JSON: {proc.stdout} (stderr: {proc.stderr})")

        self.assertEqual(data.get("schemaVersion"), 1)
        self.assertEqual(data.get("command"), "clipboard.list")
        self.assertEqual(data.get("entries"), [])
        err = data.get("error")
        if err is not None:
            self.assertEqual(err.get("code"), "cliphist_watcher_inactive")
        else:
            self.assertIsNone(err)
            self.assertTrue(data.get("ok"))

    def test_qml_process_environment(self):
        """Verify that ClipboardService.qml passes clean XDG_CACHE_HOME to child processes."""
        qml_path = SHELL_DIR / "services" / "ClipboardService.qml"
        content = qml_path.read_text(encoding="utf-8")
        self.assertIn('"XDG_CACHE_HOME=" + Paths.xdgCacheHome', content)
        # Should be bound to multiple processes (config, list, action, inspect)
        self.assertGreaterEqual(content.count('"XDG_CACHE_HOME=" + Paths.xdgCacheHome'), 4)

    def test_key_cli_cache_normalization(self):
        """Verify key clipboard list normalizes /nyxuri-shell suffix in XDG_CACHE_HOME."""
        key_bin = shutil.which("key")
        if not key_bin:
            self.skipTest("key command not found in PATH")

        # Setup mock cache hierarchy:
        # real cache has 'cliphist/db'
        # fake nyxuri-shell cache is empty
        real_cache = self.ctx.home / ".cache"
        nyxuri_cache = real_cache / "nyxuri-shell"
        nyxuri_cache.mkdir(parents=True)

        fake_bin_dir = self.ctx.home / "fake_bin2"
        fake_bin_dir.mkdir(parents=True)
        fake_cliphist = fake_bin_dir / "cliphist"
        # cliphist records its active db path
        fake_cliphist.write_text(
            "#!/bin/sh\n"
            "printf '1\\tactive_cache=%s\\n' \"$XDG_CACHE_HOME\"\n"
            "exit 0\n"
        )
        fake_cliphist.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin_dir}:{env.get('PATH', '')}"
        env["XDG_CACHE_HOME"] = str(nyxuri_cache)
        env["NYXURI_ORIGINAL_CACHE_HOME"] = str(real_cache)
        user_site = Path("/home/ray/.local/lib/python3.14/site-packages")
        if user_site.exists():
            env["PYTHONPATH"] = f"{user_site}:{env.get('PYTHONPATH', '')}"

        proc = subprocess.run(
            [key_bin, "clipboard", "list", "--format", "json"],
            capture_output=True,
            text=True,
            env=env,
        )

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"Invalid JSON: {proc.stdout}")

        entries = data.get("entries", [])
        self.assertEqual(len(entries), 1)
        preview = entries[0].get("preview", "")
        # The active cache seen by cliphist must be normalized (not ending with nyxuri-shell)
        self.assertNotIn("/nyxuri-shell", preview)
        self.assertEqual(preview, f"active_cache={real_cache}")


if __name__ == "__main__":
    unittest.main()


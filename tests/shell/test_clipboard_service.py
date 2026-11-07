"""Tests for clipboard service contract."""

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

    def test_qml_process_environment(self):
        """Verify that ClipboardService.qml passes clean XDG_CACHE_HOME to child processes."""
        qml_path = SHELL_DIR / "services" / "ClipboardService.qml"
        content = qml_path.read_text(encoding="utf-8")
        self.assertIn('"XDG_CACHE_HOME=" + Paths.xdgCacheHome', content)
        # Should be bound to multiple processes (config, list, action, inspect)
        self.assertGreaterEqual(content.count('"XDG_CACHE_HOME=" + Paths.xdgCacheHome'), 4)


if __name__ == "__main__":
    unittest.main()


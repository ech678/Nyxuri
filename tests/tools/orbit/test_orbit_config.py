"""Regression tests for upstream defects fixed during the bug-hunt rounds.

Each test reproduces a concrete failure that shipped in v4.0.0-alpha.1 and
asserts the corrected behavior, so the defect cannot silently return.
"""

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestOrbitConfigValidation(unittest.TestCase):

    def _config(self):
        import importlib.util
        path = Path(__file__).resolve().parents[3] / "plugins" / "noctalia" / "tools" / "orbit" / "config.py"
        spec = importlib.util.spec_from_file_location("orbit_config_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_string_engine_list_is_rejected(self):
        mod = self._config()
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "cfg.toml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('search_engines = ["bing", "google"]\n')
        with patch.object(mod, "CONFIG_PATHS", [path]):
            engines, meta = _quiet(mod.load_search_config)
        self.assertTrue(all(isinstance(entry, dict) for entry in engines))
        self.assertIsInstance(meta, dict)

    def test_string_items_are_rejected(self):
        mod = self._config()
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "cfg.toml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('items = ["oops", 42]\n')
        with patch.object(mod, "CONFIG_PATHS", [path]):
            tree = _quiet(mod.load_menu_tree)
        self.assertTrue(all(isinstance(entry, dict) for entry in tree))

    def test_search_metadata_without_engines_is_kept(self):
        mod = self._config()
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "cfg.toml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('[search]\ndefault_engine = "google"\nplaceholder = "Ask anything"\n')
        with patch.object(mod, "CONFIG_PATHS", [path]):
            _engines, meta = _quiet(mod.load_search_config)
        self.assertEqual(meta.get("default_engine"), "google")
        self.assertEqual(meta.get("placeholder"), "Ask anything")

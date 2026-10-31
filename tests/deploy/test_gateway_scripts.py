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


class TestScriptContracts(unittest.TestCase):

    def _niri_scripts(self):
        return Path(__file__).resolve().parents[2] / "plugins" / "niri" / "scripts"

    def test_scripts_read_the_config_root_the_deployer_writes(self):
        for name in ("niri-brightness.sh", "shell-action.sh"):
            source = (self._niri_scripts() / name).read_text(encoding="utf-8")
            self.assertNotIn("XDG_CONFIG_HOME", source, name)

    def test_mpvpaper_reads_the_assignments_envelope(self):
        script = Path(__file__).resolve().parents[2] / "plugins" / "noctalia" / "mpvpaper-sync.sh"
        source = script.read_text(encoding="utf-8")
        self.assertIn(".assignments // .", source)

    def test_thumbnail_temp_file_keeps_an_image_suffix(self):
        script = Path(__file__).resolve().parents[2] / "plugins" / "noctalia" / "mpvpaper-sync.sh"
        source = script.read_text(encoding="utf-8")
        self.assertIn("${THUMB_PATH%.jpg}.tmp.$$.jpg", source)

    def test_eyecare_temp_is_preserved_across_deploys(self):
        manifest = Path(__file__).resolve().parents[2] / "plugins" / "niri" / "manifest.toml"
        self.assertIn("eyecare_temp", manifest.read_text(encoding="utf-8"))

    def test_set_temp_rejects_out_of_range_values(self):
        import shutil
        script = self._niri_scripts() / "toggle-eyecare.sh"
        if not shutil.which("bash"):
            self.skipTest("bash unavailable")
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home)
            for value in ("abc", "99999999", "999"):
                result = subprocess.run(["bash", str(script), "set-temp", value],
                                        capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 2, value)

class TestToolConfigRoot(unittest.TestCase):

    def test_scratch_menu_wrapper_ignores_a_divergent_xdg_config_home(self):
        script = (Path(__file__).resolve().parents[2] / "plugins" / "niri" / "scripts"
                  / "niri-scratch-menu.py")
        self.assertNotIn("XDG_CONFIG_HOME", script.read_text(encoding="utf-8"))

    def test_translate_config_path_follows_the_deployer(self):
        tools = Path(__file__).resolve().parents[2] / "plugins" / "noctalia" / "tools"
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            result = subprocess.run(
                [sys.executable, "-c",
                 'import sys; sys.path.insert(0, "%s")\n'
                 'from orbit_translate.config import config_path\n'
                 'print(config_path())' % tools],
                capture_output=True, text=True,
                env={"HOME": str(home), "XDG_CONFIG_HOME": str(home / "elsewhere"),
                     "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                     "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()),
                         home / ".config" / "noctalia" / "tools" / "orbit-translate__custom__.toml")

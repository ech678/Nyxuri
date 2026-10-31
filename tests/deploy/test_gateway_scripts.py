"""Regression tests for upstream defects fixed during the bug-hunt rounds.

Each test reproduces a concrete failure that shipped in v4.0.0-alpha.1 and
asserts the corrected behavior, so the defect cannot silently return.
"""

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class TestScriptContracts(unittest.TestCase):

    def _niri_scripts(self):
        return Path(__file__).resolve().parents[2] / "plugins" / "niri" / "scripts"

    def test_scripts_read_the_config_root_the_deployer_writes(self):
        for name in ("niri-brightness.sh", "niri-scratch-menu.py", "shell-action.sh"):
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

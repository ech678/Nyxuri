"""Tests for doctor preset-drift check (§8/§11)."""

import contextlib
import io
import unittest

from tests.utils import TempEnv


class TestPresetDrift(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _run_drift(self):
        from nyxuri.doctor import _check_preset_drift
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _check_preset_drift(self._ctx.env)
        return buf.getvalue()

    def test_default_active_no_warn(self):
        # All apps at default → no drift.
        self.assertNotIn("已不在仓库", self._run_drift())

    def test_active_existing_preset_no_warn(self):
        from nyxuri.deploy.preset import write_active_preset
        # 'transparent' exists in the shipped kitty presets → no drift.
        write_active_preset("kitty", "transparent")
        self.assertNotIn("已不在仓库", self._run_drift())

    def test_active_missing_preset_warns(self):
        from nyxuri.deploy.preset import write_active_preset
        write_active_preset("kitty", "ghost")  # not in repo or user presets
        out = self._run_drift()
        self.assertIn("kitty", out)
        self.assertIn("ghost", out)


if __name__ == "__main__":
    unittest.main()

"""Tests for doctor form-drift check (§8/§11)."""

import contextlib
import io
import unittest

from tests.utils import TempEnv


class TestFormDrift(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _run_drift(self):
        from nyxuri.sysdoctor import _check_form_drift
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _check_form_drift(self._ctx.env)
        return buf.getvalue()

    def test_default_active_no_warn(self):
        # All plugins at default → no drift.
        self.assertNotIn("已不在仓库", self._run_drift())

    def test_active_existing_form_no_warn(self):
        from nyxuri.deploy.forms import write_active_form
        # 'transparent' exists in the shipped kitty __forms__ → no drift.
        write_active_form("kitty", "transparent")
        self.assertNotIn("已不在仓库", self._run_drift())

    def test_active_missing_form_warns(self):
        from nyxuri.deploy.forms import write_active_form
        write_active_form("kitty", "ghost")  # not in repo or user forms
        out = self._run_drift()
        self.assertIn("kitty", out)
        self.assertIn("ghost", out)


if __name__ == "__main__":
    unittest.main()

"""Behavior contracts for the python3 -m nyxuri entrypoint guard.

A missing nyxuri.* module (engine tree mixed/partial, e.g. an update
interrupted mid-checkout) must fail with one clear line instead of a raw
traceback; foreign ModuleNotFoundError must propagate untouched.
"""

import io
import sys
import types
import unittest
from unittest.mock import patch

from nyxuri.__main__ import _run


class TestEntrypointGuard(unittest.TestCase):

    def _run_with_main_raising(self, exc):
        fake_cli = types.ModuleType("nyxuri.cli")

        def _main():
            raise exc

        fake_cli.main = _main
        with patch.dict(sys.modules, {"nyxuri.cli": fake_cli}):
            with patch("sys.stderr", new=io.StringIO()) as err:
                rc = _run()
        return rc, err.getvalue()

    def test_missing_engine_module_prints_clear_error(self):
        exc = ModuleNotFoundError("No module named 'nyxuri.ghost'", name="nyxuri.ghost")
        rc, err = self._run_with_main_raising(exc)
        self.assertEqual(rc, 1)
        self.assertIn("install.sh", err)
        self.assertNotIn("Traceback", err)

    def test_foreign_missing_module_reraised(self):
        exc = ModuleNotFoundError("No module named 'otherpkg'", name="otherpkg")
        with self.assertRaises(ModuleNotFoundError):
            self._run_with_main_raising(exc)

    def test_unnamed_missing_module_reraised(self):
        exc = ModuleNotFoundError("boom")
        with self.assertRaises(ModuleNotFoundError):
            self._run_with_main_raising(exc)

    def test_clean_run_returns_0(self):
        fake_cli = types.ModuleType("nyxuri.cli")
        fake_cli.main = lambda: None
        with patch.dict(sys.modules, {"nyxuri.cli": fake_cli}):
            rc = _run()
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

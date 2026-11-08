"""Behavior contracts for the python3 -m nyxuri entrypoint guard.

A missing nyxuri.* module (engine tree mixed/partial, e.g. an update
interrupted mid-checkout) must fail with one clear line instead of a raw
traceback; foreign ModuleNotFoundError must propagate untouched.

The launcher entry is also pinned here: update re-execs through it (#138), so
it has to resolve the engine package from any working directory.
"""

import io
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import nyxuri
from nyxuri.__main__ import _run
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import re



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


class TestLauncherEntry(unittest.TestCase):
    """launcher.sh must resolve the engine from any cwd without PYTHON* help —
    update's re-exec hands the process over to it (#138)."""

    def test_runs_from_foreign_cwd(self):
        launcher = Path(nyxuri.__file__).resolve().parent / "launcher.sh"
        if not launcher.is_file():
            self.skipTest("this tree ships no launcher.sh")
        with TempEnv():
            env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
            with tempfile.TemporaryDirectory() as cwd:
                result = subprocess.run(
                    [str(launcher), "help"], cwd=cwd, env=env,
                    capture_output=True, text=True, timeout=60,
                )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nyxuri", result.stdout)


if __name__ == "__main__":
    unittest.main()


class TestEntryPointImportGuard(unittest.TestCase):

    def test_partial_tree_import_error_is_reported_without_traceback(self):
        import shutil
        root = Path(tempfile.mkdtemp()) / "tree"
        shutil.copytree(Path(__file__).resolve().parents[2] / "nyxuri", root / "nyxuri")
        cli = root / "nyxuri" / "cli.py"
        cli.write_text("from nyxuri.system.env import NYXURI_MISSING_SYMBOL\n" + cli.read_text(encoding="utf-8"),
                       encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "nyxuri", "help"],
                cwd=str(root), capture_output=True, text=True,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(root)},
            )
        finally:
            shutil.rmtree(root.parent, ignore_errors=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)

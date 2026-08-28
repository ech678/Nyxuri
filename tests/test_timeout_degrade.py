"""Behavior contracts for timeout degradation (timed_run + call sites).

v3.0.3 shipped `timeout=` on external commands but only network.py caught
TimeoutExpired — every other site turned a hang into a crash (real-world:
fisher install stalled on weak network, whole deploy died mid-flow). These
tests pin the degrade semantics: external commands are polish, never
load-bearing; a timeout must skip the step and move on.
"""

import subprocess
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from tests.utils import TempEnv


def _cp(returncode=0, stdout=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class TestTimedRun(unittest.TestCase):

    def test_timeout_degrades_to_none(self):
        from nyxniri.core import timed_run

        with patch("nyxniri.core.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["x"], timeout=5)):
            self.assertIsNone(timed_run(["x"], 5, check=False))

    def test_passes_through_args_and_result(self):
        from nyxniri.core import timed_run

        with patch("nyxniri.core.subprocess.run", return_value=_cp(0)) as m:
            r = timed_run(["x"], 7, check=False, capture_output=True)
        m.assert_called_once_with(["x"], timeout=7, check=False, capture_output=True)
        self.assertEqual(r.returncode, 0)


class TestPostInstallHooksIndependence(unittest.TestCase):
    """A timed-out hook (theme-sync) must not abort the remaining hooks (fisher)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_sync_timeout_does_not_block_fisher(self):
        from nyxniri.deploy.deploy import _phase_post_install_services

        sync_script = self._ctx.env.config_dir / "noctalia" / "theme-sync.sh"
        sync_script.parent.mkdir(parents=True, exist_ok=True)
        sync_script.touch()

        with patch("nyxniri.deploy.deploy.timed_run", side_effect=[None, None]), \
             patch("nyxniri.deploy.deploy.shutil.which", return_value=True), \
             patch("nyxniri.modules.fisher.fisher_install") as mock_fisher, \
             patch("builtins.print"):
            _phase_post_install_services()

        mock_fisher.assert_called_once()


class TestDepsTimeout(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_pacman_timeout_degrades_to_empty_set(self):
        import nyxniri.deps as deps_mod

        deps_mod._PACMAN_INSTALLED_CACHE = None
        try:
            with patch("nyxniri.deps.timed_run", return_value=None):
                self.assertEqual(deps_mod._get_pacman_installed(), set())
        finally:
            deps_mod._PACMAN_INSTALLED_CACHE = None

    def test_fc_list_timeout_degrades_to_empty(self):
        import nyxniri.deps as deps_mod

        deps_mod._FC_LIST_CACHE = None
        try:
            with patch("nyxniri.deps.timed_run", return_value=None):
                self.assertEqual(deps_mod._get_fc_list(), "")
        finally:
            deps_mod._FC_LIST_CACHE = None

    def test_gi_probe_timeout_reports_missing(self):
        import nyxniri.deps as deps_mod

        with patch("nyxniri.deps.timed_run", return_value=None):
            self.assertFalse(deps_mod.is_dep_installed("python-gobject"))


class TestDoctorTimeout(unittest.TestCase):
    """One stalled probe must not kill the whole diagnosis."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_check_timeout_does_not_abort_run_doctor(self):
        from nyxniri.doctor import run_doctor

        def boom(env):
            raise subprocess.TimeoutExpired(cmd="probe", timeout=1)

        with patch("nyxniri.doctor.DOCTOR_SECTIONS", [("doctor_sec_x", [boom])]), \
             patch("builtins.print"):
            self.assertTrue(run_doctor())


class TestGitTimeout(unittest.TestCase):
    """safe_git_pull must return False (not crash) when the reset step stalls."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        # TempEnv defaults repo_dir to the real repo root — redirect into the
        # temp HOME so we never mkdir inside the actual repository tree.
        self._ctx.env.repo_dir = self._ctx.home / "repo"
        (self._ctx.env.repo_dir / ".git").mkdir(parents=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_reset_timeout_returns_false(self):
        from nyxniri.network import safe_git_pull

        fake_env = type("E", (), {"run_mode": "cache"})()
        with patch("nyxniri.network.get_env", return_value=fake_env), \
             patch("nyxniri.network.shutil.which", return_value=True), \
             patch("nyxniri.network.subprocess.run", return_value=_cp(0, "")), \
             patch("nyxniri.network._run_git_transfer", side_effect=[_cp(1), _cp(0)]), \
             patch("nyxniri.network.timed_run", return_value=None):
            self.assertIs(safe_git_pull(self._ctx.env.repo_dir), False)


class TestGtkThemeTimeout(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_render_timeout_degrades_to_pending(self):
        from nyxniri.modules.gtktheme import gtktheme_trigger_render

        with patch("nyxniri.modules.gtktheme.noctalia_available", return_value=True), \
             patch("nyxniri.modules.gtktheme.timed_run", return_value=None), \
             patch("builtins.print"):
            gtktheme_trigger_render()


if __name__ == "__main__":
    unittest.main()

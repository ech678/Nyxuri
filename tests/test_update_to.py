"""Behavior contracts for pinned updates: safe_git_checkout_ref."""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv


class TestSafeGitCheckoutRef(unittest.TestCase):
    """safe_git_checkout_ref must fail loud on dirty trees and carry network timeouts."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.home = self._ctx.home
        self.fake_repo = self.home / "fake-repo"
        self.fake_repo.mkdir()
        (self.fake_repo / ".git").mkdir()

    def tearDown(self):
        self._ctx.__exit__()

    def _run_mode(self):
        from nyxniri.core import get_env
        return get_env()

    def test_git_missing_returns_false_not_crash(self):
        from nyxniri.network import safe_git_checkout_ref

        with patch("shutil.which", return_value=None):
            with redirect_stdout(io.StringIO()):
                result = safe_git_checkout_ref(Path("/fake/repo"), "v9.9.9")

        self.assertFalse(result, "Should return False when git is missing")

    def test_dirty_tree_refused_returns_false(self):
        """Pinned reset is destructive: dirty tree must fail (False), never skip (None)."""
        from nyxniri.network import safe_git_checkout_ref

        env = self._run_mode()
        env.run_mode = "repo"
        env.repo_dir = self.fake_repo

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "status" in cmd and "--porcelain" in cmd:
                mock.stdout = " M some-file\n"
                mock.returncode = 0
            else:
                mock.stdout = ""
                mock.returncode = 0
            return mock

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run", side_effect=fake_run):
                with redirect_stdout(io.StringIO()):
                    result = safe_git_checkout_ref(self.fake_repo, "v9.9.9")

        self.assertEqual(result, False, "Dirty tree must be refused with False")

    def test_clean_tree_fetches_ref_with_timeouts_then_resets_to_fetch_head(self):
        from nyxniri.network import safe_git_checkout_ref

        env = self._run_mode()
        env.run_mode = "repo"
        env.repo_dir = self.fake_repo

        commands = []

        def fake_run(cmd, **kwargs):
            commands.append(cmd)
            mock = MagicMock()
            mock.stdout = ""
            mock.returncode = 0
            return mock

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run", side_effect=fake_run):
                with redirect_stdout(io.StringIO()):
                    result = safe_git_checkout_ref(self.fake_repo, "abc1234")

        self.assertTrue(result, "Clean tree should succeed")
        fetch_cmds = [c for c in commands if "fetch" in c]
        reset_cmds = [c for c in commands if "reset" in c]
        self.assertEqual(len(fetch_cmds), 1, "Exactly one fetch expected")
        self.assertEqual(len(reset_cmds), 1, "Exactly one reset expected")
        fetch = fetch_cmds[0]
        self.assertIn("abc1234", fetch, "Fetch must target the requested ref")
        self.assertIn("--depth", fetch, "Fetch must stay shallow")
        joined = " ".join(fetch)
        self.assertIn("http.lowSpeedLimit", joined, "Fetch must carry network timeouts")
        self.assertIn("http.timeout", joined, "Fetch must carry overall timeout")
        self.assertIn("FETCH_HEAD", reset_cmds[0], "Reset must target FETCH_HEAD")

    def test_system_mode_skips_returns_none(self):
        from nyxniri.network import safe_git_checkout_ref

        env = self._run_mode()
        env.run_mode = "system"

        with patch("shutil.which", return_value="/usr/bin/git"):
            with redirect_stdout(io.StringIO()):
                result = safe_git_checkout_ref(self.fake_repo, "v9.9.9")

        self.assertIsNone(result, "System mode should skip (None), pointing at pacman")


if __name__ == "__main__":
    unittest.main()

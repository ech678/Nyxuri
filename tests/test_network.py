"""Behavior contracts for network: dirty tree return value, git existence check."""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv


class TestGitExistenceCheck(unittest.TestCase):
    """safe_git_pull must check git exists before running git commands."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_git_missing_returns_false_not_crash(self):
        """If git is not installed, should return False with friendly message, not crash."""
        from nyxniri.network import safe_git_pull

        with patch("shutil.which", return_value=None):
            with redirect_stdout(io.StringIO()):
                result = safe_git_pull(Path("/fake/repo"))

        self.assertFalse(result, "Should return False when git is missing")


class TestRawFetchDigest(unittest.TestCase):
    """A reviewed raw asset must match its digest before it is handed to Fish."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_digest_mismatch_never_moves_downloaded_file(self):
        from nyxniri.network import _ProcessAttempt, fetch_raw_with_fallback

        target = self._ctx.home / "bootstrap.fish"
        url = "https://example.invalid/org/repo/commit/file.fish"

        def fake_process(command, **kwargs):
            tmp_path = Path(command[9])
            self.assertEqual(
                command,
                ["curl", "-sfL", "--connect-timeout", "3", "-m", "10", "-w", "%{http_code}",
                 "-o", str(tmp_path), url],
            )
            tmp_path.write_text("unexpected", encoding="utf-8")
            return _ProcessAttempt(0, "200")

        with patch("nyxniri.network.RAW_MIRROR_TEMPLATES", [("test", url)]), \
             patch("nyxniri.network._run_cancellable_process", side_effect=fake_process), \
             redirect_stdout(io.StringIO()):
            self.assertFalse(fetch_raw_with_fallback("org/repo", "commit", "file.fish", target, "0" * 64))

        self.assertFalse(target.exists())


class TestDirtyTreeReturnValue(unittest.TestCase):
    """Non-interactive dirty tree must return False (not None), so exit code is non-zero."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.home = self._ctx.home

    def tearDown(self):
        self._ctx.__exit__()

    def test_non_interactive_dirty_tree_returns_false(self):
        """Non-interactive + dirty tree should return False (not None=skip, not True=ok)."""
        from nyxniri.network import safe_git_pull

        fake_repo = self.home / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / ".git").mkdir()

        # Force standalone mode so dirty tree doesn't short-circuit on "repo" mode
        from nyxniri.core import get_env
        get_env().run_mode = "standalone"
        get_env().repo_dir = fake_repo

        # git status --porcelain returns dirty
        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "status" in cmd and "--porcelain" in cmd:
                mock.stdout = " M some-file\n"  # dirty
                mock.returncode = 0
            else:
                mock.stdout = ""
                mock.returncode = 0
            return mock

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run", side_effect=fake_run):
                with patch("sys.stdin.isatty", return_value=False):
                    with redirect_stdout(io.StringIO()):
                        result = safe_git_pull(fake_repo)

        self.assertEqual(result, False,
                         "Non-interactive dirty tree should return False (non-zero exit), not None (skip)")

    def test_interactive_dirty_tree_cancelled_returns_none(self):
        """Interactive + dirty tree + user says no → None (skip)."""
        from nyxniri.network import safe_git_pull

        fake_repo = self.home / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / ".git").mkdir()

        from nyxniri.core import get_env
        get_env().run_mode = "standalone"
        get_env().repo_dir = fake_repo

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
                with patch("sys.stdin.isatty", return_value=True):
                    with patch("nyxniri.network.prompt_confirm", return_value=False):
                        with redirect_stdout(io.StringIO()):
                            result = safe_git_pull(fake_repo)

        self.assertIsNone(result,
                          "Interactive dirty tree with user cancel should return None (skip)")

    def test_clean_tree_proceeds_to_pull(self):
        """Clean tree should proceed to git pull."""
        from nyxniri.network import safe_git_pull

        fake_repo = self.home / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / ".git").mkdir()

        from nyxniri.core import get_env
        get_env().run_mode = "standalone"
        get_env().repo_dir = fake_repo

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "status" in cmd and "--porcelain" in cmd:
                mock.stdout = ""  # clean
                mock.returncode = 0
            elif "pull" in cmd:
                mock.stdout = "Already up to date."
                mock.returncode = 0
            else:
                mock.stdout = ""
                mock.returncode = 0
            return mock

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("nyxniri.network._run_git_transfer") as mock_transfer:
                mock_transfer.return_value = MagicMock(returncode=0)
                with redirect_stdout(io.StringIO()):
                    result = safe_git_pull(fake_repo)

        self.assertTrue(result, "Clean tree with successful pull should return True")


class TestGitProgressInsertion(unittest.TestCase):
    """--progress 必须插在 git 子命令之后，绝不能成为 -c 的 value。"""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_progress_after_subcommand_for_c_prefixed_pull(self):
        """对 `git -c K=V -c K=V pull --ff-only`，--progress 必须在 pull 之后。"""
        from nyxniri.network import _with_git_progress

        with patch("sys.stderr.isatty", return_value=True):
            cmd, show = _with_git_progress(
                ["git", "-c", "http.lowSpeedLimit=1000",
                 "-c", "http.lowSpeedTime=15", "pull", "--ff-only"]
            )
        self.assertTrue(show)
        # --progress 绝不能紧跟在 -c 后面（否则会被当成 -c 的 key）
        for i, tok in enumerate(cmd):
            if tok == "-c":
                self.assertNotEqual(cmd[i + 1], "--progress",
                                    "--progress must not become the -c value")
        # 子命令 pull 必须在 --progress 之前
        self.assertLess(cmd.index("pull"), cmd.index("--progress"))
        self.assertEqual(cmd, ["git", "-c", "http.lowSpeedLimit=1000",
                               "-c", "http.lowSpeedTime=15",
                               "pull", "--progress", "--ff-only"])

    def test_progress_after_clone_subcommand(self):
        """对 `git clone -c ...`，--progress 必须紧跟 clone 之后。"""
        from nyxniri.network import _with_git_progress

        with patch("sys.stderr.isatty", return_value=True):
            cmd, show = _with_git_progress(
                ["git", "clone", "-c", "http.lowSpeedTime=15",
                 "-c", "http.lowSpeedLimit=1000",
                 "--depth", "1", "url", "dir"]
            )
        self.assertTrue(show)
        self.assertEqual(cmd[1], "clone")
        self.assertEqual(cmd[2], "--progress")

    def test_no_progress_when_not_tty(self):
        """非 tty 环境不应注入 --progress。"""
        from nyxniri.network import _with_git_progress

        with patch("sys.stderr.isatty", return_value=False):
            cmd, show = _with_git_progress(
                ["git", "-c", "K=V", "pull", "--ff-only"]
            )
        self.assertFalse(show)
        self.assertNotIn("--progress", cmd)


class TestSafeGitPullCommandShape(unittest.TestCase):
    """safe_git_pull 构造的 pull 命令必须含完整网络超时 flag（§9 参数形状契约）。

    mock 打在 subprocess.run 层（紧贴被测代码），让命令流经 _with_git_progress
    构造逻辑，而非在 _run_git_transfer 层截断绕过构造（见 AGENTS.md §9 反例）。
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.home = self._ctx.home

    def tearDown(self):
        self._ctx.__exit__()

    def test_pull_command_has_network_timeouts(self):
        from nyxniri.network import safe_git_pull
        from nyxniri.core import get_env

        fake_repo = self.home / "fake-repo"
        fake_repo.mkdir()
        (fake_repo / ".git").mkdir()
        get_env().run_mode = "standalone"
        get_env().repo_dir = fake_repo

        captured = {}

        def fake_run(cmd, **kw):
            m = MagicMock()
            if "status" in cmd and "--porcelain" in cmd:
                m.stdout = ""  # clean tree
                m.returncode = 0
            elif "pull" in cmd:
                captured["cmd"] = cmd
                m.stdout = "Already up to date."
                m.returncode = 0
            else:
                m.stdout = ""
                m.returncode = 0
            return m

        with patch("shutil.which", return_value="/usr/bin/git"), \
             patch("subprocess.run", side_effect=fake_run), \
             redirect_stdout(io.StringIO()):
            result = safe_git_pull(fake_repo)

        self.assertTrue(result)
        cmd = captured["cmd"]
        for flag in ("http.connectTimeout=10", "http.timeout=20",
                     "http.lowSpeedLimit=1000", "http.lowSpeedTime=15"):
            self.assertIn(flag, cmd)
        self.assertIn("pull", cmd)
        self.assertIn("--ff-only", cmd)


if __name__ == "__main__":
    unittest.main()

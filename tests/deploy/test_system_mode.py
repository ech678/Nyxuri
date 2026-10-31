"""Contract tests for system mode (§5, §14 C2).

Covers: .system-install marker detection (first), repo/standalone fallbacks,
PATH occlusion warning, safe_git_pull system branch, and ensure_nyxuri_symlink
no-op in system mode.
"""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nyxuri.core as core
import nyxuri.tui as tui
from tests.utils import TempEnv


class TestDetectRunMode(unittest.TestCase):
    """§14 C2: branch coverage for the marker-first mode detection."""

    def test_system_marker_wins_over_repo_signature(self):
        # A root with .system-install AND configs/+assets/ → system (not repo).
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / ".system-install").touch()
            (root / "plugins").mkdir()
            (root / "assets").mkdir()
            cache = Path("/nonexistent/cache")
            mode, label, repo = core._detect_run_mode(root, cache)
            self.assertEqual(mode, "system")
            self.assertEqual(label, "System Package")
            self.assertEqual(repo, root)

    def test_repo_when_configs_and_assets_present(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "plugins").mkdir()
            (root / "assets").mkdir()
            cache = Path("/nonexistent/cache")
            mode, label, repo = core._detect_run_mode(root, cache)
            self.assertEqual(mode, "repo")
            self.assertEqual(repo, root)

    def test_standalone_when_root_equals_cache(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            mode, label, repo = core._detect_run_mode(root, root)
            self.assertEqual(mode, "standalone")
            self.assertEqual(repo, root)

    def test_standalone_fallback_when_nothing_matches(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)  # no marker, no configs/assets, not the cache
            cache = Path("/nonexistent/cache")
            mode, label, repo = core._detect_run_mode(root, cache)
            self.assertEqual(mode, "standalone")
            self.assertEqual(repo, cache)


class TestCheckPathOcclusion(unittest.TestCase):
    """§5.3: system mode warns when ~/.local/bin/nyxuri shadows /usr/bin/nyxuri."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_warns_in_system_mode_when_user_link_present(self):
        self._ctx.env.run_mode = "system"
        (self._ctx.env.home / ".local/bin").mkdir(parents=True, exist_ok=True)
        (self._ctx.env.home / ".local/bin" / "nyxuri").symlink_to("/usr/bin/nyxuri")
        with patch("builtins.print"):
            self.assertTrue(core.check_path_occlusion())

    def test_silent_in_system_mode_when_no_user_link(self):
        self._ctx.env.run_mode = "system"
        with patch("builtins.print"):
            self.assertFalse(core.check_path_occlusion())

    def test_silent_outside_system_mode(self):
        self._ctx.env.run_mode = "repo"
        (self._ctx.env.home / ".local/bin").mkdir(parents=True, exist_ok=True)
        (self._ctx.env.home / ".local/bin" / "nyxuri").symlink_to("/usr/bin/foo")
        with patch("builtins.print"):
            self.assertFalse(core.check_path_occlusion())


class TestEnsureSymlinkSystemMode(unittest.TestCase):
    """§5.3: in system mode the package owns the CLI; the user link is untouched."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_system_mode_does_not_create_user_link(self):
        self._ctx.env.run_mode = "system"
        target = self._ctx.env.home / ".local/bin" / "nyxuri"
        core.ensure_nyxuri_symlink()
        self.assertFalse(target.exists(), "system mode must not create a user-territory link")


class TestCliLinkOwnership(unittest.TestCase):
    """The CLI only replaces and removes its own expected symlink."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.target = self.env.home / ".local/bin" / "nyxuri"

    def tearDown(self):
        self._ctx.__exit__()

    def _uninstall_cli(self):
        from nyxuri.state.uninstall import uninstall_nyxuri

        with patch("sys.stdin.isatty", return_value=False), \
             patch("builtins.print"):
            self.assertTrue(uninstall_nyxuri("all"))

    def test_regular_file_survives_cli_start_and_uninstall(self):
        self.target.write_text("my launcher")
        core.ensure_nyxuri_symlink()
        self.assertEqual(self.target.read_text(), "my launcher")
        self._uninstall_cli()
        self.assertEqual(self.target.read_text(), "my launcher")

    def test_directory_survives_cli_start_and_uninstall(self):
        self.target.mkdir()
        core.ensure_nyxuri_symlink()
        self.assertTrue(self.target.is_dir())
        self._uninstall_cli()
        self.assertTrue(self.target.is_dir())

    def test_foreign_and_dangling_foreign_links_survive(self):
        for name, destination in (
            ("foreign", self.env.home / "other-launcher"),
            ("dangling", self.env.home / "missing-launcher"),
        ):
            with self.subTest(name=name):
                self.target.symlink_to(destination)
                core.ensure_nyxuri_symlink()
                self.assertTrue(self.target.is_symlink())
                self.assertEqual(self.target.resolve(strict=False), destination.resolve(strict=False))
                self._uninstall_cli()
                self.assertTrue(self.target.is_symlink())
                self.assertEqual(self.target.resolve(strict=False), destination.resolve(strict=False))
                self.target.unlink()

    def test_created_link_is_kept_then_removed(self):
        marker = self.env.state_dir / "nyxuri.link"
        core.ensure_nyxuri_symlink()
        before = self.target.lstat().st_ino
        core.ensure_nyxuri_symlink()
        self.assertEqual(self.target.lstat().st_ino, before)
        self.assertTrue(marker.is_file())
        self._uninstall_cli()
        self.assertFalse(self.target.is_symlink())
        self.assertFalse(marker.exists())

    def test_cli_start_adopts_unrecorded_expected_link_and_records_marker(self):
        self.target.symlink_to(self.env.repo_dir / "nyxuri" / "launcher.sh")
        core.ensure_nyxuri_symlink()
        marker = self.env.state_dir / "nyxuri.link"
        self.assertTrue(marker.is_file(), "adopted link must have marker recorded")
        self._uninstall_cli()
        self.assertFalse(self.target.is_symlink(), "adopted link is cleanly removed on uninstall")

    def test_pre_km5_installer_link_is_healed_to_launcher(self):
        """One-generation heal: links owned by the pre-KM5 entry (which pointed
        at install.sh, then the launcher itself) are re-pointed to the launcher."""
        self.target.symlink_to(self.env.repo_dir / "install.sh")
        core.ensure_nyxuri_symlink()
        self.assertEqual(
            self.target.resolve(strict=False),
            (self.env.repo_dir / "nyxuri" / "launcher.sh").resolve(strict=False),
        )
        marker = self.env.state_dir / "nyxuri.link"
        self.assertTrue(marker.is_file())

    def test_dangling_nyxniri_cache_link_is_healed(self):
        # User previously ran remote cache script, but cache was cleared or missing
        dangling_target = self.env.cache_dir / "install.sh"
        self.target.symlink_to(dangling_target)
        self.assertFalse(self.target.exists(), "must be a dangling link initially")
        core.ensure_nyxuri_symlink()
        self.assertEqual(
            self.target.resolve(strict=False),
            (self.env.repo_dir / "nyxuri" / "launcher.sh").resolve(strict=False),
            "dangling NyxNiri link must be healed to the current launcher",
        )
        marker = self.env.state_dir / "nyxuri.link"
        self.assertTrue(marker.is_file())

    def test_dangling_expected_link_is_removed(self):
        source = self.env.home / "old-nyxuri"
        source.mkdir()
        (source / "nyxuri").mkdir()
        launcher = source / "nyxuri" / "launcher.sh"
        launcher.write_text("#!/bin/sh\n")
        self.env.repo_dir = source
        core.ensure_nyxuri_symlink()
        launcher.unlink()
        self.assertTrue(self.target.is_symlink())
        self._uninstall_cli()
        self.assertFalse(self.target.is_symlink())

    def test_forged_marker_does_not_claim_foreign_link(self):
        foreign = self.env.home / "another-launcher"
        marker = self.env.state_dir / "nyxuri.link"
        self.target.symlink_to(foreign)
        marker.write_text(f"{foreign}\n0:0\n")
        core.ensure_nyxuri_symlink()
        self._uninstall_cli()
        self.assertTrue(self.target.is_symlink())

    def test_stale_marker_does_not_claim_replaced_link(self):
        marker = self.env.state_dir / "nyxuri.link"
        core.ensure_nyxuri_symlink()
        self.target.unlink()
        self.target.symlink_to(self.env.home / "another-launcher")
        core.ensure_nyxuri_symlink()
        self.assertTrue(marker.is_file())
        self._uninstall_cli()
        self.assertTrue(self.target.is_symlink())

    def test_owned_link_updates_to_new_launcher(self):
        old_source = self.env.home / "old-nyxuri"
        new_source = self.env.home / "new-nyxuri"
        for source in (old_source, new_source):
            source.mkdir()
            (source / "nyxuri").mkdir()
            (source / "nyxuri" / "launcher.sh").write_text("#!/bin/sh\n")
        old_launcher = old_source / "nyxuri" / "launcher.sh"
        new_launcher = new_source / "nyxuri" / "launcher.sh"
        self.env.repo_dir = old_source
        core.ensure_nyxuri_symlink()
        self.env.repo_dir = new_source
        core.ensure_nyxuri_symlink()
        self.assertEqual(self.target.resolve(strict=False), new_launcher.resolve(strict=False))
        self._uninstall_cli()
        self.assertFalse(self.target.is_symlink())

    def test_xdg_state_home_outside_home_is_isolated(self):
        import os
        from nyxuri.core import Environment
        with patch.dict(os.environ, {"XDG_STATE_HOME": "/some/foreign/home/.local/state"}):
            env = Environment()
            self.assertEqual(
                env.state_dir,
                env.home / ".local/state" / "nyxuri",
                "XDG_STATE_HOME outside home must not be used",
            )


class TestSafeGitPullSystemBranch(unittest.TestCase):
    """§5.6: system mode refuses git pull, hints pacman.

    Regression (2026-10-18 real-package smoke): the repo-shape guards used to
    precede the system branch — a pacman-owned tree ships NO .git, so real
    system packages got "update failed" instead of the pacman hint. The short
    circuit must fire before any .git probing.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self._ctx.env.run_mode = "system"
        # Real package shape: NO .git in the tree (payload ships code only).
        self._ctx.env.repo_dir = self._ctx.home / "repo"
        self._ctx.env.repo_dir.mkdir(parents=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_system_mode_returns_none_without_git_dir(self):
        from nyxuri.pkg.net import safe_git_pull
        with patch("nyxuri.pkg.net.shutil.which", return_value="/usr/bin/git"), \
             patch("builtins.print"):
            result = safe_git_pull(self._ctx.env.repo_dir)
        self.assertIsNone(result, "system mode must skip git pull (return None)")

    def test_system_mode_pinned_checkout_returns_none_without_git_dir(self):
        from nyxuri.pkg.net import safe_git_checkout_ref
        with patch("nyxuri.pkg.net.shutil.which", return_value="/usr/bin/git"), \
             patch("builtins.print"):
            result = safe_git_checkout_ref(self._ctx.env.repo_dir, "v1.2.3")
        self.assertIsNone(result, "system mode must skip pinned checkout (return None)")


class TestRemovePath(unittest.TestCase):
    """core.remove_path: symlink-to-dir is unlinked, not rmtree'd through the link.

    Regression guard for the cleanup_temp_paths latent bug (is_dir() follows the
    link → would delete the target's contents). The symlink check precedes is_dir().
    """

    def test_symlink_to_dir_unlinks_link_not_target(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            target_dir = root / "real"
            target_dir.mkdir()
            (target_dir / "file").write_text("payload")
            link = root / "link"
            link.symlink_to(target_dir)
            core.remove_path(link)
            self.assertFalse(link.exists(), "symlink must be removed")
            self.assertTrue(target_dir.is_dir(), "target dir must survive (link not followed)")
            self.assertTrue((target_dir / "file").exists(), "target contents must survive")

    def test_regular_dir_removed(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "sub"
            d.mkdir()
            (d / "f").write_text("x")
            core.remove_path(d)
            self.assertFalse(d.exists())

    def test_missing_path_is_noop(self):
        # Must not raise on a path that does not exist, and must not create it.
        target = Path("/nonexistent/nyxuri-does-not-exist")
        core.remove_path(target)
        self.assertFalse(target.exists())


class TestRawInputMode(unittest.TestCase):
    """raw_input_mode no-ops on non-tty stdin (tests rely on this); drain discards bytes."""

    def test_noop_on_non_tty_stdin(self):
        with tui.raw_input_mode(tui.stdin_fd()):
            pass
        self.assertTrue(True)

    def test_noop_on_stdin_without_fileno(self):
        class NoFileno:
            def isatty(self):
                return True

            def fileno(self):
                raise io.UnsupportedOperation("redirected stdin is pseudofile")

        with patch.object(sys, "stdin", NoFileno()):
            self.assertIsNone(tui.stdin_fd())
            with tui.raw_input_mode(tui.stdin_fd()):
                pass
        self.assertTrue(True)

    def test_drain_pending_discards_pipe_bytes(self):
        r, w = os.pipe()
        os.write(w, b"abc")
        os.close(w)
        tui._drain_pending(r)  # must drain "abc" without blocking, then return at EOF
        self.assertEqual(os.read(r, 64), b"")  # fully drained (EOF)

    def test_drain_stdin_noop_on_non_tty(self):
        tui.drain_stdin()  # guarded by isatty() → no-op, no raise/block


if __name__ == "__main__":
    unittest.main()

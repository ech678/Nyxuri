"""Behavior contracts for pinned updates: safe_git_checkout_ref."""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import subprocess
import sys



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
        from nyxuri.core import get_env
        return get_env()

    def test_git_missing_returns_false_not_crash(self):
        from nyxuri.pkg.net import safe_git_checkout_ref

        with patch("shutil.which", return_value=None):
            with redirect_stdout(io.StringIO()):
                result = safe_git_checkout_ref(Path("/fake/repo"), "v9.9.9")

        self.assertFalse(result, "Should return False when git is missing")

    def test_dirty_tree_refused_returns_false(self):
        """Pinned reset is destructive: dirty tree must fail (False), never skip (None)."""
        from nyxuri.pkg.net import safe_git_checkout_ref

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
        from nyxuri.pkg.net import safe_git_checkout_ref

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
        from nyxuri.pkg.net import safe_git_checkout_ref

        env = self._run_mode()
        env.run_mode = "system"

        with patch("shutil.which", return_value="/usr/bin/git"):
            with redirect_stdout(io.StringIO()):
                result = safe_git_checkout_ref(self.fake_repo, "v9.9.9")

        self.assertIsNone(result, "System mode should skip (None), pointing at pacman")


if __name__ == "__main__":
    unittest.main()


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestIssue139UpdateNeverClobbersUserFiles(unittest.TestCase):
    """Issue #139: `nyxuri update` silently overwrote user-edited managed
    files (binds.kdl / config.kdl) and silently deleted user-placed files
    (fish conf.d/zz-tools.fish). The ownership carry makes both impossible:
    the swap judges every dest entry against the ledger baseline and carries
    what the engine cannot explain. --force stays the explicit adopt verb."""

    def _stage_unit(self, ctx):
        configs = ctx.home / "configs-src"
        plugin = configs / "app"
        plugin.mkdir(parents=True, exist_ok=True)
        (plugin / "manifest.toml").write_text("packages = []\n", encoding="utf-8")
        (plugin / "a.conf").write_text("v1\n", encoding="utf-8")
        ctx.env.plugins_src = configs
        import nyxuri.deploy.deploy as _deploy_core
        import nyxuri.deploy.manifest as _deploy_manifest
        _deploy_core._CONFIG_ITEMS_CACHE = []
        _deploy_manifest._MANIFEST_CACHE = None
        return plugin

    def _run_update(self, flag=""):
        from nyxuri.installer.workflows import offer_overwrite_upgrade

        captured = {}
        with patch("sys.stdin.isatty", return_value=False), \
             patch("nyxuri.installer.workflows._enable_wallpapers", return_value=True), \
             patch("nyxuri.installer.workflows._enable_theme", return_value=True), \
             patch("nyxuri.installer.workflows.run_user_hooks", return_value=[]), \
             patch("nyxuri.installer.workflows.render_completion_screen") as screen:
            ok = offer_overwrite_upgrade(flag)
        if screen.call_args:
            captured["preserved"] = screen.call_args.kwargs.get("preserved_lines") or []
            captured["notices"] = screen.call_args.kwargs.get("notice_lines") or []
            captured["groups"] = screen.call_args.kwargs.get("carried_groups") or {}
        return ok, captured

    def test_update_carries_edits_and_extra_files_then_force_adopts(self):
        from nyxuri.kernel import ledger, transaction

        with TempEnv() as ctx:
            plugin = self._stage_unit(ctx)
            self.assertTrue(transaction.plugin_on("app")[0].ok)
            dest = ctx.home / ".config/app"
            # The user's two fatal moves from the issue: editing a managed
            # file and dropping a personal file next to it.
            (dest / "a.conf").write_text("my binds\n", encoding="utf-8")
            (dest / "zz-tools.fish").write_text("atuin init\n", encoding="utf-8")
            # The repo moves on.
            plugin.joinpath("a.conf").write_text("v2\n", encoding="utf-8")

            ok, captured = _quiet(self._run_update, "")
            self.assertTrue(ok)
            self.assertEqual((dest / "a.conf").read_text(), "my binds\n",
                             "user edits must never be clobbered by an update")
            self.assertEqual((dest / "zz-tools.fish").read_text(), "atuin init\n",
                             "user-placed files must never be deleted by an update")
            self.assertEqual(captured["groups"].get("modified"), ["~/.config/app/a.conf"])
            self.assertTrue(any("zz-tools.fish" in line for line in captured["preserved"]))
            rec = ledger.get_plugin("app")
            self.assertNotIn("a.conf", rec["files"],
                             "a carried file must never read as engine-laid")
            self.assertEqual(transaction.audit_plugins("app"), {"app": "Synced"})

            # --force is the adopt verb: template side wins, baseline clears.
            ok, _ = _quiet(self._run_update, "--force")
            self.assertTrue(ok)
            self.assertEqual((dest / "a.conf").read_text(), "v2\n")
            self.assertEqual((dest / "zz-tools.fish").read_text(), "atuin init\n",
                             "force adopts the template, it is not a purge")
            self.assertEqual(
                ledger.get_plugin("app")["files"]["a.conf"],
                __import__("hashlib").sha256((dest / "a.conf").read_bytes()).hexdigest(),
            )
            self.assertEqual(transaction.audit_plugins("app"), {"app": "Synced"})

    def test_ghost_unit_update_freezes_and_hints_adoption(self):
        from nyxuri.kernel import ledger, transaction

        with TempEnv() as ctx:
            plugin = self._stage_unit(ctx)
            dest = ctx.home / ".config/app"
            dest.mkdir(parents=True)
            (dest / "a.conf").write_text("v3-era\n", encoding="utf-8")
            self.assertIsNone(ledger.get_plugin("app"), "precondition: Ghost")

            ok, captured = _quiet(self._run_update, "")
            self.assertTrue(ok)
            self.assertEqual((dest / "a.conf").read_text(), "v3-era\n",
                             "an unregistered plugin's content is never overwritten")
            self.assertTrue(any("app" in line for line in captured["notices"]),
                             "the update must point at `nyxuri on` adoption")
            self.assertIsNone(ledger.get_plugin("app"),
                              "the installer never invents switch state")

            # Adoption is the explicit way out: template claims its names.
            self.assertTrue(transaction.plugin_on("app")[0].ok)
            self.assertEqual((dest / "a.conf").read_text(), "v1\n")
            self.assertEqual(transaction.audit_plugins("app"), {"app": "Synced"})


if __name__ == "__main__":
    unittest.main()

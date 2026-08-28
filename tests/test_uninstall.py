"""Contract tests for the checkbox uninstall + 5 gap fixes (§8, §14 B3/D1).

Covers: only-installed modules are shown/uninstalled; execution order (module
uninstallers before state_dir deletion); NyxNiri_archive_* glob cleanup (gap #1);
fisher uninstall incl. fish-absent degrade (gap #3); quickphrase.conf restore
(gap #5); greeter /var/lib removal (gap #2).
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv


class TestUninstallModuleVisibility(unittest.TestCase):
    """§14 B3: only installed modules are uninstalled (all_keys reflects install)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_only_installed_module_uninstallers_run(self):
        from nyxniri.state.uninstall import uninstall_nyxniri

        fcitx_u = MagicMock()
        gtk_u = MagicMock()
        greeter_u = MagicMock()
        fisher_u = MagicMock()
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.state.uninstall.copy_path"), patch("nyxniri.state.uninstall.remove_path"), \
             patch("nyxniri.state.uninstall.get_pics_dir", return_value=self._ctx.env.home / "Pictures"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=False), \
             patch("nyxniri.modules.fcitx.fcitx_uninstall", side_effect=fcitx_u), \
             patch("nyxniri.modules.gtktheme.gtktheme_uninstall", side_effect=gtk_u), \
             patch("nyxniri.modules.greeter.greeter_uninstall", side_effect=greeter_u), \
             patch("nyxniri.modules.fisher.fisher_uninstall", side_effect=fisher_u):
            result = uninstall_nyxniri("")

        self.assertTrue(result)
        fcitx_u.assert_called_once()   # installed → uninstalled
        gtk_u.assert_not_called()
        greeter_u.assert_not_called()
        fisher_u.assert_not_called()  # fisher.fish absent → not shown → not called

    def test_greeter_uninstall_failure_propagates(self):
        from nyxniri.state.uninstall import uninstall_nyxniri

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.state.uninstall.copy_path"), patch("nyxniri.state.uninstall.remove_path"), \
             patch("nyxniri.state.uninstall.get_pics_dir", return_value=self._ctx.env.home / "Pictures"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=False), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=True), \
             patch("nyxniri.modules.greeter.greeter_uninstall", return_value=False), \
             patch("nyxniri.modules.fisher.fisher_installed", return_value=False):
            result = uninstall_nyxniri("")

        self.assertFalse(result)


class TestUninstallExecutionOrder(unittest.TestCase):
    """§14 B3: module uninstallers run BEFORE nyx_dir/state_dir deletion."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("x")

    def tearDown(self):
        self._ctx.__exit__()

    def test_fcitx_runs_before_state_dir_deleted(self):
        from nyxniri.state.uninstall import uninstall_nyxniri

        state_at_fcitx = {}

        def fcitx_side():
            # When fcitx runs, state_dir (holding its .prev) must still exist.
            state_at_fcitx["exists"] = self.env.state_dir.exists()

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.state.uninstall.copy_path"), \
             patch("nyxniri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=False), \
             patch("nyxniri.modules.fcitx.fcitx_uninstall", side_effect=fcitx_side):
            uninstall_nyxniri("")

        self.assertTrue(state_at_fcitx.get("exists"), "state_dir must outlive module uninstallers")


class TestUninstallArchiveGlob(unittest.TestCase):
    """Gap #1: NyxNiri_archive_* dirs are cleaned when 'archives' selected."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_old_archives_cleaned_new_archive_preserved(self):
        from nyxniri.state.uninstall import uninstall_nyxniri
        from nyxniri.constants import PROJECT_NAME

        old = self.env.config_dir / f"{PROJECT_NAME}_archive_20250101_000000"
        old.mkdir(parents=True)
        (old / "niri").mkdir()
        (old / "niri" / "config.kdl").write_text("old")
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("current")

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=False), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=False):
            uninstall_nyxniri("")  # non-TTY → all selected, configs archived

        # Old archive cleaned (gap #1), but the freshly-created config archive survives.
        self.assertFalse(old.exists(), "Pre-existing archive must be cleaned")
        new_archives = list(self.env.config_dir.glob(f"{PROJECT_NAME}_archive_*"))
        self.assertEqual(len(new_archives), 1, "Only the freshly-created archive remains")
        self.assertTrue((new_archives[0] / "niri" / "config.kdl").exists())


class TestFisherOwnership(unittest.TestCase):
    """Fisher cleanup is limited to the files recorded by NyxNiri."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.fish_dir = self.env.config_dir / "fish"
        (self.fish_dir / "functions").mkdir(parents=True)
        (self.fish_dir / "conf.d").mkdir(parents=True)

    def tearDown(self):
        self._ctx.__exit__()

    def _write_lockfile(self, content=None):
        from nyxniri.modules.fisher import FISHER_PLUGINS

        (self.fish_dir / "fish_plugins").write_text(
            content if content is not None else "\n".join(FISHER_PLUGINS) + "\n",
            encoding="utf-8",
        )

    def test_uninstall_without_ownership_preserves_existing_fisher(self):
        from nyxniri.modules.fisher import fisher_uninstall

        fisher_file = self.fish_dir / "functions" / "fisher.fish"
        unrelated = self.fish_dir / "conf.d" / "user-plugin.fish"
        fisher_file.write_text("user fisher", encoding="utf-8")
        unrelated.write_text("user plugin", encoding="utf-8")

        with patch("nyxniri.modules.fisher.shutil.which", return_value=None):
            self.assertFalse(fisher_uninstall())

        self.assertEqual(fisher_file.read_text(encoding="utf-8"), "user fisher")
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "user plugin")

    def test_fish_absent_removes_only_recorded_files(self):
        from nyxniri.modules.fisher import _ownership_path, fisher_uninstall

        owned = self.fish_dir / "conf.d" / "autopair.fish"
        unrelated = self.fish_dir / "conf.d" / "user-plugin.fish"
        owned.write_text("managed", encoding="utf-8")
        unrelated.write_text("user plugin", encoding="utf-8")
        _ownership_path().write_text(
            json.dumps({"files": ["conf.d/autopair.fish"], "complete": True, "fisher_preexisting": False}),
            encoding="utf-8",
        )

        with patch("nyxniri.modules.fisher.shutil.which", return_value=None):
            self.assertTrue(fisher_uninstall())

        self.assertFalse(owned.exists())
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "user plugin")
        self.assertTrue((self.fish_dir / "conf.d").is_dir())

    def test_install_rejects_mutable_lock_before_running_fish(self):
        from nyxniri.modules.fisher import fisher_install

        self._write_lockfile("jorgebucaran/fisher@main\n")
        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback") as fetch, \
             patch("nyxniri.modules.fisher.subprocess.run") as run, \
             patch("builtins.print"):
            self.assertFalse(fisher_install())

        fetch.assert_not_called()
        run.assert_not_called()

    def test_install_passes_only_pinned_sources_and_records_new_files(self):
        from nyxniri.modules.fisher import (
            FISHER_BOOTSTRAP_COMMIT,
            FISHER_BOOTSTRAP_SHA256,
            FISHER_PLUGINS,
            _ownership_path,
            fisher_install,
        )

        self._write_lockfile()
        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            (self.fish_dir / "functions" / "fisher.fish").write_text("managed", encoding="utf-8")
            return MagicMock(returncode=0)

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback", return_value=True) as fetch, \
             patch("nyxniri.modules.fisher.subprocess.run", side_effect=fake_run), \
             patch("builtins.print"):
            self.assertTrue(fisher_install())

        bootstrap = fetch.call_args.args[3]
        fetch.assert_called_once_with(
            "jorgebucaran/fisher",
            FISHER_BOOTSTRAP_COMMIT,
            "functions/fisher.fish",
            bootstrap,
            FISHER_BOOTSTRAP_SHA256,
        )
        self.assertEqual(
            calls,
            [["fish", "-c", "set --global fisher_path $argv[2]; source -- $argv[1]; fisher install $argv[3..-1]",
              "--", str(bootstrap), str(self.fish_dir), *FISHER_PLUGINS]],
        )
        state = json.loads(_ownership_path().read_text(encoding="utf-8"))
        self.assertTrue(state["complete"])
        self.assertEqual(state["files"], ["functions/fisher.fish"])
        self.assertFalse(state["fisher_preexisting"])
        self.assertEqual(state["plugins"], list(FISHER_PLUGINS))

    def test_partial_install_is_owned_and_retryable(self):
        from nyxniri.modules.fisher import _ownership_path, fisher_install

        self._write_lockfile()
        autopair_file = self.fish_dir / "conf.d" / "autopair.fish"

        def failed_run(*args, **kwargs):
            autopair_file.write_text("managed", encoding="utf-8")
            return MagicMock(returncode=1)

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback", return_value=True), \
             patch("nyxniri.modules.fisher.subprocess.run", side_effect=failed_run), \
             patch("builtins.print"):
            self.assertFalse(fisher_install())

        state = json.loads(_ownership_path().read_text(encoding="utf-8"))
        self.assertFalse(state["complete"])
        self.assertEqual(state["files"], ["conf.d/autopair.fish"])

        fzf_file = self.fish_dir / "conf.d" / "fzf.fish"

        def completed_run(*args, **kwargs):
            fzf_file.write_text("managed", encoding="utf-8")
            return MagicMock(returncode=0)

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback", return_value=True), \
             patch("nyxniri.modules.fisher.subprocess.run", side_effect=completed_run), \
             patch("builtins.print"):
            self.assertTrue(fisher_install())

        state = json.loads(_ownership_path().read_text(encoding="utf-8"))
        self.assertTrue(state["complete"])
        self.assertEqual(state["files"], ["conf.d/autopair.fish", "conf.d/fzf.fish"])

    def test_timeout_records_only_files_created_before_timeout(self):
        from nyxniri.modules.fisher import _ownership_path, fisher_install

        self._write_lockfile()
        autopair_file = self.fish_dir / "conf.d" / "autopair.fish"

        def timeout_run(*args, **kwargs):
            autopair_file.write_text("managed", encoding="utf-8")
            raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback", return_value=True), \
             patch("nyxniri.modules.fisher.subprocess.run", side_effect=timeout_run), \
             patch("builtins.print"):
            self.assertFalse(fisher_install())

        state = json.loads(_ownership_path().read_text(encoding="utf-8"))
        self.assertFalse(state["complete"])
        self.assertEqual(state["files"], ["conf.d/autopair.fish"])

    def test_preexisting_fisher_skips_install_without_ownership_state(self):
        from nyxniri.modules.fisher import _ownership_path, fisher_install

        fisher_file = self.fish_dir / "functions" / "fisher.fish"
        autopair_file = self.fish_dir / "conf.d" / "autopair.fish"
        fisher_file.write_text("user fisher", encoding="utf-8")
        autopair_file.write_text("user autopair", encoding="utf-8")
        self._write_lockfile()

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback") as fetch, \
             patch("nyxniri.modules.fisher.subprocess.run") as run:
            self.assertFalse(fisher_install())

        fetch.assert_not_called()
        run.assert_not_called()
        self.assertFalse(_ownership_path().exists())
        self.assertEqual(fisher_file.read_text(encoding="utf-8"), "user fisher")
        self.assertEqual(autopair_file.read_text(encoding="utf-8"), "user autopair")

    def test_legacy_preexisting_ownership_state_skips_install(self):
        from nyxniri.modules.fisher import _ownership_path, fisher_install

        fisher_file = self.fish_dir / "functions" / "fisher.fish"
        autopair_file = self.fish_dir / "conf.d" / "autopair.fish"
        fisher_file.write_bytes(b"user fisher\x00")
        autopair_file.write_bytes(b"user autopair\x00")
        _ownership_path().write_text(
            json.dumps({
                "files": ["conf.d/autopair.fish"],
                "complete": False,
                "fisher_preexisting": True,
            }),
            encoding="utf-8",
        )
        self._write_lockfile()

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback") as fetch, \
             patch("nyxniri.modules.fisher.subprocess.run") as run:
            self.assertFalse(fisher_install())

        fetch.assert_not_called()
        run.assert_not_called()
        self.assertEqual(fisher_file.read_bytes(), b"user fisher\x00")
        self.assertEqual(autopair_file.read_bytes(), b"user autopair\x00")

    def test_complete_current_install_is_idempotent(self):
        from nyxniri.modules.fisher import FISHER_PLUGINS, _ownership_path, fisher_install

        self._write_lockfile()
        (self.fish_dir / "conf.d" / "autopair.fish").write_text("managed", encoding="utf-8")
        _ownership_path().write_text(
            json.dumps({
                "files": ["conf.d/autopair.fish"],
                "complete": True,
                "fisher_preexisting": False,
                "plugins": list(FISHER_PLUGINS),
            }),
            encoding="utf-8",
        )
        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback") as fetch, \
             patch("nyxniri.modules.fisher.subprocess.run") as run:
            self.assertTrue(fisher_install())

        fetch.assert_not_called()
        run.assert_not_called()

    def test_old_lock_fingerprint_runs_current_pinned_command(self):
        from nyxniri.modules.fisher import FISHER_PLUGINS, _ownership_path, fisher_install

        self._write_lockfile()
        (self.fish_dir / "conf.d" / "autopair.fish").write_text("managed", encoding="utf-8")
        _ownership_path().write_text(
            json.dumps({
                "files": ["conf.d/autopair.fish"],
                "complete": True,
                "fisher_preexisting": False,
                "plugins": ["old-lock"],
            }),
            encoding="utf-8",
        )
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return MagicMock(returncode=0)

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback", return_value=True), \
             patch("nyxniri.modules.fisher.subprocess.run", side_effect=fake_run), \
             patch("builtins.print"):
            self.assertTrue(fisher_install())

        self.assertEqual(calls[0][6:], list(FISHER_PLUGINS))
        self.assertEqual(json.loads(_ownership_path().read_text(encoding="utf-8"))["plugins"], list(FISHER_PLUGINS))

    def test_missing_owned_file_runs_repair(self):
        from nyxniri.modules.fisher import FISHER_PLUGINS, _ownership_path, fisher_install

        self._write_lockfile()
        missing = self.fish_dir / "conf.d" / "autopair.fish"
        _ownership_path().write_text(
            json.dumps({
                "files": ["conf.d/autopair.fish"],
                "complete": True,
                "fisher_preexisting": False,
                "plugins": list(FISHER_PLUGINS),
            }),
            encoding="utf-8",
        )
        def repaired_run(*args, **kwargs):
            missing.write_text("managed", encoding="utf-8")
            return MagicMock(returncode=0)

        run = MagicMock(side_effect=repaired_run)

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback", return_value=True), \
             patch("nyxniri.modules.fisher.subprocess.run", run), \
             patch("builtins.print"):
            self.assertTrue(fisher_install())

        run.assert_called_once()
        self.assertTrue(missing.is_file())

    def test_failed_repair_stays_incomplete_after_creating_missing_file(self):
        from nyxniri.modules.fisher import FISHER_PLUGINS, _ownership_path, fisher_install

        self._write_lockfile()
        missing = self.fish_dir / "conf.d" / "autopair.fish"
        _ownership_path().write_text(
            json.dumps({
                "files": ["conf.d/autopair.fish"],
                "complete": True,
                "fisher_preexisting": False,
                "plugins": list(FISHER_PLUGINS),
            }),
            encoding="utf-8",
        )

        def failed_run(*args, **kwargs):
            missing.write_text("managed", encoding="utf-8")
            return MagicMock(returncode=1)

        fetch = MagicMock(return_value=True)
        run = MagicMock(side_effect=failed_run)
        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.fetch_raw_with_fallback", fetch), \
             patch("nyxniri.modules.fisher.subprocess.run", run), \
             patch("builtins.print"):
            self.assertFalse(fisher_install())
            self.assertFalse(fisher_install())

        self.assertFalse(json.loads(_ownership_path().read_text(encoding="utf-8"))["complete"])
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(run.call_count, 2)

    def test_bootstrap_path_is_an_argv_value_not_fish_code(self):
        from nyxniri.modules.fisher import FISHER_PLUGINS, fisher_install

        self._write_lockfile()
        special_tmp = self.env.home / "tmp dir; injected"
        special_tmp.mkdir()
        calls = []

        def failed_run(command, **kwargs):
            calls.append(command)
            return MagicMock(returncode=1)

        old_tempdir = tempfile.tempdir
        tempfile.tempdir = None
        try:
            with patch.dict(os.environ, {"TMPDIR": str(special_tmp)}), \
                 patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
                 patch("nyxniri.modules.fisher.fetch_raw_with_fallback", return_value=True), \
                 patch("nyxniri.modules.fisher.subprocess.run", side_effect=failed_run), \
                 patch("builtins.print"):
                self.assertFalse(fisher_install())
        finally:
            tempfile.tempdir = old_tempdir

        self.assertEqual(
            calls,
            [["fish", "-c", "set --global fisher_path $argv[2]; source -- $argv[1]; fisher install $argv[3..-1]",
              "--", calls[0][4], str(self.fish_dir), *FISHER_PLUGINS]],
        )
        self.assertTrue(str(calls[0][4]).startswith(str(special_tmp)))


class TestQuickphraseRestore(unittest.TestCase):
    """Gap #5: fcitx_uninstall restores prior quickphrase.conf hotkeys."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.qp = self.env.config_dir / "fcitx5" / "conf" / "quickphrase.conf"
        self.qp.parent.mkdir(parents=True)
        # Prior user setting (before NyxNiri touched it).
        self.qp.write_text("[Hotkey]\nTriggerKey=Super+space\n", encoding="utf-8")

    def tearDown(self):
        self._ctx.__exit__()

    def test_uninstall_restores_prior_quickphrase(self):
        from nyxniri.modules.fcitx import fcitx_configure_quickphrase, fcitx_uninstall

        # NyxNiri install overrides the hotkey (and backs up the prior state).
        fcitx_configure_quickphrase()
        self.assertIn("Super+semicolon", self.qp.read_text())

        with patch("nyxniri.modules.fcitx.fcitx_restart"):
            fcitx_uninstall()

        # Prior hotkey restored, .prev state file consumed.
        content = self.qp.read_text()
        self.assertIn("Super+space", content)
        self.assertNotIn("Super+semicolon", content)
        self.assertFalse((self.env.state_dir / "fcitx-nyxmellow-quickphrase.prev").exists())

    def test_uninstall_deletes_quickphrase_if_never_existed(self):
        from nyxniri.modules.fcitx import fcitx_configure_quickphrase, fcitx_uninstall

        # No prior quickphrase.conf → install creates it, uninstall deletes it.
        self.qp.unlink()
        fcitx_configure_quickphrase()
        self.assertTrue(self.qp.exists())
        with patch("nyxniri.modules.fcitx.fcitx_restart"):
            fcitx_uninstall()
        self.assertFalse(self.qp.exists(), "quickphrase.conf must be deleted if it never existed")


class TestGreeterStateDirRemoval(unittest.TestCase):
    """Gap #2: greeter_uninstall removes /var/lib/noctalia-greeter."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_var_lib_state_dir_removed(self):
        from nyxniri.modules.greeter import greeter_uninstall

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        dm_state = self._ctx.env.home / "display-manager"
        calls = []
        def fake_run(command, **kwargs):
            calls.append(command)
            result = MagicMock()
            result.returncode = 1 if command == ["systemctl", "is-enabled", "greetd"] else 0
            result.stdout = ""
            return result

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.GREETER_DM_STATE", dm_state), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/systemctl"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run):
            greeter_uninstall()

        # A `sudo rm -rf <state_dir>` command was issued.
        self.assertTrue(
            any("rm" in c and "-rf" in c and str(state_dir) in " ".join(c) for c in calls),
            f"Expected sudo rm -rf {state_dir}, got: {calls}",
        )


class TestFisherInstallDetect(unittest.TestCase):
    """Fisher needs both the host and NyxNiri's ownership record."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_installed_requires_ownership_record(self):
        from nyxniri.modules.fisher import _ownership_path, fisher_installed
        fish_dir = self.env.config_dir / "fish" / "functions"
        fish_dir.mkdir(parents=True)
        (fish_dir / "fisher.fish").write_text("# fisher")
        self.assertFalse(fisher_installed())
        _ownership_path().write_text(json.dumps({"files": ["functions/fisher.fish"], "fisher_preexisting": False}), encoding="utf-8")
        self.assertTrue(fisher_installed())

    def test_install_noop_when_fish_absent(self):
        from nyxniri.modules.fisher import fisher_install
        with patch("nyxniri.modules.fisher.shutil.which", return_value=None), patch("builtins.print"):
            self.assertFalse(fisher_install())


if __name__ == "__main__":
    unittest.main()

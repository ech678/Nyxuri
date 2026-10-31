"""Contract tests for the checkbox uninstall (KM3 unit-model edition).

Covers: only ledger-enabled hook units are offered and switched off; execution
order (unit off before state_dir deletion); archive glob cleanup; the fish
unit's pinned Fisher hooks (lockfile guard, pin argv, unowned-fisher refusal,
legacy ownership record cleanup).
"""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv

REPO = Path(__file__).resolve().parents[2]


def _load_hook(unit: str, name: str):
    """Import a unit hook script as a module (scripts guard on __main__)."""
    from importlib.machinery import SourceFileLoader

    path = REPO / "plugins" / unit / "hooks" / name
    name = f"hook_{unit}_{name}"
    spec = importlib.util.spec_from_file_location(name, path, loader=SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestUninstallUnitVisibility(unittest.TestCase):
    """KM3: only ledger-enabled hook units are offered and switched off."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def _stage_enabled(self, uid: str):
        from nyxuri.kernel import ledger
        dest = self.env.config_dir / uid
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "marker.conf").write_text("x", encoding="utf-8")
        ledger.set_unit(uid, state="enabled", files={}, vault=None)

    def test_only_enabled_units_are_switched_off(self):
        from nyxuri.state.uninstall import uninstall_nyxuri
        self._stage_enabled("fish")

        off = MagicMock(return_value=[])
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxuri.state.uninstall.copy_path"), patch("nyxuri.state.uninstall.remove_path"), \
             patch("nyxuri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"), \
             patch("nyxuri.kernel.transaction.unit_off", side_effect=off):
            result = uninstall_nyxuri("")

        self.assertTrue(result)
        # Only the enabled hook unit goes through the transaction; greeter is
        # not enabled → never offered, never switched.
        self.assertEqual([c.args[0] for c in off.call_args_list], ["fish"])

    def test_unit_off_failure_propagates(self):
        from nyxuri.state.uninstall import uninstall_nyxuri
        self._stage_enabled("greeter")

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxuri.state.uninstall.copy_path"), patch("nyxuri.state.uninstall.remove_path"), \
             patch("nyxuri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"), \
             patch("nyxuri.kernel.transaction.unit_off",
                   return_value=[MagicMock(ok=False, unit="greeter", detail="boom")]):
            result = uninstall_nyxuri("")

        self.assertFalse(result)


class TestUninstallExecutionOrder(unittest.TestCase):
    """Unit offs run BEFORE nyx_dir/state_dir deletion."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("x")

    def tearDown(self):
        self._ctx.__exit__()

    def test_unit_off_runs_before_state_dir_deleted(self):
        from nyxuri.state.uninstall import uninstall_nyxuri
        from nyxuri.kernel import ledger

        dest = self.env.config_dir / "fish"
        dest.mkdir(parents=True, exist_ok=True)
        ledger.set_unit("fish", state="enabled", files={}, vault=None)

        state_at_off = {}

        def off_side(uid, *, cascade=False):
            state_at_off["exists"] = self.env.state_dir.exists()
            return []

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxuri.state.uninstall.copy_path"), \
             patch("nyxuri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"), \
             patch("nyxuri.kernel.transaction.unit_off", side_effect=off_side):
            uninstall_nyxuri("")

        self.assertTrue(state_at_off.get("exists"), "state_dir must outlive unit offs")


class TestUninstallArchiveGlob(unittest.TestCase):
    """Gap #1: NyxNiri_archive_* dirs are cleaned when 'archives' selected."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_old_archives_cleaned_new_archive_preserved(self):
        from nyxuri.state.uninstall import uninstall_nyxuri
        from nyxuri.core import PROJECT_NAME

        old = self.env.config_dir / f"{PROJECT_NAME}_archive_20250101_000000"
        old.mkdir(parents=True)
        (old / "niri").mkdir()
        (old / "niri" / "config.kdl").write_text("old")
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("current")

        with patch("sys.stdin.isatty", return_value=True), patch("builtins.print"), \
             patch("nyxuri.state.uninstall.CheckboxList") as checklist:
            checklist.return_value.run.return_value = ["configs", "archives"]
            uninstall_nyxuri("")

        # Old archive cleaned (gap #1), but the freshly-created config archive survives.
        self.assertFalse(old.exists(), "Pre-existing archive must be cleaned")
        new_archives = list(self.env.config_dir.glob(f"{PROJECT_NAME}_archive_*"))
        self.assertEqual(len(new_archives), 1, "Only the freshly-created archive remains")
        self.assertTrue((new_archives[0] / "niri" / "config.kdl").exists())


class TestUninstallHookPreservation(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_standard_uninstall_keeps_hooks_but_purge_removes_them(self):
        from nyxuri.state.uninstall import uninstall_nyxuri

        hook = self.env.nyx_dir / "hooks" / "keep.sh"
        hook.parent.mkdir(parents=True)
        hook.write_text("#!/bin/sh\n")

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            self.assertTrue(uninstall_nyxuri(""))
        self.assertTrue(hook.exists())

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            self.assertTrue(uninstall_nyxuri("all"))
        self.assertFalse(hook.exists())


class TestFisherHookLockfile(unittest.TestCase):
    """The fish unit's install hook refuses anything but the reviewed lockfile."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.fish_dir = self.env.config_dir / "fish"
        (self.fish_dir / "functions").mkdir(parents=True)
        (self.fish_dir / "conf.d").mkdir(parents=True)
        self.hook = _load_hook("fish", "install-fisher")

    def tearDown(self):
        self._ctx.__exit__()

    def _write_lockfile(self, content):
        (self.fish_dir / "fish_plugins").write_text(content, encoding="utf-8")

    def test_install_rejects_mutable_lock_before_running_fish(self):
        self._write_lockfile("jorgebucaran/fisher@main\n")
        with patch.object(self.hook.shutil, "which", return_value="/usr/bin/fish"), \
             patch.object(self.hook, "fetch_raw_with_fallback") as fetch, \
             patch.object(self.hook.subprocess, "run") as run, \
             patch("builtins.print"):
            self.assertNotEqual(self.hook.main(), 0)

        fetch.assert_not_called()
        run.assert_not_called()

    def test_install_noop_when_fish_absent(self):
        self._write_lockfile("\n".join(self.hook.PLUGINS) + "\n")
        with patch.object(self.hook.shutil, "which", return_value=None), patch("builtins.print"):
            self.assertNotEqual(self.hook.main(), 0)

    def test_install_passes_only_pinned_sources(self):
        self._write_lockfile("\n".join(self.hook.PLUGINS) + "\n")
        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            (self.fish_dir / "functions" / "fisher.fish").write_text("managed", encoding="utf-8")
            return MagicMock(returncode=0)

        with patch.object(self.hook.shutil, "which", return_value="/usr/bin/fish"), \
             patch.object(self.hook, "fetch_raw_with_fallback", return_value=True) as fetch, \
             patch.object(self.hook.subprocess, "run", side_effect=fake_run), \
             patch("builtins.print"):
            self.assertEqual(self.hook.main(), 0)

        bootstrap = fetch.call_args.args[3]
        fetch.assert_called_once_with(
            "jorgebucaran/fisher",
            self.hook.BOOTSTRAP_COMMIT,
            "functions/fisher.fish",
            bootstrap,
            self.hook.BOOTSTRAP_SHA256,
        )
        self.assertEqual(calls[0][6:], list(self.hook.PLUGINS))

    def test_install_refuses_unowned_fisher(self):
        """A fisher.fish that is neither pin-content nor legacy-recorded is hands-off."""
        self._write_lockfile("\n".join(self.hook.PLUGINS) + "\n")
        fisher_file = self.fish_dir / "functions" / "fisher.fish"
        fisher_file.write_text("user fisher", encoding="utf-8")

        with patch.object(self.hook.shutil, "which", return_value="/usr/bin/fish"), \
             patch.object(self.hook, "fetch_raw_with_fallback") as fetch, \
             patch.object(self.hook.subprocess, "run") as run, \
             patch("builtins.print"):
            self.assertNotEqual(self.hook.main(), 0)

        fetch.assert_not_called()
        run.assert_not_called()
        self.assertEqual(fisher_file.read_text(encoding="utf-8"), "user fisher")

    def test_legacy_ownership_record_still_proves_ownership(self):
        """Module-era machines carry fisher.json; it authorizes a refresh."""
        self._write_lockfile("\n".join(self.hook.PLUGINS) + "\n")
        (self.fish_dir / "functions" / "fisher.fish").write_text("old install", encoding="utf-8")
        state_dir = self.env.home / ".local" / "state" / "nyxuri"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "fisher.json").write_text(
            json.dumps({"files": ["functions/fisher.fish"], "complete": True}), encoding="utf-8"
        )

        with patch.object(self.hook.shutil, "which", return_value="/usr/bin/fish"), \
             patch.object(self.hook, "fetch_raw_with_fallback", return_value=True), \
             patch.object(self.hook.subprocess, "run", return_value=MagicMock(returncode=0)), \
             patch("builtins.print"):
            self.assertEqual(self.hook.main(), 0)


class TestFisherHookLegacyCleanup(unittest.TestCase):
    """The fish unit's off-hook retires the module-era ownership record only."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.fish_dir = self.env.config_dir / "fish"
        (self.fish_dir / "conf.d").mkdir(parents=True)
        self.hook = _load_hook("fish", "remove-fisher")

    def tearDown(self):
        self._ctx.__exit__()

    def test_removes_only_recorded_files_and_the_record(self):
        owned = self.fish_dir / "conf.d" / "autopair.fish"
        unrelated = self.fish_dir / "conf.d" / "user-plugin.fish"
        owned.write_text("managed", encoding="utf-8")
        unrelated.write_text("user plugin", encoding="utf-8")
        record = self.env.home / ".local" / "state" / "nyxuri" / "fisher.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(
            json.dumps({"files": ["conf.d/autopair.fish"], "complete": True}), encoding="utf-8"
        )

        with patch("builtins.print"):
            self.assertEqual(self.hook.main(), 0)

        self.assertFalse(owned.exists())
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "user plugin")
        self.assertFalse(record.exists())

    def test_no_record_is_a_silent_noop(self):
        with patch("builtins.print"):
            self.assertEqual(self.hook.main(), 0)
        self.assertTrue(self.fish_dir.is_dir())


class TestGreeterStateDirRemoval(unittest.TestCase):
    """The greeter off-hook removes /var/lib/noctalia-greeter via sudo rm -rf."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.hook = _load_hook("greeter", "deactivate")

    def tearDown(self):
        self._ctx.__exit__()

    def test_var_lib_state_dir_removed(self):
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

        with patch.object(self.hook, "GREETER_ETC_CFG", config), \
             patch.object(self.hook, "GREETER_POLKIT_RULE", polkit), \
             patch.object(self.hook, "GREETER_STATE_DIR", state_dir), \
             patch.object(self.hook, "GREETER_DM_STATE", dm_state), \
             patch.object(self.hook.shutil, "which", return_value="/usr/bin/systemctl"), \
             patch.object(self.hook.subprocess, "run", side_effect=fake_run), \
             patch("builtins.print"):
            self.assertEqual(self.hook.main(), 0)

        self.assertTrue(
            any("rm" in c and "-rf" in c and str(state_dir) in " ".join(c) for c in calls),
            f"Expected sudo rm -rf {state_dir}, got: {calls}",
        )


if __name__ == "__main__":
    unittest.main()

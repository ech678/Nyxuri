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
from nyxuri.core import remove_path

REPO = Path(__file__).resolve().parents[2]


def _load_hook(unit: str, name: str):
    """Import a unit hook script as a module (scripts guard on __main__)."""
    from importlib.machinery import SourceFileLoader

    path = REPO / "units" / unit / "hooks" / name
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
             patch("nyxuri.state.uninstall.copy_path"), patch("nyxuri.state.uninstall.remove_path", wraps=remove_path), \
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
             patch("nyxuri.state.uninstall.copy_path"), patch("nyxuri.state.uninstall.remove_path", wraps=remove_path), \
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

        # 旧归档按显式选择清理，本轮保险集中在状态域；无账本的配置保留原位。
        self.assertFalse(old.exists(), "Pre-existing archive must be cleaned")
        new_archives = list(self.env.config_dir.glob(f"{PROJECT_NAME}_archive_*"))
        self.assertEqual(len(new_archives), 0)
        recovery = list((self.env.state_dir / "uninstall-backups").iterdir())
        self.assertEqual(len(recovery), 1)
        self.assertTrue((recovery[0] / "niri" / "config.kdl").exists())
        self.assertEqual((self.env.config_dir / "niri" / "config.kdl").read_text(), "current")


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


class TestUninstallManagedLifecycle(unittest.TestCase):
    """卸载必须先备份，再按账本撤回；个人文件与未确认 marker 保留。"""

    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.env = self.ctx.env

    def tearDown(self):
        self.ctx.__exit__()

    def stage(self):
        from nyxuri.kernel import ledger
        import hashlib
        dest = self.env.config_dir / "kitty"
        dest.mkdir()
        (dest / "kitty.conf").write_text("baseline")
        (dest / "personal.conf").write_text("personal")
        ledger.set_unit("kitty", state="enabled", files={"kitty.conf": hashlib.sha256(b"baseline").hexdigest()})
        ledger.set_deployment("kitty", target=str(dest), shape="directory", preserve=[], pending=None)
        return dest

    def test_managed_uninstall_backs_up_before_off_and_preserves_personal_file(self):
        from nyxuri.state.uninstall import uninstall_nyxuri
        from nyxuri.kernel import ledger
        dest = self.stage()
        (dest / "kitty.conf").write_text("edited")
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            self.assertTrue(uninstall_nyxuri())
        self.assertFalse((dest / "kitty.conf").exists())
        self.assertEqual((dest / "personal.conf").read_text(), "personal")
        self.assertEqual(ledger.get_unit("kitty")["state"], "disabled")
        safety = next((self.env.state_dir / "uninstall-backups").iterdir())
        self.assertEqual((safety / "units/0/kitty.conf").read_text(), "edited")

    def test_backup_failure_prevents_off_and_state_deletion(self):
        from nyxuri.state.uninstall import uninstall_nyxuri
        from nyxuri.kernel import ledger
        dest = self.stage()
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxuri.state.uninstall.backup_configs", return_value=None), \
             patch("nyxuri.kernel.transaction.unit_off") as off:
            self.assertFalse(uninstall_nyxuri("all"))
        off.assert_not_called()
        self.assertTrue((dest / "kitty.conf").exists())
        self.assertEqual(ledger.get_unit("kitty")["state"], "enabled")

    def test_old_wallpaper_marker_does_not_authorize_deletion(self):
        from nyxuri.state.uninstall import uninstall_nyxuri
        wallpapers = self.env.home / "Pictures/Wallpapers"
        wallpapers.mkdir()
        (wallpapers / "personal.jpg").write_text("personal")
        (wallpapers / ".nyxuri-managed.json").write_text('["personal.jpg"]')
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            self.assertTrue(uninstall_nyxuri("all"))
        self.assertEqual((wallpapers / "personal.jpg").read_text(), "personal")
        recovery = list((self.env.state_dir / "uninstall-backups").iterdir())
        self.assertTrue(recovery)


class TestFisherHookLockfile(unittest.TestCase):
    """固定插件隔离生成，冲突/强制/停用都不吞个人插件与清单。"""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.fish_dir = self.env.config_dir / "fish"
        (self.fish_dir / "functions").mkdir(parents=True)
        (self.fish_dir / "conf.d").mkdir(parents=True)
        self.hook = _load_hook("fish", "install-fisher")
        self.remove = _load_hook("fish", "remove-fisher")

    def tearDown(self):
        self._ctx.__exit__()

    def install(self, *, force=False):
        self.calls = []

        def fake_run(command, **kwargs):
            self.calls.append((command, kwargs))
            payload = Path(command[6])
            (payload / "functions").mkdir(parents=True)
            (payload / "conf.d").mkdir()
            (payload / "functions/fisher.fish").write_bytes(b"pinned fisher")
            (payload / "conf.d/autopair.fish").write_bytes(b"pinned autopair")
            (payload / "fish_plugins").write_text("temporary fixed list\n")
            return MagicMock(returncode=0)

        with patch.object(self.hook.shutil, "which", return_value="/usr/bin/fish"), \
             patch.object(self.hook, "fetch_raw_with_fallback", return_value=True) as fetch, \
             patch.object(self.hook.subprocess, "run", side_effect=fake_run), \
             patch.dict(os.environ, {"NYXURI_FORCE": "1" if force else "0"}), \
             patch("builtins.print"):
            result = self.hook.main()
        return result, fetch

    def test_personal_plugin_list_is_not_an_install_input(self):
        plugins = self.fish_dir / "fish_plugins"
        plugins.write_text("personal/plugin@main\n")
        extra = self.fish_dir / "conf.d/personal.fish"
        extra.write_bytes(b"personal plugin")
        self.assertEqual(self.install()[0], 0)
        self.assertEqual(plugins.read_text(), "personal/plugin@main\n")
        self.assertEqual(extra.read_bytes(), b"personal plugin")

    def test_install_noop_when_fish_absent(self):
        with patch.object(self.hook.shutil, "which", return_value=None), patch("builtins.print"):
            self.assertNotEqual(self.hook.main(), 0)

    def test_install_passes_only_pinned_sources_in_isolated_home(self):
        result, fetch = self.install()
        self.assertEqual(result, 0)
        command, kwargs = self.calls[0]
        self.assertEqual(command[:3], ["fish", "--no-config", "-c"])
        self.assertEqual(command[7:], list(self.hook.PLUGINS))
        self.assertEqual(command[4], "--")
        self.assertNotEqual(kwargs["env"]["HOME"], str(self.env.home))
        self.assertTrue(Path(command[6]).is_relative_to(Path(kwargs["env"]["HOME"])))
        fetch.assert_called_once_with("jorgebucaran/fisher", self.hook.BOOTSTRAP_COMMIT,
            "functions/fisher.fish", Path(command[5]), self.hook.BOOTSTRAP_SHA256)

    def test_unknown_fisher_conflict_preserves_entire_set(self):
        fisher = self.fish_dir / "functions/fisher.fish"
        fisher.write_bytes(b"personal fisher")
        self.assertNotEqual(self.install()[0], 0)
        self.assertEqual(fisher.read_bytes(), b"personal fisher")
        self.assertFalse((self.fish_dir / "conf.d/autopair.fish").exists())

    def test_legacy_file_list_does_not_authorize_overwrite(self):
        fisher = self.fish_dir / "functions/fisher.fish"
        fisher.write_bytes(b"legacy or personal")
        record = self.env.state_dir / "fisher.json"
        record.write_text(json.dumps({"files": ["functions/fisher.fish"], "complete": True}))
        self.assertNotEqual(self.install()[0], 0)
        self.assertEqual(fisher.read_bytes(), b"legacy or personal")

    def test_force_overwrites_declared_files_and_restores_original_on_remove(self):
        fisher = self.fish_dir / "functions/fisher.fish"
        fisher.write_bytes(b"personal fisher")
        extra = self.fish_dir / "conf.d/personal.fish"
        extra.write_bytes(b"personal plugin")
        self.assertEqual(self.install(force=True)[0], 0)
        self.assertEqual(fisher.read_bytes(), b"pinned fisher")
        self.assertEqual(extra.read_bytes(), b"personal plugin")
        self.assertEqual(self.remove.main(), 0)
        self.assertEqual(fisher.read_bytes(), b"personal fisher")
        self.assertEqual(extra.read_bytes(), b"personal plugin")
        self.assertFalse((self.fish_dir / "conf.d/autopair.fish").exists())

    def test_fixed_set_refresh_retires_old_output_without_touching_extra_plugin(self):
        from nyxuri.desktop.owned_outputs import write_output_set
        extra = self.fish_dir / "conf.d/personal.fish"
        extra.write_bytes(b"personal plugin")
        self.assertEqual(self.install()[0], 0)
        conflicts = write_output_set("fish-plugins", "fish", {
            self.fish_dir / "functions/fisher.fish": b"new pinned fisher",
            self.fish_dir / "conf.d/new-fixed.fish": b"new fixed plugin",
        })
        self.assertEqual(conflicts, [])
        self.assertFalse((self.fish_dir / "conf.d/autopair.fish").exists())
        self.assertEqual(extra.read_bytes(), b"personal plugin")
        self.assertEqual((self.fish_dir / "conf.d/new-fixed.fish").read_bytes(), b"new fixed plugin")

    def test_later_personal_change_blocks_refresh_and_survives_remove(self):
        self.assertEqual(self.install()[0], 0)
        fisher = self.fish_dir / "functions/fisher.fish"
        fisher.write_bytes(b"later personal edit")
        self.assertNotEqual(self.install()[0], 0)
        self.assertEqual(self.remove.main(), 0)
        self.assertEqual(fisher.read_bytes(), b"later personal edit")


class TestFisherHookLegacyCleanup(unittest.TestCase):
    """旧清单缺少原值和hash，不能授权删除现存插件。"""

    def test_legacy_record_and_plugin_survive(self):
        with TempEnv() as context:
            plugin = context.env.config_dir / "fish/conf.d/autopair.fish"
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"possibly personal")
            record = context.env.state_dir / "fisher.json"
            record.write_text(json.dumps({"files": ["conf.d/autopair.fish"]}))
            hook = _load_hook("fish", "remove-fisher")
            self.assertEqual(hook.main(), 0)
            self.assertEqual(plugin.read_bytes(), b"possibly personal")
            self.assertTrue(record.is_file())


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

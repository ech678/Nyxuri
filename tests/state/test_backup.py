"""Behavior contracts for backup/uninstall: non-interactive no-op, interactive flag, mode aliases.

Safety: all tests run inside TempEnv which isolates HOME to a temp directory.
No test may call real fcitx_uninstall, greeter_uninstall, or touch real ~/.config.
"""

import sys
import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv
from nyxuri.core import remove_path


class TestUninstallNonInteractive(unittest.TestCase):
    """Non-interactive uninstall: no mode → standard scope + archive (§8.5)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("test")

    def tearDown(self):
        self._ctx.__exit__()

    def test_non_interactive_uninstall_uses_standard_scope_and_archives(self):
        """Non-interactive uninstall archives configs without removing user data."""
        from nyxuri.state.uninstall import uninstall_nyxuri
        from nyxuri.state.backup import get_all_backups

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            result = uninstall_nyxuri("")

        self.assertTrue(result, "Non-interactive uninstall uses standard scope")
        # 没有账本的同名目录属于来源不明配置；卸载只备份，不擅自接管删除。
        self.assertTrue(get_all_backups())
        self.assertEqual((self.env.config_dir / "niri" / "config.kdl").read_text(), "test")

    def test_non_interactive_uninstall_purge_still_works(self):
        """Explicit purge mode should still execute even non-interactively."""
        from nyxuri.state.uninstall import uninstall_nyxuri

        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.print"):
                with patch("nyxuri.state.uninstall.prompt_confirm", return_value=True):
                    with patch("nyxuri.state.uninstall.get_all_backups", return_value=[]):
                        with patch("nyxuri.state.uninstall.remove_path", wraps=remove_path):
                            with patch("nyxuri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"):
                                result = uninstall_nyxuri("purge")

        self.assertTrue(result)


class TestModeAliases(unittest.TestCase):
    """Legacy mode aliases (1/safe/--safe/2/--restore/3/--purge) are accepted."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_alias_safe_accepted(self):
        """Alias 'safe' is accepted and runs the standard path (non-TTY)."""
        from nyxuri.state.uninstall import uninstall_nyxuri

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxuri.state.uninstall.copy_path"), patch("nyxuri.state.uninstall.remove_path", wraps=remove_path):
            result = uninstall_nyxuri("safe")

        self.assertTrue(result)

    def test_alias_purge_maps_correctly(self):
        """Alias '3' should map to purge."""
        from nyxuri.state.uninstall import uninstall_nyxuri

        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.print"):
                with patch("nyxuri.state.uninstall.prompt_confirm", return_value=True):
                    with patch("nyxuri.state.uninstall.get_all_backups", return_value=[]):
                        with patch("nyxuri.state.uninstall.remove_path", wraps=remove_path):
                            with patch("nyxuri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"):
                                result = uninstall_nyxuri("3")
                                self.assertTrue(result)


class TestBackupInteractiveFlag(unittest.TestCase):
    """interactive=False should suppress printing."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_interactive_false_suppresses_output(self):
        """backup_configs with interactive=False should not print backing_up/done messages."""
        from nyxuri.state.backup import backup_configs

        with patch("builtins.print") as mock_print:
            with patch("nyxuri.deploy.deploy.discover_config_items", return_value=[]):
                backup_configs(note="test", interactive=False)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertNotIn("backing_up", printed.lower(),
                         "interactive=False should not print backing_up message")

    def test_interactive_true_prints_output(self):
        """backup_configs with interactive=True should print."""
        from nyxuri.state.backup import backup_configs

        with patch("builtins.print") as mock_print:
            with patch("nyxuri.deploy.deploy.discover_config_items", return_value=[]):
                backup_configs(note="test", interactive=True)

        mock_print.assert_called()


class TestSnapshotRotation(unittest.TestCase):
    """_prune_old_snapshots keeps MAX_SNAPSHOTS, deletes oldest beyond that."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.base_dir = self.env.nyx_dir / "backups"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_excess_snapshots_pruned_oldest_first(self):
        """Beyond MAX_SNAPSHOTS, oldest (by name) are removed."""
        from nyxuri.state.backup import _prune_old_snapshots, MAX_SNAPSHOTS

        for i in range(MAX_SNAPSHOTS + 3):
            d = self.base_dir / f"snapshot_20260101_000000_{i:06d}"
            d.mkdir()

        _prune_old_snapshots(self.base_dir)

        remaining = sorted(d.name for d in self.base_dir.iterdir() if d.is_dir())
        self.assertEqual(len(remaining), MAX_SNAPSHOTS,
                         "Should keep exactly MAX_SNAPSHOTS")
        # Oldest 3 (indices 0,1,2) pruned; newest 30 (indices 3..32) kept
        self.assertNotIn("snapshot_20260101_000000_000000", remaining)
        self.assertIn("snapshot_20260101_000000_000003", remaining)
        self.assertIn("snapshot_20260101_000000_000032", remaining)

    def test_at_or_below_limit_no_prune(self):
        """At or below MAX_SNAPSHOTS → nothing removed."""
        from nyxuri.state.backup import _prune_old_snapshots, MAX_SNAPSHOTS

        for i in range(MAX_SNAPSHOTS):
            d = self.base_dir / f"snapshot_20260101_000000_{i:06d}"
            d.mkdir()

        _prune_old_snapshots(self.base_dir)

        remaining = [d for d in self.base_dir.iterdir() if d.is_dir()]
        self.assertEqual(len(remaining), MAX_SNAPSHOTS)


class TestRollbackSafety(unittest.TestCase):
    """Rollback restores the selected snapshot without losing or overlaying it."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.base_dir = self.env.nyx_dir / "backups"
        self.base_dir.mkdir(parents=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_oldest_snapshot_survives_pre_rollback_rotation(self):
        """At the limit, rollback keeps and restores the chosen oldest snapshot."""
        from nyxuri.state.backup import MAX_SNAPSHOTS, rollback_configs

        oldest = None
        for index in range(MAX_SNAPSHOTS):
            snapshot = self.base_dir / f"snapshot_20260101_000000_{index:06d}"
            snapshot.mkdir()
            if index == 0:
                (snapshot / "niri").mkdir()
                (snapshot / "niri" / "config.kdl").write_text("historical")
                oldest = snapshot

        current = self.env.config_dir / "niri"
        current.mkdir()
        (current / "config.kdl").write_text("current")

        with patch("nyxuri.deploy.deploy.discover_config_items", return_value=["niri"]):
            self.assertTrue(rollback_configs(str(oldest)))

        self.assertTrue(oldest.is_dir())
        self.assertEqual((current / "config.kdl").read_text(), "historical")
        self.assertEqual(len(list(self.base_dir.iterdir())), MAX_SNAPSHOTS)

    def test_default_rollback_restores_snapshot_custom_bytes(self):
        """Rollback must not overlay snapshot custom files with current config."""
        from nyxuri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        (snapshot / "niri").mkdir(parents=True)
        (snapshot / "niri" / "__custom__.kdl").write_text("historical custom")
        (snapshot / "niri" / "__custom__").mkdir()
        (snapshot / "niri" / "__custom__" / "rule.kdl").write_text("historical rule")
        current = self.env.config_dir / "niri"
        current.mkdir()
        (current / "__custom__.kdl").write_text("current custom")
        (current / "__custom__").mkdir()
        (current / "__custom__" / "rule.kdl").write_text("current rule")

        with patch("nyxuri.deploy.deploy.discover_config_items", return_value=["niri"]):
            self.assertTrue(rollback_configs(str(snapshot)))

        self.assertEqual((current / "__custom__.kdl").read_text(), "historical custom")
        self.assertEqual((current / "__custom__" / "rule.kdl").read_text(), "historical rule")

    def test_rollback_fails_when_selected_source_disappears(self):
        """A selected snapshot removed during the safety backup is a hard failure."""
        from nyxuri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        (snapshot / "niri").mkdir(parents=True)
        (snapshot / "niri" / "config.kdl").write_text("historical")

        def remove_source(*_args, **_kwargs):
            shutil.rmtree(snapshot)
            return self.base_dir / "snapshot_20260102_000000"

        with patch("nyxuri.state.backup.backup_configs", side_effect=remove_source), \
             patch("nyxuri.deploy.deploy.discover_config_items", return_value=["niri"]), \
             patch("nyxuri.state.backup.msg", side_effect=lambda key, *_args: key), \
             patch("builtins.print") as mock_print:
            self.assertFalse(rollback_configs(str(snapshot)))

        self.assertIn("rollback_source_missing", str(mock_print.call_args_list))

    def test_rollback_fails_when_an_expected_item_disappears(self):
        """Rollback must not partly restore a snapshot whose item disappears."""
        from nyxuri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        for item, content in (("niri", "historical niri"), ("kitty", "historical kitty")):
            (snapshot / item).mkdir(parents=True)
            (snapshot / item / "config").write_text(content)
            (self.env.config_dir / item).mkdir()
            (self.env.config_dir / item / "config").write_text(f"current {item}")

        def remove_niri(*_args, **_kwargs):
            shutil.rmtree(snapshot / "niri")
            return self.base_dir / "snapshot_20260102_000000"

        with patch("nyxuri.state.backup.backup_configs", side_effect=remove_niri), \
             patch("nyxuri.deploy.deploy.discover_config_items", return_value=["niri", "kitty"]), \
             patch("builtins.print"):
            self.assertFalse(rollback_configs(str(snapshot)))

        self.assertEqual((self.env.config_dir / "kitty" / "config").read_text(), "current kitty")

    def test_rollback_keeps_earlier_items_when_a_later_item_disappears(self):
        """All expected items must survive the safety backup before any restore."""
        from nyxuri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        for item, content in (("niri", "historical niri"), ("kitty", "historical kitty")):
            (snapshot / item).mkdir(parents=True)
            (snapshot / item / "config").write_text(content)
            (self.env.config_dir / item).mkdir()
            (self.env.config_dir / item / "config").write_text(f"current {item}")

        def remove_kitty(*_args, **_kwargs):
            shutil.rmtree(snapshot / "kitty")
            return self.base_dir / "snapshot_20260102_000000"

        with patch("nyxuri.state.backup.backup_configs", side_effect=remove_kitty), \
             patch("nyxuri.deploy.deploy.discover_config_items", return_value=["niri", "kitty"]), \
             patch("builtins.print"):
            self.assertFalse(rollback_configs(str(snapshot)))

        self.assertEqual((self.env.config_dir / "niri" / "config").read_text(), "current niri")

    def test_rollback_fails_when_snapshot_has_no_restorable_items(self):
        """A snapshot that restores nothing must not report success."""
        from nyxuri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        snapshot.mkdir()

        with patch("nyxuri.deploy.deploy.discover_config_items", return_value=["niri"]), \
             patch("builtins.print"):
            self.assertFalse(rollback_configs(str(snapshot)))


class TestManagedSnapshotLifecycle(unittest.TestCase):
    """覆盖已确认的快照、个人修改、新增单元与回滚对账场景。"""

    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.env = self.ctx.env

    def tearDown(self):
        self.ctx.__exit__()

    def stage(self, uid, content):
        from nyxuri.kernel import ledger
        import hashlib
        dest = self.env.config_dir / uid
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "config").write_text(content)
        ledger.set_unit(uid, state="enabled", preset="default",
                        files={"config": hashlib.sha256(content.encode()).hexdigest()})
        ledger.set_deployment(uid, target=str(dest), shape="directory", preserve=[], pending=None)
        return dest

    def test_rollback_restores_unit_state_with_content_and_disables_new_unit(self):
        from nyxuri.state.backup import backup_configs, rollback_configs, get_all_backups
        from nyxuri.kernel import ledger, transaction
        dest = self.stage("kitty", "baseline")
        ledger.update_ledger(active_shell="noctalia", unrelated={"keep": 1},
                             presets={"kitty": "default"}, parts={"kitty:colors": "old", "other:slot": "old"})
        with patch("builtins.print"):
            snap = backup_configs(interactive=False)
        self.assertIsNotNone(snap)
        (dest / "config").write_text("personal edit")
        (dest / "foreign").write_text("new personal file")
        newer = self.stage("snapshot-new", "new payload")
        ledger.update_ledger(active_shell="nyxuri-shell", unrelated={"keep": 2},
                             parts={"kitty:colors": "new", "other:slot": "new"})
        with patch("builtins.print"):
            self.assertTrue(rollback_configs(str(snap)))
        self.assertEqual((dest / "config").read_text(), "baseline")
        self.assertEqual((dest / "foreign").read_text(), "new personal file")
        self.assertFalse((newer / "config").exists())
        self.assertEqual(ledger.get_unit("snapshot-new")["state"], "disabled")
        self.assertEqual(ledger.read_ledger()["unrelated"], {"keep": 2})
        self.assertEqual(ledger.active_shell(), "nyxuri-shell")
        self.assertEqual(ledger.read_ledger()["parts"], {"kitty:colors": "old", "other:slot": "new"})
        self.assertEqual(transaction.audit_units("kitty"), {"kitty": "Synced"})
        safety = next(p for p in get_all_backups() if p != snap)
        self.assertEqual((safety / "units" / "0" / "config").read_text(), "personal edit")

    def test_failed_safety_backup_blocks_rollback_before_content_changes(self):
        from nyxuri.state.backup import backup_configs, rollback_configs
        dest = self.stage("kitty", "baseline")
        with patch("builtins.print"):
            snap = backup_configs(interactive=False)
        (dest / "config").write_text("personal edit")
        with patch("builtins.print"), patch("nyxuri.state.backup.backup_configs", return_value=None):
            self.assertFalse(rollback_configs(str(snap)))
        self.assertEqual((dest / "config").read_text(), "personal edit")

    def test_snapshot_restores_protected_ownership_without_claiming_foreign_paths(self):
        """快照带回来源集合；同目录个人保留文件仍无撤回权限。"""
        from nyxuri.kernel import ledger, transaction
        from nyxuri.state.backup import backup_configs, rollback_configs
        dest = self.stage("app", "baseline")
        (dest / "owned__custom__.conf").write_text("personal owned")
        (dest / "foreign__custom__.conf").write_text("personal foreign")
        ledger.set_deployment("app", protected_paths=["owned__custom__.conf"])
        with patch("builtins.print"):
            snap = backup_configs(interactive=False)
            self.assertTrue(transaction.unit_off("app")[0].ok)
            self.assertTrue(rollback_configs(str(snap)))
        self.assertEqual(ledger.get_deployment("app")["protected_paths"], ["owned__custom__.conf"])
        self.assertTrue(transaction.unit_off("app")[0].ok)
        self.assertFalse((dest / "owned__custom__.conf").exists())
        self.assertEqual((dest / "foreign__custom__.conf").read_text(), "personal foreign")

    def test_snapshot_rejects_unsafe_protected_paths_before_withdrawal(self):
        """撤回现状之前验证来源字段，防止非法路径到写账本阶段才被拒绝。"""
        from nyxuri.kernel import ledger
        from nyxuri.state.backup import backup_configs, rollback_configs
        dest = self.stage("app", "baseline")
        with patch("builtins.print"):
            snap = backup_configs(interactive=False)
        metadata = json.loads((snap / "snapshot.json").read_text())
        metadata["deployments"]["app"]["protected_paths"] = ["../foreign"]
        (snap / "snapshot.json").write_text(json.dumps(metadata))
        with patch("builtins.print"), patch("sys.stderr"):
            self.assertFalse(rollback_configs(str(snap)))
        self.assertEqual((dest / "config").read_text(), "baseline")
        self.assertEqual(ledger.get_unit("app")["state"], "enabled")

    def legacy_rime_state(self):
        """模拟旧钩子写入 seed 后，Rime 正常构建更新同一运行时文件。"""
        from nyxuri.desktop import owned_outputs
        path = self.env.home / ".local/share/fcitx5/rime/user.yaml"
        owned_outputs.write_output("fcitx5-rime", "fcitx5-rime", path,
                                   b"var:\n  previously_selected_schema: rime_ice\n")
        claim = json.loads(owned_outputs.metadata_path().read_text())["outputs"][str(path)]
        path.write_bytes(b"var:\n  last_build_time: 1793089092\n  previously_selected_schema: rime_ice")
        return path, claim

    def test_rollback_accepts_unchanged_rime_runtime_and_keeps_legacy_baseline(self):
        from nyxuri.desktop import owned_outputs
        from nyxuri.state.backup import backup_configs, rollback_configs
        dest = self.stage("kitty", "baseline")
        runtime, claim = self.legacy_rime_state()
        runtime_bytes = runtime.read_bytes()
        with patch("builtins.print"):
            snap = backup_configs(interactive=False)
        (dest / "config").write_text("personal edit")
        self.stage("snapshot-new", "new payload")

        with patch("builtins.print"):
            self.assertTrue(rollback_configs(str(snap)))

        self.assertEqual((dest / "config").read_text(), "baseline")
        self.assertEqual(runtime.read_bytes(), runtime_bytes)
        # 无写入恢复不能把 Rime 更新后的内容重基成 Nyxuri 的最后写入身份。
        self.assertEqual(json.loads(owned_outputs.metadata_path().read_text())["outputs"][str(runtime)], claim)

    def test_rollback_still_preserves_rime_changes_after_snapshot(self):
        from nyxuri.state.backup import backup_configs, rollback_configs, get_all_backups
        self.stage("kitty", "baseline")
        runtime, _claim = self.legacy_rime_state()
        with patch("builtins.print"):
            snap = backup_configs(interactive=False)
        personal = b"var:\n  previously_selected_schema: personal\n"
        runtime.write_bytes(personal)

        with patch("builtins.print"), patch("sys.stderr"):
            self.assertFalse(rollback_configs(str(snap)))

        self.assertEqual(runtime.read_bytes(), personal)
        safety = next(path for path in get_all_backups() if path != snap)
        external = json.loads((safety / "external/outputs.json").read_text())
        import base64
        self.assertEqual(base64.b64decode(external["targets"][str(runtime)]["value"]), personal)


if __name__ == "__main__":
    unittest.main()

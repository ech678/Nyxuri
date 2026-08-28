"""Behavior contracts for backup/uninstall: non-interactive no-op, interactive flag, mode aliases.

Safety: all tests run inside TempEnv which isolates HOME to a temp directory.
No test may call real fcitx_uninstall, greeter_uninstall, or touch real ~/.config.
"""

import sys
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv


class TestUninstallNonInteractive(unittest.TestCase):
    """Non-interactive uninstall: no mode → select-all + archive (§8.5)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("test")

    def tearDown(self):
        self._ctx.__exit__()

    def test_non_interactive_uninstall_selects_all_and_archives(self):
        """Non-interactive uninstall (no mode) selects all + archives configs."""
        from nyxniri.state.uninstall import uninstall_nyxniri
        from nyxniri.constants import PROJECT_NAME

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=False), \
                 patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
                 patch("nyxniri.modules.greeter.greeter_installed", return_value=False):
                result = uninstall_nyxniri("")

        self.assertTrue(result, "Non-interactive uninstall selects all (no longer a no-op)")
        archives = list(self.env.config_dir.glob(f"{PROJECT_NAME}_archive_*"))
        self.assertTrue(archives, "Configs should be archived (non-interactive default = archive)")
        self.assertTrue((archives[0] / "niri" / "config.kdl").exists())
        self.assertFalse((self.env.config_dir / "niri").exists(), "Original removed after archiving")

    def test_non_interactive_uninstall_purge_still_works(self):
        """Explicit purge mode should still execute even non-interactively."""
        from nyxniri.state.uninstall import uninstall_nyxniri

        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.print"):
                with patch("nyxniri.state.uninstall.prompt_confirm", return_value=True):
                    with patch("nyxniri.state.uninstall.get_all_backups", return_value=[]):
                        with patch("nyxniri.modules.fcitx.fcitx_uninstall"):
                            with patch("nyxniri.modules.greeter.greeter_uninstall"):
                                with patch("nyxniri.state.uninstall.remove_path"):
                                    with patch("nyxniri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"):
                                        result = uninstall_nyxniri("purge")

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
        """Alias 'safe' is accepted and runs the all+archive path (non-TTY)."""
        from nyxniri.state.uninstall import uninstall_nyxniri

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.state.uninstall.copy_path"), patch("nyxniri.state.uninstall.remove_path"):
            with patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=False), \
                 patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
                 patch("nyxniri.modules.greeter.greeter_installed", return_value=False):
                result = uninstall_nyxniri("safe")

        self.assertTrue(result)

    def test_alias_purge_maps_correctly(self):
        """Alias '3' should map to purge."""
        from nyxniri.state.uninstall import uninstall_nyxniri

        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.print"):
                with patch("nyxniri.state.uninstall.prompt_confirm", return_value=True):
                    with patch("nyxniri.state.uninstall.get_all_backups", return_value=[]):
                        with patch("nyxniri.modules.fcitx.fcitx_uninstall"):
                            with patch("nyxniri.modules.greeter.greeter_uninstall"):
                                with patch("nyxniri.state.uninstall.remove_path"):
                                    with patch("nyxniri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"):
                                        result = uninstall_nyxniri("3")
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
        from nyxniri.state.backup import backup_configs

        with patch("builtins.print") as mock_print:
            with patch("nyxniri.deploy.deploy.discover_config_items", return_value=[]):
                backup_configs(note="test", interactive=False)

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertNotIn("backing_up", printed.lower(),
                         "interactive=False should not print backing_up message")

    def test_interactive_true_prints_output(self):
        """backup_configs with interactive=True should print."""
        from nyxniri.state.backup import backup_configs

        with patch("builtins.print") as mock_print:
            with patch("nyxniri.deploy.deploy.discover_config_items", return_value=[]):
                backup_configs(note="test", interactive=True)

        mock_print.assert_called()


class TestSnapshotRotation(unittest.TestCase):
    """_prune_old_snapshots keeps MAX_SNAPSHOTS, deletes oldest beyond that."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.base_dir = self.env.config_dir / "NyxNiri" / "backups"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_excess_snapshots_pruned_oldest_first(self):
        """Beyond MAX_SNAPSHOTS, oldest (by name) are removed."""
        from nyxniri.state.backup import _prune_old_snapshots, MAX_SNAPSHOTS

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
        from nyxniri.state.backup import _prune_old_snapshots, MAX_SNAPSHOTS

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
        self.base_dir = self.env.config_dir / "NyxNiri" / "backups"
        self.base_dir.mkdir(parents=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_oldest_snapshot_survives_pre_rollback_rotation(self):
        """At the limit, rollback keeps and restores the chosen oldest snapshot."""
        from nyxniri.state.backup import MAX_SNAPSHOTS, rollback_configs

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

        with patch("nyxniri.deploy.deploy.discover_config_items", return_value=["niri"]):
            self.assertTrue(rollback_configs(str(oldest)))

        self.assertTrue(oldest.is_dir())
        self.assertEqual((current / "config.kdl").read_text(), "historical")
        self.assertEqual(len(list(self.base_dir.iterdir())), MAX_SNAPSHOTS)

    def test_default_rollback_restores_snapshot_custom_bytes(self):
        """Rollback must not overlay snapshot custom files with current config."""
        from nyxniri.state.backup import rollback_configs

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

        with patch("nyxniri.deploy.deploy.discover_config_items", return_value=["niri"]):
            self.assertTrue(rollback_configs(str(snapshot)))

        self.assertEqual((current / "__custom__.kdl").read_text(), "historical custom")
        self.assertEqual((current / "__custom__" / "rule.kdl").read_text(), "historical rule")

    def test_rollback_fails_when_selected_source_disappears(self):
        """A selected snapshot removed during the safety backup is a hard failure."""
        from nyxniri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        (snapshot / "niri").mkdir(parents=True)
        (snapshot / "niri" / "config.kdl").write_text("historical")

        def remove_source(*_args, **_kwargs):
            shutil.rmtree(snapshot)
            return self.base_dir / "snapshot_20260102_000000"

        with patch("nyxniri.state.backup.backup_configs", side_effect=remove_source), \
             patch("nyxniri.deploy.deploy.discover_config_items", return_value=["niri"]), \
             patch("nyxniri.state.backup.msg", side_effect=lambda key, *_args: key), \
             patch("builtins.print") as mock_print:
            self.assertFalse(rollback_configs(str(snapshot)))

        self.assertIn("rollback_source_missing", str(mock_print.call_args_list))

    def test_rollback_fails_when_an_expected_item_disappears(self):
        """Rollback must not partly restore a snapshot whose item disappears."""
        from nyxniri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        for item, content in (("niri", "historical niri"), ("kitty", "historical kitty")):
            (snapshot / item).mkdir(parents=True)
            (snapshot / item / "config").write_text(content)
            (self.env.config_dir / item).mkdir()
            (self.env.config_dir / item / "config").write_text(f"current {item}")

        def remove_niri(*_args, **_kwargs):
            shutil.rmtree(snapshot / "niri")
            return self.base_dir / "snapshot_20260102_000000"

        with patch("nyxniri.state.backup.backup_configs", side_effect=remove_niri), \
             patch("nyxniri.deploy.deploy.discover_config_items", return_value=["niri", "kitty"]), \
             patch("builtins.print"):
            self.assertFalse(rollback_configs(str(snapshot)))

        self.assertEqual((self.env.config_dir / "kitty" / "config").read_text(), "current kitty")

    def test_rollback_keeps_earlier_items_when_a_later_item_disappears(self):
        """All expected items must survive the safety backup before any restore."""
        from nyxniri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        for item, content in (("niri", "historical niri"), ("kitty", "historical kitty")):
            (snapshot / item).mkdir(parents=True)
            (snapshot / item / "config").write_text(content)
            (self.env.config_dir / item).mkdir()
            (self.env.config_dir / item / "config").write_text(f"current {item}")

        def remove_kitty(*_args, **_kwargs):
            shutil.rmtree(snapshot / "kitty")
            return self.base_dir / "snapshot_20260102_000000"

        with patch("nyxniri.state.backup.backup_configs", side_effect=remove_kitty), \
             patch("nyxniri.deploy.deploy.discover_config_items", return_value=["niri", "kitty"]), \
             patch("builtins.print"):
            self.assertFalse(rollback_configs(str(snapshot)))

        self.assertEqual((self.env.config_dir / "niri" / "config").read_text(), "current niri")

    def test_rollback_fails_when_snapshot_has_no_restorable_items(self):
        """A snapshot that restores nothing must not report success."""
        from nyxniri.state.backup import rollback_configs

        snapshot = self.base_dir / "snapshot_20260101_000000"
        snapshot.mkdir()

        with patch("nyxniri.deploy.deploy.discover_config_items", return_value=["niri"]), \
             patch("builtins.print"):
            self.assertFalse(rollback_configs(str(snapshot)))


if __name__ == "__main__":
    unittest.main()

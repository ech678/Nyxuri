"""Contract tests for NyxNiri -> Nyxuri rebranding and storage migration."""

import os
from pathlib import Path
import unittest

from tests.utils import TempEnv
from nyxuri.constants import get_compat_env
from nyxuri.core import (
    ensure_nyxuri_symlink,
    is_nyxuri_cli_symlink,
    migrate_legacy_storage,
)


class TestRebrandStorageMigration(unittest.TestCase):
    """Legacy NyxNiri directories migrate cleanly into nyxuri with zero residue."""

    def test_legacy_config_and_state_migration(self):
        with TempEnv() as ctx:
            env = ctx.env
            legacy_config = env.home / ".config" / "NyxNiri"
            legacy_config.mkdir(parents=True, exist_ok=True)
            (legacy_config / "marker.txt").write_text("config_payload", encoding="utf-8")

            legacy_state = env.home / ".local" / "state" / "NyxNiri"
            legacy_state.mkdir(parents=True, exist_ok=True)
            (legacy_state / "state.log").write_text("log_payload", encoding="utf-8")

            legacy_cache = env.home / ".cache" / "nyxniri"
            legacy_cache.mkdir(parents=True, exist_ok=True)
            (legacy_cache / "cached.dat").write_text("cache_payload", encoding="utf-8")

            migrate_legacy_storage(env)

            # Old directories must not exist
            self.assertFalse(legacy_config.exists(), "Legacy config directory must be removed")
            self.assertFalse(legacy_state.exists(), "Legacy state directory must be removed")
            self.assertFalse(legacy_cache.exists(), "Legacy cache directory must be removed")

            # New directories must contain the migrated payloads
            self.assertTrue(env.nyx_dir.is_dir())
            self.assertEqual((env.nyx_dir / "marker.txt").read_text(encoding="utf-8"), "config_payload")
            self.assertEqual((env.state_dir / "state.log").read_text(encoding="utf-8"), "log_payload")
            self.assertEqual((env.cache_dir / "cached.dat").read_text(encoding="utf-8"), "cache_payload")

    def test_recursive_directory_merge(self):
        """When target directory already exists, nested directories must merge recursively without data loss."""
        with TempEnv() as ctx:
            env = ctx.env
            # Target already has presets/niri.active and presets/custom_preset/item1
            (env.nyx_dir / "presets" / "custom_preset").mkdir(parents=True, exist_ok=True)
            (env.nyx_dir / "presets" / "niri.active").write_text("active_target", encoding="utf-8")
            (env.nyx_dir / "presets" / "custom_preset" / "item1.kdl").write_text("item1_target", encoding="utf-8")

            # Legacy has presets/custom_preset/item1 (collision) and presets/custom_preset/item2 (new)
            legacy_config = env.home / ".config" / "NyxNiri"
            (legacy_config / "presets" / "custom_preset").mkdir(parents=True, exist_ok=True)
            (legacy_config / "presets" / "custom_preset" / "item1.kdl").write_text("item1_legacy", encoding="utf-8")
            (legacy_config / "presets" / "custom_preset" / "item2.kdl").write_text("item2_legacy", encoding="utf-8")
            (legacy_config / "presets" / "legacy_preset").mkdir(parents=True, exist_ok=True)
            (legacy_config / "presets" / "legacy_preset" / "item3.kdl").write_text("item3_legacy", encoding="utf-8")

            migrate_legacy_storage(env)

            self.assertFalse(legacy_config.exists())
            # Existing target files preserved
            self.assertEqual((env.nyx_dir / "presets" / "niri.active").read_text(encoding="utf-8"), "active_target")
            self.assertEqual((env.nyx_dir / "presets" / "custom_preset" / "item1.kdl").read_text(encoding="utf-8"), "item1_target")
            # Legacy files merged in
            self.assertEqual((env.nyx_dir / "presets" / "custom_preset" / "item2.kdl").read_text(encoding="utf-8"), "item2_legacy")
            self.assertEqual((env.nyx_dir / "presets" / "legacy_preset" / "item3.kdl").read_text(encoding="utf-8"), "item3_legacy")

    def test_legacy_cli_link_purged_on_ensure(self):
        with TempEnv() as ctx:
            env = ctx.env
            bin_dir = env.home / ".local/bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            legacy_link = bin_dir / "nyxniri"
            installer = env.repo_dir / "install.sh"
            installer.touch()
            legacy_link.symlink_to(installer)

            self.assertTrue(is_nyxuri_cli_symlink(legacy_link))
            ensure_nyxuri_symlink()

            new_link = bin_dir / "nyxuri"
            self.assertTrue(new_link.is_symlink())
            self.assertEqual(new_link.resolve(), installer.resolve())
            self.assertFalse(legacy_link.exists(), "Legacy CLI symlink must be purged")


class TestCompatEnv(unittest.TestCase):
    """Backward-compatible environment variable resolution."""

    def test_nyxuri_takes_precedence_over_nyxniri(self):
        env_vars = {
            "NYXURI_CUSTOM_SHELL": "/bin/zsh",
            "NYXNIRI_CUSTOM_SHELL": "/bin/bash",
        }
        with unittest.mock.patch.dict(os.environ, env_vars, clear=False):
            self.assertEqual(get_compat_env("CUSTOM_SHELL"), "/bin/zsh")

    def test_fallback_to_legacy_nyxniri(self):
        env_vars = {
            "NYXNIRI_CUSTOM_SHELL": "/bin/fish",
        }
        with unittest.mock.patch.dict(os.environ, env_vars, clear=False):
            if "NYXURI_CUSTOM_SHELL" in os.environ:
                del os.environ["NYXURI_CUSTOM_SHELL"]
            self.assertEqual(get_compat_env("CUSTOM_SHELL"), "/bin/fish")

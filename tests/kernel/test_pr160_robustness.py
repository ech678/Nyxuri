"""Unit tests for PR #160 runtime robustness fixes.

All filesystem tests run inside ``TempEnv`` and isolated temporary plugin
directories so neither real ``~/.config`` nor repo ``plugins/`` is touched.
"""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


class TestSwapJournalRecovery(unittest.TestCase):
    """Tests for nyxuri.deploy.atomic.recover_interrupted_swaps."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_restores_missing_dest_and_cleans_journal(self):
        from nyxuri.deploy import atomic

        dest = self.env.config_dir / "kitty"
        old_dest = self.env.config_dir / "kitty.old.99999"
        tmp_new = self.env.config_dir / "kitty.new.99999"
        old_dest.mkdir(parents=True, exist_ok=True)
        (old_dest / "kitty.conf").write_text("font_size 12\n")
        tmp_new.mkdir(parents=True, exist_ok=True)
        (tmp_new / "kitty.conf").write_text("stale\n")

        atomic._swap_journal_begin(dest, old_dest, tmp_new)
        recovered = atomic.recover_interrupted_swaps()

        self.assertEqual(recovered, ["kitty"])
        self.assertTrue((dest / "kitty.conf").is_file())
        self.assertFalse(old_dest.exists())
        self.assertFalse(tmp_new.exists())
        self.assertFalse(atomic._swap_journal_file(dest).exists())

    def test_keeps_journal_when_rename_fails(self):
        from nyxuri.deploy import atomic

        dest = self.env.config_dir / "niri"
        old_dest = self.env.config_dir / "niri.old.99999"
        tmp_new = self.env.config_dir / "niri.new.99999"
        old_dest.mkdir(parents=True, exist_ok=True)
        (old_dest / "config.kdl").write_text("// kdl\n")

        atomic._swap_journal_begin(dest, old_dest, tmp_new)
        journal = atomic._swap_journal_file(dest)
        self.assertTrue(journal.is_file())

        with patch.object(Path, "rename", side_effect=OSError("busy")):
            recovered = atomic.recover_interrupted_swaps()

        self.assertEqual(recovered, [])
        self.assertTrue(journal.is_file(), "journal must survive failed recovery for retry")


class TestManifestTargetValidation(unittest.TestCase):
    """Tests for nyxuri.deploy.manifest target path restrictions."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_rejects_absolute_and_bare_tilde_targets(self):
        from nyxuri.deploy import manifest

        for bad_target in ("/etc/passwd", "~", "~other/file"):
            plugin = self.env.plugins_src / "bad"
            plugin.mkdir(parents=True, exist_ok=True)
            (plugin / "a.conf").write_text("x\n")
            (plugin / "manifest.toml").write_text(
                f'schemaVersion = 1\nid = "bad"\nkinds = ["config"]\ntarget = "{bad_target}"\n'
            )
            with self.assertRaises(ValueError, msg=f"expected rejection for {bad_target}"):
                manifest.load_manifest(plugin)

    def test_allows_home_relative_target(self):
        from nyxuri.deploy import manifest

        plugin = self.env.plugins_src / "good"
        plugin.mkdir(parents=True, exist_ok=True)
        (plugin / "a.conf").write_text("x\n")
        (plugin / "manifest.toml").write_text(
            'schemaVersion = 1\nid = "good"\nkinds = ["config"]\ntarget = "~/.config/good"\n'
        )
        m = manifest.load_manifest(plugin)
        resolved = manifest.living_path(m, self.env.config_dir)
        self.assertEqual(resolved, self.env.home / ".config" / "good")


class TestStoreCorruptBackup(unittest.TestCase):
    """Tests for nyxuri.state.store corrupt state.json preservation."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_preserves_corrupt_state_idempotently(self):
        from nyxuri.state import store

        path = store.store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{broken json", encoding="utf-8")

        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            first = store.read_state()
            second = store.read_state()

        self.assertEqual(first, {})
        self.assertEqual(second, {})
        backups = list(path.parent.glob(f"{path.name}.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{broken json")
        self.assertIn("state.json unreadable", stderr_buf.getvalue())


class TestEngineDriftAndForms(unittest.TestCase):
    """Tests for engine.plugin_off drift archiving and plugin_on form validation."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def _make_plugin(self, name: str = "demo"):
        p = self.env.plugins_src / name
        p.mkdir(parents=True, exist_ok=True)
        (p / "demo.conf").write_text("original\n")
        (p / "manifest.toml").write_text(
            f'schemaVersion = 1\nid = "{name}"\nkinds = ["config"]\npackages = []\n'
        )
        return p

    def test_plugin_off_archives_drifted_managed_file(self):
        from nyxuri.deploy import engine

        self._make_plugin("demo")
        on_steps = engine.plugin_on("demo")
        self.assertTrue(all(s.ok for s in on_steps), on_steps)

        live_file = self.env.config_dir / "demo" / "demo.conf"
        live_file.write_text("user-edited\n")

        off_steps = engine.plugin_off("demo")
        self.assertTrue(all(s.ok for s in off_steps), off_steps)
        self.assertIn("drift-archived: 1", off_steps[0].detail)

        archived = list((engine.vault_dir("demo") / ".drift").rglob("demo.conf"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_text(encoding="utf-8"), "user-edited\n")

    def test_plugin_on_rejects_invalid_and_missing_forms(self):
        from nyxuri.deploy import engine

        self._make_plugin("demo")
        bad = engine.plugin_on("demo", form="../evil")
        self.assertFalse(bad[0].ok)
        self.assertTrue(bad[0].detail.startswith("invalid-form:"), bad[0].detail)

        missing = engine.plugin_on("demo", form="nonexistent")
        self.assertFalse(missing[0].ok)
        self.assertTrue(missing[0].detail.startswith("form-not-found:"), missing[0].detail)


class TestShellBinResolution(unittest.TestCase):
    """Tests for nyxuri.system.shell repo-local binary discovery."""

    def test_find_default_custom_bin_resolves_repo_shell(self):
        from nyxuri.system import shell

        repo_root = Path(shell.__file__).resolve().parent.parent.parent
        expected = repo_root / "shell" / "nyxuri-shell"
        self.assertTrue(expected.is_file(), f"expected {expected} to exist")
        self.assertEqual(shell.find_default_custom_bin(), str(expected))


if __name__ == "__main__":
    unittest.main()

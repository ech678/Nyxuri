"""Contract tests for the preset mechanism (§3.2).

Covers §14 shapes: the four src-selection branches, dest-missing reset with
upstream-removed warning, state file read/write, and __custom__ preservation
across preset switches (regression guard for the copytree ignore change).
"""

import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import nyxniri.deploy.preset as preset
from nyxniri.deploy.atomic import atomic_replace_item
from nyxniri.tui import PresetSwitcher
from nyxniri.i18n import msg
from tests.utils import TempEnv


class TestActiveStateFile(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_read_default_when_no_file(self):
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_write_then_read(self):
        preset.write_active_preset("kitty", "transparent")
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")

    def test_write_creates_presets_dir(self):
        # presets_dir does not exist initially; write must create it.
        self.assertFalse(self._ctx.env.presets_dir.exists())
        preset.write_active_preset("kitty", "compact")
        self.assertTrue(self._ctx.env.presets_dir.is_dir())

    def test_read_empty_file_freezes_instead_of_default(self):
        self._ctx.env.presets_dir.mkdir(parents=True, exist_ok=True)
        (self._ctx.env.presets_dir / "kitty.active").write_text("   \n")
        with self.assertRaises(preset.InvalidActivePresetError):
            preset.read_active_preset("kitty")

    def test_read_rejects_active_name_with_outer_whitespace(self):
        self._ctx.env.presets_dir.mkdir(parents=True, exist_ok=True)
        active = self._ctx.env.presets_dir / "kitty.active"
        for value in (" transparent", "transparent ", "transparent\n"):
            with self.subTest(value=value):
                active.write_text(value)
                with self.assertRaises(preset.InvalidActivePresetError):
                    preset.read_active_preset("kitty")


class TestResolvePresetSrc(unittest.TestCase):
    """The four src branches (§3.2) — parameter-shape contract on src path."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.configs_src = Path(self._sandbox.name)

        self.app = "kitty"
        self.app_root = self.env.configs_src / self.app
        self.app_root.mkdir(parents=True)
        (self.app_root / "kitty.conf").write_text("# default")

        self.official = self.app_root / "presets" / "transparent"
        self.official.mkdir(parents=True)
        (self.official / "kitty.conf").write_text("# transparent")

        self.dest = self.env.config_dir / self.app

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_default_branch(self):
        r = preset.resolve_preset_src(self.app, "default", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertIsNone(r.reset_active)
        self.assertEqual(r.warnings, [])

    def test_official_preset_branch(self):
        self.dest.mkdir(parents=True)
        (self.dest / "old.conf").write_text("x")
        r = preset.resolve_preset_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.official)
        self.assertIsNone(r.reset_active)

    def test_user_preset_branch(self):
        self.dest.mkdir(parents=True)
        user_dir = self.env.presets_dir / self.app / "mine"
        user_dir.mkdir(parents=True)
        r = preset.resolve_preset_src(self.app, "mine", self.dest)
        self.assertEqual(r.src, user_dir)

    def test_official_preferred_over_user_same_name(self):
        # §2.2: official wins on name collision
        self.dest.mkdir(parents=True)
        (self.env.presets_dir / self.app / "transparent").mkdir(parents=True)
        r = preset.resolve_preset_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.official)

    def test_not_found_freezes_dest(self):
        # active = ghost, dest exists → src None (freeze), warning. Do NOT
        # fall back to default (would silently wipe the user's config). §3.2
        self.dest.mkdir(parents=True)
        r = preset.resolve_preset_src(self.app, "ghost", self.dest)
        self.assertIsNone(r.src)
        self.assertTrue(r.warnings)

    def test_dest_missing_resets_to_default(self):
        # dest absent + active=transparent (still upstream) → default, no extra warning
        r = preset.resolve_preset_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertEqual(r.reset_active, "default")
        self.assertEqual(r.warnings, [])

    def test_dest_missing_and_upstream_removed_warns(self):
        # dest absent + active=ghost (gone upstream) → default + extra warning (B1)
        r = preset.resolve_preset_src(self.app, "ghost", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertEqual(r.reset_active, "default")
        self.assertTrue(r.warnings)


class TestCustomSurvivesPresetSwitch(unittest.TestCase):
    """__custom__ files survive preset switches (Dunder + copytree-ignore compat)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.configs_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_custom_file_retained_across_two_presets(self):
        app = "kitty"
        root = self.env.configs_src / app
        root.mkdir(parents=True)
        transparent = root / "presets" / "transparent"
        transparent.mkdir(parents=True)
        (transparent / "kitty.conf").write_text("# transparent")
        compact = root / "presets" / "compact"
        compact.mkdir(parents=True)
        (compact / "kitty.conf").write_text("# compact")

        dest = self.env.config_dir / app
        # First deploy transparent, then add a user __custom__.conf, then switch.
        self.assertTrue(atomic_replace_item(transparent, dest))
        (dest / "__custom__.conf").write_text("# my overrides")
        self.assertTrue(atomic_replace_item(compact, dest))

        # compact's kitty.conf is now in dest, and __custom__.conf survived.
        self.assertEqual((dest / "kitty.conf").read_text(), "# compact")
        self.assertTrue((dest / "__custom__.conf").exists())
        self.assertEqual((dest / "__custom__.conf").read_text(), "# my overrides")

    def test_module_toml_not_shipped_to_dest(self):
        # §10.4 boundary: .module.toml is repo metadata, must not land in dest.
        app = "kitty"
        root = self.env.configs_src / app
        root.mkdir(parents=True)
        (root / "kitty.conf").write_text("# conf")
        (root / ".module.toml").write_text('[packages]\nrepo = ["kitty"]\n')
        dest = self.env.config_dir / app
        atomic_replace_item(root, dest)
        self.assertFalse((dest / ".module.toml").exists())
        # The real kitty.conf did ship.
        self.assertTrue((dest / "kitty.conf").exists())

    def test_presets_subdir_not_shipped_to_dest(self):
        # presets/ stays in repo, not deployed into ~/.config/<app>/presets/
        app = "kitty"
        root = self.env.configs_src / app
        root.mkdir(parents=True)
        (root / "kitty.conf").write_text("# conf")
        (root / "presets" / "transparent").mkdir(parents=True)
        (root / "presets" / "transparent" / "kitty.conf").write_text("# t")
        dest = self.env.config_dir / app
        atomic_replace_item(root, dest)
        self.assertFalse((dest / "presets").exists())


class TestPresetOperations(unittest.TestCase):
    """list/apply/save/delete against the real repo's kitty + transparent demo."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_list_marks_active_default(self):
        entries = preset.list_presets("kitty")
        names = [n for n, _, _ in entries]
        self.assertIn("default", names)
        self.assertIn("transparent", names)  # the shipped demo preset
        active_entry = [e for e in entries if e[2]]
        self.assertEqual(len(active_entry), 1)
        self.assertEqual(active_entry[0][0], "default")  # fresh = default

    def test_apply_transparent_writes_active_and_deploys_variant(self):
        ok = preset.apply_preset("kitty", "transparent")
        self.assertTrue(ok)
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")
        conf = self.env.config_dir / "kitty" / "kitty.conf"
        self.assertTrue(conf.is_file())
        self.assertIn("0.75", conf.read_text())  # the transparent variant

    def test_apply_default_resets(self):
        preset.write_active_preset("kitty", "transparent")
        ok = preset.apply_preset("kitty", "default")
        self.assertTrue(ok)
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_apply_unknown_preset_fails_without_writing(self):
        # Nonexistent preset: fail, do not touch active.
        preset.write_active_preset("kitty", "transparent")
        ok = preset.apply_preset("kitty", "ghost")
        self.assertFalse(ok)
        self.assertEqual(preset.read_active_preset("kitty"), "transparent")

    def test_apply_then_write_timing_atomic_fail_leaves_active(self):
        # B2 (§14): if atomic_replace fails, active must NOT be written.
        preset.write_active_preset("kitty", "default")
        with patch("nyxniri.deploy.atomic.atomic_replace_item", return_value=False):
            ok = preset.apply_preset("kitty", "transparent")
        self.assertFalse(ok)
        # active still default — deploy-then-write held back the write.
        self.assertEqual(preset.read_active_preset("kitty"), "default")

    def test_save_rejects_reserved_default(self):
        # Set up a dest so the rejection is specifically the name, not the empty dest.
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# conf")
        self.assertFalse(preset.save_preset("kitty", "default"))

    def test_save_rejects_official_name_collision(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# conf")
        # 'transparent' is an official preset — collision must be rejected.
        self.assertFalse(preset.save_preset("kitty", "transparent"))

    def test_save_snapshots_tree_minus_custom(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# my conf")
        (dest / "__custom__.conf").write_text("# private")
        custom_dir = dest / "__custom__"
        custom_dir.mkdir()
        (custom_dir / "extra.conf").write_text("# nested custom")

        self.assertTrue(preset.save_preset("kitty", "mine"))
        target = self.env.presets_dir / "kitty" / "mine"
        self.assertTrue((target / "kitty.conf").is_file())
        # __custom__ entries filtered out (both file and dir).
        self.assertFalse((target / "__custom__.conf").exists())
        self.assertFalse((target / "__custom__").exists())

    def test_save_then_apply_user_preset(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# my flavor")
        self.assertTrue(preset.save_preset("kitty", "mine"))
        # Wipe dest, then re-apply the saved user preset.
        import shutil
        shutil.rmtree(dest)
        self.assertTrue(preset.apply_preset("kitty", "mine"))
        self.assertEqual(preset.read_active_preset("kitty"), "mine")
        self.assertEqual((dest / "kitty.conf").read_text(), "# my flavor")

    def test_delete_user_preset(self):
        target = self.env.presets_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        (target / "kitty.conf").write_text("# x")
        self.assertTrue(preset.delete_preset("kitty", "mine"))
        self.assertFalse(target.exists())

    def test_delete_rejects_default_and_official(self):
        self.assertFalse(preset.delete_preset("kitty", "default"))
        self.assertFalse(preset.delete_preset("kitty", "transparent"))

    def test_save_presets_open_failure_closes_source_fd(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# conf")
        real_open = os.open
        source_fd = None

        def track_source_open(path, flags, *args, **kwargs):
            nonlocal source_fd
            fd = real_open(path, flags, *args, **kwargs)
            if path == dest:
                source_fd = fd
            return fd

        with patch.object(preset.os, "open", side_effect=track_source_open), \
             patch.object(preset, "_open_presets_dir", side_effect=OSError), \
             patch.object(preset.os, "close", wraps=os.close) as close:
            self.assertFalse(preset.save_preset("kitty", "mine"))

        self.assertIsNotNone(source_fd)
        self.assertTrue(any(call.args == (source_fd,) for call in close.call_args_list))


class TestApplyNarrowPath(unittest.TestCase):
    """§9 / §14 U1: apply runs only atomic_replace + render — no hw patches, no services."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_apply_skips_hardware_patches_and_post_install_services(self):
        # Patch the deploy namespace: deploy.py holds its own from-import of
        # _phase_hardware_patches, so patching the hardware module would miss.
        with patch("nyxniri.deploy.deploy._phase_hardware_patches") as hw, \
             patch("nyxniri.deploy.deploy._phase_post_install_services") as svc:
            ok = preset.apply_preset("kitty", "transparent")
        self.assertTrue(ok)
        hw.assert_not_called()
        svc.assert_not_called()


class TestPresetSwitchPreservesManifestFiles(unittest.TestCase):
    """The narrow deploy path honours the manifest ``preserve`` list.

    Regression guard: applying a preset must not wipe runtime-managed files the
    new variant doesn't ship — specifically niri/effects.kdl (a symlink whose
    target encodes EyeCare on/off) and niri/monitor.kdl (user-generated). Both
    are declared in niri/.module.toml preserve and must survive a switch.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.niri_dest = self.env.config_dir / "niri"
        # Deploy niri defaults first so monitor.kdl + effects_*.kdl exist.
        from nyxniri.deploy.atomic import atomic_replace_item
        atomic_replace_item(self.env.configs_src / "niri", self.niri_dest)
        # Create the runtime effects.kdl symlink (as deploy.py does on first install).
        effects_normal = self.niri_dest / "effects_normal.kdl"
        self.effects_sym = self.niri_dest / "effects.kdl"
        self.effects_sym.symlink_to(effects_normal)
        # Mark monitor.kdl so we can detect a wipe.
        self.monitor = self.niri_dest / "monitor.kdl"
        with self.monitor.open("a") as f:
            f.write("# USER-MARKER\n")

    def tearDown(self):
        self._ctx.__exit__()

    def test_effects_kdl_symlink_survives_preset_switch(self):
        self.assertTrue(preset.apply_preset("niri", "default"))
        self.assertTrue(self.effects_sym.is_symlink(), "effects.kdl symlink was wiped")
        self.assertIn("effects_normal.kdl", os.readlink(self.effects_sym))

    def test_monitor_kdl_survives_preset_switch(self):
        self.assertTrue(preset.apply_preset("niri", "default"))
        self.assertIn("# USER-MARKER", self.monitor.read_text())


class TestPresetPathBoundary(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_traversal_is_rejected_before_delete_or_active_write(self):
        victim = self.env.presets_dir / "victim"
        victim.mkdir(parents=True)
        sentinel = victim / "sentinel"
        sentinel.write_text("keep")
        escaped_active = self.env.config_dir / "escaped.active"
        escaped_active.write_text("keep")

        self.assertFalse(preset.delete_preset("kitty", "../victim"))
        with self.assertRaises(ValueError):
            preset.write_active_preset("../../escaped", "mine")

        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(escaped_active.read_text(), "keep")

    def test_every_operation_rejects_absolute_and_dot_components(self):
        absolute = str(self._ctx.home / "outside")
        for name in ("../victim", absolute, ".", ".."):
            with self.subTest(name=name), \
                 patch("nyxniri.deploy.atomic.atomic_replace_item") as replace, \
                 patch.object(preset.subprocess, "run") as run:
                self.assertFalse(preset.apply_preset("kitty", name))
                self.assertFalse(preset.save_preset("kitty", name))
                self.assertFalse(preset.delete_preset("kitty", name))
                self.assertFalse(preset.edit_preset("kitty", name))
                with self.assertRaises(ValueError):
                    preset.write_active_preset("kitty", name)
                replace.assert_not_called()
                run.assert_not_called()

        self.assertFalse(preset.apply_preset("../outside", "default"))
        with self.assertRaises(ValueError):
            preset.write_active_preset("../outside", "mine")

    def test_symlinked_user_preset_never_starts_editor(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        user_root = self.env.presets_dir / "kitty"
        user_root.mkdir(parents=True)
        (user_root / "mine").symlink_to(outside, target_is_directory=True)

        with patch("sys.stdin.isatty", return_value=True), \
             patch.object(preset.subprocess, "run") as run:
            self.assertFalse(preset.edit_preset("kitty", "mine"))

        run.assert_not_called()

    def test_symlinked_user_preset_is_never_applied_or_deleted(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        user_root = self.env.presets_dir / "kitty"
        user_root.mkdir(parents=True)
        (user_root / "mine").symlink_to(outside, target_is_directory=True)

        with patch("nyxniri.deploy.atomic.atomic_replace_item") as replace:
            self.assertFalse(preset.apply_preset("kitty", "mine"))
        self.assertFalse(preset.delete_preset("kitty", "mine"))

        replace.assert_not_called()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_symlinked_config_target_is_rejected_before_apply(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("keep")
        (self.env.config_dir / "kitty").symlink_to(outside, target_is_directory=True)

        with patch("nyxniri.deploy.atomic.atomic_replace_item") as replace:
            self.assertFalse(preset.apply_preset("kitty", "default"))

        replace.assert_not_called()
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_symlinked_config_target_is_rejected_before_save(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        (self.env.config_dir / "kitty").symlink_to(outside, target_is_directory=True)

        self.assertFalse(preset.save_preset("kitty", "mine"))

        self.assertEqual(sentinel.read_text(), "keep")

    def test_active_rejects_absolute_traversal_and_symlink(self):
        active = self.env.presets_dir / "kitty.active"
        active.parent.mkdir(parents=True, exist_ok=True)
        for name in ("../victim", str(self._ctx.home / "outside")):
            with self.subTest(name=name):
                active.write_text(name)
                with self.assertRaises(preset.InvalidActivePresetError):
                    preset.read_active_preset("kitty")
        outside = self._ctx.home / "outside-active"
        outside.write_text("transparent")
        active.unlink()
        active.symlink_to(outside)
        with self.assertRaises(preset.InvalidActivePresetError):
            preset.read_active_preset("kitty")
        with self.assertRaises(OSError):
            preset.write_active_preset("kitty", "default")
        self.assertEqual(outside.read_text(), "transparent")

    def test_invalid_active_state_freezes_deploy(self):
        active = self.env.presets_dir / "kitty.active"
        active.parent.mkdir(parents=True, exist_ok=True)
        active.write_text("../victim")

        with patch("nyxniri.deploy.deploy.atomic_replace_item") as replace, \
             patch("sys.stdout", new_callable=StringIO) as output:
            from nyxniri.deploy.deploy import _phase_atomic_deployment
            _phase_atomic_deployment(["kitty"])

        replace.assert_not_called()
        self.assertIn(msg("preset_warn_invalid_active", "kitty"), output.getvalue())

    def test_invalid_active_state_is_visible_when_collecting(self):
        active = self.env.presets_dir / "kitty.active"
        active.parent.mkdir(parents=True, exist_ok=True)
        active.write_text("../victim")

        with patch("sys.stdout", new_callable=StringIO) as output:
            self.assertEqual(preset.collect_presets("kitty"), [])

        self.assertIn(msg("preset_warn_invalid_active", "kitty"), output.getvalue())

    def test_unicode_leaf_name_remains_usable(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("current")
        name = "主题 浅色"

        self.assertTrue(preset.save_preset("kitty", name))
        self.assertTrue(preset.apply_preset("kitty", name))
        self.assertTrue(preset.delete_preset("kitty", name))

    def test_delete_rejects_directory_swap_after_lookup(self):
        user_root = self.env.presets_dir / "kitty"
        mine = user_root / "mine"
        mine.mkdir(parents=True)
        outside = self._ctx.home / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        stash = user_root / "mine-stash"
        real_open = os.open
        swapped = False

        def open_then_swap(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == "mine" and not swapped:
                mine.rename(stash)
                outside.rename(mine)
                swapped = True
            return real_open(path, flags, *args, **kwargs)

        with patch("nyxniri.deploy.preset.os.open", side_effect=open_then_swap):
            self.assertFalse(preset.delete_preset("kitty", "mine"))

        self.assertTrue(swapped)
        self.assertEqual((mine / "sentinel").read_text(), "keep")


class TestPresetSwitcher(unittest.TestCase):
    """Preset Switcher interactive tests via a mocked key stream."""

    def _run_keys(self, switcher, keys):
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=keys), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def test_enter_returns_app_and_preset(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # RIGHT → expand kitty & land on default; DOWN → transparent; ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "DOWN", "ENTER"]), ("kitty", "transparent"))

    def test_pane_switch_keeps_app_cursor(self):
        apps = ["fastfetch", "kitty"]
        presets_kitty = [("default", True), ("transparent", False)]
        sw = PresetSwitcher(apps, lambda a: presets_kitty if a == "kitty" else [("default", True)])
        # DOWN→app kitty; RIGHT→expand; LEFT→back to app kitty; RIGHT→focus presets; DOWN; ENTER
        self.assertEqual(
            self._run_keys(sw, ["DOWN", "RIGHT", "LEFT", "RIGHT", "DOWN", "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_up_down_cycles_in_pane(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False), ("compact", False)])
        # RIGHT; DOWN; DOWN; ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "DOWN", "DOWN", "ENTER"]), ("kitty", "compact"))

    def test_app_switch_lands_cursor_on_active_preset(self):
        apps = ["fastfetch", "kitty"]
        presets_kitty = [("default", False), ("transparent", True)]  # transparent is active
        sw = PresetSwitcher(apps, lambda a: presets_kitty if a == "kitty" else [("default", True)])
        # DOWN→kitty; RIGHT→expand kitty; ENTER applies active transparent directly
        self.assertEqual(self._run_keys(sw, ["DOWN", "RIGHT", "ENTER"]), ("kitty", "transparent"))

    def test_cancel_returns_none(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        self.assertIsNone(self._run_keys(sw, ["q"]))

    def test_no_tty_returns_none(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        with patch("sys.stdin.isatty", return_value=False):
            self.assertIsNone(sw.run())


class TestPresetSwitcherMouse(unittest.TestCase):
    """Mouse interaction: click selects/expands, wheel scrolls."""

    def _run_keys(self, switcher, keys):
        import os
        import nyxniri.tui as tui
        fake_size = os.terminal_size((80, 24))
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=keys), \
             patch.object(tui.shutil, "get_terminal_size", return_value=fake_size), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def _click(self, col, row):
        from nyxniri.tui import MouseEvent
        return MouseEvent(kind="PRESS", col=col, row=row)

    def _wheel(self, kind, col=3, row=15):
        from nyxniri.tui import MouseEvent
        return MouseEvent(kind=kind, col=col, row=row)

    def test_click_app_applies_active_preset_in_standalone_mode(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True), ("transparent", False)])
        # Click kitty at row 15 -> returns ("kitty", "default")
        self.assertEqual(self._run_keys(sw, [self._click(10, 14)]), ("kitty", "default"))

    def test_wheel_down_cycles_app(self):
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True)] if a == "fastfetch" else [("transparent", True)],
        )
        # wheel-down -> fastfetch to kitty; Enter applies kitty/transparent.
        self.assertEqual(
            self._run_keys(sw, [self._wheel("WHEEL_DOWN"), "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_wheel_up_cycles_backwards(self):
        sw = PresetSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", True)] if a == "fastfetch" else [("transparent", True)],
        )
        # DOWN to kitty first, then WHEEL_UP back to fastfetch, Enter -> fastfetch/default.
        self.assertEqual(
            self._run_keys(sw, ["DOWN", self._wheel("WHEEL_UP"), "ENTER"]),
            ("fastfetch", "default"),
        )

    def test_click_on_header_row_is_ignored(self):
        sw = PresetSwitcher(["kitty"], lambda a: [("default", True)])
        self.assertEqual(self._run_keys(sw, [self._click(40, 12), "ENTER"]), ("kitty", "default"))


class TestEditPreset(unittest.TestCase):
    """edit_preset: rejects default/official/missing; opens editor on a user preset."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_rejects_default(self):
        self.assertFalse(preset.edit_preset("kitty", "default"))

    def test_rejects_official(self):
        # 'transparent' is a shipped official preset — read-only.
        self.assertFalse(preset.edit_preset("kitty", "transparent"))

    def test_rejects_missing(self):
        self.assertFalse(preset.edit_preset("kitty", "ghost"))

    def test_non_tty_hints_path(self):
        target = self.env.presets_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            self.assertFalse(preset.edit_preset("kitty", "mine"))

    def test_opens_editor_on_user_preset(self):
        target = self.env.presets_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        (target / "kitty.conf").write_text("# mine")
        with patch("sys.stdin.isatty", return_value=True), \
             patch.dict("os.environ", {"EDITOR": "myed"}), \
             patch.object(preset.subprocess, "run") as mock_run:
            self.assertTrue(preset.edit_preset("kitty", "mine"))
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], "myed")
        self.assertTrue(args[0][1].startswith("/proc/self/fd/"))
        self.assertEqual(kwargs["pass_fds"], (int(args[0][1].rsplit("/", 1)[1]),))
        self.assertFalse(kwargs["check"])

    def test_open_failure_closes_already_open_preset_dir(self):
        self.env.presets_dir.mkdir(parents=True, exist_ok=True)
        presets_fd = os.open(self.env.presets_dir, os.O_RDONLY | os.O_DIRECTORY)
        real_close = os.close
        with patch.object(preset, "_open_presets_dir", return_value=presets_fd), \
             patch.object(preset, "_open_child_dir", side_effect=OSError), \
             patch.object(preset.os, "close", wraps=real_close) as close:
            self.assertFalse(preset.edit_preset("kitty", "mine"))

        self.assertIn(((presets_fd,), {}), close.call_args_list)


class TestPresetStudioInspection(unittest.TestCase):
    """Tests for preset metadata inspection (get_preset_info)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_default_preset_info(self):
        info = preset.get_preset_info("kitty", "default")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "default")
        self.assertEqual(info.source, "official")
        self.assertFalse(info.is_editable)
        self.assertFalse(info.is_deletable)
        self.assertEqual(info.path, "configs/kitty")

    def test_official_preset_info(self):
        info = preset.get_preset_info("kitty", "transparent")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "transparent")
        self.assertEqual(info.source, "official")
        self.assertFalse(info.is_editable)
        self.assertFalse(info.is_deletable)
        self.assertEqual(info.path, "configs/kitty/presets/transparent")

    def test_user_preset_info(self):
        user_dir = self.env.presets_dir / "kitty" / "my-nord"
        user_dir.mkdir(parents=True)
        (user_dir / "kitty.conf").write_text("# my theme")

        info = preset.get_preset_info("kitty", "my-nord")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "my-nord")
        self.assertEqual(info.source, "user")
        self.assertTrue(info.is_editable)
        self.assertTrue(info.is_deletable)
        self.assertIn("kitty.conf", info.files)

    def test_invalid_info_never_loads_a_manifest(self):
        for app, name in (("../../outside", "default"), ("kitty", "../outside")):
            with self.subTest(app=app, name=name), \
                 patch("nyxniri.deploy.manifest.load_manifest_for") as load_manifest:
                info = preset.get_preset_info(app, name)

            self.assertEqual(info.path, "(invalid)")
            load_manifest.assert_not_called()


class TestPresetStudioActions(unittest.TestCase):
    """Tests for Preset Studio interactive actions via on_action callback."""

    def _run_keys(self, switcher, keys):
        fake_size = os.terminal_size((80, 24))
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.tui.read_key", side_effect=keys), \
             patch("shutil.get_terminal_size", return_value=fake_size), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def test_apply_action_triggered(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Applied {name}"

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("default", "official", True), ("transparent", "official", False)],
            on_action=on_action,
        )
        # RIGHT -> move to presets, DOWN -> transparent, ENTER -> apply, q -> quit
        self._run_keys(sw, ["RIGHT", "DOWN", "ENTER", "q"])
        self.assertEqual(actions, [("apply", "kitty", "transparent")])

    def test_save_action_triggered(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Saved {name}"

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("default", "official", True)],
            on_action=on_action,
        )
        # 's' triggers save prompt -> type 'm', 'i', 'n', 'e', ENTER -> q to quit
        self._run_keys(sw, ["s", "m", "i", "n", "e", "ENTER", "q"])
        self.assertEqual(actions, [("save", "kitty", "mine")])

    def test_delete_action_with_confirmation(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Deleted {name}"

        info_map = {
            ("kitty", "my-nord"): preset.PresetInfo(
                app="kitty", name="my-nord", source="user", is_active=False,
                path="~/.config/NyxNiri/presets/kitty/my-nord", files=[], preserve=[],
                is_editable=True, is_deletable=True
            )
        }

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("my-nord", "user", False)],
            info_for=lambda a, n: info_map.get((a, n)),
            on_action=on_action,
        )
        # RIGHT -> presets, 'd' -> delete, 'y' -> confirm, 'q' -> quit
        self._run_keys(sw, ["RIGHT", "d", "y", "q"])
        self.assertEqual(actions, [("delete", "kitty", "my-nord")])

    def test_delete_action_cancelled(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Deleted {name}"

        info_map = {
            ("kitty", "my-nord"): preset.PresetInfo(
                app="kitty", name="my-nord", source="user", is_active=False,
                path="~/.config/NyxNiri/presets/kitty/my-nord", files=[], preserve=[],
                is_editable=True, is_deletable=True
            )
        }

        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("my-nord", "user", False)],
            info_for=lambda a, n: info_map.get((a, n)),
            on_action=on_action,
        )
        # RIGHT -> presets, 'd' -> delete, 'n' -> cancel, 'q' -> quit
        self._run_keys(sw, ["RIGHT", "d", "n", "q"])
        self.assertEqual(actions, [])

    def test_tab_toggles_details(self):
        info_map = {
            ("kitty", "default"): preset.PresetInfo(
                app="kitty", name="default", source="official", is_active=True,
                path="configs/kitty", files=["kitty.conf"], preserve=["monitor.kdl"],
                is_editable=False, is_deletable=False
            )
        }
        sw = PresetSwitcher(
            apps=["kitty"],
            presets_for=lambda a: [("default", "official", True)],
            info_for=lambda a, n: info_map.get((a, n)),
        )
        # TAB expands, TAB collapses, q quits cleanly
        result = self._run_keys(sw, ["TAB", "TAB", "q"])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

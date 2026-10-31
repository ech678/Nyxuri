"""Contract tests for the form mechanism (R0-2 杀词并轨).

Covers: the four src-selection branches, dest-missing reset with
upstream-removed warning, ledger-single-truth writes with the legacy
``<app>.active`` adoption shim, __custom__ preservation across form
switches, slot axes, and the single apply path (replay included).
"""

import os
import subprocess
import tempfile
import tomllib
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import nyxuri.deploy.forms as forms
import nyxuri.desktop.forms as desktop_forms
import nyxuri.deploy.manifest as manifest
from nyxuri.deploy.atomic import atomic_replace_item
from nyxuri.tui import FormSwitcher
from nyxuri.core import msg
from tests.utils import TempEnv
import contextlib
import io
import sys




class TestActiveFormLedger(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_read_default_when_nothing_recorded(self):
        self.assertEqual(forms.read_active_form("kitty"), "default")

    def test_write_then_read(self):
        forms.write_active_form("kitty", "transparent")
        self.assertEqual(forms.read_active_form("kitty"), "transparent")

    def test_write_lands_in_ledger_record(self):
        from nyxuri.kernel.ledger import get_plugin
        forms.write_active_form("kitty", "transparent")
        self.assertEqual(get_plugin("kitty")["form"], "transparent")
        # never-switched choice: a disabled record, nothing archived
        rec = get_plugin("kitty")
        self.assertEqual(rec["state"], "disabled")
        self.assertIsNone(rec["vault"])

    def test_write_preserves_existing_record(self):
        from nyxuri.kernel.ledger import set_plugin, get_plugin
        set_plugin("kitty", state="enabled", files={"k.conf": "h1"})
        forms.write_active_form("kitty", "transparent")
        rec = get_plugin("kitty")
        self.assertEqual(rec["state"], "enabled")
        self.assertEqual(rec["form"], "transparent")
        self.assertEqual(rec["files"], {"k.conf": "h1"})

    def test_write_consumes_legacy_active_marker(self):
        marker = self._ctx.env.forms_dir / "kitty.active"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("transparent\n", encoding="utf-8")
        forms.write_active_form("kitty", "transparent")
        self.assertFalse(marker.exists(), "the retired marker must not survive a ledger write")

    def test_legacy_marker_is_adopted_on_sight(self):
        marker = self._ctx.env.forms_dir / "kitty.active"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("transparent", encoding="utf-8")
        self.assertEqual(forms.read_active_form("kitty"), "transparent")
        from nyxuri.kernel.ledger import get_plugin
        self.assertEqual(get_plugin("kitty")["form"], "transparent",
                         "adoption must land the choice in the ledger")
        self.assertFalse(marker.exists(), "adoption consumes the marker")

    def test_invalid_legacy_marker_is_ignored_not_fatal(self):
        """Ledger is the single truth: a garbage marker can no longer freeze."""
        marker = self._ctx.env.forms_dir / "kitty.active"
        marker.parent.mkdir(parents=True, exist_ok=True)
        for value in ("   \n", " transparent", "../victim"):
            with self.subTest(value=value):
                marker.write_text(value, encoding="utf-8")
                self.assertEqual(forms.read_active_form("kitty"), "default")

    def test_symlinked_legacy_marker_is_ignored(self):
        outside = self._ctx.home / "outside-active"
        outside.write_text("transparent", encoding="utf-8")
        marker = self._ctx.env.forms_dir / "kitty.active"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.symlink_to(outside)
        self.assertEqual(forms.read_active_form("kitty"), "default")
        self.assertEqual(outside.read_text(), "transparent")

    def test_write_rejects_invalid_app_and_name(self):
        with self.assertRaises(ValueError):
            forms.write_active_form("../../escaped", "mine")
        with self.assertRaises(ValueError):
            forms.write_active_form("kitty", "../victim")


class TestResolveFormSrc(unittest.TestCase):
    """The four src branches — parameter-shape contract on src path."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

        self.app = "kitty"
        self.app_root = self.env.plugins_src / self.app
        self.app_root.mkdir(parents=True)
        (self.app_root / "kitty.conf").write_text("# default")

        self.official = self.app_root / "__forms__" / "transparent"
        self.official.mkdir(parents=True)
        (self.official / "kitty.conf").write_text("# transparent")

        self.dest = self.env.config_dir / self.app

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_default_branch(self):
        r = forms.resolve_form_src(self.app, "default", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertIsNone(r.reset_form)
        self.assertEqual(r.warnings, [])

    def test_official_form_branch(self):
        self.dest.mkdir(parents=True)
        (self.dest / "old.conf").write_text("x")
        r = forms.resolve_form_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.official)
        self.assertIsNone(r.reset_form)

    def test_user_form_branch(self):
        self.dest.mkdir(parents=True)
        user_dir = self.env.forms_dir / self.app / "mine"
        user_dir.mkdir(parents=True)
        r = forms.resolve_form_src(self.app, "mine", self.dest)
        self.assertEqual(r.src, user_dir)

    def test_official_preferred_over_user_same_name(self):
        self.dest.mkdir(parents=True)
        (self.env.forms_dir / self.app / "transparent").mkdir(parents=True)
        r = forms.resolve_form_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.official)

    def test_not_found_freezes_dest(self):
        # form = ghost, dest exists → src None (freeze), warning. Do NOT
        # fall back to default (would silently wipe the user's config).
        self.dest.mkdir(parents=True)
        r = forms.resolve_form_src(self.app, "ghost", self.dest)
        self.assertIsNone(r.src)
        self.assertTrue(r.warnings)

    def test_dest_missing_resets_to_default(self):
        # dest absent + form=transparent (still upstream) → default, no extra warning
        r = forms.resolve_form_src(self.app, "transparent", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertEqual(r.reset_form, "default")
        self.assertEqual(r.warnings, [])

    def test_dest_missing_and_upstream_removed_warns(self):
        # dest absent + form=ghost (gone upstream) → default + extra warning
        r = forms.resolve_form_src(self.app, "ghost", self.dest)
        self.assertEqual(r.src, self.app_root)
        self.assertEqual(r.reset_form, "default")
        self.assertTrue(r.warnings)


class TestCustomSurvivesFormSwitch(unittest.TestCase):
    """__custom__ files survive form switches (Dunder + copytree-ignore compat)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_custom_file_retained_across_two_forms(self):
        app = "kitty"
        root = self.env.plugins_src / app
        root.mkdir(parents=True)
        transparent = root / "__forms__" / "transparent"
        transparent.mkdir(parents=True)
        (transparent / "kitty.conf").write_text("# transparent")
        compact = root / "__forms__" / "compact"
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

    def test_manifest_not_shipped_to_dest(self):
        # §10.4 boundary: manifest.toml is repo metadata, must not land in dest.
        app = "kitty"
        root = self.env.plugins_src / app
        root.mkdir(parents=True)
        (root / "kitty.conf").write_text("# conf")
        (root / "manifest.toml").write_text('packages = ["kitty"]\n')
        dest = self.env.config_dir / app
        atomic_replace_item(root, dest)
        self.assertFalse((dest / "manifest.toml").exists())
        # The real kitty.conf did ship.
        self.assertTrue((dest / "kitty.conf").exists())

    def test_forms_dir_not_shipped_to_dest(self):
        # __forms__/ stays in repo, not deployed into ~/.config/<app>/__forms__/
        app = "kitty"
        root = self.env.plugins_src / app
        root.mkdir(parents=True)
        (root / "kitty.conf").write_text("# conf")
        (root / "__forms__" / "transparent").mkdir(parents=True)
        (root / "__forms__" / "transparent" / "kitty.conf").write_text("# t")
        dest = self.env.config_dir / app
        atomic_replace_item(root, dest)
        self.assertFalse((dest / "__forms__").exists())


class TestFormOperations(unittest.TestCase):
    """use/save/delete against the real repo's kitty + transparent demo."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_list_marks_active_default(self):
        entries = desktop_forms.list_forms("kitty")
        names = [n for n, _, _ in entries]
        self.assertIn("default", names)
        self.assertIn("transparent", names)  # the shipped demo form
        active_entry = [e for e in entries if e[2]]
        self.assertEqual(len(active_entry), 1)
        self.assertEqual(active_entry[0][0], "default")  # fresh = default

    def test_use_transparent_writes_form_and_deploys_variant(self):
        ok = desktop_forms.apply_form("kitty", "transparent")
        self.assertTrue(ok)
        self.assertEqual(forms.read_active_form("kitty"), "transparent")
        conf = self.env.config_dir / "kitty" / "kitty.conf"
        self.assertTrue(conf.is_file())
        self.assertIn("0.75", conf.read_text())  # the transparent variant

    def test_list_includes_niri_slot_axes(self):
        entries = desktop_forms.collect_forms("niri")
        names = [n for n, _, _ in entries]
        self.assertEqual(names, ["default"])

        slots = forms.list_slots("niri")
        self.assertIn("effects", slots)
        self.assertEqual(set(slots["effects"]["variants"]), {"default", "xray-blur"})
        self.assertIn("glow", slots)
        self.assertEqual(set(slots["glow"]["variants"]), {"default", "glow", "glow-material-you"})

    def test_apply_niri_glow_sparse_overlay_end_to_end(self):
        ok = forms.use_form("niri", "glow", "glow")
        self.assertTrue(ok)
        self.assertEqual(forms.get_active_slot("niri", "glow"), "glow")

        glow_file = self.env.config_dir / "niri" / "glow.kdl"
        self.assertTrue(glow_file.is_file())
        content = glow_file.read_text(encoding="utf-8")
        self.assertIn("width 2", content)
        self.assertIn("shadow", content)

    def test_apply_niri_glow_material_you_sets_sentinel(self):
        self.assertTrue(forms.use_form("niri", "glow", "glow-material-you"))
        self.assertEqual(forms.get_active_slot("niri", "glow"), "glow-material-you")
        glow_file = self.env.config_dir / "niri" / "glow.kdl"
        self.assertTrue(glow_file.is_file())
        content = glow_file.read_text(encoding="utf-8")
        self.assertIn('include optional=true "colors.kdl"', content)
        self.assertNotIn("#1a73e8", content)

        self.assertTrue(forms.use_form("niri", "glow", "default"))
        self.assertEqual(forms.get_active_slot("niri", "glow"), "default")
        def_content = glow_file.read_text(encoding="utf-8")
        self.assertIn("off", def_content)
        self.assertNotIn("colors.kdl", def_content)

    def test_niri_glow_material_you_template_is_dynamic(self):
        template = self.env.plugins_src / "theme" / "niri-glow-material-you.kdl"
        content = template.read_text(encoding="utf-8")
        self.assertIn("{{ colors.primary.default.hex }}", content)
        self.assertIn("{{ colors.error.default.hex }}", content)
        self.assertIn("{{ colors.primary_container.default.hex }}", content)
        self.assertNotIn("#1a73e8", content)
        noctalia = (self.env.plugins_src / "noctalia" / "noctalia-config.toml").read_text(encoding="utf-8")
        self.assertIn('output_path = "/home/user/.config/niri/colors.kdl"', noctalia)
        self.assertNotIn('output_path = "/home/user/.config/niri/layout.kdl"', noctalia)
        parsed = tomllib.loads(noctalia)
        niri_tpl = parsed.get("theme", {}).get("templates", {}).get("user", {}).get("nyxuri_niri_glow_material_you", {})
        self.assertNotIn("post_hook", niri_tpl)

    @unittest.mock.patch("nyxuri.deploy.forms.timed_run")
    def test_apply_niri_glow_material_you_has_no_daemon_side_effect(self, mock_timed_run):
        with patch("shutil.which", side_effect=lambda command: f"/usr/bin/{command}"):
            self.assertTrue(forms.use_form("niri", "glow", "glow-material-you"))

        mock_timed_run.assert_not_called()

    @unittest.mock.patch("nyxuri.deploy.forms.timed_run")
    @unittest.mock.patch("shutil.which", return_value="/usr/bin/niri")
    def test_apply_form_niri_has_no_daemon_side_effect(self, mock_which, mock_timed_run):
        ok = forms.use_form("niri", "glow", "glow")
        self.assertTrue(ok)
        mock_timed_run.assert_not_called()

    @unittest.mock.patch("nyxuri.deploy.forms.timed_run")
    @unittest.mock.patch("shutil.which", return_value="/usr/bin/pkill")
    def test_apply_form_kitty_reloads(self, mock_which, mock_timed_run):
        ok = desktop_forms.apply_form("kitty", "transparent")
        self.assertTrue(ok)
        mock_timed_run.assert_called_with(
            ["pkill", "-SIGUSR1", "-x", "kitty"],
            2,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def test_apply_default_resets(self):
        forms.write_active_form("kitty", "transparent")
        ok = desktop_forms.apply_form("kitty", "default")
        self.assertTrue(ok)
        self.assertEqual(forms.read_active_form("kitty"), "default")

    def test_apply_unknown_form_fails_without_writing(self):
        # Nonexistent form: fail, do not touch the ledger choice.
        forms.write_active_form("kitty", "transparent")
        ok = desktop_forms.apply_form("kitty", "ghost")
        self.assertFalse(ok)
        self.assertEqual(forms.read_active_form("kitty"), "transparent")

    def test_apply_then_write_timing_atomic_fail_leaves_form(self):
        # If atomic_replace fails, the choice must NOT be written.
        forms.write_active_form("kitty", "default")
        with patch("nyxuri.deploy.atomic.atomic_replace_item", return_value=False):
            ok = desktop_forms.apply_form("kitty", "transparent")
        self.assertFalse(ok)
        # form still default — deploy-then-write held back the write.
        self.assertEqual(forms.read_active_form("kitty"), "default")

    def test_save_rejects_reserved_default(self):
        # Set up a dest so the rejection is specifically the name, not the empty dest.
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# conf")
        self.assertFalse(desktop_forms.save_form("kitty", "default"))

    def test_save_rejects_official_name_collision(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# conf")
        # 'transparent' is an official form — collision must be rejected.
        self.assertFalse(desktop_forms.save_form("kitty", "transparent"))

    def test_save_snapshots_tree_minus_custom(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# my conf")
        (dest / "__custom__.conf").write_text("# private")
        custom_dir = dest / "__custom__"
        custom_dir.mkdir()
        (custom_dir / "extra.conf").write_text("# nested custom")

        self.assertTrue(desktop_forms.save_form("kitty", "mine"))
        target = self.env.forms_dir / "kitty" / "mine"
        self.assertTrue((target / "kitty.conf").is_file())
        # __custom__ entries filtered out (both file and dir).
        self.assertFalse((target / "__custom__.conf").exists())
        self.assertFalse((target / "__custom__").exists())

    def test_save_then_apply_user_form(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# my flavor")
        self.assertTrue(desktop_forms.save_form("kitty", "mine"))
        # Wipe dest, then re-apply the saved user form.
        import shutil
        shutil.rmtree(dest)
        self.assertTrue(desktop_forms.apply_form("kitty", "mine"))
        self.assertEqual(forms.read_active_form("kitty"), "mine")
        self.assertEqual((dest / "kitty.conf").read_text(), "# my flavor")

    def test_delete_user_form(self):
        target = self.env.forms_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        (target / "kitty.conf").write_text("# x")
        self.assertTrue(desktop_forms.delete_form("kitty", "mine"))
        self.assertFalse(target.exists())

    def test_delete_rejects_default_and_official(self):
        self.assertFalse(desktop_forms.delete_form("kitty", "default"))
        self.assertFalse(desktop_forms.delete_form("kitty", "transparent"))

    def test_delete_active_form_resets_to_default(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("# base")
        self.assertTrue(desktop_forms.save_form("kitty", "mine"))
        self.assertTrue(desktop_forms.apply_form("kitty", "mine"))
        self.assertEqual(forms.read_active_form("kitty"), "mine")
        self.assertTrue(desktop_forms.delete_form("kitty", "mine"))
        self.assertEqual(forms.read_active_form("kitty"), "default")

    def test_save_forms_open_failure_closes_source_fd(self):
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

        with patch.object(desktop_forms.os, "open", side_effect=track_source_open), \
             patch.object(desktop_forms, "_open_forms_dir", side_effect=OSError), \
             patch.object(desktop_forms.os, "close", wraps=os.close) as close:
            self.assertFalse(desktop_forms.save_form("kitty", "mine"))

        self.assertIsNotNone(source_fd)
        self.assertTrue(any(call.args == (source_fd,) for call in close.call_args_list))


class TestApplyNarrowPath(unittest.TestCase):
    """Use runs only atomic_replace + render, without post-install services."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_apply_skips_post_install_services(self):
        with patch("nyxuri.deploy.deploy._phase_post_install_services") as svc:
            ok = desktop_forms.apply_form("kitty", "transparent")
        self.assertTrue(ok)
        svc.assert_not_called()


class TestFormSwitchPreservesManifestFiles(unittest.TestCase):
    """The narrow deploy path honours the manifest ``preserve`` list.

    Regression guard: applying a form must not wipe runtime-managed files the
    new variant doesn't ship — specifically niri/effects.kdl (a symlink whose
    target encodes EyeCare on/off) and niri/monitor.kdl (user-generated). Both
    are declared in niri/manifest.toml preserve and must survive a switch.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.niri_dest = self.env.config_dir / "niri"
        # Deploy niri defaults first so monitor.kdl + effects_*.kdl exist.
        from nyxuri.deploy.atomic import atomic_replace_item
        atomic_replace_item(self.env.plugins_src / "niri", self.niri_dest)
        # The repo ships effects.kdl as a symlink; recreate it only when the
        # variant under test dropped it, so the runtime link state is present.
        effects_normal = self.niri_dest / "effects_normal.kdl"
        self.effects_sym = self.niri_dest / "effects.kdl"
        if not self.effects_sym.is_symlink():
            self.effects_sym.symlink_to(effects_normal)
        # Mark monitor.kdl so we can detect a wipe.
        self.monitor = self.niri_dest / "monitor.kdl"
        with self.monitor.open("a") as f:
            f.write("# USER-MARKER\n")

    def tearDown(self):
        self._ctx.__exit__()

    def test_effects_kdl_symlink_survives_form_switch(self):
        self.assertTrue(desktop_forms.apply_form("niri", "default"))
        self.assertTrue(self.effects_sym.is_symlink(), "effects.kdl symlink was wiped")
        self.assertIn("effects_normal.kdl", os.readlink(self.effects_sym))

    def test_monitor_kdl_survives_form_switch(self):
        self.assertTrue(desktop_forms.apply_form("niri", "default"))
        self.assertIn("# USER-MARKER", self.monitor.read_text())

    def test_effects_normal_kdl_survives_form_switch(self):
        normal_file = self.niri_dest / "effects_normal.kdl"
        normal_file.write_text("// USER-EFFECTS-MARKER\n")
        self.assertTrue(desktop_forms.apply_form("niri", "default"))
        self.assertIn("// USER-EFFECTS-MARKER", normal_file.read_text())


class TestKittyRuntimeThemeSurvivesFormSwitch(unittest.TestCase):
    """Kitty's palette is rendered at runtime; a form switch must not reset it.

    Noctalia owns ~/.config/kitty/themes/noctalia.conf (dark/light following the
    wallpaper). The repo also ships a static copy in both the app root and the
    transparent variant, so a switch would clobber the rendered palette unless
    the manifest preserves it.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.kitty_dest = self.env.config_dir / "kitty"
        from nyxuri.deploy.atomic import atomic_replace_item
        atomic_replace_item(self.env.plugins_src / "kitty", self.kitty_dest)

    def tearDown(self):
        self._ctx.__exit__()

    def test_manifest_preserves_runtime_theme_files(self):
        m = manifest.load_manifest(self.env.plugins_src / "kitty")
        self.assertIn("current-theme.conf", m.preserve)
        self.assertIn("themes/noctalia.conf", m.preserve)

    def test_rendered_palette_survives_form_switch(self):
        theme = self.kitty_dest / "themes" / "noctalia.conf"
        rendered = theme.read_text(encoding="utf-8").replace("#131318", "#f5f0f7")
        theme.write_text(rendered, encoding="utf-8")

        self.assertTrue(desktop_forms.apply_form("kitty", "transparent"))
        self.assertIn("#f5f0f7", theme.read_text(encoding="utf-8"),
                      "form switch wiped the runtime-rendered palette")

        self.assertTrue(desktop_forms.apply_form("kitty", "default"))
        self.assertIn("#f5f0f7", theme.read_text(encoding="utf-8"))

    def test_theme_symlink_still_points_at_noctalia(self):
        link = self.kitty_dest / "current-theme.conf"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "themes/noctalia.conf")
        self.assertTrue(desktop_forms.apply_form("kitty", "transparent"))
        self.assertTrue(link.is_symlink(), "current-theme.conf symlink was wiped")
        self.assertEqual(os.readlink(link), "themes/noctalia.conf")


class TestFormPathBoundary(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_traversal_is_rejected_before_delete_or_form_write(self):
        victim = self.env.forms_dir / "victim"
        victim.mkdir(parents=True)
        sentinel = victim / "sentinel"
        sentinel.write_text("keep")

        self.assertFalse(desktop_forms.delete_form("kitty", "../victim"))
        with self.assertRaises(ValueError):
            forms.write_active_form("../../escaped", "mine")

        self.assertEqual(sentinel.read_text(), "keep")

    def test_every_operation_rejects_absolute_and_dot_components(self):
        absolute = str(self._ctx.home / "outside")
        for name in ("../victim", absolute, ".", ".."):
            with self.subTest(name=name), \
                 patch("nyxuri.deploy.atomic.atomic_replace_item") as replace, \
                 patch.object(forms.subprocess, "run") as run:
                self.assertFalse(desktop_forms.apply_form("kitty", name))
                self.assertFalse(desktop_forms.save_form("kitty", name))
                self.assertFalse(desktop_forms.delete_form("kitty", name))
                self.assertFalse(desktop_forms.edit_form("kitty", name))
                with self.assertRaises(ValueError):
                    forms.write_active_form("kitty", name)
                replace.assert_not_called()
                run.assert_not_called()

        self.assertFalse(desktop_forms.apply_form("../outside", "default"))
        with self.assertRaises(ValueError):
            forms.write_active_form("../outside", "mine")

    def test_symlinked_user_form_never_starts_editor(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        user_root = self.env.forms_dir / "kitty"
        user_root.mkdir(parents=True)
        (user_root / "mine").symlink_to(outside, target_is_directory=True)

        with patch("sys.stdin.isatty", return_value=True), \
             patch.object(forms.subprocess, "run") as run:
            self.assertFalse(desktop_forms.edit_form("kitty", "mine"))

        run.assert_not_called()

    def test_symlinked_user_form_is_never_applied_or_deleted(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        user_root = self.env.forms_dir / "kitty"
        user_root.mkdir(parents=True)
        (user_root / "mine").symlink_to(outside, target_is_directory=True)

        with patch("nyxuri.deploy.atomic.atomic_replace_item") as replace:
            self.assertFalse(desktop_forms.apply_form("kitty", "mine"))
        self.assertFalse(desktop_forms.delete_form("kitty", "mine"))

        replace.assert_not_called()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_symlinked_config_target_is_rejected_before_apply(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("keep")
        (self.env.config_dir / "kitty").symlink_to(outside, target_is_directory=True)

        with patch("nyxuri.deploy.atomic.atomic_replace_item") as replace:
            self.assertFalse(desktop_forms.apply_form("kitty", "default"))

        replace.assert_not_called()
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_symlinked_config_target_is_rejected_before_save(self):
        outside = self._ctx.home / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        (self.env.config_dir / "kitty").symlink_to(outside, target_is_directory=True)

        self.assertFalse(desktop_forms.save_form("kitty", "mine"))

        self.assertEqual(sentinel.read_text(), "keep")

    def test_unicode_leaf_name_remains_usable(self):
        dest = self.env.config_dir / "kitty"
        dest.mkdir(parents=True)
        (dest / "kitty.conf").write_text("current")
        name = "主题 浅色"

        self.assertTrue(desktop_forms.save_form("kitty", name))
        self.assertTrue(desktop_forms.apply_form("kitty", name))
        self.assertTrue(desktop_forms.delete_form("kitty", name))

    def test_delete_rejects_directory_swap_after_lookup(self):
        user_root = self.env.forms_dir / "kitty"
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

        with patch("nyxuri.desktop.forms.os.open", side_effect=open_then_swap):
            self.assertFalse(desktop_forms.delete_form("kitty", "mine"))

        self.assertTrue(swapped)
        self.assertEqual((mine / "sentinel").read_text(), "keep")


class TestFormSwitcher(unittest.TestCase):
    """Form Switcher interactive tests via a mocked key stream."""

    def _run_keys(self, switcher, keys):
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxuri.tui.read_key", side_effect=keys), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def test_enter_returns_app_and_form(self):
        sw = FormSwitcher(["kitty"], lambda a: [("default", "official", True), ("transparent", "user", False)])
        # RIGHT → expand kitty & land on default; DOWN → transparent; ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "DOWN", "ENTER"]), ("kitty", "transparent"))

    def test_pane_switch_keeps_app_cursor(self):
        apps = ["fastfetch", "kitty"]
        forms_kitty = [("default", "official", True), ("transparent", "user", False)]
        sw = FormSwitcher(apps, lambda a: forms_kitty if a == "kitty" else [("default", "official", True)])
        # DOWN→app kitty; RIGHT→expand; LEFT→back to app kitty; RIGHT→focus forms; DOWN; ENTER
        self.assertEqual(
            self._run_keys(sw, ["DOWN", "RIGHT", "LEFT", "RIGHT", "DOWN", "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_up_down_cycles_in_pane(self):
        sw = FormSwitcher(["kitty"], lambda a: [("default", "official", True), ("transparent", "user", False), ("compact", "user", False)])
        # RIGHT; DOWN; DOWN; ENTER
        self.assertEqual(self._run_keys(sw, ["RIGHT", "DOWN", "DOWN", "ENTER"]), ("kitty", "compact"))

    def test_app_switch_lands_cursor_on_active_form(self):
        apps = ["fastfetch", "kitty"]
        forms_kitty = [("default", "official", False), ("transparent", "user", True)]  # transparent is active
        sw = FormSwitcher(apps, lambda a: forms_kitty if a == "kitty" else [("default", "official", True)])
        # DOWN→kitty; RIGHT→expand kitty; ENTER applies active transparent directly
        self.assertEqual(self._run_keys(sw, ["DOWN", "RIGHT", "ENTER"]), ("kitty", "transparent"))

    def test_cancel_returns_none(self):
        sw = FormSwitcher(["kitty"], lambda a: [("default", "official", True)])
        self.assertIsNone(self._run_keys(sw, ["q"]))

    def test_no_tty_returns_none(self):
        sw = FormSwitcher(["kitty"], lambda a: [("default", "official", True)])
        with patch("sys.stdin.isatty", return_value=False):
            self.assertIsNone(sw.run())

    def test_slots_keyboard_navigation_and_selection(self):
        slots_data = {
            "effects": {
                "desc": "Window effects",
                "target": "effects_normal.kdl",
                "default": "default",
                "variants": ["default", "xray-blur"],
            }
        }
        sw = FormSwitcher(
            apps=["niri"],
            forms_for=lambda a: [("default", "official", True)],
            slots_for=lambda a: slots_data if a == "niri" else {},
            active_slot_for=lambda a, slot: "default",
        )
        self.assertEqual(
            self._run_keys(sw, ["RIGHT", "DOWN", "RIGHT", "DOWN", "ENTER"]),
            ("niri", "effects:xray-blur"),
        )

    def test_slots_action_callback(self):
        slots_data = {
            "effects": {
                "desc": "Window effects",
                "target": "effects_normal.kdl",
                "default": "default",
                "variants": ["default", "xray-blur"],
            }
        }
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return "ok"

        sw = FormSwitcher(
            apps=["niri"],
            forms_for=lambda a: [("default", "official", True)],
            slots_for=lambda a: slots_data,
            active_slot_for=lambda a, slot: "default",
            on_action=on_action,
        )
        self._run_keys(sw, ["RIGHT", "DOWN", "RIGHT", "DOWN", "ENTER", "q"])
        self.assertEqual(actions, [("apply_slot", "niri", "effects:xray-blur")])

    def test_slots_left_arrow_navigation(self):
        slots_data = {
            "effects": {
                "desc": "Window effects",
                "target": "effects_normal.kdl",
                "default": "default",
                "variants": ["default", "xray-blur"],
            }
        }
        sw = FormSwitcher(
            apps=["niri"],
            forms_for=lambda a: [("default", "official", True)],
            slots_for=lambda a: slots_data,
            active_slot_for=lambda a, slot: "default",
        )
        self.assertEqual(
            self._run_keys(sw, ["RIGHT", "DOWN", "RIGHT", "LEFT", "LEFT", "LEFT", "ENTER"]),
            ("niri", "default"),
        )


class TestFormSwitcherMouse(unittest.TestCase):
    """Mouse interaction: click selects/expands, wheel scrolls."""

    def _run_keys(self, switcher, keys):
        import os
        import nyxuri.tui as tui
        fake_size = os.terminal_size((80, 24))
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxuri.tui.read_key", side_effect=keys), \
             patch.object(tui.shutil, "get_terminal_size", return_value=fake_size), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def _click(self, col, row):
        from nyxuri.tui import MouseEvent
        return MouseEvent(kind="PRESS", col=col, row=row)

    def _wheel(self, kind, col=3, row=15):
        from nyxuri.tui import MouseEvent
        return MouseEvent(kind=kind, col=col, row=row)

    def test_click_app_applies_active_form_in_standalone_mode(self):
        sw = FormSwitcher(["kitty"], lambda a: [("default", "official", True), ("transparent", "user", False)])
        # Click kitty at row 15 -> returns ("kitty", "default")
        self.assertEqual(self._run_keys(sw, [self._click(10, 14)]), ("kitty", "default"))

    def test_wheel_down_cycles_app(self):
        sw = FormSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", "official", True)] if a == "fastfetch" else [("transparent", "user", True)],
        )
        # wheel-down -> fastfetch to kitty; Enter applies kitty/transparent.
        self.assertEqual(
            self._run_keys(sw, [self._wheel("WHEEL_DOWN"), "ENTER"]),
            ("kitty", "transparent"),
        )

    def test_wheel_up_cycles_backwards(self):
        sw = FormSwitcher(
            ["fastfetch", "kitty"],
            lambda a: [("default", "official", True)] if a == "fastfetch" else [("transparent", "user", True)],
        )
        # DOWN to kitty first, then WHEEL_UP back to fastfetch, Enter -> fastfetch/default.
        self.assertEqual(
            self._run_keys(sw, ["DOWN", self._wheel("WHEEL_UP"), "ENTER"]),
            ("fastfetch", "default"),
        )

    def test_click_on_header_row_is_ignored(self):
        sw = FormSwitcher(["kitty"], lambda a: [("default", "official", True)])
        self.assertEqual(self._run_keys(sw, [self._click(40, 12), "ENTER"]), ("kitty", "default"))


class TestEditForm(unittest.TestCase):
    """edit_form: rejects default/official/missing; opens editor on a user form."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_rejects_default(self):
        self.assertFalse(desktop_forms.edit_form("kitty", "default"))

    def test_rejects_official(self):
        # 'transparent' is a shipped official form — read-only.
        self.assertFalse(desktop_forms.edit_form("kitty", "transparent"))

    def test_rejects_missing(self):
        self.assertFalse(desktop_forms.edit_form("kitty", "ghost"))

    def test_non_tty_hints_path(self):
        target = self.env.forms_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"):
            self.assertFalse(desktop_forms.edit_form("kitty", "mine"))

    def test_opens_editor_on_user_form(self):
        target = self.env.forms_dir / "kitty" / "mine"
        target.mkdir(parents=True)
        (target / "kitty.conf").write_text("# mine")
        with patch("sys.stdin.isatty", return_value=True), \
             patch.dict("os.environ", {"EDITOR": "myed"}), \
             patch.object(forms.subprocess, "run") as mock_run:
            self.assertTrue(desktop_forms.edit_form("kitty", "mine"))
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], "myed")
        self.assertTrue(args[0][1].startswith("/proc/self/fd/"))
        self.assertEqual(kwargs["pass_fds"], (int(args[0][1].rsplit("/", 1)[1]),))
        self.assertFalse(kwargs["check"])

    def test_open_failure_closes_already_open_form_dir(self):
        self.env.forms_dir.mkdir(parents=True, exist_ok=True)
        forms_fd = os.open(self.env.forms_dir, os.O_RDONLY | os.O_DIRECTORY)
        real_close = os.close
        with patch.object(desktop_forms, "_open_forms_dir", return_value=forms_fd), \
             patch.object(desktop_forms, "_open_child_dir", side_effect=OSError), \
             patch.object(desktop_forms.os, "close", wraps=real_close) as close:
            self.assertFalse(desktop_forms.edit_form("kitty", "mine"))

        self.assertIn(((forms_fd,), {}), close.call_args_list)


class TestFormStudioInspection(unittest.TestCase):
    """Tests for form metadata inspection (get_form_info)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_default_form_info(self):
        info = desktop_forms.get_form_info("kitty", "default")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "default")
        self.assertEqual(info.source, "official")
        self.assertFalse(info.is_editable)
        self.assertFalse(info.is_deletable)
        self.assertEqual(info.path, "configs/kitty")

    def test_official_form_info(self):
        info = desktop_forms.get_form_info("kitty", "transparent")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "transparent")
        self.assertEqual(info.source, "official")
        self.assertFalse(info.is_editable)
        self.assertFalse(info.is_deletable)
        self.assertEqual(info.path, "configs/kitty/__forms__/transparent")

    def test_user_form_info(self):
        user_dir = self.env.forms_dir / "kitty" / "my-nord"
        user_dir.mkdir(parents=True)
        (user_dir / "kitty.conf").write_text("# my theme")

        info = desktop_forms.get_form_info("kitty", "my-nord")
        self.assertEqual(info.app, "kitty")
        self.assertEqual(info.name, "my-nord")
        self.assertEqual(info.source, "user")
        self.assertTrue(info.is_editable)
        self.assertTrue(info.is_deletable)
        self.assertIn("kitty.conf", info.files)

    def test_invalid_info_never_loads_a_manifest(self):
        for app, name in (("../../outside", "default"), ("kitty", "../outside")):
            with self.subTest(app=app, name=name), \
                 patch("nyxuri.deploy.manifest.load_manifest_for") as load_manifest:
                info = desktop_forms.get_form_info(app, name)

            self.assertEqual(info.path, "(invalid)")
            load_manifest.assert_not_called()


class TestFormStudioActions(unittest.TestCase):
    """Tests for Form Studio interactive actions via on_action callback."""

    def _run_keys(self, switcher, keys):
        fake_size = os.terminal_size((80, 24))
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxuri.tui.read_key", side_effect=keys), \
             patch("shutil.get_terminal_size", return_value=fake_size), \
             patch("sys.stdout", new_callable=StringIO):
            return switcher.run()

    def test_apply_action_triggered(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Applied {name}"

        sw = FormSwitcher(
            apps=["kitty"],
            forms_for=lambda a: [("default", "official", True), ("transparent", "official", False)],
            on_action=on_action,
        )
        # RIGHT -> move to forms, DOWN -> transparent, ENTER -> apply, q -> quit
        self._run_keys(sw, ["RIGHT", "DOWN", "ENTER", "q"])
        self.assertEqual(actions, [("apply", "kitty", "transparent")])

    def test_save_action_triggered(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Saved {name}"

        sw = FormSwitcher(
            apps=["kitty"],
            forms_for=lambda a: [("default", "official", True)],
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
            ("kitty", "my-nord"): desktop_forms.FormInfo(
                app="kitty", name="my-nord", source="user", is_active=False,
                path="~/.config/nyxuri/forms/kitty/my-nord", files=[], preserve=[],
                is_editable=True, is_deletable=True
            )
        }

        sw = FormSwitcher(
            apps=["kitty"],
            forms_for=lambda a: [("my-nord", "user", False)],
            info_for=lambda a, n: info_map.get((a, n)),
            on_action=on_action,
        )
        # RIGHT -> forms, 'd' -> delete, 'y' -> confirm, 'q' -> quit
        self._run_keys(sw, ["RIGHT", "d", "y", "q"])
        self.assertEqual(actions, [("delete", "kitty", "my-nord")])

    def test_delete_action_cancelled(self):
        actions = []
        def on_action(action, app, name):
            actions.append((action, app, name))
            return f"Deleted {name}"

        info_map = {
            ("kitty", "my-nord"): desktop_forms.FormInfo(
                app="kitty", name="my-nord", source="user", is_active=False,
                path="~/.config/nyxuri/forms/kitty/my-nord", files=[], preserve=[],
                is_editable=True, is_deletable=True
            )
        }

        sw = FormSwitcher(
            apps=["kitty"],
            forms_for=lambda a: [("my-nord", "user", False)],
            info_for=lambda a, n: info_map.get((a, n)),
            on_action=on_action,
        )
        # RIGHT -> forms, 'd' -> delete, 'n' -> cancel, 'q' -> quit
        self._run_keys(sw, ["RIGHT", "d", "n", "q"])
        self.assertEqual(actions, [])

    def test_tab_toggles_details(self):
        info_map = {
            ("kitty", "default"): desktop_forms.FormInfo(
                app="kitty", name="default", source="official", is_active=True,
                path="configs/kitty", files=["kitty.conf"], preserve=["monitor.kdl"],
                is_editable=False, is_deletable=False
            )
        }
        sw = FormSwitcher(
            apps=["kitty"],
            forms_for=lambda a: [("default", "official", True)],
            info_for=lambda a, n: info_map.get((a, n)),
        )
        # TAB expands, TAB collapses, q quits cleanly
        result = self._run_keys(sw, ["TAB", "TAB", "q"])
        self.assertIsNone(result)


class TestFormInheritance(unittest.TestCase):
    """Form inheritance, whitelists, blacklists, and base overlay deployment."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

        self.app = "niri_test"
        self.app_root = self.env.plugins_src / self.app
        self.app_root.mkdir(parents=True)
        (self.app_root / "config.kdl").write_text("// base config")
        (self.app_root / "layout.kdl").write_text("// base layout")
        (self.app_root / "binds.kdl").write_text("// base binds")
        (self.app_root / "scripts").mkdir(parents=True)
        (self.app_root / "scripts" / "run.sh").write_text("#!/bin/sh\necho ok")
        (self.app_root / "scripts" / "debug.bak").write_text("bak")
        (self.app_root / "unwanted.txt").write_text("skip me")

        # Create sparse form 'glow'
        self.sparse = self.app_root / "__forms__" / "glow"
        self.sparse.mkdir(parents=True)
        (self.sparse / "layout.kdl").write_text("// glow layout")

        # Create standalone form 'isolated'
        self.isolated = self.app_root / "__forms__" / "isolated"
        self.isolated.mkdir(parents=True)
        (self.isolated / "isolated.kdl").write_text("// isolated only")

        self.dest = self.env.config_dir / self.app

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_inheritance_not_enabled_by_default(self):
        base_src, inc, exc = forms.resolve_form_inheritance(self.app, "glow")
        self.assertIsNone(base_src)
        self.assertEqual(inc, [])
        self.assertEqual(exc, [])

    def test_inheritance_allow_whitelist(self):
        (self.app_root / "manifest.toml").write_text("""
[forms]
allow = ["glow"]
include = ["scripts/**", "*.kdl"]
exclude = ["*.bak"]
""")
        # 'glow' is allowed -> should inherit with whitelists/blacklists
        base_src, inc, exc = forms.resolve_form_inheritance(self.app, "glow")
        self.assertEqual(base_src, self.app_root)
        self.assertEqual(inc, ["scripts/**", "*.kdl"])
        self.assertEqual(exc, ["*.bak"])

        # 'other' is not in allow -> should not inherit
        base_src_other, _, _ = forms.resolve_form_inheritance(self.app, "other")
        self.assertIsNone(base_src_other)

    def test_inheritance_standalone_blacklist(self):
        (self.app_root / "manifest.toml").write_text("""
[forms]
inherit = true
standalone = ["isolated"]
""")
        base_src, _, _ = forms.resolve_form_inheritance(self.app, "glow")
        self.assertEqual(base_src, self.app_root)

        base_src_iso, _, _ = forms.resolve_form_inheritance(self.app, "isolated")
        self.assertIsNone(base_src_iso)

    def test_inheritance_simultaneous_whitelist_and_blacklist(self):
        (self.app_root / "manifest.toml").write_text("""
[forms]
allow = ["style-*"]
standalone = ["style-dark"]
include = ["scripts/**", "*.kdl"]
exclude = ["scripts/debug.bak"]
""")
        # 1. Matches allow and not standalone -> inherits
        base_src, inc, exc = forms.resolve_form_inheritance(self.app, "style-light")
        self.assertEqual(base_src, self.app_root)
        self.assertEqual(inc, ["scripts/**", "*.kdl"])
        self.assertEqual(exc, ["scripts/debug.bak"])

        # 2. Matches allow BUT also matches standalone -> standalone vetoes -> does NOT inherit
        base_src_veto, _, _ = forms.resolve_form_inheritance(self.app, "style-dark")
        self.assertIsNone(base_src_veto)

        # 3. Does not match allow -> does NOT inherit
        base_src_none, _, _ = forms.resolve_form_inheritance(self.app, "other")
        self.assertIsNone(base_src_none)

    def test_atomic_replace_item_base_overlay_filtering(self):
        ok = atomic_replace_item(
            src=self.sparse,
            dest=self.dest,
            base_src=self.app_root,
            base_include=["scripts/**", "*.kdl"],
            base_exclude=["*.bak"],
        )
        self.assertTrue(ok)
        # 1. Overridden file from the form
        self.assertEqual((self.dest / "layout.kdl").read_text(), "// glow layout")
        # 2. Inherited base files
        self.assertEqual((self.dest / "config.kdl").read_text(), "// base config")
        self.assertEqual((self.dest / "binds.kdl").read_text(), "// base binds")
        self.assertTrue((self.dest / "scripts" / "run.sh").is_file())
        # 3. Excluded file (*.bak) not present
        self.assertFalse((self.dest / "scripts" / "debug.bak").exists())
        # 4. Un-whitelisted file (unwanted.txt) not present
        self.assertFalse((self.dest / "unwanted.txt").exists())

    def test_apply_sparse_form_end_to_end(self):
        (self.app_root / "manifest.toml").write_text("""
preserve = ["monitor.kdl"]

[forms]
allow = ["glow"]
include = ["scripts/**", "*.kdl"]
exclude = ["*.bak"]
""")
        # Pre-seed destination with Dunder and Preserved files
        self.dest.mkdir(parents=True)
        (self.dest / "monitor.kdl").write_text("// user monitor")
        (self.dest / "input__custom__.kdl").write_text("// user input")

        ok = desktop_forms.apply_form(self.app, "glow")
        self.assertTrue(ok)
        self.assertEqual(forms.read_active_form(self.app), "glow")

        # Check deployed contents
        self.assertEqual((self.dest / "layout.kdl").read_text(), "// glow layout")
        self.assertEqual((self.dest / "config.kdl").read_text(), "// base config")
        self.assertEqual((self.dest / "binds.kdl").read_text(), "// base binds")
        self.assertTrue((self.dest / "scripts" / "run.sh").is_file())
        self.assertFalse((self.dest / "scripts" / "debug.bak").exists())
        self.assertFalse((self.dest / "unwanted.txt").exists())

        # Check preserved files survived
        self.assertEqual((self.dest / "monitor.kdl").read_text(), "// user monitor")


class TestSlotMechanism(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

        self.app = "niri_parts_test"
        self.app_root = self.env.plugins_src / self.app
        self.app_root.mkdir(parents=True)
        self.dest = self.env.config_dir / self.app
        self.dest.mkdir(parents=True)

        # Setup manifest
        (self.app_root / "manifest.toml").write_text("""
preserve = ["monitor.kdl"]

[forms.effects]
target = "effects_normal.kdl"
source_dir = "effects"
default = "default"
""")

        # Setup slot files under __forms__/effects
        effects_dir = self.app_root / "__forms__" / "effects"
        effects_dir.mkdir(parents=True)
        (effects_dir / "default.kdl").write_text("// default blur")
        (effects_dir / "xray.kdl").write_text("// xray blur")

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def test_list_slots(self):
        slots_info = forms.list_slots(self.app)
        self.assertIn("effects", slots_info)
        eff = slots_info["effects"]
        self.assertEqual(eff["target"], "effects_normal.kdl")
        self.assertEqual(eff["default"], "default")
        self.assertEqual(sorted(eff["variants"]), ["default", "xray"])

    def test_apply_slot_success(self):
        from nyxuri.kernel.ledger import get_form_slots
        target_file = self.dest / "effects_normal.kdl"
        target_file.write_text("// initial")

        ok = forms.use_form(self.app, "effects", "xray")
        self.assertTrue(ok)
        self.assertEqual(target_file.read_text(), "// xray blur")
        self.assertEqual(get_form_slots(self.app).get("effects"), "xray")

    def test_apply_slot_nonexistent_returns_false(self):
        ok = forms.use_form(self.app, "effects", "ghost")
        self.assertFalse(ok)

    def test_collect_forms_excludes_slot_source_dirs(self):
        entries = desktop_forms.collect_forms(self.app)
        form_names = [p[0] for p in entries]
        self.assertNotIn("effects", form_names)

    def test_get_active_slot(self):
        self.assertEqual(forms.get_active_slot(self.app, "effects"), "default")
        forms.use_form(self.app, "effects", "xray")
        self.assertEqual(forms.get_active_slot(self.app, "effects"), "xray")

    def test_form_switcher_loop_wires_slots_and_on_action(self):
        from nyxuri.installer.menus import form_switcher_loop
        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxuri.installer.menus.discover_config_items", return_value=["niri"]), \
             patch("nyxuri.deploy.forms.use_form", return_value=True) as mock_apply, \
             patch("nyxuri.installer.menus.FormSwitcher") as mock_switcher_cls:
            form_switcher_loop()
            mock_switcher_cls.assert_called_once()
            _, kwargs = mock_switcher_cls.call_args
            self.assertIn("slots_for", kwargs)
            self.assertIn("active_slot_for", kwargs)
            on_action = kwargs["on_action"]
            toast = on_action("apply_slot", "niri", "effects:xray-blur")
            mock_apply.assert_called_once_with("niri", "effects", "xray-blur")
            self.assertIn("xray-blur", toast)

    def test_deploy_replays_active_slots_end_to_end(self):
        from nyxuri.deploy.deploy import deploy_selected_configs
        (self.app_root / "config.kdl").write_text("// base config")
        (self.app_root / "effects_normal.kdl").write_text("// default blur")

        # 1. Apply xray slot
        self.assertTrue(forms.use_form(self.app, "effects", "xray"))
        self.assertEqual(forms.get_active_slot(self.app, "effects"), "xray")

        # Re-deploy configs (deploy_selected_configs)
        with patch("nyxuri.deploy.deploy._phase_render_templates"), \
             patch("nyxuri.deploy.deploy._phase_post_install_services"):
            failed = deploy_selected_configs(items_to_deploy=[self.app])
            self.assertEqual(failed, [])

        target_file = self.dest / "effects_normal.kdl"
        self.assertTrue(target_file.is_file())
        self.assertEqual(target_file.read_text(), "// xray blur")
        self.assertEqual(forms.get_active_slot(self.app, "effects"), "xray")

        # 2. Desync healing: disk was reset to default, but ledger records xray
        target_file.write_text("// default blur")
        self.assertEqual(target_file.read_text(), "// default blur")

        with patch("nyxuri.deploy.deploy._phase_render_templates"), \
             patch("nyxuri.deploy.deploy._phase_post_install_services"):
            failed = deploy_selected_configs(items_to_deploy=[self.app])
            self.assertEqual(failed, [])

        self.assertEqual(target_file.read_text(), "// xray blur")
        self.assertEqual(forms.get_active_slot(self.app, "effects"), "xray")


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestFormDurability(unittest.TestCase):

    def _sandbox(self, ctx):
        ctx.env.plugins_src = Path(tempfile.mkdtemp())
        import nyxuri.deploy.manifest as manifest
        manifest._MANIFEST_CACHE = None
        return ctx.env.plugins_src

    def _app(self, src, name, manifest_toml, files):
        root = src / name
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        (root / "manifest.toml").write_text(manifest_toml, encoding="utf-8")
        return root

    def test_failed_save_keeps_the_existing_form(self):
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            self._app(src, "kitty", "", {"kitty.conf": "# conf"})
            dest = ctx.env.config_dir / "kitty"
            dest.mkdir(parents=True)
            (dest / "kitty.conf").write_text("# live", encoding="utf-8")
            os.mkfifo(dest / "ipc.fifo")
            old = ctx.env.forms_dir / "kitty" / "mine"
            old.mkdir(parents=True)
            (old / "old.conf").write_text("OLD-FORM", encoding="utf-8")
            self.assertFalse(_quiet(desktop_forms.save_form, "kitty", "mine"))
            self.assertEqual((old / "old.conf").read_text(encoding="utf-8"), "OLD-FORM")
            self.assertEqual(sorted(p.name for p in (ctx.env.forms_dir / "kitty").iterdir()), ["mine"])

    def test_official_guard_uses_the_resolved_official_dir(self):
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            root = self._app(src, "kitty", "", {"kitty.conf": "# base"})
            official = root / "__forms__" / "shared"
            official.mkdir(parents=True)
            (official / "kitty.conf").write_text("# official", encoding="utf-8")
            shadow = ctx.env.forms_dir / "kitty" / "shared"
            shadow.mkdir(parents=True)
            (shadow / "kitty.conf").write_text("# shadow", encoding="utf-8")
            self.assertFalse(_quiet(desktop_forms.delete_form, "kitty", "shared"))
            self.assertFalse(_quiet(desktop_forms.edit_form, "kitty", "shared"))
            self.assertTrue(shadow.is_dir())

    def test_ledger_is_the_single_form_truth(self):
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            self._app(src, "demo", "", {"config.kdl": "// b"})
            forms.write_active_form("demo", "A")
            self.assertEqual(forms.read_active_form("demo"), "A")
            # a stale legacy marker cannot override the ledger once a choice exists
            marker = ctx.env.forms_dir / "demo.active"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("B", encoding="utf-8")
            self.assertEqual(forms.read_active_form("demo"), "A",
                             "the ledger record wins; the retired marker is dead")

    def test_non_string_slot_target_returns_false(self):
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            root = self._app(src, "demo", '[forms.x]\ntarget = ["a.kdl"]\nsource_dir = "x"\n',
                             {"config.kdl": "// b"})
            slot = root / "__forms__" / "x"
            slot.mkdir(parents=True)
            (slot / "default.kdl").write_text("// v", encoding="utf-8")
            self.assertFalse(_quiet(forms.use_form, "demo", "x", "default"))

    def test_form_include_keeps_directory_and_double_star_matches(self):
        cases = (
            ('["scripts"]', {"a.kdl", "scripts/run.sh"}),
            ('["**/*.kdl"]', {"a.kdl", "sub/x.kdl"}),
            ('["*.kdl"]', {"a.kdl", "sub/x.kdl"}),
        )
        for include, expected in cases:
            with TempEnv() as ctx:
                src = self._sandbox(ctx)
                self._app(
                    src, "demo",
                    f"[forms]\ninherit = true\ninclude = {include}\n",
                    {"config.kdl": "// c", "scripts/run.sh": "#!/bin/sh\n",
                     "sub/x.kdl": "// x", "a.kdl": "// a"},
                )
                root = src / "demo" / "__forms__" / "A"
                root.mkdir(parents=True)
                (root / "a.kdl").write_text("// a", encoding="utf-8")
                self.assertTrue(_quiet(desktop_forms.apply_form, "demo", "A"))
                dest = ctx.env.config_dir / "demo"
                got = {str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()}
                self.assertTrue(expected <= got, f"{include}: missing {sorted(expected - got)}")

    def test_apply_form_applies_manifest_chmod(self):
        with TempEnv() as ctx:
            src = self._sandbox(ctx)
            root = self._app(src, "demo",
                             'chmod = ["scripts/*.sh"]\n[forms]\ninherit = true\n',
                             {"config.kdl": "// c", "scripts/run.sh": "#!/bin/sh\n"})
            os.chmod(root / "scripts" / "run.sh", 0o644)
            slot = root / "__forms__" / "A"
            slot.mkdir(parents=True)
            (slot / "a.kdl").write_text("// a", encoding="utf-8")
            self.assertTrue(_quiet(desktop_forms.apply_form, "demo", "A"))
            script = ctx.env.config_dir / "demo" / "scripts" / "run.sh"
            self.assertTrue(script.is_file())
            self.assertEqual(script.stat().st_mode & 0o777, 0o755)


if __name__ == "__main__":
    unittest.main()

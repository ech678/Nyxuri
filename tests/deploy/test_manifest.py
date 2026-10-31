"""Contract tests for manifest.toml plugin manifests and plugin discovery.

Covers §4 shapes: schema defaults (no file), flat field overrides, bad-toml
error, single-file target plugins, manifest-only (non-deployable) plugins, and
discovery filters.
"""

import tempfile
import unittest
import unittest.mock
from pathlib import Path

import tomllib

import nyxuri.deploy.manifest as manifest
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import io



class TestManifestDefaults(unittest.TestCase):
    """No manifest file → every default derived from the plugin dir name."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        # Synthetic configs tree so we control layout precisely.
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def _write(self, rel: str, content: str = "") -> Path:
        p = self.env.plugins_src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def _mkdir(self, rel: str) -> Path:
        d = self.env.plugins_src / rel
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_dir_unit_no_manifest_full_defaults(self):
        kitty = self._mkdir("kitty")
        (kitty / "kitty.conf").write_text("# conf")
        m = manifest.load_manifest(kitty)
        self.assertEqual(m.name, "kitty")
        self.assertEqual(m.packages_repo, ["kitty"])
        self.assertEqual(m.packages_aur, [])
        self.assertEqual(m.preserve, [])
        self.assertEqual(m.chmod, [])
        self.assertEqual(m.label, "kitty")
        self.assertEqual(m.detect, "kitty")
        self.assertFalse(m.is_optional)
        self.assertEqual(m.target, "")
        self.assertTrue(m.is_deployable)

    def test_manifest_only_dir_not_deployable(self):
        # A dir whose only entry is manifest.toml → manifest-only (optional plugin).
        plugin = self._mkdir("nautilus")
        (plugin / "manifest.toml").write_text('optional = true\n')
        m = manifest.load_manifest(plugin)
        self.assertFalse(m.is_deployable)
        self.assertTrue(m.is_optional)
        self.assertEqual(m.packages_repo, ["nautilus"])

    def test_dir_with_manifest_plus_config_is_deployable(self):
        niri = self._mkdir("niri")
        (niri / "config.kdl").write_text("# conf")
        (niri / "manifest.toml").write_text('preserve = ["monitor.kdl"]\n')
        m = manifest.load_manifest(niri)
        self.assertTrue(m.is_deployable)
        self.assertEqual(m.preserve, ["monitor.kdl"])

    def test_stray_top_level_file_is_not_a_unit(self):
        # configs/ is flat: every plugin is a directory. Stray files are ignored.
        self._write("stray.toml", "# junk")
        names = [n for n, _ in manifest.discover_manifest_apps()]
        self.assertNotIn("stray.toml", names)


class TestManifestOverrides(unittest.TestCase):
    """Each field can be overridden; fields are flat at the top level."""

    def setUp(self):
        self._sandbox = tempfile.TemporaryDirectory()
        self.root = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()

    def test_full_override(self):
        plugin = self.root / "xdp"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(
            'packages = ["xdg-desktop-portal"]\n'
            'preserve = ["portals.conf"]\n'
            'chmod = ["*.sh"]\n'
            'label = "XDG Portals"\n'
            'detect = "xdg-desktop-portal"\n'
        )
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.packages_repo, ["xdg-desktop-portal"])
        self.assertEqual(m.packages_aur, [])
        self.assertEqual(m.preserve, ["portals.conf"])
        self.assertEqual(m.chmod, ["*.sh"])
        self.assertEqual(m.label, "XDG Portals")
        self.assertEqual(m.detect, "xdg-desktop-portal")

    def test_optional_flag_parsed(self):
        plugin = self.root / "lutris"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(
            'optional = true\npackages = ["lutris"]\nlabel = "Lutris"\ncategory = "game"\n'
        )
        m = manifest.load_manifest(plugin)
        self.assertTrue(m.is_optional)
        self.assertEqual(m.category, "game")

    def test_target_single_file_unit(self):
        plugin = self.root / "starship"
        plugin.mkdir()
        (plugin / "starship.toml").write_text("# conf")
        (plugin / "manifest.toml").write_text('target = "starship.toml"\n')
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.target, "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertEqual(m.detect, "starship")
        self.assertTrue(m.is_deployable)

    def test_xdg_target_resolves_through_pics_dir(self):
        """#144: `xdg:PICTURES/<rest>` resolves via the XDG Pictures dir."""
        plugin = self.root / "wallpapers"
        plugin.mkdir()
        (plugin / "fallback.webp").write_bytes(b"img")
        (plugin / "manifest.toml").write_text(
            'target = "xdg:PICTURES/Wallpapers"\nmerge = true\n'
        )
        m = manifest.load_manifest(plugin)
        pics = self.root / "MyPictures"
        with unittest.mock.patch("nyxuri.core.get_pics_dir", return_value=pics):
            resolved = manifest.living_path(m, Path("/sandbox/.config"))
        self.assertEqual(resolved, pics / "Wallpapers")

    def test_xdg_target_rejects_unknown_kind(self):
        """#144: an unknown xdg: category is refused, never guessed."""
        plugin = self.root / "weird"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text('target = "xdg:MUSIC/Playlists"\n')
        m = manifest.load_manifest(plugin)
        with self.assertRaises(ValueError):
            manifest.living_path(m, Path("/sandbox/.config"))

    def test_preserve_values_parsed(self):
        plugin = self.root / "noctalia"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(
            'preserve_values = { "noctalia-config.toml" = ["enable_ddcutil"] }\n'
        )
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.preserve_values, {"noctalia-config.toml": ["enable_ddcutil"]})
        self.assertEqual(m.preserve, [])

    def test_preserve_values_defaults_to_empty(self):
        plugin = self.root / "kitty"
        plugin.mkdir()
        (plugin / "kitty.conf").write_text("conf")
        self.assertEqual(manifest.load_manifest(plugin).preserve_values, {})

    def test_preserve_values_rejects_hostile_shapes(self):
        plugin = self.root / "weird"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(
            'preserve_values = { "a.toml" = [], "b.toml" = "k", "c.toml" = [1, "k"] }\n'
        )
        self.assertEqual(manifest.load_manifest(plugin).preserve_values,
                         {"b.toml": ["k"], "c.toml": ["k"]})

    def test_preserve_values_non_table_falls_back(self):
        plugin = self.root / "odd"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text('preserve_values = "nope"\n')
        self.assertEqual(manifest.load_manifest(plugin).preserve_values, {})

    def test_aur_packages(self):
        plugin = self.root / "fcitx5-rime"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(
            'packages = ["fcitx5", "fcitx5-rime"]\npackages_aur = ["rime-ice-git"]\n'
        )
        m = manifest.load_manifest(plugin)
        self.assertEqual(m.packages_repo, ["fcitx5", "fcitx5-rime"])
        self.assertEqual(m.packages_aur, ["rime-ice-git"])

    def test_bad_toml_raises(self):
        plugin = self.root / "bad"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text("this is = = not toml [[[\n")
        with self.assertRaises(tomllib.TOMLDecodeError):
            manifest.load_manifest(plugin)


class TestRealRepoManifests(unittest.TestCase):
    """The shipped manifests in the real configs/ tree parse as designed."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_niri_manifest(self):
        m = manifest.load_manifest(self.env.plugins_src / "niri")
        self.assertEqual(m.preserve, ["monitor.kdl", "effects.kdl", "effects_normal.kdl", "glow.kdl", "colors.kdl", "noctalia.kdl", "eyecare_temp"])
        self.assertEqual(m.chmod, ["scripts/*.sh", "scripts/*.py"])
        self.assertTrue(m.is_deployable)
        self.assertIn("effects", m.forms)
        self.assertIn("glow", m.forms)
        # dir name = package = binary → no packages override needed
        self.assertEqual(m.packages_repo, ["niri"])

    def test_noctalia_manifest_preserves_ddcutil(self):
        m = manifest.load_manifest(self.env.plugins_src / "noctalia")
        self.assertEqual(m.preserve_values,
                         {"noctalia-config.toml": ["enable_ddcutil"]})
        self.assertEqual(m.preserve, [])

    def test_starship_target_unit(self):
        m = manifest.load_manifest(self.env.plugins_src / "starship")
        self.assertEqual(m.target, "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertEqual(m.detect, "starship")
        self.assertTrue(m.is_deployable)

    def test_packages_only_names_are_plugins_but_never_dotfiles(self):
        # R0-2 catalog 并轨: packages-only software lives in the blueprint as
        # manifest-only plugin dirs. They are registry-known plugins, yet
        # never deployable — and the ``deploy = false`` declaration, not
        # directory emptiness, is what keeps them out of the dotfile world.
        manifests = dict(manifest.discover_manifest_apps())
        for name in ("nautilus", "missioncenter", "brave-origin", "vscode", "wechat"):
            m = manifests[name]
            self.assertFalse(m.deploy_declared, f"{name} must declare deploy = false")
            self.assertFalse(m.is_deployable, f"{name} must never become a dotfile plugin")

    def test_optional_units_keep_manifest_declaration(self):
        opts = manifest.discover_optional_apps()
        for name in ("fcitx5-rime", "greeter", "mango", "zed"):
            self.assertIn(name, opts)

    def test_deployable_excludes_manifest_only(self):
        deployable = manifest.discover_deployable_apps()
        self.assertNotIn("nautilus", deployable)
        self.assertNotIn("missioncenter", deployable)
        # The shipped config plugins are all present. `theme` is a merge plugin
        # (shared living area) — it deploys only through the transaction's
        # no-clobber path and never joins the atomic batch.
        for name in ("fastfetch", "fish", "kitty", "niri", "noctalia",
                     "starship", "xdg-desktop-portal", "zed", "mango",
                     "fcitx5-rime"):
            self.assertIn(name, deployable)
        self.assertNotIn("theme", deployable)
        merge_units = {name for name, m in manifest.discover_manifest_apps() if m.merge}
        self.assertIn("theme", merge_units)

    def test_stray_sidecar_files_are_gone(self):
        # KM1 ② enforcement: configs/ is a flat plugin directory — no sidecars.
        src = self.env.plugins_src
        self.assertFalse((src / ".optional-apps.toml").exists())
        self.assertFalse((src / "starship.toml").exists())
        self.assertEqual(list(src.glob("**/*.module.toml")), [])

    def test_packages_only_manifest_detect_fixes_status_lookup(self):
        # Package name "mission-center" differs from plugin name (R0-2:
        # the old catalog row is now a manifest-only plugin dir).
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["missioncenter"]
        self.assertEqual(m.detect, "mission-center")
        self.assertEqual(m.packages_repo, ["mission-center"])
        self.assertFalse(m.is_deployable, "packages-only plugin ships no living area")

    def test_fcitx5_rime_aur_packages(self):
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["fcitx5-rime"]
        self.assertEqual(m.packages_aur, ["rime-ice-git"])
        self.assertIn("fcitx5-rime", m.packages_repo)
        self.assertTrue(m.is_optional)
        # KM3: skin + profile live in the blueprint; hooks run the side domains.
        self.assertEqual(m.post_install, "activate")
        self.assertEqual(m.post_remove, "deactivate")
        self.assertIn("conf/classicui.conf", m.preserve)
        self.assertIn("profile", m.preserve)

    def test_privilege_declaration_parsed(self):
        """[privilege] declares root-level side effects (KM3: the greeter case)."""
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["greeter"]
        self.assertTrue(m.requires_root)
        self.assertTrue(any(p.startswith("/etc/greetd") for p in m.system_paths))
        self.assertEqual(m.post_install, "activate")
        self.assertEqual(m.post_remove, "deactivate")
        self.assertFalse(m.is_deployable, "manifest-only plugin stays non-deployable")
        # Plugins without the table default to unprivileged.
        self.assertFalse(manifests["kitty"].requires_root)
        self.assertEqual(manifests["kitty"].system_paths, [])

    def test_zed_optional_and_deployable(self):
        # zed ships config AND stays optional — both axes true at once.
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["zed"]
        self.assertTrue(m.is_optional)
        self.assertTrue(m.is_deployable)
        self.assertEqual(m.category, "dev")
        self.assertEqual(m.packages_repo, ["zed"])
        self.assertEqual(m.detect, "zed")
        self.assertIn("zed", manifest.discover_optional_apps())
        self.assertIn("zed", manifest.discover_deployable_apps())

    def test_flatpak_only_manifests_have_no_pacman_packages(self):
        # qq/wechat/spotify install via Flathub. Explicit empty repo list
        # must survive parsing, or pacman would be handed a nonexistent name.
        manifests = dict(manifest.discover_manifest_apps())
        expected = {
            "qq": ["com.qq.QQ"],
            "wechat": ["com.tencent.WeChat"],
            "spotify": ["com.spotify.Client"],
        }
        for name, ids in expected.items():
            m = manifests[name]
            self.assertEqual(m.packages_repo, [], f"{name} must keep packages empty")
            self.assertEqual(m.packages_aur, [])
            self.assertEqual(m.packages_flatpak, ids)

    def test_all_optional_units_categorized(self):
        known = {"browser", "office", "dev", "social", "media", "game",
                 "video", "download", "proxy", "terminal", "system"}
        for _name, m in manifest.discover_manifest_apps():
            if m.is_optional:
                self.assertIn(m.category, known, f"{_name} has unknown category")

    def test_full_optional_catalog(self):
        """Optional surface = packages-only plugins + optional plugins, one supply."""
        from nyxuri.pkg.deps import _supply_items

        keys = {item["key"] for item in _supply_items()}
        for name in ("brave-origin", "libreoffice", "vscode", "wechat", "qq",
                     "telegram", "spotify", "steam", "lutris", "protonplus",
                     "kdenlive", "obs", "motrix", "flclash", "shelly",
                     "nautilus", "missioncenter"):
            self.assertIn(name, keys, f"{name} must come from its packages-only manifest")
        for name in ("fcitx5-rime", "greeter", "mango", "zed"):
            self.assertIn(name, keys, f"{name} must come from its manifest")

    def test_merge_unit_excluded_from_atomic_batch(self):
        # The wallpapers plugin is a shared living area: it must never join
        # the atomic swap batch (a swap would clobber user content).
        names = [name for name, _m in manifest.discover_manifest_apps()]
        self.assertIn("wallpapers", names)
        self.assertNotIn("wallpapers", manifest.discover_deployable_apps())

    def test_wallpaper_target_and_hook_resolve_xdg(self):
        """#144: manifest target and the pack hook share the XDG Pictures dir."""
        m = manifest.load_manifest_for("wallpapers")
        self.assertEqual(m.target, "xdg:PICTURES/Wallpapers")
        self.assertTrue(m.merge)

        hook = (self.env.plugins_src / "wallpapers" / "hooks" / "install-pack").read_text()
        self.assertIn('NYXURI_UNIT_DEST', hook)
        self.assertIn("xdg-user-dir PICTURES", hook)
        self.assertNotIn("$HOME/Pictures/Wallpapers", hook)

    def test_theme_declares_adw_gtk3_package(self):
        """#146: the GTK3 theme Nyxuri sets must ship with its provider package."""
        m = manifest.load_manifest_for("theme")
        self.assertIn("adw-gtk-theme", m.packages_repo)

    def test_real_niri_manifest_has_slot_axes(self):
        m = manifest.load_manifest_for("niri")
        self.assertIn("effects", m.forms)
        self.assertEqual(m.forms["effects"]["target"], "effects_normal.kdl")
        self.assertIn("glow", m.forms)
        self.assertEqual(m.forms["glow"]["target"], "glow.kdl")


class TestManifestPresets(unittest.TestCase):
    """Presets table parsing in manifest.toml (whitelist/blacklist/inheritance)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.plugins_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def _mkdir(self, rel: str) -> Path:
        d = self.env.plugins_src / rel
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_no_forms_table_defaults_to_safe(self):
        plugin = self._mkdir("myapp")
        (plugin / "config.conf").write_text("# conf")
        m = manifest.load_manifest(plugin)
        self.assertFalse(m.form_inherit)
        self.assertEqual(m.form_allow, [])
        self.assertEqual(m.form_standalone, [])
        self.assertEqual(m.form_include, [])
        self.assertEqual(m.form_exclude, [])

    def test_forms_table_parsed_correctly(self):
        plugin = self._mkdir("niri_test")
        (plugin / "config.kdl").write_text("# conf")
        (plugin / "manifest.toml").write_text("""
preserve = ["monitor.kdl"]

[forms]
inherit = true
allow = ["glow", "compact"]
standalone = ["isolated"]
include = ["scripts/**", "*.kdl"]
exclude = ["scripts/debug.sh"]
""")
        m = manifest.load_manifest(plugin)
        self.assertTrue(m.form_inherit)
        self.assertEqual(m.form_allow, ["glow", "compact"])
        self.assertEqual(m.form_standalone, ["isolated"])
        self.assertEqual(m.form_include, ["scripts/**", "*.kdl"])
        self.assertEqual(m.form_exclude, ["scripts/debug.sh"])

    def test_slot_targets_auto_included_in_preserve(self):
        plugin = self._mkdir("part_unit")
        (plugin / "config.kdl").write_text("# conf")
        (plugin / "manifest.toml").write_text("""
preserve = ["explicit.kdl"]

[forms.theme]
target = "theme.kdl"

[forms.effects]
target = "effects.kdl"
""")
        m = manifest.load_manifest(plugin)
        self.assertIn("explicit.kdl", m.preserve)
        self.assertIn("theme.kdl", m.preserve)
        self.assertIn("effects.kdl", m.preserve)
        # Ensure no duplicates if target was already explicitly declared
        (plugin / "manifest.toml").write_text("""
preserve = ["theme.kdl"]

[forms.theme]
target = "theme.kdl"
""")
        m2 = manifest.load_manifest(plugin)
        self.assertEqual(m2.preserve, ["theme.kdl"])


if __name__ == "__main__":
    unittest.main()


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestManifestCoercion(unittest.TestCase):

    def _sandbox(self, ctx):
        ctx.env.plugins_src = Path(tempfile.mkdtemp())
        return ctx.env.plugins_src

    def test_scalar_package_fields_become_single_element_lists(self):
        from nyxuri.deploy.manifest import load_manifest
        with TempEnv() as ctx:
            src = self._sandbox(ctx) / "demo"
            src.mkdir(parents=True)
            (src / "config.conf").write_text("# conf\n", encoding="utf-8")
            (src / "manifest.toml").write_text(
                'packages = "kitty"\npackages_aur = "foo-bar"\npreserve = "single.conf"\n',
                encoding="utf-8",
            )
            m = _quiet(load_manifest, src)
            self.assertEqual(m.packages_repo, ["kitty"])
            self.assertEqual(m.packages_aur, ["foo-bar"])
            self.assertEqual(m.preserve, ["single.conf"])

    def test_scalar_forms_entry_is_dropped(self):
        from nyxuri.deploy.manifest import load_manifest
        with TempEnv() as ctx:
            src = self._sandbox(ctx) / "demo2"
            src.mkdir(parents=True)
            (src / "config.conf").write_text("# conf\n", encoding="utf-8")
            (src / "manifest.toml").write_text(
                '[forms]\ngood = { target = "a.conf" }\nbad = "oops"\n', encoding="utf-8"
            )
            m = _quiet(load_manifest, src)
            self.assertEqual(sorted(m.forms), ["good"])

    def test_empty_packages_list_stays_empty(self):
        from nyxuri.deploy.manifest import load_manifest
        with TempEnv() as ctx:
            src = self._sandbox(ctx) / "flatpak-only"
            src.mkdir(parents=True)
            (src / "manifest.toml").write_text(
                'packages = []\npackages_flatpak = ["com.example.App"]\n', encoding="utf-8"
            )
            m = _quiet(load_manifest, src)
            self.assertEqual(m.packages_repo, [])

    def test_malformed_manifest_does_not_break_discovery(self):
        from nyxuri.deploy.manifest import discover_manifest_apps
        with TempEnv() as ctx:
            sandbox = self._sandbox(ctx)
            bad = sandbox / "bad-plugin"
            bad.mkdir()
            (bad / "manifest.toml").write_text("not = = toml\n", encoding="utf-8")
            good = sandbox / "good-plugin"
            good.mkdir()
            (good / "config.conf").write_text("# conf\n", encoding="utf-8")
            apps = _quiet(discover_manifest_apps)
            self.assertIsInstance(apps, list)
            self.assertEqual([n for n, _ in apps], ["good-plugin"])

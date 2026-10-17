"""Contract tests for manifest.toml unit manifests and unit discovery.

Covers §4 shapes: schema defaults (no file), flat field overrides, bad-toml
error, single-file target units, manifest-only (non-deployable) units, and
discovery filters.
"""

import tempfile
import unittest
from pathlib import Path

import tomllib

import nyxuri.deploy.manifest as manifest
from tests.utils import TempEnv


class TestManifestDefaults(unittest.TestCase):
    """No manifest file → every default derived from the unit dir name."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        # Synthetic configs tree so we control layout precisely.
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.configs_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def _write(self, rel: str, content: str = "") -> Path:
        p = self.env.configs_src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def _mkdir(self, rel: str) -> Path:
        d = self.env.configs_src / rel
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
        # A dir whose only entry is manifest.toml → manifest-only (optional unit).
        unit = self._mkdir("nautilus")
        (unit / "manifest.toml").write_text('optional = true\n')
        m = manifest.load_manifest(unit)
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
        # configs/ is flat: every unit is a directory. Stray files are ignored.
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
        unit = self.root / "xdp"
        unit.mkdir()
        (unit / "manifest.toml").write_text(
            'packages = ["xdg-desktop-portal"]\n'
            'preserve = ["portals.conf"]\n'
            'chmod = ["*.sh"]\n'
            'label = "XDG Portals"\n'
            'detect = "xdg-desktop-portal"\n'
        )
        m = manifest.load_manifest(unit)
        self.assertEqual(m.packages_repo, ["xdg-desktop-portal"])
        self.assertEqual(m.packages_aur, [])
        self.assertEqual(m.preserve, ["portals.conf"])
        self.assertEqual(m.chmod, ["*.sh"])
        self.assertEqual(m.label, "XDG Portals")
        self.assertEqual(m.detect, "xdg-desktop-portal")

    def test_optional_flag_parsed(self):
        unit = self.root / "lutris"
        unit.mkdir()
        (unit / "manifest.toml").write_text(
            'optional = true\npackages = ["lutris"]\nlabel = "Lutris"\ncategory = "game"\n'
        )
        m = manifest.load_manifest(unit)
        self.assertTrue(m.is_optional)
        self.assertEqual(m.category, "game")

    def test_target_single_file_unit(self):
        unit = self.root / "starship"
        unit.mkdir()
        (unit / "starship.toml").write_text("# conf")
        (unit / "manifest.toml").write_text('target = "starship.toml"\n')
        m = manifest.load_manifest(unit)
        self.assertEqual(m.target, "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertEqual(m.detect, "starship")
        self.assertTrue(m.is_deployable)

    def test_preserve_values_parsed(self):
        unit = self.root / "noctalia"
        unit.mkdir()
        (unit / "manifest.toml").write_text(
            'preserve_values = { "noctalia-config.toml" = ["enable_ddcutil"] }\n'
        )
        m = manifest.load_manifest(unit)
        self.assertEqual(m.preserve_values, {"noctalia-config.toml": ["enable_ddcutil"]})
        self.assertEqual(m.preserve, [])

    def test_preserve_values_defaults_to_empty(self):
        unit = self.root / "kitty"
        unit.mkdir()
        (unit / "kitty.conf").write_text("conf")
        self.assertEqual(manifest.load_manifest(unit).preserve_values, {})

    def test_preserve_values_rejects_hostile_shapes(self):
        unit = self.root / "weird"
        unit.mkdir()
        (unit / "manifest.toml").write_text(
            'preserve_values = { "a.toml" = [], "b.toml" = "k", "c.toml" = [1, "k"] }\n'
        )
        self.assertEqual(manifest.load_manifest(unit).preserve_values,
                         {"b.toml": ["k"], "c.toml": ["k"]})

    def test_preserve_values_non_table_falls_back(self):
        unit = self.root / "odd"
        unit.mkdir()
        (unit / "manifest.toml").write_text('preserve_values = "nope"\n')
        self.assertEqual(manifest.load_manifest(unit).preserve_values, {})

    def test_aur_packages(self):
        unit = self.root / "fcitx5-rime"
        unit.mkdir()
        (unit / "manifest.toml").write_text(
            'packages = ["fcitx5", "fcitx5-rime"]\npackages_aur = ["rime-ice-git"]\n'
        )
        m = manifest.load_manifest(unit)
        self.assertEqual(m.packages_repo, ["fcitx5", "fcitx5-rime"])
        self.assertEqual(m.packages_aur, ["rime-ice-git"])

    def test_bad_toml_raises(self):
        unit = self.root / "bad"
        unit.mkdir()
        (unit / "manifest.toml").write_text("this is = = not toml [[[\n")
        with self.assertRaises(tomllib.TOMLDecodeError):
            manifest.load_manifest(unit)


class TestRealRepoManifests(unittest.TestCase):
    """The shipped manifests in the real configs/ tree parse as designed."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_niri_manifest(self):
        m = manifest.load_manifest(self.env.configs_src / "niri")
        self.assertEqual(m.preserve, ["monitor.kdl", "effects.kdl", "effects_normal.kdl", "glow.kdl", "colors.kdl", "eyecare_temp"])
        self.assertEqual(m.chmod, ["scripts/*.sh", "scripts/*.py"])
        self.assertTrue(m.is_deployable)
        self.assertIn("effects", m.parts)
        self.assertIn("glow", m.parts)
        # dir name = package = binary → no packages override needed
        self.assertEqual(m.packages_repo, ["niri"])

    def test_noctalia_manifest_preserves_ddcutil(self):
        m = manifest.load_manifest(self.env.configs_src / "noctalia")
        self.assertEqual(m.preserve_values,
                         {"noctalia-config.toml": ["enable_ddcutil"]})
        self.assertEqual(m.preserve, [])

    def test_starship_target_unit(self):
        m = manifest.load_manifest(self.env.configs_src / "starship")
        self.assertEqual(m.target, "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertEqual(m.detect, "starship")
        self.assertTrue(m.is_deployable)

    def test_manifest_only_optional_units(self):
        # nautilus/missioncenter/fcitx5-rime declare packages only — optional
        # and not deployable.
        manifests = dict(manifest.discover_manifest_apps())
        for name in ("nautilus", "missioncenter", "fcitx5-rime"):
            self.assertIn(name, manifests)
            m = manifests[name]
            self.assertFalse(m.is_deployable, f"{name} has no config to ship")
            self.assertTrue(m.is_optional, f"{name} must declare optional = true")
        opts = manifest.discover_optional_apps()
        for name in ("nautilus", "missioncenter", "fcitx5-rime"):
            self.assertIn(name, opts)

    def test_deployable_excludes_manifest_only(self):
        deployable = manifest.discover_deployable_apps()
        self.assertNotIn("nautilus", deployable)
        self.assertNotIn("missioncenter", deployable)
        self.assertNotIn("fcitx5-rime", deployable)
        # The 9 shipped config units are all present.
        for name in ("fastfetch", "fish", "kitty", "niri", "noctalia",
                     "starship", "xdg-desktop-portal", "zed", "mango"):
            self.assertIn(name, deployable)

    def test_stray_sidecar_files_are_gone(self):
        # KM1 ② enforcement: configs/ is a flat unit directory — no sidecars.
        src = self.env.configs_src
        self.assertFalse((src / ".optional-apps.toml").exists())
        self.assertFalse((src / "starship.toml").exists())
        self.assertEqual(list(src.glob("**/*.module.toml")), [])

    def test_missioncenter_detect_fixes_status_lookup(self):
        # Package name "mission-center" differs from dir name "missioncenter".
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["missioncenter"]
        self.assertEqual(m.detect, "mission-center")
        self.assertEqual(m.packages_repo, ["mission-center"])
        self.assertTrue(m.is_optional)

    def test_telegram_detect_matches_its_package(self):
        """Arch ships the binary as /usr/bin/Telegram, so the unit name misses both paths."""
        m = dict(manifest.discover_manifest_apps())["telegram"]
        self.assertEqual(m.detect, "telegram-desktop")
        self.assertEqual(m.packages_repo, ["telegram-desktop"])

    def test_optional_units_all_have_a_menu_label(self):
        """Every optional unit needs its own app_<name> entry or the menu shows the key."""
        from nyxuri.i18n import msg

        for name in manifest.discover_optional_apps():
            key = "app_" + name.replace("-", "_")
            with self.subTest(unit=name):
                self.assertNotEqual(msg(key), key)

    def test_fcitx5_rime_aur_packages(self):
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["fcitx5-rime"]
        self.assertEqual(m.packages_aur, ["rime-ice-git"])
        self.assertIn("fcitx5-rime", m.packages_repo)
        self.assertTrue(m.is_optional)
        self.assertEqual(m.post_install, "fcitx:setup_rime_ice")

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

    def test_flatpak_only_units_have_no_pacman_packages(self):
        # qq/wechat/spotify install via Flathub. packages = [] must override
        # the [<name>] default, or pacman would be handed a nonexistent package.
        manifests = dict(manifest.discover_manifest_apps())
        expected = {
            "qq": ["com.qq.QQ"],
            "wechat": ["com.tencent.WeChat"],
            "spotify": ["com.spotify.Client"],
        }
        for name, ids in expected.items():
            m = manifests[name]
            self.assertEqual(m.packages_repo, [], f"{name} must declare packages = []")
            self.assertEqual(m.packages_aur, [])
            self.assertEqual(m.packages_flatpak, ids)
            self.assertFalse(m.is_deployable)
            self.assertTrue(m.is_optional)

    def test_all_optional_units_categorized(self):
        known = {"browser", "office", "dev", "social", "media", "game",
                 "video", "download", "proxy", "terminal", "system"}
        for _name, m in manifest.discover_manifest_apps():
            if m.is_optional:
                self.assertIn(m.category, known, f"{_name} has unknown category")

    def test_full_optional_catalog(self):
        opts = manifest.discover_optional_apps()
        for name in ("brave-origin", "libreoffice", "vscode", "zed", "wechat", "qq",
                     "telegram", "spotify", "steam", "lutris", "protonplus", "kdenlive",
                     "obs", "motrix", "flclash", "shelly", "nautilus", "missioncenter",
                     "fcitx5-rime", "mango"):
            self.assertIn(name, opts)

    def test_real_niri_manifest_has_parts(self):
        m = manifest.load_manifest_for("niri")
        self.assertIn("effects", m.parts)
        self.assertEqual(m.parts["effects"]["target"], "effects_normal.kdl")
        self.assertIn("glow", m.parts)
        self.assertEqual(m.parts["glow"]["target"], "glow.kdl")


class TestManifestPresets(unittest.TestCase):
    """Presets table parsing in manifest.toml (whitelist/blacklist/inheritance)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self._sandbox = tempfile.TemporaryDirectory()
        self.env.configs_src = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()
        self._ctx.__exit__()

    def _mkdir(self, rel: str) -> Path:
        d = self.env.configs_src / rel
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_no_presets_table_defaults_to_safe(self):
        unit = self._mkdir("myapp")
        (unit / "config.conf").write_text("# conf")
        m = manifest.load_manifest(unit)
        self.assertFalse(m.preset_inherit)
        self.assertEqual(m.preset_allow, [])
        self.assertEqual(m.preset_standalone, [])
        self.assertEqual(m.preset_include, [])
        self.assertEqual(m.preset_exclude, [])

    def test_presets_table_parsed_correctly(self):
        unit = self._mkdir("niri_test")
        (unit / "config.kdl").write_text("# conf")
        (unit / "manifest.toml").write_text("""
preserve = ["monitor.kdl"]

[presets]
inherit = true
allow = ["glow", "compact"]
standalone = ["isolated"]
include = ["scripts/**", "*.kdl"]
exclude = ["scripts/debug.sh"]
""")
        m = manifest.load_manifest(unit)
        self.assertTrue(m.preset_inherit)
        self.assertEqual(m.preset_allow, ["glow", "compact"])
        self.assertEqual(m.preset_standalone, ["isolated"])
        self.assertEqual(m.preset_include, ["scripts/**", "*.kdl"])
        self.assertEqual(m.preset_exclude, ["scripts/debug.sh"])

    def test_parts_targets_auto_included_in_preserve(self):
        unit = self._mkdir("part_unit")
        (unit / "config.kdl").write_text("# conf")
        (unit / "manifest.toml").write_text("""
preserve = ["explicit.kdl"]

[parts.theme]
target = "theme.kdl"

[parts.effects]
target = "effects.kdl"
""")
        m = manifest.load_manifest(unit)
        self.assertIn("explicit.kdl", m.preserve)
        self.assertIn("theme.kdl", m.preserve)
        self.assertIn("effects.kdl", m.preserve)
        # Ensure no duplicates if target was already explicitly declared
        (unit / "manifest.toml").write_text("""
preserve = ["theme.kdl"]

[parts.theme]
target = "theme.kdl"
""")
        m2 = manifest.load_manifest(unit)
        self.assertEqual(m2.preserve, ["theme.kdl"])


if __name__ == "__main__":
    unittest.main()

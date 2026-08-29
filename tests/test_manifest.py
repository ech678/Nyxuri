"""Contract tests for .module.toml manifest parsing and app discovery.

Covers §14 shapes: schema defaults (no file), field overrides, bad-toml error,
file-type sidecar, manifest-only (non-deployable) apps, and discovery filters.
"""

import tempfile
import unittest
from pathlib import Path

import tomllib

import nyxniri.deploy.manifest as manifest
from tests.utils import TempEnv


class TestManifestDefaults(unittest.TestCase):
    """No manifest file → every default derived from the app/dir name."""

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

    def test_dir_app_no_manifest_full_defaults(self):
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
        self.assertTrue(m.is_deployable)

    def test_file_app_no_sidecar_defaults(self):
        # A file-type app with no sidecar: name = filename (no stripping).
        app = self._write("starship.toml", "# conf")
        m = manifest.load_manifest(app)
        self.assertEqual(m.name, "starship.toml")
        self.assertEqual(m.packages_repo, ["starship.toml"])
        self.assertEqual(m.detect, "starship.toml")
        self.assertTrue(m.is_deployable)

    def test_manifest_only_dir_not_deployable(self):
        # A dir whose only entry is .module.toml → manifest-only (optional app).
        app = self._mkdir("nautilus")
        (app / ".module.toml").write_text('[packages]\nrepo = ["nautilus"]\n')
        m = manifest.load_manifest(app)
        self.assertFalse(m.is_deployable)
        self.assertEqual(m.packages_repo, ["nautilus"])

    def test_dir_with_manifest_plus_config_is_deployable(self):
        niri = self._mkdir("niri")
        (niri / "config.kdl").write_text("# conf")
        (niri / ".module.toml").write_text('[packages]\npreserve = ["monitor.kdl"]\n')
        m = manifest.load_manifest(niri)
        self.assertTrue(m.is_deployable)
        self.assertEqual(m.preserve, ["monitor.kdl"])


class TestManifestOverrides(unittest.TestCase):
    """Each field can be overridden; [packages] table scopes repo/aur only."""

    def setUp(self):
        self._sandbox = tempfile.TemporaryDirectory()
        self.root = Path(self._sandbox.name)

    def tearDown(self):
        self._sandbox.cleanup()

    def test_full_override(self):
        app = self.root / "xdp"
        app.mkdir()
        (app / ".module.toml").write_text(
            '[packages]\n'
            'repo = ["xdg-desktop-portal"]\n'
            'aur = []\n'
            'preserve = ["portals.conf"]\n'
            'chmod = ["*.sh"]\n'
            'label = "XDG Portals"\n'
            'detect = "xdg-desktop-portal"\n'
        )
        m = manifest.load_manifest(app)
        self.assertEqual(m.packages_repo, ["xdg-desktop-portal"])
        self.assertEqual(m.packages_aur, [])
        self.assertEqual(m.preserve, ["portals.conf"])
        self.assertEqual(m.chmod, ["*.sh"])
        self.assertEqual(m.label, "XDG Portals")
        self.assertEqual(m.detect, "xdg-desktop-portal")

    def test_aur_packages(self):
        app = self.root / "fcitx5-rime"
        app.mkdir()
        (app / ".module.toml").write_text(
            '[packages]\n'
            'repo = ["fcitx5", "fcitx5-rime"]\n'
            'aur = ["rime-ice-git"]\n'
        )
        m = manifest.load_manifest(app)
        self.assertEqual(m.packages_repo, ["fcitx5", "fcitx5-rime"])
        self.assertEqual(m.packages_aur, ["rime-ice-git"])

    def test_file_type_sidecar(self):
        # starship.toml file + sidecar starship.toml.module.toml
        (self.root / "starship.toml").write_text("# conf")
        (self.root / "starship.toml.module.toml").write_text(
            '[packages]\nrepo = ["starship"]\n\ndetect = "starship"\nlabel = "Starship"\n'
        )
        m = manifest.load_manifest(self.root / "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertEqual(m.detect, "starship")
        self.assertEqual(m.label, "Starship")
        self.assertTrue(m.is_deployable)

    def test_bad_toml_raises(self):
        app = self.root / "bad"
        app.mkdir()
        (app / ".module.toml").write_text("this is = = not toml [[[\n")
        with self.assertRaises(tomllib.TOMLDecodeError):
            manifest.load_manifest(app)


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
        self.assertEqual(m.preserve, ["monitor.kdl", "effects.kdl"])
        self.assertEqual(m.chmod, ["scripts/*.sh"])
        self.assertTrue(m.is_deployable)
        # dir name = package = binary → no [packages] override needed
        self.assertEqual(m.packages_repo, ["niri"])

    def test_starship_sidecar(self):
        m = manifest.load_manifest(self.env.configs_src / "starship.toml")
        self.assertEqual(m.packages_repo, ["starship"])
        self.assertEqual(m.detect, "starship")
        self.assertTrue(m.is_deployable)

    def test_manifest_only_optional_apps(self):
        # nautilus/missioncenter/fcitx5-rime live in .optional-apps.toml (axis B),
        # not as config dirs — they are optional and not deployable.
        manifests = dict(manifest.discover_manifest_apps())
        for name in ("nautilus", "missioncenter", "fcitx5-rime"):
            self.assertIn(name, manifests)
            m = manifests[name]
            self.assertFalse(m.is_deployable, f"{name} has no config dir")
            self.assertTrue(m.is_optional, f"{name} should be in .optional-apps.toml")
        opts = manifest.discover_optional_apps()
        for name in ("nautilus", "missioncenter", "fcitx5-rime"):
            self.assertIn(name, opts)

    def test_deployable_excludes_manifest_only(self):
        deployable = manifest.discover_deployable_apps()
        self.assertNotIn("nautilus", deployable)
        self.assertNotIn("missioncenter", deployable)
        self.assertNotIn("fcitx5-rime", deployable)
        # The 8 shipped config apps are all present.
        for name in ("fastfetch", "fish", "kitty", "niri", "noctalia",
                     "starship.toml", "xdg-desktop-portal", "zed"):
            self.assertIn(name, deployable)

    def test_sidecar_manifest_not_discovered_as_app(self):
        # starship.toml.module.toml is a sidecar, not an app — must not deploy.
        names = [n for n, _ in manifest.discover_manifest_apps()]
        self.assertIn("starship.toml", names)
        self.assertNotIn("starship.toml.module.toml", names)
        deployable = manifest.discover_deployable_apps()
        self.assertNotIn("starship.toml.module.toml", deployable)

    def test_missioncenter_detect_fixes_status_lookup(self):
        # Package name "mission-center" differs from dir name "missioncenter";
        # declared in .optional-apps.toml.
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["missioncenter"]
        self.assertEqual(m.detect, "mission-center")
        self.assertEqual(m.packages_repo, ["mission-center"])
        self.assertTrue(m.is_optional)

    def test_fcitx5_rime_aur_packages(self):
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["fcitx5-rime"]
        self.assertEqual(m.packages_aur, ["rime-ice-git"])
        self.assertIn("fcitx5-rime", m.packages_repo)
        self.assertTrue(m.is_optional)

    def test_zed_dual_axis_merge(self):
        # zed ships config AND registers in .optional-apps.toml (§2 coexistence):
        # deployability comes from the dir, optional-axis fields from the toml.
        manifests = dict(manifest.discover_manifest_apps())
        m = manifests["zed"]
        self.assertTrue(m.is_optional)
        self.assertTrue(m.is_deployable)
        self.assertEqual(m.category, "dev")
        self.assertEqual(m.packages_repo, ["zed"])
        self.assertEqual(m.detect, "zed")
        self.assertIn("zed", manifest.discover_optional_apps())
        self.assertIn("zed", manifest.discover_deployable_apps())

    def test_flatpak_only_apps_have_no_pacman_packages(self):
        # qq/wechat/spotify install via Flathub. repo=[] must override the
        # [<name>] default, or pacman would be handed a nonexistent package.
        manifests = dict(manifest.discover_manifest_apps())
        expected = {
            "qq": ["com.qq.QQ"],
            "wechat": ["com.tencent.WeChat"],
            "spotify": ["com.spotify.Client"],
        }
        for name, ids in expected.items():
            m = manifests[name]
            self.assertEqual(m.packages_repo, [], f"{name} must declare repo = []")
            self.assertEqual(m.packages_aur, [])
            self.assertEqual(m.packages_flatpak, ids)
            self.assertFalse(m.is_deployable)
            self.assertTrue(m.is_optional)

    def test_all_optional_apps_categorized(self):
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
                     "fcitx5-rime"):
            self.assertIn(name, opts)


if __name__ == "__main__":
    unittest.main()

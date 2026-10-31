"""发行版依赖声明的替换、拒绝和真实清单契约。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests.utils import TempEnv


def _item(**kwargs):
    values = {
        "name": "sample",
        "packages_repo": ["arch-package"],
        "packages_aur": ["aur-package"],
        "packages_flatpak": ["org.example.App"],
        "platforms": {},
    }
    values.update(kwargs)
    return SimpleNamespace(**values)


class TestResolveRequirements(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_arch_uses_original_declarations_and_ubuntu_replaces_native_packages(self):
        from nyxuri.pkg.requirements import resolve_requirements

        item = _item(platforms={"ubuntu": {"packages": ["deb-package"]}})
        original_repo = list(item.packages_repo)
        original_aur = list(item.packages_aur)
        self.assertEqual(
            resolve_requirements(item, "arch"),
            resolve_requirements(_item(), "arch"),
        )
        ubuntu = resolve_requirements(item, "ubuntu")
        self.assertEqual(ubuntu.packages_repo, ["deb-package"])
        self.assertEqual(ubuntu.packages_aur, [])
        self.assertEqual(ubuntu.packages_flatpak, ["org.example.App"])
        self.assertEqual(ubuntu.manual, [])
        self.assertTrue(ubuntu.supported)
        arch_after_override = resolve_requirements(item, "arch")
        self.assertEqual(arch_after_override.packages_repo, original_repo)
        self.assertEqual(arch_after_override.packages_aur, original_aur)
        self.assertEqual(item.packages_repo, original_repo)
        self.assertEqual(item.packages_aur, original_aur)

    def test_flatpak_only_and_package_free_items_work_without_override(self):
        from nyxuri.pkg.requirements import resolve_requirements

        flatpak = resolve_requirements(_item(packages_repo=[], packages_aur=[]), "ubuntu")
        self.assertTrue(flatpak.supported)
        self.assertEqual(flatpak.packages_flatpak, ["org.example.App"])

        empty = resolve_requirements(
            _item(packages_repo=[], packages_aur=[], packages_flatpak=[]), "ubuntu")
        self.assertTrue(empty.supported)
        self.assertEqual(empty.packages_repo, [])

    def test_missing_mapping_and_explicit_unsupported_platform_fail_closed(self):
        from nyxuri.pkg.requirements import resolve_requirements

        missing = resolve_requirements(_item(), "ubuntu")
        self.assertFalse(missing.supported)
        self.assertIn("no Ubuntu package mapping", missing.reason)

        unsupported = resolve_requirements(_item(platforms={
            "ubuntu": {"supported": False, "reason": "not packaged"},
        }), "ubuntu")
        self.assertFalse(unsupported.supported)
        self.assertEqual(unsupported.reason, "not packaged")
        self.assertEqual(unsupported.packages_repo, [])
        self.assertEqual(unsupported.packages_aur, [])

    def test_empty_override_requires_an_explicit_dependency_field(self):
        from nyxuri.pkg.requirements import resolve_requirements

        for override in ({}, {"reason": "PPA required"}, {"supported": True}):
            with self.subTest(override=override):
                result = resolve_requirements(_item(platforms={"ubuntu": override}), "ubuntu")
                self.assertFalse(result.supported)
                self.assertIn("explicitly declared", result.reason)

        explicit_empty = resolve_requirements(
            _item(platforms={"ubuntu": {"packages": []}}), "ubuntu")
        self.assertTrue(explicit_empty.supported)
        self.assertEqual(explicit_empty.packages_repo, [])

    def test_malformed_override_fields_fail_closed(self):
        from nyxuri.pkg.requirements import resolve_requirements

        invalid_overrides = (
            {"packages": ["ok", 7]},
            {"packages": ""},
            {"manual": [""]},
            {"packages_flatpak": ["org.example.App", None]},
            {"packages": ["pkg"], "supported": "yes"},
        )
        for override in invalid_overrides:
            with self.subTest(override=override):
                result = resolve_requirements(_item(platforms={"ubuntu": override}), "ubuntu")
                self.assertFalse(result.supported)
                self.assertTrue(result.reason)
                self.assertEqual(result.packages_repo, [])
                self.assertEqual(result.packages_aur, [])

    def test_manual_resources_and_flatpak_override_are_kept_separate(self):
        from nyxuri.pkg.requirements import resolve_requirements

        result = resolve_requirements(_item(platforms={"ubuntu": {
            "packages": ["apt-native"],
            "packages_flatpak": ["org.example.Other"],
            "manual": ["material-symbols-rounded-font"],
            "reason": "manual font required",
        }}), "ubuntu")
        self.assertEqual(result.packages_repo, ["apt-native"])
        self.assertEqual(result.packages_aur, [])
        self.assertEqual(result.packages_flatpak, ["org.example.Other"])
        self.assertEqual(result.manual, ["material-symbols-rounded-font"])
        self.assertEqual(result.reason, "manual font required")


class TestShippedPlatformDeclarations(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_niri_noctalia_and_quickshell_resolve_to_ubuntu_packages(self):
        from nyxuri.deploy.manifest import load_manifest
        from nyxuri.pkg.requirements import resolve_requirements
        from nyxuri.pkg.catalog import get_entry

        niri = load_manifest(self.env.env.units_src / "niri")
        niri_result = resolve_requirements(niri, "ubuntu")
        self.assertTrue(niri_result.supported)
        self.assertEqual(niri_result.packages_repo, ["niri"])

        noctalia = load_manifest(self.env.env.units_src / "noctalia")
        noctalia_result = resolve_requirements(noctalia, "ubuntu")
        self.assertTrue(noctalia_result.supported)
        self.assertIn("python3-gi-cairo", noctalia_result.packages_repo)
        self.assertNotIn("python-gobject", noctalia_result.packages_repo)
        self.assertNotIn("gtk-layer-shell", noctalia_result.packages_repo)

        quickshell = get_entry("quickshell")
        self.assertIsNotNone(quickshell)
        quickshell_result = resolve_requirements(quickshell, "ubuntu")
        self.assertTrue(quickshell_result.supported)
        self.assertIn("qml6-module-qtquick-controls", quickshell_result.packages_repo)
        self.assertIn("matugen", quickshell_result.packages_repo)
        self.assertIn("jq", quickshell_result.packages_repo)
        self.assertEqual(quickshell_result.packages_aur, [])
        self.assertEqual(
            quickshell_result.manual,
            ["material-symbols-rounded-font", "material-symbols-outlined-font"],
        )

    def test_catalog_shortcuts_and_unsupported_units_are_explicit(self):
        from nyxuri.deploy.manifest import load_manifest
        from nyxuri.pkg.requirements import resolve_requirements
        from nyxuri.pkg.catalog import get_entry

        vscode = resolve_requirements(get_entry("vscode"), "ubuntu")
        self.assertTrue(vscode.supported)
        self.assertEqual(vscode.packages_repo, ["code"])
        self.assertEqual(vscode.packages_aur, [])

        missioncenter = resolve_requirements(get_entry("missioncenter"), "ubuntu")
        self.assertTrue(missioncenter.supported)
        self.assertEqual(missioncenter.packages_repo, [])
        self.assertEqual(missioncenter.packages_flatpak, ["io.missioncenter.MissionCenter"])

        mango = resolve_requirements(load_manifest(self.env.env.units_src / "mango"), "ubuntu")
        self.assertFalse(mango.supported)

    def test_ubuntu_video_player_is_optional_without_changing_arch_toolchain(self):
        """Ubuntu 基础工具链保留必需字体，视频播放器仅由可选目录条目声明。"""
        from nyxuri.core import AUR_DEPS, CORE_DEPS
        from nyxuri.pkg.deps import core_requirements
        from nyxuri.pkg.catalog import get_entry
        from nyxuri.pkg.requirements import resolve_requirements

        with patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"):
            required = core_requirements()
        self.assertNotIn("mpvpaper", required.packages_repo + required.packages_aur + required.manual)
        self.assertIn("jetbrains-mono-nerd-font", required.manual)
        optional = resolve_requirements(get_entry("mpvpaper"), "ubuntu")
        self.assertTrue(optional.supported)
        self.assertEqual(optional.packages_repo, [])
        self.assertEqual(optional.packages_aur, [])
        self.assertEqual(optional.manual, ["mpvpaper"])
        self.assertIn("video wallpaper", optional.reason)
        self.assertIn("mpvpaper", CORE_DEPS)
        self.assertIn("mpvpaper", AUR_DEPS)

    def test_manifest_and_catalog_retain_arch_source_data(self):
        from nyxuri.deploy.manifest import load_manifest
        from nyxuri.pkg.requirements import resolve_requirements
        from nyxuri.pkg.catalog import get_entry

        fcitx = load_manifest(self.env.env.units_src / "fcitx5-rime")
        self.assertIn("rime-ice-git", fcitx.packages_aur)
        ubuntu_fcitx = resolve_requirements(fcitx, "ubuntu")
        self.assertTrue(ubuntu_fcitx.supported)
        self.assertEqual(ubuntu_fcitx.packages_aur, [])
        self.assertIn("rime-ice", ubuntu_fcitx.manual)
        # 平台解析只返回视图，不篡改 AUR 打包所读的原始声明。
        self.assertIn("rime-ice-git", fcitx.packages_aur)

        brave = get_entry("brave-origin")
        self.assertIn("brave-origin-bin", brave.packages_aur)
        self.assertEqual(resolve_requirements(brave, "ubuntu").packages_repo, ["brave-origin"])
        self.assertIn("brave-origin-bin", brave.packages_aur)

    def test_catalog_platform_table_is_loaded_from_a_temp_file(self):
        from nyxuri.pkg import catalog
        from nyxuri.pkg.requirements import resolve_requirements

        fixture = self.env.home / "catalog.toml"
        fixture.write_text(
            '[sample-app]\n'
            'packages = ["arch-app"]\n'
            'packages_aur = ["arch-app-bin"]\n'
            '[sample-app.platforms.ubuntu]\n'
            'packages = ["apt-app"]\n'
            'reason = "external APT source required"\n',
            encoding="utf-8",
        )
        with patch.object(catalog, "catalog_path", return_value=fixture):
            entries = catalog.catalog_entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.packages_repo, ["arch-app"])
        self.assertEqual(entry.packages_aur, ["arch-app-bin"])
        self.assertEqual(entry.platforms["ubuntu"], {
            "packages": ["apt-app"], "reason": "external APT source required",
        })
        resolved = resolve_requirements(entry, "ubuntu")
        self.assertTrue(resolved.supported)
        self.assertEqual(resolved.packages_repo, ["apt-app"])
        self.assertEqual(resolved.packages_aur, [])

"""首次安装覆盖共享目录，且保持独占原子批次、壁纸与可选供给边界。"""

import unittest
from unittest.mock import patch

from tests.utils import TempEnv


def stage_candidates(ctx):
    """铺设无外部依赖的各类配置载荷，安装事务可完整落入临时 HOME。"""
    units = ctx.home / "installer-units"
    specs = {
        "niri": ('', {"config.kdl": "niri-config"}),
        "starship": ('target = "starship.toml"\n', {"starship.toml": "starship-config"}),
        "xdg-desktop-portal": ('merge = true\nwhen_units = { "niri-portals.conf" = ["niri"] }\n',
                               {"niri-portals.conf": "portal-route"}),
        "fcitx5-rime": ('merge = true\ntarget = "fcitx5"\noptional = true\n',
                        {"config": "fcitx-config"}),
        "theme": ('merge = true\ntarget = "nyxuri/templates"\n', {"theme.conf": "theme-config"}),
        "wallpapers": ('merge = true\ntarget = "@pictures/Wallpapers"\n', {"fallback.png": "picture"}),
        "packages-only": ('', {}),
        "runtime-example": ('runtime = true\n', {"source.py": "runtime-source"}),
    }
    for uid, (manifest, files) in specs.items():
        source = units / uid
        source.mkdir(parents=True)
        (source / "manifest.toml").write_text('packages = []\n' + manifest, encoding="utf-8")
        for rel, content in files.items():
            (source / rel).write_text(content, encoding="utf-8")
    ctx.env.units_src = units


class TestInstallConfigCandidates(unittest.TestCase):
    def test_all_payload_shapes_are_candidates_without_expanding_atomic_batch(self):
        from nyxuri.installer.candidates import discover_install_config_items
        from nyxuri.deploy.deploy import discover_config_items
        with TempEnv() as ctx:
            stage_candidates(ctx)
            candidates = set(discover_install_config_items())
            self.assertEqual(candidates, {"niri", "starship", "xdg-desktop-portal", "fcitx5-rime", "theme"})
            atomic = set(discover_config_items())
            self.assertTrue({"niri", "starship"} <= atomic)
            self.assertFalse({"xdg-desktop-portal", "fcitx5-rime", "theme", "wallpapers"} & atomic)

    def test_menu_shows_shared_units_optional_supply_and_separate_wallpapers(self):
        from nyxuri.installer import menus
        captured = {}

        def select_checked(checklist):
            captured.update({entry.key: entry for entry in checklist.entries})
            return [entry.key for entry in checklist.entries if entry.checked and not entry.is_separator]

        with TempEnv() as ctx:
            stage_candidates(ctx)
            with patch.object(menus.CheckboxList, "run", select_checked), \
                 patch.object(menus, "detect_preferred_wm", return_value="niri"), \
                 patch.object(menus, "is_dep_installed", return_value=True), \
                 patch.object(menus, "supply_installed", return_value=False), \
                 patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"):
                result = menus.run_master_component_menu(mode="full")
            self.assertTrue(captured["config_xdg-desktop-portal"].checked)
            self.assertTrue(captured["config_theme"].checked)
            self.assertFalse(captured["config_fcitx5-rime"].checked)
            self.assertIn("assets_wallpapers", captured)
            self.assertTrue(captured["assets_wallpapers"].checked)
            self.assertTrue(result["wallpapers"])
            self.assertNotIn("Videos", captured["assets_wallpapers"].label)
            self.assertNotIn("download", captured["assets_wallpapers"].label.lower())
            self.assertNotIn("config_wallpapers", captured)
            self.assertNotIn("config_runtime-example", captured)
            self.assertNotIn("config_packages-only", captured)
            self.assertEqual(set(result["configs"]), {"niri", "starship", "xdg-desktop-portal", "theme"})

    def test_noninteractive_install_deploys_portal_and_supplied_optional_merge(self):
        from nyxuri.installer import workflows
        from nyxuri.kernel import ledger, transaction
        for optional_available in (False, True):
            with self.subTest(optional_available=optional_available), TempEnv() as ctx:
                stage_candidates(ctx)
                shared = ctx.env.config_dir / "fcitx5"
                shared.mkdir()
                (shared / "profile").write_text("existing-personal-profile")
                with patch("sys.stdin.isatty", return_value=False), \
                     patch.object(workflows, "backend_available", return_value=True), \
                     patch.object(workflows, "current_platform", return_value="ubuntu"), \
                     patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu"), \
                     patch.object(workflows, "detect_preferred_wm", return_value="niri"), \
                     patch.object(workflows, "supply_installed", return_value=optional_available), \
                     patch.object(workflows, "_phase_preflight_check"), \
                     patch.object(workflows, "get_missing_deps", return_value=[]), \
                     patch.object(workflows, "run_user_hooks", return_value=[]), \
                     patch.object(workflows, "render_completion_screen"), \
                     patch("builtins.print"):
                    self.assertTrue(workflows.install_configs_workflow("full"))
                expected = {"niri", "starship", "xdg-desktop-portal", "theme", "wallpapers"}
                if optional_available:
                    expected.add("fcitx5-rime")
                    self.assertEqual((shared / "config").read_text(), "fcitx-config")
                self.assertEqual(set(ledger.all_units()), expected)
                self.assertTrue(all(record["state"] == "enabled" for record in ledger.all_units().values()))
                self.assertEqual((ctx.env.config_dir / "xdg-desktop-portal/niri-portals.conf").read_text(), "portal-route")
                self.assertEqual((ctx.env.config_dir / "nyxuri/templates/theme.conf").read_text(), "theme-config")
                self.assertEqual((ctx.env.config_dir / "starship.toml").read_text(), "starship-config")
                self.assertEqual((shared / "profile").read_text(), "existing-personal-profile")
                self.assertEqual(transaction.audit_units("xdg-desktop-portal"), {"xdg-desktop-portal": "Synced"})

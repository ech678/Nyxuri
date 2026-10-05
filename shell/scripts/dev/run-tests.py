#!/usr/bin/env python3
"""Nyxuri Shell Categorized Test Runner (R5).

Executes tests across five explicit categories:
  [STATIC]    Static rules, ARCH001 boundary matrix, LIFE001-006, shared layer purity
  [LOGIC]     Pure algorithms, KDL parser, search catalog, state machines, QML math
  [RESOURCE]  Shaders (.qsb), SVG icons, TOML i18n dictionaries, Matugen templates
  [NATIVE]    Niri IPC mock socket, CLI launcher arguments, dual shell hot switch
  [GRAPHICS]  Headless Weston Wayland presentation, Quickshell rendering, dynamic theme

Usage:
  python3 shell/scripts/dev/run-tests.py [--category <name>] [--all] [-v]
"""

import argparse
import os
import sys
import time
import unittest
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[3]
SHELL_DIR = REPO_ROOT / "shell"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))


class ResourceIntegrityTests(unittest.TestCase):
    """Runtime resource integrity contracts for R5."""

    def test_all_shader_binaries_exist(self):
        """Assert all required GLSL fragment shaders have precompiled .qsb assets."""
        shaders_dir = SHELL_DIR / "assets" / "shaders"
        required_qsbs = [
            shaders_dir / "keystone" / "qsb" / "long_split.frag.qsb",
            shaders_dir / "keystone" / "qsb" / "pill_morph.frag.qsb",
            shaders_dir / "launcher" / "qsb" / "spotlight_mode_field.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "wp_disc.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "wp_fade.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "wp_iris_bloom.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "wp_pixelate.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "wp_portal.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "wp_stripes.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "wp_wipe.frag.qsb",
            shaders_dir / "wallpaper" / "qsb" / "zen-palette.frag.qsb",
        ]
        for qsb in required_qsbs:
            self.assertTrue(qsb.is_file(), f"Missing required precompiled shader: {qsb}")
            self.assertGreater(qsb.stat().st_size, 0, f"Shader file is empty: {qsb}")

    def test_zen_palette_renderer_has_no_dangling_qrc(self):
        """Assert ZenPaletteRenderer.qml uses Paths.fileUrl instead of old qrc:/clavis."""
        renderer = SHELL_DIR / "modules" / "wallpaper" / "ZenPaletteRenderer.qml"
        content = renderer.read_text(encoding="utf-8")
        self.assertNotIn("qrc:/", content)
        self.assertIn("zen-palette.frag.qsb", content)
        self.assertIn("Paths.fileUrl", content)

    def test_dead_icons_and_svg_icon_eliminated(self):
        """Assert dead unconsumed Font Awesome icons and SvgIcon.qml are removed."""
        icons_dir = SHELL_DIR / "assets" / "icons"
        for dead_icon in ["play.svg", "pause.svg", "previous.svg", "next.svg"]:
            self.assertFalse((icons_dir / dead_icon).exists(), f"Dead icon must be removed: {dead_icon}")
        svg_icon = SHELL_DIR / "shared" / "controls" / "SvgIcon.qml"
        self.assertFalse(svg_icon.exists(), "SvgIcon.qml must be removed as zero-consumer dead code")

    def test_active_icons_complete(self):
        """Assert humidity and keyboard icons are intact."""
        icons_dir = SHELL_DIR / "assets" / "icons"
        for pct in [7, 30, 50, 75, 90]:
            self.assertTrue((icons_dir / f"humidity_percent_{pct}.svg").is_file())

        kb_dir = icons_dir / "keyboard"
        expected_kb = ["apple.svg", "arch.svg", "debian.svg", "fedora.svg", "gentoo.svg",
                       "googlechrome.svg", "linux.svg", "linuxmint.svg", "nixos.svg",
                       "steam.svg", "ubuntu.svg", "windows.svg"]
        for kb in expected_kb:
            self.assertTrue((kb_dir / kb).is_file(), f"Missing keyboard logo: {kb}")

    def test_toml_i18n_syntax_and_dead_section_purged(self):
        """Assert zh_CN.toml and en_US.toml parse cleanly with tomllib and have no dead sections."""
        import tomllib
        zh_cn_path = SHELL_DIR / "assets" / "i18n" / "zh_CN.toml"
        en_us_path = SHELL_DIR / "assets" / "i18n" / "en_US.toml"

        with open(zh_cn_path, "rb") as f:
            zh_data = tomllib.load(f)
        self.assertNotIn("VerticalLyricsLayout", zh_data, "Dead lyrics section must not be in zh_CN.toml")
        self.assertIn("WallpaperPage", zh_data)

        with open(en_us_path, "rb") as f:
            en_data = tomllib.load(f)
        self.assertIn("%n minute(s) ago", en_data)

    def test_matugen_templates_exist(self):
        """Assert all 4 Matugen template files exist."""
        t_dir = SHELL_DIR / "assets" / "matugen" / "templates"
        for t_file in ["btop.theme", "kitty-colors.conf", "quickshell-colors.json", "yazi-theme.toml"]:
            self.assertTrue((t_dir / t_file).is_file(), f"Missing Matugen template: {t_file}")


def build_category_suite(category: str) -> unittest.TestSuite:
    """Build test suite for a specific category."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if category == "STATIC":
        # Lifecycle and boundary tests
        from shell.tests.test_lifecycle_audit import TestLifecycleAudit
        suite.addTests(loader.loadTestsFromTestCase(TestLifecycleAudit))
        from shell.tests.test_visual_tokens import DesignTokenContracts
        suite.addTests(loader.loadTestsFromTestCase(DesignTokenContracts))
        from shell.tests.test_contrast_guard import ContrastContracts
        suite.addTests(loader.loadTestsFromTestCase(ContrastContracts))
        from shell.tests.test_reduce_motion import ReduceMotionContracts
        suite.addTests(loader.loadTestsFromTestCase(ReduceMotionContracts))
        from shell.tests.test_i18n_catalog import CatalogContracts
        suite.addTests(loader.loadTestsFromTestCase(CatalogContracts))
        from shell.tests.test_accessibility import AccessibilityContracts
        suite.addTests(loader.loadTestsFromTestCase(AccessibilityContracts))
        from shell.tests.test_keyboard_navigation import KeyboardNavigationContracts
        suite.addTests(loader.loadTestsFromTestCase(KeyboardNavigationContracts))
        from tests.test_shell import TestShellManagement
        static_test_names = [
            "test_p2_layer_structure_and_session_decoupling",
            "test_p3_settings_decoupling_and_module_structure",
            "test_shell_directory_hygiene_and_module_unification",
            "test_r4c_c05_cpp_toolchain_elimination",
            "test_r4_architecture_and_lifecycle_contracts",
            "test_r4c_tree_inventory_and_domain_reorganization",
            "test_r4c_naming_codex_and_dead_stub_elimination",
            "test_r4c_app_global_boundary_convergence",
            "test_r4c_c06_domain_closure_and_single_state_source",
        ]
        for name in static_test_names:
            if hasattr(TestShellManagement, name):
                suite.addTest(TestShellManagement(name))

    elif category == "LOGIC":
        # Pure logic, KDL parsing, search catalog, state machines
        from shell.tests.test_niri_config import ConfigurationContracts, OutputContracts
        suite.addTests(loader.loadTestsFromTestCase(ConfigurationContracts))
        suite.addTests(loader.loadTestsFromTestCase(OutputContracts))
        from shell.tests.test_search_catalog import CatalogTests
        suite.addTests(loader.loadTestsFromTestCase(CatalogTests))
        from tests.test_shell import TestShellManagement
        logic_test_names = [
            "test_p3_r10_20x_lifecycle_simulation",
            "test_r2_startup_closure_and_lazy_hosts",
        ]
        for name in logic_test_names:
            if hasattr(TestShellManagement, name):
                suite.addTest(TestShellManagement(name))

    elif category == "RESOURCE":
        # Resource integrity, shaders, icons, i18n
        suite.addTests(loader.loadTestsFromTestCase(ResourceIntegrityTests))
        from tests.test_shell import TestShellManagement
        resource_test_names = [
            "test_r3_brand_paths_and_toml_i18n_contracts",
            "test_r4c_i18n_service_and_catalog_contracts",
            "test_r2_pruned_optional_features_contract",
        ]
        for name in resource_test_names:
            if hasattr(TestShellManagement, name):
                suite.addTest(TestShellManagement(name))

    elif category == "NATIVE":
        # Native IPC, command line arguments, process lifecycle
        from shell.tests.test_display_preview import PreviewContracts
        suite.addTests(loader.loadTestsFromTestCase(PreviewContracts))
        from tests.test_shell_runtime import ShellLauncherTests
        suite.addTests(loader.loadTestsFromTestCase(ShellLauncherTests))
        from tests.test_shell import TestShellManagement
        native_test_names = [
            "test_default_shell_is_noctalia",
            "test_set_shell_valid",
            "test_set_shell_invalid_raises_error",
            "test_cmd_shell_get",
            "test_cmd_shell_set",
            "test_cmd_shell_switch",
            "test_cmd_shell_status",
            "test_preflight_shell",
            "test_ensure_compositor_gateway_scripts",
            "test_hot_switch_success",
            "test_hot_switch_failure_and_rollback",
            "test_r2_lifecycle_exit_sigterm_and_crash_recovery",
            "test_r4c_niri_single_runtime_entry",
        ]
        for name in native_test_names:
            if hasattr(TestShellManagement, name):
                suite.addTest(TestShellManagement(name))

    elif category == "GRAPHICS":
        # Presentation under Weston Wayland
        from tests.test_shell_runtime import ShellPresentationTests
        suite.addTests(loader.loadTestsFromTestCase(ShellPresentationTests))

    return suite


CATEGORIES = [
    ("STATIC", "静态规则测试 (STATIC RULES)", "ARCH001 边界矩阵、LIFE001–006 零违规、shared 纯净度与命名法典"),
    ("LOGIC", "逻辑与算法测试 (LOGIC & ALGORITHMS)", "Niri KDL 解析与冲突裁决、搜索路由生成、生命周期高频仿真"),
    ("RESOURCE", "运行时资源测试 (RUNTIME RESOURCES)", "着色器 QSB 存在性、本地 SVG 图标完整性、双语 TOML 语法与模板"),
    ("NATIVE", "Native 与外部环境测试 (NATIVE / ENVIRONMENT)", "DisplayPreview Unix Socket 模拟、nyxuri-shell 参数形状、双 Shell 热切换"),
    ("GRAPHICS", "图形呈现测试 (GRAPHICS / PRESENTATION)", "Headless Weston + 私有 D-Bus 真实渲染、调色板动态变更感知与导航"),
]


def run_category(code: str, title: str, desc: str, verbose: bool = False) -> tuple[int, int, int, float]:
    """Run a single test category and format the result."""
    suite = build_category_suite(code)
    test_count = suite.countTestCases()
    print(f"\n[{code}] {title}")
    print(f"  说明: {desc}")
    print(f"  用例数: {test_count}")

    start_time = time.monotonic()
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1, stream=sys.stdout)
    result = runner.run(suite)
    elapsed = time.monotonic() - start_time

    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    failed = len(result.failures) + len(result.errors)
    skipped = len(result.skipped)

    status_tag = "[ PASS ]" if failed == 0 else "[ FAIL ]"
    print(f"  --> {code} 小结: {passed} 通过, {failed} 失败, {skipped} 跳过 (耗时 {elapsed:.2f}s) {status_tag}")
    return passed, failed, skipped, elapsed


def main():
    parser = argparse.ArgumentParser(description="Nyxuri Shell Categorized Test Runner (R5)")
    parser.add_argument("--category", choices=["STATIC", "LOGIC", "RESOURCE", "NATIVE", "GRAPHICS"],
                        help="Run only tests from a specific category")
    parser.add_argument("--all", action="store_true", default=True,
                        help="Run all categories (default)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose test execution output")
    args = parser.parse_args()

    selected_categories = CATEGORIES
    if args.category:
        selected_categories = [c for c in CATEGORIES if c[0] == args.category]

    print("=" * 80)
    print("           NYXURI SHELL R5 CATEGORIZED TEST SUITE EXECUTION REPORT           ")
    print("=" * 80)

    summary = []
    total_passed = total_failed = total_skipped = 0
    total_time = 0.0

    for code, title, desc in selected_categories:
        passed, failed, skipped, elapsed = run_category(code, title, desc, verbose=args.verbose)
        summary.append((code, title, passed, failed, skipped, elapsed))
        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        total_time += elapsed

    print("\n" + "=" * 80)
    print("                             五大分类验收总评表                             ")
    print("=" * 80)
    all_ok = True
    for code, title, passed, failed, skipped, elapsed in summary:
        status = "PASSED" if failed == 0 else "FAILED"
        if failed > 0:
            all_ok = False
        print(f"  [{code:<8}] {title:<36} : {passed:>3} passed, {failed:>2} failed, {skipped:>2} skipped ({elapsed:.2f}s) [{status}]")

    print("-" * 80)
    print(f"  全量汇总: {total_passed} 通过, {total_failed} 失败, {total_skipped} 跳过 (总耗时 {total_time:.2f}s)")
    if all_ok and total_failed == 0:
        print("  验收判定: 5 大分类全部独立通过。未采用单一总数掩盖分类缺陷。R5 验收门禁: [ 通过 ]")
        print("=" * 80)
        return 0
    else:
        print("  验收判定: 存在未通过分类！R5 验收门禁: [ 阻断 ]")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())

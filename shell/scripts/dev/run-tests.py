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


from tests.shell.test_resource_integrity import TestResourceIntegrity


def build_category_suite(category: str) -> unittest.TestSuite:
    """Build test suite for a specific category."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if category == "STATIC":
        # Lifecycle and boundary tests
        from tests.shell.test_lifecycle_audit import TestLifecycleAudit
        suite.addTests(loader.loadTestsFromTestCase(TestLifecycleAudit))
        from tests.shell.test_plugin_manifests import (TestPluginManifestSync, TestHostClosure,
                                                       TestEventLoop, TestRetiredMirrors,
                                                       TestZeroHostChangesDiscovery)
        suite.addTests(loader.loadTestsFromTestCase(TestPluginManifestSync))
        suite.addTests(loader.loadTestsFromTestCase(TestHostClosure))
        suite.addTests(loader.loadTestsFromTestCase(TestEventLoop))
        suite.addTests(loader.loadTestsFromTestCase(TestRetiredMirrors))
        suite.addTests(loader.loadTestsFromTestCase(TestZeroHostChangesDiscovery))
        from tests.shell.test_shell import TestShellManagement
        static_test_names = [
            "test_p2_layer_structure_and_session_decoupling",
            "test_p3_settings_decoupling_and_module_structure",
            "test_shell_directory_hygiene_and_module_unification",
            "test_r4c_c05_cpp_toolchain_elimination",
            "test_r4_architecture_and_lifecycle_contracts",
            "test_r4c_domain_reorganization_contract",
            "test_r4c_naming_codex_and_dead_stub_elimination",
            "test_r4c_app_global_boundary_convergence",
            "test_r4c_c06_domain_closure_and_single_state_source",
            "test_r10_action_gateway_and_module_autonomy",
            "test_r11_shell_control_plane_and_transparency",
        ]
        for name in static_test_names:
            if hasattr(TestShellManagement, name):
                suite.addTest(TestShellManagement(name))

    elif category == "LOGIC":
        # Pure logic, KDL parsing, search catalog, state machines
        from tests.shell.test_niri_config import ConfigurationContracts, OutputContracts
        suite.addTests(loader.loadTestsFromTestCase(ConfigurationContracts))
        suite.addTests(loader.loadTestsFromTestCase(OutputContracts))
        from tests.shell.test_search_catalog import CatalogTests
        suite.addTests(loader.loadTestsFromTestCase(CatalogTests))
        from tests.shell.test_shell import TestShellManagement
        logic_test_names = [
            "test_p3_r10_20x_lifecycle_simulation",
            "test_r2_startup_closure_and_lazy_hosts",
        ]
        for name in logic_test_names:
            if hasattr(TestShellManagement, name):
                suite.addTest(TestShellManagement(name))

    elif category == "RESOURCE":
        # Resource integrity, shaders, icons, i18n
        suite.addTests(loader.loadTestsFromTestCase(TestResourceIntegrity))
        from tests.shell.test_shell import TestShellManagement
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
        from tests.shell.test_display_preview import PreviewContracts
        suite.addTests(loader.loadTestsFromTestCase(PreviewContracts))
        from tests.shell.test_shell_runtime import ShellLauncherTests
        suite.addTests(loader.loadTestsFromTestCase(ShellLauncherTests))
        from tests.shell.test_shell import TestShellManagement
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
        from tests.shell.test_shell_runtime import ShellPresentationTests
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

"""Contract tests for P2: True Decoupling & Fault Isolation.

Guarantees the zero-cross-plugin-import invariant and fault isolation:
1. Zero cross-plugin imports across all shell/plugins/
2. Removal of ALLOWED_MODULE_CROSS_IMPORTS allowlist from audit-lifecycle.py
3. Layer purity: shell.qml, services/, ui/, and commons/ have zero imports of plugins/
4. Hot-unplug fault isolation across all 12 plugin domains
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from tests.utils import TempEnv

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL_DIR = REPO_ROOT / "shell"
PLUGINS_DIR = SHELL_DIR / "plugins"
AUDITOR_PATH = SHELL_DIR / "scripts" / "dev" / "audit-lifecycle.py"

def get_all_plugin_domains():
    return sorted(
        d.name for d in PLUGINS_DIR.iterdir()
        if d.is_dir() and d.name != "__pycache__"
    )


def load_auditor_module():
    spec = importlib.util.spec_from_file_location("audit_lifecycle", str(AUDITOR_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestPluginDecouplingContracts(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def test_zero_cross_plugin_imports_in_tree(self):
        """Assert zero static cross-plugin imports exist across the entire plugins/ tree."""
        cross_plugin_violations = []

        for domain in get_all_plugin_domains():
            domain_dir = PLUGINS_DIR / domain
            self.assertTrue(domain_dir.is_dir(), f"Plugin domain {domain} must exist")

            for root, _, files in os.walk(domain_dir):
                for filename in files:
                    if not (filename.endswith(".qml") or filename.endswith(".js")):
                        continue
                    file_path = Path(root) / filename
                    rel_to_shell = file_path.relative_to(SHELL_DIR).as_posix()

                    with open(file_path, "r", encoding="utf-8") as f:
                        for line_idx, line in enumerate(f, 1):
                            s = line.strip()
                            if not s.startswith("import"):
                                continue

                            # Check for module import of other plugins
                            m_mod = re.search(r'import\s+qs\.plugins\.([a-zA-Z0-9_]+)', s)
                            if m_mod:
                                target_domain = m_mod.group(1).lower()
                                if target_domain != domain:
                                    cross_plugin_violations.append(
                                        f"{rel_to_shell}:{line_idx} imports qs.plugins.{target_domain}"
                                    )

                            # Check for relative import into other plugins
                            m_rel = re.search(r'import\s+["\']([^"\']+)["\']', s)
                            if m_rel:
                                import_target = m_rel.group(1)
                                resolved = (file_path.parent / import_target).resolve()
                                try:
                                    target_rel = resolved.relative_to(PLUGINS_DIR).as_posix()
                                    target_domain = target_rel.split("/")[0].lower()
                                    if target_domain != domain:
                                        cross_plugin_violations.append(
                                            f"{rel_to_shell}:{line_idx} relative import {import_target} -> {target_domain}"
                                        )
                                except ValueError:
                                    # Not pointing into plugins/ (e.g. pointing to commons or services)
                                    pass

        self.assertEqual(
            cross_plugin_violations,
            [],
            f"Zero cross-plugin imports permitted in plugins/. Violations found:\n"
            + "\n".join(cross_plugin_violations),
        )

    def test_audit_lifecycle_allowlist_burned(self):
        """Assert ALLOWED_MODULE_CROSS_IMPORTS has been permanently eliminated from the auditor."""
        with open(AUDITOR_PATH, "r", encoding="utf-8") as f:
            auditor_src = f.read()

        self.assertNotIn(
            "ALLOWED_MODULE_CROSS_IMPORTS",
            auditor_src,
            "ALLOWED_MODULE_CROSS_IMPORTS allowlist must be burned permanently",
        )
        self.assertIn("ARCH001", auditor_src, "ARCH001 must be enforced in auditor")

    def test_shell_host_and_shared_layers_purity(self):
        """Assert shell.qml, services/, ui/, and commons/ contain zero plugin imports."""
        # 1. shell.qml
        shell_qml = SHELL_DIR / "shell.qml"
        with open(shell_qml, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                s = line.strip()
                if s.startswith("import") and ("plugins" in s):
                    self.fail(f"shell.qml:{idx} illegally imports plugin: {line.strip()}")

        # 2. services/, ui/, commons/
        for shared_dir in ("services", "ui", "commons"):
            base = SHELL_DIR / shared_dir
            for root, _, files in os.walk(base):
                for filename in files:
                    if not (filename.endswith(".qml") or filename.endswith(".js")):
                        continue
                    file_path = Path(root) / filename
                    rel_path = file_path.relative_to(SHELL_DIR).as_posix()
                    with open(file_path, "r", encoding="utf-8") as f:
                        for idx, line in enumerate(f, 1):
                            s = line.strip()
                            if s.startswith("import") and ("plugins" in s):
                                self.fail(f"{rel_path}:{idx} illegally imports plugin: {line.strip()}")

    def test_hot_unplug_fault_isolation(self):
        """Assert each plugin can be physically unplugged without causing static audit violations in remaining modules."""
        auditor = load_auditor_module()

        # Isolate shell copy in TempEnv
        temp_shell = self.ctx.home / "isolated_shell"
        shutil.copytree(
            SHELL_DIR,
            temp_shell,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )

        for domain in get_all_plugin_domains():
            domain_path = temp_shell / "plugins" / domain
            unplugged_path = temp_shell / "plugins" / f"{domain}.unplugged"

            # Physically unplug plugin
            domain_path.rename(unplugged_path)
            try:
                # Audit remaining tree in-process
                files_to_check = auditor.get_all_target_files(temp_shell)
                violations = []
                for file_path in files_to_check:
                    # Skip files in unplugged folder
                    if f"{domain}.unplugged" in file_path.as_posix():
                        continue
                    v = auditor.check_file_violations(file_path, temp_shell)
                    violations.extend(v)

                self.assertEqual(
                    violations,
                    [],
                    f"Unplugging plugin '{domain}' resulted in {len(violations)} auditor violations in remaining tree:\n"
                    + "\n".join(repr(x) for x in violations),
                )
            finally:
                # Restore plugin
                unplugged_path.rename(domain_path)


if __name__ == "__main__":
    unittest.main()

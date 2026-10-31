"""Ubuntu 与 Arch 的发行版和原生包数据库契约。"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


class TestPlatformDetection(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_known_ubuntu_ids_and_ubuntu_id_like(self):
        from nyxuri.pkg import platform

        for release in (
            {"ID": "ubuntu"}, {"ID": "kubuntu"}, {"ID": "xubuntu"},
            {"ID": "lubuntu"}, {"ID": "ubuntustudio"},
            {"ID": "pop", "ID_LIKE": "ubuntu debian"},
        ):
            with self.subTest(release=release), \
                 patch.object(platform, "_os_release", return_value=release), \
                 patch.object(Path, "is_file", return_value=False), \
                 patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/pacman"):
                self.assertEqual(platform.current_platform(), "ubuntu")

    def test_os_release_parser_reads_only_id_fields_and_unquotes_values(self):
        from nyxuri.pkg import platform

        content = (
            'NAME="Ubuntu Example"\n'
            'ID="Ubuntu"\n'
            'ID_LIKE="Debian ubuntu"\n'
            'VERSION_ID="26.04"\n'
        )
        with patch.object(Path, "read_text", return_value=content):
            self.assertEqual(platform._os_release(), {
                "ID": "ubuntu", "ID_LIKE": "debian ubuntu",
            })

    def test_ubuntu_never_becomes_arch_because_pacman_is_on_path(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "_os_release", return_value={"ID": "ubuntu"}), \
             patch.object(Path, "is_file", return_value=False), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/pacman"):
            self.assertEqual(platform.current_platform(), "ubuntu")

    def test_arch_cachyos_and_unknown_fallbacks(self):
        from nyxuri.pkg import platform

        cases = [
            ({"ID": "arch"}, False, None, "arch"),
            ({"ID": "cachyos"}, False, None, "arch"),
            ({"ID": "manjaro", "ID_LIKE": "arch"}, False, None, "arch"),
            ({"ID": "mystery"}, False, "/usr/bin/pacman", "unsupported"),
            ({}, False, "/usr/bin/pacman", "arch"),
            ({}, False, None, "unsupported"),
        ]
        for release, cachyos_file, pacman, expected in cases:
            with self.subTest(release=release, pacman=pacman), \
                 patch.object(platform, "_os_release", return_value=release), \
                 patch.object(Path, "is_file", return_value=cachyos_file), \
                 patch("nyxuri.pkg.platform.shutil.which", return_value=pacman):
                self.assertEqual(platform.current_platform(), expected)

    def test_backend_availability_requires_platform_commands(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", side_effect=lambda name: {
                 "apt-get": "/usr/bin/apt-get", "dpkg-query": "/usr/bin/dpkg-query",
             }.get(name)):
            self.assertTrue(platform.backend_available())
        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", side_effect=lambda name: {
                 "apt-get": "/usr/bin/apt-get",
             }.get(name)):
            self.assertFalse(platform.backend_available())
        with patch.object(platform, "current_platform", return_value="unsupported"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/apt-get"):
            self.assertFalse(platform.backend_available())


class TestDpkgDatabase(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_normalizes_only_installed_native_architecture_aliases(self):
        from nyxuri.pkg.platform import normalize_dpkg_package_names

        output = (
            "ii  libc6:amd64\n"
            "ii  libc6:i386\n"
            "rc  old-package:amd64\n"
            "un  absent-package\n"
            "malformed\n"
        )
        with patch("nyxuri.pkg.platform._native_architecture", return_value="amd64"):
            self.assertEqual(
                normalize_dpkg_package_names(output),
                {"libc6:amd64", "libc6", "libc6:i386"},
            )

        # Foreign-architecture-only package must not satisfy a manifest's
        # unqualified native package requirement.
        with patch("nyxuri.pkg.platform._native_architecture", return_value="amd64"):
            self.assertEqual(
                normalize_dpkg_package_names("ii  libc6:i386\n"),
                {"libc6:i386"},
            )

    def test_installed_packages_query_uses_dpkg_and_locale_c(self):
        from nyxuri.pkg import platform

        result = subprocess.CompletedProcess(
            [], 0, "ii  libc6:amd64\nii  libc6:i386\nrc  removed\n", "")
        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("nyxuri.pkg.platform._native_architecture", return_value="amd64"), \
             patch("nyxuri.pkg.platform.subprocess.run", return_value=result) as run:
            names = platform.installed_package_names()

        self.assertEqual(names, {"libc6:amd64", "libc6", "libc6:i386"})
        self.assertEqual(run.call_args.args[0], [
            "dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n",
        ])
        self.assertFalse(run.call_args.kwargs["check"])
        self.assertEqual(run.call_args.kwargs["timeout"], 30)
        self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")

    def test_package_version_requires_installed_native_architecture(self):
        from nyxuri.pkg import platform

        output = "ii\tlibc6:amd64\t2.39\n ii\tlibc6:i386\t2.39\n"
        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("nyxuri.pkg.platform._native_architecture", return_value="amd64"), \
             patch("nyxuri.pkg.platform.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, output, "")) as run:
            self.assertEqual(platform.native_package_version("libc6"), "2.39")
            self.assertIsNone(platform.native_package_version("not-installed"))
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args[0], [
            "dpkg-query", "-W", "-f=${db:Status-Abbrev}\\t${binary:Package}\\t${Version}\\n",
            "--", "not-installed",
        ])

    def test_rc_package_state_never_counts_as_installed_or_versioned(self):
        from nyxuri.pkg import platform

        listing = "rc  old-package:amd64\n"
        version = "rc\told-package:amd64\t1.0\n"
        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("nyxuri.pkg.platform._native_architecture", return_value="amd64"), \
             patch("nyxuri.pkg.platform.subprocess.run", side_effect=(
                 subprocess.CompletedProcess([], 0, listing, ""),
                 subprocess.CompletedProcess([], 0, version, ""),
             )):
            self.assertEqual(platform.installed_package_names(), set())
            self.assertIsNone(platform.native_package_version("old-package"))

    def test_package_database_errors_and_timeouts_fail_closed(self):
        from nyxuri.pkg import platform

        for failure in (
            subprocess.CompletedProcess([], 1, "", "dpkg-query failed"),
            subprocess.TimeoutExpired(["dpkg-query"], 30),
            FileNotFoundError("dpkg-query"),
        ):
            with self.subTest(failure=failure), \
                 patch.object(platform, "current_platform", return_value="ubuntu"), \
                 patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/dpkg-query"), \
                 patch("nyxuri.pkg.platform.subprocess.run", side_effect=(failure,)):
                self.assertEqual(platform.installed_package_names(), set())

        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("nyxuri.pkg.platform.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(["dpkg-query"], 15)):
            self.assertIsNone(platform.native_package_version("kitty"))


class TestAptCandidateQueries(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_package_indexes_require_a_configured_index_source(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/apt-cache"), \
             patch("nyxuri.pkg.platform.subprocess.run", return_value=subprocess.CompletedProcess(
                 [], 0, "Package files:\n 100 /var/lib/dpkg/status\n 500 http://archive.ubuntu.com/ubuntu noble/main amd64 Packages\n", "")) as run:
            self.assertTrue(platform.package_indexes_available())
        self.assertEqual(run.call_args.args[0], ["apt-cache", "policy"])
        self.assertEqual(run.call_args.kwargs["timeout"], 30)
        self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")

        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/apt-cache"), \
             patch("nyxuri.pkg.platform.subprocess.run", return_value=subprocess.CompletedProcess(
                 [], 0, "Package files:\n 100 /var/lib/dpkg/status\n", "")):
            self.assertFalse(platform.package_indexes_available())

    def test_candidate_requires_repository_origin_and_requested_version(self):
        from nyxuri.pkg import platform

        sourced = """niri:
  Installed: 26.04
  Candidate: 26.04
  Version table:
 *** 26.04 100
        100 /var/lib/dpkg/status
     500 http://example.invalid stable/main amd64 Packages
    26.03 500
     500 http://example.invalid old/main amd64 Packages
"""
        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/apt-cache"), \
             patch("nyxuri.pkg.platform.subprocess.run", return_value=subprocess.CompletedProcess(
                 [], 0, sourced, "")) as run:
            # Ubuntu 渐进更新只给版本行追加提示，仍必须核对候选与实际索引来源。
            for output in (sourced, sourced.replace("26.04 100", "26.04 100 (phased 80%)")):
                run.return_value = subprocess.CompletedProcess([], 0, output, "")
                self.assertTrue(platform.package_candidate_available("niri"))
                self.assertTrue(platform.package_candidate_available("niri=26.03"))
                self.assertFalse(platform.package_candidate_available("niri=25.00"))
        self.assertEqual(run.call_count, 6)
        self.assertEqual(run.call_args.args[0], ["apt-cache", "policy", "niri"])
        self.assertEqual(run.call_args.kwargs["timeout"], 15)

    def test_candidate_is_false_when_policy_has_only_installed_status(self):
        from nyxuri.pkg import platform

        installed_only = """kitty:
  Installed: 0.42.2
  Candidate: 0.42.2
  Version table:
 *** 0.42.2 100
        100 /var/lib/dpkg/status
"""
        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/apt-cache"), \
             patch("nyxuri.pkg.platform.subprocess.run", return_value=subprocess.CompletedProcess(
                 [], 0, installed_only, "")) as run:
            self.assertFalse(platform.package_candidate_available("kitty"))
        self.assertEqual(run.call_args.args[0], ["apt-cache", "policy", "kitty"])

    def test_candidate_fails_closed_for_invalid_names_missing_tools_and_errors(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/apt-cache"), \
             patch("nyxuri.pkg.platform.subprocess.run") as run:
            for name in ("", "-o=bad", "niri something"):
                with self.subTest(name=name):
                    self.assertFalse(platform.package_candidate_available(name))
            run.assert_not_called()

        for result in (
            subprocess.CompletedProcess([], 1, "", "error"),
            subprocess.CompletedProcess([], 0, "Candidate: (none)\n", ""),
        ):
            with patch.object(platform, "current_platform", return_value="ubuntu"), \
                 patch("nyxuri.pkg.platform.shutil.which", return_value="/usr/bin/apt-cache"), \
                 patch("nyxuri.pkg.platform.subprocess.run", return_value=result):
                self.assertFalse(platform.package_candidate_available("missing"))

        with patch.object(platform, "current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.platform.shutil.which", return_value=None), \
             patch("nyxuri.pkg.platform.subprocess.run") as run:
            self.assertFalse(platform.package_candidate_available("niri"))
            self.assertFalse(platform.package_indexes_available())
            run.assert_not_called()

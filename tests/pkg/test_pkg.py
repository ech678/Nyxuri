"""Shared package adapter contracts: argv, failure propagation and probe scope."""

import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from nyxuri import pkg
from nyxuri.pkg import fzf as cli
from nyxuri.pkg.detection import DependencyProbe
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import json
import os
import sys
from pathlib import Path



class TestPackageAdapter(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)
        arch = patch("nyxuri.pkg.platform.current_platform", return_value="arch")
        arch.start()
        self.addCleanup(arch.stop)

    def test_install_command_shapes(self):
        cases = [
            ("pacman", "repo", ["sudo", "pacman", "-S", "--needed", "--noconfirm", "fish"]),
            ("paru", "aur", ["paru", "-S", "--needed", "--noconfirm", "fish"]),
            ("yay", "repo", ["yay", "-S", "--needed", "--noconfirm", "fish"]),
            ("shelly", "repo", ["shelly", "install", "standard", "--no-confirm", "fish"]),
            ("shelly", "aur", ["shelly", "install", "aur", "--no-confirm", "fish"]),
        ]
        for manager, source, expected in cases:
            with self.subTest(manager=manager, source=source), patch("nyxuri.pkg.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(expected, 0)
                self.assertTrue(pkg.install(["fish", "fish"], source=source, manager=manager))
                run.assert_called_once_with(expected, check=False, capture_output=False, text=True, timeout=1800)

    def test_remove_and_upgrade_commands(self):
        self.assertEqual(pkg.command("remove", ["fish"], manager="pacman"), ["sudo", "pacman", "-Rns", "fish"])
        self.assertEqual(pkg.command("remove", ["fish"], manager="shelly"), ["shelly", "remove", "standard", "fish"])
        self.assertEqual(pkg.command("upgrade", manager="shelly"), ["shelly", "upgrade", "all"])
        self.assertEqual(pkg.command("upgrade", manager="yay"), ["yay", "-Syu"])
        with self.assertRaises(ValueError):
            pkg.command("install", ["aur-pkg"], source="aur", manager="pacman")

    def test_failure_and_timeout_are_not_success(self):
        for failure in (subprocess.CompletedProcess([], 1), subprocess.TimeoutExpired([], 1800), FileNotFoundError("missing")):
            with self.subTest(failure=failure), patch("nyxuri.pkg.subprocess.run") as run:
                if isinstance(failure, Exception):
                    run.side_effect = failure
                else:
                    run.return_value = failure
                self.assertFalse(pkg.install(["fish"], manager="pacman"))

    def test_upgrade_cancellation_does_not_retry_with_another_manager(self):
        with patch("nyxuri.pkg.fzf.preferred_manager", return_value="shelly"), \
             patch("nyxuri.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 130)) as run:
            self.assertEqual(cli.main(["upgrade"]), 130)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["shelly", "upgrade", "all"])

    def test_signal_exit_uses_shell_status(self):
        with patch("nyxuri.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], -2)):
            self.assertEqual(pkg.run(["paru", "-Syu"]).returncode, 130)

    def test_flatpak_remote_failure_stops_install(self):
        with patch("shutil.which", return_value="/usr/bin/flatpak"), \
             patch("nyxuri.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 1)) as run:
            self.assertFalse(pkg.install_flatpaks(["com.qq.QQ"]))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", pkg.FLATHUB_REMOTE_URL])

    def test_probe_caches_only_within_one_inspection(self):
        with patch("nyxuri.pkg.detection.current_platform", return_value="arch"), \
             patch("shutil.which", return_value="/usr/bin/pacman"), \
             patch("nyxuri.pkg.detection.timed_run", side_effect=[
                 subprocess.CompletedProcess([], 0, "old\n"),
                 subprocess.CompletedProcess([], 0, "old\nnew\n"),
             ]) as run:
            first = DependencyProbe()
            self.assertEqual(first.packages, {"old"})
            self.assertEqual(first.packages, {"old"})
            self.assertEqual(DependencyProbe().packages, {"old", "new"})
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args.args, (["pacman", "-Qq"], 30))

    def test_search_preserves_source_and_uses_bounded_query(self):
        with patch("nyxuri.pkg.fzf.preferred_manager", return_value="paru"), \
             patch("nyxuri.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "some-app\n", "")) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["search", "aur", "some"]), 0)
        self.assertEqual(output.getvalue(), "[AUR] some-app\n")
        self.assertEqual(run.call_args.args[0], ["paru", "-Ssq", "--aur", "--", "some"])
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_installer_reports_failed_dependency_batch(self):
        from nyxuri.pkg.deps import install_selected_deps
        with patch("nyxuri.pkg.preferred_manager", return_value="pacman"), \
             patch("nyxuri.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 7)) as run:
            self.assertFalse(install_selected_deps(["fish"]))
        self.assertEqual(run.call_args.args[0], ["sudo", "pacman", "-S", "--needed", "--noconfirm", "fish"])

    def test_shelly_search_decodes_structured_names(self):
        with patch("nyxuri.pkg.fzf.preferred_manager", return_value="shelly"), \
             patch("nyxuri.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 0, '[{"Name":"sample-bin","Description":"Name is not a package"}]', "")) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["search", "aur sample"]), 0)
        self.assertEqual(output.getvalue(), "[AUR] sample-bin\n")
        self.assertEqual(run.call_args.args[0], ["shelly", "search", "aur", "--json", "--", "sample"])

    def test_block_page_is_not_a_package_list(self):
        with patch("nyxuri.pkg.fzf.preferred_manager", return_value="shelly"), \
             patch("nyxuri.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 0, '<html>Blocked</html>', "")), \
             contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["search", "aur sample"]), 1)
        self.assertEqual(output.getvalue(), "")

    def test_selected_sources_reach_shelly_install(self):
        with patch("nyxuri.pkg.platform.current_platform", return_value="arch"), \
             patch("nyxuri.pkg.fzf.preferred_manager", return_value="shelly"), \
             patch("nyxuri.pkg.subprocess.run", side_effect=[
                 subprocess.CompletedProcess([], 0, "fish\n", ""),
                 subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 0),
             ]) as run:
            self.assertEqual(cli.main(["install", "repo/fish", "aur/sample-bin"]), 0)
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ["pacman", "-Slq"], ["shelly", "install", "standard", "fish"],
            ["shelly", "install", "aur", "sample-bin"],
        ])

    def test_tool_help_does_not_create_deployment_state(self):
        from pathlib import Path
        import os
        import sys
        before = set(self.env.home.rglob("*"))
        result = subprocess.run([sys.executable, "-m", "nyxuri", "clean", "--help"],
                                cwd=Path(__file__).resolve().parents[2],
                                env=dict(os.environ), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("clean", result.stdout)
        self.assertEqual(set(self.env.home.rglob("*")), before)


class TestPackageArgv(unittest.TestCase):

    def test_scalar_packages_is_not_split_into_characters(self):
        from nyxuri import pkg
        with patch.object(pkg, "preferred_manager", return_value="pacman"):
            argv = pkg.command("install", "fish")
        self.assertEqual(argv[-1], "fish")
        self.assertNotIn("f", argv)
        with patch.object(pkg, "preferred_manager", return_value="pacman"), \
             patch.object(pkg, "run", return_value=type("R", (), {"returncode": 0})()) as runner:
            pkg.install("fish")
        self.assertEqual(runner.call_args.args[0][-1], "fish")

    def test_shelly_aur_search_passes_the_separator(self):
        from nyxuri.pkg import fzf as cli
        with patch.object(cli, "preferred_manager", return_value="shelly"), \
             patch.object(cli, "run", return_value=type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()) as runner:
            cli.search("aur --regex")
        argv = runner.call_args.args[0]
        self.assertIn("--", argv)
        self.assertEqual(argv[-1], "--regex")

    def test_shelly_remove_classifies_aur_operands(self):
        from nyxuri.pkg import fzf as cli
        with patch("nyxuri.pkg.fzf.current_platform", return_value="arch"), \
             patch.object(cli, "preferred_manager", return_value="shelly"), \
             patch.object(cli, "run") as runner:
            runner.side_effect = [
                type("R", (), {"returncode": 0, "stdout": "repo-pkg\n", "stderr": ""})(),
                type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
            ]
            rc = cli.main(["remove", "aur-pkg"])
            calls = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(rc, 0)
        self.assertEqual(calls[-1][:3], ["shelly", "remove", "aur"])


class TestAptPackageAdapter(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_apt_command_shapes_and_operands(self):
        self.assertEqual(
            pkg.command("install", ["kitty", "niri"], manager="apt"),
            ["sudo", "apt-get", "install", "--", "kitty", "niri"],
        )
        self.assertEqual(
            pkg.command("install", ["kitty=1.2.3"], manager="apt", automatic=True),
            ["sudo", "apt-get", "install", "--yes", "--", "kitty=1.2.3"],
        )
        self.assertEqual(
            pkg.command("remove", ["kitty"], manager="apt"),
            ["sudo", "apt-get", "remove", "--", "kitty"],
        )
        self.assertEqual(pkg.command("upgrade", manager="apt"),
                         ["sudo", "apt-get", "upgrade"])
        with self.assertRaisesRegex(ValueError, "does not accept package names"):
            pkg.command("upgrade", ["kitty"], manager="apt")

    def test_apt_rejects_malformed_operands_and_aur(self):
        for name in ("--purge", "kitty other", "kitty;touch", "kitty="):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Invalid package operand"):
                pkg.command("install", [name], manager="apt")
        with self.assertRaisesRegex(ValueError, "AUR packages are unavailable"):
            pkg.command("install", ["paru-package"], source="aur", manager="apt")
        with self.assertRaisesRegex(ValueError, "AUR packages are unavailable"):
            pkg.command("remove", ["paru-package"], source="aur", manager="apt")

    def test_apt_install_skips_already_installed_packages(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "backend_available", return_value=True), \
             patch.object(platform, "installed_package_names", return_value={"kitty"}), \
             patch.object(platform, "package_indexes_available") as indexes, \
             patch.object(platform, "package_candidate_available") as candidate, \
             patch.object(pkg, "run") as run:
            self.assertTrue(pkg.install(["kitty"], manager="apt"))
        indexes.assert_not_called()
        candidate.assert_not_called()
        run.assert_not_called()

    def test_apt_version_pin_is_not_skipped_for_an_installed_package(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "backend_available", return_value=True), \
             patch.object(platform, "installed_package_names", return_value={"kitty"}), \
             patch.object(platform, "package_indexes_available", return_value=True), \
             patch.object(platform, "package_candidate_available", return_value=True) as candidate, \
             patch.object(pkg, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertTrue(pkg.install(["kitty=1.2.3"], manager="apt"))
        candidate.assert_called_once_with("kitty=1.2.3")
        self.assertEqual(run.call_args.args[0], [
            "sudo", "apt-get", "install", "--yes", "--", "kitty=1.2.3",
        ])

    def test_apt_install_checks_index_and_candidate_before_calling_apt(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "backend_available", return_value=True), \
             patch.object(platform, "installed_package_names", return_value=set()), \
             patch.object(platform, "package_indexes_available", return_value=True), \
             patch.object(platform, "package_candidate_available", return_value=True), \
             patch.object(pkg, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertTrue(pkg.install(["kitty"], manager="apt", automatic=False))
        self.assertEqual(run.call_args.args[0], ["sudo", "apt-get", "install", "--", "kitty"])

    def test_apt_install_fails_closed_without_index_or_candidate(self):
        from nyxuri.pkg import platform

        cases = (
            (False, True, "APT package indexes are unavailable"),
            (True, False, "No candidate was found"),
        )
        for indexes_available, candidate_available, expected in cases:
            with self.subTest(indexes=indexes_available, candidate=candidate_available), \
                 patch.object(platform, "backend_available", return_value=True), \
                 patch.object(platform, "installed_package_names", return_value=set()), \
                 patch.object(platform, "package_indexes_available", return_value=indexes_available), \
                 patch.object(platform, "package_candidate_available", return_value=candidate_available), \
                 patch.object(pkg, "run") as run, \
                 contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertFalse(pkg.install(["kitty"], manager="apt"))
                self.assertIn(expected, stderr.getvalue())
                run.assert_not_called()

    def test_apt_install_fails_when_backend_is_incomplete_or_apt_fails(self):
        from nyxuri.pkg import platform

        with patch.object(platform, "backend_available", return_value=False), \
             patch.object(platform, "installed_package_names") as installed, \
             patch.object(pkg, "run") as run, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(pkg.install(["kitty"], manager="apt"))
        installed.assert_not_called()
        run.assert_not_called()

        with patch.object(platform, "backend_available", return_value=True), \
             patch.object(platform, "installed_package_names", return_value=set()), \
             patch.object(platform, "package_indexes_available", return_value=True), \
             patch.object(platform, "package_candidate_available", return_value=True), \
             patch.object(pkg, "run", return_value=subprocess.CompletedProcess([], 100)) as run:
            self.assertFalse(pkg.install(["kitty"], manager="apt"))
        self.assertEqual(run.call_args.args[0], ["sudo", "apt-get", "install", "--yes", "--", "kitty"])

    def test_apt_search_and_install_reject_aur_without_installing_other_operands(self):
        from nyxuri.pkg import fzf

        with patch.object(fzf, "preferred_manager", return_value="apt"), \
             patch.object(fzf, "run", return_value=subprocess.CompletedProcess(
                 [], 0, "kitty - terminal\n", "")) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(fzf.search("kitty"), 0)
        self.assertEqual(output.getvalue(), "[APT] kitty\n")
        self.assertEqual(run.call_args.args[0], ["apt-cache", "search", "--names-only", "--", "kitty"])
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

        with patch.object(fzf, "preferred_manager", return_value="apt"), \
             patch.object(fzf, "run", return_value=subprocess.CompletedProcess([], 0, "kitty\n", "")) as run, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fzf.main(["install", "repo/kitty", "aur/foo"]), 1)
        self.assertEqual([call.args[0] for call in run.call_args_list], [["apt-cache", "pkgnames"]])

    def test_apt_installed_lists_only_configured_packages_with_matching_query(self):
        from nyxuri.pkg import fzf

        with patch.object(fzf, "preferred_manager", return_value="apt"), \
             patch.object(fzf, "run", return_value=subprocess.CompletedProcess(
                 [], 0, "ii  kitty\nii  kitty-doc\nrc  old-kitty\n", "")) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(fzf.main(["installed", "kitty"]), 0)
        self.assertEqual(output.getvalue(), "kitty\nkitty-doc\n")
        self.assertEqual(run.call_args.args[0], [
            "dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n",
        ])

    def test_apt_info_falls_back_to_dpkg_for_installed_package(self):
        from nyxuri.pkg import fzf

        with patch.object(fzf, "preferred_manager", return_value="apt"), \
             patch.object(fzf, "run", side_effect=(
                 subprocess.CompletedProcess([], 100, "", "no cached package"),
                 subprocess.CompletedProcess([], 0, "Package: kitty\nStatus: install ok installed\n", ""),
             )) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(fzf.main(["info", "kitty"]), 0)
        self.assertEqual(output.getvalue(), "Package: kitty\nStatus: install ok installed\n")
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ["apt-cache", "show", "--", "kitty"],
            ["dpkg-query", "-s", "--", "kitty"],
        ])

    def test_apt_remove_strips_repository_tag_and_rejects_aur_tag(self):
        from nyxuri.pkg import fzf

        with patch.object(fzf, "preferred_manager", return_value="apt"), \
             patch.object(fzf, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(fzf.main(["remove", "repo/kitty"]), 0)
        self.assertEqual(run.call_args.args[0], [
            "sudo", "apt-get", "remove", "--", "kitty",
        ])

        with patch.object(fzf, "preferred_manager", return_value="apt"), \
             patch.object(fzf, "run") as run, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fzf.main(["remove", "aur/kitty-bin"]), 1)
        run.assert_not_called()

    def test_apt_upgrade_preserves_cancellation_status_without_retry(self):
        from nyxuri.pkg import fzf

        with patch.object(fzf, "preferred_manager", return_value="apt"), \
             patch.object(fzf, "run", return_value=subprocess.CompletedProcess([], 130)) as run:
            self.assertEqual(fzf.main(["upgrade"]), 130)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["sudo", "apt-get", "upgrade"])

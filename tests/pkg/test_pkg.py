"""Shared package adapter contracts: argv, failure propagation and probe scope."""

import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from nyxuri.system import pkg
from nyxuri.system import pkg as cli
from nyxuri.system.pkg import DependencyProbe
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

    def test_install_command_shapes(self):
        cases = [
            ("pacman", "repo", ["sudo", "pacman", "-S", "--needed", "--noconfirm", "fish"]),
            ("paru", "aur", ["paru", "-S", "--needed", "--noconfirm", "fish"]),
            ("yay", "repo", ["yay", "-S", "--needed", "--noconfirm", "fish"]),
            ("shelly", "repo", ["shelly", "install", "standard", "--no-confirm", "fish"]),
            ("shelly", "aur", ["shelly", "install", "aur", "--no-confirm", "fish"]),
        ]
        for manager, source, expected in cases:
            with self.subTest(manager=manager, source=source), patch("nyxuri.system.pkg.subprocess.run") as run:
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
            with self.subTest(failure=failure), patch("nyxuri.system.pkg.subprocess.run") as run:
                if isinstance(failure, Exception):
                    run.side_effect = failure
                else:
                    run.return_value = failure
                self.assertFalse(pkg.install(["fish"], manager="pacman"))

    def test_upgrade_cancellation_does_not_retry_with_another_manager(self):
        with patch("nyxuri.system.pkg.preferred_manager", return_value="shelly"), \
             patch("nyxuri.system.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 130)) as run:
            self.assertEqual(cli.main(["upgrade"]), 130)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["shelly", "upgrade", "all"])

    def test_signal_exit_uses_shell_status(self):
        with patch("nyxuri.system.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], -2)):
            self.assertEqual(pkg.run(["paru", "-Syu"]).returncode, 130)

    def test_flatpak_remote_failure_stops_install(self):
        with patch("shutil.which", return_value="/usr/bin/flatpak"), \
             patch("nyxuri.system.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 1)) as run:
            self.assertFalse(pkg.install_flatpaks(["com.qq.QQ"]))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", pkg.FLATHUB_REMOTE_URL])

    def test_probe_caches_only_within_one_inspection(self):
        with patch("shutil.which", return_value="/usr/bin/pacman"), \
             patch("nyxuri.system.pkg.timed_run", side_effect=[
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
        with patch("nyxuri.system.pkg.preferred_manager", return_value="paru"), \
             patch("nyxuri.system.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "some-app\n", "")) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["search", "aur", "some"]), 0)
        self.assertEqual(output.getvalue(), "[AUR] some-app\n")
        self.assertEqual(run.call_args.args[0], ["paru", "-Ssq", "--aur", "--", "some"])
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_installer_reports_failed_dependency_batch(self):
        from nyxuri.system.pkg import install_selected_deps
        with patch("nyxuri.system.pkg.preferred_manager", return_value="pacman"), \
             patch("nyxuri.system.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 7)) as run:
            self.assertFalse(install_selected_deps(["fish"]))
        self.assertEqual(run.call_args.args[0], ["sudo", "pacman", "-S", "--needed", "--noconfirm", "fish"])

    def test_shelly_search_decodes_structured_names(self):
        with patch("nyxuri.system.pkg.preferred_manager", return_value="shelly"), \
             patch("nyxuri.system.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 0, '[{"Name":"sample-bin","Description":"Name is not a package"}]', "")) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["search", "aur sample"]), 0)
        self.assertEqual(output.getvalue(), "[AUR] sample-bin\n")
        self.assertEqual(run.call_args.args[0], ["shelly", "search", "aur", "--json", "--", "sample"])

    def test_block_page_is_not_a_package_list(self):
        with patch("nyxuri.system.pkg.preferred_manager", return_value="shelly"), \
             patch("nyxuri.system.pkg.subprocess.run", return_value=subprocess.CompletedProcess([], 0, '<html>Blocked</html>', "")), \
             contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["search", "aur sample"]), 1)
        self.assertEqual(output.getvalue(), "")

    def test_selected_sources_reach_shelly_install(self):
        with patch("nyxuri.system.pkg.preferred_manager", return_value="shelly"), \
             patch("nyxuri.system.pkg.subprocess.run", side_effect=[
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
        from nyxuri.system import pkg
        with patch.object(pkg, "preferred_manager", return_value="pacman"):
            argv = pkg.command("install", "fish")
        self.assertEqual(argv[-1], "fish")
        self.assertNotIn("f", argv)
        with patch.object(pkg, "preferred_manager", return_value="pacman"), \
             patch.object(pkg, "run", return_value=type("R", (), {"returncode": 0})()) as runner:
            pkg.install("fish")
        self.assertEqual(runner.call_args.args[0][-1], "fish")

    def test_shelly_aur_search_passes_the_separator(self):
        from nyxuri.system import pkg as cli
        with patch.object(cli, "preferred_manager", return_value="shelly"):
            with patch.object(cli, "run", return_value=type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()) as runner:
                cli.search("aur --regex")
        argv = runner.call_args.args[0]
        self.assertIn("--", argv)
        self.assertEqual(argv[-1], "--regex")

    def test_shelly_remove_classifies_aur_operands(self):
        from nyxuri.system import pkg as cli
        with patch.object(cli, "preferred_manager", return_value="shelly"), \
             patch.object(cli, "run") as runner:
            runner.side_effect = [
                type("R", (), {"returncode": 0, "stdout": "repo-pkg\n", "stderr": ""})(),
                type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
            ]
            rc = cli.main(["remove", "aur-pkg"])
            calls = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(rc, 0)
        self.assertEqual(calls[-1][:3], ["shelly", "remove", "aur"])

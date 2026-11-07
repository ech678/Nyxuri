"""Distribution backend contracts: family detection, name mapping, dnf argv and outcome probes."""

import io
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from nyxuri.system import backend, pkg
from tests.utils import TempEnv


class BackendFamilyTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def tearDown(self):
        backend.os_release.cache_clear()

    def test_unknown_host_keeps_arch_default(self):
        backend.os_release.cache_clear()
        with patch.object(backend, "os_release", return_value={}), \
             patch.dict("os.environ", {}, clear=True):
            self.assertEqual(backend.family(), backend.ARCH)
            self.assertEqual(backend.native_manager(), "pacman")
            self.assertTrue(backend.supports_aur())

    def test_fedora_id_selects_dnf_and_drops_aur(self):
        for fields in ({"ID": "fedora"}, {"ID": "nobara"}, {"ID": "some", "ID_LIKE": "rhel fedora"}):
            with self.subTest(fields=fields), \
                 patch.object(backend, "os_release", return_value=fields), \
                 patch.dict("os.environ", {}, clear=True):
                self.assertEqual(backend.family(), backend.FEDORA)
                self.assertEqual(backend.native_manager(), "dnf")
                self.assertFalse(backend.supports_aur())

    def test_arch_ids_win_over_unknown(self):
        for fields in ({"ID": "arch"}, {"ID": "cachyos"}, {"ID": "manjaro", "ID_LIKE": "arch"}):
            with self.subTest(fields=fields), \
                 patch.object(backend, "os_release", return_value=fields), \
                 patch.dict("os.environ", {}, clear=True):
                self.assertEqual(backend.family(), backend.ARCH)

    def test_environment_override_beats_os_release(self):
        with patch.object(backend, "os_release", return_value={"ID": "fedora"}), \
             patch.dict("os.environ", {"NYXURI_PKG_FAMILY": "arch"}, clear=True):
            self.assertEqual(backend.family(), backend.ARCH)
        with patch.object(backend, "os_release", return_value={"ID": "arch"}), \
             patch.dict("os.environ", {"NYXURI_PKG_FAMILY": "fedora"}, clear=True):
            self.assertEqual(backend.family(), backend.FEDORA)

    def test_rename_applies_only_on_fedora(self):
        with patch.object(backend, "family", return_value=backend.FEDORA):
            self.assertEqual(backend.rename("ttf-jetbrains-mono"), "jetbrains-mono-fonts")
            self.assertEqual(backend.rename("python-gobject"), "python3-gobject")
            self.assertEqual(backend.rename("fish"), "fish")
            self.assertEqual(backend.copr("starship"), "atim/starship")
            self.assertIsNone(backend.copr("mpvpaper"))
        with patch.object(backend, "family", return_value=backend.ARCH):
            self.assertEqual(backend.rename("ttf-jetbrains-mono"), "ttf-jetbrains-mono")
            self.assertIsNone(backend.copr("starship"))


class FedoraCommandTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)
        self.no_sudo = patch.object(backend, "needs_superuser_prefix", return_value=False)
        self.no_sudo.start()
        self.addCleanup(self.no_sudo.stop)

    def test_argv_shapes(self):
        with patch.object(backend, "family", return_value=backend.FEDORA):
            self.assertEqual(pkg.command("install", ["fish"], manager="dnf", automatic=True),
                             ["dnf", "install", "-y", "fish"])
            self.assertEqual(pkg.command("remove", ["fish"], manager="dnf"),
                             ["dnf", "remove", "fish"])
            self.assertEqual(pkg.command("upgrade", manager="dnf", automatic=True),
                             ["dnf", "upgrade", "-y"])
            self.assertEqual(pkg.command("install", ["ttf-jetbrains-mono"], manager="dnf"),
                             ["dnf", "install", "jetbrains-mono-fonts"])
            with self.assertRaises(ValueError):
                pkg.command("install", ["aur-only"], source="aur", manager="dnf")

    def test_sudo_prefix_only_without_root(self):
        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(backend, "needs_superuser_prefix", return_value=True), \
             patch("nyxuri.system.pkg.shutil.which", return_value="/usr/bin/sudo"):
            self.assertEqual(pkg.command("install", ["fish"], manager="dnf"),
                             ["sudo", "dnf", "install", "fish"])

    def test_install_translates_skips_and_reports(self):
        stream = io.StringIO()
        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg, "repo_packages", return_value={"fish", "je"}), \
             patch.object(pkg, "run", return_value=subprocess.CompletedProcess([], 0)) as run, \
             redirect_stderr(stream):
            self.assertTrue(pkg.install(["fish", "mpvpaper"]))
        self.assertEqual(run.call_args.args[0], ["dnf", "install", "-y", "fish"])
        self.assertIn("mpvpaper", stream.getvalue())

    def test_absent_names_alone_are_not_a_failure(self):
        stream = io.StringIO()
        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg, "repo_packages", return_value={"fish"}), \
             patch.object(pkg, "run") as run, \
             redirect_stderr(stream):
            self.assertTrue(pkg.install(["mpvpaper", "mangowm"]))
        run.assert_not_called()

    def test_failed_transaction_is_judged_by_installed_state(self):
        failing = subprocess.CompletedProcess([], 1)
        legacy_stream = io.StringIO()
        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg, "repo_packages", return_value={"fish"}), \
             patch.object(pkg, "run", return_value=failing), \
             patch.object(pkg, "_rpm_installed", return_value=True), \
             redirect_stderr(legacy_stream):
            self.assertTrue(pkg.install(["fish"]))
        self.assertIn("scriptlet", legacy_stream.getvalue())

        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg, "repo_packages", return_value={"fish"}), \
             patch.object(pkg, "run", return_value=failing), \
             patch.object(pkg, "_rpm_installed", return_value=False), \
             redirect_stderr(io.StringIO()):
            self.assertFalse(pkg.install(["fish"]))

    def test_copr_channel_is_enabled_before_install(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)

        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg, "repo_packages", return_value={"fish"}), \
             patch.object(pkg, "run", side_effect=fake_run), \
             redirect_stdout(io.StringIO()):
            self.assertTrue(pkg.install(["starship"]))
        self.assertEqual(calls[0], ["dnf", "-y", "copr", "enable", "atim/starship"])
        self.assertEqual(calls[1], ["dnf", "install", "-y", "starship"])

    def test_copr_failure_stops_the_install(self):
        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg, "repo_packages", return_value=set()), \
             patch.object(pkg, "run", return_value=subprocess.CompletedProcess([], 1)), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertFalse(pkg.install(["starship"]))


class FedoraProbeTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_installed_uses_rpm_names(self):
        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg.DependencyProbe, "_query",
                          return_value="jetbrains-mono-fonts\nfish\n"):
            probe = pkg.DependencyProbe()
            self.assertTrue(probe.installed("ttf-jetbrains-mono"))
            self.assertTrue(probe.installed("fish"))
            self.assertFalse(probe.installed("mpvpaper"))

    def test_availability_is_fedora_only(self):
        with patch.object(backend, "family", return_value=backend.FEDORA), \
             patch.object(pkg, "repo_packages", return_value={"fish"}), \
             patch.object(pkg.DependencyProbe, "_query", return_value=""):
            probe = pkg.DependencyProbe()
            self.assertTrue(probe.available("fish"))
            self.assertFalse(probe.available("mpvpaper"))
        with patch.object(backend, "family", return_value=backend.ARCH), \
             patch.object(pkg, "repo_packages") as index:
            self.assertTrue(pkg.DependencyProbe().available("mpvpaper"))
        index.assert_not_called()


if __name__ == "__main__":
    unittest.main()

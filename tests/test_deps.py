"""Behavior contracts for deps: package name mapping, mpvpaper detection via pacman -Qi."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv


class TestOptionalAppPackageMapping(unittest.TestCase):
    """Optional apps must map to correct package names before installation."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_missioncenter_maps_to_mission_center(self):
        """missioncenter key must install 'mission-center' package (hyphen difference)."""
        from nyxniri.deps import install_optional_apps

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            with patch("nyxniri.deps.get_preferred_pkg_manager", return_value=["sudo", "pacman"]):
                with patch("nyxniri.deps.aur_helper_usable", return_value=None):
                    with patch("nyxniri.deps.ensure_aur_helper", return_value=None):
                        with patch("shutil.which", return_value=None):
                            with patch("builtins.print"):
                                install_optional_apps(["missioncenter"])

        # Should have installed mission-center (with hyphen), not missioncenter
        install_cmd = captured_cmds[0]
        self.assertIn("mission-center", install_cmd,
                      "missioncenter must be mapped to 'mission-center' package")
        self.assertNotIn("missioncenter", [a for a in install_cmd if a == "missioncenter"],
                         "Raw 'missioncenter' key must not be passed to pacman")

    def test_fcitx5_rime_installs_full_suite(self):
        """fcitx5-rime must install fcitx5 core + gtk + qt + configtool + rime + rime-ice-git."""
        from nyxniri.deps import install_optional_apps

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            with patch("nyxniri.deps.get_preferred_pkg_manager", return_value=["paru"]):
                with patch("nyxniri.deps.aur_helper_usable", return_value="paru"):
                    with patch("shutil.which", return_value="/usr/bin/fcitx5"):
                        with patch("nyxniri.modules.fcitx.fcitx_install", return_value=True):
                            with patch("builtins.print"):
                                install_optional_apps(["fcitx5-rime"])

        # Find the repo packages command
        repo_cmd = captured_cmds[0]
        for pkg in ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"]:
            self.assertIn(pkg, repo_cmd, f"{pkg} must be in the install command")

        # Find the AUR packages command
        aur_cmd = captured_cmds[1]
        self.assertIn("rime-ice-git", aur_cmd, "rime-ice-git must be installed from AUR")

    def test_fcitx_skin_hook_after_install(self):
        """After installing fcitx5-rime, fcitx_install should be called."""
        from nyxniri.deps import install_optional_apps

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("nyxniri.deps.get_preferred_pkg_manager", return_value=["paru"]):
                with patch("nyxniri.deps.aur_helper_usable", return_value="paru"):
                    with patch("shutil.which", return_value="/usr/bin/fcitx5"):
                        with patch("nyxniri.modules.fcitx.fcitx_install") as mock_fcitx:
                            with patch("builtins.print"):
                                install_optional_apps(["fcitx5-rime"])

                        mock_fcitx.assert_called_once_with()


class TestMpvpaperDetection(unittest.TestCase):
    """mpvpaper version must be checked via pacman -Qi, not binary --version."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_uses_pacman_qi_not_binary_version(self):
        """check_mpvpaper_leak should use pacman -Qi, not mpvpaper --version."""
        from nyxniri.deps import check_mpvpaper_leak

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            mock = MagicMock()
            if "pacman" in cmd and "-Qq" in cmd and "mpvpaper-git" in cmd:
                mock.returncode = 1  # git version not installed
            elif "pacman" in cmd and "-Qi" in cmd and "mpvpaper" in cmd:
                mock.returncode = 0
                mock.stdout = "Name      : mpvpaper\nVersion    : 1.8.2-3\n"
            else:
                mock.returncode = 0
                mock.stdout = ""
            return mock

        with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}" if x in ("pacman", "mpvpaper") else None):
            with patch("subprocess.run", side_effect=fake_run):
                with patch("nyxniri.deps.prompt_confirm", return_value=False):
                    with patch("builtins.print"):
                        check_mpvpaper_leak()

        # Should have called pacman -Qi mpvpaper (not mpvpaper --version)
        pacman_qi_calls = [c for c in captured_cmds if "pacman" in c and "-Qi" in c]
        self.assertTrue(len(pacman_qi_calls) > 0,
                        "Should use pacman -Qi to check mpvpaper version")

        # Should NOT have called mpvpaper --version
        mpvpaper_version_calls = [c for c in captured_cmds if "mpvpaper" in c and "--version" in c]
        self.assertEqual(len(mpvpaper_version_calls), 0,
                         "Should not use 'mpvpaper --version' binary output")

    def test_git_version_short_circuits(self):
        """If mpvpaper-git is installed, should report OK and not check regular version."""
        from nyxniri.deps import check_mpvpaper_leak

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            mock = MagicMock()
            if "pacman" in cmd and "-Qq" in cmd and "mpvpaper-git" in cmd:
                mock.returncode = 0  # git version IS installed
            else:
                mock.returncode = 0
                mock.stdout = ""
            return mock

        with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}" if x in ("pacman",) else None):
            with patch("subprocess.run", side_effect=fake_run):
                with patch("builtins.print") as mock_print:
                    check_mpvpaper_leak()

        # Should not check regular mpvpaper version
        pacman_qi_mpvpaper = [c for c in captured_cmds if "pacman" in c and "-Qi" in c and "mpvpaper" in c]
        self.assertEqual(len(pacman_qi_mpvpaper), 0,
                         "Should not check regular mpvpaper when git version is installed")


class TestAurBootstrapFailsClosed(unittest.TestCase):
    """AUR bootstrap must not execute mutable source builds."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_missing_repo_package_never_builds_from_aur(self):
        from nyxniri.deps import ensure_aur_helper

        commands = []

        def fake_run(cmd, **kwargs):
            commands.append(cmd)
            result = MagicMock(returncode=0, stdout="")
            if cmd[:2] == ["pacman", "-Qq"] or cmd == ["pacman", "-Si", "paru"]:
                result.returncode = 1
            return result

        with patch("subprocess.run", side_effect=fake_run), \
             patch("nyxniri.deps.aur_helper_usable", return_value=None), \
             patch("nyxniri.deps.prompt_confirm", return_value=True), \
             patch("shutil.which", side_effect=lambda name: "/usr/bin/pacman" if name == "pacman" else None), \
             patch("builtins.print"):
            self.assertIsNone(ensure_aur_helper())

        self.assertEqual(commands, [
            ["pacman", "-Qq", "paru-bin"],
            ["pacman", "-Qq", "paru-bin-debug"],
            ["pacman", "-Si", "paru"],
        ])
        self.assertFalse(any(cmd[0] in ("git", "makepkg") for cmd in commands))


if __name__ == "__main__":
    unittest.main()

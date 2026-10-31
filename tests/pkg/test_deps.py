"""Behavior contracts for deps: package mapping via the transaction installer, mpvpaper detection via pacman -Qi."""


import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import io
import subprocess
import sys



class TestMpvpaperDetection(unittest.TestCase):
    """mpvpaper version must be checked via pacman -Qi, not binary --version."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_uses_pacman_qi_not_binary_version(self):
        """check_mpvpaper_leak should use pacman -Qi, not mpvpaper --version."""
        from nyxuri.pkg.deps import check_mpvpaper_leak

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
                with patch("nyxuri.pkg.deps.prompt_confirm", return_value=False):
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
        from nyxuri.pkg.deps import check_mpvpaper_leak

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


class TestFlatpakApps(unittest.TestCase):
    """Flatpak apps must install via the flatpak CLI; IDs never touch pacman.

    供给菜单已处决——契约走事务安装器 ``plugin_package_installer``（on 路径）。
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        configs = self._ctx.home / "configs-src"
        configs.mkdir(exist_ok=True)
        plugin = configs / "someflatpak"
        plugin.mkdir()
        (plugin / "manifest.toml").write_text(
            'packages = []\npackages_flatpak = ["com.example.App"]\n', encoding="utf-8"
        )
        self._ctx.env.plugins_src = configs

    def tearDown(self):
        self._ctx.__exit__()

    def test_flatpak_ids_never_leak_into_pacman(self):
        """pacman gets only 'flatpak'; the ID goes to the flatpak CLI."""
        from nyxuri.pkg import FLATHUB_REMOTE_URL
        from nyxuri.pkg.deps import plugin_package_installer

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            with patch("nyxuri.pkg.preferred_manager", return_value="pacman"):
                with patch("nyxuri.pkg.deps.aur_helper_usable", return_value=None):
                    with patch("nyxuri.pkg.deps.ensure_aur_helper", return_value=None):
                        with patch("shutil.which", side_effect=lambda x: "/usr/bin/flatpak" if x == "flatpak" else None):
                            with patch("builtins.print"):
                                plugin_package_installer("someflatpak", ["com.example.App"])

        repo_cmds = [c for c in captured_cmds if c[:2] == ["sudo", "pacman"]]
        self.assertEqual(len(repo_cmds), 1, "exactly one repo batch expected")
        self.assertIn("flatpak", repo_cmds[0], "flatpak runtime must be provisioned")
        self.assertNotIn("com.example.App", repo_cmds[0], "flatpak ID must not reach pacman")

        remote_cmds = [c for c in captured_cmds if c[:2] == ["flatpak", "remote-add"]]
        self.assertEqual(
            remote_cmds,
            [["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", FLATHUB_REMOTE_URL]],
        )

        install_cmds = [c for c in captured_cmds if c[:2] == ["flatpak", "install"]]
        self.assertEqual(
            install_cmds,
            [["flatpak", "install", "--system", "--noninteractive", "flathub", "com.example.App"]],
        )

        import nyxuri.pkg as pkg_mod
        self.assertFalse(hasattr(pkg_mod, "_FLATPAK_LIST_CACHE"))

    def test_missing_flatpak_binary_skips_flatpak_cli(self):
        """Without the flatpak binary the runtime is still provisioned, but no CLI call."""
        from nyxuri.pkg.deps import plugin_package_installer

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            with patch("nyxuri.pkg.preferred_manager", return_value="pacman"):
                with patch("nyxuri.pkg.deps.aur_helper_usable", return_value=None):
                    with patch("nyxuri.pkg.deps.ensure_aur_helper", return_value=None):
                        with patch("shutil.which", return_value=None):
                            with patch("builtins.print"):
                                plugin_package_installer("someflatpak", ["com.example.App"])

        self.assertFalse(
            any(c[:2] == ["flatpak", "install"] for c in captured_cmds),
            "flatpak CLI must not run without the binary",
        )
        repo_cmd = next(c for c in captured_cmds if c[:2] == ["sudo", "pacman"])
        self.assertIn("flatpak", repo_cmd)

    def test_flatpak_detection_uses_list_columns(self):
        """Detection probes `flatpak list --system --app --columns=application` with LC_ALL=C."""
        from nyxuri.pkg.detection import DependencyProbe
        probe = DependencyProbe()

        captured_cmds = []

        def fake_timed_run(cmd, timeout, **kwargs):
            captured_cmds.append((list(cmd), kwargs))
            result = MagicMock(returncode=0)
            result.stdout = "com.spotify.Client\ncom.qq.QQ\n"
            return result

        with patch("shutil.which", return_value="/usr/bin/flatpak"):
            with patch("nyxuri.pkg.detection.timed_run", side_effect=fake_timed_run):
                self.assertTrue("com.qq.QQ" in probe.flatpaks)
                self.assertFalse("com.tencent.WeChat" in probe.flatpaks)

        self.assertEqual(len(captured_cmds), 1, "probe must be cached across calls")
        cmd, kwargs = captured_cmds[0]
        self.assertEqual(cmd, ["flatpak", "list", "--system", "--app", "--columns=application"])
        self.assertEqual(kwargs.get("env", {}).get("LC_ALL"), "C")


class TestAurBootstrapFailsClosed(unittest.TestCase):
    """AUR bootstrap must not execute mutable source builds."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_missing_repo_package_never_builds_from_aur(self):
        from nyxuri.pkg.deps import ensure_aur_helper

        commands = []

        def fake_run(cmd, **kwargs):
            commands.append(cmd)
            result = MagicMock(returncode=0, stdout="")
            if cmd[:2] == ["pacman", "-Qq"] or cmd == ["pacman", "-Si", "paru"]:
                result.returncode = 1
            return result

        with patch("subprocess.run", side_effect=fake_run), \
             patch("nyxuri.pkg.deps.aur_helper_usable", return_value=None), \
             patch("nyxuri.pkg.deps.prompt_confirm", return_value=True), \
             patch("shutil.which", side_effect=lambda name: "/usr/bin/pacman" if name == "pacman" else None), \
             patch("builtins.print"):
            self.assertIsNone(ensure_aur_helper())

        self.assertEqual(commands, [
            ["pacman", "-Si", "paru"],
        ])
        self.assertFalse(any(cmd[0] in ("git", "makepkg") for cmd in commands))


class TestAurHelperCacheInvalidation(unittest.TestCase):
    """装完 paru 后必须重新探测：首查缓存的「不可用」不得盖住新装的结果。"""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        import nyxuri.pkg.deps as deps_mod

    def tearDown(self):
        import nyxuri.pkg.deps as deps_mod
        self._ctx.__exit__()

    def test_freshly_installed_paru_is_rediscovered_not_uninstalled(self):
        import nyxuri.pkg.deps as deps_mod
        from nyxuri.pkg.deps import ensure_aur_helper

        state = {"installed": False}
        removed = []

        def fake_which(name):
            if name == "pacman":
                return "/usr/bin/pacman"
            if name == "paru":
                return "/usr/bin/paru" if state["installed"] else None
            return None

        def fake_run(cmd, **kwargs):
            result = MagicMock(returncode=1, stdout="")
            if cmd == ["pacman", "-Si", "paru"]:
                result.returncode = 0
            elif cmd[:3] == ["sudo", "pacman", "-S"]:
                state["installed"] = True
                result.returncode = 0
            elif len(cmd) == 2 and cmd[1] == "--version":
                result.returncode = 0
            elif cmd[:3] == ["sudo", "pacman", "-Rdd"]:
                removed.append(cmd)
            return result

        with patch("shutil.which", side_effect=fake_which), \
             patch("nyxuri.pkg.subprocess.run", side_effect=fake_run), \
             patch("nyxuri.pkg.deps.prompt_confirm", return_value=True), \
             patch("builtins.print"):
            self.assertEqual(ensure_aur_helper(), "paru")

        self.assertEqual(removed, [], "freshly installed paru must not be removed")


if __name__ == "__main__":
    unittest.main()


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestDepsMenuReportsFailure(unittest.TestCase):

    def test_failed_install_propagates(self):
        import nyxuri.pkg.deps as deps
        with TempEnv():
            with patch.object(deps.CheckboxList, "run", return_value=["fish"]), \
                 patch.object(deps, "install_selected_deps", return_value=False), \
                 patch.object(deps.sys.stdin, "isatty", return_value=True):
                self.assertFalse(_quiet(deps.run_dep_menu_loop))

    def test_empty_selection_is_success(self):
        import nyxuri.pkg.deps as deps
        with TempEnv():
            with patch.object(deps.CheckboxList, "run", return_value=[]), \
                 patch.object(deps.sys.stdin, "isatty", return_value=True):
                self.assertTrue(_quiet(deps.run_dep_menu_loop))

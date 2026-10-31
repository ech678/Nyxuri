"""Behavior contracts for deps: package name mapping, mpvpaper detection via pacman -Qi."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import io
import subprocess
import sys



class TestOptionalAppPackageMapping(unittest.TestCase):
    """Optional apps must map to correct package names before installation."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self._arch = patch("nyxuri.pkg.platform.current_platform", return_value="arch")
        self._arch.start()

    def tearDown(self):
        self._arch.stop()
        self._ctx.__exit__()

    def test_missioncenter_maps_to_mission_center(self):
        """missioncenter key must install 'mission-center' package (hyphen difference)."""
        from nyxuri.pkg.deps import install_optional_apps

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            with patch("nyxuri.pkg.preferred_manager", return_value="pacman"):
                with patch("nyxuri.pkg.deps.aur_helper_usable", return_value=None):
                    with patch("nyxuri.pkg.deps.ensure_aur_helper", return_value=None):
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
        from nyxuri.pkg.deps import install_optional_apps

        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            with patch("nyxuri.pkg.preferred_manager", return_value="paru"):
                with patch("nyxuri.pkg.deps.aur_helper_usable", return_value="paru"):
                    with patch("shutil.which", return_value="/usr/bin/fcitx5"):
                        with patch("builtins.print"):
                            install_optional_apps(["fcitx5-rime"])

        # Find the repo packages command
        repo_cmd = captured_cmds[0]
        for pkg in ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"]:
            self.assertIn(pkg, repo_cmd, f"{pkg} must be in the install command")

        # Find the AUR packages command
        aur_cmd = captured_cmds[1]
        self.assertIn("rime-ice-git", aur_cmd, "rime-ice-git must be installed from AUR")

    def test_installer_does_not_activate_units(self):
        """Installing packages neither activates a unit nor runs its hooks."""
        from nyxuri.pkg.deps import install_optional_apps

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("nyxuri.pkg.preferred_manager", return_value="paru"):
                with patch("nyxuri.pkg.deps.aur_helper_usable", return_value="paru"):
                    with patch("shutil.which", return_value="/usr/bin/fcitx5"):
                        with patch("nyxuri.kernel.transaction._run_unit_hook") as mock_hook, \
                             patch("nyxuri.kernel.transaction.unit_on") as mock_on:
                            with patch("builtins.print"):
                                install_optional_apps(["fcitx5-rime"])

                        mock_hook.assert_not_called()
                        mock_on.assert_not_called()


class TestMpvpaperDetection(unittest.TestCase):
    """mpvpaper version must be checked via pacman -Qi, not binary --version."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self._arch = patch("nyxuri.pkg.platform.current_platform", return_value="arch")
        self._arch.start()

    def tearDown(self):
        self._arch.stop()
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
    """Flatpak apps must install via the flatpak CLI; IDs never touch pacman."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self._arch = patch("nyxuri.pkg.platform.current_platform", return_value="arch")
        self._arch.start()
        import nyxuri.pkg.deps as deps_mod

    def tearDown(self):
        self._arch.stop()
        self._ctx.__exit__()

    def test_flatpak_ids_never_leak_into_pacman(self):
        """Selecting qq+wechat: pacman gets only 'flatpak'; IDs go to the flatpak CLI."""
        from nyxuri.pkg.deps import FLATHUB_REMOTE_URL, install_optional_apps

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
                                install_optional_apps(["qq", "wechat"])

        repo_cmds = [c for c in captured_cmds if c[:2] == ["sudo", "pacman"]]
        self.assertEqual(len(repo_cmds), 1, "exactly one repo batch expected")
        self.assertIn("flatpak", repo_cmds[0], "flatpak runtime must be provisioned")
        for leaked in ("qq", "wechat", "com.qq.QQ", "com.tencent.WeChat"):
            self.assertNotIn(leaked, repo_cmds[0], f"{leaked} must not reach pacman")

        remote_cmds = [c for c in captured_cmds if c[:2] == ["flatpak", "remote-add"]]
        self.assertEqual(
            remote_cmds,
            [["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", FLATHUB_REMOTE_URL]],
        )

        install_cmds = [c for c in captured_cmds if c[:2] == ["flatpak", "install"]]
        self.assertEqual(
            install_cmds,
            [["flatpak", "install", "--system", "--noninteractive", "flathub", "com.qq.QQ", "com.tencent.WeChat"]],
        )

        import nyxuri.pkg.deps as deps_mod
        self.assertFalse(hasattr(deps_mod, "_FLATPAK_LIST_CACHE"))

    def test_missing_flatpak_binary_skips_flatpak_cli(self):
        """Without the flatpak binary the runtime is still provisioned, but no CLI call."""
        from nyxuri.pkg.deps import install_optional_apps

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
                                install_optional_apps(["spotify"])

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
        self._arch = patch("nyxuri.pkg.platform.current_platform", return_value="arch")
        self._arch.start()

    def tearDown(self):
        self._arch.stop()
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
        self._arch = patch("nyxuri.pkg.platform.current_platform", return_value="arch")
        self._arch.start()
        import nyxuri.pkg.deps as deps_mod

    def tearDown(self):
        import nyxuri.pkg.deps as deps_mod
        self._arch.stop()
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


class TestUbuntuDependencyRouting(unittest.TestCase):
    """Ubuntu 的单元和应用依赖按 APT、Flatpak 与手动资源分流。"""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__)
        self._platform = patch("nyxuri.pkg.platform.current_platform", return_value="ubuntu")
        self._platform.start()
        self.addCleanup(self._platform.stop)
        # 拒绝任何未在具体用例中声明的外部进程；回归误走其他安装分支也不能碰宿主。
        process_guard = patch("subprocess.run", side_effect=AssertionError("Unexpected external process"))
        process_guard.start()
        self.addCleanup(process_guard.stop)

    def test_unit_installer_uses_ubuntu_mapping_and_rejects_undeclared_names(self):
        from nyxuri.pkg.deps import unit_package_installer
        from nyxuri import pkg

        with patch.object(pkg, "install", return_value=True) as install:
            self.assertTrue(unit_package_installer("niri", ["niri"]))
        install.assert_called_once_with(["niri"])

        with patch.object(pkg, "install") as install:
            self.assertFalse(unit_package_installer("niri", ["niri-aur-only-name"]))
        install.assert_not_called()

    def test_selected_core_dependencies_resolve_ubuntu_names(self):
        from nyxuri.pkg.deps import install_selected_deps
        from nyxuri import pkg

        with patch.object(pkg, "install", return_value=True) as install:
            self.assertTrue(install_selected_deps(["fish"]))
        install.assert_called_once_with(["fish"])

        with patch.object(pkg, "install") as install:
            self.assertFalse(install_selected_deps(["not-declared-on-ubuntu"]))
        install.assert_not_called()

    def test_optional_video_player_reports_manual_missing_without_installing(self):
        """显式选择视频能力仍须供给播放器；缺席时不能假报可用或转为 APT/编译。"""
        from nyxuri.pkg import deps
        from nyxuri.pkg.catalog import get_entry
        from nyxuri import pkg

        item = get_entry("mpvpaper")
        self.assertIsNotNone(item)
        with patch.object(deps.DependencyProbe, "installed", return_value=False), \
             patch.object(pkg, "install") as install, \
             patch.object(pkg, "install_flatpaks") as flatpak, \
             contextlib.redirect_stdout(io.StringIO()) as output, \
             contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertFalse(deps.supply_installed(item))
            self.assertFalse(deps.install_optional_apps(["mpvpaper"]))
        install.assert_not_called()
        flatpak.assert_not_called()
        self.assertIn("mpvpaper", error.getvalue())
        self.assertIn("static wallpapers do not require", output.getvalue())
        self.assertIn("provide the mpvpaper executable manually", output.getvalue())

    def test_optional_app_installer_maps_ubuntu_repository_package(self):
        from nyxuri.pkg.deps import install_optional_apps
        from nyxuri import pkg

        with patch.object(pkg, "install", return_value=True) as install, \
             patch.object(pkg, "install_flatpaks") as flatpak:
            self.assertTrue(install_optional_apps(["vscode"]))
        install.assert_called_once_with(["code"])
        flatpak.assert_not_called()

    def _run_flatpak_app_supply(self, apt_runtime_result=0):
        """只替换外部命令结果，保留依赖分流与包管理调用链。"""
        from nyxuri.pkg.deps import install_optional_apps

        commands = []

        def fake_run(argv, **kwargs):
            command = list(argv)
            commands.append(command)
            if command == [
                "dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n",
            ]:
                return subprocess.CompletedProcess(command, 0, "", "")
            if command == ["apt-cache", "policy"]:
                output = "Package files:\n 500 http://archive.example/ubuntu stable/main amd64 Packages\n"
                return subprocess.CompletedProcess(command, 0, output, "")
            if command == ["apt-cache", "policy", "flatpak"]:
                output = (
                    "flatpak:\n  Installed: (none)\n  Candidate: 1.0\n  Version table:\n"
                    "     1.0 500\n        500 http://archive.example/ubuntu stable/main amd64 Packages\n"
                )
                return subprocess.CompletedProcess(command, 0, output, "")
            if command[:3] == ["sudo", "apt-get", "install"]:
                return subprocess.CompletedProcess(command, apt_runtime_result, "", "")
            if command[:2] in (["flatpak", "remote-add"], ["flatpak", "install"]):
                return subprocess.CompletedProcess(command, 0, "", "")
            raise AssertionError(f"Unexpected package command: {command}")

        with patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}" if name in {
            "apt-get", "apt-cache", "dpkg-query", "flatpak",
        } else None), \
             patch("subprocess.run", side_effect=fake_run):
            result = install_optional_apps(["qq", "wechat"])
        return result, commands

    def test_flatpak_apps_use_apt_only_for_runtime_and_flatpak_for_app_ids(self):
        from nyxuri.pkg import FLATHUB_REMOTE_URL

        result, commands = self._run_flatpak_app_supply()

        self.assertTrue(result)
        apt_installs = [cmd for cmd in commands if cmd[:3] == ["sudo", "apt-get", "install"]]
        self.assertEqual(apt_installs, [[
            "sudo", "apt-get", "install", "--yes", "--", "flatpak",
        ]])
        self.assertNotIn("com.qq.QQ", apt_installs[0])
        self.assertNotIn("com.tencent.WeChat", apt_installs[0])

        remote_adds = [cmd for cmd in commands if cmd[:2] == ["flatpak", "remote-add"]]
        self.assertEqual(remote_adds, [[
            "flatpak", "remote-add", "--system", "--if-not-exists", "flathub", FLATHUB_REMOTE_URL,
        ]])
        app_installs = [cmd for cmd in commands if cmd[:2] == ["flatpak", "install"]]
        self.assertEqual(app_installs, [[
            "flatpak", "install", "--system", "--noninteractive", "flathub",
            "com.qq.QQ", "com.tencent.WeChat",
        ]])
        self.assertLess(commands.index(apt_installs[0]), commands.index(remote_adds[0]))
        self.assertLess(commands.index(remote_adds[0]), commands.index(app_installs[0]))

    def test_flatpak_apps_report_failure_when_runtime_apt_install_fails(self):
        result, commands = self._run_flatpak_app_supply(apt_runtime_result=42)

        self.assertFalse(result)
        apt_installs = [cmd for cmd in commands if cmd[:3] == ["sudo", "apt-get", "install"]]
        self.assertEqual(apt_installs, [[
            "sudo", "apt-get", "install", "--yes", "--", "flatpak",
        ]])

    def test_manual_resources_are_never_sent_as_apt_packages(self):
        from nyxuri.pkg.deps import install_optional_apps
        from nyxuri import pkg

        with patch("nyxuri.pkg.deps.DependencyProbe.installed", return_value=False), \
             patch.object(pkg, "install", return_value=True) as install, \
             patch.object(pkg, "install_flatpaks") as flatpak, \
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertFalse(install_optional_apps(["quickshell"]))
        install.assert_called_once_with([
            "quickshell", "matugen", "jq", "qml6-module-qtquick-controls", "qml6-module-qtquick-effects",
            "qml6-module-qtquick-layouts", "qml6-module-qtcore",
            "qml6-module-qt-labs-folderlistmodel", "qml6-module-qt5compat-graphicaleffects",
        ])
        self.assertFalse(any("material-symbols" in name for name in install.call_args.args[0]))
        self.assertIn("material-symbols-rounded-font", stderr.getvalue())
        flatpak.assert_not_called()

    def test_unsupported_optional_unit_never_reaches_a_package_installer(self):
        from nyxuri.pkg.deps import install_optional_apps
        from nyxuri import pkg

        with patch.object(pkg, "install") as install, \
             patch.object(pkg, "install_flatpaks") as flatpak, \
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertFalse(install_optional_apps(["mango"]))
        install.assert_not_called()
        flatpak.assert_not_called()
        self.assertIn("Ubuntu", stderr.getvalue())

    def test_supply_installed_requires_every_declared_manual_font(self):
        from types import SimpleNamespace
        from nyxuri.pkg.catalog import get_entry
        from nyxuri.pkg.deps import supply_installed

        item = get_entry("quickshell")
        self.assertIsNotNone(item)
        probe = SimpleNamespace(
            installed=lambda name: name != "material-symbols-rounded-font",
            flatpaks=set(),
        )
        self.assertFalse(supply_installed(item, probe))

        complete = SimpleNamespace(installed=lambda _name: True, flatpaks=set())
        self.assertTrue(supply_installed(item, complete))

    def test_supply_installed_builds_a_fresh_probe_for_each_inspection(self):
        from nyxuri.pkg.catalog import get_entry
        from nyxuri.pkg.deps import supply_installed
        import nyxuri.pkg.deps as deps

        item = get_entry("quickshell")
        state = {"rounded_font": False}

        class Probe:
            def installed(self, name):
                if name == "material-symbols-rounded-font":
                    return state["rounded_font"]
                return True

            flatpaks = set()

        with patch.object(deps, "DependencyProbe", side_effect=lambda: Probe()) as factory:
            self.assertFalse(supply_installed(item))
            state["rounded_font"] = True
            self.assertTrue(supply_installed(item))
        self.assertEqual(factory.call_count, 2)

    def test_ubuntu_never_attempts_to_bootstrap_an_aur_helper(self):
        import nyxuri.pkg.deps as deps
        from nyxuri.pkg.deps import ensure_aur_helper

        with patch.object(deps.pkg, "run") as run, \
             patch.object(deps.pkg, "install") as install, \
             patch.object(deps, "prompt_confirm") as confirm, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(ensure_aur_helper())
        run.assert_not_called()
        install.assert_not_called()
        confirm.assert_not_called()


if __name__ == "__main__":
    unittest.main()

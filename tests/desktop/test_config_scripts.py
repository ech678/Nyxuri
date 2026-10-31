"""Safety contracts for deployed shell scripts in configs/.

These scripts run inside the user session; their behavior boundaries are
pinned here because the project has no bash test framework.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv

_REPO = Path(__file__).resolve().parents[2]
_TOGGLE = _REPO / "units" / "niri" / "scripts" / "niri-scratch-toggle.sh"
_CLEAN_CACHE = _REPO / "nyxuri" / "desktop" / "clean.py"
_START_NOCTALIA = _REPO / "units" / "niri" / "scripts" / "session-shell.sh"
_SESSION_SHELL = _REPO / "units" / "niri" / "scripts" / "session-shell.sh"
_SHELL_ACTION = _REPO / "units" / "niri" / "scripts" / "shell-action.sh"
_BRIGHTNESS = _REPO / "units" / "niri" / "scripts" / "niri-brightness.sh"


class TestShellAction(unittest.TestCase):
    """Contract tests for shell-action.sh gateway."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.home = self._ctx.home
        self.bin_dir = self.home / "bin"
        self.bin_dir.mkdir()
        self.calls = self.home / "calls"

    def tearDown(self):
        self._ctx.__exit__()

    def _write_command(self, name, body):
        command = self.bin_dir / name
        command.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        command.chmod(0o755)

    def _run_action(self, *args):
        return subprocess.run(
            ["/bin/bash", str(_SHELL_ACTION), *args],
            capture_output=True,
            text=True,
            timeout=10,
            env={
                "PATH": f"{self.bin_dir}:/usr/bin:/bin",
                "HOME": str(self.home),
                "CALLS": str(self.calls),
            },
        )

    def test_actions_map_to_exact_commands(self):
        self._write_command("noctalia", 'printf "%s\\n" "$*" >>"$CALLS"')

        verb_expected = {
            "launcher": "msg panel-toggle launcher",
            "session": "msg panel-toggle session",
            "settings": "msg settings-toggle",
            "clipboard": "msg panel-toggle clipboard",
            "lock": "msg session lock",
            "wallpaper-random": "msg wallpaper-random",
        }

        for verb, expected_args in verb_expected.items():
            self.calls.unlink(missing_ok=True)
            proc = self._run_action(verb)
            self.assertEqual(proc.returncode, 0, f"Action '{verb}' failed: {proc.stderr}")
            self.assertEqual(
                self.calls.read_text(encoding="utf-8").strip(),
                expected_args,
                f"Action '{verb}' did not produce expected arguments",
            )

    def test_translate_runs_deployed_tool_without_arguments(self):
        tool = self.home / ".config" / "noctalia" / "tools" / "orbit-translate.py"
        tool.parent.mkdir(parents=True)
        tool.write_text('#!/bin/sh\nprintf "translate:%s\\n" "$#" >>"$CALLS"\n', encoding="utf-8")
        tool.chmod(0o755)
        proc = self._run_action("translate")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.calls.read_text(encoding="utf-8").strip(), "translate:0")

    def test_unknown_action_refused(self):
        proc = self._run_action("invalid-verb")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Unknown shell action", proc.stderr)

    def test_actions_custom_shell_dispatch(self):
        self._write_command("nyxuri-shell", 'printf "%s\\n" "$*" >>"$CALLS"')

        state_dir = self.home / ".local" / "state" / "nyxuri"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "state.json"
        state_file.write_text('{"active_shell": "custom", "custom_shell_bin": ""}', encoding="utf-8")

        verbs = [
            "launcher",
            "session",
            "settings",
            "clipboard",
            "lock",
            "wallpaper-random",
            "wallpaper-picker",
        ]

        for verb in verbs:
            self.calls.unlink(missing_ok=True)
            proc = self._run_action(verb)
            self.assertEqual(proc.returncode, 0, f"Custom action '{verb}' failed: {proc.stderr}")
            self.assertEqual(
                self.calls.read_text(encoding="utf-8").strip(),
                f"--action {verb}",
                f"Action '{verb}' did not dispatch with --action {verb}",
            )

    def test_actions_nyxuri_shell_dispatch(self):
        self._write_command("nyxuri-shell", 'printf "%s\\n" "$*" >>"$CALLS"')

        state_dir = self.home / ".local" / "state" / "nyxuri"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "state.json"
        state_file.write_text('{"active_shell": "nyxuri-shell", "custom_shell_bin": ""}', encoding="utf-8")

        verbs = [
            "launcher",
            "session",
            "settings",
            "clipboard",
            "lock",
            "wallpaper-random",
            "wallpaper-picker",
        ]

        for verb in verbs:
            self.calls.unlink(missing_ok=True)
            proc = self._run_action(verb)
            self.assertEqual(proc.returncode, 0, f"Nyxuri shell action '{verb}' failed: {proc.stderr}")
            self.assertEqual(
                self.calls.read_text(encoding="utf-8").strip(),
                f"--action {verb}",
                f"Action '{verb}' did not dispatch with --action {verb}",
            )


class TestNoctaliaStartup(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.home = self._ctx.home
        self.bin_dir = self.home / "bin"
        self.bin_dir.mkdir()
        self.calls = self.home / "calls"

    def tearDown(self):
        self._ctx.__exit__()

    def _write_command(self, name, body):
        command = self.bin_dir / name
        command.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        command.chmod(0o755)

    def _run_start(self):
        return subprocess.run(
            ["/bin/bash", str(_START_NOCTALIA)],
            capture_output=True,
            text=True,
            timeout=10,
            env={
                "PATH": f"{self.bin_dir}:/usr/bin:/bin",
                "HOME": str(self.home),
                "CALLS": str(self.calls),
            },
        )

    def test_stale_noctalia_scope_is_stopped_before_start(self):
        self._write_command("systemctl", 'printf "systemctl:%s\\n" "$*" >>"$CALLS"')
        self._write_command("noctalia", 'printf "noctalia\\n" >>"$CALLS"')

        proc = self._run_start()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.calls.read_text(encoding="utf-8").splitlines(),
            [
                "systemctl:--user stop app-niri-noctalia-*.scope",
                "noctalia",
            ],
        )

    def test_session_shell_stops_stale_scope_and_starts(self):
        self._write_command("systemctl", 'printf "systemctl:%s\\n" "$*" >>"$CALLS"')
        self._write_command("noctalia", 'printf "noctalia\\n" >>"$CALLS"')

        proc = subprocess.run(
            ["/bin/bash", str(_SESSION_SHELL)],
            capture_output=True,
            text=True,
            timeout=10,
            env={
                "PATH": f"{self.bin_dir}:/usr/bin:/bin",
                "HOME": str(self.home),
                "CALLS": str(self.calls),
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.calls.read_text(encoding="utf-8").splitlines(),
            [
                "systemctl:--user stop app-niri-noctalia-*.scope",
                "noctalia",
            ],
        )

    def test_session_shell_launches_nyxuri_shell(self):
        self._write_command("systemctl", 'printf "systemctl:%s\n" "$*" >>"$CALLS"')
        self._write_command("nyxuri-shell", 'printf "nyxuri-shell\n" >>"$CALLS"')
        self._write_command("noctalia", 'printf "noctalia\n" >>"$CALLS"')

        state_dir = self.home / ".local" / "state" / "nyxuri"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text('{"active_shell": "nyxuri-shell"}', encoding="utf-8")

        proc = subprocess.run(
            ["/bin/bash", str(_SESSION_SHELL)],
            capture_output=True,
            text=True,
            timeout=10,
            env={
                "PATH": f"{self.bin_dir}:/usr/bin:/bin",
                "HOME": str(self.home),
                "CALLS": str(self.calls),
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.calls.read_text(encoding="utf-8").splitlines(),
            [
                "systemctl:--user stop app-niri-noctalia-*.scope",
                "nyxuri-shell",
            ],
        )

    def test_session_shell_fallback_when_nyxuri_shell_missing(self):
        self._write_command("systemctl", 'printf "systemctl:%s\n" "$*" >>"$CALLS"')
        self._write_command("noctalia", 'printf "noctalia\n" >>"$CALLS"')
        self._write_command("notify-send", 'printf "notify-send:%s\n" "$*" >>"$CALLS"')

        state_dir = self.home / ".local" / "state" / "nyxuri"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text('{"active_shell": "nyxuri-shell", "custom_shell_bin": "/nonexistent/path"}', encoding="utf-8")

        proc = subprocess.run(
            ["/bin/bash", str(_SESSION_SHELL)],
            capture_output=True,
            text=True,
            timeout=10,
            env={
                "PATH": f"{self.bin_dir}:/usr/bin:/bin",
                "HOME": str(self.home),
                "CALLS": str(self.calls),
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        calls = self.calls.read_text(encoding="utf-8").splitlines()
        self.assertIn("noctalia", calls)


class TestScratchToggle(unittest.TestCase):

    def test_clean_and_preserved_legacy_paths_use_engine_command(self):
        with TempEnv() as env:
            bindir = env.home / "bin"
            bindir.mkdir()
            calls = env.home / "calls"
            niri = bindir / "niri"
            niri.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CALLS"\n')
            niri.chmod(0o755)
            for target in ("clean", "clean-cache.py", "~/.config/fish/clean-cache.py", str(env.home / ".config/fish/clean-cache.py")):
                result = subprocess.run(["bash", str(_TOGGLE), target], capture_output=True, text=True,
                                        env={**os.environ, "PATH": f"{bindir}:/usr/bin:/bin", "CALLS": str(calls), "XDG_RUNTIME_DIR": str(env.home)})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls.read_text().splitlines(), ["msg", "action", "spawn", "--", "kitty", "--app-id", "scratchpad", "-e", "nyxuri", "clean"])

    def test_translate_opens_settings_in_scratchpad_kitty(self):
        with TempEnv() as env:
            bindir = env.home / "bin"
            bindir.mkdir()
            calls = env.home / "calls"
            niri = bindir / "niri"
            niri.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CALLS"\n')
            niri.chmod(0o755)
            for target in ("translate", "translate-settings"):
                result = subprocess.run(["bash", str(_TOGGLE), target], capture_output=True, text=True,
                                        env={**os.environ, "PATH": f"{bindir}:/usr/bin:/bin", "CALLS": str(calls), "XDG_RUNTIME_DIR": str(env.home)})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(calls.read_text().splitlines(), [
                    "msg", "action", "spawn", "--", "kitty", "--app-id", "scratchpad", "--title", "Translate",
                    "-e", str(env.home / ".config/noctalia/tools/orbit-translate.py"), "--settings",
                ])

    def test_no_shell_string_execution_fallback(self):
        """Menu cmds are data, not shell input: no `bash -c` fallback may exist."""
        src = _TOGGLE.read_text(encoding="utf-8")
        self.assertNotIn("bash -c", src)

    def test_unknown_cmd_is_refused_not_executed(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / "pwned"
            proc = subprocess.run(
                ["/bin/bash", str(_TOGGLE), f"touch {marker}; echo pwned"],
                capture_output=True, text=True, timeout=10,
                env={"PATH": "/usr/bin:/bin", "HOME": td, "XDG_RUNTIME_DIR": td},
            )
            self.assertIn("refusing", proc.stderr)
            self.assertFalse(marker.exists())


class TestCleanCache(unittest.TestCase):
    """clean-cache v4 契约：围栏删除、干跑纯预览、--only 选择执行、sudo 参数形状。"""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.home = self._ctx.home
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.calls = self.home / "calls"
        self._stubs()
        self._seed()
        # 本类原有用例验证 Arch 清理命令；显式固定平台与工具，避免由宿主发行版决定分支。
        platform = patch("nyxuri.pkg.platform.current_platform", return_value="arch")
        platform.start()
        self.addCleanup(platform.stop)
        home = patch("nyxuri.desktop.clean.HOME", self.home)
        home.start()
        self.addCleanup(home.stop)
        original_which = shutil.which
        tools = patch("shutil.which", side_effect=lambda name: (
            str(self.bin / name) if (self.bin / name).is_file() else original_which(name)
        ))
        tools.start()
        self.addCleanup(tools.stop)

    def _stubs(self):
        log = "printf '%s\\n' \"$*\" >>\"$CALLS\"\n"
        # sudo 模拟器：-v 成功；-Scc 记录 stdin 形状；其余记参数后成功
        self._stub("sudo", (
            log
            + 'if [ "$1" = "-v" ]; then exit 0; fi\n'
            + 'if [ "$1" = "pacman" ] && [ "$2" = "-Scc" ]; then\n'
            + '  cat >>"$CALLS.stdin"\n'
            + '  exit 0\n'
            + 'fi\n'
            + "exit 0\n"
        ))
        self._stub("pacman", log + 'if [ "$1" = "-Qdtq" ]; then printf "foo\\nbar\\n"; fi\n')
        self._stub("flatpak", log)
        # 只会被 sudo stub 拦下、自身从不真正执行的探测项
        self._stub("journalctl")
        self._stub("fstrim")
        self._stub("pacdiff")

    def _stub(self, name, body="exit 0"):
        script = self.bin / name
        script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        script.chmod(0o755)

    def _seed(self):
        self.markers = []
        for rel in (
            ".cache", ".npm", ".thumbnails",
            ".cargo/registry/cache", ".cargo/git/db",
            ".local/share/Trash/files",
            ".local/share/Steam/steamapps/shadercache",
            ".var/app/org.test.App/cache",
        ):
            d = self.home / rel
            d.mkdir(parents=True, exist_ok=True)
            (d / "marker").write_text("x", encoding="utf-8")
            self.markers.append(d / "marker")
        (self.home / ".local/share/flatpak").mkdir(parents=True, exist_ok=True)

    def _env(self):
        return {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.home),
            "LANG": "C", "LC_ALL": "C",
            "CALLS": str(self.calls),
        }

    def _run(self, *args, platform="arch"):
        # 子进程不继承 mock；只注入发行版身份，保留真实 main、任务构造及参数处理。
        driver = (
            "import sys\n"
            "from unittest.mock import patch\n"
            "from nyxuri.desktop.clean import main\n"
            "with patch('nyxuri.pkg.platform._os_release', return_value={'ID': sys.argv[1]}):\n"
            "    sys.exit(main(sys.argv[2:]))\n"
        )
        return subprocess.run(
            [sys.executable, "-c", driver, platform, *args],
            capture_output=True, text=True, timeout=120,
            env=self._env(), stdin=subprocess.DEVNULL, cwd=_REPO,
        )

    def _calls_text(self):
        return self.calls.read_text(encoding="utf-8") if self.calls.exists() else ""

    def test_dry_run_is_pure_preview(self):
        """-n 只读预览：不删文件、不提权、不发变更命令。(#45 延续)"""
        proc = self._run("-n")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        out = proc.stdout + proc.stderr
        self.assertIn("would", out)
        self.assertIn("dry-run", out.lower())
        for marker in self.markers:
            self.assertTrue(marker.exists(), f"dry-run deleted {marker}")
        lines = self._calls_text().splitlines()
        self.assertIn("-Qdtq", lines)
        self.assertNotIn("-v", lines)
        self.assertNotIn("pacman -Scc --noconfirm", lines)
        self.assertNotIn("fstrim -av", lines)

    def test_ubuntu_dry_run_does_not_clean_or_query_pacman(self):
        """APT 干跑仅展示命令；即使 PATH 中有 pacman，也不查询孤立包或执行清理。"""
        self._stub("apt-get", "printf 'apt-get %s\\n' \"$*\" >>\"$CALLS\"\n")
        proc = self._run("-n", platform="ubuntu")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("sudo apt-get clean", proc.stdout)
        calls = self._calls_text().splitlines()
        self.assertNotIn("-Qdtq", calls)
        self.assertNotIn("-v", calls)
        self.assertFalse(any("apt-get" in command or "pacman" in command for command in calls))
        self.assertTrue(all(marker.exists() for marker in self.markers))

    def test_ubuntu_apt_cache_runs_only_download_cache_clean(self):
        """选择 APT 缓存只允许 sudo apt-get clean，不夹带卸载或用户缓存删除。"""
        self._stub("apt-get")
        proc = self._run("--only", "apt-cache", platform="ubuntu")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._calls_text().splitlines(), ["-v", "apt-get clean"])
        self.assertTrue(all(marker.exists() for marker in self.markers))

    def test_ubuntu_does_not_offer_arch_package_cleanup(self):
        """显式要求 Arch 缓存或孤立包任务时，Ubuntu 不生成可执行任务。"""
        self._stub("apt-get")
        proc = self._run("--only", "scc,orphans", platform="ubuntu")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("No matching tasks", proc.stdout)
        self.assertEqual(self._calls_text(), "")

    def test_default_mode_requires_confirmation(self):
        """无 --only 且非交互 stdin：拒绝执行，零改动。"""
        proc = self._run()

        self.assertEqual(proc.returncode, 1)
        for marker in self.markers:
            self.assertTrue(marker.exists(), f"unconfirmed run deleted {marker}")
        self.assertNotIn("pacman -Scc --noconfirm", self._calls_text())

    def test_only_all_runs_and_command_shapes(self):
        """--only all 执行全部：围栏内真删、目录壳保留、sudo 参数形状逐条对得上。"""
        proc = self._run("--only", "all")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        for marker in self.markers:
            self.assertFalse(marker.exists(), f"should be cleaned: {marker}")
        for shell in (".cache", ".npm", ".thumbnails", ".cargo/registry",
                      ".local/share/Trash", ".var/app/org.test.App"):
            self.assertTrue((self.home / shell).is_dir(), f"root dir lost: {shell}")

        lines = self._calls_text().splitlines()
        self.assertIn("-v", lines)
        self.assertIn("-Qdtq", lines)
        self.assertIn("pacman -Scc", lines)
        self.assertNotIn("pacman -Scc --noconfirm", lines)
        # -Scc 两问的 stdin 形状：必须喂 y，--noconfirm 会按默认值答 N
        stdin_log = self.home / "calls.stdin"
        self.assertIn("y\ny\n", stdin_log.read_text(encoding="utf-8"))
        self.assertIn("pacman -Rns --noconfirm foo bar", lines)
        self.assertIn("journalctl --vacuum-time=3d --vacuum-size=100M --rotate", lines)
        self.assertIn("tee /proc/sys/vm/drop_caches", lines)
        self.assertIn("fstrim -av", lines)
        self.assertIn("uninstall --unused --delete-data -y --user", lines)
        self.assertIn("find /var/tmp -mindepth 1 -maxdepth 1 -mtime +7 -exec rm -rf -- {} +", lines)
        if Path("/var/lib/flatpak").is_dir():
            self.assertIn("uninstall --unused --delete-data -y --system", lines)
            self.assertNotIn("flatpak uninstall --unused --delete-data -y --system", lines)
        if (
            Path("/var/cache/pacman/pkg").is_dir()
            and not Path("/var/cache/pacman/pkg").is_symlink()
            and not Path("/var/lib/pacman/db.lck").exists()
        ):
            self.assertIn(
                "find /var/cache/pacman/pkg -mindepth 1 -maxdepth 1 "
                "-type d -name download-* -exec rm -rf -- {} +", lines)
        if Path("/var/lib/systemd/coredump").is_dir():
            self.assertIn(
                "find /var/lib/systemd/coredump -mindepth 1 -maxdepth 1 "
                "-exec rm -rf -- {} +", lines)
        # tee 静默契约：drop_caches 的 "3" 不得回显到终端
        for line in _CLEAN_CACHE.read_text(encoding="utf-8").splitlines():
            if '"tee", "/proc/sys/vm/drop_caches"' in line:
                self.assertIn("quiet=True", line)

    def test_only_selective_skips_unselected(self):
        """--only 只执行命名任务：未选中的系统/用户任务零动作。"""
        proc = self._run("--only", "scc,journal")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        for marker in self.markers:
            self.assertTrue(marker.exists(), f"unselected task deleted {marker}")

        lines = self._calls_text().splitlines()
        self.assertIn("-v", lines)
        self.assertIn("pacman -Scc", lines)
        self.assertIn("journalctl --vacuum-time=3d --vacuum-size=100M --rotate", lines)
        self.assertNotIn("pacman -Rns --noconfirm foo bar", lines)
        self.assertNotIn("tee /proc/sys/vm/drop_caches", lines)
        self.assertNotIn("fstrim -av", lines)
        self.assertNotIn("uninstall --unused --delete-data -y --user", lines)
        self.assertNotIn("uninstall --unused --delete-data -y --system", lines)

    def test_only_rejects_unknown_key(self):
        """--only 非法 key：报错并列出合法值，零动作。"""
        proc = self._run("--only", "cache,bogus")

        self.assertEqual(proc.returncode, 1)
        self.assertIn("bogus", proc.stderr)
        self.assertIn("cache", proc.stderr)
        for marker in self.markers:
            self.assertTrue(marker.exists(), f"invalid run deleted {marker}")

    def test_removed_yes_flag_is_rejected(self):
        """-y 已被移除：报未知参数，零动作。"""
        proc = self._run("-y")

        self.assertEqual(proc.returncode, 1)
        self.assertIn("unknown", proc.stderr)
        for marker in self.markers:
            self.assertTrue(marker.exists(), f"-y run deleted {marker}")

    def test_default_off_excludes_trim_and_nv(self):
        """勾选默认态：TRIM 与 nv 默认不勾，其余默认勾。"""
        src = _CLEAN_CACHE.read_text(encoding="utf-8")
        self.assertIn('DEFAULT_OFF = ("trim", "nv")', src)
        self.assertIn('"trim"', src)
        self.assertIn('"nv"', src)

    def test_clean_cache_skips_nv_and_nv_task_cleans_it(self):
        """nv 着色器独立任务：--only cache 保留 nv，--only nv 清空其内容且保留目录壳。"""
        nv_dir = self.home / ".cache" / "nv"
        gl_cache = nv_dir / "GLCache"
        gl_cache.mkdir(parents=True, exist_ok=True)
        shader_file = gl_cache / "shader.bin"
        shader_file.write_text("bin", encoding="utf-8")

        other_cache = self.home / ".cache" / "other"
        other_cache.mkdir(parents=True, exist_ok=True)
        other_file = other_cache / "file.txt"
        other_file.write_text("txt", encoding="utf-8")

        # 1. 仅执行 cache：普通缓存删除，nv 目录及其内部文件被完整跳过保留
        proc = self._run("--only", "cache")
        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        self.assertFalse(other_file.exists())
        self.assertTrue(shader_file.exists())
        self.assertTrue(nv_dir.is_dir())

        # 2. 显式执行 nv：清空内部着色器，但 nv 目录壳本身依然保留
        proc2 = self._run("--only", "nv")
        self.assertEqual(proc2.returncode, 0, proc2.stderr[-400:])
        self.assertFalse(shader_file.exists())
        self.assertTrue(nv_dir.is_dir())

    def test_failed_task_marks_warning_not_success(self):
        """act 非零退出：任务标 ! 不标 ✓，退出码可读。"""
        self._stub("flatpak", "printf 'flatpak %s\\n' \"$*\" >>\"$CALLS\"\nexit 3\n")

        proc = self._run("--only", "flatpak")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        self.assertIn("exit 3", proc.stderr)
        self.assertNotIn("✓ Remove unused Flatpak", proc.stdout)
        self.assertIn("! Remove unused Flatpak", proc.stdout)

    def test_interrupted_child_reports_signal(self):
        """子进程被信号杀掉：报告信号名而不是裸负数。"""
        self._stub("flatpak", "kill -INT $$\n")

        proc = self._run("--only", "flatpak")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        self.assertIn("SIGINT", proc.stderr)

    def test_symlinked_cache_is_refused(self):
        """围栏：~/.cache 是指向外部的 symlink 时不追、不删、不摘链。"""
        outside = self.home / "outside"
        outside.mkdir()
        (outside / "precious").write_text("keep", encoding="utf-8")
        shutil.rmtree(self.home / ".cache")
        os.symlink(outside, self.home / ".cache")

        proc = self._run("--only", "all")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        self.assertTrue((outside / "precious").exists(), "fence leaked through symlink")
        self.assertTrue((self.home / ".cache").is_symlink(), "symlink was removed")
        self.assertFalse((self.home / ".npm/marker").exists(), "other fences still work")
        self.assertIn("symlink", proc.stderr)

    def test_flatpak_runs_as_user_task_without_sudo_elevation(self):
        """Flatpak 清理为纯用户任务：不走 sudo -v 提权，去 sudo 执行。(#141)"""
        proc = self._run("--only", "flatpak")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        lines = self._calls_text().splitlines()
        self.assertNotIn("-v", lines)
        self.assertIn("uninstall --unused --delete-data -y --user", lines)
        if Path("/var/lib/flatpak").is_dir():
            self.assertIn("uninstall --unused --delete-data -y --system", lines)
            self.assertNotIn("flatpak uninstall --unused --delete-data -y --system", lines)

    def test_scc_cleans_download_dirs_before_pacman_scc(self):
        """pacman -Scc 前置清理 download-*：避免 EISDIR 导致 exit 193。(#141)"""
        proc = self._run("--only", "scc")

        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        lines = self._calls_text().splitlines()
        self.assertIn("pacman -Scc", lines)
        find_cmd = (
            "find /var/cache/pacman/pkg -mindepth 1 -maxdepth 1 "
            "-type d -name download-* -exec rm -rf -- {} +"
        )
        if (
            Path("/var/cache/pacman/pkg").is_dir()
            and not Path("/var/cache/pacman/pkg").is_symlink()
            and not Path("/var/lib/pacman/db.lck").exists()
        ):
            self.assertIn(find_cmd, lines)
            self.assertLess(lines.index(find_cmd), lines.index("pacman -Scc"))

    def test_scc_skips_download_cleanup_when_locked(self):
        """当 db.lck 存在（pacman 正在运行）时，跳过 download-* 目录清理。(#141)"""
        from unittest.mock import patch
        import nyxuri.desktop.clean as clean

        called_cmds = []
        with patch.object(clean, "act", side_effect=lambda cmd, **kw: called_cmds.append((cmd, kw))):
            with patch.object(Path, "is_dir", return_value=True):
                with patch.object(Path, "is_symlink", return_value=False):
                    with patch.object(Path, "exists", return_value=True):
                        tasks = clean.build_tasks({}, [])
                        scc_task = next(t for t in tasks if t["key"] == "scc")
                        scc_task["run"]()

        self.assertEqual(len(called_cmds), 1)
        self.assertEqual(called_cmds[0][0], ["pacman", "-Scc"])

    def test_scc_runs_download_cleanup_when_unlocked(self):
        """当 db.lck 不存在时，先 find 清理 download-* 再调用 pacman -Scc。(#141)"""
        from unittest.mock import patch
        import nyxuri.desktop.clean as clean

        called_cmds = []
        with patch.object(clean, "act", side_effect=lambda cmd, **kw: called_cmds.append((cmd, kw))):
            with patch.object(Path, "is_dir", return_value=True):
                with patch.object(Path, "is_symlink", return_value=False):
                    with patch.object(Path, "exists", return_value=False):
                        tasks = clean.build_tasks({}, [])
                        scc_task = next(t for t in tasks if t["key"] == "scc")
                        scc_task["run"]()

        self.assertEqual(len(called_cmds), 2)
        self.assertEqual(called_cmds[0][0][:4], ["find", "/var/cache/pacman/pkg", "-mindepth", "1"])
        self.assertEqual(called_cmds[1][0], ["pacman", "-Scc"])


class TestBrightnessKeys(unittest.TestCase):
    """niri-brightness.sh: internal backlight vs external DDC fallback."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.home = Path(self._td.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.calls = self.home / "calls"
        self.backlight = self.home / "backlight"
        self.backlight.mkdir()
        self.conf = self.home / ".config" / "noctalia"
        self.conf.mkdir(parents=True)
        (self.conf / "noctalia-config.toml").write_text(
            "[brightness]\nenable_ddcutil = false\n", encoding="utf-8"
        )
        self._stub("noctalia", 'printf "noctalia:%s\\n" "$*" >>"$CALLS"\n')
        self._stub("ddcutil", 'printf "ddcutil:%s\\n" "$*" >>"$CALLS"\n')
        self._stub(
            "niri",
            'if [ "$1" = "msg" ] && [ "$2" = "focused-output" ]; then '
            'printf "%s\\n" "$FOCUSED_OUTPUT"; fi\n',
        )

    def tearDown(self):
        self._td.cleanup()

    def _stub(self, name, body="exit 0"):
        script = self.bin / name
        script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        script.chmod(0o755)

    def _run(self, *args, focused="", backlight=True):
        if backlight:
            (self.backlight / "amdgpu_bl2").mkdir(exist_ok=True)
        elif self.backlight.exists():
            shutil.rmtree(self.backlight)
            self.backlight.mkdir()
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.home),
            "CALLS": str(self.calls),
            "FOCUSED_OUTPUT": focused,
            "NYXURI_BACKLIGHT_DIR": str(self.backlight),
        }
        return subprocess.run(
            ["/bin/bash", str(_BRIGHTNESS), *args],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )

    def _calls(self):
        if not self.calls.exists():
            return []
        return self.calls.read_text(encoding="utf-8").splitlines()

    def test_internal_panel_uses_noctalia_not_ddcutil(self):
        proc = self._run("up", focused='Output "BOE" (eDP-1)')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._calls(), ["noctalia:msg brightness-up"])

    def test_external_panel_keeps_ddcutil_fallback(self):
        proc = self._run("down", focused='Output "DELL" (HDMI-A-1)')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._calls(),
            ["noctalia:msg brightness-down", "ddcutil:setvcp 10 - 10"],
        )

    def test_unknown_connector_with_backlight_skips_ddcutil(self):
        proc = self._run("up", focused="")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._calls(), ["noctalia:msg brightness-up"])

    def test_desktop_without_backlight_uses_ddcutil(self):
        proc = self._run("up", focused="", backlight=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._calls(),
            ["noctalia:msg brightness-up", "ddcutil:setvcp 10 + 10"],
        )

    def test_noctalia_ddc_enabled_does_not_double_step(self):
        (self.conf / "noctalia-config.toml").write_text(
            "[brightness]\nenable_ddcutil = true\n", encoding="utf-8"
        )
        proc = self._run("up", focused='Output "DELL" (DP-1)')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._calls(), ["noctalia:msg brightness-up"])

    def test_bad_args_are_refused(self):
        proc = self._run("sideways", focused='Output "BOE" (eDP-1)')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage", proc.stderr)
        self.assertEqual(self._calls(), [])


class TestKittyConfiguredMouseBindings(unittest.TestCase):
    """用实际Kitty解析默认/transparent配置，确认无无效鼠标绑定且键盘缩放生效。"""

    def test_templates_parse_without_wheel_binding_warnings(self):
        executable = shutil.which("kitty")
        if executable is None:
            self.skipTest("Kitty parser is unavailable")
        driver = (
            "import sys\n"
            "from kitty.config import load_config\n"
            "from kitty.options.utils import parse_shortcut\n"
            "bad = []\n"
            "config = load_config(sys.argv[-1], accumulate_bad_lines=bad)\n"
            "assert not bad, repr(bad)\n"
            "for key, action in [('ctrl+equal','change_font_size all +1.0'),('ctrl+minus','change_font_size all -1.0'),('ctrl+0','change_font_size all 0')]:\n"
            "    mappings = config.keyboard_modes[''].keymap[parse_shortcut(key)]\n"
            "    assert mappings[-1].definition == action, (key, mappings[-1].definition)\n"
        )
        with TempEnv():
            for relative in ("units/kitty/kitty.conf", "units/kitty/__presets__/transparent/kitty.conf"):
                with self.subTest(config=relative):
                    command = [executable, "+runpy", driver, str(_REPO / relative)]
                    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
                    self.assertEqual(command[:2], [executable, "+runpy"])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("not recognized", result.stderr)
                    self.assertNotIn("Ignoring invalid mouse action", result.stderr)


if __name__ == "__main__":
    unittest.main()

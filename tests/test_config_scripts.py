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

from tests.utils import TempEnv

_REPO = Path(__file__).resolve().parent.parent
_TOGGLE = _REPO / "configs" / "niri" / "scripts" / "niri-scratch-toggle.sh"
_CLEAN_CACHE = _REPO / "configs" / "fish" / "clean-cache.py"
_START_NOCTALIA = _REPO / "configs" / "niri" / "scripts" / "start-noctalia.sh"
_BRIGHTNESS = _REPO / "configs" / "niri" / "scripts" / "niri-brightness.sh"


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

    def test_no_matching_scope_does_not_block_start(self):
        self._write_command("systemctl", "exit 1")
        self._write_command("noctalia", 'printf "noctalia\\n" >"$CALLS"')

        proc = self._run_start()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.calls.read_text(encoding="utf-8"), "noctalia\n")


class TestScratchToggle(unittest.TestCase):

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
        self._td = tempfile.TemporaryDirectory()
        self.home = Path(self._td.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.calls = self.home / "calls"
        self._stubs()
        self._seed()

    def tearDown(self):
        self._td.cleanup()

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

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(_CLEAN_CACHE), *args],
            capture_output=True, text=True, timeout=120,
            env=self._env(), stdin=subprocess.DEVNULL,
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
            self.assertIn("flatpak uninstall --unused --delete-data -y --system", lines)
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

    def test_default_off_excludes_trim(self):
        """勾选默认态：TRIM 默认不勾，其余默认勾。"""
        src = _CLEAN_CACHE.read_text(encoding="utf-8")
        self.assertIn('DEFAULT_OFF = ("trim",)', src)
        self.assertIn('"trim"', src)

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
            "NYXNIRI_BACKLIGHT_DIR": str(self.backlight),
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


if __name__ == "__main__":
    unittest.main()

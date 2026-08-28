"""Safety contracts for deployed shell scripts in configs/.

These scripts run inside the user session; their behavior boundaries are
pinned here because the project has no bash test framework.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_TOGGLE = _REPO / "configs" / "niri" / "scripts" / "niri-scratch-toggle.sh"
_CLEAN_CACHE = _REPO / "configs" / "fish" / "clean-cache"


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


class TestCleanCacheDryRun(unittest.TestCase):
    """clean-cache --dry-run 必须是纯计划预览：不 sudo、不删、不动服务。(#45)"""

    def test_dry_run_state_survives_reexec(self):
        """-n 翻译成 auto 后 re-exec 必须透传 dry-run 状态，且初始化不得无条件重置。"""
        src = _CLEAN_CACHE.read_text(encoding="utf-8")
        self.assertIn(": \"${_mc_dryrun:=0}\"", src)
        self.assertIn("_mc_auto=1 _mc_dryrun=1 exec --", src)
        self.assertNotIn("_mc_dryrun=0\n", src)

    def test_all_mutation_commands_are_guarded(self):
        """变更型工具命令必须走 _mc_sudo_wrap 收口或自带 _mc_dryrun 守卫。"""
        import re

        src = _CLEAN_CACHE.read_text(encoding="utf-8")
        offenders = []
        for lineno, line in enumerate(src.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if re.search(r'^\s*(flatpak|npm|pip|go|cargo|gem|paccache|yarn|bun|ccache|snap|docker|journalctl|pkcon|pacman)\s', line) \
                    or "systemctl start" in line:
                if "_mc_sudo_wrap" not in line and "_mc_dryrun" not in line:
                    offenders.append(f"{lineno}: {line.strip()}")
        self.assertEqual(offenders, [])

    def test_dry_run_is_pure_preview(self):
        import subprocess

        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            marker = home / ".cache" / "keep-me-marker"
            marker.parent.mkdir()
            marker.write_text("survive")
            env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "XDG_RUNTIME_DIR": td,
                   "LANG": "C", "USER": "nobody"}
            proc = subprocess.run(
                ["/bin/bash", str(_CLEAN_CACHE), "-n"],
                capture_output=True, text=True, timeout=60, env=env,
                stdin=subprocess.DEVNULL,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
            self.assertIn("Would", proc.stdout + proc.stderr)
            self.assertNotIn("sudo: ", proc.stderr)
            self.assertTrue(marker.exists(), "dry-run deleted a user file")

    def test_auto_mode_still_demands_confirmation_state(self):
        """非 dry-run 的 auto 路径保留 sudo 提示与最终警告，不被 dry-run 修复波及。"""
        src = _CLEAN_CACHE.read_text(encoding="utf-8")
        self.assertIn("_mc_sudo_wrap -k", src)
        self.assertIn("final warning", src.lower())


if __name__ == "__main__":
    unittest.main()

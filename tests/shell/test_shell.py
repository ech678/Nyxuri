"""Contract tests for dual shell management and CLI (nyxuri shell)."""

import glob
import io
import json
import os
import re
import shutil
import signal
import sys
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

from nyxuri.kernel.ledger import active_shell, custom_shell_bin, set_shell
from nyxuri.cli import _cmd_shell
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import subprocess
from pathlib import Path





class TestShellManagement(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        # 本类验证管理状态机；真实runtime供给与QML探针由test_shell_switcher专项覆盖。
        self.runtime_preflight = patch("nyxuri.desktop.shell_runtime.preflight_runtime", return_value="")
        self.runtime_preflight.start()
        self.addCleanup(self.runtime_preflight.stop)

    def tearDown(self):
        self._ctx.__exit__()

    def test_default_shell_is_noctalia(self):
        self.assertEqual(active_shell(), "noctalia")
        self.assertEqual(custom_shell_bin(), "")

    def test_set_shell_valid(self):
        set_shell("nyxuri-shell", "/usr/bin/my-shell")
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/usr/bin/my-shell")

        # Backward compatibility with 'custom' and 'nyxuri'
        set_shell("custom", "/usr/bin/custom-shell")
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/usr/bin/custom-shell")

        set_shell("nyxuri")
        self.assertEqual(active_shell(), "nyxuri-shell")

        set_shell("noctalia")
        self.assertEqual(active_shell(), "noctalia")
        # custom_shell_bin remains recorded
        self.assertEqual(custom_shell_bin(), "/usr/bin/custom-shell")

    def test_set_shell_invalid_raises_error(self):
        with self.assertRaises(ValueError):
            set_shell("invalid_shell")

    def test_cmd_shell_get(self):
        set_shell("noctalia")
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["get"])
        self.assertEqual(ret, 0)
        self.assertEqual(f.getvalue().strip(), "noctalia")

        set_shell("nyxuri-shell")
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["get"])
        self.assertEqual(ret, 0)
        self.assertEqual(f.getvalue().strip(), "nyxuri-shell")

    def test_cmd_shell_set(self):
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["set", "nyxuri-shell", "/bin/sh"])
        self.assertEqual(ret, 0)
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/bin/sh")
        self.assertIn("EXPERIMENTAL", f.getvalue())

        # Test backward-compatible alias 'custom'
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["set", "custom", "/bin/bash"])
        self.assertEqual(ret, 0)
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertEqual(custom_shell_bin(), "/bin/bash")
        self.assertIn("EXPERIMENTAL", f.getvalue())

    def test_cmd_shell_switch(self):
        # 1. Switch with explicit target
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["switch", "noctalia"])
        self.assertEqual(ret, 0)
        self.assertEqual(active_shell(), "noctalia")
        self.assertNotIn("EXPERIMENTAL", f.getvalue())

        # 2. Switch toggle: noctalia -> nyxuri-shell
        with patch("nyxuri.desktop.shell_switcher.hot_switch_shell", return_value=(True, "Switched successfully")) as mock_switch:
            f = io.StringIO()
            with redirect_stdout(f):
                ret = _cmd_shell(["switch"])
            self.assertEqual(ret, 0)
            mock_switch.assert_called_with("nyxuri-shell", None)
            self.assertIn("EXPERIMENTAL", f.getvalue())

        # 3. Switch toggle: nyxuri-shell -> noctalia
        set_shell("nyxuri-shell", "/bin/sh")
        with patch("nyxuri.desktop.shell_switcher.hot_switch_shell", return_value=(True, "Switched successfully")) as mock_switch:
            f = io.StringIO()
            with redirect_stdout(f):
                ret = _cmd_shell(["switch"])
            self.assertEqual(ret, 0)
            mock_switch.assert_called_with("noctalia", None)

        # 4. Switch with alias 'custom'
        with patch("nyxuri.desktop.shell_switcher.hot_switch_shell", return_value=(True, "Switched successfully")) as mock_switch:
            f = io.StringIO()
            with redirect_stdout(f):
                ret = _cmd_shell(["switch", "custom", "/bin/sh"])
            self.assertEqual(ret, 0)
            mock_switch.assert_called_with("nyxuri-shell", "/bin/sh")

    def test_cmd_shell_status(self):
        set_shell("nyxuri-shell", "/bin/sh")
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["status"])
        self.assertEqual(ret, 0)
        output = f.getvalue()
        self.assertIn("EXPERIMENTAL", output)
        self.assertIn("Active Shell: nyxuri-shell", output)
        self.assertIn("Nyxuri Shell Binary: /bin/sh", output)
        self.assertIn("Nyxuri Shell Status: Ready", output)

    def test_preflight_shell(self):
        from nyxuri.desktop.shell_switcher import preflight_shell
        ok, _, err = preflight_shell("invalid")
        self.assertFalse(ok)
        self.assertIn("Unknown target shell", err)

        ok, _, err = preflight_shell("nyxuri-shell", "/nonexistent/path/to/shell")
        self.assertFalse(ok)
        self.assertIn("does not exist", err)

        ok, resolved, err = preflight_shell("nyxuri-shell", "/bin/sh")
        self.assertTrue(ok)
        self.assertEqual(resolved, "/bin/sh")
        self.assertEqual(err, "")

        # Alias custom
        ok, resolved, err = preflight_shell("custom", "/bin/sh")
        self.assertTrue(ok)
        self.assertEqual(resolved, "/bin/sh")

    def test_ensure_compositor_gateway_scripts(self):
        from nyxuri.core import get_env
        from nyxuri.desktop.shell_switcher import ensure_compositor_gateway_scripts
        env = get_env()
        fake_configs = self._ctx.home / "fake_configs"
        env.units_src = fake_configs
        src_dir = fake_configs / "niri" / "scripts"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "session-shell.sh").write_text("#!/bin/sh\necho session new\n", encoding="utf-8")
        (src_dir / "shell-action.sh").write_text("#!/bin/sh\necho action new\n", encoding="utf-8")

        dest_dir = env.config_dir / "niri" / "scripts"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "session-shell.sh").write_text("#!/bin/sh\necho session old\n", encoding="utf-8")
        (dest_dir / "shell-action.sh").write_text("#!/bin/sh\necho action old\n", encoding="utf-8")
        (dest_dir / "session-shell.sh").chmod(0o644)

        # 切换入口只验证事务已经部署的网关，不复制较新的源码，也不偷偷修chmod。
        with self.assertRaisesRegex(RuntimeError, "refresh niri"):
            ensure_compositor_gateway_scripts()
        self.assertEqual((dest_dir / "session-shell.sh").read_text(), "#!/bin/sh\necho session old\n")
        self.assertEqual((dest_dir / "session-shell.sh").stat().st_mode & 0o777, 0o644)

        for name in ("session-shell.sh", "shell-action.sh"):
            (dest_dir / name).chmod(0o755)
        ensure_compositor_gateway_scripts()
        self.assertEqual((dest_dir / "shell-action.sh").read_text(), "#!/bin/sh\necho action old\n")

        (dest_dir / "shell-action.sh").unlink()
        with self.assertRaisesRegex(RuntimeError, "refresh niri"):
            ensure_compositor_gateway_scripts()
        self.assertFalse((dest_dir / "shell-action.sh").exists())
        self.assertEqual((dest_dir / "session-shell.sh").read_text(), "#!/bin/sh\necho session old\n")

    @patch("nyxuri.desktop.shell_switcher.stop_all_shell_instances")
    @patch("nyxuri.desktop.shell_switcher.wait_shell_ready")
    @patch("nyxuri.desktop.shell_switcher.spawn_shell")
    @patch("nyxuri.desktop.shell_switcher.stop_shell_process")
    @patch("nyxuri.desktop.shell_switcher.probe_running_shells")
    def test_hot_switch_success(self, mock_probe, mock_stop, mock_spawn, mock_wait, mock_sweep):
        import os
        from unittest.mock import MagicMock
        from nyxuri.desktop.shell_switcher import hot_switch_shell

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        mock_probe.return_value = [("noctalia", 1234)]
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_spawn.return_value = mock_proc
        mock_wait.return_value = True

        ok, msg = hot_switch_shell("nyxuri-shell", "/bin/sh")
        self.assertTrue(ok)
        self.assertIn("Successfully switched to nyxuri-shell", msg)
        self.assertEqual(active_shell(), "nyxuri-shell")
        self.assertTrue(mock_stop.called)
        mock_spawn.assert_called_once_with("nyxuri-shell", "/bin/sh")
        mock_wait.assert_called_once()
        # R10-fix: the field sweep must cover BOTH kinds before spawning.
        swept = {call.args[0] for call in mock_sweep.call_args_list}
        self.assertIn("nyxuri-shell", swept)
        self.assertIn("noctalia", swept)

    @patch("nyxuri.desktop.shell_switcher.stop_all_shell_instances")
    @patch("nyxuri.desktop.shell_switcher.wait_shell_ready")
    @patch("nyxuri.desktop.shell_switcher.spawn_shell")
    @patch("nyxuri.desktop.shell_switcher.stop_shell_process")
    @patch("nyxuri.desktop.shell_switcher.probe_running_shells")
    def test_hot_switch_failure_and_rollback(self, mock_probe, mock_stop, mock_spawn, mock_wait, mock_sweep):
        import os
        from unittest.mock import MagicMock
        from nyxuri.desktop.shell_switcher import hot_switch_shell

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        mock_probe.return_value = [("noctalia", 1234)]
        mock_new_proc = MagicMock()
        mock_new_proc.poll.return_value = None
        mock_restore_proc = MagicMock()
        mock_spawn.side_effect = [mock_new_proc, mock_restore_proc]
        # Target fails readiness, restore succeeds
        mock_wait.side_effect = [False, True]

        ok, msg = hot_switch_shell("nyxuri-shell", "/bin/sh")
        self.assertFalse(ok)
        self.assertIn("failed readiness probe", msg)
        self.assertIn("rolled back to noctalia", msg)
        # Ledger must NOT have been changed to target
        self.assertEqual(active_shell(), "noctalia")
        mock_new_proc.terminate.assert_called()

    @patch("nyxuri.desktop.shell_switcher.set_shell")
    @patch("nyxuri.desktop.shell_switcher.stop_all_shell_instances")
    @patch("nyxuri.desktop.shell_switcher.stop_shell_process")
    @patch("nyxuri.desktop.shell_switcher.probe_running_shells")
    def test_switch_cleans_lingering_side_when_target_already_running(
            self, mock_probe, mock_stop, mock_sweep, mock_set_shell):
        """R10-fix: target up + other shell lingering is residue, not success."""
        from nyxuri.desktop.shell_switcher import hot_switch_shell
        import os

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        # First inventory: both alive. After the side sweep: target only.
        mock_probe.side_effect = [
            [("nyxuri-shell", 111), ("noctalia", 222)],
            [("nyxuri-shell", 111)],
        ]
        mock_stop.return_value = True

        ok, msg = hot_switch_shell("nyxuri-shell", "/bin/sh")
        self.assertTrue(ok)
        self.assertIn("cleaned lingering residue", msg)
        self.assertIn("noctalia(222)", msg)
        # The noctalia residue was the object of the stop, not the target.
        stopped = [call.args[:2] for call in mock_stop.call_args_list]
        self.assertIn(("noctalia", 222), stopped)
        mock_set_shell.assert_called_once()

    @patch("nyxuri.desktop.shell_switcher.stop_all_shell_instances")
    @patch("nyxuri.desktop.shell_switcher.wait_shell_ready")
    @patch("nyxuri.desktop.shell_switcher.spawn_shell")
    @patch("nyxuri.desktop.shell_switcher.stop_shell_process")
    @patch("nyxuri.desktop.shell_switcher.probe_running_shells")
    def test_switch_towards_noctalia_sweeps_noctalia_residue(
            self, mock_probe, mock_stop, mock_spawn, mock_wait, mock_sweep):
        """R10-fix: the old code swept nyxuri-shell when targeting noctalia —
        exactly how a surviving noctalia blocked every later attempt."""
        import os
        from unittest.mock import MagicMock
        from nyxuri.desktop.shell_switcher import hot_switch_shell

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        mock_probe.return_value = [("nyxuri-shell", 34529)]
        mock_proc = MagicMock()
        mock_proc.pid = 64899
        mock_spawn.return_value = mock_proc
        mock_wait.return_value = True

        ok, msg = hot_switch_shell("noctalia", "")
        self.assertTrue(ok)
        swept = {call.args[0] for call in mock_sweep.call_args_list}
        self.assertIn("noctalia", swept)
        self.assertIn("nyxuri-shell", swept)

    def test_noctalia_readiness_requires_ipc_answer(self):
        """R10-fix: `noctalia msg` has no ping; the old alive-past-1s branch
        reported ready while the previous shell was still running."""
        import time
        from unittest.mock import MagicMock, patch
        from nyxuri.desktop.shell_switcher import wait_shell_ready

        proc = MagicMock()
        proc.poll.return_value = None

        real_sleep = time.sleep
        with patch("nyxuri.desktop.shell_switcher.subprocess.run", return_value=MagicMock(returncode=7)) as run_mock, \
             patch("nyxuri.desktop.shell_switcher.time.sleep", side_effect=lambda *_: None):
            start = time.time()
            self.assertFalse(wait_shell_ready("noctalia", proc, "/usr/bin/noctalia", timeout=0.4))
            self.assertLess(time.time() - start, 3.0)
        probed = run_mock.call_args_list[0].args[0]
        self.assertEqual(probed, ["noctalia", "msg", "theme-mode-get"])

        with patch("nyxuri.desktop.shell_switcher.subprocess.run", return_value=MagicMock(returncode=0)):
            self.assertTrue(wait_shell_ready("noctalia", proc, "/usr/bin/noctalia", timeout=2.0))
        real_sleep(0)

    def test_stop_shell_process_escalates_and_reports_survivor(self):
        """R10-fix: SIGKILL delivery is observed, not assumed; a survivor
        must surface as False so the switcher can re-sweep."""
        import signal
        from unittest.mock import patch
        from nyxuri.desktop.shell_switcher import stop_shell_process

        # PID checks always report alive: SIGTERM then SIGKILL both land, the
        # process survives them all -> False.
        def alive_kill(pid, sig):
            if sig == signal.SIGTERM:
                raise InterruptedError
        with patch("nyxuri.desktop.shell_switcher.os.kill", side_effect=alive_kill), \
             patch("nyxuri.desktop.shell_switcher.time.sleep", side_effect=lambda *_: None):
            self.assertFalse(stop_shell_process("noctalia", 222, "", timeout=0.2))

        # PID disappears after SIGTERM: bounded wait observes it -> True.
        kills = []
        def gone_after_term(pid, sig):
            kills.append(sig)
            if sig == signal.SIGTERM:
                raise InterruptedError
            raise ProcessLookupError
        with patch("nyxuri.desktop.shell_switcher.os.kill", side_effect=gone_after_term), \
             patch("nyxuri.desktop.shell_switcher.time.sleep", side_effect=lambda *_: None):
            self.assertTrue(stop_shell_process("noctalia", 222, "", timeout=0.2))
        self.assertEqual(kills[0], signal.SIGTERM)


class TestIssue140NoctaliaTemplatesDoNotCauseUnitDrift(unittest.TestCase):
    """Issue #140: Noctalia template rendering must not mutate kitty/niri/starship

    Enabling noctalia triggers render-gtk and templates-apply. The template
    products must not overwrite managed blueprint files or cause kitty, niri,
    or starship to report Drifted in doctor audit.
    """

    def test_units_remain_synced_after_noctalia_template_rendering(self):
        from nyxuri.kernel import ledger, transaction
        from nyxuri.desktop import owned_outputs
        import tomllib

        with TempEnv() as ctx, \
             patch("nyxuri.pkg.platform.current_platform", return_value="arch"), \
             patch("nyxuri.pkg.detection.DependencyProbe.installed", return_value=True) as installed:
            # 本例只验证部署/渲染归属：完整声明的依赖视为已供应，不读取宿主包数据库。
            # 真实daemon hook在专项测试中验收，这里通过实际暂存提交入口模拟其渲染结果。
            for uid in ("kitty", "starship", "niri", "noctalia"):
                steps = transaction.unit_on(uid, run_hooks=False)
                self.assertTrue(all(step.ok for step in steps), f"failed to enable {uid}: {steps}")
            requested = {entry.args[0] for entry in installed.call_args_list}
            self.assertTrue({"wl-clipboard", "python-cairo"}.issubset(requested))
            self.assertEqual(ledger.get_unit("theme")["state"], "enabled")

            config = ctx.env.config_dir / "noctalia/noctalia-config.toml"
            templates = tomllib.loads(config.read_text())["theme"]["templates"]["user"]
            self.assertIn("nyxuri_kitty", templates)
            self.assertIn("nyxuri_niri_glow_material_you", templates)
            self.assertNotIn("nyxuri_mango", templates)
            self.assertNotIn("nyxmellow_theme", templates)
            payloads = {
                "nyxuri_kitty": b"color0 #000000\n",
                "nyxuri_niri_glow_material_you": b'layout { focus-ring { active-color "#ffffff" } }\n',
            }
            for name, content in payloads.items():
                stage = Path(templates[name]["output_path"])
                self.assertTrue(stage.is_relative_to(ctx.env.state_dir))
                stage.write_bytes(content)
                self.assertTrue(owned_outputs.commit_template(name))
            self.assertEqual((ctx.env.config_dir / "kitty/themes/noctalia.conf").read_bytes(), payloads["nyxuri_kitty"])
            self.assertEqual((ctx.env.config_dir / "niri/colors.kdl").read_bytes(), payloads["nyxuri_niri_glow_material_you"])
            self.assertIn(ctx.env.config_dir / "kitty/themes/noctalia.conf", owned_outputs.managed_paths())

            report = transaction.audit_units()
            for uid in ("kitty", "starship", "niri", "noctalia"):
                self.assertEqual(report.get(uid), "Synced", uid)

            # 停用后旧守护进程排队的渲染也不能重建消费者目录。
            steps = transaction.unit_off("kitty")
            self.assertTrue(all(step.ok for step in steps), steps)
            self.assertTrue(owned_outputs.commit_template("nyxuri_kitty"))
            self.assertFalse((ctx.env.config_dir / "kitty/themes/noctalia.conf").exists())
            self.assertEqual(transaction.audit_units().get("noctalia"), "Synced")

"""验证 GTK 渲染钩子的真实返回值与 IPC 顺序，避免复制配置被当成渲染成功。"""

import contextlib
import io
import os
import sys
import hashlib
import json
import shutil
import tomllib
from pathlib import Path
import runpy
import signal
import subprocess
import unittest
from unittest.mock import call, patch

from tests.utils import TempEnv


class TestNoctaliaRenderHook(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        hook = Path(__file__).resolve().parents[2] / "units/noctalia/hooks/render-gtk"
        # 加载交付脚本本身；只替换外部进程边界，不重写钩子的成功/失败逻辑。
        self.main = runpy.run_path(str(hook))["main"]

    def invoke(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = self.main()
        return status, output.getvalue()

    @staticmethod
    def expected_calls():
        return [
            call(["noctalia", "msg", "config-reload"], timeout=15, check=False,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            call(["noctalia", "msg", "templates-apply"], timeout=30, check=False,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        ]

    def test_missing_executable_is_pending_without_ipc(self):
        with patch("shutil.which", return_value=None), patch("subprocess.run") as runner:
            status, output = self.invoke()
        self.assertEqual(status, 1)
        self.assertIn("pending", output)
        runner.assert_not_called()

    def test_reload_failure_stops_before_template_application(self):
        with patch("shutil.which", return_value="/fixture/noctalia"), \
             patch("subprocess.run", return_value=subprocess.CompletedProcess([], 7)) as runner:
            status, output = self.invoke()
        self.assertEqual(status, 1)
        self.assertIn("remain pending", output)
        self.assertEqual(runner.call_args_list, self.expected_calls()[:1])

    def test_template_failure_is_not_reported_as_rendered(self):
        with patch("shutil.which", return_value="/fixture/noctalia"), \
             patch("subprocess.run", side_effect=[
                 subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1),
             ]) as runner:
            status, output = self.invoke()
        self.assertEqual(status, 1)
        self.assertNotIn("templates rendered", output)
        self.assertEqual(runner.call_args_list, self.expected_calls())

    def test_timeout_or_os_error_is_pending_at_either_stage(self):
        for error in (OSError("unavailable"), subprocess.TimeoutExpired("noctalia", 15)):
            for stage in (0, 1):
                with self.subTest(error=type(error).__name__, stage=stage), \
                     patch("shutil.which", return_value="/fixture/noctalia"), \
                     patch("subprocess.run", side_effect=[
                         *[subprocess.CompletedProcess([], 0) for _ in range(stage)], error,
                     ]) as runner:
                    status, output = self.invoke()
                self.assertEqual(status, 1)
                self.assertIn("retry", output)
                self.assertEqual(runner.call_args_list, self.expected_calls()[:stage + 1])

    def test_success_requires_reload_then_apply(self):
        with patch("shutil.which", return_value="/fixture/noctalia"), \
             patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as runner:
            status, output = self.invoke()
        self.assertEqual(status, 0)
        self.assertIn("templates rendered", output)
        self.assertEqual(runner.call_args_list, self.expected_calls())


class TestExternalOutputLifecycle(unittest.TestCase):
    """验证已批准的跨目录原值恢复、个人修改及停用后渲染场景。"""

    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        from nyxuri.desktop import owned_outputs
        self.outputs = owned_outputs

    def enable(self, unit_id):
        from nyxuri.kernel import ledger
        # 既有用例启用 theme 时同时准备真实模板，符合事务先部署再注册消费者的顺序。
        if unit_id == "theme":
            shutil.copytree(self.ctx.env.units_src / "theme",
                            self.ctx.env.config_dir / "nyxuri/templates", dirs_exist_ok=True)
        config = self.ctx.env.config_dir / "noctalia/noctalia-config.toml"
        files = ({"noctalia-config.toml": hashlib.sha256(config.read_bytes()).hexdigest()}
                 if unit_id == "noctalia" and config.is_file() else {})
        ledger.set_unit(unit_id, state="enabled", files=files)

    def test_restore_original_and_preserve_later_user_changes(self):
        css = self.ctx.home / ".config/gtk-3.0/gtk.css"
        css.parent.mkdir(parents=True)
        css.write_bytes(b"personal original")
        self.assertFalse(self.outputs.write_output("noctalia", "theme", css, b"rendered"))
        self.assertEqual(css.read_bytes(), b"personal original")
        self.assertTrue(self.outputs.write_output("noctalia", "theme", css, b"rendered", force=True))
        self.outputs.withdraw_outputs(producer="noctalia")
        self.assertEqual(css.read_bytes(), b"personal original")
        self.outputs.write_output("noctalia", "theme", css, b"rendered", force=True)
        css.write_bytes(b"later personal edit")
        self.assertFalse(self.outputs.write_output("noctalia", "theme", css, b"new colors"))
        self.outputs.withdraw_outputs(producer="noctalia")
        self.assertEqual(css.read_bytes(), b"later personal edit")

    def test_real_cleanup_hooks_complete_while_parent_holds_ledger_lock(self):
        from nyxuri.kernel import ledger
        root = Path(__file__).resolve().parents[2]
        cases = [
            ("fish-plugins", "fish", "units/fish/hooks/remove-fisher", ".config/fish/functions/owned.fish"),
            ("noctalia", "theme", "units/noctalia/hooks/remove-gtk-css", ".config/gtk-3.0/gtk.css"),
            ("fcitx5-rime", "fcitx5-rime", "units/fcitx5-rime/hooks/deactivate", ".local/share/fcitx5/rime/default.custom.yaml"),
        ]
        for producer, consumer, script, relative in cases:
            with self.subTest(hook=script):
                target = self.ctx.home / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"original personal content")
                self.assertTrue(self.outputs.write_output(producer, consumer, target, b"managed output", force=True))
                command = [sys.executable, str(root / script)]
                # 真实父进程持flock、真实子进程执行交付hook，不能用同进程可重入锁掩盖死锁。
                with ledger.mutation_lock():
                    result = subprocess.run(command, capture_output=True, text=True, timeout=3,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                self.assertEqual(command[1], str(root / script))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(target.read_bytes(), b"original personal content")
                self.assertNotIn(target, self.outputs.managed_paths())

    def test_hook_cleanup_rejects_transform_without_waiting_for_parent_ledger(self):
        from nyxuri.kernel import ledger
        target = self.ctx.env.config_dir / "starship.toml"
        target.write_bytes(b"source baseline")
        self.enable("theme")
        ledger.set_shell("nyxuri-shell")
        ledger.set_unit("starship", state="enabled", files={"starship.toml": hashlib.sha256(target.read_bytes()).hexdigest()})
        ledger.set_deployment("starship", target=str(target), shape="file")
        self.assertTrue(self.outputs.write_transformation("nyxuri-shell", "starship", target, b"runtime transform"))
        root = Path(__file__).resolve().parents[2]
        code = ("import sys; sys.path.insert(0, sys.argv[1]); "
                "from nyxuri.desktop.owned_outputs import withdraw_outputs; "
                "withdraw_outputs(consumer='starship', ordinary_only=True)")
        with ledger.mutation_lock():
            result = subprocess.run([sys.executable, "-c", code, str(root)], capture_output=True,
                text=True, timeout=3, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("parent unit transaction", result.stderr)
        self.assertEqual(target.read_bytes(), b"runtime transform")
        # 父事务仍负责完整恢复原值及账本基线。
        self.outputs.withdraw_outputs(consumer="starship")
        self.assertEqual(target.read_bytes(), b"source baseline")
        self.assertEqual(ledger.get_unit("starship")["files"]["starship.toml"], hashlib.sha256(target.read_bytes()).hexdigest())

    def test_force_authorization_is_identity_bound_and_consumed_once(self):
        from nyxuri.state.backup import backup_configs
        css = self.ctx.env.config_dir / "gtk-3.0/gtk.css"
        css.parent.mkdir()
        css.write_bytes(b"unknown theme")
        with contextlib.redirect_stdout(io.StringIO()):
            backup = backup_configs(note="force-output-fixture", interactive=False)
        self.outputs.authorize_output_overwrites("theme", backup)
        css.write_bytes(b"changed after approval")
        self.assertFalse(self.outputs.write_output("noctalia", "theme", css, b"rendered"))
        self.assertEqual(css.read_bytes(), b"changed after approval")
        self.outputs.authorize_output_overwrites("theme", backup)
        self.assertTrue(self.outputs.write_output("noctalia", "theme", css, b"rendered"))
        css.write_bytes(b"later change")
        self.assertFalse(self.outputs.write_output("noctalia", "theme", css, b"new render"))
        self.assertEqual(css.read_bytes(), b"later change")

    def test_daemon_commit_protects_unknown_output_until_snapshot_authorization(self):
        from nyxuri.state.backup import backup_configs
        for uid in ("noctalia", "theme"):
            self.enable(uid)
        css = self.ctx.env.config_dir / "gtk-3.0/gtk.css"
        css.parent.mkdir()
        css.write_bytes(b"existing personal CSS")
        stage = self.ctx.env.state_dir / "template-staging/noctalia/nyxuri_gtk3"
        stage.parent.mkdir(parents=True)
        stage.write_bytes(b"rendered colors")
        self.assertFalse(self.outputs.commit_template("nyxuri_gtk3"))
        self.assertEqual(css.read_bytes(), b"existing personal CSS")
        with contextlib.redirect_stdout(io.StringIO()):
            backup = backup_configs(note="daemon-force-fixture", interactive=False)
        captured = json.loads((backup / "external/outputs.json").read_text())
        self.assertIn(str(css), captured["unmanaged_targets"])
        self.outputs.authorize_output_overwrites("theme", backup)
        self.assertTrue(self.outputs.commit_template("nyxuri_gtk3"))
        self.assertEqual(css.read_bytes(), b"rendered colors")
        self.outputs.restore_state(backup / "external", {"version": 1, "file": "outputs.json"})
        self.assertEqual(css.read_bytes(), b"existing personal CSS")

    def test_unknown_equal_output_can_be_registered_without_being_removed(self):
        target = self.ctx.env.config_dir / "gtk-3.0/gtk.css"
        target.parent.mkdir()
        target.write_bytes(b"same output")
        self.assertTrue(self.outputs.write_output("noctalia", "theme", target, b"same output"))
        self.outputs.withdraw_outputs(producer="noctalia")
        self.assertEqual(target.read_bytes(), b"same output")

    def test_personal_noctalia_template_config_is_not_rewritten_by_other_unit(self):
        config = self.ctx.env.config_dir / "noctalia/noctalia-config.toml"
        config.parent.mkdir()
        config.write_text('[theme.templates]\nbuiltin_ids = ["kitty"]\n')
        self.enable("noctalia")
        self.enable("theme")
        # 基线登记后发生个人修改，消费者开关只能改外置门控。
        config.write_text('[theme.templates]\nbuiltin_ids = ["kitty", "custom"]\n')
        original = config.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "configuration conflict"):
            self.outputs.refresh_consumer_outputs({"kitty": True})
        self.assertEqual(config.read_bytes(), original)
        states = json.loads((self.ctx.env.state_dir / "template-consumers.json").read_text())
        self.assertTrue(states["kitty"])

    def test_generic_css_and_unknown_symlink_are_not_ownership(self):
        directory = self.ctx.home / ".config/gtk-3.0"
        directory.mkdir(parents=True)
        (directory / "gtk.css").write_text("@define-color accent_bg_color red;")
        (directory / "gtk-dark.css").symlink_to("gtk.css")
        hook = Path(__file__).resolve().parents[2] / "units/noctalia/hooks/remove-gtk-css"
        self.assertEqual(runpy.run_path(str(hook))["main"](), 0)
        self.assertTrue((directory / "gtk.css").is_file())
        self.assertTrue((directory / "gtk-dark.css").is_symlink())

    def test_consumer_sync_skips_absent_noctalia_but_running_reload_failure_remains_partial(self):
        from nyxuri.kernel import ledger
        config = self.ctx.env.config_dir / "noctalia/noctalia-config.toml"
        config.parent.mkdir()
        source = Path(__file__).resolve().parents[2] / "units/noctalia/noctalia-config.toml"
        config.write_bytes(source.read_bytes())
        for uid in ("theme", "noctalia"):
            self.enable(uid)
        ledger.set_shell("nyxuri-shell")
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
             patch("shutil.which", return_value="/fixture/noctalia"), \
             patch("nyxuri.desktop.shell_switcher.probe_running_shells", return_value=[("nyxuri-shell", os.getpid())]), \
             patch("subprocess.run") as runner:
            self.outputs.refresh_consumer_outputs()
            runner.assert_not_called()
        # 即使偏好是Nyxuri Shell，残留的真实同用户Noctalia拒绝重载仍须返回未完成。
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
             patch("shutil.which", return_value="/fixture/noctalia"), \
             patch("nyxuri.desktop.shell_switcher.probe_running_shells", return_value=[("noctalia", os.getpid())]), \
             patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1)) as runner:
            with self.assertRaisesRegex(RuntimeError, "reload failed"):
                self.outputs.refresh_consumer_outputs()
            runner.assert_called_once_with(["noctalia", "msg", "config-reload"], timeout=15,
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_other_user_noctalia_and_ipc_client_are_not_running_server_proof(self):
        from types import SimpleNamespace
        real_stat = Path.stat
        real_read = Path.read_bytes
        def process_stat(path, *args, **kwargs):
            return SimpleNamespace(st_uid=os.getuid() + 1) if str(path) == "/proc/424242" else real_stat(path, *args, **kwargs)
        with patch("nyxuri.desktop.shell_switcher.probe_running_shells", return_value=[("noctalia", 424242)]), \
             patch.object(Path, "stat", process_stat):
            self.assertFalse(self.outputs._noctalia_instance_running())
        def process_command(path):
            if str(path) == f"/proc/{os.getpid()}/cmdline":
                return b"noctalia\0msg\0theme-mode-get\0"
            return real_read(path)
        with patch("nyxuri.desktop.shell_switcher.probe_running_shells", return_value=[("noctalia", os.getpid())]), \
             patch.object(Path, "read_bytes", process_command):
            self.assertFalse(self.outputs._noctalia_instance_running())

    def test_optional_consumers_and_queued_render_follow_off_gate(self):
        env = self.ctx.env
        source = Path(__file__).resolve().parents[2] / "units/noctalia/noctalia-config.toml"
        config = env.config_dir / "noctalia/noctalia-config.toml"
        config.parent.mkdir()
        shutil.copyfile(source, config)
        for uid in ("noctalia", "theme", "kitty"):
            self.enable(uid)
        with patch("shutil.which", return_value=None):
            self.outputs.refresh_consumer_outputs()
        templates = tomllib.loads(config.read_text())["theme"]["templates"]["user"]
        self.assertIn("nyxuri_kitty", templates)
        self.assertNotIn("nyxuri_mango", templates)
        stage = env.state_dir / "template-staging/noctalia/nyxuri_kitty"
        stage.write_bytes(b"rendered")
        with patch("shutil.which", return_value=None):
            self.outputs.refresh_consumer_outputs({"kitty": False})
        self.assertTrue(self.outputs.commit_template("nyxuri_kitty"))
        self.assertFalse((env.config_dir / "kitty").exists())
        self.assertNotIn("nyxuri_kitty", tomllib.loads(config.read_text())["theme"]["templates"]["user"])

    def prepare_kitty_render(self, producer="noctalia"):
        for uid in ("theme", "noctalia", "kitty"):
            self.enable(uid)
        name = "nyxuri_kitty" if producer == "noctalia" else "kitty"
        stage = self.ctx.env.state_dir / "template-staging" / producer / name
        stage.parent.mkdir(parents=True, exist_ok=True)
        stage.write_bytes(b"background #121317\n")
        return stage, self.ctx.env.config_dir / "kitty/themes/noctalia.conf"

    def test_kitty_reload_follows_actual_theme_commit_for_both_producers(self):
        from nyxuri.kernel import ledger
        for producer in ("noctalia", "nyxuri-shell"):
            with self.subTest(producer=producer):
                stage, target = self.prepare_kitty_render(producer)
                if producer == "nyxuri-shell":
                    ledger.set_shell("nyxuri-shell")
                def observe_signal(pid, sig):
                    self.assertEqual(target.read_bytes(), stage.read_bytes())
                with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
                     patch.object(self.outputs, "_kitty_instances", return_value=[6001, 6002]), \
                     patch.object(self.outputs.os, "kill", side_effect=observe_signal) as notify, \
                     patch("subprocess.run") as runner:
                    result = (self.outputs.commit_template("nyxuri_kitty") if producer == "noctalia"
                              else self.outputs.commit_shell_template("kitty", stage))
                self.assertTrue(result)
                self.assertEqual(notify.call_args_list, [call(6001, signal.SIGUSR1), call(6002, signal.SIGUSR1)])
                runner.assert_not_called()

    def test_kitty_reload_without_instance_is_benign_and_failed_signal_can_retry(self):
        stage, target = self.prepare_kitty_render()
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
             patch.object(self.outputs, "_kitty_instances", return_value=[]), \
             patch.object(self.outputs.os, "kill") as notify:
            self.assertTrue(self.outputs.commit_template("nyxuri_kitty"))
            notify.assert_not_called()
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
             patch.object(self.outputs, "_kitty_instances", return_value=[6001]), \
             patch.object(self.outputs.os, "kill", side_effect=PermissionError("fixture denied")), \
             contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertFalse(self.outputs.commit_template("nyxuri_kitty"))
            self.assertIn("Kitty reload failed", error.getvalue())
        self.assertEqual(target.read_bytes(), stage.read_bytes())
        # 相同字节仍可再次发通知，不能用持久去重把上次失败变成永久失效。
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
             patch.object(self.outputs, "_kitty_instances", return_value=[6001]), \
             patch.object(self.outputs.os, "kill") as notify:
            self.assertTrue(self.outputs.commit_template("nyxuri_kitty"))
            notify.assert_called_once_with(6001, signal.SIGUSR1)

    def test_kitty_disabled_between_commit_and_reload_is_not_notified(self):
        from nyxuri.kernel import ledger
        self.prepare_kitty_render()
        real_write = self.outputs.write_output
        def commit_then_disable(*args, **kwargs):
            result = real_write(*args, **kwargs)
            ledger.set_unit("kitty", state="disabled", vault=str(self.ctx.env.state_dir / "vault/kitty"))
            return result
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-test"}), \
             patch.object(self.outputs, "write_output", side_effect=commit_then_disable), \
             patch.object(self.outputs, "_kitty_instances") as instances, \
             patch.object(self.outputs.os, "kill") as notify:
            self.assertTrue(self.outputs.commit_template("nyxuri_kitty"))
            instances.assert_not_called()
            notify.assert_not_called()

    def test_kitty_process_probe_excludes_other_users_and_command_helpers(self):
        from types import SimpleNamespace
        process_root = self.ctx.home / "fake-proc"
        cases = [("6001", "kitty", b"/usr/bin/kitty\0"),
                 ("6002", "kitty", b"/usr/bin/kitty\0"),
                 ("6003", "kitty", b"/usr/bin/kitty\0+runpy\0driver\0"),
                 ("6004", "other", b"/usr/bin/other\0")]
        entries = []
        for pid, name, command in cases:
            process = process_root / pid
            process.mkdir(parents=True)
            (process / "comm").write_text(name + "\n")
            (process / "cmdline").write_bytes(command)
            entries.append(process)
        real_iterdir, real_stat = Path.iterdir, Path.stat
        def list_processes(path):
            return iter(entries) if path == Path("/proc") else real_iterdir(path)
        def process_stat(path, *args, **kwargs):
            return SimpleNamespace(st_uid=os.getuid() + 1) if path == process_root / "6002" else real_stat(path, *args, **kwargs)
        with patch.object(Path, "iterdir", list_processes), patch.object(Path, "stat", process_stat):
            self.assertEqual(self.outputs._kitty_instances(), [6001])

    def test_shell_gateway_check_preserves_personal_script(self):
        from nyxuri.desktop.shell_switcher import ensure_compositor_gateway_scripts
        directory = self.ctx.env.config_dir / "niri/scripts"
        directory.mkdir(parents=True)
        for name in ("session-shell.sh", "shell-action.sh"):
            script = directory / name
            script.write_bytes(b"#!/bin/sh\n# personal gateway\n")
            script.chmod(0o755)
        ensure_compositor_gateway_scripts()
        self.assertEqual((directory / "shell-action.sh").read_bytes(), b"#!/bin/sh\n# personal gateway\n")

    def test_restore_identical_runtime_content_does_not_write_or_rebaseline_old_claim(self):
        target = self.ctx.home / ".local/share/fcitx5/rime/user.yaml"
        self.outputs.write_output("fcitx5-rime", "fcitx5-rime", target, b"var:\n  seed: true\n")
        seed_metadata = json.loads(self.outputs.metadata_path().read_text())
        target.write_bytes(b"var:\n  seed: true\n  last_build_time: 1234567890\n")
        root = self.ctx.home / "snapshot-with-old-claim"
        manifest = self.outputs.snapshot_state(root)
        desired = target.read_bytes()
        snapshot_metadata = json.loads((root / "outputs.json").read_text())["metadata"]
        with patch.object(self.outputs, "_restore", wraps=self.outputs._restore) as restore:
            self.outputs.restore_state(root, manifest)
        self.assertFalse(any(call.args[0] == target for call in restore.call_args_list))
        self.assertEqual(target.read_bytes(), desired)
        restored = json.loads(self.outputs.metadata_path().read_text())
        self.assertEqual(restored, snapshot_metadata)
        self.assertEqual(restored["outputs"][str(target)]["last"], seed_metadata["outputs"][str(target)]["last"])
        # 真正晚于快照的运行时或个人变化仍要冲突；不能通过幂等分支认领新内容。
        target.write_bytes(b"var:\n  changed_after_snapshot: true\n")
        with self.assertRaisesRegex(RuntimeError, "External output conflict"):
            self.outputs.restore_state(root, manifest)
        self.assertIn(b"changed_after_snapshot", target.read_bytes())

    def test_new_snapshots_do_not_capture_unclaimed_rime_user_runtime_state(self):
        runtime = self.ctx.home / ".local/share/fcitx5/rime/user.yaml"
        runtime.parent.mkdir(parents=True)
        runtime.write_bytes(b"var:\n  last_build_time: 1234567890\n")
        root = self.ctx.home / "snapshot-runtime-unowned"
        self.outputs.snapshot_state(root)
        captured = json.loads((root / "outputs.json").read_text())
        self.assertNotIn(str(runtime), captured["targets"])
        self.assertNotIn(str(runtime), captured["unmanaged_targets"])
        self.assertIn(str(runtime.with_name("default.custom.yaml")), captured["unmanaged_targets"])

    def test_snapshot_restores_output_and_original_metadata(self):
        target = self.ctx.home / ".config/gtk-3.0/gtk.css"
        self.outputs.write_output("noctalia", "theme", target, b"old")
        root = self.ctx.home / "snapshot"
        manifest = self.outputs.snapshot_state(root)
        self.outputs.write_output("noctalia", "theme", target, b"new")
        extra = self.ctx.home / ".config/mango/noctalia.conf"
        self.outputs.write_output("noctalia", "mango", extra, b"new output")
        self.outputs.restore_state(root, manifest)
        self.assertEqual(target.read_bytes(), b"old")
        self.assertFalse(extra.exists())
        self.outputs.withdraw_outputs()
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

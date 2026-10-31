"""Behavior contracts for CLI: exit code propagation, --force path, update hooks.

Safety: all tests run inside TempEnv. CLI main() calls acquire_lock, init_logger,
ensure_nyxuri_symlink — these are patched to avoid touching real system state.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from nyxuri.core import PENDING_UPGRADE_ENV, PENDING_UPGRADE_MENU_ENV
from tests.utils import TempEnv


class TestRetiredModuleCommands(unittest.TestCase):
    """KM3 execution: module verbs are physically gone; invoking them still
    points at their plugin-verb replacements instead of dying silently."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _run(self, *argv):
        import contextlib
        import io
        from nyxuri.cli import main
        out, err = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["nyxuri", *argv]):
            with patch("nyxuri.cli.acquire_lock"), \
                 patch("nyxuri.cli.init_logger"), \
                 patch("nyxuri.cli.ensure_nyxuri_symlink"), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    main()
        return caught.exception.code, out.getvalue(), err.getvalue()

    def test_km3_5_legacy_commands_are_physically_gone(self):
        """KM3.5 enforcement: the alias table and every retired name are gone —
        old commands are plain unknown commands, not ghost pointers."""
        import io
        from nyxuri.cli import COMMANDS

        with open("nyxuri/cli.py", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("RETIREMENTS", source, "the alias table must stay dead")
        retired = ("deploy", "backup", "restore", "remove", "purge", "recommended",
                   "wp", "report", "apps", "wallpapers", "greeter", "fcitx",
                   "gtk", "fisher", "preset", "-h", "--help")
        for name in retired:
            self.assertNotIn(name, COMMANDS, name)
            code, _, err = self._run(name, "extra")
            self.assertEqual(code, 2, name)
            self.assertNotIn("KM5", err, name)


class TestUpdateForcePath(unittest.TestCase):
    """update --force deploys wallpapers and replays enabled-plugin hooks."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_force_deploys_wallpapers_and_replays_hooks(self):
        from nyxuri.installer.workflows import offer_overwrite_upgrade

        with patch("nyxuri.installer.workflows.deploy_selected_configs", return_value=[]), \
             patch("nyxuri.installer.workflows._enable_wallpapers", return_value=True) as mock_wp, \
             patch("nyxuri.installer.workflows.transaction.replay_enabled_hooks") as replay, \
             patch("nyxuri.installer.workflows.render_completion_screen"):
            self.assertTrue(offer_overwrite_upgrade("--force"))

        mock_wp.assert_called_once_with()
        replay.assert_called_once()


class TestUserHookEntrypoints(unittest.TestCase):
    """Hooks run once only after a successful config deployment."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_force_update_runs_hooks_before_completion(self):
        from nyxuri.installer.workflows import offer_overwrite_upgrade

        events = []
        with patch("nyxuri.installer.workflows.deploy_selected_configs", side_effect=lambda **_: events.append("configs") or []), \
             patch("nyxuri.installer.workflows._enable_wallpapers", side_effect=lambda: events.append("wallpapers") or True), \
             patch("nyxuri.installer.workflows.transaction.replay_enabled_hooks",
                   side_effect=lambda: events.append("plugin-hooks")), \
             patch("nyxuri.installer.workflows.run_user_hooks", side_effect=lambda: events.append("hooks") or []), \
             patch("nyxuri.installer.workflows.render_completion_screen", side_effect=lambda *_, **__: events.append("completion")):
            self.assertTrue(offer_overwrite_upgrade("--force"))

        self.assertEqual(events, ["configs", "wallpapers", "plugin-hooks", "hooks", "completion"])

    def test_failed_and_code_only_updates_skip_hooks(self):
        from nyxuri.installer.workflows import offer_overwrite_upgrade

        with patch("nyxuri.installer.workflows.deploy_selected_configs", return_value=["niri"]), \
             patch("nyxuri.installer.workflows.render_completion_screen"), \
             patch("nyxuri.installer.workflows.run_user_hooks") as hooks:
            self.assertFalse(offer_overwrite_upgrade("--force"))
        hooks.assert_not_called()

        with patch("nyxuri.installer.workflows.run_user_hooks") as hooks:
            self.assertTrue(offer_overwrite_upgrade("--no-deploy"))
        hooks.assert_not_called()


class TestUpdateReexecHandoff(unittest.TestCase):
    """update must re-exec with the pending-upgrade marker so the deploy runs
    on the freshly pulled code, not on modules loaded before the pull."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _main_update(self, *flags, pull=True, checkout=True, exec_side_effect=None):
        from nyxuri.cli import main

        with patch("sys.argv", ["nyxuri", "update", *flags]):
            with patch("nyxuri.cli.acquire_lock"), \
                 patch("nyxuri.cli.init_logger"), \
                 patch("nyxuri.cli.ensure_nyxuri_symlink"), \
                 patch("nyxuri.cli.check_path_occlusion"), \
                 patch("nyxuri.cli.safe_git_pull", return_value=True if pull else False), \
                 patch("nyxuri.cli.safe_git_checkout_ref", return_value=True if checkout else False), \
                 patch("nyxuri.core.os.execve", side_effect=exec_side_effect) as mock_exec, \
                 patch("builtins.print"):
                with self.assertRaises(SystemExit) as ctx:
                    main()
        return mock_exec, ctx

    def test_update_reexecs_into_fresh_process(self):
        mock_exec, ctx = self._main_update()
        mock_exec.assert_called_once()
        target, argv, env = mock_exec.call_args[0]
        # §9 argument-shape contract: the restart goes back through the
        # permanent launcher entry — repo/standalone runs are only importable
        # there, since launcher.sh is what seeds sys.path (#138).
        launcher = Path(__file__).resolve().parent.parent / "nyxuri" / "launcher.sh"
        self.assertEqual(target, str(launcher))
        self.assertEqual(argv, [str(launcher)])
        self.assertEqual(env[PENDING_UPGRADE_ENV], "")
        self.assertNotIn(PENDING_UPGRADE_MENU_ENV, env)  # CLI source: exit after deploy
        self.assertEqual(ctx.exception.code, 0)

    def test_update_reexec_falls_back_to_module_without_launcher(self):
        with patch("nyxuri.core.launcher_path", return_value=None):
            mock_exec, ctx = self._main_update()
        target, argv, _ = mock_exec.call_args[0]
        self.assertEqual(target, sys.executable)
        self.assertEqual(argv, [sys.executable, "-m", "nyxuri"])
        self.assertEqual(ctx.exception.code, 0)

    def test_update_force_carries_flag(self):
        mock_exec, _ = self._main_update("--force")
        self.assertEqual(mock_exec.call_args[0][2][PENDING_UPGRADE_ENV], "--force")

    def test_update_no_deploy_also_hands_off(self):
        mock_exec, ctx = self._main_update("--no-deploy")
        mock_exec.assert_called_once()
        self.assertEqual(mock_exec.call_args[0][2][PENDING_UPGRADE_ENV], "--no-deploy")
        self.assertEqual(ctx.exception.code, 0)

    def test_update_to_ref_hands_off_too(self):
        mock_exec, _ = self._main_update("--to", "v3.0.3")
        mock_exec.assert_called_once()

    def test_reexec_failure_returns_1(self):
        mock_exec, ctx = self._main_update(exec_side_effect=OSError("boom"))
        mock_exec.assert_called_once()
        self.assertEqual(ctx.exception.code, 1)

    def test_pull_failure_returns_1_without_reexec(self):
        mock_exec, ctx = self._main_update(pull=False)
        mock_exec.assert_not_called()
        self.assertEqual(ctx.exception.code, 1)

    def test_update_keeps_foreign_cli_link(self):
        from nyxuri.cli import main

        target = self._ctx.env.home / ".local/bin" / "nyxuri"
        target.symlink_to(self._ctx.env.home / "another-launcher")
        with patch("sys.argv", ["nyxuri", "update"]), \
             patch("nyxuri.cli.acquire_lock"), \
             patch("nyxuri.cli.init_logger"), \
             patch("nyxuri.cli.safe_git_pull", return_value=None), \
             patch("builtins.print"):
            with self.assertRaises(SystemExit) as ctx:
                main()

        self.assertEqual(ctx.exception.code, 0)
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(strict=False), (self._ctx.env.home / "another-launcher").resolve(strict=False))


class TestCliLinkOwnershipCallChains(unittest.TestCase):
    """Install and update retain an entry Nyxuri does not own."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_install_keeps_foreign_cli_file(self):
        from nyxuri.cli import main

        target = self._ctx.env.home / ".local/bin" / "nyxuri"
        target.write_text("my launcher")
        with patch("sys.argv", ["nyxuri", "install", "config"]), \
             patch("nyxuri.cli.acquire_lock"), \
             patch("nyxuri.cli.init_logger"), \
             patch("nyxuri.cli.install_configs_workflow", return_value=True):
            with self.assertRaises(SystemExit) as ctx:
                main()

        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(target.read_text(), "my launcher")


class TestCheckNewDepsPostUpdate(unittest.TestCase):
    """check_new_deps_post_update should detect and offer to install missing deps."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_no_missing_deps_no_action(self):
        from nyxuri.installer.workflows import check_new_deps_post_update

        with patch("nyxuri.installer.workflows.get_missing_deps", return_value=[]):
            with patch("nyxuri.installer.workflows.install_selected_deps") as mock_install:
                check_new_deps_post_update()

        mock_install.assert_not_called()

    def test_missing_deps_non_interactive_auto_installs(self):
        from nyxuri.installer.workflows import check_new_deps_post_update

        with patch("nyxuri.installer.workflows.get_missing_deps", return_value=["some-pkg"]):
            with patch("sys.stdin.isatty", return_value=False):
                with patch("nyxuri.installer.workflows.install_selected_deps") as mock_install:
                    with patch("builtins.print"):
                        check_new_deps_post_update()

        mock_install.assert_called_once_with(["some-pkg"])


class TestPendingUpgradeBranch(unittest.TestCase):
    """The fresh process handed the pending-upgrade marker must run the deploy
    offer there (on new code), then exit — or return to the menu when the
    update came from the interactive menu."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        os.environ.pop(PENDING_UPGRADE_ENV, None)
        os.environ.pop(PENDING_UPGRADE_MENU_ENV, None)
        self._ctx.__exit__()

    def _main_pending(self, env_extra, tty=False, offer_result=True):
        from nyxuri.cli import main

        fake_stdin = MagicMock()
        fake_stdin.isatty.return_value = tty
        os.environ.update(env_extra)

        with patch("sys.argv", ["nyxuri"]), \
             patch("sys.stdin", fake_stdin), \
             patch("nyxuri.cli.acquire_lock"), \
             patch("nyxuri.cli.init_logger"), \
             patch("nyxuri.cli.ensure_nyxuri_symlink"), \
             patch("nyxuri.cli.offer_overwrite_upgrade", return_value=offer_result) as mock_offer, \
             patch("nyxuri.cli.check_new_deps_post_update") as mock_check, \
             patch("nyxuri.cli.press_any_key"), \
             patch("nyxuri.cli.select_language"), \
             patch("nyxuri.cli.main_menu_loop") as mock_menu, \
             patch("builtins.print"):
            if tty:
                try:
                    main()
                except SystemExit as e:
                    ctx = e
                else:
                    ctx = None
            else:
                with self.assertRaises(SystemExit) as ctx:
                    main()
        return mock_offer, mock_check, mock_menu, ctx

    def test_pending_flag_deploys_and_exits(self):
        mock_offer, mock_check, _, ctx = self._main_pending({PENDING_UPGRADE_ENV: "--force"})
        mock_offer.assert_called_once_with("--force")
        mock_check.assert_called_once()
        self.assertEqual(ctx.exception.code, 0)
        self.assertNotIn(PENDING_UPGRADE_ENV, os.environ)  # marker consumed

    def test_pending_deploy_failure_exits_1(self):
        _, _, _, ctx = self._main_pending({PENDING_UPGRADE_ENV: ""}, offer_result=False)
        self.assertEqual(ctx.exception.code, 1)

    def test_pending_cli_source_exits_even_interactive(self):
        _, _, mock_menu, ctx = self._main_pending({PENDING_UPGRADE_ENV: ""}, tty=True)
        mock_menu.assert_not_called()
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.code, 0)

    def test_pending_menu_source_returns_to_menu(self):
        env = {PENDING_UPGRADE_ENV: "", PENDING_UPGRADE_MENU_ENV: "1"}
        _, _, mock_menu, ctx = self._main_pending(env, tty=True)
        mock_menu.assert_called_once()
        self.assertIsNone(ctx)


class TestDistroGuard(unittest.TestCase):
    """Non-Arch systems must get a clear message instead of a wall of pacman errors."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_install_full_blocked_without_pacman(self):
        from nyxuri.installer.workflows import install_configs_workflow

        with patch("nyxuri.installer.workflows.shutil.which", return_value=None), \
             patch("nyxuri.installer.workflows.run_master_component_menu") as menu, \
             patch("builtins.print") as prn:
            result = install_configs_workflow("full")

        self.assertFalse(result)
        menu.assert_not_called()
        printed = " ".join(str(c.args[0]) for c in prn.call_args_list)
        self.assertIn("pacman", printed)

    def test_install_config_mode_not_blocked(self):
        from nyxuri.installer.workflows import install_configs_workflow

        with patch("nyxuri.installer.workflows.shutil.which", return_value=None), \
             patch("sys.stdin.isatty", return_value=True), \
             patch("nyxuri.installer.workflows.run_master_component_menu", return_value=None), \
             patch("builtins.print"):
            result = install_configs_workflow("config")

        self.assertTrue(result)  # cancelled-by-user path, not the distro guard

    def test_component_menu_probes_declared_packages(self):
        """组件菜单对可选插件做已装判定：走声明包名，不再读退役的 detect 字段。

        回归用例：R0-2 步 5 处决 ``detect`` 后，菜单曾因 ``m.detect`` 直接
        AttributeError 崩溃（`nyxuri` 主菜单 → 应用配置）。
        """
        from nyxuri.installer.menus import run_master_component_menu
        from nyxuri.deploy.manifest import discover_manifest_apps

        probed = []

        with patch("nyxuri.installer.menus.discover_optional_apps",
                   return_value=["zed"]), \
             patch("nyxuri.installer.menus.discover_config_items",
                   return_value=["zed"]), \
             patch("nyxuri.installer.menus.is_dep_installed",
                   side_effect=lambda name: probed.append(name) or True), \
             patch("nyxuri.installer.menus.CheckboxList") as chk, \
             patch("nyxuri.installer.menus.discover_manifest_apps",
                   return_value=[("zed", discover_manifest_apps() and
                                  dict(discover_manifest_apps())["zed"])]):
            chk.return_value.run.return_value = []
            run_master_component_menu(is_update=False, mode="config")

        self.assertIn("zed", probed)


class TestPreflightSudo(unittest.TestCase):
    """Preflight must not request a password when sudo is already passwordless."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    @staticmethod
    def _result(command, returncode=0):
        import subprocess
        return subprocess.CompletedProcess(command, returncode)

    def _preflight(self):
        from nyxuri.installer.workflows import _phase_preflight_check
        _phase_preflight_check("full", [], False, False)

    def test_passwordless_sudo_skips_interactive_authentication(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return self._result(command)

        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxuri.installer.workflows.subprocess.run", side_effect=fake_run), \
             patch("sys.stdout"), \
             patch("builtins.print"):
            self._preflight()

        self.assertEqual(calls, [["sudo", "-n", "/bin/sh", "-c", ":"]])

    def test_password_sudo_falls_back_to_existing_tty_commands(self):
        for isatty, expected in ((True, ["sudo", "-v"]), (False, ["sudo", "-n", "-v"])):
            with self.subTest(isatty=isatty):
                calls = []

                def fake_run(command, **kwargs):
                    calls.append(command)
                    return self._result(command, 1 if len(calls) == 1 else 0)

                with patch("sys.stdin.isatty", return_value=isatty), \
                     patch("nyxuri.installer.workflows.subprocess.run", side_effect=fake_run), \
                     patch("sys.stdout"), \
                     patch("builtins.print"):
                    self._preflight()

                self.assertEqual(calls, [["sudo", "-n", "/bin/sh", "-c", ":"], expected])

    def test_failed_fallback_still_aborts(self):
        for isatty, expected in ((True, ["sudo", "-v"]), (False, ["sudo", "-n", "-v"])):
            with self.subTest(isatty=isatty):
                calls = []

                def fake_run(command, **kwargs):
                    calls.append(command)
                    return self._result(command, 1)

                with patch("sys.stdin.isatty", return_value=isatty), \
                     patch("nyxuri.installer.workflows.subprocess.run", side_effect=fake_run), \
                     patch("sys.stdout"), \
                     patch("builtins.print"), \
                     self.assertRaises(SystemExit) as ctx:
                    self._preflight()

                self.assertEqual(ctx.exception.code, 1)
                self.assertEqual(calls, [["sudo", "-n", "/bin/sh", "-c", ":"], expected])


class TestCoreVerbs(unittest.TestCase):
    """KM3 core verbs: argument shapes, disclosure, Step→prose, retirement countdown.

    The real repo configs serve as the blueprint; the ledger lives in the
    temp HOME. Package/transaction side effects are patched at the cli seam.
    """

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        from nyxuri import core as i18n
        self._old_lang = i18n.get_lang()
        i18n.set_lang("en")

    def tearDown(self):
        from nyxuri import core as i18n
        i18n.set_lang(self._old_lang)
        self._ctx.__exit__()

    def _run(self, *argv):
        import contextlib
        import io
        from nyxuri.cli import main
        out, err = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["nyxuri", *argv]):
            with patch("nyxuri.cli.acquire_lock"), \
                 patch("nyxuri.cli.init_logger"), \
                 patch("nyxuri.cli.ensure_nyxuri_symlink"), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    main()
        return caught.exception.code, out.getvalue(), err.getvalue()

    # -- argument shapes ------------------------------------------------

    def test_on_without_unit_exits_2(self):
        code, _, _ = self._run("on")
        self.assertEqual(code, 2)

    def test_on_rejects_form_flag_without_value(self):
        code, _, _ = self._run("on", "kitty", "--form")
        self.assertEqual(code, 2)

    def test_on_rejects_deprecated_preset_flag_without_value(self):
        code, _, _ = self._run("on", "kitty", "--preset")
        self.assertEqual(code, 2)

    def test_on_rejects_unknown_flag(self):
        code, _, _ = self._run("on", "kitty", "--force")
        self.assertEqual(code, 2)

    def test_on_unknown_unit_exits_2_with_hint(self):
        code, _, err = self._run("on", "no-such-plugin")
        self.assertEqual(code, 2)
        self.assertIn("Unknown plugin", err)

    def test_list_detail_unknown_unit_exits_2(self):
        code, _, err = self._run("list", "no-such-plugin")
        self.assertEqual(code, 2)
        self.assertIn("Unknown plugin", err)

    def test_doctor_rejects_second_argument(self):
        code, _, _ = self._run("doctor", "kitty", "extra")
        self.assertEqual(code, 2)

    # -- verb wiring ----------------------------------------------------

    def test_on_forwards_form_and_injected_installer(self):
        from nyxuri.cli import _package_installer
        from nyxuri.kernel.transaction import Step
        captured = {}

        def fake_unit_on(plugin, *, form=None, install_packages=None):
            captured.update(plugin=plugin, form=form, installer=install_packages)
            return [Step(plugin, True, "enabled")]

        with patch("nyxuri.cli.transaction.plugin_on", side_effect=fake_unit_on), \
             patch("nyxuri.cli.transaction.missing_packages", return_value=[]):
            code, out, _ = self._run("on", "kitty", "--form", "dark")
        self.assertEqual(code, 0)
        self.assertEqual(captured["plugin"], "kitty")
        self.assertEqual(captured["form"], "dark")
        self.assertIs(captured["installer"], _package_installer)
        self.assertIn("enabled", out)

    def test_on_rejects_deprecated_preset_flag_at_r0_3(self):
        """R0-3 sweep: --preset flag is retired, rejected with exit 2."""
        code, _, _ = self._run("on", "kitty", "--preset", "dark")
        self.assertEqual(code, 2)

    def test_on_reports_missing_packages_failure(self):
        from nyxuri.kernel.transaction import Step
        steps = [Step("kitty", False, "missing-packages: kitty, fish")]
        with patch("nyxuri.cli.transaction.plugin_on", return_value=steps), \
             patch("nyxuri.cli.transaction.missing_packages", return_value=[]):
            code, out, _ = self._run("on", "kitty")
        self.assertEqual(code, 1)
        self.assertIn("missing declared packages: kitty, fish", out)

    def test_off_forwards_cascade_flag(self):
        from nyxuri.kernel.transaction import Step
        with patch("nyxuri.cli.transaction.plan_off", return_value=["kitty"]) as plan, \
             patch("nyxuri.cli.transaction.plugin_off",
                   return_value=[Step("kitty", True, "disabled")]) as off:
            code, out, _ = self._run("off", "kitty", "--cascade")
        plan.assert_called_once_with("kitty")
        off.assert_called_once_with("kitty", cascade=True)
        self.assertEqual(code, 0)
        self.assertIn("disabled", out)

    def test_off_blocked_without_cascade_never_transacts(self):
        with patch("nyxuri.cli.transaction.plan_off", return_value=["kitty", "bar"]) as plan, \
             patch("nyxuri.cli.transaction.plugin_off") as off:
            code, _, err = self._run("off", "kitty")
        plan.assert_called_once_with("kitty")
        off.assert_not_called()
        self.assertEqual(code, 1)
        self.assertIn("blocked by enabled dependents: bar", err)

    # -- list / doctor ----------------------------------------------------

    def test_list_prints_blueprint_inventory(self):
        code, out, _ = self._run("list")
        self.assertEqual(code, 0)
        self.assertIn("kitty", out)
        self.assertIn("niri", out)

    def test_doctor_bare_prints_audit_then_checkup(self):
        with patch("nyxuri.cli.transaction.audit_plugins",
                   return_value={"kitty": "Synced", "fish": "Ghost"}) as audit, \
             patch("nyxuri.cli.run_doctor", return_value=True) as checkup:
            code, out, _ = self._run("doctor")
        audit.assert_called_once_with(None)
        checkup.assert_called_once()
        self.assertEqual(code, 0)
        self.assertIn("Synced", out)
        self.assertIn("Ghost", out)

    def test_doctor_unit_arg_skips_system_checkup(self):
        with patch("nyxuri.cli.transaction.audit_plugins", return_value={}) as audit, \
             patch("nyxuri.cli.run_doctor", return_value=True) as checkup:
            code, _, _ = self._run("doctor", "kitty")
        audit.assert_called_once_with("kitty")
        checkup.assert_not_called()
        self.assertEqual(code, 0)

    # -- retirement enforcement (KM3.5) ------------------------------------

    def test_legacy_alias_prints_countdown_notice(self):
        """The old `backup` alias is gone; `snapshot` is the only door."""
        code, _, err = self._run("backup")
        self.assertEqual(code, 2)
        self.assertTrue("未知命令" in err or "nknown command" in err, err)

    def test_snapshot_list_delegates_to_backup_listing(self):
        with patch("nyxuri.cli.list_backups") as listing:
            code, _, _ = self._run("snapshot", "list")
        listing.assert_called_once()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

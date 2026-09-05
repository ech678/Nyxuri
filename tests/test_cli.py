"""Behavior contracts for CLI: exit code propagation, --force path, update hooks.

Safety: all tests run inside TempEnv. CLI main() calls acquire_lock, init_logger,
ensure_nyxniri_symlink — these are patched to avoid touching real system state.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from nyxniri.constants import PENDING_UPGRADE_ENV, PENDING_UPGRADE_MENU_ENV
from tests.utils import TempEnv


class TestGreeterExitCode(unittest.TestCase):
    """greeter install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_greeter_install_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "greeter", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.greeter.greeter_install", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)

    def test_greeter_install_success_propagates_exit_0(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "greeter", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.greeter.greeter_install", return_value=True):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 0)


class TestFcitxExitCode(unittest.TestCase):
    """fcitx install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_fcitx_uninstall_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "fcitx", "uninstall"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.fcitx.fcitx_uninstall", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)


class TestGtkExitCode(unittest.TestCase):
    """gtk install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_gtk_install_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "gtk", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.gtktheme.gtktheme_install", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)

    def test_gtk_install_success_propagates_exit_0(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "gtk", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.gtktheme.gtktheme_install", return_value=True):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 0)


class TestFisherExitCode(unittest.TestCase):
    """fisher install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_fisher_install_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "fisher", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.fisher.fisher_install", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)

    def test_fisher_install_success_propagates_exit_0(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "fisher", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.fisher.fisher_install", return_value=True):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 0)


class TestUpdateForcePath(unittest.TestCase):
    """update --force must deploy wallpapers + greeter, not just configs + fcitx."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_force_deploys_wallpapers_and_greeter(self):
        from nyxniri.cli import offer_overwrite_upgrade

        with patch("nyxniri.cli.deploy_selected_configs", return_value=[]):
            with patch("nyxniri.cli.deploy_wallpapers") as mock_wp:
                with patch("nyxniri.cli.fcitx_enabled", return_value=True):
                    with patch("nyxniri.cli.fcitx_install"):
                        with patch("nyxniri.cli.greeter_install") as mock_greeter:
                            with patch("nyxniri.cli.render_completion_screen"):
                                offer_overwrite_upgrade("--force")

        mock_wp.assert_called_once_with(do_download=True)
        mock_greeter.assert_called_once()

    def test_force_returns_false_when_greeter_fails(self):
        from nyxniri.cli import offer_overwrite_upgrade

        with patch("nyxniri.cli.deploy_selected_configs", return_value=[]), \
             patch("nyxniri.cli.deploy_wallpapers"), \
             patch("nyxniri.cli.fcitx_enabled", return_value=False), \
             patch("nyxniri.cli.greeter_install", return_value=False), \
             patch("nyxniri.cli.render_completion_screen") as render:
            result = offer_overwrite_upgrade("--force")

        self.assertFalse(result)
        render.assert_not_called()


class TestGreeterWorkflowFailure(unittest.TestCase):
    """Install and interactive update must not report a failed greeter as complete."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    @staticmethod
    def _greeter_only_selection():
        return {
            "configs": [], "wallpapers": False, "fcitx": False,
            "greeter": True, "backup": False,
        }

    def test_install_returns_false_when_greeter_fails(self):
        from nyxniri.cli import install_configs_workflow

        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.cli.run_master_component_menu", return_value=self._greeter_only_selection()), \
             patch("nyxniri.cli._phase_preflight_check"), \
             patch("nyxniri.cli.deploy_wallpapers"), \
             patch("nyxniri.cli.greeter_install", return_value=False), \
             patch("nyxniri.cli.render_completion_screen") as render, \
             patch("builtins.print"):
            result = install_configs_workflow("config")

        self.assertFalse(result)
        render.assert_not_called()

    def test_interactive_update_returns_false_when_greeter_fails(self):
        from nyxniri.cli import offer_overwrite_upgrade

        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.cli.Menu") as menu, \
             patch("nyxniri.cli.run_master_component_menu", return_value=self._greeter_only_selection()), \
             patch("nyxniri.cli.greeter_install", return_value=False), \
             patch("nyxniri.cli.render_completion_screen") as render, \
             patch("builtins.print"):
            menu.return_value.run.return_value = 0
            result = offer_overwrite_upgrade()

        self.assertFalse(result)
        render.assert_not_called()


class TestUpdateReexecHandoff(unittest.TestCase):
    """update must re-exec with the pending-upgrade marker so the deploy runs
    on the freshly pulled code, not on modules loaded before the pull."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _main_update(self, *flags, pull=True, checkout=True, exec_side_effect=None):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "update", *flags]):
            with patch("nyxniri.cli.acquire_lock"), \
                 patch("nyxniri.cli.init_logger"), \
                 patch("nyxniri.cli.ensure_nyxniri_symlink"), \
                 patch("nyxniri.cli.check_path_occlusion"), \
                 patch("nyxniri.cli.safe_git_pull", return_value=True if pull else False), \
                 patch("nyxniri.cli.safe_git_checkout_ref", return_value=True if checkout else False), \
                 patch("nyxniri.cli.os.execve", side_effect=exec_side_effect) as mock_exec, \
                 patch("builtins.print"):
                with self.assertRaises(SystemExit) as ctx:
                    main()
        return mock_exec, ctx

    def test_update_reexecs_into_fresh_process(self):
        mock_exec, ctx = self._main_update()
        mock_exec.assert_called_once()
        argv = mock_exec.call_args[0][1]
        env = mock_exec.call_args[0][2]
        # §9 argument-shape contract: [python, -m, <cli>] + pending marker
        self.assertEqual(argv, [sys.executable, "-m", "nyxniri"])
        self.assertEqual(env[PENDING_UPGRADE_ENV], "")
        self.assertNotIn(PENDING_UPGRADE_MENU_ENV, env)  # CLI source: exit after deploy
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
        from nyxniri.cli import main

        target = self._ctx.env.home / ".local/bin" / "nyxniri"
        target.symlink_to(self._ctx.env.home / "another-launcher")
        with patch("sys.argv", ["nyxniri", "update"]), \
             patch("nyxniri.cli.acquire_lock"), \
             patch("nyxniri.cli.init_logger"), \
             patch("nyxniri.cli.safe_git_pull", return_value=None), \
             patch("builtins.print"):
            with self.assertRaises(SystemExit) as ctx:
                main()

        self.assertEqual(ctx.exception.code, 0)
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(strict=False), (self._ctx.env.home / "another-launcher").resolve(strict=False))


class TestCliLinkOwnershipCallChains(unittest.TestCase):
    """Install and update retain an entry NyxNiri does not own."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_install_keeps_foreign_cli_file(self):
        from nyxniri.cli import main

        target = self._ctx.env.home / ".local/bin" / "nyxniri"
        target.write_text("my launcher")
        with patch("sys.argv", ["nyxniri", "install", "config"]), \
             patch("nyxniri.cli.acquire_lock"), \
             patch("nyxniri.cli.init_logger"), \
             patch("nyxniri.cli.install_configs_workflow", return_value=True):
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
        from nyxniri.cli import check_new_deps_post_update

        with patch("nyxniri.cli.get_missing_deps", return_value=[]):
            with patch("nyxniri.cli.install_selected_deps") as mock_install:
                check_new_deps_post_update()

        mock_install.assert_not_called()

    def test_missing_deps_non_interactive_auto_installs(self):
        from nyxniri.cli import check_new_deps_post_update

        with patch("nyxniri.cli.get_missing_deps", return_value=["some-pkg"]):
            with patch("sys.stdin.isatty", return_value=False):
                with patch("nyxniri.cli.install_selected_deps") as mock_install:
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
        from nyxniri.cli import main

        fake_stdin = MagicMock()
        fake_stdin.isatty.return_value = tty
        os.environ.update(env_extra)

        with patch("sys.argv", ["nyxniri"]), \
             patch("sys.stdin", fake_stdin), \
             patch("nyxniri.cli.acquire_lock"), \
             patch("nyxniri.cli.init_logger"), \
             patch("nyxniri.cli.ensure_nyxniri_symlink"), \
             patch("nyxniri.cli.offer_overwrite_upgrade", return_value=offer_result) as mock_offer, \
             patch("nyxniri.cli.check_new_deps_post_update") as mock_check, \
             patch("nyxniri.cli.press_any_key"), \
             patch("nyxniri.cli.select_language"), \
             patch("nyxniri.cli.main_menu_loop") as mock_menu, \
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
        from nyxniri.cli import install_configs_workflow

        with patch("nyxniri.cli.shutil.which", return_value=None), \
             patch("nyxniri.cli.run_master_component_menu") as menu, \
             patch("builtins.print") as prn:
            result = install_configs_workflow("full")

        self.assertFalse(result)
        menu.assert_not_called()
        printed = " ".join(str(c.args[0]) for c in prn.call_args_list)
        self.assertIn("pacman", printed)

    def test_install_config_mode_not_blocked(self):
        from nyxniri.cli import install_configs_workflow

        with patch("nyxniri.cli.shutil.which", return_value=None), \
             patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.cli.run_master_component_menu", return_value=None), \
             patch("builtins.print"):
            result = install_configs_workflow("config")

        self.assertTrue(result)  # cancelled-by-user path, not the distro guard

    def test_deps_menu_blocked_without_pacman(self):
        from nyxniri.cli import deps_menu_loop

        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.cli.shutil.which", return_value=None), \
             patch("nyxniri.cli.Menu") as menu, \
             patch("builtins.print") as prn:
            deps_menu_loop()

        menu.assert_not_called()
        printed = " ".join(str(c.args[0]) for c in prn.call_args_list)
        self.assertIn("pacman", printed)


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
        from nyxniri.cli import _phase_preflight_check
        _phase_preflight_check("full", [], False, False, False, False)

    def test_passwordless_sudo_skips_interactive_authentication(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return self._result(command)

        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.cli.subprocess.run", side_effect=fake_run), \
             patch("builtins.print"), \
             patch("nyxniri.cli.log_msg"):
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
                     patch("nyxniri.cli.subprocess.run", side_effect=fake_run), \
                     patch("builtins.print"), \
                     patch("nyxniri.cli.log_msg"):
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
                     patch("nyxniri.cli.subprocess.run", side_effect=fake_run), \
                     patch("builtins.print"), \
                     patch("nyxniri.cli.log_msg"), \
                     self.assertRaises(SystemExit) as ctx:
                    self._preflight()

                self.assertEqual(ctx.exception.code, 1)
                self.assertEqual(calls, [["sudo", "-n", "/bin/sh", "-c", ":"], expected])


if __name__ == "__main__":
    unittest.main()

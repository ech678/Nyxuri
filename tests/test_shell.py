"""Contract tests for dual shell management and CLI (nyxuri shell)."""

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from nyxuri.state.ledger import active_shell, custom_shell_bin, set_shell
from nyxuri.cli import _cmd_shell
from tests.utils import TempEnv


class TestShellManagement(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_default_shell_is_noctalia(self):
        self.assertEqual(active_shell(), "noctalia")
        self.assertEqual(custom_shell_bin(), "")

    def test_set_shell_valid(self):
        set_shell("custom", "/usr/bin/my-shell")
        self.assertEqual(active_shell(), "custom")
        self.assertEqual(custom_shell_bin(), "/usr/bin/my-shell")

        set_shell("noctalia")
        self.assertEqual(active_shell(), "noctalia")
        # custom_shell_bin remains recorded
        self.assertEqual(custom_shell_bin(), "/usr/bin/my-shell")

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

    def test_cmd_shell_set(self):
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["set", "custom", "/bin/sh"])
        self.assertEqual(ret, 0)
        self.assertEqual(active_shell(), "custom")
        self.assertEqual(custom_shell_bin(), "/bin/sh")

    def test_cmd_shell_status(self):
        set_shell("custom", "/bin/sh")
        f = io.StringIO()
        with redirect_stdout(f):
            ret = _cmd_shell(["status"])
        self.assertEqual(ret, 0)
        output = f.getvalue()
        self.assertIn("Active Shell: custom", output)
        self.assertIn("Custom Shell Binary: /bin/sh", output)
        self.assertIn("Custom Shell Status: Ready", output)

    def test_preflight_shell(self):
        from nyxuri.shell_switcher import preflight_shell
        ok, _, err = preflight_shell("invalid")
        self.assertFalse(ok)
        self.assertIn("Unknown target shell", err)

        ok, _, err = preflight_shell("custom", "/nonexistent/path/to/shell")
        self.assertFalse(ok)
        self.assertIn("does not exist", err)

        ok, resolved, err = preflight_shell("custom", "/bin/sh")
        self.assertTrue(ok)
        self.assertEqual(resolved, "/bin/sh")
        self.assertEqual(err, "")

    @patch("nyxuri.shell_switcher.wait_shell_ready")
    @patch("nyxuri.shell_switcher.spawn_shell")
    @patch("nyxuri.shell_switcher.stop_shell_process")
    @patch("nyxuri.shell_switcher.probe_running_shell")
    def test_hot_switch_success(self, mock_probe, mock_stop, mock_spawn, mock_wait):
        import os
        from unittest.mock import MagicMock
        from nyxuri.shell_switcher import hot_switch_shell

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        mock_probe.return_value = ("noctalia", 1234)
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_spawn.return_value = mock_proc
        mock_wait.return_value = True

        ok, msg = hot_switch_shell("custom", "/bin/sh")
        self.assertTrue(ok)
        self.assertIn("Successfully switched to custom", msg)
        self.assertEqual(active_shell(), "custom")
        self.assertTrue(mock_stop.called)
        mock_spawn.assert_called_once_with("custom", "/bin/sh")
        mock_wait.assert_called_once()

    @patch("nyxuri.shell_switcher.wait_shell_ready")
    @patch("nyxuri.shell_switcher.spawn_shell")
    @patch("nyxuri.shell_switcher.stop_shell_process")
    @patch("nyxuri.shell_switcher.probe_running_shell")
    def test_hot_switch_failure_and_rollback(self, mock_probe, mock_stop, mock_spawn, mock_wait):
        import os
        from unittest.mock import MagicMock
        from nyxuri.shell_switcher import hot_switch_shell

        os.environ["WAYLAND_DISPLAY"] = "wayland-test"
        mock_probe.return_value = ("noctalia", 1234)
        mock_new_proc = MagicMock()
        mock_new_proc.poll.return_value = None
        mock_restore_proc = MagicMock()
        mock_spawn.side_effect = [mock_new_proc, mock_restore_proc]
        # Target fails readiness, restore succeeds
        mock_wait.side_effect = [False, True]

        ok, msg = hot_switch_shell("custom", "/bin/sh")
        self.assertFalse(ok)
        self.assertIn("failed readiness probe", msg)
        self.assertIn("rolled back to noctalia", msg)
        # Ledger must NOT have been changed to target
        self.assertEqual(active_shell(), "noctalia")
        mock_new_proc.terminate.assert_called()

    def test_p2_layer_structure_and_session_decoupling(self):
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Verify 4-layer directories exist
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "app")))
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "shared")))
        self.assertTrue(os.path.isdir(os.path.join(repo_root, "shell", "modules", "session")))

        # Verify ActionGateway and SessionHost exist
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "app", "ActionGateway.qml")))
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "modules", "session", "SessionHost.qml")))
        self.assertTrue(os.path.isfile(os.path.join(repo_root, "shell", "modules", "session", "SessionPanel.qml")))

        # Verify old PowerMenu directory and service are completely deleted
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Modules", "PowerMenu")))
        self.assertFalse(os.path.exists(os.path.join(repo_root, "shell", "Services", "PowerMenuService.qml")))

    def test_action_gateway_command_arguments(self):
        import subprocess
        from pathlib import Path
        nyxuri_shell_bin = Path(__file__).resolve().parent.parent / "shell" / "bin" / "nyxuri-shell"
        self.assertTrue(nyxuri_shell_bin.exists() and os.access(nyxuri_shell_bin, os.X_OK))

        # Check help output lists session and all standard actions
        res = subprocess.run([str(nyxuri_shell_bin), "--help"], capture_output=True, text=True, check=True)
        self.assertIn("--action", res.stdout)
        self.assertIn("session", res.stdout)
        self.assertIn("launcher", res.stdout)


if __name__ == "__main__":
    unittest.main()

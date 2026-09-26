"""Contract tests for dual shell management and CLI (nyxniri shell)."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from nyxniri.state.ledger import active_shell, custom_shell_bin, set_shell
from nyxniri.cli import _cmd_shell
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


if __name__ == "__main__":
    unittest.main()

"""Contract tests for NYXNIRI_AUTO_YES confirmation semantics.

AUTO_YES is an express-mode convenience: it may auto-consent to routine
prompts, never to destructive ones (purge / snapshot delete / dirty-tree
reset). An env var must not be able to answer "yes, destroy my data".
"""

import inspect
import os
import unittest
from unittest.mock import patch

from tests.utils import TempEnv


class TestAutoYesBoundaries(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        os.environ["NYXNIRI_AUTO_YES"] = "1"

    def tearDown(self):
        os.environ.pop("NYXNIRI_AUTO_YES", None)
        self._ctx.__exit__()

    def test_auto_yes_consents_to_routine_prompt(self):
        from nyxniri.tui import prompt_confirm

        self.assertTrue(prompt_confirm("prompt_install_missing_deps", "y"))

    def test_destructive_prompt_still_asked_under_auto_yes(self):
        from nyxniri.tui import prompt_confirm

        # Force the non-tty fallback (answers with the default "n", i.e. it did
        # NOT blindly consent — the ask still happened). Without this the tty
        # path enters raw mode and blocks the suite waiting for a keypress.
        with patch("nyxniri.tui.sys.stdout"), \
             patch("nyxniri.tui.sys.stdin.isatty", return_value=False):
            self.assertFalse(prompt_confirm("purge_prompt", "n", destructive=True))
            self.assertFalse(prompt_confirm("delete_prompt", "n", destructive=True))
            self.assertFalse(prompt_confirm("dirty_tree_confirm", "n", destructive=True))

    def test_destructive_call_sites_are_marked(self):
        from nyxniri import network
        from nyxniri.state import backup, uninstall

        for module, key in (
            (uninstall, "purge_prompt"),
            (backup, "delete_prompt"),
            (network, "dirty_tree_confirm"),
        ):
            src = inspect.getsource(module)
            self.assertIn(f'prompt_confirm("{key}", "n", destructive=True)', src,
                          f"{module.__name__} must mark {key} as destructive")


if __name__ == "__main__":
    unittest.main()

"""Contract tests for NYXNIRI_REPO clone-source override."""

import subprocess
import sys
import unittest


class TestCloneSourceOverride(unittest.TestCase):
    def _registry_with_env(self, env_value=None):
        env_assignment = (
            f"os.environ['NYXNIRI_REPO']={env_value!r};" if env_value is not None else "os.environ.pop('NYXNIRI_REPO', None);"
        )
        code = (
            "import os;" + env_assignment +
            "from nyxniri import constants;"
            "print(constants.REPO_URL);"
            "print(constants.GIT_MIRROR_REGISTRY)"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, check=True,
        )
        lines = res.stdout.strip().splitlines()
        return lines[0], lines[1]

    def test_override_collapses_to_single_custom_mirror(self):
        custom = "https://git.internal/NyxNiri.git"
        repo_url, registry = self._registry_with_env(custom)
        self.assertEqual(registry, f"[('Custom', '{custom}')]")

    def test_display_repo_url_stays_official_even_when_overridden(self):
        repo_url, _ = self._registry_with_env("https://git.internal/NyxNiri.git")
        self.assertTrue(repo_url.endswith("ech678/NyxNiri.git"))

    def test_default_without_env_unchanged(self):
        repo_url, registry = self._registry_with_env(None)
        self.assertIn("gh-proxy.org", registry)
        self.assertIn("Official", registry)

    def _clone_behavior_with_env(self, env_value):
        """Run clone_repo_with_fallback in a fresh interpreter with the env set."""
        env_assignment = (
            f"os.environ['NYXNIRI_REPO']={env_value!r};" if env_value is not None else "os.environ.pop('NYXNIRI_REPO', None);"
        )
        code = (
            "import os, tempfile\n"
            "from pathlib import Path\n"
            + env_assignment.rstrip(";") + "\n" +
            "from unittest.mock import patch\n"
            "from nyxniri.network import clone_repo_with_fallback\n"
            "with patch('nyxniri.network.git_clone_timeout') as gct:\n"
            "    result = clone_repo_with_fallback(Path(tempfile.mkdtemp()))\n"
            "print(result)\n"
            "print(gct.call_args_list)\n"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, check=True,
        )
        lines = res.stdout.strip().splitlines()
        return lines[0], lines[1]

    def test_invalid_custom_repo_fails_closed_without_git_call(self):
        result, git_calls = self._clone_behavior_with_env("file:///tmp/evil")
        self.assertEqual(result, "False")
        self.assertEqual(git_calls, "[]")

    def test_invalid_custom_repo_never_falls_back_to_official(self):
        """单源直连语义:非法地址不能静默换回官方镜像,必须拒绝。"""
        result, git_calls = self._clone_behavior_with_env("/local/path")
        self.assertEqual(result, "False")
        self.assertEqual(git_calls, "[]")

    def test_valid_custom_repo_clones_single_source(self):
        result, git_calls = self._clone_behavior_with_env("ssh://git.internal/NyxNiri.git")
        self.assertEqual(result, "True")
        self.assertIn("ssh://git.internal/NyxNiri.git", git_calls)


if __name__ == "__main__":
    unittest.main()

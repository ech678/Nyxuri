"""Bootstrap + launcher security tests for install.sh (KM5).

install.sh is a one-time bootstrap: fetch/verify the tree, then hand off to
nyxuri/launcher.sh with NO argument passthrough. The launcher is the permanent
CLI entry and must replicate the pre-KM5 hardening: python3 -I -S -c with the
repo root injected, so PYTHON*/sitecustomize injection from the launch
directory can never reach the engine.
"""

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import time
from unittest.mock import patch



REPO_ROOT = Path(__file__).resolve().parents[2]


def _launcher_python_snippet() -> str:
    """The exact -c snippet the launcher execs (single source: the file itself)."""
    src = (REPO_ROOT / "nyxuri" / "launcher.sh").read_text(encoding="utf-8")
    match = re.search(r"exec python3 -I -S -c '(.*?)' \"\$repo_dir\" \"\$@\"", src, re.DOTALL)
    assert match, "launcher.sh must exec python3 -I -S -c '<snippet>' \"$repo_dir\" \"$@\""
    return match.group(1)


class TestInstallBootstrap(unittest.TestCase):
    def _fake_tools(self, root: Path, log: Path, exec_real: bool = False) -> Path:
        """Fake python3/git on PATH.

        exec_real=False (bootstrap tests): the -I -S -c launch is logged and
        stubbed — the bare handoff would otherwise trigger the interactive
        install workflow (sudo prompts, full deploy) inside the sandbox.
        exec_real=True (launcher tests): the launch is logged and forwarded to
        the real interpreter, proving PYTHON*/sitecustomize isolation.
        """
        bindir = root / "bin"
        bindir.mkdir()
        log_path = shlex.quote(str(log))
        tail = 'exec /usr/bin/python3 "$@"' if exec_real else "exit 0"
        (bindir / "python3").write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                if [ "$1" = "-I" ] && [ "$2" = "-c" ]; then
                    for arg do printf '%s\\0' "$arg"; done > {log_path}.version
                    exec /usr/bin/python3 "$@"
                fi
                if [ "$1" = "-I" ] && [ "$2" = "-S" ] && [ "$3" = "-c" ]; then
                    {{
                        printf 'cwd=%s\\0' "$PWD"
                        for arg do printf '%s\\0' "$arg"
                        done
                    }} > {log_path}
                    {tail}
                fi
                exit 99
                """
            ),
            encoding="utf-8",
        )
        (bindir / "python3").chmod(0o755)
        (bindir / "git").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (bindir / "git").chmod(0o755)
        return bindir

    def _fake_package(self, root: Path, marker: Path) -> None:
        package = root / "nyxuri"
        package.mkdir()
        (package / "__init__.py").write_text(
            f"from pathlib import Path; Path({str(marker)!r}).write_text('loaded')\n",
            encoding="utf-8",
        )
        (package / "__main__.py").write_text("print('forged')\n", encoding="utf-8")

    def _fake_sitecustomize(self, root: Path, marker: Path) -> None:
        (root / "sitecustomize.py").write_text(
            f"from pathlib import Path; Path({str(marker)!r}).write_text('loaded')\n",
            encoding="utf-8",
        )

    def _fake_user_sitecustomize(self, root: Path, marker: Path) -> None:
        user_site = Path(
            subprocess.check_output(
                ["/usr/bin/python3", "-c", "import site; print(site.getusersitepackages())"],
                env={**os.environ, "PYTHONUSERBASE": str(root / "userbase")},
                text=True,
            ).strip()
        )
        user_site.mkdir(parents=True)
        self._fake_sitecustomize(user_site, marker)

    @staticmethod
    def _read_args(path: Path) -> list[str]:
        return [part.decode() for part in path.read_bytes().split(b"\0") if part]

    def _assert_secure_launch(self, result, log: Path, marker: Path, target: Path, user_args: list[str]) -> None:
        self.assertFalse(marker.exists(), result.stdout + result.stderr)
        launch = self._read_args(log)
        # The bootstrap/launcher never cds into the target; the trusted tree is
        # injected as the first engine argument instead (KM5 launcher contract).
        self.assertEqual(launch[1:4], ["-I", "-S", "-c"])
        self.assertEqual(launch[4], _launcher_python_snippet())
        self.assertEqual(launch[5], str(target.resolve()))
        self.assertEqual(launch[6:], user_args)
        self.assertNotIn("forged", result.stdout)

    def _launch_env(self, env, bindir: Path, root: Path, userbase: Path) -> dict[str, str]:
        return {
            **os.environ,
            "HOME": str(env.home),
            "PATH": f"{bindir}:{os.environ['PATH']}",
            "PYTHONPATH": str(root),
            "PYTHONHOME": str(root / "forged-python-home"),
            "PYTHONUSERBASE": str(userbase),
        }

    def test_local_repository_bootstrap_ignores_launch_directory_package(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            self._fake_package(root, marker)
            self._fake_sitecustomize(root, marker)
            self._fake_user_sitecustomize(root, marker)
            log = root / "python.log"
            bindir = self._fake_tools(root, log)
            result = subprocess.run(
                [str(REPO_ROOT / "install.sh")],
                cwd=root,
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            # KM5: the bootstrap takes no arguments — the engine is exec'd bare.
            self._assert_secure_launch(result, log, marker, REPO_ROOT, [])

    def test_bootstrap_rejects_arguments(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            log = root / "python.log"
            bindir = self._fake_tools(root, log)
            result = subprocess.run(
                [str(REPO_ROOT / "install.sh"), "snapshot"],
                cwd=root,
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(log.exists(), "the engine must never be exec'd with args")
            self.assertFalse(marker.exists())
            self.assertTrue("nyxuri" in result.stderr, result.stderr)

    def test_local_repository_launcher_runs_real_python_help(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            self._fake_package(root, marker)
            self._fake_sitecustomize(root, marker)
            self._fake_user_sitecustomize(root, marker)
            bindir = self._fake_tools(root, root / "python-unused.log", exec_real=True)
            result = subprocess.run(
                [str(REPO_ROOT / "nyxuri" / "launcher.sh"), "help"],
                cwd=root,
                env={
                    **os.environ,
                    "HOME": str(env.home),
                    "PYTHONPATH": str(root),
                    "PYTHONHOME": str(root / "forged-python-home"),
                    "PYTHONUSERBASE": str(root / "userbase"),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Nyxuri", result.stdout)
            self.assertIn("(nyxuri)", result.stdout)
            self.assertFalse(marker.exists(), result.stdout)

    def test_launcher_passes_arguments_securely(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            self._fake_package(root, marker)
            self._fake_sitecustomize(root, marker)
            self._fake_user_sitecustomize(root, marker)
            log = root / "python.log"
            bindir = self._fake_tools(root, log, exec_real=True)
            user_args = ["definitely-not-a-verb", "arg with spaces", "quote'and\"chars"]
            result = subprocess.run(
                [str(REPO_ROOT / "nyxuri" / "launcher.sh"), *user_args],
                cwd=root,
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self._assert_secure_launch(result, log, marker, REPO_ROOT, user_args)

    def _prepare_cache(self, env, root: Path) -> Path:
        cache = env.home / ".cache" / "nyxuri"
        shutil.copytree(
            REPO_ROOT,
            cache,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".qmlls.ini"),
            ignore_dangling_symlinks=True,
        )
        (cache / ".git").mkdir()
        return cache

    def test_cache_repository_bootstrap_ignores_launch_directory_package(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            self._fake_package(root, marker)
            self._fake_sitecustomize(root, marker)
            cache = self._prepare_cache(env, root)
            self._fake_user_sitecustomize(root, marker)
            log = root / "python.log"
            bindir = self._fake_tools(root, log)
            trusted = root / "trusted"
            trusted.mkdir()
            script = trusted / "install.sh"
            shutil.copy2(REPO_ROOT / "install.sh", script)
            script.chmod(0o755)
            result = subprocess.run(
                [str(script)],
                cwd=root,
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self._assert_secure_launch(result, log, marker, cache, [])

    def test_piped_bootstrap_ignores_launch_directory_package(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            self._fake_package(root, marker)
            self._fake_sitecustomize(root, marker)
            cache = self._prepare_cache(env, root)
            self._fake_user_sitecustomize(root, marker)
            log = root / "python.log"
            bindir = self._fake_tools(root, log)
            # setsid detaches any controlling terminal so the bootstrap's
            # /dev/tty reconnect probe deterministically falls through to the
            # plain (non-interactive) exec path.
            bash_cmd = "bash"
            if shutil.which("setsid"):
                bash_cmd = "setsid bash"
            result = subprocess.run(
                f"{bash_cmd} -s",
                cwd=root,
                input=(REPO_ROOT / "install.sh").read_text(encoding="utf-8"),
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
                shell=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self._assert_secure_launch(result, log, marker, cache, [])


if __name__ == "__main__":
    unittest.main()


class TestInstallBootstrapCacheCopy(unittest.TestCase):
    """A leftover QML tooling link must not abort the cache copy.

    Running the shell from the source tree makes Quickshell drop a .qmlls.ini
    VFS symlink next to shell.qml; once that VFS is gone the link dangles and
    copytree aborted with Errno 2 before the ignore list knew about the file.
    """

    def test_dangling_qmlls_link_does_not_abort_the_cache_copy(self):
        from tests.deploy import test_install_bootstrap

        with TempEnv() as env, tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            (repo / "shell").mkdir(parents=True)
            (repo / "shell" / "shell.qml").write_text("", encoding="utf-8")
            (repo / "shell" / ".qmlls.ini").symlink_to("/tmp/gone-quickshell-vfs/.qmlls.ini")
            with patch.object(test_install_bootstrap, "REPO_ROOT", repo):
                cache = test_install_bootstrap.TestInstallBootstrap()._prepare_cache(env, Path(raw))
            self.assertTrue((cache / "shell" / "shell.qml").is_file())
            self.assertFalse((cache / "shell" / ".qmlls.ini").exists())

    def test_other_dangling_links_are_skipped_rather_than_fatal(self):
        from tests.deploy import test_install_bootstrap

        with TempEnv() as env, tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            (repo / "plugins").mkdir(parents=True)
            (repo / "plugins" / "effects.kdl").symlink_to("/tmp/gone-niri-config/effects.kdl")
            with patch.object(test_install_bootstrap, "REPO_ROOT", repo):
                cache = test_install_bootstrap.TestInstallBootstrap()._prepare_cache(env, Path(raw))
            self.assertFalse((cache / "plugins" / "effects.kdl").exists())

"""Bootstrap import-boundary tests for install.sh."""

import os
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.utils import TempEnv


REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON_LAUNCHER = (
    'import sys; target = sys.argv.pop(1); sys.path.insert(0, target); '
    'sys.argv[0] = "nyxniri"; from nyxniri.cli import main; main()'
)
PYTHON_VERSION_CODE = 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'


class TestInstallBootstrap(unittest.TestCase):
    def _fake_tools(self, root: Path, log: Path) -> Path:
        bindir = root / "bin"
        bindir.mkdir()
        log_path = shlex.quote(str(log))
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
                        for arg do printf '%s\\0' "$arg"; done
                    }} > {log_path}
                    exec /usr/bin/python3 "$@"
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
        package = root / "nyxniri"
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

    def _assert_secure_launch(
        self, result, log: Path, marker: Path, target: Path, user_args: list[str]
    ) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists(), result.stdout)
        self.assertEqual(
            self._read_args(log.with_name(f"{log.name}.version")),
            ["-I", "-c", PYTHON_VERSION_CODE],
        )
        launch = self._read_args(log)
        self.assertEqual(launch[0], f"cwd={target.resolve()}")
        self.assertEqual(launch[1:], ["-I", "-S", "-c", PYTHON_LAUNCHER, str(target.resolve()), *user_args])
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

    def test_local_repository_ignores_launch_directory_package(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            self._fake_package(root, marker)
            self._fake_sitecustomize(root, marker)
            self._fake_user_sitecustomize(root, marker)
            log = root / "python.log"
            bindir = self._fake_tools(root, log)
            user_args = ["snapshot", "arg with spaces", "quote'and\"chars"]
            result = subprocess.run(
                [str(REPO_ROOT / "install.sh"), *user_args],
                cwd=root,
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
            )
            self._assert_secure_launch(result, log, marker, REPO_ROOT, user_args)

    def test_local_repository_runs_real_python_help(self):
        with TempEnv() as env, tempfile.TemporaryDirectory(dir=env.home) as raw:
            root = Path(raw)
            marker = root / "forged-marker"
            self._fake_package(root, marker)
            self._fake_sitecustomize(root, marker)
            self._fake_user_sitecustomize(root, marker)
            result = subprocess.run(
                [str(REPO_ROOT / "install.sh"), "help"],
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
            self.assertIn("NyxNiri", result.stdout)
            self.assertIn("(nyxniri)", result.stdout)
            self.assertFalse(marker.exists(), result.stdout)

    def _prepare_cache(self, env, root: Path) -> Path:
        cache = env.home / ".cache" / "NyxNiri"
        shutil.copytree(
            REPO_ROOT,
            cache,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        (cache / ".git").mkdir()
        return cache

    def test_cache_repository_ignores_launch_directory_package(self):
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
            user_args = ["snapshot", "arg with spaces", "quote'and\"chars"]
            result = subprocess.run(
                [str(script), *user_args],
                cwd=root,
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
            )
            self._assert_secure_launch(result, log, marker, cache, user_args)

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
            user_args = ["snapshot", "arg with spaces", "quote'and\"chars"]
            result = subprocess.run(
                ["bash", "-s", "--", *user_args],
                cwd=root,
                input=(REPO_ROOT / "install.sh").read_text(encoding="utf-8"),
                env=self._launch_env(env, bindir, root, root / "userbase"),
                capture_output=True,
                text=True,
                check=False,
            )
            self._assert_secure_launch(result, log, marker, cache, user_args)


if __name__ == "__main__":
    unittest.main()

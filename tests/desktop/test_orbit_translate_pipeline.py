"""End-to-end lifecycle and gateway integration test for third-party tools (S1-4).

Exercises the full pipeline:
1. `sources.add(repo)` with bare id ("orbit-translate")
2. `engine.plugin_on("orbit-translate")`
3. `shell-action.sh translate` dynamically discovers and executes the tool from Nyxuri plugins
4. `niri-scratch-toggle.sh translate` dynamically passes the tool to scratchpad kitty
5. `sysdoctor` inspects scripts and orbit runtime
6. `sources.remove("orbit-translate")` withdraws cleanly
"""

import os
import subprocess
import unittest
from pathlib import Path

from nyxuri.system.env import get_env
from nyxuri.state import store
from nyxuri.deploy import catalog, engine
from nyxuri.deploy import sources
from nyxuri.system import doctor as sysdoctor
from tests.utils import TempEnv


def _git(dir_: Path, *args: str):
    return subprocess.run(
        ["git", "-C", str(dir_), *args],
        capture_output=True, text=True, check=False,
    )


class TestOrbitTranslatePipeline(unittest.TestCase):
    def _create_mock_upstream(self, root: Path) -> Path:
        upstream = root / "upstream-orbit-translate"
        upstream.mkdir(parents=True)
        (upstream / "manifest.toml").write_text(
            'schemaVersion = 1\n'
            'id = "orbit-translate"\n'
            'kinds = ["config"]\n'
            'label = "Orbit Translate"\n'
            'category = "tools"\n'
            'packages = ["python-gobject", "gtk3", "gtk-layer-shell", "wl-clipboard"]\n'
            'chmod = ["orbit-translate.py"]\n',
            encoding="utf-8",
        )
        tool = upstream / "orbit-translate.py"
        tool.write_text(
            '#!/bin/sh\n'
            'printf "DISPATCHED:%s:%s\\n" "$#" "$*" >> "${CALLS:-/dev/null}"\n',
            encoding="utf-8",
        )
        tool.chmod(0o755)

        _git(upstream, "init", "-q")
        _git(upstream, "config", "user.email", "test@local")
        _git(upstream, "config", "user.name", "test")
        _git(upstream, "add", "-A")
        _git(upstream, "commit", "-q", "-m", "init")
        return upstream

    def test_full_pipeline_add_on_dispatch_and_remove(self):
        with TempEnv() as ctx:
            home = ctx.home
            env = ctx.env
            calls_file = home / "calls.log"

            # 1. Create upstream git repository
            upstream = self._create_mock_upstream(home)

            # 2. Add as third-party plugin via bare name
            result = sources.add(f"file://{upstream}")
            self.assertEqual(result["id"], "orbit-translate")
            landed = env.data_dir / "plugins" / "orbit-translate"
            self.assertTrue(landed.is_dir())
            self.assertIn("orbit-translate", catalog.plugin_ids())
            self.assertEqual(catalog.plugin_origin("orbit-translate"), "third-party")

            # Default state is OFF
            self.assertIsNone(store.get_plugin("orbit-translate"))

            # 3. Enable plugin
            steps = engine.plugin_on("orbit-translate", install_packages=None)
            self.assertTrue(steps and all(s.ok for s in steps))
            rec = store.get_plugin("orbit-translate")
            self.assertIsNotNone(rec)
            self.assertEqual(rec["state"], "enabled")

            # 4. Test shell-action.sh translate dispatch
            action_script = Path(__file__).resolve().parents[2] / "plugins" / "niri" / "scripts" / "shell-action.sh"
            self.assertTrue(action_script.is_file())

            env_vars = {
                **os.environ,
                "HOME": str(home),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "CALLS": str(calls_file),
            }

            res = subprocess.run(
                ["bash", str(action_script), "translate"],
                capture_output=True, text=True, env=env_vars,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(calls_file.exists())
            self.assertIn("DISPATCHED:0:", calls_file.read_text(encoding="utf-8"))

            # 5. Test niri-scratch-toggle.sh translate
            toggle_script = Path(__file__).resolve().parents[2] / "plugins" / "niri" / "scripts" / "niri-scratch-toggle.sh"
            bindir = home / "bin"
            bindir.mkdir(exist_ok=True)
            mock_niri = bindir / "niri"
            mock_niri.write_text('#!/bin/sh\nprintf "NIRI:%s\\n" "$*" >> "${NIRI_CALLS}"\n', encoding="utf-8")
            mock_niri.chmod(0o755)

            niri_calls = home / "niri_calls.log"
            env_vars["PATH"] = f"{bindir}:{os.environ.get('PATH', '/usr/bin:/bin')}"
            env_vars["NIRI_CALLS"] = str(niri_calls)
            env_vars["XDG_RUNTIME_DIR"] = str(home)

            res = subprocess.run(
                ["bash", str(toggle_script), "translate"],
                capture_output=True, text=True, env=env_vars,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(niri_calls.exists())
            niri_output = niri_calls.read_text(encoding="utf-8")
            self.assertIn("msg action spawn -- kitty --app-id scratchpad --title Translate", niri_output)
            self.assertIn("--settings", niri_output)

            # 6. Test sysdoctor checks
            # _check_scripts verifies executable permissions on plugin scripts
            sysdoctor._check_scripts(env)
            sysdoctor._check_orbit(env)

            # 7. Test plugin_off blocks execution via store gate
            steps_off = engine.plugin_off("orbit-translate")
            self.assertTrue(steps_off and all(s.ok for s in steps_off))
            rec_off = store.get_plugin("orbit-translate")
            self.assertIsNotNone(rec_off)
            self.assertEqual(rec_off["state"], "disabled")

            # shell-action.sh should now refuse to dispatch translate
            calls_before = calls_file.read_text(encoding="utf-8")
            res_off = subprocess.run(
                ["bash", str(action_script), "translate"],
                capture_output=True, text=True, env=env_vars,
            )
            self.assertEqual(res_off.returncode, 1)
            self.assertIn("Translate tool not found or disabled", res_off.stderr)
            self.assertEqual(calls_file.read_text(encoding="utf-8"), calls_before)

            # niri-scratch-toggle.sh should also refuse to dispatch translate
            res_toggle_off = subprocess.run(
                ["bash", str(toggle_script), "translate"],
                capture_output=True, text=True, env=env_vars,
            )
            self.assertEqual(res_toggle_off.returncode, 1)
            self.assertIn("Translate tool not found or disabled", res_toggle_off.stderr)

            # nyxuri-shell --action translate should also refuse to dispatch
            shell_bin = Path(__file__).resolve().parents[2] / "shell" / "nyxuri-shell"
            res_shell_off = subprocess.run(
                ["bash", str(shell_bin), "--action", "translate"],
                capture_output=True, text=True, env=env_vars,
            )
            self.assertEqual(res_shell_off.returncode, 1)
            self.assertIn("Translate tool not found or disabled", res_shell_off.stderr)

            # 8. Remove plugin cleanly
            rm_res = sources.remove("orbit-translate")
            self.assertFalse(rm_res["off_failed"])
            self.assertFalse(landed.exists())
            self.assertNotIn("orbit-translate", catalog.plugin_ids())
            self.assertIsNone(store.get_plugin("orbit-translate"))
            self.assertIsNone(store.get_source("orbit-translate"))


if __name__ == "__main__":
    unittest.main()

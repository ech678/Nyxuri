#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'nyxuri-shell'

QS_STUB = '''#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$QS_LOG"
printf 'QML_IMPORT_PATH=%s\\n' "${QML_IMPORT_PATH:-}" >> "$QS_LOG"
if [ "${1:-}" = "kill" ]; then
    exit "${QS_KILL_RC:-0}"
fi
if [ "${1:-}" = "-p" ] && [ "${3:-}" = "ipc" ] && [ "${4:-}" = "call" ] && [ "${5:-}" = "shell" ] && [ "${6:-}" = "isReady" ]; then
    printf '%s\\n' "${QS_READY_OUT:-true}"
    exit "${QS_READY_RC:-0}"
fi
if [ "${1:-}" = "-p" ] && [ "${3:-}" = "ipc" ] && [ "${4:-}" = "show" ]; then
    exit "${QS_SHOW_RC:-0}"
fi
exit 0
'''


class ExitCleanupContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='clavis-exit-test-')
        self.addCleanup(self.temp.cleanup)
        self.bin = Path(self.temp.name) / 'bin'
        self.bin.mkdir()
        self.log = Path(self.temp.name) / 'qs.log'
        stub = self.bin / 'qs'
        stub.write_text(QS_STUB)
        stub.chmod(0o755)

    def invoke(self, *args, **env):
        environment = dict(os.environ)
        environment['PATH'] = str(self.bin) + os.pathsep + environment['PATH']
        environment['QS_LOG'] = str(self.log)
        environment.update(env)
        result = subprocess.run([str(LAUNCHER), *args], capture_output=True, text=True, env=environment)
        rows = self.log.read_text().splitlines() if self.log.exists() else []
        calls = [row for row in rows if not row.startswith('QML_IMPORT_PATH=')]
        imports = [row.split('=', 1)[1] for row in rows if row.startswith('QML_IMPORT_PATH=')]
        return result, calls, imports

    def test_stop_scopes_kill_to_this_shell_directory(self):
        result, calls, _ = self.invoke('--stop')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['kill -p ' + str(ROOT)])

    def test_stop_is_isolated_from_other_shells_and_does_not_recurse(self):
        result, calls, _ = self.invoke('--stop', QS_KILL_RC='1')
        self.assertEqual(calls, ['kill -p ' + str(ROOT)])
        self.assertEqual(result.returncode, 1)

    def test_check_ready_reports_ready_from_single_status_probe(self):
        result, calls, _ = self.invoke('--check-ready')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['-p ' + str(ROOT) + ' ipc call shell isReady'])

    def test_check_ready_falls_back_to_ipc_show(self):
        result, calls, _ = self.invoke('--check-ready', QS_READY_RC='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [
            '-p ' + str(ROOT) + ' ipc call shell isReady',
            '-p ' + str(ROOT) + ' ipc show'])

    def test_check_ready_reports_not_ready_after_cleanup(self):
        result, calls, _ = self.invoke('--check-ready', QS_READY_RC='1', QS_SHOW_RC='1')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 2)

    def test_launcher_exports_shared_fallback_without_native_build(self):
        _, _, imports = self.invoke('--stop')
        self.assertTrue(imports)
        self.assertTrue(all(row.startswith(str(ROOT / 'fallback')) for row in imports))
        self.assertFalse((ROOT / 'CMakeLists.txt').exists())
        self.assertFalse((ROOT / 'native').exists())

    def test_unknown_action_exits_without_touching_shell(self):
        result, calls, _ = self.invoke('--action', 'nope')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
"""Behavior contracts for Noctalia Greeter system setup."""

import shutil
import stat
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tests.utils import TempEnv


def _result(returncode=0, stdout=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


class TestGreeterInstall(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _install(self, fake_run):
        from nyxniri.modules.greeter import greeter_install

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        dm_state = self._ctx.env.home / "display-manager"
        with patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/env"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.GREETER_DM_STATE", dm_state), \
             patch("nyxniri.modules.greeter.log_msg") as log, \
             patch("builtins.print"):
            result = greeter_install()
        return result, log

    def test_config_failure_returns_false_without_switching_display_manager(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[0:3] == ["sudo", "install", "-D"] and argv[-1] == str(self._ctx.env.home / "greetd" / "config.toml"):
                return _result(1)
            return _result()

        result, log = self._install(fake_run)

        self.assertFalse(result)
        log.assert_not_called()
        self.assertFalse(any(command[:3] == ["sudo", "systemctl", "disable"] for command in calls))

    def test_failed_setup_removes_transaction_backups_after_restoring_files(self):
        from nyxniri.modules.greeter import greeter_install

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        config.parent.mkdir(parents=True)
        config.write_text("old config", encoding="utf-8")
        polkit.write_text("old rule", encoding="utf-8")
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ["sudo", "cat"]:
                return _result(stdout=Path(argv[-1]).read_text(encoding="utf-8"))
            if argv[:2] == ["sudo", "cp"]:
                Path(argv[-1]).write_text(Path(argv[-2]).read_text(encoding="utf-8"), encoding="utf-8")
            if argv[:3] == ["sudo", "install", "-D"]:
                destination = Path(argv[-1])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(Path(argv[-2]).read_text(encoding="utf-8"), encoding="utf-8")
            if argv[:3] == ["sudo", "install", "-d"]:
                return _result(1)
            if argv[:3] == ["sudo", "rm", "-f"]:
                Path(argv[-1]).unlink(missing_ok=True)
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/env"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("builtins.print"):
            self.assertFalse(greeter_install())

        self.assertEqual(config.read_text(encoding="utf-8"), "old config")
        self.assertEqual(polkit.read_text(encoding="utf-8"), "old rule")
        self.assertEqual(calls[:4], [
            ["sudo", "cat", str(config)],
            ["sudo", "cat", str(polkit)],
            ["sudo", "cp", "-n", "--", str(config), f"{config}.nyxniri.bak"],
            ["sudo", "cp", "-n", "--", str(polkit), f"{polkit}.nyxniri.bak"],
        ])
        self.assertIn(["sudo", "rm", "-f", f"{config}.nyxniri.bak"], calls)
        self.assertIn(["sudo", "rm", "-f", f"{polkit}.nyxniri.bak"], calls)
        self.assertFalse(Path(f"{config}.nyxniri.bak").exists())
        self.assertFalse(Path(f"{polkit}.nyxniri.bak").exists())

    def test_failed_setup_keeps_existing_backups(self):
        from nyxniri.modules.greeter import greeter_install

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        config.parent.mkdir(parents=True)
        config.write_text("old config", encoding="utf-8")
        polkit.write_text("old rule", encoding="utf-8")
        config_backup = Path(f"{config}.nyxniri.bak")
        polkit_backup = Path(f"{polkit}.nyxniri.bak")
        config_backup.write_text("keep config", encoding="utf-8")
        polkit_backup.write_text("keep rule", encoding="utf-8")
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ["sudo", "cat"]:
                return _result(stdout=Path(argv[-1]).read_text(encoding="utf-8"))
            if argv[:3] == ["sudo", "install", "-D"]:
                destination = Path(argv[-1])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(Path(argv[-2]).read_text(encoding="utf-8"), encoding="utf-8")
            if argv[:3] == ["sudo", "install", "-d"]:
                return _result(1)
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/env"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("builtins.print"):
            self.assertFalse(greeter_install())

        self.assertEqual(config_backup.read_text(encoding="utf-8"), "keep config")
        self.assertEqual(polkit_backup.read_text(encoding="utf-8"), "keep rule")
        self.assertNotIn(["sudo", "rm", "-f", str(config_backup)], calls)
        self.assertNotIn(["sudo", "rm", "-f", str(polkit_backup)], calls)

    def test_second_backup_failure_only_removes_transaction_config_backup(self):
        from nyxniri.modules.greeter import greeter_install

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        config.parent.mkdir(parents=True)
        config.write_bytes(b"old config\n")
        polkit.write_bytes(b"old rule\n")
        config.chmod(0o640)
        polkit.chmod(0o600)
        config_mode = config.stat().st_mode
        polkit_mode = polkit.stat().st_mode
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ["sudo", "cat"]:
                return _result(stdout=Path(argv[-1]).read_text(encoding="utf-8"))
            if argv == ["sudo", "cp", "-n", "--", str(config), f"{config}.nyxniri.bak"]:
                Path(argv[-1]).write_bytes(config.read_bytes())
                return _result()
            if argv == ["sudo", "cp", "-n", "--", str(polkit), f"{polkit}.nyxniri.bak"]:
                return _result(1)
            if argv == ["sudo", "rm", "-f", f"{config}.nyxniri.bak"]:
                Path(argv[-1]).unlink(missing_ok=True)
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/env"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("builtins.print"):
            self.assertFalse(greeter_install())

        self.assertEqual(calls, [
            ["sudo", "cat", str(config)],
            ["sudo", "cat", str(polkit)],
            ["sudo", "cp", "-n", "--", str(config), f"{config}.nyxniri.bak"],
            ["sudo", "cp", "-n", "--", str(polkit), f"{polkit}.nyxniri.bak"],
            ["sudo", "rm", "-f", f"{config}.nyxniri.bak"],
        ])
        self.assertEqual(config.read_bytes(), b"old config\n")
        self.assertEqual(polkit.read_bytes(), b"old rule\n")
        self.assertEqual(config.stat().st_mode, config_mode)
        self.assertEqual(polkit.stat().st_mode, polkit_mode)
        self.assertFalse(state_dir.exists())

    def test_untrusted_session_path_is_rejected_before_privileged_command(self):
        from nyxniri.modules.greeter import greeter_install

        calls = []
        packages = MagicMock(return_value=True)
        with patch(
            "nyxniri.modules.greeter.shutil.which",
            side_effect=lambda name: "/tmp/noctalia;id\n" if name == "noctalia-greeter-session" else "/usr/bin/systemctl",
        ), patch("nyxniri.modules.greeter.subprocess.run", side_effect=lambda argv, **kwargs: calls.append(argv)), \
             patch("nyxniri.modules.greeter.greeter_install_packages", packages), \
             patch("builtins.print"):
            result = greeter_install()

        self.assertFalse(result)
        packages.assert_not_called()
        self.assertEqual(calls, [])

    def test_trusted_executable_requires_root_owned_nonwritable_ancestors(self):
        from nyxniri.modules.greeter import _trusted_executable

        class FakePath:
            def __init__(self, name, uid=0, mode=stat.S_IFDIR | 0o755):
                self.name = name
                self.uid = uid
                self.mode = mode
                self.parent = self

            def resolve(self, strict=False):
                return self

            def stat(self):
                return SimpleNamespace(st_uid=self.uid, st_mode=self.mode)

            def __str__(self):
                return self.name

        def validate(
            directory_uid=0,
            directory_mode=stat.S_IFDIR | 0o755,
            executable_uid=0,
            executable_mode=stat.S_IFREG | 0o755,
        ):
            root = FakePath("/")
            trusted_dir = FakePath("/usr/bin", uid=directory_uid, mode=directory_mode)
            trusted_dir.parent = root
            executable = FakePath(
                "/usr/bin/noctalia-greeter-session", uid=executable_uid, mode=executable_mode
            )
            executable.parent = trusted_dir
            with patch("nyxniri.modules.greeter.Path", return_value=executable), \
                 patch("nyxniri.modules.greeter.TRUSTED_EXEC_DIRS", (trusted_dir,)):
                return _trusted_executable("/usr/bin/noctalia-greeter-session")

        self.assertEqual(validate(), "/usr/bin/noctalia-greeter-session")
        self.assertIsNone(validate(executable_uid=1000))
        self.assertIsNone(validate(executable_mode=stat.S_IFREG | 0o644))
        self.assertIsNone(validate(directory_uid=1000))
        self.assertIsNone(validate(directory_mode=stat.S_IFDIR | 0o775))

    def test_enable_verification_failure_restores_previous_display_manager(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv == ["systemctl", "is-enabled", "greetd"]:
                return _result(1)
            return _result()

        result, log = self._install(fake_run)

        self.assertFalse(result)
        log.assert_not_called()
        self.assertIn(["sudo", "systemctl", "disable", "sddm"], calls)
        self.assertIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertIn(["sudo", "systemctl", "enable", "--force", "sddm"], calls)
        record_writes = [
            command for command in calls
            if command[:3] == ["sudo", "install", "-D"] and command[-1] == str(self._ctx.env.home / "display-manager")
        ]
        self.assertEqual(len(record_writes), 1)
        self.assertEqual(record_writes[0][:9], ["sudo", "install", "-D", "-o", "root", "-g", "root", "-m", "600"])
        self.assertEqual(len(record_writes[0]), 11)
        self.assertNotIn(["sudo", "systemctl", "disable", "--now", "sddm"], calls)

    def test_privileged_writes_use_install_without_shell(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ["systemctl", "is-enabled"]:
                return _result(0 if argv[-1] == "greetd" else 1)
            return _result()

        result, _ = self._install(fake_run)

        self.assertTrue(result)
        self.assertFalse(any("sh" in command for command in calls))
        root_writes = [command for command in calls if command[:3] == ["sudo", "install", "-D"]]
        self.assertEqual(len(root_writes), 2)
        for command in root_writes:
            self.assertEqual(command[:9], ["sudo", "install", "-D", "-o", "root", "-g", "root", "-m", "644"])
            self.assertEqual(len(command), 11)
        self.assertEqual(
            {command[-1] for command in root_writes},
            {str(self._ctx.env.home / "greetd" / "config.toml"), str(self._ctx.env.home / "polkit.rules")},
        )
        self.assertIn(["sudo", "install", "-d", "-o", "greeter", "-g", "greeter", "-m", "755", str(self._ctx.env.home / "state-dir")], calls)
        self.assertIn(["systemctl", "cat", "greetd"], calls)

    def test_failed_switch_restores_even_when_disabling_previous_manager_fails(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv == ["systemctl", "is-enabled", "greetd"]:
                return _result(1)
            if argv == ["sudo", "systemctl", "disable", "sddm"]:
                return _result(1)
            return _result()

        result, _ = self._install(fake_run)

        self.assertFalse(result)
        self.assertIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertIn(["sudo", "systemctl", "enable", "--force", "sddm"], calls)

    def test_failed_switch_does_not_claim_restore_when_greetd_stays_enabled(self):
        from nyxniri.modules.greeter import _switch_to_greetd

        calls = []
        greetd_checks = {"count": 0}

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv == ["systemctl", "is-enabled", "greetd"]:
                greetd_checks["count"] += 1
                return _result(1 if greetd_checks["count"] == 1 else 0)
            return _result(1 if argv == ["sudo", "systemctl", "enable", "greetd"] else 0)

        with patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter._clear_display_manager_record") as clear_record, \
             patch("builtins.print"):
            result = _switch_to_greetd("sddm")

        self.assertFalse(result)
        self.assertIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertIn(["systemctl", "is-enabled", "greetd"], calls)
        clear_record.assert_not_called()

    def test_backup_failure_returns_false_before_configuration_changes(self):
        from nyxniri.modules.greeter import greeter_install

        config = self._ctx.env.home / "config.toml"
        config.write_text("old", encoding="utf-8")
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ["sudo", "cp"]:
                return _result(1)
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/env"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("nyxniri.modules.greeter.log_msg"), \
             patch("builtins.print"):
            result = greeter_install()

        self.assertFalse(result)
        self.assertEqual(calls, [
            ["sudo", "cat", str(config)],
            ["sudo", "cp", "-n", "--", str(config), f"{config}.nyxniri.bak"],
        ])

    def test_state_directory_and_polkit_failures_propagate(self):
        for failing_destination in ("state", "polkit"):
            with self.subTest(failing_destination=failing_destination):
                calls = []

                def fake_run(argv, **kwargs):
                    calls.append(argv)
                    if failing_destination == "state" and argv[:3] == ["sudo", "install", "-d"]:
                        return _result(1)
                    if failing_destination == "polkit" and argv[:3] == ["sudo", "install", "-D"] and argv[-1].endswith(".rules"):
                        return _result(1)
                    return _result()

                result, log = self._install(fake_run)

                self.assertFalse(result)
                log.assert_not_called()
                self.assertNotIn(["systemctl", "cat", "greetd"], calls)
                self.assertIn(["sudo", "rm", "-f", str(self._ctx.env.home / "greetd" / "config.toml")], calls)
                if failing_destination == "polkit":
                    self.assertIn(["sudo", "rm", "-f", str(self._ctx.env.home / "polkit.rules")], calls)

    def test_setup_failure_restores_existing_configuration_and_polkit_rule(self):
        from nyxniri.modules.greeter import greeter_install

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        config.parent.mkdir(parents=True)
        config.write_text("old config", encoding="utf-8")
        polkit.write_text("old rule", encoding="utf-8")

        def fake_run(argv, **kwargs):
            if argv[:2] == ["sudo", "cat"]:
                return _result(stdout=Path(argv[-1]).read_text(encoding="utf-8"))
            if argv[:3] == ["sudo", "install", "-D"]:
                destination = Path(argv[-1])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(Path(argv[-2]).read_text(encoding="utf-8"), encoding="utf-8")
            if argv[:3] == ["sudo", "install", "-d"]:
                return _result(1)
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/env"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("builtins.print"):
            result = greeter_install()

        self.assertFalse(result)
        self.assertEqual(config.read_text(encoding="utf-8"), "old config")
        self.assertEqual(polkit.read_text(encoding="utf-8"), "old rule")

    def test_enable_command_failure_returns_false_even_if_status_is_enabled(self):
        calls = []
        greetd_checks = {"count": 0}

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv == ["sudo", "systemctl", "enable", "greetd"]:
                return _result(1)
            if argv == ["systemctl", "is-enabled", "greetd"]:
                greetd_checks["count"] += 1
                return _result(0 if greetd_checks["count"] == 2 else 1)
            return _result()

        result, log = self._install(fake_run)

        self.assertFalse(result)
        log.assert_not_called()
        self.assertIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertGreaterEqual(calls.count(["systemctl", "is-enabled", "greetd"]), 3)

    def test_failed_reinstall_restores_recorded_manager_without_deleting_record(self):
        from nyxniri.modules.greeter import greeter_install

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        record = self._ctx.env.home / "display-manager"
        record.write_text("sddm\n", encoding="utf-8")
        calls = []
        greetd_checks = {"count": 0}
        sddm_enabled = {"value": False}

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv == ["sudo", "cat", str(record)]:
                return _result(stdout="sddm\n")
            if argv == ["systemctl", "is-enabled", "greetd"]:
                greetd_checks["count"] += 1
                return _result(1)
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0 if sddm_enabled["value"] else 1)
            if argv[:2] == ["systemctl", "is-enabled"]:
                return _result(1)
            if argv == ["sudo", "systemctl", "enable", "--force", "sddm"]:
                sddm_enabled["value"] = True
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.GREETER_DM_STATE", record), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/systemctl"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("builtins.print"):
            result = greeter_install()

        self.assertFalse(result)
        self.assertIn(["sudo", "systemctl", "enable", "--force", "sddm"], calls)
        self.assertNotIn(["sudo", "rm", "-f", str(record)], calls)
        self.assertEqual(record.read_text(encoding="utf-8"), "sddm\n")


class TestGreeterUninstall(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.state_file = self._ctx.env.home / "display-manager"

    def tearDown(self):
        self._ctx.__exit__()

    def _uninstall(self, state="sddm\n", fail=None, greetd_enabled=False):
        from nyxniri.modules.greeter import greeter_uninstall

        if state is not None:
            self.state_file.write_text(state, encoding="utf-8")
        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        calls = []
        active = {"greetd": greetd_enabled}

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv == ["sudo", "cat", str(self.state_file)]:
                return _result(stdout=state or "")
            if fail and argv == fail:
                return _result(1)
            if argv == ["sudo", "systemctl", "enable", "--force", "greetd"]:
                active["greetd"] = True
            if argv == ["sudo", "systemctl", "disable", "greetd"]:
                active["greetd"] = False
            if argv == ["systemctl", "is-enabled", "greetd"]:
                return _result(0 if active["greetd"] else 1)
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_DM_STATE", self.state_file), \
             patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/systemctl"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.log_msg") as log, \
             patch("builtins.print"):
            result = greeter_uninstall()
        return result, calls, log

    def test_successful_uninstall_disables_greetd_and_restores_recorded_manager(self):
        result, calls, log = self._uninstall()

        self.assertTrue(result)
        self.assertEqual(calls[:6], [
            ["sudo", "cat", str(self.state_file)],
            ["systemctl", "is-enabled", "greetd"],
            ["sudo", "systemctl", "disable", "greetd"],
            ["systemctl", "is-enabled", "greetd"],
            ["sudo", "systemctl", "enable", "--force", "sddm"],
            ["systemctl", "is-enabled", "sddm"],
        ])
        log.assert_called_once_with("INFO", "Uninstalled Noctalia Greeter configuration")

    def test_successful_install_then_uninstall_restores_original_manager(self):
        from nyxniri.modules.greeter import greeter_install, greeter_uninstall

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        active = {"greetd": False}
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[:3] == ["sudo", "install", "-D"]:
                destination = Path(argv[-1])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(Path(argv[-2]).read_text(encoding="utf-8"), encoding="utf-8")
            if argv[:3] == ["sudo", "install", "-d"]:
                Path(argv[-1]).mkdir(parents=True, exist_ok=True)
            if argv[:3] == ["sudo", "rm", "-f"]:
                Path(argv[-1]).unlink(missing_ok=True)
            if argv[:3] == ["sudo", "rm", "-rf"]:
                shutil.rmtree(argv[-1], ignore_errors=True)
            if argv == ["sudo", "systemctl", "enable", "greetd"]:
                active["greetd"] = True
            if argv == ["sudo", "systemctl", "disable", "greetd"]:
                active["greetd"] = False
            if argv == ["systemctl", "is-enabled", "greetd"]:
                return _result(0 if active["greetd"] else 1)
            if argv == ["systemctl", "is-enabled", "sddm"]:
                return _result(0)
            if argv == ["sudo", "cat", str(self.state_file)]:
                return _result(stdout=self.state_file.read_text(encoding="utf-8"))
            return _result()

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.GREETER_DM_STATE", self.state_file), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/systemctl"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run), \
             patch("nyxniri.modules.greeter.greeter_install_packages", return_value=True), \
             patch("nyxniri.modules.greeter._greeter_session_path", return_value="/usr/bin/noctalia-greeter-session"), \
             patch("nyxniri.modules.greeter._greeter_session_arg", return_value=""), \
             patch("builtins.print"):
            self.assertTrue(greeter_install())
            self.assertTrue(greeter_uninstall())

        self.assertIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertIn(["sudo", "systemctl", "enable", "--force", "sddm"], calls)
        self.assertFalse(self.state_file.exists())
        self.assertTrue(config.exists())
        self.assertNotIn(["sudo", "rm", "-f", str(config)], calls)
        self.assertFalse(polkit.exists())
        self.assertFalse(state_dir.exists())

    def test_tampered_record_is_rejected_before_greetd_is_disabled(self):
        result, calls, log = self._uninstall("sddm\nrm -rf /\n")

        self.assertFalse(result)
        self.assertEqual(calls, [
            ["sudo", "cat", str(self.state_file)],
            ["systemctl", "is-enabled", "greetd"],
        ])
        log.assert_not_called()

    def test_restore_failure_returns_false_without_claiming_completion(self):
        result, calls, log = self._uninstall(fail=["sudo", "systemctl", "enable", "--force", "sddm"])

        self.assertFalse(result)
        self.assertIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertIn(["sudo", "systemctl", "enable", "--force", "sddm"], calls)
        self.assertIn(["sudo", "systemctl", "enable", "--force", "greetd"], calls)
        self.assertGreaterEqual(calls.count(["systemctl", "is-enabled", "greetd"]), 2)
        self.assertFalse(any(command[:3] == ["sudo", "rm", "-rf"] for command in calls))
        log.assert_not_called()

    def test_disable_failure_restores_greetd_before_returning_false(self):
        result, calls, log = self._uninstall(fail=["sudo", "systemctl", "disable", "greetd"])

        self.assertFalse(result)
        self.assertIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertIn(["sudo", "systemctl", "enable", "--force", "greetd"], calls)
        self.assertFalse(any(command[:4] == ["sudo", "systemctl", "enable", "--force"] and command[-1] == "sddm" for command in calls))
        log.assert_not_called()

    def test_uninstall_with_no_record_does_not_guess_a_manager(self):
        result, calls, log = self._uninstall(state=None)

        self.assertTrue(result)
        self.assertEqual(calls[0], ["systemctl", "is-enabled", "greetd"])
        self.assertNotIn(["sudo", "systemctl", "disable", "greetd"], calls)
        self.assertFalse(any(command[:4] == ["sudo", "systemctl", "enable", "--force"] for command in calls))
        log.assert_called_once_with("INFO", "Uninstalled Noctalia Greeter configuration")

    def test_enabled_greetd_without_record_keeps_configuration(self):
        result, calls, log = self._uninstall(state=None, greetd_enabled=True)

        self.assertFalse(result)
        self.assertEqual(calls, [["systemctl", "is-enabled", "greetd"]])
        self.assertFalse(any("disable" in command or "rm" in command or "mv" in command for command in calls))
        log.assert_not_called()


if __name__ == "__main__":
    unittest.main()

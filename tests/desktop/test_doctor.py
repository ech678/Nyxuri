"""Tests for doctor preset-drift check (§8/§11)."""

import contextlib
import io
import hashlib
import subprocess
import sys
import unittest
from unittest.mock import patch

from tests.utils import TempEnv


class TestPresetDrift(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def _run_drift(self):
        from nyxuri.sysdoctor import _check_preset_drift
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _check_preset_drift(self._ctx.env)
        return buf.getvalue()

    def test_default_active_no_warn(self):
        # 默认状态应完全安静，也不能把单文件单元误报为无效预设。
        self.assertEqual(self._run_drift(), "")

    def test_active_existing_preset_no_warn(self):
        from nyxuri.deploy.preset import write_active_preset
        # 'transparent' exists in the shipped kitty presets → no drift.
        write_active_preset("kitty", "transparent")
        self.assertNotIn("已不在仓库", self._run_drift())

    def test_synced_flatfile_has_no_preset_warning_or_diagnostic_writes(self):
        """Starship 的真实单文件账本保持 Synced，预设诊断不读取不适用状态。"""
        from nyxuri.kernel import ledger, transaction
        config = self._ctx.env.config_dir / "starship.toml"
        config.write_text("add_newline = false\n", encoding="utf-8")
        ledger.set_unit("starship", state="enabled", preset="default",
                        files={"starship.toml": hashlib.sha256(config.read_bytes()).hexdigest()})
        ledger.set_deployment("starship", target=str(config), shape="file", preserve=[], pending=None)
        before_config = config.read_bytes()
        before_ledger = ledger.ledger_path().read_bytes()
        self.assertEqual(transaction.audit_units("starship"), {"starship": "Synced"})
        self.assertEqual(self._run_drift(), "")
        self.assertEqual(config.read_bytes(), before_config)
        self.assertEqual(ledger.ledger_path().read_bytes(), before_ledger)
        self.assertFalse((self._ctx.env.config_dir / "starship").exists())

    def test_invalid_directory_active_preset_still_warns(self):
        """支持目录预设的 Kitty 若活动记录无效，仍明确报告冻结。"""
        directory = self._ctx.env.presets_dir
        directory.mkdir(parents=True, exist_ok=True)
        marker = directory / "kitty.active"
        marker.write_text("../invalid-preset", encoding="utf-8")
        with patch("nyxuri.core._CURRENT_LANG", "en"):
            output = self._run_drift()
        self.assertIn("kitty: active preset state is invalid", output)
        self.assertIn("~/.config/kitty is frozen", output)
        self.assertNotIn("starship", output)
        self.assertEqual(marker.read_text(), "../invalid-preset")

    def test_active_missing_preset_warns(self):
        from nyxuri.deploy.preset import write_active_preset
        write_active_preset("kitty", "ghost")  # not in repo or user presets
        out = self._run_drift()
        self.assertIn("kitty", out)
        self.assertIn("ghost", out)


class TestUbuntuDesktopDiagnostics(unittest.TestCase):
    """诊断使用真实平台查询逻辑；外部运行时仅在进程边界替换。"""

    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        for target, value in (
            ("nyxuri.core._CURRENT_LANG", "en"),
            ("nyxuri.pkg.platform._os_release", {"ID": "ubuntu"}),
        ):
            option = {"return_value": value} if target.endswith("_os_release") else {"new": value}
            patcher = patch(target, **option)
            patcher.start()
            self.addCleanup(patcher.stop)

    def capture(self, operation):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            operation(self.ctx.env)
        return output.getvalue()

    def test_orbit_checks_cairo_converter_and_reports_ubuntu_packages(self):
        from nyxuri.sysdoctor import _check_orbit
        # 缺转换器时 import cairo 可以成功；诊断必须把 require_foreign 放入同一探针。
        for result in (None, subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)):
            with self.subTest(result=result), \
                 patch("nyxuri.sysdoctor.timed_run", return_value=result) as runner:
                output = self.capture(_check_orbit)
            runner.assert_called_once_with(
                [sys.executable, "-c", "import gi; import cairo; gi.require_foreign('cairo'); gi.require_version('Gtk', '3.0'); gi.require_version('GtkLayerShell', '0.1')"],
                10, capture_output=True, check=False,
            )
            if result is not None and result.returncode == 0:
                self.assertIn("runtime is available", output)
            else:
                for package in ("python3-gi", "python3-cairo", "python3-gi-cairo", "gir1.2-gtklayershell-0.1"):
                    self.assertIn(package, output)
                self.assertNotIn("python-gobject", output)

    def test_orbit_unknown_platform_does_not_recommend_arch_packages(self):
        from nyxuri.sysdoctor import _check_orbit
        with patch("nyxuri.pkg.platform.current_platform", return_value="unsupported"), \
             patch("nyxuri.sysdoctor.timed_run", return_value=None):
            output = self.capture(_check_orbit)
        self.assertIn("bindings are missing", output)
        self.assertNotIn("python-gobject", output)
        self.assertNotIn("python3-gi", output)

    def test_orbit_probe_skipped_when_another_shell_is_active(self):
        from nyxuri.sysdoctor import _check_orbit
        with patch("nyxuri.kernel.ledger.active_shell", return_value="nyxuri-shell"), \
             patch("nyxuri.sysdoctor.timed_run") as runner:
            self.assertEqual(self.capture(_check_orbit), "")
        runner.assert_not_called()

    def test_portal_uses_dpkg_installed_status(self):
        from nyxuri.sysdoctor import _check_portal_gtk
        for state, expected in (("ii ", "backend is installed"), ("rc ", "is missing")):
            commands = []

            def run(argv, **kwargs):
                commands.append((argv, kwargs))
                output = "amd64\n" if argv[0] == "dpkg" else f"{state} xdg-desktop-portal-gtk:amd64\n"
                return subprocess.CompletedProcess(argv, 0, output, "")

            with self.subTest(state=state), patch("shutil.which", side_effect=lambda name: f"/fixture/{name}"), \
                 patch("subprocess.run", side_effect=run):
                output = self.capture(_check_portal_gtk)
            self.assertIn(expected, output)
            self.assertEqual([argv for argv, _ in commands], [
                ["dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n"],
                ["dpkg", "--print-architecture"],
            ])
            for _, kwargs in commands:
                self.assertEqual(kwargs["env"]["LC_ALL"], "C")
                self.assertGreater(kwargs["timeout"], 0)

    def test_portal_unavailable_backend_skips_package_query(self):
        from nyxuri.sysdoctor import _check_portal_gtk
        with patch("shutil.which", return_value=None), patch("subprocess.run") as runner:
            output = self.capture(_check_portal_gtk)
        self.assertIn("database is unavailable", output)
        runner.assert_not_called()

    def test_report_uses_native_versions_without_binary_version_side_effects(self):
        from nyxuri.sysdoctor import generate_bug_report
        calls = []
        available = {"dpkg-query", "dpkg", "apt-get", "mpvpaper", "wpctl"}

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv == ["dpkg", "--print-architecture"]:
                output = "amd64\n"
            else:
                self.assertEqual(argv[:3], ["dpkg-query", "-W", "-f=${db:Status-Abbrev}\\t${binary:Package}\\t${Version}\\n"])
                self.assertEqual(argv[-2], "--")
                output = f"ii \t{argv[-1]}:amd64\t9.1\n"
            return subprocess.CompletedProcess(argv, 0, output, "")

        with patch("shutil.which", side_effect=lambda name: f"/fixture/{name}" if name in available else None), \
             patch("subprocess.run", side_effect=run), contextlib.redirect_stdout(io.StringIO()):
            report = generate_bug_report()
        self.assertTrue(report.is_relative_to(self.ctx.home))
        content = report.read_text()
        for expected in ("mpvpaper: 9.1", "wpctl: 9.1", "xdg-desktop-portal-gtk: 9.1"):
            self.assertIn(expected, content)
        self.assertEqual({argv[-1] for argv, _ in calls if argv[0] == "dpkg-query"}, {
            "mpvpaper", "wireplumber", "xdg-desktop-portal-gtk",
        })
        self.assertTrue(all(argv[0] in {"dpkg-query", "dpkg"} for argv, _ in calls))
        for _, kwargs in calls:
            self.assertEqual(kwargs["env"]["LC_ALL"], "C")
            self.assertGreater(kwargs["timeout"], 0)


if __name__ == "__main__":
    unittest.main()

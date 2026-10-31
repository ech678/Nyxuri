"""Ubuntu 的包数据库、手动资源与字体探测契约。"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


class TestUbuntuDependencyProbe(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv()
        self.env.__enter__()
        self.addCleanup(self.env.__exit__, None, None, None)

    def test_dpkg_probe_is_scoped_to_one_probe_instance(self):
        from nyxuri.pkg.detection import DependencyProbe

        outputs = iter(("ii  kitty\n", "ii  kitty\nii  niri\n"))
        calls = []

        def fake_run(argv, timeout, **kwargs):
            calls.append((argv, timeout, kwargs))
            return subprocess.CompletedProcess(argv, 0, next(outputs), "")

        with patch("nyxuri.pkg.detection.current_platform", return_value="ubuntu"), \
             patch("nyxuri.pkg.detection.shutil.which",
                   side_effect=lambda name: "/usr/bin/dpkg-query" if name == "dpkg-query" else None), \
             patch("nyxuri.pkg.detection.normalize_dpkg_package_names", side_effect=lambda value: set(value.split())), \
             patch("nyxuri.pkg.detection.timed_run", side_effect=fake_run):
            first = DependencyProbe()
            self.assertTrue(first.installed("kitty"))
            self.assertFalse(first.installed("niri"))
            second = DependencyProbe()
            self.assertTrue(second.installed("niri"))

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], [
            "dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\\n",
        ])
        self.assertEqual(calls[0][1], 30)
        self.assertEqual(calls[0][2]["env"]["LC_ALL"], "C")

    def test_manual_font_probe_requires_both_material_symbols_families(self):
        from nyxuri.pkg.detection import DependencyProbe

        outputs = {
            "both": "Material Symbols Rounded,Material Symbols Outlined\nMaterial Icons\n",
            "rounded": "Material Symbols Rounded\nMaterial Icons\n",
            "icons_only": "Material Icons\n",
        }

        for key, expected_rounded, expected_outlined in (
            ("both", True, True), ("rounded", True, False), ("icons_only", False, False),
        ):
            with self.subTest(font_set=key), \
                 patch("nyxuri.pkg.detection.shutil.which", return_value="/usr/bin/fc-list"), \
                 patch("nyxuri.pkg.detection.timed_run", return_value=subprocess.CompletedProcess(
                     [], 0, outputs[key], "")) as run:
                probe = DependencyProbe()
                self.assertEqual(
                    probe.manual_installed("material-symbols-rounded-font"), expected_rounded)
                self.assertEqual(
                    probe.manual_installed("material-symbols-outlined-font"), expected_outlined)
            self.assertEqual(run.call_args.args[0], ["fc-list", ":", "family"])
            self.assertEqual(run.call_args.args[1], 15)

    def test_rime_ice_probe_checks_schema_at_supported_user_path(self):
        from nyxuri.pkg.detection import DependencyProbe

        root = self.env.home / ".local/share/fcitx5/rime"
        root.mkdir(parents=True)
        schema = root / "rime_ice.schema.yaml"
        probe = DependencyProbe()
        (root / "luna_pinyin.schema.yaml").write_text("schema: unrelated\n", encoding="utf-8")
        schema.write_text("schema: rime_ice\n", encoding="utf-8")

        real_is_file = Path.is_file

        def is_temp_file(candidate):
            # 系统级 /usr/share/rime-data 也是正式探测路径，测试中必须屏蔽宿主状态。
            return candidate.is_relative_to(self.env.home) and real_is_file(candidate)

        with patch.object(Path, "is_file", is_temp_file):
            schema.unlink()
            self.assertFalse(probe.manual_installed("rime-ice"))
            (root / "luna_pinyin.schema.yaml").write_text("schema: unrelated\n", encoding="utf-8")
            self.assertFalse(probe.manual_installed("rime-ice"))
            schema.write_text("schema: rime_ice\n", encoding="utf-8")
            self.assertTrue(probe.manual_installed("rime-ice"))

    def test_manual_binary_and_font_detection_are_read_only_probes(self):
        from nyxuri.pkg.detection import DependencyProbe

        probe = DependencyProbe()
        with patch("nyxuri.pkg.detection.shutil.which", side_effect=lambda name: {
            "mpvpaper": "/usr/bin/mpvpaper",
        }.get(name)), patch.object(probe, "fonts", "jetbrains mono nerd font"):
            self.assertTrue(probe.manual_installed("mpvpaper"))
            self.assertTrue(probe.manual_installed("jetbrains-mono-nerd-font"))
            self.assertFalse(probe.manual_installed("unknown-resource"))


if __name__ == "__main__":
    unittest.main()

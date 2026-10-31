"""默认截图目录在成功部署后准备，模板渲染本身与个人路径保持无额外写入。"""

import re
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


_DEFAULT = 'screenshot-path "~/Pictures/Screenshots/Screenshot from %Y-%m-%d %H-%M-%S.png"\n'


class TestNiriScreenshotDirectory(unittest.TestCase):
    def stage(self, ctx):
        """使用临时 Niri 单元走真实事务，不执行任何桌面会话命令。"""
        root = ctx.home / "units"
        unit = root / "niri"
        unit.mkdir(parents=True)
        (unit / "manifest.toml").write_text('packages = []\n', encoding="utf-8")
        (unit / "config.kdl").write_text(_DEFAULT, encoding="utf-8")
        ctx.env.units_src = root
        return ctx.env.config_dir / "niri/config.kdl"

    def test_default_and_localized_screenshots_can_be_created_after_install(self):
        from nyxuri.kernel import transaction
        for dirname in ("Pictures", "图片 空间"):
            with self.subTest(dirname=dirname), TempEnv() as ctx:
                config = self.stage(ctx)
                pictures = ctx.home / dirname
                pictures.mkdir(exist_ok=True)
                self.assertFalse((pictures / "Screenshots").exists())
                with patch("nyxuri.deploy.templates.get_pics_dir", return_value=pictures):
                    steps = transaction.unit_on("niri")
                    self.assertTrue(all(step.ok for step in steps), steps)
                    pattern = re.search(r'^screenshot-path "([^"]+)"', config.read_text()).group(1)
                    destination = Path(datetime(2026, 10, 27, 12, 0).strftime(pattern)).expanduser()
                    # 对照 Portal 的 File::create 边界：不自行 mkdir，直接创建输出文件。
                    destination.write_bytes(b"screenshot-content")
                    self.assertEqual(destination.parent, pictures / "Screenshots")
                    self.assertTrue(all(step.ok for step in transaction.unit_refresh("niri")))
                    self.assertEqual(destination.read_bytes(), b"screenshot-content")
                    self.assertTrue(all(step.ok for step in transaction.unit_off("niri")))
                    self.assertEqual(destination.read_bytes(), b"screenshot-content")

    def test_render_only_and_carried_personal_configuration_do_not_prepare_directory(self):
        from nyxuri.deploy.templates import _phase_render_templates, prepare_screenshot_directory
        from nyxuri.kernel import transaction
        with TempEnv() as ctx:
            config = self.stage(ctx)
            config.parent.mkdir()
            config.write_text(_DEFAULT)
            pictures = ctx.home / "图片"
            pictures.mkdir()
            with patch("nyxuri.deploy.templates.get_pics_dir", return_value=pictures):
                _phase_render_templates(only_app="niri")
                self.assertFalse((pictures / "Screenshots").exists())
                config.write_text('screenshot-path "/personal/path/%s.png"\n')
                prepare_screenshot_directory(only_app="niri")
                self.assertFalse((pictures / "Screenshots").exists())
                before = config.read_bytes()
                steps = transaction.unit_on("niri")
                self.assertTrue(all(step.ok for step in steps), steps)
                self.assertEqual(config.read_bytes(), before)
                self.assertFalse((pictures / "Screenshots").exists())

    def test_directory_failure_is_pending_and_retry_uses_saved_configuration_baseline(self):
        from nyxuri.kernel import ledger, transaction
        with TempEnv() as ctx:
            self.stage(ctx)
            pictures = ctx.home / "Pictures"
            destination = pictures / "Screenshots"
            destination.write_text("existing-user-file")
            with patch("nyxuri.deploy.templates.get_pics_dir", return_value=pictures):
                steps = transaction.unit_on("niri")
                self.assertFalse(steps[-1].ok)
                self.assertEqual(ledger.get_deployment("niri")["pending"], "deploy")
                self.assertIn("config.kdl", ledger.get_unit("niri")["files"])
                self.assertEqual(destination.read_text(), "existing-user-file")
                destination.unlink()
                steps = transaction.unit_on("niri")
                self.assertTrue(all(step.ok for step in steps), steps)
                self.assertTrue(destination.is_dir())
                self.assertIsNone(ledger.get_deployment("niri")["pending"])

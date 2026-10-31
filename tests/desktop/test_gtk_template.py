"""使用真实 GTK3 CSS 解析器守护主题模板的语法兼容性。"""

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

from tests.utils import TempEnv


class TestGtk3TemplateSyntax(unittest.TestCase):
    def setUp(self):
        self.ctx = TempEnv()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)

    def test_shipped_template_is_accepted_by_gtk3(self):
        """填入固定色值后解析整份 CSS，捕获 GTK3 不接受的 color-mix 等表达式。"""
        template = Path(__file__).resolve().parents[2] / "units/theme/gtk-3.0.css"
        # 本测试只验证 CSS 语法，不替代 Noctalia 的取色和模板渲染测试。
        css = re.sub(
            r"\{\{\s*colors\.[a-z_]+\.default\.(hex|rgb_csv)\s*\}\}",
            lambda match: "#112233" if match[1] == "hex" else "17, 34, 51",
            template.read_text(encoding="utf-8"),
        )
        self.assertNotIn("{{", css, "Unrecognized color placeholder in GTK3 template")
        path = self.ctx.home / "gtk.css"
        path.write_text(css, encoding="utf-8")
        driver = (
            "import sys\n"
            "try:\n"
            "    import gi\n"
            "    gi.require_version('Gtk', '3.0')\n"
            "    from gi.repository import Gtk\n"
            "except (ImportError, ValueError) as error:\n"
            "    print(str(error), file=sys.stderr)\n"
            "    sys.exit(77)\n"
            "provider = Gtk.CssProvider()\n"
            "errors = []\n"
            "provider.connect('parsing-error', lambda provider, section, error: errors.append(str(error)))\n"
            "try:\n"
            "    provider.load_from_path(sys.argv[1])\n"
            "except Exception as error:\n"
            "    errors.append(str(error))\n"
            "print('\\n'.join(errors), file=sys.stderr)\n"
            "sys.exit(bool(errors))\n"
        )
        # CSS 解析无需显示服务器；清除会话地址，防止无意连接正在使用的桌面。
        environment = {key: value for key, value in os.environ.items()
                       if key not in {"DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"}}
        result = subprocess.run(
            [sys.executable, "-c", driver, str(path)], env=environment,
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 77:
            self.skipTest("GTK3 Python bindings unavailable: " + result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

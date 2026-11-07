"""Runtime resource integrity contracts (shaders, icons, templates, TOML i18n)."""

import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL_DIR = REPO_ROOT / "shell"


class TestResourceIntegrity(unittest.TestCase):
    """Runtime resource integrity contracts."""

    def test_all_shader_binaries_exist(self):
        """Assert all required GLSL fragment shaders have precompiled .qsb assets."""
        required_qsbs = [
            SHELL_DIR / "plugins" / "bar" / "island" / "shaders" / "qsb" / "long_split.frag.qsb",
            SHELL_DIR / "plugins" / "bar" / "island" / "shaders" / "qsb" / "pill_morph.frag.qsb",
            SHELL_DIR / "plugins" / "launcher" / "shaders" / "qsb" / "spotlight_mode_field.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "wp_disc.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "wp_fade.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "wp_iris_bloom.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "wp_pixelate.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "wp_portal.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "wp_stripes.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "wp_wipe.frag.qsb",
            SHELL_DIR / "plugins" / "wallpaper" / "shaders" / "qsb" / "zen-palette.frag.qsb",
        ]
        for qsb in required_qsbs:
            self.assertTrue(qsb.is_file(), f"Missing required precompiled shader: {qsb}")
            self.assertGreater(qsb.stat().st_size, 0, f"Shader file is empty: {qsb}")

    def test_zen_palette_renderer_has_no_dangling_qrc(self):
        """Assert ZenPaletteRenderer.qml loads the unit-owned precompiled qsb as a real file URL."""
        renderer = SHELL_DIR / "plugins" / "wallpaper" / "ZenPaletteRenderer.qml"
        content = renderer.read_text(encoding="utf-8")
        self.assertNotIn("qrc:/", content)
        self.assertIn('Qt.resolvedUrl("shaders/qsb/zen-palette.frag.qsb")', content)

    def test_dead_pools_stay_eliminated(self):
        """Assert dissolved shell/app and shell/shared pools remain eliminated."""
        self.assertFalse((SHELL_DIR / "app").exists(), "shell/app must stay eliminated")
        self.assertFalse((SHELL_DIR / "shared").exists(), "shell/shared must stay eliminated")

    def test_humidity_icons_complete(self):
        """Assert weather humidity icons in sidebars assets are intact."""
        icons_dir = SHELL_DIR / "plugins" / "sidebars" / "assets" / "icons"
        for pct in [7, 30, 50, 75, 90]:
            self.assertTrue((icons_dir / f"humidity_percent_{pct}.svg").is_file(),
                            f"Missing humidity icon: humidity_percent_{pct}.svg")

    def test_toml_i18n_syntax_and_dead_section_purged(self):
        """Assert zh_CN.toml and en_US.toml parse cleanly with tomllib and have no dead sections."""
        import tomllib
        zh_cn_path = SHELL_DIR / "commons" / "i18n" / "zh_CN.toml"
        en_us_path = SHELL_DIR / "commons" / "i18n" / "en_US.toml"

        with open(zh_cn_path, "rb") as f:
            zh_data = tomllib.load(f)
        self.assertNotIn("VerticalLyricsLayout", zh_data, "Dead lyrics section must not be in zh_CN.toml")
        self.assertIn("WallpaperPage", zh_data)

        with open(en_us_path, "rb") as f:
            en_data = tomllib.load(f)
        self.assertIn("%n second(s)", en_data)

    def test_builtin_templates_exist(self):
        """Assert the Noctalia-syntax builtin template pool is complete."""
        t_dir = SHELL_DIR / "commons" / "assets" / "templates"
        for t_file in ["config.toml", "kitty/kitty.conf", "kitty/kitty-apply.sh",
                       "btop/btop.theme", "btop/btop-apply.sh",
                       "starship/starship.toml", "starship/starship-apply.sh"]:
            self.assertTrue((t_dir / t_file).is_file(), f"Missing builtin template: {t_file}")


if __name__ == "__main__":
    unittest.main()

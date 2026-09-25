"""Behavior contract tests for Orbit Launcher palette loading.

Verifies priority loading of native M3 ~/.cache/nyxniri/palette.toml,
fallback to Noctalia starship palette cache, and final static default fallback.
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv

_PALETTE_PATH = Path(__file__).resolve().parent.parent / "configs" / "niri" / "scripts" / "orbit" / "palette.py"


def _load_palette_module():
    spec = importlib.util.spec_from_file_location("orbit_palette_under_test", _PALETTE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestOrbitPalette(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.orbit_palette = _load_palette_module()

    def tearDown(self):
        self._ctx.__exit__()

    def test_native_m3_palette_priority(self):
        """Native M3 palette must be parsed directly without Catppuccin guessing."""
        m3_content = (
            'primary = "#123456"\n'
            'secondary = "#654321"\n'
            'tertiary = "#abcdef"\n'
            'surface = "#1a1a24"\n'
            'surface_dim = "#0a0a12"\n'
            'on_surface = "#f0f0f5"\n'
            'on_surface_variant = "#888899"\n'
            'outline = "#a0a0b0"\n'
        )
        starship_content = (
            'blue = "#ffffff"\n'
            'base = "#000000"\n'
        )
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f1, \
             tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f2:
            f1.write(m3_content)
            f2.write(starship_content)
            m3_path, starship_path = f1.name, f2.name

        try:
            with patch.object(self.orbit_palette, "NYXNIRI_PALETTE_PATH", m3_path), \
                 patch.object(self.orbit_palette, "STARSHIP_PALETTE_PATH", starship_path):
                palette = self.orbit_palette.load_material_palette()
                self.assertEqual(palette["primary"], self.orbit_palette.hex_to_rgb("#123456"))
                self.assertEqual(palette["secondary"], self.orbit_palette.hex_to_rgb("#654321"))
                self.assertEqual(palette["tertiary"], self.orbit_palette.hex_to_rgb("#abcdef"))
                self.assertEqual(palette["surface"], self.orbit_palette.hex_to_rgb("#1a1a24"))
                self.assertEqual(palette["on_surface_var"], self.orbit_palette.hex_to_rgb("#888899"))
                self.assertTrue(palette["is_dark"])
        finally:
            os.unlink(m3_path)
            os.unlink(starship_path)

    def test_fallback_to_starship_when_m3_absent(self):
        """When native M3 palette does not exist, fall back to starship cache."""
        starship_content = (
            'blue = "#feacef"\n'
            'teal = "#c6c3e9"\n'
            'base = "#131318"\n'
            'text = "#e5e1e9"\n'
        )
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(starship_content)
            starship_path = f.name

        try:
            with patch.object(self.orbit_palette, "NYXNIRI_PALETTE_PATH", "/nonexistent/palette.toml"), \
                 patch.object(self.orbit_palette, "STARSHIP_PALETTE_PATH", starship_path):
                palette = self.orbit_palette.load_material_palette()
                self.assertEqual(palette["primary"], self.orbit_palette.hex_to_rgb("#feacef"))
                self.assertEqual(palette["secondary"], self.orbit_palette.hex_to_rgb("#c6c3e9"))
                self.assertEqual(palette["surface"], self.orbit_palette.hex_to_rgb("#131318"))
                self.assertEqual(palette["on_surface"], self.orbit_palette.hex_to_rgb("#e5e1e9"))
        finally:
            os.unlink(starship_path)

    def test_fallback_to_defaults_when_both_absent(self):
        """When neither palette exists, return static fallback values."""
        with patch.object(self.orbit_palette, "NYXNIRI_PALETTE_PATH", "/nonexistent/palette.toml"), \
             patch.object(self.orbit_palette, "STARSHIP_PALETTE_PATH", "/nonexistent/starship.toml"):
            palette = self.orbit_palette.load_material_palette()
            self.assertEqual(palette["primary"], (0.42, 0.70, 1.00))
            self.assertEqual(palette["surface"], (0.12, 0.13, 0.18))
            self.assertTrue(palette["is_dark"])


if __name__ == "__main__":
    unittest.main()

"""Contract tests for the wallpaper picker's Material 3 theme engine.

theme.py is the single source of truth for the picker's design tokens. These
tests pin the tonal derivations (container-tier monotonicity, on-color
contrast, starship palette mapping) and the CSS compilation contract, so the
"fundamentalist M3" guarantee cannot silently rot.
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_THEME = Path(__file__).resolve().parent.parent / "configs" / "niri" / "scripts" / "wallpaper_picker" / "theme.py"


def _load_theme():
    spec = importlib.util.spec_from_file_location("wp_theme_under_test", _THEME)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_DARK_RAW = {
    "blue": "#feacef", "teal": "#c6c3e9", "pink": "#c4c0ff",
    "base": "#131318", "text": "#e5e1e9", "subtext0": "#928f9c",
    "overlay1": "#928f9c", "overlay0": "#474551",
}
_LIGHT_RAW = {
    "blue": "#6d5a9e", "base": "#fbf8fd", "text": "#1b1b1f",
    "subtext0": "#474551",
}

_TIER_ORDER = (
    "surface_container_lowest", "surface_container_low",
    "surface_container", "surface_container_high", "surface_container_highest",
)


class TestColorHelpers(unittest.TestCase):
    def setUp(self):
        self.theme = _load_theme()

    def test_hex_to_rgb_valid(self):
        self.assertEqual(self.theme.hex_to_rgb("#ff8000"), (1.0, 128 / 255, 0.0))

    def test_hex_to_rgb_invalid_returns_default(self):
        self.assertIsNone(self.theme.hex_to_rgb("nonsense"))
        self.assertEqual(self.theme.hex_to_rgb("bad", default=(0, 0, 0)), (0, 0, 0))

    def test_luminance_extremes(self):
        self.assertAlmostEqual(self.theme._luminance((1, 1, 1)), 1.0)
        self.assertAlmostEqual(self.theme._luminance((0, 0, 0)), 0.0)

    def test_on_color_picks_higher_contrast(self):
        self.assertEqual(self.theme._on_color((1, 1, 1)), (0.0, 0.0, 0.0))
        self.assertEqual(self.theme._on_color((0, 0, 0)), (1.0, 1.0, 1.0))

    def test_mix(self):
        self.assertEqual(
            self.theme._mix((0, 0, 0), (1, 1, 1), 0.25), (0.25, 0.25, 0.25))


class TestTokens(unittest.TestCase):
    def setUp(self):
        self.theme = _load_theme()

    def test_dark_tiers_monotonic(self):
        t = self.theme.build_tokens(raw=_DARK_RAW)
        self.assertTrue(t["is_dark"])
        lums = [self.theme._luminance(t[k]) for k in _TIER_ORDER]
        for i in range(4):
            self.assertLess(lums[i], lums[i + 1])

    def test_light_lowest_brighter_than_surface(self):
        t = self.theme.build_tokens(raw=_LIGHT_RAW)
        self.assertFalse(t["is_dark"])
        self.assertGreater(
            self.theme._luminance(t["surface_container_lowest"]),
            self.theme._luminance(t["surface"]))
        # M3 light ladder: 96 > 94 > 92 > 90 — tiers darken monotonically.
        lums = [self.theme._luminance(t[k]) for k in _TIER_ORDER[1:]]
        for i in range(3):
            self.assertGreater(lums[i], lums[i + 1])

    def test_on_color_contrast(self):
        for raw in (_DARK_RAW, _LIGHT_RAW):
            t = self.theme.build_tokens(raw=raw)
            self.assertGreaterEqual(
                self.theme._contrast(t["primary"], t["on_primary"]), 4.5)
            self.assertGreaterEqual(
                self.theme._contrast(t["primary_container"], t["on_primary_container"]), 3.0)
            self.assertGreaterEqual(
                self.theme._contrast(t["secondary_container"], t["on_secondary_container"]), 3.0)

    def test_raw_source_respected(self):
        t = self.theme.build_tokens(raw=_DARK_RAW)
        self.assertEqual(t["primary"], self.theme.hex_to_rgb("#feacef"))
        self.assertEqual(t["surface"], self.theme.hex_to_rgb("#131318"))

    def test_fallback_when_no_raw(self):
        t = self.theme.build_tokens(raw={})
        self.assertTrue(t["is_dark"])
        self.assertEqual(t["primary"], self.theme._FALLBACK["primary"])

    def test_all_roles_present(self):
        t = self.theme.build_tokens(raw=_DARK_RAW)
        for role in ("primary", "on_primary", "primary_container", "on_primary_container",
                     "secondary", "on_secondary", "secondary_container", "on_secondary_container",
                     "tertiary", "on_tertiary", "surface", "surface_variant",
                     "on_surface", "on_surface_variant",
                     *_TIER_ORDER, "outline", "outline_variant", "is_dark"):
            self.assertIn(role, t)


class TestStarshipLoading(unittest.TestCase):
    def setUp(self):
        self.theme = _load_theme()

    def test_parses_starship_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('# Noctalia Starship Palette\n'
                    '[palettes.noctalia]\n'
                    'blue = "#feacef"\n'
                    'text = "#e5e1e9"\n'
                    'base = "#131318"\n')
            path = f.name
        try:
            colors = self.theme._load_starship_colors(path)
        finally:
            os.unlink(path)
        self.assertEqual(colors["blue"], self.theme.hex_to_rgb("#feacef"))
        self.assertEqual(colors["text"], self.theme.hex_to_rgb("#e5e1e9"))
        self.assertEqual(colors["base"], self.theme.hex_to_rgb("#131318"))

    def test_missing_file_returns_empty(self):
        self.assertEqual(self.theme._load_starship_colors("/nonexistent/x.toml"), {})


class TestCssContract(unittest.TestCase):
    def setUp(self):
        self.theme = _load_theme()
        self.t = self.theme.build_tokens(raw=_DARK_RAW)
        self.css = self.theme.build_css(self.t, {"card_w": 328, "thumb_h": 184})

    def test_component_selectors_present(self):
        for sel in (".picker-dialog", ".appbar-title", ".icon-btn", ".search",
                    ".chip", ".card", ".thumb", ".badge", ".fab", ".grid-scroll",
                    ".empty-title", ".card.current"):
            self.assertIn(sel, self.css)

    def test_geometry_baked_in(self):
        self.assertIn("min-width: 328px", self.css)
        self.assertIn("min-height: 184px", self.css)

    def test_roles_baked_in(self):
        self.assertIn(self.theme._rgb(self.t["surface"]), self.css)
        self.assertIn(self.theme._rgb(self.t["surface_container_high"]), self.css)
        self.assertIn(self.theme._rgb(self.t["secondary_container"]), self.css)
        self.assertIn(self.theme._rgb(self.t["primary_container"]), self.css)

    def test_m3_spec_values(self):
        # Shape scale: dialog extra-large 28, card medium 12, FAB large 16.
        # Component geometry: search bar 56dp, filter chip 32dp, FAB 56dp.
        self.assertIn("border-radius: 28px", self.css)
        self.assertIn("border-radius: 12px", self.css)
        self.assertIn("border-radius: 16px", self.css)
        self.assertIn("min-height: 56px", self.css)
        self.assertIn("min-height: 32px", self.css)

    def test_state_layers_follow_m3_opacities(self):
        hover_chip = self.theme._rgb(self.theme._mix(
            self.t["surface"], self.t["on_surface"], 0.08))
        hover_card = self.theme._rgb(self.theme._mix(
            self.t["surface_container_low"], self.t["on_surface"], 0.08))
        self.assertIn(hover_chip, self.css)
        self.assertIn(hover_card, self.css)


if __name__ == "__main__":
    unittest.main()

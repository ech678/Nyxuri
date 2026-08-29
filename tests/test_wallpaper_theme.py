"""Contract tests for the wallpaper picker's Material 3 Expressive (M3E) theme engine.

theme.py is the single source of truth for the picker's design tokens. These
tests pin the tonal derivations (container-tier monotonicity, on-color
contrast, text-contrast contract, starship palette mapping, error role),
10-step shape scale, 30-style type scale, spatial/effects motion spring
curves, and the CSS compilation contract — including the chip corner-morph
(spatial spring), pressed shape, 48dp hit targets, search-bar tiering,
overscroll suppression and scrim/reveal transitions.
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
    "blue": "#feacef", "teal": "#c6c3e9", "pink": "#c4c0ff", "red": "#ed8796",
    "base": "#131318", "text": "#e5e1e9", "subtext0": "#928f9c",
    "overlay1": "#928f9c", "overlay0": "#474551",
}
_LIGHT_RAW = {
    "blue": "#6d5a9e", "red": "#d20f39", "base": "#fbf8fd", "text": "#1b1b1f",
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


class TestShapeScale(unittest.TestCase):
    def setUp(self):
        self.theme = _load_theme()

    def test_shape_scale_ten_steps(self):
        expected_steps = {
            "none": 0, "xs": 4, "s": 8, "m": 12, "l": 16,
            "l_inc": 20, "xl": 28, "xl_inc": 32, "xxl": 48, "full": 9999
        }
        for step, val in expected_steps.items():
            self.assertIn(step, self.theme.SHAPE)
            self.assertEqual(self.theme.SHAPE[step], val)


class TestTypeScale(unittest.TestCase):
    def setUp(self):
        self.theme = _load_theme()

    def test_thirty_styles_present(self):
        self.assertEqual(len(self.theme.TYPE), 30)

    def test_emphasized_weights(self):
        # Emphasized styles have equal or higher weight than baseline
        for role in ("display-large", "headline-large", "title-large", "body-large", "label-large"):
            base_size, base_weight = self.theme.TYPE[role]
            emph_size, emph_weight = self.theme.TYPE[f"{role}-emph"]
            self.assertEqual(base_size, emph_size)
            self.assertGreaterEqual(emph_weight, base_weight)


class TestMotionSprings(unittest.TestCase):
    def setUp(self):
        self.theme = _load_theme()

    def test_spatial_springs_have_overshoot(self):
        # Spatial fast spring cubic-bezier y1 > 1 (overshoot bounce)
        self.assertIn("1.67", self.theme.EASE_EXPRESSIVE_FAST_SPATIAL)
        self.assertIn("1.21", self.theme.EASE_EXPRESSIVE_DEFAULT_SPATIAL)

    def test_effects_springs_no_overshoot(self):
        # Effects springs damping 1.0, y1 <= 1.0
        self.assertIn("0.94", self.theme.EASE_EXPRESSIVE_FAST_EFFECTS)
        self.assertIn("0.80", self.theme.EASE_EXPRESSIVE_DEFAULT_EFFECTS)


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

    def test_error_role_contrast(self):
        # Large badge: error/on-error must clear the 3:1 minimum
        for raw in (_DARK_RAW, _LIGHT_RAW, {}):
            t = self.theme.build_tokens(raw=raw)
            self.assertGreaterEqual(
                self.theme._contrast(t["error"], t["on_error"]), 3.0)

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
                     "tertiary", "on_tertiary", "tertiary_container", "on_tertiary_container",
                     "surface", "on_surface", "on_surface_variant",
                     *_TIER_ORDER, "outline", "outline_variant",
                     "error", "on_error", "is_dark"):
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
        self.css = self.theme.build_css(self.t, {
            "card_w": 334, "thumb_w": 328, "thumb_h": 184,
            "search_h": 56, "chip_h": 48,
        })

    def _block(self, selector):
        """Return the declaration block of a top-level CSS selector."""
        return self.css.split(selector + " {")[1].split("}")[0]

    def test_component_selectors_present(self):
        for sel in (".picker-dialog", ".appbar-title", ".count-label", ".icon-btn", ".search",
                    ".chip", ".chip-face", ".icon-btn-face", ".card", ".thumb", ".live",
                    ".scrim", ".grid-scroll", ".empty-title"):
            self.assertIn(sel, self.css)

    def test_no_fab(self):
        # The grid itself is the primary action surface; M3 says no FAB when
        # images represent the actions, so the stylesheet must not carry one.
        self.assertNotIn(".fab", self.css)

    def test_reveal_transitions_present(self):
        # Entry/exit: dialog + scrim fade in via the .revealed class
        self.assertIn(".picker-dialog.revealed", self.css)
        self.assertIn(".scrim.revealed", self.css)
        self.assertIn("rgba(0,0,0,0.32)", self.css)

    def test_geometry_baked_in(self):
        self.assertIn("min-width: 328px", self.css)
        self.assertIn("min-height: 184px", self.css)

    def test_roles_baked_in(self):
        self.assertIn(self.theme._rgb(self.t["surface_container_high"]), self.css)
        self.assertIn(self.theme._rgb(self.t["secondary_container"]), self.css)
        self.assertIn(self.theme._rgb(self.t["primary_container"]), self.css)

    def test_m3_spec_values(self):
        # Shape scale: dialog extra-large 28, card medium 12, chip face
        # small 8 (also the pressed shape), selected chip morphs to full.
        # Component geometry: search bar 56dp, chip face 32dp, live tag
        # 16dp, hit targets 48dp.
        self.assertIn("border-radius: 28px", self.css)
        self.assertIn("border-radius: 12px", self.css)
        self.assertIn("border-radius: 8px", self.css)
        self.assertIn("min-height: 56px", self.css)
        self.assertIn("min-height: 48px", self.css)
        self.assertIn("min-height: 32px", self.css)
        self.assertIn("min-height: 16px", self.css)

    def test_search_uses_container_low(self):
        # On a surface-container-high dialog the search bar must drop to
        # container-low (>1 step, per the anti-blending rule)
        self.assertIn(
            self.theme._rgb(self.t["surface_container_low"]),
            self._block(".search"))

    def test_search_hover_and_focus(self):
        hover = self.theme._rgb(self.theme._mix(
            self.t["surface_container_low"], self.t["on_surface"], 0.08))
        self.assertIn(hover, self._block(".search:hover"))
        self.assertIn(".search:focus", self.css)

    def test_count_label_neutral(self):
        # The count is informational text; error must not reach the
        # stylesheet at all (M3 reserves it for alerts)
        self.assertIn(".count-label", self.css)
        self.assertNotIn(self.theme._rgb(self.t["error"]), self.css)

    def test_live_tag_full_pill(self):
        self.assertIn("border-radius: 9999px", self._block(".live"))

    def test_overscroll_suppressed(self):
        # M3 publishes no over/underscroll treatment; the toolkit's Adwaita
        # edge glow is foreign chrome and must not reach the grid viewport.
        self.assertIn(
            "background: none",
            self._block(".grid-scroll undershoot, .grid-scroll overshoot"))

    def test_chip_pressed_morph(self):
        # M3E pressed shape (CornerSmall): the face snaps back to 8dp on press
        self.assertIn("border-radius: 8px", self._block(".chip:active > .chip-face"))

    def test_chip_selected_shape_full(self):
        # M3E Chips v37.2.1: SelectedShape = CornerFull — selection morphs
        # to the pill, not a mid-scale corner.
        self.assertIn("border-radius: 9999px", self._block(".chip:checked > .chip-face"))

    def test_chip_hit_target_single_source(self):
        # The 48dp hit-target height flows from the geometry dict into the
        # CSS (window.py CHIP_ROW_H), not a magic number here.
        self.assertIn("min-height: 48px", self._block(".chip"))

    def test_hit_targets_48dp(self):
        # Visual faces (32/40dp) live inside 48dp hit-target buttons
        self.assertIn("min-height: 48px", self._block(".chip"))
        self.assertIn("min-height: 48px", self._block(".icon-btn"))

    def test_chip_morph_uses_spatial_spring(self):
        # Unselected→selected corner morph rides the fast spatial spring
        # (350ms, overshoot bezier) while colors ride fast effects.
        self.assertIn(
            f"border-radius {self.theme.DUR_FAST_SPATIAL_MS}ms "
            f"{self.theme.EASE_EXPRESSIVE_FAST_SPATIAL}", self.css)
        self.assertEqual(self.theme.DUR_STATE_MS, 150)

    def test_state_layers_follow_m3_opacities(self):
        hover_chip = self.theme._rgb(self.theme._mix(
            self.t["surface_container_high"], self.t["on_surface"], 0.08))
        hover_card = self.theme._rgb(self.theme._mix(
            self.t["surface_container_low"], self.t["on_surface"], 0.08))
        self.assertIn(hover_chip, self.css)
        self.assertIn(hover_card, self.css)

    def test_no_corner_badge(self):
        # Enabled/selected state rides the card outline itself; the old
        # corner disc is gone and must never come back silently.
        self.assertNotIn(".badge", self.css)

    def test_cards_reserve_border_footprint(self):
        # The selection border's footprint is resident on every card, so
        # toggling selection only recolors it and never shifts content.
        card = self._block(".card")
        self.assertIn("border: 3px solid transparent", card)
        self.assertIn("border-color", card)  # animated like the other states

    def test_current_and_selected_share_border(self):
        # M3 photo picker: selection is a 3dp primary outline, shared by
        # .card.current, .card:selected, and .card:focus.
        self.assertIn(".card.current, .card:selected, .card:focus {", self.css)
        block = self._block(".card.current, .card:selected, .card:focus")
        self.assertIn(f"border-color: {self.theme._rgb(self.t['primary'])}", block)
        self.assertNotIn("outline", block)

    def test_card_focus_is_state_layer_not_ring(self):
        # Keyboard navigation rides the selection border; focus must not
        # paint a second (outer, clip-prone) ring on cards.
        card_focus = self._block("\n.card:focus")
        expected = self.theme._rgb(self.theme._mix(
            self.t["surface_container_low"], self.t["on_surface"],
            self.theme.STATE_FOCUSED))
        self.assertIn(expected, card_focus)
        self.assertNotIn("outline-style", card_focus)

    def test_nested_radii_optical_roundness(self):
        # M3 Expressive nested radii rule: inner = outer - padding/border.
        # Outer card is 12px with 3px border, so inner thumb top radius is 9px.
        thumb = self._block(".thumb")
        self.assertIn("border-radius: 9px 9px 0 0", thumb)

    def test_flowboxchild_padding_zero(self):
        # Reset GtkFlowBoxChild Adwaita default padding to avoid horizontal overflow
        flowboxchild = self._block("flowboxchild")
        self.assertIn("padding: 0", flowboxchild)
        self.assertIn("margin: 0", flowboxchild)
        self.assertIn("outline: none", flowboxchild)


class TestTextContrastContract(unittest.TestCase):
    """M3 guarantees text-role contrast by construction (tone distance).
    The linear-mix adaptation must uphold the same promise: on_surface_variant
    is the workhorse text color (chip labels, search icon, empty-state hints).
    """

    def setUp(self):
        self.theme = _load_theme()

    def test_on_surface_variant_readable_on_surface(self):
        for raw in (_DARK_RAW, _LIGHT_RAW, {}):
            t = self.theme.build_tokens(raw=raw)
            contrast = self.theme._contrast(t["on_surface_variant"], t["surface"])
            self.assertGreaterEqual(contrast, 4.5,
                                    f"on_surface_variant vs surface for raw={raw}")


if __name__ == "__main__":
    unittest.main()

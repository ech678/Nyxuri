"""Unit tests for template_registry primitives and placeholder interpolation."""

import unittest
from nyxuri.template_registry import has_section, add_section, render_template


class TestTemplateRegistryPrimitives(unittest.TestCase):
    def test_has_section(self):
        content = """
[package]
name = "nyxuri"

[parts.effects]
target = "effects.kdl"
"""
        self.assertTrue(has_section(content, "package"))
        self.assertTrue(has_section(content, "parts.effects"))
        self.assertFalse(has_section(content, "presets"))

    def test_add_section_new(self):
        base = '[package]\nname = "test"'
        updated = add_section(base, "presets", {"reload": "true"})
        self.assertTrue(has_section(updated, "presets"))
        self.assertIn('reload = "true"', updated)

    def test_add_section_existing_merges_keys(self):
        base = '[package]\nname = "test"\n'
        updated = add_section(base, "package", {"version": "3.0.5"})
        self.assertIn('name = "test"', updated)
        self.assertIn('version = "3.0.5"', updated)

    def test_render_template(self):
        tpl = "Primary: {{ colors.primary.hex }}, Surface: {{ colors.surface.hex }}"
        ctx = {
            "colors": {
                "primary": {"hex": "#1a73e8"},
                "surface": {"hex": "#ffffff"}
            }
        }
        res = render_template(tpl, ctx)
        self.assertEqual(res, "Primary: #1a73e8, Surface: #ffffff")

    def test_render_template_missing_key_preserved(self):
        tpl = "Found: {{ colors.primary.hex }}, Missing: {{ colors.unknown.hex }}"
        ctx = {
            "colors": {
                "primary": {"hex": "#1a73e8"}
            }
        }
        res = render_template(tpl, ctx)
        self.assertEqual(res, "Found: #1a73e8, Missing: {{ colors.unknown.hex }}")


if __name__ == "__main__":
    unittest.main()

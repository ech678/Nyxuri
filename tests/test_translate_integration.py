"""Orbit Translate ↔ Nyxuri integration contracts: palette, templates, entry points."""

from __future__ import annotations

from tests.translate_support import TOOLS, setUpModule, tearDownModule  # noqa: F401

import os
from pathlib import Path
import re
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from orbit_translate.config import config_path, load_config
from orbit_translate.theme import Palette, load_palette


_REPO = TOOLS.parents[2]


class NativePaletteTests(unittest.TestCase):
    def test_native_priority_and_legacy_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            with patch.dict(os.environ, {"XDG_CACHE_HOME": str(cache)}):
                self.assertEqual(load_palette(), Palette())
                paths = (
                    cache / "noctalia/starship-palette.toml",
                    cache / "nyxniri/palette.toml",
                    cache / "nyxuri/palette.toml",
                )
                for index, path in enumerate(paths):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    color = ("#113355", "#335577", "#557799")[index]
                    path.write_text(f'primary = "{color}"\non_surface_variant = "#aabbcc"\n')
                    self.assertEqual(load_palette().primary, color)
                    self.assertEqual(load_palette().muted, "#aabbcc")
                self.assertEqual(load_palette(paths[0]).primary, "#113355")

    def test_invalid_or_missing_explicit_palette_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "palette.toml"
            self.assertEqual(load_palette(path), Palette())
            path.write_text('primary = "not-a-color"\non_surface_variant = "#010203"\n')
            self.assertEqual(load_palette(path).primary, Palette.primary)
            self.assertEqual(load_palette(path).muted, "#010203")
            path.write_text("invalid = [")
            self.assertEqual(load_palette(path), Palette())

    def test_default_palette_skips_invalid_native_file_but_explicit_path_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            native = cache / "nyxuri/palette.toml"
            legacy = cache / "nyxniri/palette.toml"
            native.parent.mkdir(parents=True)
            legacy.parent.mkdir(parents=True)
            native.write_text("invalid = [")
            legacy.write_text('primary = "#335577"\n')
            with patch.dict(os.environ, {"XDG_CACHE_HOME": str(cache)}):
                self.assertEqual(load_palette().primary, "#335577")
                self.assertEqual(load_palette(native), Palette())


class NyxuriTemplateTests(unittest.TestCase):
    def test_user_config_is_a_dunder_template_next_to_the_tool(self) -> None:
        path = config_path()
        self.assertEqual(path, Path(os.environ["XDG_CONFIG_HOME"]) / "noctalia/tools" / path.name)
        self.assertIn("__custom__", path.name)
        template = TOOLS / path.name
        config = load_config(template)
        self.assertTrue(any(provider.enabled for provider in config.providers))
        self.assertNotIn("api_key =", template.read_text(encoding="utf-8"))

    def test_orbit_system_tools_folder_lists_translate_settings(self) -> None:
        menu = tomllib.loads((TOOLS / "orbit-items__custom__.toml").read_text(encoding="utf-8"))
        tools = next(item for item in menu["items"] if item["id"] == "tools")
        children = tools["children"]
        item = next(child for child in children if child["id"] == "translate")
        self.assertEqual((item["cmd"], item["color_key"]), ("translate", "secondary"))
        shortcuts = [child["shortcut"] for child in children]
        self.assertEqual(len(shortcuts), len(set(shortcuts)))
        self.assertEqual(tools["desc"], f"Folder · {len(children)} Tools")

    def test_alt_e_goes_through_the_shell_action_gateway(self) -> None:
        binds = (_REPO / "configs/niri/binds.kdl").read_text(encoding="utf-8")
        lines = [line for line in binds.splitlines() if re.match(r"\s*Alt\+E\b", line)]
        self.assertEqual(len(lines), 1)
        self.assertIn('spawn "~/.config/niri/scripts/shell-action.sh" "translate"', lines[0])
        self.assertIn("repeat=false", lines[0])

    def test_runtime_packages_are_declared_in_the_noctalia_manifest(self) -> None:
        manifest = tomllib.loads((TOOLS.parent / ".module.toml").read_text(encoding="utf-8"))
        for package in ("python-gobject", "gtk-layer-shell", "wl-clipboard"):
            self.assertIn(package, manifest["packages"]["repo"])


if __name__ == "__main__":
    unittest.main()

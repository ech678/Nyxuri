"""fcitx5-rime plugin hook contracts (KM3): skin deploy, rime patch, revert.

The hooks live at configs/fcitx5-rime/hooks/ and are imported as modules.
Living-area files (classicui.conf, profile) are blueprint+preserve owned —
the hooks only touch the side domains, which is what these tests pin.
"""

import importlib.util
import configparser
import shutil
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.utils import TempEnv

REPO = Path(__file__).resolve().parents[2]


def _load_hook(name: str):
    path = REPO / "plugins" / "fcitx5-rime" / "hooks" / name
    mod_name = f"fcitx5_rime_hook_{name}"
    spec = importlib.util.spec_from_file_location(mod_name, path, loader=SourceFileLoader(mod_name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSkinDeploy(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.activate = _load_hook("activate")
        self.deactivate = _load_hook("deactivate")

    def tearDown(self):
        self._ctx.__exit__()

    def test_deploy_skin_copies_blueprint_templates(self):
        plugin_src = REPO / "plugins" / "fcitx5-rime"
        self.assertTrue(self.activate.deploy_skin(plugin_src))
        theme_dir = self._ctx.env.home / ".local/share/fcitx5/themes/nyxmellow/templates"
        for name in ("theme.conf", "panel.svg", "highlight.svg"):
            self.assertTrue((theme_dir / name).is_file(), name)

    def test_deploy_skin_fails_without_payload(self):
        empty = self._ctx.env.home / "empty-plugin"
        empty.mkdir()
        self.assertFalse(self.activate.deploy_skin(empty))


class TestRimeMount(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.activate = _load_hook("activate")
        self.home = self._ctx.env.home
        self.rime_dir = self.home / ".local/share/fcitx5/rime"
        self.marker = self.home / ".local/state/nyxuri/fcitx-nyxmellow-rime.owned"

    def tearDown(self):
        self._ctx.__exit__()

    def test_fresh_mount_writes_patch_and_ownership(self):
        with patch.object(self.activate.shutil, "which", return_value=None), \
             patch("builtins.print"):
            self.activate.mount_rime(self.rime_dir, self.marker)

        custom = self.rime_dir / "default.custom.yaml"
        self.assertEqual(custom.read_text(encoding="utf-8"), "patch:\n  schema_list:\n    - schema: rime_ice\n")
        self.assertTrue(self.marker.is_file())
        self.assertIn("default.custom.yaml", self.marker.read_text(encoding="utf-8"))

    def test_mount_is_idempotent(self):
        self.rime_dir.mkdir(parents=True)
        custom = self.rime_dir / "default.custom.yaml"
        custom.write_text("patch:\n  schema_list:\n    - schema: rime_ice\n", encoding="utf-8")

        with patch.object(self.activate.shutil, "which", return_value=None), \
             patch("builtins.print"):
            self.activate.mount_rime(self.rime_dir, self.marker)

        self.assertEqual(
            custom.read_text(encoding="utf-8"),
            "patch:\n  schema_list:\n    - schema: rime_ice\n",
            "idempotent mount must not duplicate the schema entry",
        )

    def test_mount_merges_into_existing_user_patch(self):
        self.rime_dir.mkdir(parents=True)
        custom = self.rime_dir / "default.custom.yaml"
        custom.write_text("patch:\n  schema_list:\n", encoding="utf-8")

        with patch.object(self.activate.shutil, "which", return_value=None), \
             patch("builtins.print"):
            self.activate.mount_rime(self.rime_dir, self.marker)

        content = custom.read_text(encoding="utf-8")
        self.assertIn("schema: rime_ice", content)


class TestRimeRevert(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.deactivate = _load_hook("deactivate")
        self.home = self._ctx.env.home
        self.rime_dir = self.home / ".local/share/fcitx5/rime"
        self.marker = self.home / ".local/state/nyxuri/fcitx-nyxmellow-rime.owned"
        self.rime_dir.mkdir(parents=True)
        self.marker.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_owned_patch_file_is_removed_entirely(self):
        (self.rime_dir / "default.custom.yaml").write_text(
            "patch:\n  schema_list:\n    - schema: rime_ice\n", encoding="utf-8"
        )
        self.marker.write_text("default.custom.yaml\n", encoding="utf-8")

        self.deactivate.revert_rime(self.rime_dir, self.marker)

        self.assertFalse((self.rime_dir / "default.custom.yaml").exists())
        self.assertFalse(self.marker.exists())

    def test_user_lines_survive_owned_line_removal(self):
        (self.rime_dir / "default.custom.yaml").write_text(
            "patch:\n  schema_list:\n    - schema: lunar\n    - schema: rime_ice\n", encoding="utf-8"
        )
        self.marker.write_text("default.custom.yaml\n", encoding="utf-8")

        self.deactivate.revert_rime(self.rime_dir, self.marker)

        content = (self.rime_dir / "default.custom.yaml").read_text(encoding="utf-8")
        self.assertIn("schema: lunar", content)
        self.assertNotIn("schema: rime_ice", content)

    def test_unowned_file_is_never_touched(self):
        custom = self.rime_dir / "default.custom.yaml"
        custom.write_text("patch:\n  schema_list:\n    - schema: rime_ice\n", encoding="utf-8")

        self.deactivate.revert_rime(self.rime_dir, self.marker)

        self.assertTrue(custom.is_file(), "no ownership record → hands off")


class TestSkinWithdraw(unittest.TestCase):
    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.deactivate = _load_hook("deactivate")
        self.theme_dir = self._ctx.env.home / ".local/share/fcitx5/themes/nyxmellow"

    def tearDown(self):
        self._ctx.__exit__()

    def test_known_files_removed_user_files_survive(self):
        (self.theme_dir / "templates").mkdir(parents=True)
        (self.theme_dir / "templates" / "theme.conf").write_text("t")
        (self.theme_dir / "theme.conf").write_text("rendered")
        (self.theme_dir / "user-notes.txt").write_text("mine")

        self.deactivate.withdraw_skin(self.theme_dir)

        self.assertFalse((self.theme_dir / "templates").exists())
        self.assertFalse((self.theme_dir / "theme.conf").exists())
        self.assertTrue((self.theme_dir / "user-notes.txt").is_file())


# --- merged from test_fcitx_theme_assets.py (KM3.5 测试镜像树) ---

"""Nine-slice images must leave a positive center for Fcitx 5.1.22+."""

import configparser
import shutil
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.utils import TempEnv


class TestThemeSlices(unittest.TestCase):
    def setUp(self):
        self.source = Path(__file__).resolve().parents[2] / "plugins/fcitx5-rime/hooks/skin/templates"

    def _load_theme(self):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.source / "theme.conf")
        return config

    def test_image_margins_leave_positive_center(self):
        with TempEnv() as env:
            target = env.home / "theme"
            shutil.copytree(self.source, target)
            config = configparser.ConfigParser(interpolation=None)
            config.read(target / "theme.conf")
            for section in config.sections():
                image = config[section].get("Image", "")
                margin_section = section + "/Margin"
                if not image or margin_section not in config:
                    continue
                with self.subTest(section=section):
                    svg = ET.parse(target / image).getroot()
                    margins = config[margin_section]
                    width = float(svg.attrib["width"])
                    height = float(svg.attrib["height"])
                    self.assertGreater(width - margins.getint("Left") - margins.getint("Right"), 0)
                    self.assertGreater(height - margins.getint("Top") - margins.getint("Bottom"), 0)

    def test_input_panel_slice_geometry_keeps_original_edges(self):
        config = self._load_theme()
        background = config["InputPanel/Background/Margin"]
        highlight = config["InputPanel/Highlight/Margin"]
        content_margin = config["InputPanel/ContentMargin"]
        panel = ET.parse(self.source / "panel.svg").getroot()
        highlight_svg = ET.parse(self.source / "highlight.svg").getroot()

        self.assertEqual(background.getint("Left"), 15)
        self.assertEqual(background.getint("Right"), 15)
        self.assertEqual(background.getint("Top"), 15)
        self.assertEqual(background.getint("Bottom"), 15)
        self.assertEqual(panel.attrib["viewBox"], "0 0 31 31")
        self.assertEqual(float(panel.attrib["width"]) - background.getint("Left") - background.getint("Right"), 1)
        self.assertEqual(float(panel.attrib["height"]) - background.getint("Top") - background.getint("Bottom"), 1)

        self.assertEqual(highlight.getint("Left"), 15)
        self.assertEqual(highlight.getint("Right"), 15)
        self.assertEqual(highlight.getint("Top"), 10)
        self.assertEqual(highlight.getint("Bottom"), 10)
        self.assertEqual(highlight_svg.attrib["viewBox"], "0 0 31 31")
        self.assertEqual(float(highlight_svg.attrib["width"]) - highlight.getint("Left") - highlight.getint("Right"), 1)
        self.assertEqual(content_margin.getint("Bottom"), 6)

    def test_theme_svg_templates_have_no_expensive_filters(self):
        for svg_name in ("panel.svg", "highlight.svg"):
            with self.subTest(svg=svg_name):
                content = (self.source / svg_name).read_text(encoding="utf-8")
                self.assertNotIn("filter=", content)
                self.assertNotIn("filter:", content)
                self.assertNotIn("<filter", content)
                self.assertNotIn("feGaussianBlur", content)

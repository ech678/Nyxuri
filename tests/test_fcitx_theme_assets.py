"""Nine-slice images must leave a positive center for Fcitx 5.1.22+."""

import configparser
import shutil
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.utils import TempEnv


class TestThemeSlices(unittest.TestCase):
    def setUp(self):
        self.source = Path(__file__).resolve().parents[1] / "assets/fcitx5/nyxmellow/templates"

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
        panel = ET.parse(self.source / "panel.svg").getroot()
        highlight_svg = ET.parse(self.source / "highlight.svg").getroot()

        self.assertEqual(background.getint("Left"), 15)
        self.assertEqual(background.getint("Right"), 15)
        self.assertEqual(background.getint("Top"), 15)
        self.assertEqual(background.getint("Bottom"), 15)
        self.assertEqual(panel.attrib["viewBox"], "0 0 64 64")
        self.assertEqual(float(panel.attrib["width"]) - background.getint("Left") - background.getint("Right"), 2)
        self.assertEqual(float(panel.attrib["height"]) - background.getint("Top") - background.getint("Bottom"), 2)

        self.assertEqual(highlight.getint("Left"), 15)
        self.assertEqual(highlight.getint("Right"), 15)
        self.assertEqual(highlight.getint("Top"), 10)
        self.assertEqual(highlight.getint("Bottom"), 10)
        self.assertEqual(highlight_svg.attrib["viewBox"], "0 0 64 60")
        self.assertEqual(float(highlight_svg.attrib["width"]) - highlight.getint("Left") - highlight.getint("Right"), 2)

    def test_theme_svg_templates_have_no_expensive_filters(self):
        for svg_name in ("panel.svg", "highlight.svg"):
            with self.subTest(svg=svg_name):
                content = (self.source / svg_name).read_text(encoding="utf-8")
                self.assertNotIn("filter=", content)
                self.assertNotIn("filter:", content)
                self.assertNotIn("<filter", content)
                self.assertNotIn("feGaussianBlur", content)


"""Nine-slice images must leave a positive center for Fcitx 5.1.22+."""

import configparser
import shutil
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.utils import TempEnv


class TestThemeSlices(unittest.TestCase):
    def test_image_margins_leave_positive_center(self):
        source = Path(__file__).resolve().parents[1] / "assets/fcitx5/nyxmellow/templates"
        with TempEnv() as env:
            target = env.home / "theme"
            shutil.copytree(source, target)
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

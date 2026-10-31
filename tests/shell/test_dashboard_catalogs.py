"""Dashboard control/transition catalog integrity contracts."""
import glob
import io
import json
import os
import re
import shutil
import signal
import sys
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

from nyxuri.kernel.ledger import active_shell, custom_shell_bin, set_shell
from nyxuri.cli import _cmd_shell
from tests.utils import TempEnv
# Imports consolidated from the dissolved bugfix ledger.
import contextlib
import subprocess
from pathlib import Path




class TestDashboardTransitionCatalogContract(unittest.TestCase):
    """Contract tests for Dashboard transition settings controls and catalogs."""

    def test_transition_catalog_and_control_contract(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shell_dir = os.path.join(repo_root, "shell")

        # 1. DashboardSettingsCatalog configures transition cards as 'combo'
        catalog_path = os.path.join(shell_dir, "plugins", 'settings', 'dashwindow', "DashboardSettingsCatalog.qml")
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog_content = f.read()

        # Desktop transition must be combo
        desktop_match = re.search(r'\"type\":\s*\"([^\"]+)\",\s*\"key\":\s*\"wallpaper:Desktop transition\"', catalog_content)
        self.assertIsNotNone(desktop_match, "wallpaper:Desktop transition must exist in DashboardSettingsCatalog")
        self.assertEqual(desktop_match.group(1), "combo", "wallpaper:Desktop transition must be combo")

        # Overview transition must be combo
        overview_match = re.search(r'\"type\":\s*\"([^\"]+)\",\s*\"key\":\s*\"wallpaper:Overview transition\"', catalog_content)
        self.assertIsNotNone(overview_match, "wallpaper:Overview transition must exist in DashboardSettingsCatalog")
        self.assertEqual(overview_match.group(1), "combo", "wallpaper:Overview transition must be combo")

        # 2. SettingsControlCatalog binds overview transition to PersonalizationConfig.transitionTypes
        control_path = os.path.join(shell_dir, "plugins", 'settings', 'dashwindow', "SettingsControlCatalog.qml")
        with open(control_path, "r", encoding="utf-8") as f:
            control_content = f.read()

        self.assertIn('"wallpaper:Overview transition"', control_content)
        self.assertIn("PersonalizationConfig.setOverviewTransitionType", control_content)
        self.assertIn("value), PersonalizationConfig.transitionTypes),", control_content,
                      "Overview transition must use PersonalizationConfig.transitionTypes, not awwwTransitionTypes")

        # Desktop transition must use native transitionTypes
        self.assertIn('"wallpaper:Desktop transition"', control_content)
        self.assertIn("WallpaperService.setWallpaperTransitionType", control_content)
        self.assertNotIn("awwwTransitionTypes", control_content)

        # 3. DashboardSelectCard hides MaterialSymbol when no icon is present
        select_card_path = os.path.join(shell_dir, "plugins", 'settings', 'dashwindow', "DashboardSelectCard.qml")
        with open(select_card_path, "r", encoding="utf-8") as f:
            select_card_content = f.read()

        self.assertIn("visible: !!(option.modelData && option.modelData.icon)", select_card_content,
                      "DashboardSelectCard must guard MaterialSymbol visibility to avoid empty icon spacing")


class TestDashboardSettingsCatalogIntegrity(unittest.TestCase):
    """Every settings card must resolve to a registered control.

    A card whose key has no control renders as a dead tile, and a control with no
    card is unreachable config. The two self-driven tiles (bar layout, easing
    curve) are the only intentional exceptions: they own their own state and read
    no registry entry.
    """

    # Tile types that carry their own state instead of a registry control.
    SELF_DRIVEN = {"barlayout", "bezier"}

    def _read(self, *parts):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(repo_root, "shell", "plugins", 'settings', 'dashwindow', *parts)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _entries(self):
        catalog = self._read("DashboardSettingsCatalog.qml")
        return re.findall(r'"type":\s*"([^"]+)",\s*"key":\s*"([^"]+)"', catalog)

    def test_every_card_resolves_to_a_control(self):
        controls = self._read("SettingsControlCatalog.qml")
        entries = self._entries()
        self.assertGreater(len(entries), 100, "catalog should carry the full settings surface")

        control_keys = set(re.findall(r'^\s*"([a-z]+:[^"]+)":\s*root\.', controls, re.M))
        self.assertGreater(len(control_keys), 100, "control registry should cover the catalog")

        unresolved = [key for tile_type, key in entries
                      if tile_type not in self.SELF_DRIVEN and key not in control_keys]
        self.assertEqual(unresolved, [], f"cards without a registered control: {unresolved}")

    def test_every_control_has_a_card(self):
        controls = self._read("SettingsControlCatalog.qml")
        card_keys = {key for _, key in self._entries()}
        control_keys = set(re.findall(r'^\s*"([a-z]+:[^"]+)":\s*root\.', controls, re.M))

        orphans = sorted(key for key in control_keys if key not in card_keys)
        self.assertEqual(orphans, [], f"controls unreachable from any card: {orphans}")

    def test_self_driven_tiles_are_the_only_exceptions(self):
        entries = self._entries()
        self.assertTrue(entries, "catalog must declare typed cards")

        for tile_type, key in entries:
            if tile_type in self.SELF_DRIVEN:
                continue
            self.assertIn(":", key, f"card {key} must use a namespaced key")

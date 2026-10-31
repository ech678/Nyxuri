"""Regression tests for upstream defects fixed during the bug-hunt rounds.

Each test reproduces a concrete failure that shipped in v4.0.0-alpha.1 and
asserts the corrected behavior, so the defect cannot silently return.
"""

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class TestConfigSectionHardening(unittest.TestCase):
    """A mistyped section must not abort the whole config load.

    loadFromObject() kept any truthy non-object section, because `parsed.bar
    || {}` leaves 7 untouched, and `"barLayoutLeft" in 7` throws. The catch-all
    in onLoaded then fell back to defaults and rewrote the file, so one bad
    field discarded every setting the user had already made.
    """

    def _source(self):
        return (Path(__file__).resolve().parents[2] / "shell" / "services"
                / "PersonalizationConfig.qml").read_text(encoding="utf-8")

    def _loader(self):
        source = self._source()
        start = source.index("function loadFromObject")
        return source[start:source.index("function needsScrollingMigration", start)]

    def test_every_section_is_coerced_to_an_object(self):
        loader = self._loader()
        for declaration in (
            "const wallpaper = configSection(source.wallpaper)",
            "const theme = configSection(source.theme)",
            "const effects = configSection(source.effects)",
            "const keystone = configSection(source.keystone)",
            "const media = configSection(keystone.media)",
            "const bar = configSection(source.bar)",
            "const sidebar = configSection(source.sidebar)",
            "const desktopCards = configSection(source.desktopCards)",
            "const transition = configSection(wallpaper.transition)",
            "const overview = configSection(wallpaper.overview)",
            "const parallax = configSection(wallpaper.parallax)",
            "const autoCycle = configSection(wallpaper.autoCycle)",
            "const fonts = configSection(theme.fonts)",
            "const horizontalClock = configSection(keystone.horizontalClock)",
            "const keyhole = configSection(keystone.keyhole)",
        ):
            self.assertIn(declaration, loader)

    def test_no_section_keeps_a_truthy_non_object(self):
        loader = self._loader()
        for section in ("wallpaper", "theme", "effects", "keystone", "bar", "sidebar",
                        "desktopCards", "hotCorners"):
            self.assertNotIn("parsed.%s || {}" % section, loader)

    def test_config_section_helper_rejects_non_objects_and_arrays(self):
        source = self._source()
        helper = source[source.index("function configSection"):
                        source.index("function loadFromObject")]
        self.assertIn('typeof value === "object"', helper)
        self.assertIn("!Array.isArray(value)", helper)
        self.assertIn("? value : {}", helper)

    def test_wallpaper_strings_are_type_narrowed(self):
        loader = self._loader()
        self.assertIn('typeof wallpaper.path === "string"', loader)
        self.assertIn('typeof wallpaper.folder === "string"', loader)
        self.assertIn('typeof wallpaper.pathLight === "string"', loader)
        self.assertIn('typeof wallpaper.pathDark === "string"', loader)
        self.assertNotIn('wallpaper.pathLight || ""', loader)
        self.assertNotIn('wallpaper.pathDark || ""', loader)

    def test_icon_theme_is_type_narrowed(self):
        loader = self._loader()
        self.assertIn('typeof theme.iconTheme === "string"', loader)
        self.assertNotIn('theme.iconTheme || ""', loader)

class TestConfigStoreFailureHandling(unittest.TestCase):
    """An unreadable store must be reported, never repaired by overwriting it.

    The catch-all in onLoaded used to set shouldRepair, and onLoadFailed reset
    every field to its default before saving, so one syntax error replaced the
    whole user config with defaults. Both handlers now consult the FileViewError
    the way DockService, DisplayColor and NotificationService already do.
    """

    def _source(self, name="PersonalizationConfig.qml"):
        return (Path(__file__).resolve().parents[2] / "shell" / "services"
                / name).read_text(encoding="utf-8")

    def _handler(self, source, signal, following):
        start = source.index(signal)
        return source[start:source.index(following, start)]

    def test_personalization_keeps_the_file_when_parsing_fails(self):
        source = self._source()
        catch = source[source.index("} catch (error) {", source.index("onLoaded:")):]
        self.assertIn("shouldRepair = false;", catch[:catch.index("onLoadFailed")])
        self.assertNotIn("shouldRepair = true;", catch[:catch.index("onLoadFailed")])

    def test_personalization_only_seeds_a_missing_store(self):
        handler = self._handler(self._source(), "onLoadFailed:", "onSaveFailed:")
        self.assertIn("error === FileViewError.FileNotFound", handler)
        self.assertIn("root.save();", handler)
        self.assertIn("console.warn", handler)

    def test_personalization_reports_save_failures(self):
        handler = self._handler(self._source(), "onSaveFailed:", "Component.onDestruction")
        self.assertIn("console.warn", handler)

    def test_ui_preferences_only_seeds_a_missing_store(self):
        handler = self._handler(self._source("UiPreferences.qml"), "onLoadFailed:", "onSaveFailed:")
        self.assertIn("error === FileViewError.FileNotFound", handler)
        self.assertIn("root.save();", handler)
        self.assertIn("console.warn", handler)

    def test_ui_preferences_reports_save_failures(self):
        handler = self._handler(self._source("UiPreferences.qml"), "onSaveFailed:", "Timer {")
        self.assertIn("console.warn", handler)

    AUXILIARY_STORES = (
        "services/IdleService.qml",
        "plugins/bar/tray/TrayService.qml",
        "plugins/sidebars/quicksettings/QuickToggleConfig.qml",
    )

    def _relative(self, relative):
        return (Path(__file__).resolve().parents[2] / "shell" / relative).read_text(encoding="utf-8")

    @staticmethod
    def _catch_block(source):
        marker = "} catch (error) {"
        start = source.index(marker)
        depth = 0
        for index in range(start + len(marker) - 1, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    return source[start:index + 1]
        raise AssertionError("unterminated catch block")

    def test_auxiliary_stores_keep_the_file_when_parsing_fails(self):
        for relative in self.AUXILIARY_STORES:
            block = self._catch_block(self._relative(relative))
            self.assertNotIn("root.save", block, relative)
            self.assertIn("leaving the existing", block, relative)

    def test_auxiliary_stores_only_seed_a_missing_file(self):
        for relative in self.AUXILIARY_STORES:
            source = self._relative(relative)
            handler = self._handler(source, "onLoadFailed:", "onSaveFailed:")
            self.assertIn("error === FileViewError.FileNotFound", handler, relative)
            self.assertIn("console.warn", handler, relative)

    def test_auxiliary_stores_report_save_failures(self):
        for relative in self.AUXILIARY_STORES:
            source = self._relative(relative)
            self.assertIn("onSaveFailed", source, relative)

    STATEFUL_STORES = (
        "plugins/sidebars/dashboard/infotools/InfoDrawerState.qml",
        "plugins/sidebars/dashboard/infotools/TodoService.qml",
    )

    def test_stateful_stores_only_seed_a_missing_file(self):
        for relative in self.STATEFUL_STORES:
            source = self._relative(relative)
            handler = self._handler(source, "onLoadFailed:", "onSaveFailed:")
            self.assertIn("error !== FileViewError.FileNotFound", handler, relative)
            self.assertIn("console.warn", handler, relative)

    def test_stateful_stores_report_save_failures(self):
        for relative in self.STATEFUL_STORES:
            self.assertIn("onSaveFailed", self._relative(relative), relative)

    def test_info_drawer_skips_the_rewrite_after_a_failed_parse(self):
        handler = self._handler(
            self._relative("plugins/sidebars/dashboard/infotools/InfoDrawerState.qml"),
            "onLoaded:", "onLoadFailed:")
        self.assertIn("let loaded = false;", handler)
        self.assertIn("loaded = true;", handler)
        self.assertLess(handler.index("loaded = true;"), handler.index("} catch"))
        self.assertLess(handler.index("if (loaded)"), handler.index("scheduleSave"))

class TestSystemThemeProbeGuard(unittest.TestCase):
    """The poller must only adopt a mode the system actually reported.

    `gsettings get ... color-scheme` exits 0 with 'default' wherever GNOME has
    no scheme configured, and the unguarded parse turned that into a "light"
    observation that overwrote the user's saved dark theme.
    """

    def _poller(self):
        source = (Path(__file__).resolve().parents[2] / "shell" / "services"
                  / "UiPreferences.qml").read_text(encoding="utf-8")
        start = source.index("id: themePoller")
        return source[start:source.index("id: systemThemeWriter", start)]

    def test_poller_requires_an_explicit_scheme_preference(self):
        poller = self._poller()
        self.assertIn("prefer-dark", poller)
        self.assertIn("prefer-light", poller)
        guard = poller.index("if (!prefersDark && !prefersLight)")
        emit = poller.index("root.systemThemeModeObserved(")
        self.assertLess(guard, emit, "the observation must be emitted behind the guard")

    def test_poller_does_not_infer_light_from_unrecognized_output(self):
        poller = self._poller()
        self.assertNotIn('systemThemeModeObserved(root.darkMode ? "dark" : "light")', poller)
        self.assertIn('systemThemeModeObserved(prefersDark ? "dark" : "light")', poller)

class TestUiPreferencesDarkModeMirror(unittest.TestCase):
    """darkMode drives per-mode wallpaper selection, so it cannot start stale.

    It is not persisted and was only written by setDarkMode, which ThemeService
    calls on an actual mode change, leaving it false for the whole first run.
    """

    def _source(self):
        return (Path(__file__).resolve().parents[2] / "shell" / "services"
                / "UiPreferences.qml").read_text(encoding="utf-8")

    def test_dark_mode_initializes_from_the_theme_mode(self):
        self.assertIn('property bool darkMode: PersonalizationConfig.themeMode === "dark"',
                      self._source())

    def test_dark_mode_follows_later_theme_mode_changes(self):
        source = self._source()
        self.assertIn("target: PersonalizationConfig", source)
        self.assertIn("function onThemeModeChanged()", source)

    def test_dark_mode_is_still_writable_for_set_dark_mode(self):
        source = self._source()
        self.assertNotIn("readonly property bool darkMode", source)
        self.assertIn("root.darkMode = enabled;", source)

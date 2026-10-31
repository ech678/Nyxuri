"""T3 M2 contracts: the Nexus master-detail settings shell.

The frameless window keeps its entire external API surface (routing, search
deep links, child windows) while the chrome is replaced: retired NavigationRail
family and FloatingActionButton stay dead, the NavPane is the Caelestia-style
master list driven by the M1 atoms, the in-window search is a visual stub
exactly like the original, and every new user-visible string resolves in zh_CN.
Geometry and type come from NexusStyle (unscaled Caelestia token parity).
"""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL = REPO_ROOT / "shell"
SETTINGS = SHELL / "plugins" / "settings"
CONTROLS = SHELL / "ui"

EXECUTED = (
    "NavigationRailButton.qml",
    "NavigationRailTabArray.qml",
    "NavigationRailExpandButton.qml",
    "FloatingActionButton.qml",
)

WINDOW_API = (
    "function prepareSearchTarget(",
    "function advanceSearchTarget(",
    "function openPage(",
    "function openPageSection(",
    "function applyPendingPageSection(",
    "function closeChildWindows(",
    "function showWindow(",
    "function hideWindow(",
    "function toggleWindow(",
    "function pageSource(",
    'readonly property string currentRouteId:',
    "readonly property var searchPageAnchor:",
    "signal popoutClosed",
)


def _runtime_sources():
    for sub in ("app", "commons", "ui", "services", "plugins"):
        for pattern in ("*.qml", "*.js"):
            yield from (SHELL / sub).rglob(pattern)


def _read(relative):
    return (SETTINGS / relative).read_text(encoding="utf-8")


class TestExecutedChrome(unittest.TestCase):
    """The retired rail family, FAB and the search-results experiment stay dead."""

    def test_executed_files_are_gone(self):
        missing = [name for name in EXECUTED if (SETTINGS / name).exists()]
        self.assertEqual(missing, [], f"executed files resurrected: {missing}")

    def test_no_runtime_reference_survives(self):
        offenders = []
        for path in _runtime_sources():
            if any(name[:-4] in path.read_text(encoding="utf-8") for name in EXECUTED):
                offenders.append(path.relative_to(REPO_ROOT))
        self.assertEqual(offenders, [], f"runtime code still references executed chrome: {offenders}")


class TestWindowShellIsReskinnedNotRewired(unittest.TestCase):
    """Chrome replaced, external behaviour surface intact."""

    def test_window_api_surface_is_pinned(self):
        source = _read("ControlCenterWindow.qml")
        for token in WINDOW_API:
            self.assertIn(token, source, f"window lost API token: {token}")

    def test_wayland_title_is_stable_for_focus_matching(self):
        source = _read("ControlCenterWindow.qml")
        self.assertIn('title: "nyxuri-settings"', source,
                      "SettingsBackend.focusWindow() matches this exact title")

    def test_destruction_still_closes_child_windows(self):
        self.assertIn("Component.onDestruction: root.closeChildWindows()",
                      _read("ControlCenterWindow.qml"))

    def test_two_zone_chrome_matches_the_original(self):
        source = re.sub(r"\s+", " ", _read("ControlCenterWindow.qml"))
        # Left nav zone: nav width + 16px margins, window-left corner rounding,
        # sharing the surface-container-low fill with the frame and the chip.
        self.assertIn("width: root.navPaneWidth + NexusStyle.navMargin * 2", source)
        self.assertIn("topLeftRadius: NexusStyle.rounding.large", source)
        self.assertIn("color: Appearance.colors.colSurfaceContainerLow", source)
        self.assertIn("radius: NexusStyle.rounding.large", source)
        # Pages region: 16px clear of the 12px frame band on three sides and
        # of the nav zone on the left (Pages.qml anchors).
        self.assertIn("anchors.leftMargin: NexusStyle.frameBand + NexusStyle.chromeInset", source)
        self.assertIn("anchors.rightMargin: NexusStyle.frameBand + NexusStyle.chromeInset", source)
        self.assertIn("CompositorBlurRegion {", source)
        self.assertIn("DragHandler {", source, "window must stay draggable without a titlebar")
        self.assertNotIn("titlebar", source)
        self.assertNotIn("navExpanded", source)
        self.assertNotIn('text: I18n.tr("Settings")', source, "the old centred title is retired")

    def test_window_uses_caelestia_proportions(self):
        source = _read("ControlCenterWindow.qml")
        self.assertIn("* NexusStyle.heightMult", source,
                      "height = 70% of the screen like the original")
        self.assertIn("* NexusStyle.ratio", source, "width = height * 16/9 like the original")
        self.assertIn("Math.max(NexusStyle.minHeight", source)
        self.assertIn("Math.max(NexusStyle.minWidth", source)
        # The 800x500 floor lives in the implicit-size math: Quickshell 0.3.2
        # collapses the window to minimum when minimumSize is assigned
        # (2026-10-25 width incident — window pinned at 800px wide).
        self.assertNotIn("minimumSize", source)
        self.assertNotIn("minimumWidth", source)
        self.assertNotIn("minimumHeight", source)

    def test_nav_width_holds_a_stable_quarter(self):
        # Author decision (2026-10-25): the original third felt too wide — a
        # quarter of the window (capped at 480) reads calmer at every size.
        source = _read("ControlCenterWindow.qml")
        self.assertIn("Math.min(NexusStyle.maxNavWidth, Math.round(root.width / 4))", source)

    def test_close_chip_is_retired(self):
        # Author decision (2026-10-25): no window button at all — closing
        # rides the mod+i toggle and the compositor.
        source = _read("ControlCenterWindow.qml")
        for dead in ("closeButton", "m3error", 'text: "close"', "Accessible.name"):
            self.assertNotIn(dead, source, f"close-chip remnant: {dead}")

    def test_route_title_responds_to_the_current_route(self):
        source = _read("ControlCenterWindow.qml")
        self.assertIn("NexusStyle.font.titleLarge", source)
        self.assertIn("switchAnim", source)
        self.assertIn("SettingsPageHost {", source)

    def test_route_title_shim_steps_aside_for_self_titled_pages(self):
        # NexusPageBase pages render their own title; the window shim (kept
        # only for old pre-M3 pages) must hide and collapse (2026-10-25
        # double-"About" incident).
        source = _read("ControlCenterWindow.qml")
        self.assertIn("pageLoader.item.rendersPageTitle === true", source)
        self.assertIn("visible: !root.pageRendersTitle", source)
        self.assertIn("implicitHeight: root.pageRendersTitle ? 0 : routeTitle.implicitHeight", source)

    def test_switch_animation_is_direction_aware_and_container_level(self):
        source = _read("ControlCenterWindow.qml")
        self.assertIn("animationsEnabled: false", source,
                      "the host swaps layers instantly; the container animates")
        self.assertIn("_animOffset", source)
        self.assertIn("pageContainer.anchors", source,
                      "the whole page pane slides vertically like Pages.qml")
        self.assertIn("NexusStyle.padding.extraLarge * (root.currentPage", source,
                      "28px slide offset, direction-aware")

    def test_route_descriptions_bridge_through_the_catalog(self):
        source = _read("ControlCenterWindow.qml")
        self.assertIn("SpotlightCatalog.description(", source,
                      "subtitles must use the translated catalog bridge, not raw JSON")

    def test_pane_stays_presentation_only(self):
        pane = _read("NexusNavPane.qml")
        self.assertNotIn("SettingsBackend", pane,
                         "the pane is presentation; behaviour stays with the window")


class TestNavPaneComposition(unittest.TestCase):
    """The master list is built from the M1 atoms, not a parallel system."""

    def test_nav_files_live_in_the_settings_unit_root(self):
        for name in ("NexusNavPane.qml", "NexusNavRow.qml"):
            self.assertTrue((SETTINGS / name).is_file(), f"{name} missing from plugins/settings")
            self.assertFalse((CONTROLS / name).exists(),
                             f"{name} must not leak into the atom pool")

    def test_atom_pool_is_untouched_by_the_shell(self):
        # S0-1: the eleven M1 atoms live flat in ui/ beside the control
        # library; the standalone settings/controls pool must stay gone.
        from test_preference_atoms import ATOMS
        for name in ATOMS:
            self.assertTrue((CONTROLS / name).is_file(), f"{name} missing from ui/")
        self.assertFalse((SETTINGS / "controls").exists(),
                         "the old settings/controls pool must stay gone (S0-1)")

    def test_pane_composes_the_atoms(self):
        source = _read("NexusNavPane.qml")
        for token in ("NexusSearchBar {", "NexusNavRow {", "VerticalFadeFlickable {"):
            self.assertIn(token, source, f"NavPane must compose {token}")
        self.assertNotIn("ScrollBar", source, "the original list fades at the edges, no scrollbar")

    def test_pane_carries_no_footer_actions(self):
        # Author decision (2026-10-25): the nav list is search + rows, pure
        # like the original — the configuration quick actions live in About.
        source = _read("NexusNavPane.qml")
        for dead in ("PreferenceAction", "configEditRequested", "configCopyRequested",
                     "configPath", "justCopied"):
            self.assertNotIn(dead, source, f"footer remnant in the nav pane: {dead}")

    def test_search_is_a_stub_like_the_original(self):
        source = _read("NexusNavPane.qml")
        for dead in ("routeMatches", "suggestions", "Popup", "deepSearchRequested",
                     "activateFirstMatch", "searchText"):
            self.assertNotIn(dead, source,
                             f"the original Nexus search bar is a visual stub: {dead} must not return")

    def test_categories_are_purely_geometric(self):
        source = _read("NexusNavPane.qml")
        self.assertNotIn("PreferenceHeader", source,
                         "the original NavLocations carries no section labels")
        self.assertIn("groupStart", source,
                      "category starts drive the extra gap plus connected rounding")

    def test_row_matches_the_caelestia_shape(self):
        source = re.sub(r"\s+", " ", _read("NexusNavRow.qml"))
        self.assertIn("ConnectedRect {", source)
        self.assertIn("property string description:", source)
        # Active pill = extraLargeIncreased (32), press collapse = medium (12).
        self.assertIn(
            "uniformRadius: rowPress.pressed ? NexusStyle.rounding.medium : root.active ? NexusStyle.rounding.extraLargeIncreased : -1",
            source)
        # Resting rows sit on the solved surface-container-high fill.
        self.assertIn("Appearance.colors.colSurfaceContainerHigh", source)
        # Text keeps body-medium/label-small with resting colours in every state.
        self.assertIn("NexusStyle.font.bodyMedium", source)
        self.assertIn("NexusStyle.font.labelSmall", source)
        self.assertNotIn("Font.DemiBold", source,
                         "the original label never bolds or recolours on activation")
        self.assertIn("signal activated", source)

    def test_grouping_covers_every_top_level_route(self):
        pane = _read("NexusNavPane.qml")
        table = pane[pane.index("readonly property var groupTable"):pane.index("readonly property var navModel")]
        grouped = set(re.findall(r'"([a-z.-]+)"', table))
        document = json.loads((SETTINGS / "settings-routes.json").read_text(encoding="utf-8"))
        top_level = {route["id"] for route in document["routes"] if len(route["path"]) == 1}
        self.assertTrue(top_level <= grouped,
                        f"routes missing from the grouping table (they would join the "
                        f"trailing leftovers group): {sorted(top_level - grouped)}")

    def test_no_hardcoded_colors_in_the_new_chrome(self):
        for name in ("ControlCenterWindow.qml", "NexusNavPane.qml", "NexusNavRow.qml"):
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", _read(name)),
                              f"{name} hardcodes a hex color")

    def test_new_strings_resolve_in_zh_cn(self):
        zh = (SHELL / "commons" / "i18n" / "zh_CN.toml").read_text(encoding="utf-8")
        for key in ("Edit configuration file", "Copy configuration path", "About",
                    "Compositor", "System information and versions"):
            self.assertIn(f'"{key}"', zh)


class TestAboutPage(unittest.TestCase):
    """The About page is the first page built entirely from the atom suite."""

    def test_route_is_registered(self):
        document = json.loads((SETTINGS / "settings-routes.json").read_text(encoding="utf-8"))
        route = next((r for r in document["routes"] if r["id"] == "about"), None)
        self.assertIsNotNone(route, "about route missing")
        self.assertEqual(route["icon"], "info")
        self.assertEqual(route["source"], "AboutPage.qml")
        self.assertTrue(route["description"].strip())

    def test_page_is_built_from_atoms_and_identity_service(self):
        source = _read("AboutPage.qml")
        for token in ("NexusPageBase {", "ConnectedRect {", "PreferenceHeader {",
                      "PreferenceInfo {", "PreferenceAction {"):
            self.assertIn(token, source)
        for field in ("hostName", "productName", "distroName", "kernelRelease", "biosVersion"):
            self.assertIn(field, source, f"About must surface SystemIdentityService.{field}")
        self.assertIn("SystemIdentityService.wmName", source)
        self.assertIn("NexusStyle.font.headlineLarge", source,
                      "hero title uses the original headline-large size")

    def test_configuration_quick_actions_live_here(self):
        # Relocated from the retired NavPane footer (author decision
        # 2026-10-25): edit/copy ride the page-service pattern like ShellPage.
        source = _read("AboutPage.qml")
        self.assertIn('text: I18n.tr("Edit configuration file")', source)
        self.assertIn('text: I18n.tr("Copy configuration path")', source)
        self.assertIn("ApplicationService.openUrl(Paths.fileUrl(PersonalizationConfig.filePath))",
                      source)
        self.assertIn("Quickshell.clipboardText = PersonalizationConfig.filePath", source)

    def test_external_commands_have_exact_shapes(self):
        # Views never spawn processes; the only About-related probe lives in
        # SystemIdentityService with a fixed argv.
        self.assertNotIn("Process {", _read("AboutPage.qml"),
                         "views route I/O through services, not their own processes")
        service = (SHELL / "services" / "SystemIdentityService.qml").read_text(encoding="utf-8")
        self.assertIn('command: ["quickshell", "--version"]', service)


if __name__ == "__main__":
    unittest.main()

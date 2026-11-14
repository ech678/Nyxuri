"""B4 bar reskin and cornerStyle contract tests.

Verifies:
  - Promoted end4 baseline files exist in shell/plugins/bar/ and carry GPL-3 Fork & Trim headers
  - No bare import qs statements in the promoted components
  - BarGroup.qml has trimmed dead paths (BarGroupStylePopup, widgetStyles) and manages child backgroundVisible
  - Divisor.qml supports rect/dot/space styles and connects to PersonalizationConfig
  - BarContent.qml registers "divisor" and "island" in its widget URL map
  - DynamicIsland.qml wires isMaterial to PersonalizationConfig.barCornerStyle
  - PersonalizationConfig defines barCornerStyles, barBorderlessModes, barDividerStyles, and includes "divisor"
  - BarContent.qml implements 3-lane cornerStyle, centerOnly mode, and material pill wrapping
  - HorizontalBarWindow.qml and VerticalBarWindow.qml implement roundDecorators and dynamic exclusiveThickness
"""

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAR_DIR = os.path.join(REPO_ROOT, "shell", "plugins", "bar")
SERVICES_DIR = os.path.join(REPO_ROOT, "shell", "services")
COMMONS_DIR = os.path.join(REPO_ROOT, "shell", "commons")


def read_bar_file(filename):
    with open(os.path.join(BAR_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def read_services_file(filename):
    with open(os.path.join(SERVICES_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def read_commons_file(filename):
    with open(os.path.join(COMMONS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


class BarEnd4ContractTest(unittest.TestCase):

    def test_promoted_files_exist(self):
        promoted = [
            "RoundCorner.qml",
            "Divisor.qml",
            "BarGroup.qml",
            "StyledPopupHeaderRow.qml",
            "StyledPopupValueRow.qml",
        ]
        for name in promoted:
            path = os.path.join(BAR_DIR, name)
            self.assertTrue(os.path.isfile(path), f"Missing promoted file {name} in {BAR_DIR}")

    def test_fork_and_trim_headers(self):
        for name in ["RoundCorner.qml", "Divisor.qml", "BarGroup.qml", "StyledPopupHeaderRow.qml", "StyledPopupValueRow.qml"]:
            content = read_bar_file(name)
            self.assertIn("Fork & Trim: end4-pC", content, f"{name} missing Fork & Trim header")
            self.assertIn("GPL-3", content, f"{name} missing GPL-3 notice")

    def test_no_bare_import_qs(self):
        for name in ["RoundCorner.qml", "Divisor.qml", "BarGroup.qml", "StyledPopupHeaderRow.qml", "StyledPopupValueRow.qml", "BarContent.qml"]:
            content = read_bar_file(name)
            for line in content.splitlines():
                stripped = line.strip()
                self.assertFalse(
                    stripped == "import qs" or stripped.startswith("import qs "),
                    f"{name} contains invalid bare 'import qs': {line}"
                )

    def test_bar_group_trims_and_bindings(self):
        content = read_bar_file("BarGroup.qml")
        # B8.1: the group is a full end4 fork again — the per-widget style
        # editor is wired, and persistence goes through PersonalizationConfig
        # instead of the read-only Config bridge.
        self.assertIn("BarGroupStylePopup", content, "BarGroup must wire the right-click style editor")
        self.assertIn("PersonalizationConfig.setBarWidgetStyle", content, "widget styles must persist via PersonalizationConfig")
        self.assertIn("PersonalizationConfig.barIsMaterial", content, "material treatment comes from the single source")
        self.assertIn("resolvedGroupColor", content, "BarGroup must consume bar.groupColor")
        self.assertIn("paintBackground", content, "BarGroup must honour paintBackground")
        self.assertIn("isSegmented", content, "BarGroup must implement segmented borders")
        self.assertIn("isMaterial", content)
        self.assertIn("startRadius", content)
        self.assertIn("endRadius", content)

    def test_bar_content_centered_lanes(self):
        content = read_bar_file("BarContent.qml")
        self.assertIn("(parent.width - width) / 2", content, "middle lane must be anchored to the optical centre")
        self.assertNotIn("hostScale", content, "the iNiR compression clamp is retired (NaN source)")
        self.assertNotIn("centerHostX", content, "the iNiR compression clamp is retired (NaN source)")
        self.assertIn('"island"', content, "island must be in the material-pill blacklist")
        self.assertIn("bar.m3.layouts", content)
        # B9.3: the island is a layout member, not a second config gate.
        self.assertNotIn("PersonalizationConfig.islandEnabled", content)
        self.assertNotIn("filtered.filter(name => name !== \"island\")", content)
        # Only the active style branch instantiates widgets.
        self.assertIn("active: root.isMaterial", content)
        self.assertIn("active: !root.isMaterial", content)

    def test_material_helper_is_the_single_source(self):
        config = read_services_file("PersonalizationConfig.qml")
        self.assertIn("readonly property bool barIsMaterial", config)
        self.assertIn("readonly property bool barIsMaterialHug", config)
        self.assertIn("readonly property bool barIsPanel", config)
        # B9.6: UtilButton is the end4 button verbatim — it never branches on
        # material (one hover language for both bar skins), so it left this list.
        for name in ("Media.qml", "SysTray.qml", "UtilButtons.qml",
                     "Divisor.qml", "Visualizer.qml", "BatteryIndicator.qml"):
            content = read_bar_file(name)
            self.assertIn("PersonalizationConfig.barIsMaterial", content, name)
            self.assertNotIn("cornerStyle === 3", content, f"{name} re-derives material")

    def test_system_icons_are_the_inir_fork(self):
        content = read_bar_file("SystemIcons.qml")
        self.assertIn("Fork & Trim: iNiR", content)
        self.assertIn("KeyboardIndicators", content)
        self.assertIn("HyprlandXkbIndicator", content)
        self.assertIn("contentColorOverridden", content)
        # B9.2: every status is its own fixed 26px slot, so a conditional icon
        # never changes its neighbours' width.
        self.assertGreaterEqual(content.count("SystemIconSlot {"), 5)
        self.assertIn("PeripheralBattery.lowDevices", content)
        self.assertIn("PeripheralBattery.isCritical", content)
        self.assertIn("root.openQuickSettings(\"audio\")", content)
        self.assertIn("root.openQuickSettings(\"network\")", content)
        self.assertIn("root.openQuickSettings(\"bluetooth\")", content)
        self.assertIn("VolumeService.toggleSourceMute", content)
        self.assertIn("Appearance.sizes.barUtilIconSize", read_bar_file("SystemIconSlot.qml"))
        self.assertIn("Appearance.sizes.barPowerButtonSize", read_bar_file("PowerButton.qml"))
        # UtilButton keeps the end4 hover expansion for the quick-settings row;
        # the status slot deliberately does not.
        self.assertIn("hovered ? 54 : 26", read_bar_file("UtilButton.qml"))
        slot = read_bar_file("SystemIconSlot.qml")
        self.assertNotIn("hovered ? 54 : 26", slot)
        self.assertIn("readonly property int slotSize: 26", slot)
        self.assertIn("M3ToolTip {", slot)
        self.assertIn("signal wheeled(real delta)", slot)
        self.assertFalse(os.path.exists(os.path.join(BAR_DIR, "NotificationUnreadCount.qml")),
                         "the embedded notification widget must fold into the status slot")

    def test_peripheral_battery_service_is_the_end4_fork(self):
        content = read_services_file("PeripheralBattery.qml")
        self.assertIn("Fork & Trim: end4-pC", content)
        self.assertIn("GPL-3", content)
        self.assertIn("UPowerDeviceType.Mouse", content)
        self.assertIn("UPowerDeviceType.Headset", content)
        self.assertIn("Config.options.battery.peripheralLow", content)
        self.assertIn("Config.options.battery.peripheralCritical", content)
        self.assertIn("Config.options.battery.peripheralNotify", content)
        # The probe swaps fake devices in through this seam.
        self.assertIn("property var deviceSource: UPower.devices.values", content)
        # External commands leave through the gateway with an owner, never a
        # bare execDetached.
        self.assertIn('ActionGateway.execute(', content)
        self.assertIn('"bar:peripheral-battery"', content)
        self.assertNotIn("Quickshell.execDetached(", content)
        self.assertNotIn("Translation.tr", content)
        self.assertIn("I18n.tr", content)

    def test_idle_avatar_is_optional(self):
        content = read_bar_file("DiIdle.qml")
        self.assertIn("PersonalizationConfig.islandShowAvatar", content)
        self.assertIn("visible: diIdleRoot.showAvatar", content)
        self.assertIn("avatarBlockWidth", content)

    def test_active_window_is_an_end4_fork(self):
        content = read_bar_file("ActiveWindow.qml")
        self.assertIn("Fork & Trim: end4-pC", content)
        self.assertIn("CompositorDriver.focusedWindow", content)
        self.assertIn("activeWorkspaceForOutput", content)
        self.assertIn("property color contentColor", content)
        self.assertIn("contentColorOverridden", content)
        self.assertNotIn("console.log(", content)

    def test_self_hiding_widgets_collapse_their_group(self):
        group = read_bar_file("BarGroup.qml")
        # `Item.visible` reports effective visibility, so reading it here would
        # deadlock a group that hid once (the hidden group masks the child).
        self.assertIn('"barWidgetVisible" in root.loadedWidget', group)
        self.assertIn("visible: root.hasContent", group)
        media = read_bar_file("Media.qml")
        self.assertIn("readonly property bool barWidgetVisible: root.shouldShow", media)
        self.assertIn("visible: root.shouldShow", media)

    def test_retired_island_controls_stay_out(self):
        """B8.4/B8.5: every retired key must be gone from the config store,
        the island page and both settings catalogs."""
        retired = (
            "islandStyle", "islandOverlay", "islandPosition", "islandHoverAction",
            "islandLeftClickAction", "islandMiddleClickAction", "islandMediaProgressStyle",
            "islandMediaCoverStyle", "islandMediaColorStyle", "islandKeyholeCard",
        )
        sources = {
            "PersonalizationConfig.qml": read_services_file("PersonalizationConfig.qml"),
            "IslandPage.qml": read_bar_file("island/IslandPage.qml"),
        }
        for name, content in sources.items():
            for key in retired:
                self.assertNotIn(key, content, f"{name} still carries retired key {key}")

    def test_divisor_contracts(self):
        content = read_bar_file("Divisor.qml")
        self.assertIn("PersonalizationConfig.barDividerStyle", content)
        self.assertIn("isMaterial", content)
        self.assertIn("vertical", content)

    def test_b9_6_content_color_covers_every_styleable_widget(self):
        """The right-click style editor drives contentColor through BarGroup's
        Bindings; every widget that lost the properties in the Clavis purge
        has them back per end4."""
        for name in ("ClockWidget.qml", "Resources.qml", "Resource.qml",
                     "BatteryIndicator.qml", "Divisor.qml", "UtilButtons.qml",
                     "Media.qml", "Workspaces.qml"):
            content = read_bar_file(name)
            self.assertIn("property color contentColor", content, name)
            self.assertIn("contentColorOverridden", content, name)
        # BarGroup's probe-then-bind contract still finds the properties.
        group = read_bar_file("BarGroup.qml")
        self.assertIn('"contentColor" in root.loadedWidget', group)
        self.assertIn('"contentColorOverridden" in root.loadedWidget', group)
        # The end4 override semantics at the use sites.
        self.assertIn("root.contentColorOverridden ? root.contentColor : Appearance.colors.colOnLayer1",
                      read_bar_file("Media.qml"), "media non-material text honours the override")
        self.assertIn('text: "• "', read_bar_file("Divisor.qml"), "end4 dot glyph")

    def test_b9_6_workspaces_is_the_end4_fork_with_fixed_slots(self):
        content = read_bar_file("Workspaces.qml")
        self.assertIn("Fork & Trim: end4-pC", content)
        # Slot count follows the iNiR original's dynamicCount semantics —
        # exactly the workspaces niri reports on the output (empty ones
        # persist), budget-capped with group paging. Not end4's fixed grid.
        self.assertIn("barWorkspaceShown", content)
        self.assertIn("root.group * root.shownBudget + index + 1", content)
        self.assertIn("existingMaxIdx", content)
        self.assertIn("Math.max(1, Math.min(root.shownBudget, root.existingMaxIdx - root.group * root.shownBudget))", content)
        self.assertIn("(root.activeNumber - 1) % root.shownBudget", content)
        self.assertIn("fakeWorkspace", content)
        # end4 metrics: material slots are wider (30), default 26.
        self.assertIn("PersonalizationConfig.barIsMaterial ? 30 : 26", content)
        # Four styles through the verbatim WorkspacesAlt fork.
        self.assertIn("WorkspacesAlt", content)
        alt = read_bar_file("WorkspacesAlt.qml")
        self.assertIn("Fork & Trim: end4-pC", alt)
        for style in ("gnome", "dots", "ticks"):
            self.assertIn(f'"{style}"', alt)
        # Active-indicator tinting goes through the end4 Colorizer.
        self.assertIn("Colorizer", content)
        # Right-click toggles the compositor overview; empty slots focus the
        # slot index on this output (niri creates on demand).
        self.assertIn("CompositorDriver.toggleOverview", content)
        self.assertIn("focusWorkspaceOnOutput", content)
        driver = read_services_file("NiriDriver.qml")
        self.assertIn("focusWorkspaceOnOutput", driver)
        self.assertIn('"FocusMonitor"', driver)
        self.assertIn('"Index"', driver)
        self.assertIn("focusWorkspaceOnOutput", read_services_file("CompositorDriver.qml"))
        # Settings: style select + slot count with a real store round-trip.
        config = read_services_file("PersonalizationConfig.qml")
        self.assertIn("property string barWorkspaceStyle", config)
        self.assertIn("property int barWorkspaceShown", config)
        self.assertIn("setBarWorkspaceStyle", config)
        self.assertIn("setBarWorkspaceShown", config)
        self.assertIn('"workspaceStyle"', config)
        self.assertIn('"workspaceShown"', config)
        page = read_bar_file("GeneralBarPage.qml")
        self.assertIn("setBarWorkspaceStyle", page)
        self.assertIn("setBarWorkspaceShown", page)

    def test_b9_6_geometry_matches_end4(self):
        # PowerButton: end4 material size 32 (was 28).
        self.assertIn("barPowerButtonSize: 32", read_commons_file("Appearance.qml"))
        # ActiveWindow: no right-margin squeeze, no invented fallback icon.
        active = read_bar_file("ActiveWindow.qml")
        self.assertNotIn("desktop_windows", active)
        self.assertNotIn("anchors.rightMargin: 6", active)
        # Island capsule: transparent on material / center-only like end4.
        island = read_bar_file("DynamicIsland.qml")
        self.assertIn('root.isMaterial || (GlobalStates.barCenterOnly && Config.options.bar.cornerStyle === 0) ? "transparent"', island)
        # Middle frame hugs the island (-4 / +8, full height).
        content = read_bar_file("BarContent.qml")
        self.assertIn("middleRow.implicitWidth - 4", content)
        self.assertIn("middleRow.implicitWidth + 8", content)
        # Island notification face: end4 anchors (icon 4/12 + fallback 0/4, text 14/2).
        notifs = read_bar_file("DiNotifs.qml")
        self.assertIn("di.isMaterial ? 14 : 2", notifs)
        self.assertIn("di.isMaterial ? 4 : 12", notifs)
        # Every island OSD channel runs at end4's 132 (keyboard included);
        # gamma is a registered intentional gap on Niri.
        self.assertIn("readonly property real osdWidth: 132", island)

    def test_b9_6_popup_tokens_match_end4(self):
        popup = read_bar_file("StyledPopup.qml")
        self.assertIn("colLayer1Base", popup)
        self.assertIn("Appearance.rounding.large + 5", popup)
        self.assertIn("readonly property real margin: 8", popup)
        self.assertIn("colLayer0Border", popup)
        # The zzz/angel/inir skin branches read tokens that do not exist on
        # Nyxuri's Appearance; the resolved end4 defaults are the only path.
        for name in ("SysTrayMenu.qml", "SysTrayMenuEntry.qml"):
            menu = read_bar_file(name)
            self.assertNotIn("zzzEverywhere", menu, name)
            self.assertNotIn("angelEverywhere", menu, name)
            self.assertNotIn("inirEverywhere", menu, name)
        self.assertIn("Appearance.rounding.windowRounding", read_bar_file("SysTrayMenu.qml"))
        # Tooltips keep end4's outer margins.
        with open(os.path.join(REPO_ROOT, "shell", "ui", "M3ToolTip.qml"), "r", encoding="utf-8") as f:
            tooltip = f.read()
        self.assertNotIn("horizontalMargin: 0", tooltip)
        self.assertNotIn("verticalMargin: 0", tooltip)
        # The style editor speaks end4's slider language and closes on outside click.
        style_popup = read_bar_file("BarGroupStylePopup.qml")
        self.assertIn("ConfigSlider {", style_popup)
        self.assertNotIn("PreferenceSlider {", style_popup)
        self.assertIn("bar-style-editor-catcher", style_popup)
        for name in ("ConfigSlider.qml", "StyledSlider.qml", "OptionalMaterialSymbol.qml",
                     "WorkspacesAlt.qml", "Colorizer.qml", "StateOverlay.qml",
                     "FadeLoader.qml", "StyledRectangle.qml", "ButtonMouseArea.qml",
                     "Box.qml", "Pill.qml", "Circle.qml", "StateLayer.qml",
                     "MaskMultiEffect.qml"):
            self.assertIn("Fork & Trim: end4-pC", read_bar_file(name), f"{name} fork header")

    def test_divisor_contracts(self):
        content = read_bar_file("Divisor.qml")
        self.assertIn("PersonalizationConfig.barDividerStyle", content)
        self.assertIn("isMaterial", content)
        self.assertIn("vertical", content)

    def test_component_loader_registrations(self):
        content = read_bar_file("BarContent.qml")
        self.assertIn('"divisor": "./Divisor.qml"', content)
        self.assertIn('"island": "./DynamicIsland.qml"', content)

    def test_dynamic_island_is_material_binding(self):
        content = read_bar_file("DynamicIsland.qml")
        self.assertIn("PersonalizationConfig.barIsMaterial", content)

    def test_personalization_config_bar_keys(self):
        content = read_services_file("PersonalizationConfig.qml")
        self.assertIn("barCornerStyles", content)
        self.assertIn("barCornerStyle", content)
        self.assertIn("barBorderlessModes", content)
        self.assertIn("barBorderless", content)
        self.assertIn("barDividerStyles", content)
        self.assertIn("barDividerStyle", content)
        self.assertIn("barGroupColorOptions", content)
        self.assertIn("barWidgetStyles", content)
        self.assertIn('"divisor"', content)
        self.assertIn("setBarCornerStyle", content)
        self.assertIn("setBarBorderless", content)
        self.assertIn("setBarDividerStyle", content)
        self.assertIn("setBarWidgetStyle", content)

    def test_bar_content_contracts(self):
        content = read_bar_file("BarContent.qml")
        self.assertIn("centerOnly", content)
        self.assertIn("barBackground", content)
        self.assertIn("centerPill", content)
        self.assertIn("leftMaterialPill", content)
        self.assertIn("centerMaterialPill", content)
        self.assertIn("rightMaterialPill", content)
        self.assertIn("BarGroup", content)

    def test_bar_windows_screen_corners_and_exclusive_zone(self):
        content = read_bar_file("Bar.qml")
        self.assertIn("roundDecorators", content)
        self.assertIn("shownExclusiveZone", content)
        # cornerStyle 4/5 reserve 4px in the window layer (end4 parity); the
        # formula moved to the shared BarGeometry helper in B9.5.
        self.assertIn("materialHug", content)
        self.assertIn("panelStyle", content)
        self.assertIn("BarGeometry.exclusiveZone", content)
        self.assertIn("? 4 : 0", read_commons_file("BarGeometry.js"))

    def test_bar_and_island_ipc_handlers(self):
        content = read_bar_file("Bar.qml")
        self.assertIn('target: "bar"', content)
        self.assertIn("function toggle(): string", content)
        self.assertIn("function open(): string", content)
        self.assertIn("function close(): string", content)
        self.assertIn('target: "island"', content)
        self.assertIn("function state(): string", content)
        # Recording is parked; the IPC face must not promise it.
        self.assertNotIn("stopRecording", content)


class VerticalAndMarginContractTest(unittest.TestCase):
    """B9.4/B9.5: one edge truth, a real vertical fork, shared margin math."""

    def test_config_exposes_the_edge_as_the_single_truth(self):
        config = read_services_file("Config.qml")
        self.assertIn("readonly property string edge", config)
        self.assertIn('PersonalizationConfig.barPosition === "bottom"', config)
        self.assertIn('PersonalizationConfig.barPosition === "left"', config)
        self.assertIn("edgeMargin", config)
        self.assertIn("sideMargin", config)

    def test_popups_stop_deriving_right_from_the_bottom_bool(self):
        popup = read_bar_file("StyledPopup.qml")
        self.assertIn("Config.options?.bar?.edge", popup)
        self.assertIn("root.barEdge === \"right\"", popup)
        self.assertNotIn('Config.options?.bar?.bottom ?? false) ? "right"', popup)
        style_popup = read_bar_file("BarGroupStylePopup.qml")
        self.assertIn('Config.options.bar.edge === "right"', style_popup)

    def test_vertical_content_is_the_end4_fork(self):
        content = read_bar_file("VerticalBarContent.qml")
        self.assertIn("Fork & Trim: end4-pC", content)
        self.assertIn("GPL-3", content)
        self.assertIn("readonly property bool vertical: true", content)
        self.assertIn("Appearance.sizes.verticalBarWidth", content)
        self.assertIn("laneTopHeight", content)
        self.assertIn("laneCenterY", content)
        # The island has no vertical shape yet (ROADMAP B9.4).
        self.assertIn('name !== "island"', content)
        # Only the active capsule branch instantiates widgets.
        self.assertIn("active: root.isMaterial", content)
        self.assertIn("active: !root.isMaterial", content)

    def test_vertical_thickness_and_outer_margins_are_real_settings(self):
        config = read_services_file("PersonalizationConfig.qml")
        for token in (
            "barVerticalThickness",
            "setBarVerticalThickness",
            "barEdgeMargin",
            "setBarEdgeMargin",
            "barSideMargin",
            "setBarSideMargin",
        ):
            self.assertIn(token, config, f"missing setting owner: {token}")
        appearance = read_commons_file("Appearance.qml")
        self.assertIn("verticalBarThickness", appearance)
        self.assertIn("baseVerticalBarWidth", appearance)

    def test_bar_window_branches_on_orientation(self):
        content = read_bar_file("Bar.qml")
        self.assertIn("contentLoader", content)
        self.assertIn("VerticalBarContent {}", content)
        self.assertIn("BarContent {}", content)
        self.assertIn("BarGeometry.margins", content)
        self.assertIn("BarGeometry.exclusiveZone", content)
        self.assertNotIn("barContent.centerOnly", content,
                         "the retired content id must not leak back")

    def test_orientation_switching_never_relies_on_cleared_anchors(self):
        """QML keeps an anchor when a binding yields `undefined`, so the content
        loader and the material pills must use explicit geometry."""
        bar = read_bar_file("Bar.qml")
        self.assertIn("contentOffsetX", bar)
        self.assertIn("not clear an anchor", bar)
        self.assertIn("width: barRoot.vertical ? Appearance.sizes.verticalBarWidth : parent.width", bar)
        content = read_bar_file("BarContent.qml")
        self.assertNotIn("anchors.left: root.isMaterialHug ? parent.left : undefined", content)
        self.assertNotIn("anchors.centerIn: root.isMaterialHug ? undefined : parent", content)
        self.assertNotIn("anchors.top: !Config.options.bar.bottom ? parent.top : undefined", content)

    def test_margin_geometry_is_pure_and_probeable(self):
        geometry = read_commons_file("BarGeometry.js")
        self.assertIn("function margins(", geometry)
        self.assertIn("function exclusiveZone(", geometry)
        # The window and the probe must bind the same implementation.
        probe = os.path.join(REPO_ROOT, "shell", "scripts", "dev", "probe-bar.qml")
        with open(probe, "r", encoding="utf-8") as handle:
            probe_source = handle.read()
        self.assertIn("BarGeometry.margins(", probe_source)
        self.assertIn("function margins(): string", probe_source)
        self.assertIn("function edge(value: string): string", probe_source)


class TrayContractTest(unittest.TestCase):
    """B9.1: the tray is a real pin/overflow surface, not the old stub."""

    def test_service_persists_pins_through_the_store(self):
        content = read_bar_file("TrayService.qml")
        self.assertIn("Fork & Trim: iNiR", content)
        self.assertIn("PersonalizationConfig.barTrayPinnedItems", content)
        self.assertIn("PersonalizationConfig.setBarTrayPinnedItems", content)
        # The stub returned an empty unpinned list and a no-op togglePin; both
        # are what kept the overflow arrow permanently hidden.
        self.assertNotIn("function togglePin(id) {\n    }", content)
        # Trimmed scope: no proxy supervisor, no app launch table.
        self.assertNotIn("Process {", content)
        self.assertNotIn("ShellExec", content)
        self.assertNotIn("ToplevelManager", content)
        self.assertNotIn("function smartToggle", content)

    def test_overflow_closes_on_outside_click(self):
        content = read_bar_file("SysTray.qml")
        self.assertIn("closeOnOutsideClick: true", content)
        self.assertIn("onRequestClose: root.closeOverflowMenu()", content)
        self.assertIn("root.trayOverflowOpen = false", content)

    def test_store_round_trips_the_tray_block(self):
        content = read_services_file("PersonalizationConfig.qml")
        for token in (
            "const tray = configSection(bar.tray)",
            "root.barTrayPinnedItems = root.normalizedTrayPinnedItems(tray.pinnedItems)",
            "root.barTrayFilterPassive = typeof tray.filterPassive",
            '"pinnedItems": root.barTrayPinnedItems.slice()',
            '"filterPassive": root.barTrayFilterPassive',
            '"invertPinnedItems": root.barTrayInvertPinnedItems',
            '"showItemId": root.barTrayShowItemId',
            '"monochromeIcons": root.barTrayMonochromeIcons',
        ):
            self.assertIn(token, content, f"tray persistence token missing: {token}")

    def test_tint_reads_a_real_config_property(self):
        item = read_bar_file("SysTrayItem.qml")
        self.assertIn("barTrayMonochromeIcons", read_services_file("Config.qml"))
        self.assertIn("Config.options?.bar?.m3?.tray?.monochromeIcons", item)

    def test_settings_page_exposes_the_tray_controls(self):
        page = read_bar_file("GeneralBarPage.qml")
        for prop in (
            "barTrayMonochromeIcons",
            "barTrayFilterPassive",
            "barTrayShowItemId",
            "barTrayInvertPinnedItems",
        ):
            self.assertIn(prop, page, f"tray setting has no consumer row: {prop}")
        self.assertIn('anchorId: "bar.section.tray"', page)
        with open(os.path.join(BAR_DIR, "manifest.toml"), "r", encoding="utf-8") as f:
            manifest = f.read()
        self.assertIn('id = "bar.section.tray"', manifest)


if __name__ == "__main__":
    unittest.main()

"""B4 bar reskin and cornerStyle contract tests.

Verifies:
  - Promoted end4 baseline files exist in shell/plugins/bar/ and carry GPL-3 Fork & Trim headers
  - No bare import qs statements in the promoted components
  - BarGroup.qml has trimmed dead paths (BarGroupStylePopup, widgetStyles) and manages child backgroundVisible
  - Divisor.qml supports rect/dot/space styles and connects to PersonalizationConfig
  - BarWidgetFiles.js registers "separator" (Divisor.qml), "island" and "spacer" (D4a)
  - DynamicIsland.qml wires isMaterial to PersonalizationConfig.barCornerStyle
  - PersonalizationConfig defines barCornerStyles, barBorderlessModes, barDividerStyles, whitelist via BarWidgetDefaults.IDS
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
        self.assertIn("PersonalizationConfig.setBarEntryStyle", content, "widget styles must persist via the entry (D4c uid protocol)")
        # D4f: style resolution flows through BarStyle.js from the injected per-bar axes.
        self.assertIn("readonly property var styleContext: BarStyle.resolve(root.barAxes)", content)
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
        # D4a/D4e: lanes consume the entry objects off the host's OWN bar
        # config (multi-bar: the settings-facing views are editor-only).
        self.assertIn("filterLayout(root.barConfig ? root.barConfig.lanes.left : [])", content)
        self.assertIn("filterLayout(root.barConfig ? root.barConfig.lanes.middle : [])", content)
        self.assertIn("filterLayout(root.barConfig ? root.barConfig.lanes.right : [])", content)
        # B9.3: the island is a layout member, not a second config gate.
        self.assertNotIn("PersonalizationConfig.islandEnabled", content)
        self.assertNotIn('filtered.filter(name => name !== "island")', content)
        # Only the active style branch instantiates widgets.
        self.assertIn("active: root.isMaterial", content)
        self.assertIn("active: !root.isMaterial", content)

    def test_material_helper_is_the_single_source(self):
        # D4f: BarStyle.js is the single pure style resolver for plugins/bar/;
        # per-bar widgets consume BarStyle.isTinted(root.barAxes), never global enums.
        style_js = read_bar_file("BarStyle.js")
        self.assertIn("function isTinted(axes)", style_js)
        for name in ("Media.qml", "SysTray.qml", "UtilButtons.qml",
                     "Divisor.qml", "Visualizer.qml", "BatteryIndicator.qml"):
            content = read_bar_file(name)
            self.assertIn("BarStyle.isTinted(root.barAxes)", content, name)
            self.assertNotIn("Config.options.bar.cornerStyle", content, f"{name} reads global cornerStyle")

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
        self.assertIn('di.option("showAvatar")', content)
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
        # D4b: the divider axes are separator entry overrides.
        self.assertIn('BarWidgetDefaults.option("separator", root.widgetEntry, "style")', content)
        self.assertIn('BarWidgetDefaults.option("separator", root.widgetEntry, "spacing")', content)
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
        # D4b: the budget is the entry's `shown` axis.
        self.assertIn('BarWidgetDefaults.option("workspaces", root.widgetEntry, "shown")', content)
        self.assertIn("root.group * root.shownBudget + index + 1", content)
        self.assertIn("existingMaxIdx", content)
        self.assertIn("Math.max(1, Math.min(root.shownBudget, root.existingMaxIdx - root.group * root.shownBudget))", content)
        self.assertIn("(root.activeNumber - 1) % root.shownBudget", content)
        self.assertIn("fakeWorkspace", content)
        # end4 metrics: tinted material slots are wider (30), default 26.
        self.assertIn("BarStyle.isTinted(root.barAxes) ? 30 : 26", content)
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
        # Settings: the slot budget and skins are entry axes now (D4b) —
        # the defaults table carries them and WorkspacesAlt reads the host
        # entry instead of the store.
        defaults = read_services_file("BarWidgetDefaults.js")
        self.assertIn('shown: 10', defaults)
        self.assertIn('style: "default"', defaults)
        self.assertIn('root.host.style', read_bar_file("WorkspacesAlt.qml"))
        options = read_bar_file("options/WorkspacesOptions.qml")
        self.assertIn('root.page.set("shown"', options)
        self.assertIn('root.page.set("style"', options)

    def test_b9_6_geometry_matches_end4(self):
        # PowerButton: end4 material size 32 (was 28).
        self.assertIn("barPowerButtonSize: 32", read_commons_file("Appearance.qml"))
        # ActiveWindow: no right-margin squeeze, no invented fallback icon.
        active = read_bar_file("ActiveWindow.qml")
        self.assertNotIn("desktop_windows", active)
        self.assertNotIn("anchors.rightMargin: 6", active)
        # Island capsule: transparent on lane pill / edge-flush center-only backplate.
        island = read_bar_file("DynamicIsland.qml")
        self.assertIn('root.styleContext.islandTransparent ? "transparent"', island)
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
                     "WorkspacesAlt.qml", "Colorizer.qml",
                     "FadeLoader.qml", "StyledRectangle.qml", "ButtonMouseArea.qml",
                     "Box.qml", "Pill.qml", "Circle.qml",
                     "MaskMultiEffect.qml"):
            self.assertIn("Fork & Trim: end4-pC", read_bar_file(name), f"{name} fork header")
        # D0: the end4 enum StateLayer and its StateOverlay wrapper were folded
        # into ui/StateLayer.qml (M3 contract carrier); neither may come back.
        self.assertFalse(os.path.exists(os.path.join(BAR_DIR, "StateLayer.qml")), "end4 enum StateLayer must stay retired")
        self.assertFalse(os.path.exists(os.path.join(BAR_DIR, "StateOverlay.qml")), "StateOverlay must stay retired")

    def test_divisor_contracts(self):
        content = read_bar_file("Divisor.qml")
        # D4b: the divider axes are separator entry overrides.
        self.assertIn('BarWidgetDefaults.option("separator", root.widgetEntry, "style")', content)
        self.assertIn('BarWidgetDefaults.option("separator", root.widgetEntry, "spacing")', content)
        self.assertIn("isMaterial", content)
        self.assertIn("vertical", content)

    def test_component_loader_registrations(self):
        # D4a: the id->file registry lives in BarWidgetFiles.js (the inline
        # maps in the lane host retired); unknown ids fail
        # loud instead of falling back to a capitalized file name.
        content = read_bar_file("BarWidgetFiles.js")
        self.assertIn('separator: "Divisor.qml"', content)
        self.assertIn('island: "DynamicIsland.qml"', content)
        self.assertIn('spacer: "Spacer.qml"', content)
        bar_content = read_bar_file("BarContent.qml")
        self.assertIn("BarWidgetFiles.fileFor", bar_content)
        self.assertNotIn("charAt(0).toUpperCase()", bar_content, "capitalized-name fallback must stay retired")

    def test_dynamic_island_is_material_binding(self):
        content = read_bar_file("DynamicIsland.qml")
        self.assertIn("readonly property bool isMaterial: root.styleContext.tint", content)

    def test_personalization_config_bar_keys(self):
        content = read_services_file("PersonalizationConfig.qml")
        self.assertIn("barWidgetStyleOptions", content)
        self.assertIn("barWidgetStyle", content)
        self.assertIn("barCapsuleRadiusOptions", content)
        self.assertIn("barCapsuleRadius", content)
        self.assertIn("barBackplate", content)
        self.assertIn("barLanePill", content)
        self.assertIn("barTint", content)
        self.assertIn("barGroupColorOptions", content)
        self.assertIn("BarWidgetDefaults.IDS", content)
        self.assertIn("setBarWidgetStyle", content)
        self.assertIn("setBarCapsuleRadius", content)
        self.assertIn("applyBarStylePreset", content)
        self.assertNotIn("barDividerStyles", content)
        self.assertNotIn("setBarDividerStyle", content)
        self.assertNotIn("setBarWorkspaceStyle", content)
        self.assertNotIn("barWorkspaceStyles", content)

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
        # D4f / D-8: boost comes from geometric derivation (BarDefaults.styleBoost),
        # never cornerStyle 4/5 enum branches.
        self.assertIn("materialHug", content)
        self.assertIn("panelStyle", content)
        self.assertIn("BarGeometry.exclusiveZone", content)
        self.assertIn("boostExtra || 0", read_commons_file("BarGeometry.js"))

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
        # D4g 批四: the whole selected-bar bridge view set (`edge`/
        # `bottom`/`vertical`) retired — orientation is a per-entry fact;
        # avoidance reads the ScreenBarLayout projection, popups and
        # widgets read their injected axes.
        self.assertNotIn("readonly property string edge", config)
        self.assertNotIn("readonly property bool bottom", config)
        self.assertNotIn("readonly property bool vertical", config)
        self.assertIn("edgeMargin", config)
        self.assertIn("sideMargin", config)

    def test_popups_stop_deriving_right_from_the_bottom_bool(self):
        popup = read_bar_file("StyledPopup.qml")
        self.assertIn("root.barAxes.position", popup)
        self.assertIn("root.barEdge === \"right\"", popup)
        self.assertNotIn('Config.options?.bar?.bottom ?? false) ? "right"', popup)
        style_popup = read_bar_file("BarGroupStylePopup.qml")
        self.assertIn('root.barAxes.position === "right"', style_popup)

    def test_vertical_content_is_the_end4_fork(self):
        # D4g: the rail is the same host file — the end4 fork marker and the
        # rail surfaces live in BarContent behind the axis branches.
        content = read_bar_file("BarContent.qml")
        self.assertIn("Fork & Trim: end4-pC", content)
        self.assertIn("GPL-3", content)
        self.assertIn("readonly property AxisContext axis: AxisContext {", content)
        self.assertIn("readonly property bool vertical: root.axis.isVertical", content)
        self.assertIn("PersonalizationConfig.resolvedVerticalBarWidth(root.axes)", content)
        self.assertIn("laneTopHeight", content)
        self.assertIn("laneCenterY", content)
        # 批三: the island mounts on the rail as the compact face — the
        # old rail-only island drop is retired (end4 behaviour gone).
        self.assertNotIn('entry.widgetId !== "island"', content)
        self.assertNotIn("if (root.vertical)", content)
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
        # D4g: one host — a single BarContent mount, orientation via axes.
        self.assertIn("sourceComponent: barContent", content)
        self.assertIn("BarContent {", content)
        self.assertNotIn("VerticalBarContent", content)
        # D4e: the content instance receives its own bar entry.
        self.assertIn("barConfig: barRoot.barConfig", content)
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
        self.assertIn("width: barRoot.vertical ? barRoot.thickness : parent.width", bar)
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
            "root.barTrayInvertPinnedItems = typeof tray.invertPinnedItems",
            '"pinnedItems": root.barTrayPinnedItems.slice()',
            '"invertPinnedItems": root.barTrayInvertPinnedItems',
        ):
            self.assertIn(token, content, f"tray persistence token missing: {token}")
        # D4b: the per-instance tray axes (tint/hidePassive/showItemId) ride
        # the lane entries; the [bar.tray] block keeps shared state only.
        for gone in ("filterPassive", "showItemId", "monochromeIcons"):
            self.assertNotIn(f'"{gone}"', content,
                             f"tray {gone} must not persist as a flat key anymore")

    def test_tint_reads_a_real_config_property(self):
        # D4b: tint is a per-instance entry axis injected by the SysTray
        # delegates (no bridge read).
        item = read_bar_file("SysTrayItem.qml")
        self.assertIn("property bool tintIcon: true", item)
        systray = read_bar_file("SysTray.qml")
        self.assertIn('BarWidgetDefaults.option("tray", root.widgetEntry, "tintIcons")', systray)
        self.assertIn("tintIcon: root.tintIcons", systray)

    def test_settings_page_exposes_the_tray_controls(self):
        # D4b: the tray rows moved to the per-instance options page.
        page = read_bar_file("options/TrayOptions.qml")
        for token in (
            'root.page.value("tintIcons")',
            'root.page.value("hidePassive")',
            'root.page.value("showItemId")',
            "PersonalizationConfig.barTrayInvertPinnedItems",
        ):
            self.assertIn(token, page, f"tray setting has no consumer row: {token}")
        self.assertIn('anchorId: "bar.modules.tray"', page)
        with open(os.path.join(BAR_DIR, "manifest.toml"), "r", encoding="utf-8") as f:
            manifest = f.read()
        self.assertIn('id = "bar.modules.tray"', manifest)


class BarB9_7SettingsSweepTest(unittest.TestCase):
    """B9.7 设置清账：八个死键逐一接消费者或处决，可见设置必有唯一 owner。"""

    def test_bar_overlay_is_executed(self):
        config = read_services_file("PersonalizationConfig.qml")
        self.assertNotIn("barOverlay", config)
        self.assertNotIn('"overlay"', config)
        page = read_bar_file("GeneralBarPage.qml")
        self.assertNotIn("barOverlay", page)
        self.assertNotIn('"Floating"', page)
        catalog_path = os.path.join(REPO_ROOT, "shell", "plugins", "settings", "dashwindow", "SettingsControlCatalog.qml")
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = f.read()
        self.assertNotIn("bar:Overlay", catalog)

    def test_recorder_domain_is_executed(self):
        # B-4 补完：Record 按钮、恒 false 孤儿桩与指向不存在脚本的 action。
        self.assertFalse(os.path.isfile(os.path.join(SERVICES_DIR, "RecorderStatus.qml")),
                         "RecorderStatus stub must not come back")
        self.assertNotIn("RecorderStatus", read_bar_file("UtilButtons.qml"))
        self.assertNotIn("showScreenRecord", read_bar_file("UtilButtons.qml"))
        self.assertNotIn("showScreenRecord", read_services_file("Config.qml"))
        actions = read_services_file("GlobalActions.qml")
        self.assertNotIn("screen-record", actions)
        self.assertNotIn("recordScriptPath", actions)

    def test_utilbuttons_is_addable_again(self):
        config = read_services_file("PersonalizationConfig.qml")
        # D4a: the whitelist is BarWidgetDefaults.IDS; utilButtons stays in
        # it and the catalog carries its option entry.
        self.assertIn("BarWidgetDefaults.IDS", config,
                      "the widget whitelist must derive from the defaults registry")
        defaults = read_services_file("BarWidgetDefaults.js")
        self.assertIn('"utilButtons"', defaults)
        with open(os.path.join(REPO_ROOT, "shell", "ui", "BarWidgetCatalog.qml"), "r", encoding="utf-8") as f:
            catalog = f.read()
        self.assertIn('id: "utilButtons"', catalog)

    def test_settled_keys_live_in_the_store(self):
        # D4b: the per-widget settled axes moved to the entry defaults
        # table; the store keeps the bar-frame keys. D4c: those frame keys
        # are derived views off the configs entry (axes), written only
        # through the named setters.
        config = read_services_file("PersonalizationConfig.qml")
        for prop in (
            "readonly property bool barAutoHide",
            "readonly property var barScreenList",
            "readonly property bool barBackplate",
        ):
            self.assertIn(prop, config, f"settled key missing from the store: {prop}")
        # D4c: persistence rides the configs entry (sparseBarConfigs diff
        # against BarDefaults), not flat [bar] keys.
        self.assertIn("Object.keys(BarDefaults.DEFAULTS)", config)
        defaults = read_services_file("BarWidgetDefaults.js")
        for axis in (
            "screenSnip: true",
            "keyboardToggle: false",
            "cpu: true",
            "cpuTemp: false",
            "ram: true",
            "disk: false",
            "swap: false",
            "iconStyle: \"outline\"",
            "showValue: false",
            "numberStyle: \"normal\"",
        ):
            self.assertIn(axis, defaults, f"settled axis missing from the defaults table: {axis}")
        self.assertIn("function normalizedScreenList", config,
                      "settled persistence token missing: function normalizedScreenList")
        # D4c/D4f: the frame keys persist through the configs entry axes —
        # the explicit map lives in ConfigMigrations.
        migrations = read_services_file("ConfigMigrations.js")
        for token in ('var MIGRATED_BAR_GLOBALS', "autoHide: \"autoHide\"",
                      "screenList: \"screenList\"", "var MIGRATED_STYLE_KEYS"):
            self.assertIn(token, migrations, f"settled persistence token missing: {token}")

    def test_config_bridge_reads_the_store(self):
        bridge = read_services_file("Config.qml")
        self.assertNotIn("barShowBackground ?? true", bridge,
                         "the bridge must stop defaulting a nonexistent property")
        self.assertNotIn("readonly property var screenList: []", bridge)
        self.assertIn("enable: PersonalizationConfig.barAutoHide", bridge)
        self.assertIn("screenList: PersonalizationConfig.barScreenList", bridge)
        # D4b: the migrated per-widget axes left the bridge — widgets read
        # them through the entry chain (option()) instead.
        for prop in ("barShowScreenSnip", "barShowColorPicker", "barShowKeyboardToggle",
                     "barShowMicToggle", "barShowWallpaperToggle", "barShowDarkModeToggle",
                     "barShowPerformanceProfile", "barShowCpu", "barShowCpuTemp",
                     "barShowRam", "barShowDisk", "barShowSwap", "barResourceStyle",
                     "barResourceShowValue", "barWorkspaceNumberMap", "barTrayMonochromeIcons"):
            self.assertNotIn(f"PersonalizationConfig.{prop}", bridge,
                             f"{prop} still bridges a retired flat key")

    def test_settings_page_rows_and_gates(self):
        appearance = read_bar_file("BarAppearanceSection.qml")
        modules = read_bar_file("BarModulesSection.qml")
        # D4f: atomic backplate toggle + autohide.
        self.assertIn('I18n.tr("Bar backplate")', appearance)
        self.assertIn('I18n.tr("Autohide")', appearance)
        # D4b: the divider rows and the Numbers style gate moved to the
        # per-instance options pages; the appearance tab keeps frame axes.
        self.assertNotIn("barDividerStyle", appearance)
        # Screens: end4 monitor filter with the all-collapse rule.
        self.assertIn("function toggleBarScreen", appearance)
        self.assertIn("list.length === allNames.length ? [] : list", appearance)
        self.assertIn('I18n.tr("All screens")', appearance)
        self.assertNotIn("barScreenList = []", appearance.replace('setValue("barScreenList", [])', ""),
                         "writes go through setValue persistence, not raw assignment")
        # D4b: the widget-scoped groups retired from the modules tab — the
        # isUsed gate retired with them (an entry's options exist exactly
        # while the entry exists).
        self.assertNotIn("function layoutUses", modules)
        self.assertNotIn("PersonalizationConfig.barShowAppIcons", modules)
        self.assertIn("signal widgetEditorRequested(string entryUid)", modules,
                      "the chip gear routes to the per-instance editor")

    def test_power_button_toggles_session_via_action_gateway(self):
        content = read_bar_file("PowerButton.qml")
        self.assertIn("ActionGateway.requestSessionToggle(root.QsWindow.window?.screen)", content)
        self.assertNotIn("GlobalStates.sessionOpen", content)


if __name__ == "__main__":
    unittest.main()

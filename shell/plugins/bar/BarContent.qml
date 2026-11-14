// Fork & Trim: end4-pC modules/ii/bar/BarContent.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri:
//   - Dynamic-island satellite loaders removed: the island is a middle-lane
//     widget (componentId "island"), not a reserved gap (ROADMAP B-3).
//   - hyprland.general.gapsOut -> bar.m3.gapsOut; followFrameColor dropped.
//   - left/right pill corner decorators stay in Bar.qml (window layer), so the
//     copies inside the upstream file are trimmed here.
//   - lane widths collapse to 0 when the lane has no widgets (no phantom host).
//   - background spectrum (CavaProcess/SurfaceSpectrum) retired with B8.1.

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.SystemTray
import qs.services
import qs.commons
import qs.commons.i18n
import qs.ui

Item {
    id: root
    implicitHeight: Appearance.sizes.barHeight
    width: parent.width
    readonly property real barPadding: 0
    readonly property bool isMaterial: PersonalizationConfig.barIsMaterial
    readonly property bool isMaterialHug: PersonalizationConfig.barIsMaterialHug
    readonly property bool isPanel: PersonalizationConfig.barIsPanel

    readonly property color materialPillBgColor: Appearance.colors.colLayer0
    readonly property real centerPillX: centerPill.x
    readonly property real centerPillWidth: centerPill.width
    // Probe surface (scripts/dev/probe-bar.sh): the optical centre lane and its
    // evaluated geometry, so a runtime probe can catch NaN / left-edge collapse
    // without duplicating the layout math.
    readonly property real laneCenterX: absoluteCenter.x + contentContainer.x
    readonly property real laneCenterWidth: absoluteCenter.width
    readonly property bool trayHasItems: SystemTray.items.values.length > 0
    readonly property bool batteryAvailable: Battery.available

    function filterLayout(layout) {
        let filtered = Array.from(layout ?? []);
        // B8.4: islandEnabled is the island's component gate. It has to hide
        // the widget, not just release the popup slot.
        if (!PersonalizationConfig.islandEnabled)
            filtered = filtered.filter(name => name !== "island");
        if (!root.trayHasItems)
            filtered = filtered.filter(name => name !== "sysTray" && name !== "tray");
        if (!root.batteryAvailable)
            filtered = filtered.filter(name => name !== "battery" && name !== "batteryIndicator");
        return filtered;
    }

    readonly property var effectiveLeftLayout: filterLayout(Config.options.bar.m3.layouts.leftLayout)
    readonly property var effectiveMiddleLayout: filterLayout(Config.options.bar.m3.layouts.middleLayout)
    readonly property var effectiveRightLayout: filterLayout(Config.options.bar.m3.layouts.rightLayout)
    readonly property bool leftLaneFilled: root.effectiveLeftLayout.length > 0
    readonly property bool centerLaneFilled: root.effectiveMiddleLayout.length > 0
    readonly property bool rightLaneFilled: root.effectiveRightLayout.length > 0

    function getWidgetUrl(name) {
        if (!name)
            return "";
        const map = {
            "island": "./DynamicIsland.qml",
            "clock": "./ClockWidget.qml",
            "clockWidget": "./ClockWidget.qml",
            "tray": "./SysTray.qml",
            "sysTray": "./SysTray.qml",
            "systemMonitor": "./Resources.qml",
            "resources": "./Resources.qml",
            "weather": "./WeatherBar.qml",
            "battery": "./BatteryIndicator.qml",
            "batteryIndicator": "./BatteryIndicator.qml",
            "systemIcons": "./SystemIcons.qml",
            "quickSettings": "./UtilButtons.qml",
            "utilButtons": "./UtilButtons.qml",
            "launcherButton": "./LauncherButton.qml",
            "powerButton": "./PowerButton.qml",
            "divisor": "./Divisor.qml",
            "divider": "./Divisor.qml",
            "workspaces": "./Workspaces.qml",
            "activeWindow": "./ActiveWindow.qml",
            "media": "./Media.qml"
        };
        if (map[name])
            return Qt.resolvedUrl(map[name]);
        let formattedName = name.charAt(0).toUpperCase() + name.slice(1);
        return Qt.resolvedUrl("./" + formattedName + ".qml");
    }

    function shouldPaintMaterialPill(name) {
        if (!root.isMaterial)
            return false;
        // end4 baseline + "island": the island paints its own capsule
        // (paintBackground: false) and must not eat a group tint.
        const blacklist = ["workspaces", "divisor", "powerButton", "docktoPanel", "leftSidebarButton", "rightSidebarButton", "activeWindow", "dynamicIsland", "island", "avatar"];
        return !blacklist.includes(name);
    }

    function getMaterialPillColor(name) {
        return M3Palette.pillContainer(name);
    }

    // Edge scroll (iNiR behaviour kept through the B8.1 re-fork): the bare bar
    // on either side of the middle lane steps brightness / volume. Widgets sit
    // above these areas, so a scroll over a widget still belongs to the widget.
    readonly property string leftAction: Config.options?.bar?.leftScrollAction ?? "brightness"
    readonly property string rightAction: Config.options?.bar?.rightScrollAction ?? "volume"

    function performScrollAction(action: string, isUp: bool): void {
        if (action === "brightness") {
            const monitor = BrightnessService.getMonitorForScreen(root.screen);
            const current = monitor ? monitor.brightness : BrightnessService.brightnessValue;
            BrightnessService.setBrightnessForScreen(root.screen, current + (isUp ? 0.05 : -0.05), false);
        } else if (action === "volume") {
            VolumeService.setSinkVolume(VolumeService.sinkVolume + (isUp ? 0.05 : -0.05));
        } else if (action === "workspace") {
            let up = isUp;
            if (Config.options?.bar?.workspaces?.invertScroll ?? false)
                up = !up;

            if (up)
                CompositorDriver.focusWorkspaceUp();
            else
                CompositorDriver.focusWorkspaceDown();
        }
    }

    function closeOSD(action: string): void {
        if (GlobalStates.osdKind !== "")
            GlobalStates.osdKind = "";
    }

    function getScrollIcon(action: string): string {
        if (action === "brightness")
            return "light_mode";
        if (action === "volume")
            return "volume_up";
        if (action === "workspace")
            return "workspaces";
        return "";
    }

    function getScrollTooltip(action: string): string {
        if (action === "brightness")
            return I18n.tr("Scroll to change brightness");
        if (action === "volume")
            return I18n.tr("Scroll to change volume");
        if (action === "workspace")
            return I18n.tr("Scroll to switch workspaces");
        return "";
    }

    property var screen: root.QsWindow.window?.screen

    Rectangle {
        id: barBackground
        anchors.fill: parent
        anchors.margins: Config.options.bar.cornerStyle === 1 ? Config.options.bar.m3.gapsOut : 0
        color: (!centerOnly && Config.options.bar.m3.showBackground && Config.options.bar.cornerStyle !== 2 && !root.isMaterial) ? Appearance.colors.colLayer0 : "transparent"
        radius: Config.options.bar.cornerStyle === 1 ? Appearance.rounding.windowRounding : 0
        border.width: (!centerOnly && Config.options.bar.cornerStyle === 1) ? 1 : 0
        border.color: Config.options.bar.cornerStyle === 1 && !Config.options.bar.m3.showBackground ? "transparent" : ColorUtils.transparentize(Appearance.colors.colLayer0Border, 0.8)
    }

    // center-only
    readonly property bool centerOnly: !root.leftLaneFilled && !root.rightLaneFilled

    Binding {
        target: GlobalStates
        property: "barCenterOnly"
        value: root.centerOnly
        restoreMode: Binding.RestoreBinding
    }

    Rectangle {
        id: centerPill
        visible: root.centerOnly && Config.options.bar.m3.showBackground && Config.options.bar.cornerStyle !== 2
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.centerLaneFilled ? middleRow.implicitWidth + 10 : 0
        height: parent.height - (Config.options.bar.cornerStyle === 1 ? Config.options.bar.m3.gapsOut * 2 : 0)
        color: root.isMaterial ? "transparent" : Appearance.colors.colLayer0
        radius: Config.options.bar.cornerStyle === 1 || root.isMaterial ? Appearance.rounding.windowRounding : 0
        border.width: Config.options.bar.cornerStyle === 1 ? 1 : 0
        border.color: Appearance.colors.colLayer0Border

        bottomLeftRadius: Config.options.bar.cornerStyle === 0 && !Config.options.bar.bottom ? Appearance.rounding.screenRounding : radius
        bottomRightRadius: Config.options.bar.cornerStyle === 0 && !Config.options.bar.bottom ? Appearance.rounding.screenRounding : radius
        topLeftRadius: Config.options.bar.cornerStyle === 0 && Config.options.bar.bottom ? Appearance.rounding.screenRounding : radius
        topRightRadius: Config.options.bar.cornerStyle === 0 && Config.options.bar.bottom ? Appearance.rounding.screenRounding : radius
    }

    Item {
        id: contentContainer
        anchors.fill: barBackground
        anchors.margins: root.barPadding

        // Declared before the lanes so a widget always wins the click; only the
        // bare bar around them feeds these.
        FocusedScrollMouseArea {
            id: barLeftScrollArea
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            width: Math.max(0, absoluteCenter.x)

            onScrollDown: root.performScrollAction(root.leftAction, false)
            onScrollUp: root.performScrollAction(root.leftAction, true)
            onMovedAway: root.closeOSD(root.leftAction)

            ScrollHint {
                reveal: barLeftScrollArea.hovered && (Config.options?.bar?.showScrollHints ?? true) && root.leftAction !== "none"
                icon: root.getScrollIcon(root.leftAction)
                tooltipText: root.getScrollTooltip(root.leftAction)
                side: "left"
                anchors.right: parent.right
                anchors.rightMargin: Appearance.sizes.spacingLarge
                anchors.verticalCenter: parent.verticalCenter
                z: 1
            }
        }

        FocusedScrollMouseArea {
            id: barRightScrollArea
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            width: Math.max(0, parent.width - (absoluteCenter.x + absoluteCenter.width))

            onScrollDown: root.performScrollAction(root.rightAction, false)
            onScrollUp: root.performScrollAction(root.rightAction, true)
            onMovedAway: root.closeOSD(root.rightAction)

            ScrollHint {
                reveal: barRightScrollArea.hovered && (Config.options?.bar?.showScrollHints ?? true) && root.rightAction !== "none"
                icon: root.getScrollIcon(root.rightAction)
                tooltipText: root.getScrollTooltip(root.rightAction)
                side: "right"
                anchors.left: parent.left
                anchors.leftMargin: Appearance.sizes.spacingLarge
                anchors.verticalCenter: parent.verticalCenter
                z: 1
            }
        }

        // Left
        Item {
            anchors.left: parent.left
            anchors.leftMargin: root.laneMargin
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: !root.leftLaneFilled ? 0 : root.isMaterial ? (leftMaterialPill.width + (root.isMaterialHug ? leftRightOutwardCorner.implicitSize : 0)) : leftRow.implicitWidth

            // Material pill wrapper
            Rectangle {
                id: leftMaterialPill
                visible: root.isMaterial && root.leftLaneFilled
                anchors.left: root.isMaterialHug ? parent.left : undefined
                anchors.top: (root.isMaterialHug && !Config.options.bar.bottom) ? parent.top : undefined
                anchors.bottom: (root.isMaterialHug && Config.options.bar.bottom) ? parent.bottom : undefined
                anchors.centerIn: root.isMaterialHug ? undefined : parent
                width: leftMaterialRow.implicitWidth + (root.isMaterialHug ? 16 : 10)
                height: root.isMaterialHug ? parent.height : leftMaterialRow.implicitHeight
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topLeftRadius: root.isMaterialHug ? 0 : radius
                bottomLeftRadius: root.isMaterialHug ? 0 : radius
                topRightRadius: (root.isMaterialHug && Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && !Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)

                RowLayout {
                    id: leftMaterialRow
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        model: root.effectiveLeftLayout
                        delegate: leftMaterialGroupDelegate
                    }

                    Component {
                        id: leftMaterialGroupDelegate
                        BarGroup {
                            Layout.fillHeight: true
                            currentIndex: index
                            widgetName: modelData
                            totalCount: root.effectiveLeftLayout.length
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData)
                            bgColor: root.getMaterialPillColor(modelData)
                            Loader {
                                Layout.fillHeight: true
                                // The hidden branch keeps its (empty) groups so
                                // RowLayout implicit sizes stay live, but must
                                // not instantiate widgets: a second island stole
                                // islandHost and doubled service consumers.
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData)
                            }
                        }
                    }
                }
            }

            RoundCorner {
                id: leftRightOutwardCorner
                visible: root.isMaterialHug && root.leftLaneFilled
                anchors.left: leftMaterialPill.right
                anchors.top: !Config.options.bar.bottom ? parent.top : undefined
                anchors.bottom: Config.options.bar.bottom ? parent.bottom : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !Config.options.bar.bottom ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.BottomLeft
            }

            // Non-material layout
            RowLayout {
                id: leftRow
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.rowSpacing

                Repeater {
                    model: root.effectiveLeftLayout
                    delegate: leftBarGroupDelegate
                }

                Component {
                    id: leftBarGroupDelegate
                    BarGroup {
                        Layout.fillHeight: true
                        currentIndex: index
                        widgetName: modelData
                        totalCount: root.effectiveLeftLayout.length
                        Loader {
                            Layout.fillHeight: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData)
                        }
                    }
                }
            }
        }

        // Center
        Item {
            id: absoluteCenter
            // Explicit x instead of anchors.centerIn: the lane width is fed by
            // dynamically loaded widget implicit sizes, and anchors did not
            // re-centre after the idle island narrowed (startup 164 -> 154).
            x: (parent.width - width) / 2
            width: !root.centerLaneFilled ? 0 : root.isMaterial ? (centerMaterialPill.width + (root.isMaterialHug ? (centerLeftOutwardCorner.implicitSize + centerRightOutwardCorner.implicitSize) : 0)) : middleRow.implicitWidth
            height: parent.height

            RoundCorner {
                id: centerLeftOutwardCorner
                visible: root.isMaterialHug && root.centerLaneFilled
                anchors.right: centerMaterialPill.left
                anchors.top: !Config.options.bar.bottom ? parent.top : undefined
                anchors.bottom: Config.options.bar.bottom ? parent.bottom : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !Config.options.bar.bottom ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.BottomRight
            }

            // Material pill wrapper
            Rectangle {
                id: centerMaterialPill
                visible: root.isMaterial && root.centerLaneFilled
                anchors.centerIn: parent
                width: centerMaterialRow.implicitWidth + (root.isMaterialHug ? 16 : 10)
                height: root.isMaterialHug ? parent.height : centerMaterialRow.implicitHeight
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topLeftRadius: (root.isMaterialHug && Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                topRightRadius: (root.isMaterialHug && Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                bottomLeftRadius: (root.isMaterialHug && !Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && !Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)

                RowLayout {
                    id: centerMaterialRow
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        model: root.effectiveMiddleLayout
                        delegate: middleMaterialGroupDelegate
                    }

                    Component {
                        id: middleMaterialGroupDelegate
                        BarGroup {
                            Layout.fillHeight: true
                            currentIndex: index
                            widgetName: modelData
                            paintBackground: modelData !== "island"
                            totalCount: root.effectiveMiddleLayout.length
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData)
                            bgColor: root.getMaterialPillColor(modelData)
                            Loader {
                                Layout.fillHeight: true
                                // The hidden branch keeps its (empty) groups so
                                // RowLayout implicit sizes stay live, but must
                                // not instantiate widgets: a second island stole
                                // islandHost and doubled service consumers.
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData)
                            }
                        }
                    }
                }
            }

            RoundCorner {
                id: centerRightOutwardCorner
                visible: root.isMaterialHug && root.centerLaneFilled
                anchors.left: centerMaterialPill.right
                anchors.top: !Config.options.bar.bottom ? parent.top : undefined
                anchors.bottom: Config.options.bar.bottom ? parent.bottom : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !Config.options.bar.bottom ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.BottomLeft
            }

            // Non-material layout
            RowLayout {
                id: middleRow
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.rowSpacing

                Repeater {
                    model: root.effectiveMiddleLayout
                    delegate: middleBarGroupDelegate
                }

                Component {
                    id: middleBarGroupDelegate
                    BarGroup {
                        Layout.fillHeight: true
                        currentIndex: index
                        widgetName: modelData
                        paintBackground: modelData !== "island"
                        totalCount: root.effectiveMiddleLayout.length
                        Loader {
                            Layout.fillHeight: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData)
                        }
                    }
                }
            }
        }

        // Right
        Item {
            anchors.right: parent.right
            anchors.rightMargin: root.laneMargin
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: !root.rightLaneFilled ? 0 : root.isMaterial ? (rightMaterialPill.width + (root.isMaterialHug ? rightLeftOutwardCorner.implicitSize : 0)) : rightRow.implicitWidth

            RoundCorner {
                id: rightLeftOutwardCorner
                visible: root.isMaterialHug && root.rightLaneFilled
                anchors.right: rightMaterialPill.left
                anchors.top: !Config.options.bar.bottom ? parent.top : undefined
                anchors.bottom: Config.options.bar.bottom ? parent.bottom : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !Config.options.bar.bottom ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.BottomRight
            }

            // Material pill wrapper
            Rectangle {
                id: rightMaterialPill
                visible: root.isMaterial && root.rightLaneFilled
                anchors.right: root.isMaterialHug ? parent.right : undefined
                anchors.top: (root.isMaterialHug && !Config.options.bar.bottom) ? parent.top : undefined
                anchors.bottom: (root.isMaterialHug && Config.options.bar.bottom) ? parent.bottom : undefined
                anchors.centerIn: root.isMaterialHug ? undefined : parent
                width: rightMaterialRow.implicitWidth + (root.isMaterialHug ? 16 : 10)
                height: root.isMaterialHug ? parent.height : rightMaterialRow.implicitHeight
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topRightRadius: root.isMaterialHug ? 0 : radius
                bottomRightRadius: root.isMaterialHug ? 0 : radius
                topLeftRadius: (root.isMaterialHug && Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                bottomLeftRadius: (root.isMaterialHug && !Config.options.bar.bottom) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)

                RowLayout {
                    id: rightMaterialRow
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        model: root.effectiveRightLayout
                        delegate: rightMaterialGroupDelegate
                    }

                    Component {
                        id: rightMaterialGroupDelegate
                        BarGroup {
                            Layout.fillHeight: true
                            currentIndex: index
                            widgetName: modelData
                            totalCount: root.effectiveRightLayout.length
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData)
                            bgColor: root.getMaterialPillColor(modelData)
                            Loader {
                                Layout.fillHeight: true
                                // The hidden branch keeps its (empty) groups so
                                // RowLayout implicit sizes stay live, but must
                                // not instantiate widgets: a second island stole
                                // islandHost and doubled service consumers.
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData)
                            }
                        }
                    }
                }
            }

            // Non-material layout
            RowLayout {
                id: rightRow
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.rowSpacing

                Repeater {
                    model: root.effectiveRightLayout
                    delegate: rightBarGroupDelegate
                }

                Component {
                    id: rightBarGroupDelegate
                    BarGroup {
                        Layout.fillHeight: true
                        currentIndex: index
                        widgetName: modelData
                        totalCount: root.effectiveRightLayout.length
                        Loader {
                            Layout.fillHeight: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData)
                        }
                    }
                }
            }
        }
    }

    // end4's per-widget spacing: transparent pulls the groups together,
    // segmented separates them, panel keeps a wider gap.
    readonly property real rowSpacing: Config.options.bar.borderless === "transparent" ? -7 : (Config.options?.bar.borderless === "segmented" && root.isPanel) ? 3 : Config.options?.bar.borderless === "segmented" ? -1 : root.isPanel ? 4 : 2
}

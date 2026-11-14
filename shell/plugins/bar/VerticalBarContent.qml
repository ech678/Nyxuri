// Fork & Trim: end4-pC modules/ii/verticalBar/VerticalBarContent.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri:
//   - `Config.options.bar.bottom` (end4 overloaded it as "right edge" for the
//     vertical bar) is replaced by the single `bar.edge` truth; `onRight`
//     carries the mirror.
//   - followFrameColor / frameColor dropped (no UI, constant false).
//   - island is filtered out of the middle lane: the horizontal island has no
//     vertical shape yet (ROADMAP B9.4 keeps it hidden, B9.6 designs it).
//   - widget URL map + material helpers mirror BarContent instead of importing
//     it (one content instance per orientation, no shared mutable state).
//   - lane heights collapse when the lane's widgets hide themselves, same
//     contract as the horizontal lanes.
//   - probe surface (laneTopHeight / laneCenterY / ...) so the runtime probe
//     can assert the vertical geometry without re-deriving the layout.

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.SystemTray
import qs.commons
import qs.services
import qs.ui

Item {
    id: root

    implicitWidth: Appearance.sizes.verticalBarWidth
    height: parent ? parent.height : 0
    // Orientation marker: Bar.qml's probe helpers and the runtime probe read
    // this instead of guessing from the screen edge.
    readonly property bool vertical: true
    readonly property bool onRight: Config.options.bar.edge === "right"

    readonly property real barPadding: 0
    readonly property bool isMaterial: PersonalizationConfig.barIsMaterial
    readonly property bool isMaterialHug: PersonalizationConfig.barIsMaterialHug
    readonly property bool isPanel: PersonalizationConfig.barIsPanel
    // Same inset relationship as the horizontal lanes (ROADMAP B9.0).
    readonly property real laneMargin: root.isMaterialHug ? 0 : root.isMaterial ? Appearance.sizes.hyprlandGapsOut : (Config.options.bar.cornerStyle === 1 || root.isPanel) ? 4 : 8

    readonly property color materialPillBgColor: Appearance.colors.colLayer0
    readonly property bool trayHasItems: SystemTray.items.values.length > 0
    readonly property bool batteryAvailable: Battery.available

    function filterLayout(layout) {
        let filtered = Array.from(layout ?? []);
        if (!root.trayHasItems)
            filtered = filtered.filter(name => name !== "sysTray" && name !== "tray");
        if (!root.batteryAvailable)
            filtered = filtered.filter(name => name !== "battery" && name !== "batteryIndicator");
        // No vertical island shape yet.
        filtered = filtered.filter(name => name !== "island");
        return filtered;
    }

    readonly property var effectiveLeftLayout: filterLayout(Config.options.bar.m3.layouts.leftLayout)
    readonly property var effectiveMiddleLayout: filterLayout(Config.options.bar.m3.layouts.middleLayout)
    readonly property var effectiveRightLayout: filterLayout(Config.options.bar.m3.layouts.rightLayout)
    readonly property bool leftLaneFilled: root.effectiveLeftLayout.length > 0
    readonly property bool centerLaneFilled: root.effectiveMiddleLayout.length > 0
    readonly property bool rightLaneFilled: root.effectiveRightLayout.length > 0

    readonly property real centerPillY: centerPill.y
    readonly property real centerPillHeight: centerPill.height
    // Probe surface.
    readonly property real laneTopHeight: topLane.height
    readonly property real laneBottomHeight: bottomLane.height
    readonly property real laneCenterY: absoluteCenter.y + contentContainer.y
    readonly property real laneCenterHeight: absoluteCenter.height

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
        const blacklist = ["workspaces", "divisor", "powerButton", "docktoPanel", "leftSidebarButton", "rightSidebarButton", "activeWindow", "dynamicIsland", "island", "avatar"];
        return !blacklist.includes(name);
    }

    function getMaterialPillColor(name) {
        return M3Palette.pillContainer(name);
    }

    property var screen: root.QsWindow.window?.screen

    Rectangle {
        id: barBackground
        anchors.fill: parent
        anchors.margins: Config.options.bar.cornerStyle === 1 ? Config.options.bar.m3.gapsOut : 0
        color: (!root.centerOnly && Config.options.bar.m3.showBackground && Config.options.bar.cornerStyle !== 2 && !root.isMaterial) ? Appearance.colors.colLayer0 : "transparent"
        radius: Config.options.bar.cornerStyle === 1 ? Appearance.rounding.windowRounding : 0
        border.width: (!root.centerOnly && Config.options.bar.cornerStyle === 1) ? 1 : 0
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
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        height: absoluteCenter.hasContent ? middleCol.implicitHeight + 10 : 0
        width: parent.width - (Config.options.bar.cornerStyle === 1 ? Config.options.bar.m3.gapsOut * 2 : 0)
        color: root.isMaterial ? "transparent" : Appearance.colors.colLayer0
        radius: Config.options.bar.cornerStyle === 1 || root.isMaterial ? Appearance.rounding.windowRounding : 0
        border.width: Config.options.bar.cornerStyle === 1 ? 1 : 0
        border.color: Appearance.colors.colLayer0Border

        bottomRightRadius: Config.options.bar.cornerStyle === 0 && !root.onRight ? 0 : radius
        topRightRadius: Config.options.bar.cornerStyle === 0 && !root.onRight ? Appearance.rounding.screenRounding : radius
        bottomLeftRadius: Config.options.bar.cornerStyle === 0 && root.onRight ? 0 : radius
        topLeftRadius: Config.options.bar.cornerStyle === 0 && root.onRight ? Appearance.rounding.screenRounding : radius
    }

    Item {
        id: contentContainer
        anchors.fill: barBackground
        anchors.margins: root.barPadding

        // Top lane (leftLayout)
        Item {
            id: topLane
            readonly property bool hasContent: root.leftLaneFilled && (root.isMaterial ? topMaterialCol.implicitHeight > 0 : topCol.implicitHeight > 0)
            anchors.top: parent.top
            anchors.topMargin: root.isMaterialHug ? 0 : root.laneMargin
            anchors.left: parent.left
            anchors.right: parent.right
            height: !topLane.hasContent ? 0 : root.isMaterial ? (topMaterialPill.height + (root.isMaterialHug ? topBottomOutwardCorner.implicitSize : 0)) : topCol.implicitHeight

            Rectangle {
                id: topMaterialPill
                visible: root.isMaterial && root.leftLaneFilled
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: topLane.hasContent ? topMaterialCol.implicitHeight + (root.isMaterialHug ? 16 : 10) : 0
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topLeftRadius: root.isMaterialHug ? 0 : radius
                topRightRadius: root.isMaterialHug ? 0 : radius
                bottomLeftRadius: (root.isMaterialHug && root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && !root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)

                ColumnLayout {
                    id: topMaterialCol
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        model: root.effectiveLeftLayout
                        delegate: topMaterialGroupDelegate
                    }

                    Component {
                        id: topMaterialGroupDelegate
                        BarGroup {
                            Layout.fillWidth: true
                            vertical: true
                            currentIndex: index
                            widgetName: modelData
                            totalCount: root.effectiveLeftLayout.length
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData)
                            bgColor: root.getMaterialPillColor(modelData)
                            Loader {
                                Layout.fillWidth: true
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData)
                                onLoaded: {
                                    if (item && "vertical" in item)
                                        item.vertical = true;
                                }
                            }
                        }
                    }
                }
            }

            RoundCorner {
                id: topBottomOutwardCorner
                visible: root.isMaterialHug && topLane.hasContent
                anchors.top: topMaterialPill.bottom
                anchors.left: !root.onRight ? parent.left : undefined
                anchors.right: root.onRight ? parent.right : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !root.onRight ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.TopRight
            }

            ColumnLayout {
                id: topCol
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.laneSpacing

                Repeater {
                    model: root.effectiveLeftLayout
                    delegate: topGroupDelegate
                }

                Component {
                    id: topGroupDelegate
                    BarGroup {
                        Layout.fillWidth: true
                        vertical: true
                        currentIndex: index
                        widgetName: modelData
                        totalCount: root.effectiveLeftLayout.length
                        Loader {
                            Layout.fillWidth: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData)
                            onLoaded: {
                                if (item && "vertical" in item)
                                    item.vertical = true;
                            }
                        }
                    }
                }
            }
        }

        // Centre lane (middleLayout)
        Item {
            id: absoluteCenter
            readonly property bool hasContent: root.centerLaneFilled && (root.isMaterial ? centerMaterialCol.implicitHeight > 0 : middleCol.implicitHeight > 0)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: !absoluteCenter.hasContent ? 0 : root.isMaterial ? (centerMaterialPill.height + (root.isMaterialHug ? (centerTopOutwardCorner.implicitSize + centerBottomOutwardCorner.implicitSize) : 0)) : middleCol.implicitHeight

            RoundCorner {
                id: centerTopOutwardCorner
                visible: root.isMaterialHug && absoluteCenter.hasContent
                anchors.bottom: centerMaterialPill.top
                anchors.left: !root.onRight ? parent.left : undefined
                anchors.right: root.onRight ? parent.right : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !root.onRight ? RoundCorner.CornerEnum.BottomLeft : RoundCorner.CornerEnum.BottomRight
            }

            Rectangle {
                id: centerMaterialPill
                visible: root.isMaterial && root.centerLaneFilled
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width
                height: absoluteCenter.hasContent ? centerMaterialCol.implicitHeight + (root.isMaterialHug ? 16 : 10) : 0
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topLeftRadius: (root.isMaterialHug && root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                bottomLeftRadius: (root.isMaterialHug && root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                topRightRadius: (root.isMaterialHug && !root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && !root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)

                ColumnLayout {
                    id: centerMaterialCol
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        model: root.effectiveMiddleLayout
                        delegate: centerMaterialGroupDelegate
                    }

                    Component {
                        id: centerMaterialGroupDelegate
                        BarGroup {
                            Layout.fillWidth: true
                            vertical: true
                            currentIndex: index
                            widgetName: modelData
                            totalCount: root.effectiveMiddleLayout.length
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData)
                            bgColor: root.getMaterialPillColor(modelData)
                            Loader {
                                Layout.fillWidth: true
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData)
                                onLoaded: {
                                    if (item && "vertical" in item)
                                        item.vertical = true;
                                }
                            }
                        }
                    }
                }
            }

            RoundCorner {
                id: centerBottomOutwardCorner
                visible: root.isMaterialHug && absoluteCenter.hasContent
                anchors.top: centerMaterialPill.bottom
                anchors.left: !root.onRight ? parent.left : undefined
                anchors.right: root.onRight ? parent.right : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !root.onRight ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.TopRight
            }

            ColumnLayout {
                id: middleCol
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.laneSpacing

                Repeater {
                    model: root.effectiveMiddleLayout
                    delegate: middleGroupDelegate
                }

                Component {
                    id: middleGroupDelegate
                    BarGroup {
                        Layout.fillWidth: true
                        vertical: true
                        currentIndex: index
                        widgetName: modelData
                        totalCount: root.effectiveMiddleLayout.length
                        paintBackground: modelData !== "island"
                        Loader {
                            Layout.fillWidth: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData)
                            onLoaded: {
                                if (item && "vertical" in item)
                                    item.vertical = true;
                            }
                        }
                    }
                }
            }
        }

        // Bottom lane (rightLayout)
        Item {
            id: bottomLane
            readonly property bool hasContent: root.rightLaneFilled && (root.isMaterial ? bottomMaterialCol.implicitHeight > 0 : bottomCol.implicitHeight > 0)
            anchors.bottom: parent.bottom
            anchors.bottomMargin: root.isMaterialHug ? 0 : root.laneMargin
            anchors.left: parent.left
            anchors.right: parent.right
            height: !bottomLane.hasContent ? 0 : root.isMaterial ? (bottomMaterialPill.height + (root.isMaterialHug ? bottomTopOutwardCorner.implicitSize : 0)) : bottomCol.implicitHeight

            RoundCorner {
                id: bottomTopOutwardCorner
                visible: root.isMaterialHug && bottomLane.hasContent
                anchors.bottom: bottomMaterialPill.top
                anchors.left: !root.onRight ? parent.left : undefined
                anchors.right: root.onRight ? parent.right : undefined
                implicitSize: Appearance.rounding.screenRounding
                color: root.materialPillBgColor
                corner: !root.onRight ? RoundCorner.CornerEnum.BottomLeft : RoundCorner.CornerEnum.BottomRight
            }

            Rectangle {
                id: bottomMaterialPill
                visible: root.isMaterial && root.rightLaneFilled
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: bottomLane.hasContent ? bottomMaterialCol.implicitHeight + (root.isMaterialHug ? 16 : 10) : 0
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                bottomLeftRadius: root.isMaterialHug ? 0 : radius
                bottomRightRadius: root.isMaterialHug ? 0 : radius
                topLeftRadius: (root.isMaterialHug && root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)
                topRightRadius: (root.isMaterialHug && !root.onRight) ? Appearance.rounding.screenRounding : (root.isMaterialHug ? 0 : radius)

                ColumnLayout {
                    id: bottomMaterialCol
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        model: root.effectiveRightLayout
                        delegate: bottomMaterialGroupDelegate
                    }

                    Component {
                        id: bottomMaterialGroupDelegate
                        BarGroup {
                            Layout.fillWidth: true
                            vertical: true
                            currentIndex: index
                            widgetName: modelData
                            totalCount: root.effectiveRightLayout.length
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData)
                            bgColor: root.getMaterialPillColor(modelData)
                            Loader {
                                Layout.fillWidth: true
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData)
                                onLoaded: {
                                    if (item && "vertical" in item)
                                        item.vertical = true;
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                id: bottomCol
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.laneSpacing

                Repeater {
                    model: root.effectiveRightLayout
                    delegate: bottomGroupDelegate
                }

                Component {
                    id: bottomGroupDelegate
                    BarGroup {
                        Layout.fillWidth: true
                        vertical: true
                        currentIndex: index
                        widgetName: modelData
                        totalCount: root.effectiveRightLayout.length
                        Loader {
                            Layout.fillWidth: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData)
                            onLoaded: {
                                if (item && "vertical" in item)
                                    item.vertical = true;
                            }
                        }
                    }
                }
            }
        }
    }

    // end4's vertical spacing ladder. It differs from the horizontal row
    // spacing on purpose: stacked groups need more air on the transparent
    // mode and less on the segmented one.
    readonly property real laneSpacing: Config.options.bar.borderless === "transparent" ? -4 : (Config.options?.bar.borderless === "segmented" && root.isPanel) ? 3 : Config.options?.bar.borderless === "segmented" ? -2 : root.isPanel ? 4 : 2
}

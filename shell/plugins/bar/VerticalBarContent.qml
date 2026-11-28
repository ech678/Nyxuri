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
//   - widget URL resolution + material helpers mirror BarContent's
//     functions; the id->file table itself is shared (BarWidgetFiles.js,
//     D4a) so the two orientations cannot drift apart again.
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
import "BarWidgetFiles.js" as BarWidgetFiles
import "SegmentRoles.js" as SegmentRoles
import "OverflowLayout.js" as OverflowLayout

Item {
    id: root

    implicitWidth: PersonalizationConfig.resolvedVerticalBarWidth(root.axes)
    height: parent ? parent.height : 0
    // Orientation marker: Bar.qml's probe helpers and the runtime probe read
    // this instead of guessing from the screen edge.
    readonly property bool vertical: true
    // D4e per-bar host: the window injects its entry's config; standalone
    // mounts (the probe harness, direct file:// loads) fall back to the
    // settings-facing entry. Every bar-level read below resolves through
    // this, never the global views.
    property var barConfig: PersonalizationConfig.activeBarConfig()
    readonly property var axes: root.barConfig ? root.barConfig.axes : BarDefaults.DEFAULTS
    readonly property bool onRight: root.axes.position === "right"

    readonly property real barPadding: 0
    readonly property bool isMaterial: root.axes.cornerStyle === 3 || root.axes.cornerStyle === 4
    readonly property bool isMaterialHug: root.axes.cornerStyle === 4
    readonly property bool isPanel: root.axes.cornerStyle === 5
    // Same inset relationship as the horizontal lanes (ROADMAP B9.0); the
    // per-style values are the baseline under the D4c innerPadding axis.
    readonly property real laneMargin: PersonalizationConfig.resolvedBarInnerPadding(root.axes)

    readonly property color materialPillBgColor: Appearance.colors.colLayer0
    // D4c bar shell radius axis (see BarContent.shellRadius).
    readonly property real shellRadius: PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding, root.axes)
    readonly property bool trayHasItems: SystemTray.items.values.length > 0
    readonly property bool batteryAvailable: Battery.available

    // D4c SegmentRoles runs (same contract as BarContent): participation
    // from the active branch's live groups.
    function laneSegmentRoles(entries, plainRepeater, materialRepeater) {
        const repeater = root.isMaterial ? materialRepeater : plainRepeater;
        const participating = [];
        for (let i = 0; i < entries.length; i += 1) {
            const item = repeater && repeater.count === entries.length ? repeater.itemAt(i) : null;
            participating.push(item === null ? true : item.hasContent);
        }
        return SegmentRoles.resolve(entries, participating);
    }

    readonly property var leftSegmentRoles: root.laneSegmentRoles(root.effectiveLeftLayout, leftGroups, leftMaterialGroups)
    readonly property var middleSegmentRoles: root.laneSegmentRoles(root.effectiveMiddleLayout, middleGroups, middleMaterialGroups)
    readonly property var rightSegmentRoles: root.laneSegmentRoles(root.effectiveRightLayout, rightGroups, rightMaterialGroups)

    // D4d overflow engine (bar-config.md D4d): vertical twin of
    // BarContent's engine — same resolver, axis flipped to the lane
    // column's height. Lane names map middle -> dux "center" here too.
    readonly property real overflowLength: contentContainer.height
    readonly property real overflowTriggerSize: root.isMaterial ? topOverflowHostMaterial.implicitHeight : topOverflowHost.implicitHeight
    readonly property var overflowPlan: ({
        left: root.overflowMeasure(root.effectiveLeftLayout, leftGroups, leftMaterialGroups, "left"),
        center: root.overflowMeasure(root.effectiveMiddleLayout, middleGroups, middleMaterialGroups, "middle"),
        right: root.overflowMeasure(root.effectiveRightLayout, rightGroups, rightMaterialGroups, "right")
    })
    // Debounce on a 1ms timer (LIFE007's allowed non-zero interval; see
    // BarContent for why not Qt.callLater).
    onOverflowPlanChanged: overflowTimer.restart()
    onOverflowLengthChanged: overflowTimer.restart()
    onLaneSpacingChanged: overflowTimer.restart()
    onIsMaterialChanged: overflowTimer.restart()
    property var overflowPrevious: ({
        left: [],
        center: [],
        right: []
    })
    property var overflowHiddenGroupsLeft: []
    property var overflowHiddenGroupsMiddle: []
    property var overflowHiddenGroupsRight: []
    readonly property var overflowHiddenIds: {
        const ids = [];
        const collect = groups => {
            for (let i = 0; i < groups.length; i += 1)
                ids.push(groups[i].widgetName);
        };
        collect(root.overflowHiddenGroupsLeft);
        collect(root.overflowHiddenGroupsMiddle);
        collect(root.overflowHiddenGroupsRight);
        return ids;
    }

    function overflowMeasure(entries, plainRepeater, materialRepeater, zone) {
        const repeater = root.isMaterial ? materialRepeater : plainRepeater;
        const fallback = root.axes[zone + "OverflowMode"] === "bar" ? "bar" : "auto";
        const list = [];
        for (let i = 0; i < entries.length; i += 1) {
            const group = repeater && repeater.count === entries.length ? repeater.itemAt(i) : null;
            // dux placement/priority read top-level keys; flatten overrides.
            const flat = Object.assign({
                widgetId: entries[i].widgetId
            }, entries[i].overrides || {});
            list.push({
                size: group ? group.overflowEntrySize : 0,
                min: group ? group.overflowEntryMin : 0,
                mode: OverflowLayout.placement(flat, fallback),
                priority: OverflowLayout.priority(flat)
            });
        }
        return list;
    }

    function resolveOverflow() {
        const length = root.overflowLength;
        if (!(length > 0))
            return;
        const result = OverflowLayout.resolve(root.overflowPlan, {
            length: length,
            start: root.laneMargin,
            end: root.laneMargin,
            spacing: root.isMaterial ? 3 : root.laneSpacing,
            triggerSize: root.overflowTriggerSize,
            positions: {
                left: root.effectiveLeftLayout.length,
                center: root.effectiveMiddleLayout.length,
                right: 0
            },
            restoreMargin: 4
        }, root.overflowPrevious);
        root.overflowPrevious = result.hidden;
        root.applyOverflow(root.effectiveLeftLayout, leftGroups, leftMaterialGroups, result.hidden.left, result.sizes.left, "left");
        root.applyOverflow(root.effectiveMiddleLayout, middleGroups, middleMaterialGroups, result.hidden.center, result.sizes.center, "middle");
        root.applyOverflow(root.effectiveRightLayout, rightGroups, rightMaterialGroups, result.hidden.right, result.sizes.right, "right");
    }

    // Assign only on real membership changes (see BarContent.sameGroups).
    function sameGroups(a, b) {
        if (!Array.isArray(a) || a.length !== (b ? b.length : -1))
            return false;
        for (let i = 0; i < a.length; i += 1) {
            if (a[i] !== b[i])
                return false;
        }
        return true;
    }

    function applyOverflow(entries, plainRepeater, materialRepeater, hidden, sizes, zone) {
        const hiddenGroups = [];
        for (let i = 0; i < entries.length; i += 1) {
            const isHidden = hidden.indexOf(i) !== -1;
            const plainGroup = plainRepeater && plainRepeater.count === entries.length ? plainRepeater.itemAt(i) : null;
            const materialGroup = materialRepeater && materialRepeater.count === entries.length ? materialRepeater.itemAt(i) : null;
            if (plainGroup && plainGroup.inOverflow !== isHidden)
                plainGroup.inOverflow = isHidden;
            if (materialGroup && materialGroup.inOverflow !== isHidden)
                materialGroup.inOverflow = isHidden;
            const group = root.isMaterial ? materialGroup : plainGroup;
            if (!group)
                continue;
            if (isHidden && group.overflowWidget)
                hiddenGroups.push(group);
            group.setOverflowAllotment(sizes && sizes[i] !== undefined ? sizes[i] - group.padding * 2 : -1);
        }
        if (zone === "left" && !root.sameGroups(hiddenGroups, root.overflowHiddenGroupsLeft))
            root.overflowHiddenGroupsLeft = hiddenGroups;
        else if (zone === "middle" && !root.sameGroups(hiddenGroups, root.overflowHiddenGroupsMiddle))
            root.overflowHiddenGroupsMiddle = hiddenGroups;
        else if (zone === "right" && !root.sameGroups(hiddenGroups, root.overflowHiddenGroupsRight))
            root.overflowHiddenGroupsRight = hiddenGroups;
    }

    Timer {
        id: overflowTimer
        interval: 1
        repeat: false
        onTriggered: root.resolveOverflow()
    }


    // D4a: same entry model as BarContent — normalized barConfigs entries,
    // disabled widgets dropped before instantiation (they collapse the lane
    // like any self-hiding widget).
    function filterLayout(entries) {
        let filtered = Array.from(entries ?? []).filter(entry => entry && entry.enabled !== false);
        if (!root.trayHasItems)
            filtered = filtered.filter(entry => entry.widgetId !== "tray");
        if (!root.batteryAvailable)
            filtered = filtered.filter(entry => entry.widgetId !== "battery");
        // No vertical island shape yet.
        filtered = filtered.filter(entry => entry.widgetId !== "island");
        return filtered;
    }

    readonly property var effectiveLeftLayout: filterLayout(root.barConfig ? root.barConfig.lanes.left : [])
    readonly property var effectiveMiddleLayout: filterLayout(root.barConfig ? root.barConfig.lanes.middle : [])
    readonly property var effectiveRightLayout: filterLayout(root.barConfig ? root.barConfig.lanes.right : [])
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
    // D4d click-through mask surfaces (BarContent.laneMaskLeft lineage).
    readonly property Item laneMaskLeft: topLane
    readonly property Item laneMaskMiddle: absoluteCenter
    readonly property Item laneMaskRight: bottomLane

    function getWidgetUrl(id) {
        const file = BarWidgetFiles.fileFor(id);
        if (!file) {
            console.warn("[VerticalBarContent] no component registered for widget id:", id);
            return "";
        }
        return Qt.resolvedUrl("./" + file);
    }

    // D4a property-injection protocol (same as BarContent).
    function injectWidgetEntry(loader, entry) {
        if (loader.item && loader.item.widgetEntry !== undefined)
            loader.item.widgetEntry = entry;
        if (loader.item && loader.item.widgetBar !== undefined)
            loader.item.widgetBar = Qt.binding(() => root.barConfig);
    }

    function shouldPaintMaterialPill(name) {
        if (!root.isMaterial)
            return false;
        const blacklist = ["workspaces", "separator", "powerButton", "docktoPanel", "leftSidebarButton", "rightSidebarButton", "activeWindow", "dynamicIsland", "island", "avatar"];
        return !blacklist.includes(name);
    }

    function getMaterialPillColor(name) {
        return M3Palette.pillContainer(name);
    }

    property var screen: root.QsWindow.window?.screen

    Rectangle {
        id: barBackground
        objectName: "barBackground"
        anchors.fill: parent
        anchors.margins: root.axes.cornerStyle === 1 ? Config.options.bar.m3.gapsOut : 0
        color: (!root.centerOnly && root.axes.showBackground === true && root.axes.cornerStyle !== 2 && !root.isMaterial) ? PersonalizationConfig.resolvedBarSurfaceColor(Appearance.colors.colLayer0, root.axes) : "transparent"
        radius: root.axes.cornerStyle === 1 ? Appearance.rounding.windowRounding : 0
        border.width: PersonalizationConfig.barSurfaceBorderWidth(!root.centerOnly && root.axes.cornerStyle === 1 ? 1 : 0)
        border.color: PersonalizationConfig.barSurfaceBorderColor(root.axes.cornerStyle === 1 && root.axes.showBackground !== true ? "transparent" : ColorUtils.transparentize(Appearance.colors.colLayer0Border, 0.8))
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
        visible: root.centerOnly && root.axes.showBackground === true && root.axes.cornerStyle !== 2
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        height: absoluteCenter.hasContent ? middleCol.implicitHeight + 10 : 0
        width: parent.width - (root.axes.cornerStyle === 1 ? Config.options.bar.m3.gapsOut * 2 : 0)
        color: root.isMaterial ? "transparent" : Appearance.colors.colLayer0
        radius: root.axes.cornerStyle === 1 || root.isMaterial ? Appearance.rounding.windowRounding : 0
        border.width: root.axes.cornerStyle === 1 ? 1 : 0
        border.color: Appearance.colors.colLayer0Border

        bottomRightRadius: root.axes.cornerStyle === 0 && !root.onRight ? 0 : radius
        topRightRadius: root.axes.cornerStyle === 0 && !root.onRight ? root.shellRadius : radius
        bottomLeftRadius: root.axes.cornerStyle === 0 && root.onRight ? 0 : radius
        topLeftRadius: root.axes.cornerStyle === 0 && root.onRight ? root.shellRadius : radius
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
                bottomLeftRadius: (root.isMaterialHug && root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && !root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)

                ColumnLayout {
                    id: topMaterialCol
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        id: leftMaterialGroups
                        model: root.effectiveLeftLayout
                        delegate: topMaterialGroupDelegate
                    }

                    LaneOverflowHost {
                        widgetBar: root.barConfig
                        id: topOverflowHostMaterial
                        Layout.fillWidth: true
                        vertical: true
                        visible: root.overflowHiddenGroupsLeft.length > 0
                        overflowGroups: root.overflowHiddenGroupsLeft
                    }

                    Component {
                        id: topMaterialGroupDelegate
                        BarGroup {
                            barAxes: root.axes
                            Layout.fillWidth: true
                            vertical: true
                            segmentRole: root.leftSegmentRoles[index] ?? "solo"
                            widgetName: modelData.widgetId
                            widgetEntry: modelData
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData.widgetId)
                            bgColor: root.getMaterialPillColor(modelData.widgetId)
                            Loader {
                                Layout.fillWidth: true
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData.widgetId)
                                onLoaded: {
                                    root.injectWidgetEntry(this, modelData);
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
                implicitSize: root.shellRadius
                color: root.materialPillBgColor
                corner: !root.onRight ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.TopRight
            }

            ColumnLayout {
                id: topCol
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.laneSpacing

                Repeater {
                    id: leftGroups
                    model: root.effectiveLeftLayout
                    delegate: topGroupDelegate
                }

                LaneOverflowHost {
                    widgetBar: root.barConfig
                    id: topOverflowHost
                    Layout.fillWidth: true
                    vertical: true
                    visible: root.overflowHiddenGroupsLeft.length > 0
                    overflowGroups: root.overflowHiddenGroupsLeft
                }

                Component {
                    id: topGroupDelegate
                    BarGroup {
                        barAxes: root.axes
                        Layout.fillWidth: true
                        vertical: true
                        segmentRole: root.leftSegmentRoles[index] ?? "solo"
                        widgetName: modelData.widgetId
                        widgetEntry: modelData
                        Loader {
                            Layout.fillWidth: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData.widgetId)
                            onLoaded: {
                                root.injectWidgetEntry(this, modelData);
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
                implicitSize: root.shellRadius
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

                topLeftRadius: (root.isMaterialHug && root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                bottomLeftRadius: (root.isMaterialHug && root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                topRightRadius: (root.isMaterialHug && !root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && !root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)

                ColumnLayout {
                    id: centerMaterialCol
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        id: middleMaterialGroups
                        model: root.effectiveMiddleLayout
                        delegate: centerMaterialGroupDelegate
                    }

                    LaneOverflowHost {
                        widgetBar: root.barConfig
                        id: centerOverflowHostMaterial
                        Layout.fillWidth: true
                        vertical: true
                        visible: root.overflowHiddenGroupsMiddle.length > 0
                        overflowGroups: root.overflowHiddenGroupsMiddle
                    }

                    Component {
                        id: centerMaterialGroupDelegate
                        BarGroup {
                            barAxes: root.axes
                            Layout.fillWidth: true
                            vertical: true
                            segmentRole: root.middleSegmentRoles[index] ?? "solo"
                            widgetName: modelData.widgetId
                            widgetEntry: modelData
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData.widgetId)
                            bgColor: root.getMaterialPillColor(modelData.widgetId)
                            Loader {
                                Layout.fillWidth: true
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData.widgetId)
                                onLoaded: {
                                    root.injectWidgetEntry(this, modelData);
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
                implicitSize: root.shellRadius
                color: root.materialPillBgColor
                corner: !root.onRight ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.TopRight
            }

            ColumnLayout {
                id: middleCol
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.laneSpacing

                Repeater {
                    id: middleGroups
                    model: root.effectiveMiddleLayout
                    delegate: middleGroupDelegate
                }

                LaneOverflowHost {
                    widgetBar: root.barConfig
                    id: middleOverflowHost
                    Layout.fillWidth: true
                    vertical: true
                    visible: root.overflowHiddenGroupsMiddle.length > 0
                    overflowGroups: root.overflowHiddenGroupsMiddle
                }

                Component {
                    id: middleGroupDelegate
                    BarGroup {
                        barAxes: root.axes
                        Layout.fillWidth: true
                        vertical: true
                        segmentRole: root.middleSegmentRoles[index] ?? "solo"
                        widgetName: modelData.widgetId
                        widgetEntry: modelData
                        paintBackground: modelData.widgetId !== "island"
                        Loader {
                            Layout.fillWidth: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData.widgetId)
                            onLoaded: {
                                root.injectWidgetEntry(this, modelData);
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
                implicitSize: root.shellRadius
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
                topLeftRadius: (root.isMaterialHug && root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                topRightRadius: (root.isMaterialHug && !root.onRight) ? root.shellRadius : (root.isMaterialHug ? 0 : radius)

                ColumnLayout {
                    id: bottomMaterialCol
                    anchors.centerIn: parent
                    spacing: 3

                    LaneOverflowHost {
                        widgetBar: root.barConfig
                        id: bottomOverflowHostMaterial
                        Layout.fillWidth: true
                        vertical: true
                        visible: root.overflowHiddenGroupsRight.length > 0
                        overflowGroups: root.overflowHiddenGroupsRight
                    }

                    Repeater {
                        id: rightMaterialGroups
                        model: root.effectiveRightLayout
                        delegate: bottomMaterialGroupDelegate
                    }

                    Component {
                        id: bottomMaterialGroupDelegate
                        BarGroup {
                            barAxes: root.axes
                            Layout.fillWidth: true
                            vertical: true
                            segmentRole: root.rightSegmentRoles[index] ?? "solo"
                            widgetName: modelData.widgetId
                            widgetEntry: modelData
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData.widgetId)
                            bgColor: root.getMaterialPillColor(modelData.widgetId)
                            Loader {
                                Layout.fillWidth: true
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData.widgetId)
                                onLoaded: {
                                    root.injectWidgetEntry(this, modelData);
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

                LaneOverflowHost {
                    widgetBar: root.barConfig
                    id: bottomOverflowHost
                    Layout.fillWidth: true
                    vertical: true
                    visible: root.overflowHiddenGroupsRight.length > 0
                    overflowGroups: root.overflowHiddenGroupsRight
                }

                Repeater {
                    id: rightGroups
                    model: root.effectiveRightLayout
                    delegate: bottomGroupDelegate
                }

                Component {
                    id: bottomGroupDelegate
                    BarGroup {
                        barAxes: root.axes
                        Layout.fillWidth: true
                        vertical: true
                        segmentRole: root.rightSegmentRoles[index] ?? "solo"
                        widgetName: modelData.widgetId
                        widgetEntry: modelData
                        Loader {
                            Layout.fillWidth: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData.widgetId)
                            onLoaded: {
                                root.injectWidgetEntry(this, modelData);
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
    // end4's vertical spacing baseline; the D4c spacing axis overrides it
    // (sentinel -1 = the per-mode values below).
    readonly property real laneSpacing: PersonalizationConfig.resolvedBarSpacing(true, root.axes)
}

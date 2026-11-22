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
import "BarWidgetFiles.js" as BarWidgetFiles
import "SegmentRoles.js" as SegmentRoles
import "OverflowLayout.js" as OverflowLayout

Item {
    id: root
    implicitHeight: Appearance.sizes.barHeight
    width: parent.width
    // D4e per-bar host: the window injects its entry's config; standalone
    // mounts (the probe harness, direct file:// loads) fall back to the
    // settings-facing entry. Every bar-level read below resolves through
    // this, never the global views.
    property var barConfig: PersonalizationConfig.activeBarConfig()
    readonly property var axes: root.barConfig ? root.barConfig.axes : BarDefaults.DEFAULTS
    readonly property real barPadding: 0
    readonly property bool isMaterial: root.axes.cornerStyle === 3 || root.axes.cornerStyle === 4
    readonly property bool isMaterialHug: root.axes.cornerStyle === 4
    readonly property bool isPanel: root.axes.cornerStyle === 5
    // end4 lane inset (references/end4-pC/modules/ii/bar/BarContent.qml:193):
    // Material hug sits flush, the Material pill keeps its 5px outer gutter,
    // Float and Panel inset 4, every other style 8. D4c: the per-style values
    // are the baseline under the innerPadding axis (sentinel -1 = these).
    readonly property real laneMargin: PersonalizationConfig.resolvedBarInnerPadding(root.axes)

    readonly property color materialPillBgColor: Appearance.colors.colLayer0
    // D4c bar shell radius axis: -1 keeps the theme's screen rounding,
    // squareCorners flattens, an explicit value overrides — one alias per
    // host keeps every corner expression on a single source.
    readonly property real shellRadius: PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding, root.axes)
    readonly property real centerPillX: centerPill.x
    readonly property real centerPillWidth: centerPill.width
    // Probe surface (scripts/dev/probe-bar.sh): the optical centre lane and its
    // evaluated geometry, so a runtime probe can catch NaN / left-edge collapse
    // without duplicating the layout math.
    readonly property real laneCenterX: absoluteCenter.x + contentContainer.x
    readonly property real laneCenterWidth: absoluteCenter.width
    // A lane whose only widgets hide themselves (Media with no track) must
    // evaluate to 0, not to its capsule padding. The probe asserts this.
    readonly property real laneLeftWidth: leftLane.width
    readonly property real laneRightWidth: rightLane.width
    // D4d click-through mask surfaces: the three lane items (an empty lane
    // collapses to zero width, so its region vanishes) — Bar.qml's input
    // mask unions exactly these when the clickThrough axis is on.
    readonly property Item laneMaskLeft: leftLane
    readonly property Item laneMaskMiddle: absoluteCenter
    readonly property Item laneMaskRight: rightLane
    // B9.6 probe surface: the raw middle-row width, so the island-hug branch
    // (frame width = row - 4, not row + 10) is assertable at runtime.
    readonly property real middleRowImplicitWidth: middleRow.implicitWidth
    readonly property bool trayHasItems: SystemTray.items.values.length > 0
    readonly property bool batteryAvailable: Battery.available

    // D4c SegmentRoles runs (fusion corners): participation comes from the
    // live groups of the ACTIVE branch (material vs plain — the inactive
    // branch's loaders are off and would report hasContent forever). A
    // hidden widget (Media with no track) re-shapes its neighbours' roles
    // instead of stranding the "last" radius on an invisible group; a
    // not-yet-loaded group counts as participating so the bar does not
    // flicker while loaders instantiate. spacer/separator break the run
    // (SegmentRoles.breaksRun).
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

    // D4d overflow engine (bar-config.md D4d): measures the ACTIVE branch's
    // groups, resolves through the forked dux OverflowLayout (hidden sets +
    // flexible allotments + hysteresis) and pushes the results back onto the
    // groups. Debounced on a zero timer like dux; the measurement binding
    // re-evaluates when widget implicit sizes, entries or the branch flip.
    // Lane names map middle -> dux "center" at this boundary only.
    readonly property real overflowLength: contentContainer.width
    readonly property real overflowTriggerSize: root.isMaterial ? leftOverflowHostMaterial.implicitWidth : leftOverflowHost.implicitWidth
    readonly property var overflowPlan: ({
        left: root.overflowMeasure(root.effectiveLeftLayout, leftGroups, leftMaterialGroups, "left"),
        center: root.overflowMeasure(root.effectiveMiddleLayout, middleGroups, middleMaterialGroups, "middle"),
        right: root.overflowMeasure(root.effectiveRightLayout, rightGroups, rightMaterialGroups, "right")
    })
    // Debounce on a 1ms timer (LIFE007's allowed non-zero interval; NOT
    // Qt.callLater — a callLater scheduled by the initial binding evaluation
    // fires mid-incubation, before the engine methods are installed on the
    // object, which crashed the probe window).
    onOverflowPlanChanged: overflowTimer.restart()
    onOverflowLengthChanged: overflowTimer.restart()
    onRowSpacingChanged: overflowTimer.restart()
    onIsMaterialChanged: overflowTimer.restart()
    property var overflowPrevious: ({
        left: [],
        center: [],
        right: []
    })
    // Resolver outputs for the lane hosts (active-branch hidden groups, lane
    // order) and the probe.
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
            // dux placement/priority read the axes as TOP-LEVEL entry keys;
            // our storage nests them in overrides, so flatten per call.
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
            spacing: root.isMaterial ? 3 : root.rowSpacing,
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

    // Assign only on real membership changes: a fresh array identity on
    // every resolve would fire the hosts' onOverflowGroupsChanged and close
    // an open popup whenever any widget resizes (clock text, media title).
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
            // Flexible allotment (resolver shrink phase): inflexible widgets
            // ignore it; sizes[i] is the lane consumption, the widget takes
            // it minus the capsule padding.
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


    // D4a: the lane model is normalized entry objects off the barConfigs
    // truth. filterLayout keeps the system gates (no tray host without
    // items, no battery widget without a battery) and now also drops
    // entries the user disabled — a disabled widget is not instantiated,
    // so its lane collapses like any other hidden widget.
    function filterLayout(entries) {
        let filtered = Array.from(entries ?? []).filter(entry => entry && entry.enabled !== false);
        // B9.3: the island is a layout member, not a second config gate.
        if (!root.trayHasItems)
            filtered = filtered.filter(entry => entry.widgetId !== "tray");
        if (!root.batteryAvailable)
            filtered = filtered.filter(entry => entry.widgetId !== "battery");
        return filtered;
    }

    readonly property var effectiveLeftLayout: filterLayout(root.barConfig ? root.barConfig.lanes.left : [])
    readonly property var effectiveMiddleLayout: filterLayout(root.barConfig ? root.barConfig.lanes.middle : [])
    readonly property var effectiveRightLayout: filterLayout(root.barConfig ? root.barConfig.lanes.right : [])
    readonly property bool leftLaneFilled: root.effectiveLeftLayout.length > 0
    readonly property bool centerLaneFilled: root.effectiveMiddleLayout.length > 0
    readonly property bool rightLaneFilled: root.effectiveRightLayout.length > 0

    function getWidgetUrl(id) {
        const file = BarWidgetFiles.fileFor(id);
        if (!file) {
            // Normalization rejects unknown ids at load, so this is a
            // registration regression, not a user-config problem.
            console.warn("[BarContent] no component registered for widget id:", id);
            return "";
        }
        return Qt.resolvedUrl("./" + file);
    }

    // D4a property-injection protocol: hosts push the lane entry into
    // widgets that declare `widgetEntry`; the widget resolves its own axes
    // through BarWidgetDefaults.option() and never touches storage.
    function injectWidgetEntry(loader, entry) {
        if (loader.item && loader.item.widgetEntry !== undefined)
            loader.item.widgetEntry = entry;
        if (loader.item && loader.item.widgetBar !== undefined)
            loader.item.widgetBar = root.barConfig;
    }

    function shouldPaintMaterialPill(name) {
        if (!root.isMaterial)
            return false;
        // end4 baseline + "island": the island paints its own capsule
        // (paintBackground: false) and must not eat a group tint. D4a:
        // "divisor" renamed to "separator" (canonical id).
        const blacklist = ["workspaces", "separator", "powerButton", "docktoPanel", "leftSidebarButton", "rightSidebarButton", "activeWindow", "dynamicIsland", "island", "avatar"];
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
        objectName: "barBackground"
        anchors.fill: parent
        anchors.margins: root.axes.cornerStyle === 1 ? Config.options.bar.m3.gapsOut : 0
        color: (!centerOnly && root.axes.showBackground === true && root.axes.cornerStyle !== 2 && !root.isMaterial) ? PersonalizationConfig.resolvedBarSurfaceColor(Appearance.colors.colLayer0, root.axes) : "transparent"
        radius: root.axes.cornerStyle === 1 ? Appearance.rounding.windowRounding : 0
        border.width: PersonalizationConfig.barSurfaceBorderWidth(!centerOnly && root.axes.cornerStyle === 1 ? 1 : 0)
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
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter
        // end4: when the island occupies the middle lane the frame hugs it
        // (-4/+8) at full height instead of the +10 padding and inset height.
        readonly property bool islandInMiddle: PersonalizationConfig.islandInLayout && root.effectiveMiddleLayout.some(entry => entry.widgetId === "island")
        width: absoluteCenter.hasContent ? (centerPill.islandInMiddle ? (root.axes.cornerStyle === 1 ? middleRow.implicitWidth + 8 : middleRow.implicitWidth - 4) : middleRow.implicitWidth + 10) : 0
        height: parent.height - (!centerPill.islandInMiddle && root.axes.cornerStyle === 1 ? Config.options.bar.m3.gapsOut * 2 : 0)
        color: root.isMaterial ? "transparent" : Appearance.colors.colLayer0
        radius: root.axes.cornerStyle === 1 || root.isMaterial ? Appearance.rounding.windowRounding : 0
        border.width: root.axes.cornerStyle === 1 ? 1 : 0
        border.color: Appearance.colors.colLayer0Border

        bottomLeftRadius: root.axes.cornerStyle === 0 && root.axes.position !== "bottom" ? root.shellRadius : radius
        bottomRightRadius: root.axes.cornerStyle === 0 && root.axes.position !== "bottom" ? root.shellRadius : radius
        topLeftRadius: root.axes.cornerStyle === 0 && root.axes.position === "bottom" ? root.shellRadius : radius
        topRightRadius: root.axes.cornerStyle === 0 && root.axes.position === "bottom" ? root.shellRadius : radius
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
            id: leftLane

            // A lane capsule belongs to the lane, not the widgets, so a lane
            // whose widgets have all hidden themselves (Media with no track)
            // must collapse too instead of leaving its padding behind.
            readonly property bool hasContent: root.leftLaneFilled && (root.isMaterial ? leftMaterialRow.implicitWidth > 0 : leftRow.implicitWidth > 0)
            anchors.left: parent.left
            anchors.leftMargin: root.laneMargin
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: !leftLane.hasContent ? 0 : root.isMaterial ? (leftMaterialPill.width + (root.isMaterialHug ? leftRightOutwardCorner.implicitSize : 0)) : leftRow.implicitWidth

            // Material pill wrapper
            Rectangle {
                id: leftMaterialPill
                visible: root.isMaterial && root.leftLaneFilled
                // Explicit geometry on purpose: conditional anchors bound to
                // `undefined` are never cleared, so a top<->bottom switch would
                // leave the pill pinned to both edges.
                x: root.isMaterialHug ? 0 : (parent.width - width) / 2
                y: root.isMaterialHug ? 0 : (parent.height - height) / 2
                width: leftLane.hasContent ? leftMaterialRow.implicitWidth + (root.isMaterialHug ? 16 : 10) : 0
                height: root.isMaterialHug ? parent.height : leftMaterialRow.implicitHeight
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topLeftRadius: root.isMaterialHug ? 0 : radius
                bottomLeftRadius: root.isMaterialHug ? 0 : radius
                topRightRadius: (root.isMaterialHug && root.axes.position === "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && root.axes.position !== "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)

                RowLayout {
                    id: leftMaterialRow
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        id: leftMaterialGroups
                        model: root.effectiveLeftLayout
                        delegate: leftMaterialGroupDelegate
                    }

                    LaneOverflowHost {
                        widgetBar: root.barConfig
                        id: leftOverflowHostMaterial
                        Layout.fillHeight: true
                        visible: root.overflowHiddenGroupsLeft.length > 0
                        overflowGroups: root.overflowHiddenGroupsLeft
                    }

                    Component {
                        id: leftMaterialGroupDelegate
                        BarGroup {
                            barAxes: root.axes
                            Layout.fillHeight: true
                            segmentRole: root.leftSegmentRoles[index] ?? "solo"
                            widgetName: modelData.widgetId
                            widgetEntry: modelData
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData.widgetId)
                            bgColor: root.getMaterialPillColor(modelData.widgetId)
                            Loader {
                                Layout.fillHeight: true
                                // The hidden branch keeps its (empty) groups so
                                // RowLayout implicit sizes stay live, but must
                                // not instantiate widgets: a second island stole
                                // islandHost and doubled service consumers.
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData.widgetId)
                                onLoaded: root.injectWidgetEntry(this, modelData)
                            }
                        }
                    }
                }
            }

            RoundCorner {
                id: leftRightOutwardCorner
                visible: root.isMaterialHug && leftLane.hasContent
                x: leftMaterialPill.x + leftMaterialPill.width
                y: root.axes.position === "bottom" ? parent.height - implicitSize : 0
                implicitSize: root.shellRadius
                color: root.materialPillBgColor
                corner: root.axes.position !== "bottom" ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.BottomLeft
            }

            // Non-material layout
            RowLayout {
                id: leftRow
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.rowSpacing

                Repeater {
                    id: leftGroups
                    model: root.effectiveLeftLayout
                    delegate: leftBarGroupDelegate
                }

                LaneOverflowHost {
                    widgetBar: root.barConfig
                    id: leftOverflowHost
                    Layout.fillHeight: true
                    visible: root.overflowHiddenGroupsLeft.length > 0
                    overflowGroups: root.overflowHiddenGroupsLeft
                }

                Component {
                    id: leftBarGroupDelegate
                    BarGroup {
                        barAxes: root.axes
                        Layout.fillHeight: true
                        segmentRole: root.leftSegmentRoles[index] ?? "solo"
                        widgetName: modelData.widgetId
                        widgetEntry: modelData
                        Loader {
                            Layout.fillHeight: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData.widgetId)
                            onLoaded: root.injectWidgetEntry(this, modelData)
                        }
                    }
                }
            }
        }

        // Center
        Item {
            id: absoluteCenter
            // Same lane rule as the sides: hiding the last widget collapses the
            // capsule instead of leaving its padding behind.
            readonly property bool hasContent: root.centerLaneFilled && (root.isMaterial ? centerMaterialRow.implicitWidth > 0 : middleRow.implicitWidth > 0)
            // Explicit x instead of anchors.centerIn: the lane width is fed by
            // dynamically loaded widget implicit sizes, and anchors did not
            // re-centre after the idle island narrowed (startup 164 -> 154).
            x: (parent.width - width) / 2
            width: !absoluteCenter.hasContent ? 0 : root.isMaterial ? (centerMaterialPill.width + (root.isMaterialHug ? (centerLeftOutwardCorner.implicitSize + centerRightOutwardCorner.implicitSize) : 0)) : middleRow.implicitWidth
            height: parent.height

            RoundCorner {
                id: centerLeftOutwardCorner
                visible: root.isMaterialHug && absoluteCenter.hasContent
                x: centerMaterialPill.x - implicitSize
                y: root.axes.position === "bottom" ? parent.height - implicitSize : 0
                implicitSize: root.shellRadius
                color: root.materialPillBgColor
                corner: root.axes.position !== "bottom" ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.BottomRight
            }

            // Material pill wrapper
            Rectangle {
                id: centerMaterialPill
                visible: root.isMaterial && root.centerLaneFilled
                anchors.centerIn: parent
                width: absoluteCenter.hasContent ? centerMaterialRow.implicitWidth + (root.isMaterialHug ? 16 : 10) : 0
                height: root.isMaterialHug ? parent.height : centerMaterialRow.implicitHeight
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topLeftRadius: (root.isMaterialHug && root.axes.position === "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                topRightRadius: (root.isMaterialHug && root.axes.position === "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                bottomLeftRadius: (root.isMaterialHug && root.axes.position !== "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                bottomRightRadius: (root.isMaterialHug && root.axes.position !== "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)

                RowLayout {
                    id: centerMaterialRow
                    anchors.centerIn: parent
                    spacing: 3

                    Repeater {
                        id: middleMaterialGroups
                        model: root.effectiveMiddleLayout
                        delegate: middleMaterialGroupDelegate
                    }

                    LaneOverflowHost {
                        widgetBar: root.barConfig
                        id: middleOverflowHostMaterial
                        Layout.fillHeight: true
                        visible: root.overflowHiddenGroupsMiddle.length > 0
                        overflowGroups: root.overflowHiddenGroupsMiddle
                    }

                    Component {
                        id: middleMaterialGroupDelegate
                        BarGroup {
                            barAxes: root.axes
                            Layout.fillHeight: true
                            segmentRole: root.middleSegmentRoles[index] ?? "solo"
                            widgetName: modelData.widgetId
                            widgetEntry: modelData
                            paintBackground: modelData.widgetId !== "island"
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData.widgetId)
                            bgColor: root.getMaterialPillColor(modelData.widgetId)
                            Loader {
                                Layout.fillHeight: true
                                // The hidden branch keeps its (empty) groups so
                                // RowLayout implicit sizes stay live, but must
                                // not instantiate widgets: a second island stole
                                // islandHost and doubled service consumers.
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData.widgetId)
                                onLoaded: root.injectWidgetEntry(this, modelData)
                            }
                        }
                    }
                }
            }

            RoundCorner {
                id: centerRightOutwardCorner
                visible: root.isMaterialHug && absoluteCenter.hasContent
                x: centerMaterialPill.x + centerMaterialPill.width
                y: root.axes.position === "bottom" ? parent.height - implicitSize : 0
                implicitSize: root.shellRadius
                color: root.materialPillBgColor
                corner: root.axes.position !== "bottom" ? RoundCorner.CornerEnum.TopLeft : RoundCorner.CornerEnum.BottomLeft
            }

            // Non-material layout
            RowLayout {
                id: middleRow
                visible: !root.isMaterial
                anchors.fill: parent
                spacing: root.rowSpacing

                Repeater {
                    id: middleGroups
                    model: root.effectiveMiddleLayout
                    delegate: middleBarGroupDelegate
                }

                LaneOverflowHost {
                    widgetBar: root.barConfig
                    id: middleOverflowHost
                    Layout.fillHeight: true
                    visible: root.overflowHiddenGroupsMiddle.length > 0
                    overflowGroups: root.overflowHiddenGroupsMiddle
                }

                Component {
                    id: middleBarGroupDelegate
                    BarGroup {
                        barAxes: root.axes
                        Layout.fillHeight: true
                        segmentRole: root.middleSegmentRoles[index] ?? "solo"
                        widgetName: modelData.widgetId
                        widgetEntry: modelData
                        paintBackground: modelData.widgetId !== "island"
                        Loader {
                            Layout.fillHeight: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData.widgetId)
                            onLoaded: root.injectWidgetEntry(this, modelData)
                        }
                    }
                }
            }
        }

        // Right
        Item {
            id: rightLane
            readonly property bool hasContent: root.rightLaneFilled && (root.isMaterial ? rightMaterialRow.implicitWidth > 0 : rightRow.implicitWidth > 0)
            anchors.right: parent.right
            anchors.rightMargin: root.laneMargin
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: !rightLane.hasContent ? 0 : root.isMaterial ? (rightMaterialPill.width + (root.isMaterialHug ? rightLeftOutwardCorner.implicitSize : 0)) : rightRow.implicitWidth

            RoundCorner {
                id: rightLeftOutwardCorner
                visible: root.isMaterialHug && rightLane.hasContent
                x: rightMaterialPill.x - implicitSize
                y: root.axes.position === "bottom" ? parent.height - implicitSize : 0
                implicitSize: root.shellRadius
                color: root.materialPillBgColor
                corner: root.axes.position !== "bottom" ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.BottomRight
            }

            // Material pill wrapper
            Rectangle {
                id: rightMaterialPill
                visible: root.isMaterial && root.rightLaneFilled
                x: root.isMaterialHug ? parent.width - width : (parent.width - width) / 2
                y: root.isMaterialHug ? 0 : (parent.height - height) / 2
                width: rightLane.hasContent ? rightMaterialRow.implicitWidth + (root.isMaterialHug ? 16 : 10) : 0
                height: root.isMaterialHug ? parent.height : rightMaterialRow.implicitHeight
                radius: root.isMaterialHug ? 0 : Appearance.rounding.full
                color: root.materialPillBgColor

                topRightRadius: root.isMaterialHug ? 0 : radius
                bottomRightRadius: root.isMaterialHug ? 0 : radius
                topLeftRadius: (root.isMaterialHug && root.axes.position === "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)
                bottomLeftRadius: (root.isMaterialHug && root.axes.position !== "bottom") ? root.shellRadius : (root.isMaterialHug ? 0 : radius)

                RowLayout {
                    id: rightMaterialRow
                    anchors.centerIn: parent
                    spacing: 3

                    LaneOverflowHost {
                        widgetBar: root.barConfig
                        id: rightOverflowHostMaterial
                        Layout.fillHeight: true
                        visible: root.overflowHiddenGroupsRight.length > 0
                        overflowGroups: root.overflowHiddenGroupsRight
                    }

                    Repeater {
                        id: rightMaterialGroups
                        model: root.effectiveRightLayout
                        delegate: rightMaterialGroupDelegate
                    }

                    Component {
                        id: rightMaterialGroupDelegate
                        BarGroup {
                            barAxes: root.axes
                            Layout.fillHeight: true
                            segmentRole: root.rightSegmentRoles[index] ?? "solo"
                            widgetName: modelData.widgetId
                            widgetEntry: modelData
                            paintMaterialPill: root.shouldPaintMaterialPill(modelData.widgetId)
                            bgColor: root.getMaterialPillColor(modelData.widgetId)
                            Loader {
                                Layout.fillHeight: true
                                // The hidden branch keeps its (empty) groups so
                                // RowLayout implicit sizes stay live, but must
                                // not instantiate widgets: a second island stole
                                // islandHost and doubled service consumers.
                                active: root.isMaterial
                                source: root.getWidgetUrl(modelData.widgetId)
                                onLoaded: root.injectWidgetEntry(this, modelData)
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

                LaneOverflowHost {
                    widgetBar: root.barConfig
                    id: rightOverflowHost
                    Layout.fillHeight: true
                    visible: root.overflowHiddenGroupsRight.length > 0
                    overflowGroups: root.overflowHiddenGroupsRight
                }

                Repeater {
                    id: rightGroups
                    model: root.effectiveRightLayout
                    delegate: rightBarGroupDelegate
                }

                Component {
                    id: rightBarGroupDelegate
                    BarGroup {
                        barAxes: root.axes
                        Layout.fillHeight: true
                        segmentRole: root.rightSegmentRoles[index] ?? "solo"
                        widgetName: modelData.widgetId
                        widgetEntry: modelData
                        Loader {
                            Layout.fillHeight: true
                            active: !root.isMaterial
                            source: root.getWidgetUrl(modelData.widgetId)
                            onLoaded: root.injectWidgetEntry(this, modelData)
                        }
                    }
                }
            }
        }
    }

    // end4's per-widget spacing baseline (transparent pulls the groups
    // together, segmented separates them, panel keeps a wider gap); the
    // D4c spacing axis overrides it (sentinel -1 = these values).
    readonly property real rowSpacing: PersonalizationConfig.resolvedBarSpacing(false, root.axes)
}

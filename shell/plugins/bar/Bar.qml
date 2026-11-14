pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.services
import qs.commons
import qs.ui
import "../../commons/BarGeometry.js" as BarGeometry

// Separate Material 3 bar selected by `bar.appearanceStyle === "m3"`.
// It replaces modules/ii/bar/Bar.qml entirely while active (see ShellIiPanelsImpl),
// so it deliberately registers no IPC target and no GlobalShortcut: "bar" is
// owned by shell.qml and the shortcuts by modules/ii/bar/Bar.qml. Toggling
// GlobalStates.barOpen through either still drives this bar.
Scope {
    id: bar
    property bool showBarBackground: Config.options.bar.m3.showBackground
    // Probe seam (scripts/dev/probe-bar.sh window phase): the active screen's
    // PanelWindow registers itself here so the runtime probe can read the
    // evaluated window/content geometry. Single instance per probe run.
    property var windowProbe: null

    IpcHandler {
        target: "bar"

        function toggle(): string {
            GlobalStates.barOpen = !GlobalStates.barOpen;
            return GlobalStates.barOpen ? "OPEN" : "CLOSED";
        }

        function close(): string {
            GlobalStates.barOpen = false;
            return "CLOSED";
        }

        function open(): string {
            GlobalStates.barOpen = true;
            return "OPEN";
        }
    }

    IpcHandler {
        target: "island"

        function state(): string {
            return ActionGateway.islandHost ? ActionGateway.islandHost.invoke("state") : "UNAVAILABLE";
        }
    }

    Variants {
        // For each monitor
        model: {
            const screens = Quickshell.screens;
            const list = Config.options.bar.screenList;
            if (!list || list.length === 0)
                return screens;
            const matched = screens.filter(screen => {
                const screenName = screen?.name ?? "";
                return screenName.length > 0 && list.includes(screenName);
            });
            return matched.length > 0 ? matched : screens;
        }
        LazyLoader {
            id: barLoader
            active: GlobalStates.barOpen && !GlobalStates.screenLocked
            required property ShellScreen modelData
            component: PanelWindow { // Bar window
                id: barRoot
                screen: barLoader.modelData

                Component.onDestruction: {
                    if (bar.windowProbe === barRoot)
                        bar.windowProbe = null;
                }

                Connections {
                    id: realFrameConnection
                    target: barRoot.contentItem ? barRoot.contentItem.Window.window : null
                    function onFrameSwapped(): void {
                        realFrameConnection.enabled = false;
                        ShellStartupService.recordRealFirstFrame("bar");
                    }
                }

                Timer {
                    id: showBarTimer
                    interval: (Config?.options.bar.autoHide.showWhenPressingSuper.delay ?? 100)
                    repeat: false
                    onTriggered: {
                        barRoot.superShow = true;
                    }
                }
                Connections {
                    target: GlobalStates
                    function onSuperDownChanged() {
                        if (!Config?.options.bar.autoHide.showWhenPressingSuper.enable)
                            return;
                        if (GlobalStates.superDown)
                            showBarTimer.restart();
                        else {
                            showBarTimer.stop();
                            barRoot.superShow = false;
                        }
                    }
                }
                property bool superShow: false
                readonly property bool autoHideEnabled: Config.options?.bar?.autoHide?.enable ?? false
                readonly property bool pushWindowsWhenShown: Config.options?.bar?.autoHide?.pushWindows ?? false
                readonly property bool overviewOwnsEdge: GlobalStates.overviewOpen || CompositorDriver.inOverview
                readonly property string outputName: barRoot.screen?.name ?? ""
                readonly property bool materialHug: Config.options.bar.m3.cornerStyle === 4
                readonly property bool panelStyle: Config.options.bar.m3.cornerStyle === 5
                readonly property real layerGap: Config.options.bar.m3.cornerStyle === 3 ? Config.options.bar.m3.gapsOut : 0
                // B9.4: `edge` is the window-anchor truth; `vertical` is the
                // same fact in the form every ported widget already reads.
                readonly property string edge: Config.options.bar.edge
                readonly property bool vertical: Config.options.bar.vertical
                readonly property bool deadPixel: Config.options.interactions.deadPixelWorkaround.enable
                readonly property bool anchoredTop: barRoot.edge === "top" || barRoot.vertical
                readonly property bool anchoredBottom: barRoot.edge === "bottom" || barRoot.vertical
                readonly property bool anchoredLeft: barRoot.edge === "left" || !barRoot.vertical
                readonly property bool anchoredRight: barRoot.edge === "right" || !barRoot.vertical
                readonly property real thickness: barRoot.vertical ? Appearance.sizes.verticalBarWidth : Appearance.sizes.barHeight
                // B9.5 outer margins: normal axis = away from the screen edge,
                // along axis = the two ends. 0 keeps end4's edge-flush look.
                readonly property real edgeMargin: Config.options.bar.edgeMargin
                readonly property real sideMargin: Config.options.bar.sideMargin
                // The margins and the reserved exclusive zone share one pure
                // implementation (commons/BarGeometry.js) with the probe.
                readonly property var windowMargins: BarGeometry.margins(barRoot.edge, barRoot.vertical, barRoot.edgeMargin, barRoot.sideMargin, barRoot.layerGap, barRoot.autoHideEnabled, barRoot.deadPixel)
                readonly property real shownExclusiveZone: BarGeometry.exclusiveZone(barRoot.vertical, Appearance.sizes.baseBarHeight, Appearance.sizes.baseVerticalBarWidth, Config.options.bar.m3.cornerStyle, Config.options.bar.m3.gapsOut, barRoot.edgeMargin)
                // The content is instantiated exactly once, by the active
                // orientation branch (B8.6: a second copy stole islandHost and
                // doubled every service consumer).
                readonly property Item barContent: contentLoader.item
                readonly property bool centerOnly: barRoot.barContent?.centerOnly ?? false
                readonly property real centerPillX: barRoot.barContent?.centerPillX ?? 0
                readonly property real centerPillWidth: barRoot.barContent?.centerPillWidth ?? 0
                readonly property real centerPillY: barRoot.barContent?.centerPillY ?? 0
                // Probe surface: where the orientation loader actually sits in
                // the window (the item's own x/y is always 0).
                readonly property real contentOffsetX: contentLoader.x
                readonly property real contentOffsetY: contentLoader.y
                readonly property int leftLaneCount: (barRoot.barContent?.effectiveLeftLayout ?? []).length
                readonly property int rightLaneCount: (barRoot.barContent?.effectiveRightLayout ?? []).length
                property bool contextMenuHold: false
                property bool leftSidebarHold: false
                property bool rightSidebarHold: false
                property bool mediaControlsHold: false
                property bool controlPanelHold: false
                readonly property bool interactionHold: contextMenuHold || leftSidebarHold || rightSidebarHold || mediaControlsHold || controlPanelHold
                readonly property bool pointerShow: !overviewOwnsEdge && hoverRegion.containsMouse
                property bool mustShow: pointerShow || superShow || interactionHold
                property bool reservationActive: false
                exclusionMode: ExclusionMode.Ignore
                exclusiveZone: !autoHideEnabled ? shownExclusiveZone : (pushWindowsWhenShown && reservationActive ? shownExclusiveZone : 0)
                WlrLayershell.namespace: "quickshell:bar"
                // Upstream raised the bar to Overlay only while a Hyprland
                // special workspace sat over a fullscreen window. Niri has no
                // special workspace, so the bar stays on Top and fullscreen
                // windows cover it, which is what iNiR's own bar does too.
                WlrLayershell.layer: WlrLayer.Top
                implicitHeight: barRoot.vertical ? 0 : (Appearance.sizes.barHeight + Appearance.rounding.screenRounding + (barRoot.autoHideEnabled ? barRoot.layerGap : 0))
                implicitWidth: barRoot.vertical ? (Appearance.sizes.verticalBarWidth + Appearance.rounding.screenRounding + (barRoot.autoHideEnabled ? barRoot.layerGap : 0)) : 0
                // When Overlay-layer, bar shares a layer with the screen-corner click zones (ScreenCorners.qml)
                // and same-layer overlap is resolved by stacking, not layer priority - bar was winning and
                // swallowing the tiny corner-open hit rects. Carve them out of the bar's own mask so clicks
                // reach the corners underneath. Only relevant on the edge the bar and corners share.
                // The corner-open cutout only mattered while the bar was raised
                // to Overlay and shared a layer with the screen-corner click
                // zones. On Top layer the corners are already above it.
                property int cornerOpenCutHeight: (autoHideEnabled && !barRoot.vertical) ? Math.max(1, Config.options?.bar?.autoHide?.hoverRegionWidth ?? 2) + layerGap : 0
                mask: Region {
                    item: hoverMaskRegion
                    // Keep a fixed screen-edge hit strip while barContent is
                    // translated off-screen. Anchoring the only hit region to
                    // the moving bar made M3 hide correctly but unable to reveal
                    // reliably on some layer-shell/compositor combinations.
                    Region {
                        item: autoHideEdgeRegion
                    }
                    Region {
                        intersection: Intersection.Subtract
                        x: 0
                        y: barRoot.edge === "bottom" ? (barRoot.height - barRoot.cornerOpenCutHeight) : 0
                        width: barRoot.edgeCornerReserve(true)
                        height: barRoot.cornerOpenCutHeight
                    }
                    Region {
                        intersection: Intersection.Subtract
                        x: barRoot.width - barRoot.edgeCornerReserve(false)
                        y: barRoot.edge === "bottom" ? (barRoot.height - barRoot.cornerOpenCutHeight) : 0
                        width: barRoot.edgeCornerReserve(false)
                        height: barRoot.cornerOpenCutHeight
                    }
                }
                color: "transparent"

                function edgeCornerName(left: bool): string {
                    const bottom = barRoot.edge === "bottom";
                    return bottom ? (left ? "bottomLeft" : "bottomRight") : (left ? "topLeft" : "topRight");
                }

                function edgeCornerReserve(left: bool): real {
                    if (!autoHideEnabled)
                        return 0;
                    const corner = edgeCornerName(left);
                    let reserve = 0;
                    const orbitEnabled = CompositorDriver.available && (Config.options?.panelFamily ?? "ii") === "ii" && (Config.options?.orbit?.enable ?? true) && (Config.options?.orbit?.hotCornerEnable ?? true);
                    if (orbitEnabled && String(Config.options?.orbit?.hotCorner ?? "topRight") === corner)
                        reserve = Math.max(reserve, Config.options?.orbit?.hotCornerSize ?? 12);
                    const sidebarCornerEnabled = Config.options?.sidebar?.cornerOpen?.enable ?? false;
                    const sidebarCornerBottom = Config.options?.sidebar?.cornerOpen?.bottom ?? false;
                    if (sidebarCornerEnabled && sidebarCornerBottom === (barRoot.edge === "bottom"))
                        reserve = Math.max(reserve, Config.options?.sidebar?.cornerOpen?.cornerRegionWidth ?? 20);
                    return reserve;
                }

                function syncReservation(): void {
                    reservationShowTimer.stop();
                    reservationHideTimer.stop();
                    if (!autoHideEnabled || !pushWindowsWhenShown) {
                        reservationActive = false;
                        return;
                    }
                    if (interactionHold) {
                        reservationActive = true;
                        return;
                    }
                    if (pointerShow)
                        reservationShowTimer.restart();
                    else if (reservationActive)
                        reservationHideTimer.restart();
                }

                onPointerShowChanged: syncReservation()
                onInteractionHoldChanged: syncReservation()
                onAutoHideEnabledChanged: syncReservation()
                onPushWindowsWhenShownChanged: syncReservation()
                Component.onCompleted: {
                    bar.windowProbe = barRoot;
                    syncReservation();
                }

                Timer {
                    id: reservationShowTimer
                    interval: Appearance.animationsEnabled ? Appearance.animation.elementMoveEnter.duration : 1
                    onTriggered: {
                        if (barRoot.autoHideEnabled && barRoot.pushWindowsWhenShown && (barRoot.pointerShow || barRoot.interactionHold))
                            barRoot.reservationActive = true;
                    }
                }

                Timer {
                    id: reservationHideTimer
                    interval: Appearance.animationsEnabled ? Appearance.animation.elementMoveEnter.duration : 1
                    onTriggered: {
                        if (!barRoot.pointerShow && !barRoot.interactionHold)
                            barRoot.reservationActive = false;
                    }
                }

                Connections {
                    target: GlobalStates
                    function onActiveContextMenuCountChanged(): void {
                        if (GlobalStates.activeContextMenuCount <= 0)
                            barRoot.contextMenuHold = false;
                        else if (barRoot.pointerShow)
                            barRoot.contextMenuHold = true;
                    }
                    function onSidebarLeftOpenChanged(): void {
                        if (!GlobalStates.sidebarLeftOpen)
                            barRoot.leftSidebarHold = false;
                        else if (barRoot.pointerShow && GlobalStates.sidebarLeftPresentationOutput === barRoot.outputName)
                            barRoot.leftSidebarHold = true;
                    }
                    function onSidebarRightOpenChanged(): void {
                        if (!GlobalStates.sidebarRightOpen)
                            barRoot.rightSidebarHold = false;
                        else if (barRoot.pointerShow && GlobalStates.sidebarRightPresentationOutput === barRoot.outputName)
                            barRoot.rightSidebarHold = true;
                    }
                    function onMediaControlsOpenChanged(): void {
                        if (!GlobalStates.mediaControlsOpen)
                            barRoot.mediaControlsHold = false;
                        else if (barRoot.pointerShow)
                            barRoot.mediaControlsHold = true;
                    }
                    function onControlPanelOpenChanged(): void {
                        if (!GlobalStates.controlPanelOpen)
                            barRoot.controlPanelHold = false;
                        else if (barRoot.pointerShow)
                            barRoot.controlPanelHold = true;
                    }
                }

                Item {
                    id: autoHideEdgeRegion
                    // A fixed screen-edge strip so a translated-away bar can
                    // still be revealed. Horizontal bars reserve a horizontal
                    // strip, vertical bars a vertical one.
                    readonly property real strip: Math.max(1, Config.options?.bar?.autoHide?.hoverRegionWidth ?? 2) + barRoot.layerGap
                    x: barRoot.vertical ? (barRoot.edge === "right" ? parent.width - width : 0) : 0
                    y: barRoot.vertical ? 0 : (barRoot.edge === "bottom" ? parent.height - height : 0)
                    width: barRoot.vertical ? (barRoot.autoHideEnabled ? strip : 0) : parent.width
                    height: barRoot.vertical ? parent.height : (barRoot.autoHideEnabled ? strip : 0)
                }

                // Positioning
                anchors {
                    top: barRoot.anchoredTop
                    bottom: barRoot.anchoredBottom
                    left: barRoot.anchoredLeft
                    right: barRoot.anchoredRight
                }

                // B9.5: outer margins split into the normal axis (edgeMargin)
                // and the along-bar axis (sideMargin). The layer gap and the
                // dead-pixel workaround still ride on top of those.
                margins {
                    top: barRoot.windowMargins.top
                    bottom: barRoot.windowMargins.bottom
                    left: barRoot.windowMargins.left
                    right: barRoot.windowMargins.right
                }

                MouseArea {
                    id: hoverRegion
                    hoverEnabled: true
                    anchors {
                        fill: parent
                        rightMargin: (barRoot.deadPixel && barRoot.anchoredRight) * 1
                        bottomMargin: (barRoot.deadPixel && barRoot.anchoredBottom) * 1
                    }

                    Item {
                        id: hoverMaskRegion
                        anchors {
                            fill: contentLoader
                            topMargin: barRoot.vertical ? 0 : -Config.options.bar.autoHide.hoverRegionWidth
                            bottomMargin: barRoot.vertical ? 0 : -Config.options.bar.autoHide.hoverRegionWidth
                            leftMargin: barRoot.vertical ? -Config.options.bar.autoHide.hoverRegionWidth : 0
                            rightMargin: barRoot.vertical ? -Config.options.bar.autoHide.hoverRegionWidth : 0
                        }
                    }

                    RoundCorner {
                        id: leftPillCorner
                        visible: !barRoot.vertical && barRoot.centerOnly && showBarBackground && Config.options.bar.m3.cornerStyle === 0
                        x: barRoot.centerPillX - implicitSize
                        implicitSize: Appearance.rounding.screenRounding
                        color: Appearance.colors.colLayer0
                        corner: RoundCorner.CornerEnum.TopRight

                        states: State {
                            name: "bottom"
                            when: barRoot.edge === "bottom"
                            AnchorChanges {
                                target: leftPillCorner
                                anchors.top: undefined
                                anchors.bottom: contentLoader.bottom
                            }
                            PropertyChanges {
                                target: leftPillCorner
                                corner: RoundCorner.CornerEnum.BottomRight
                            }
                        }
                        AnchorChanges {
                            target: leftPillCorner
                            anchors.top: contentLoader.top
                            anchors.bottom: undefined
                        }
                    }

                    Loader {
                        id: contentLoader
                        // One content instance only: the orientation picks the
                        // component; geometry is explicit so switching edges
                        // cannot leave a stale anchor behind.
                        readonly property real slideOffset: barRoot.autoHideEnabled ? (!barRoot.mustShow ? -barRoot.thickness : barRoot.layerGap) : 0
                        // Explicit geometry, never conditional anchors: QML does
                        // not clear an anchor when the binding yields
                        // `undefined`, so a top->left->top switch used to leave
                        // the content 2519 wide / 1440 tall inside the window.
                        x: barRoot.vertical ? ((barRoot.edge === "right" ? parent.width - width + slideOffset : slideOffset) + (barRoot.edge === "right" && barRoot.deadPixel ? -1 : 0)) : 0
                        y: barRoot.vertical ? 0 : ((barRoot.edge === "bottom" ? parent.height - height + slideOffset : slideOffset) + (barRoot.edge === "bottom" && barRoot.deadPixel ? -1 : 0))
                        width: barRoot.vertical ? Appearance.sizes.verticalBarWidth : parent.width
                        height: barRoot.vertical ? parent.height : Appearance.sizes.barHeight
                        Behavior on x {
                            animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                        }
                        Behavior on y {
                            animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                        }
                        sourceComponent: barRoot.vertical ? verticalContent : horizontalContent

                        Component {
                            id: horizontalContent
                            BarContent {}
                        }

                        Component {
                            id: verticalContent
                            VerticalBarContent {}
                        }
                    }

                    RoundCorner {
                        id: rightPillCorner
                        visible: !barRoot.vertical && barRoot.centerOnly && showBarBackground && Config.options.bar.m3.cornerStyle === 0
                        x: barRoot.centerPillX + barRoot.centerPillWidth
                        implicitSize: Appearance.rounding.screenRounding
                        color: Appearance.colors.colLayer0
                        corner: RoundCorner.CornerEnum.TopLeft

                        states: State {
                            name: "bottom"
                            when: barRoot.edge === "bottom"
                            AnchorChanges {
                                target: rightPillCorner
                                anchors.top: undefined
                                anchors.bottom: contentLoader.bottom
                            }
                            PropertyChanges {
                                target: rightPillCorner
                                corner: RoundCorner.CornerEnum.BottomLeft
                            }
                        }
                        AnchorChanges {
                            target: rightPillCorner
                            anchors.top: contentLoader.top
                            anchors.bottom: undefined
                        }
                    }

                    // B9.4 vertical pill bridge: the Hug centre pill meets the
                    // screen edge at the top and bottom instead of left/right.
                    RoundCorner {
                        id: topPillCorner
                        visible: barRoot.vertical && barRoot.centerOnly && showBarBackground && Config.options.bar.m3.cornerStyle === 0
                        y: barRoot.centerPillY - implicitSize
                        x: contentLoader.x + (barRoot.edge === "right" ? -implicitSize : contentLoader.width)
                        implicitSize: Appearance.rounding.screenRounding
                        color: Appearance.colors.colLayer0
                        corner: barRoot.edge === "right" ? RoundCorner.CornerEnum.BottomRight : RoundCorner.CornerEnum.BottomLeft
                    }

                    RoundCorner {
                        id: bottomPillCorner
                        visible: barRoot.vertical && barRoot.centerOnly && showBarBackground && Config.options.bar.m3.cornerStyle === 0
                        y: barRoot.centerPillY + (barRoot.barContent?.centerPillHeight ?? 0)
                        x: contentLoader.x + (barRoot.edge === "right" ? -implicitSize : contentLoader.width)
                        implicitSize: Appearance.rounding.screenRounding
                        color: Appearance.colors.colLayer0
                        corner: barRoot.edge === "right" ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.TopLeft
                    }

                    // Round decorators: the strip that fuses the bar into the
                    // screen corner. Horizontal bars keep it below/above the
                    // bar; vertical bars place it on the interior side.
                    Loader {
                        id: roundDecorators
                        x: barRoot.vertical ? (barRoot.edge === "right" ? contentLoader.x - width : contentLoader.x + contentLoader.width) : 0
                        y: barRoot.vertical ? contentLoader.y : (barRoot.edge === "bottom" ? contentLoader.y - height : contentLoader.y + contentLoader.height)
                        width: barRoot.vertical ? Appearance.rounding.screenRounding : contentLoader.width
                        height: barRoot.vertical ? contentLoader.height : Appearance.rounding.screenRounding
                        active: (showBarBackground && Config.options.bar.m3.cornerStyle === 0 && !barRoot.centerOnly) || Config.options.bar.m3.cornerStyle === 4

                        sourceComponent: Item {
                            implicitWidth: Appearance.rounding.screenRounding
                            implicitHeight: Appearance.rounding.screenRounding
                            readonly property color decoratorColor: (Config.options.bar.m3.cornerStyle === 4 || showBarBackground) ? Appearance.colors.colLayer0 : "transparent"

                            RoundCorner {
                                id: startCorner
                                visible: Config.options.bar.m3.cornerStyle === 0 || barRoot.leftLaneCount > 0
                                x: 0
                                y: barRoot.vertical ? 0 : (barRoot.edge === "bottom" ? parent.height - height : 0)
                                width: implicitSize
                                height: implicitSize
                                implicitSize: Appearance.rounding.screenRounding
                                color: parent.decoratorColor

                                corner: barRoot.vertical ? (barRoot.edge === "right" ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.TopLeft) : (barRoot.edge === "bottom" ? RoundCorner.CornerEnum.BottomLeft : RoundCorner.CornerEnum.TopLeft)
                            }
                            RoundCorner {
                                id: endCorner
                                visible: Config.options.bar.m3.cornerStyle === 0 || barRoot.rightLaneCount > 0
                                x: barRoot.vertical ? parent.width - width : 0
                                y: barRoot.vertical ? parent.height - height : (barRoot.edge === "bottom" ? 0 : parent.height - height)
                                width: implicitSize
                                height: implicitSize
                                implicitSize: Appearance.rounding.screenRounding
                                color: parent.decoratorColor

                                corner: barRoot.vertical ? (barRoot.edge === "right" ? RoundCorner.CornerEnum.BottomRight : RoundCorner.CornerEnum.BottomLeft) : (barRoot.edge === "bottom" ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.BottomRight)
                            }
                        }
                    }
                }
            }
        }
    }
}

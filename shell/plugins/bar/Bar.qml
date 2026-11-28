pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.services
import qs.commons
import qs.ui
import "../../commons/BarGeometry.js" as BarGeometry
import "BarStyle.js" as BarStyle

// Separate Material 3 bar selected by `bar.appearanceStyle === "m3"`.
// It replaces modules/ii/bar/Bar.qml entirely while active (see ShellIiPanelsImpl),
// so it deliberately registers no IPC target and no GlobalShortcut: "bar" is
// owned by shell.qml and the shortcuts by modules/ii/bar/Bar.qml. Toggling
// GlobalStates.barOpen through either still drives this bar.
Scope {
    id: bar
    // Probe seam (scripts/dev/probe-bar.sh window phase): the last screen's
    // PanelWindow registers itself here so the runtime probe can read the
    // evaluated window/content geometry (D4e: multi-bar registers per window;
    // the probe takes the newest).
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

    // D4e multi-bar (dux ShellCore pattern): the rebuild signature decides
    // WHICH entries own windows; only identity/routing changes rebuild
    // (style edits flow through the live barConfig bindings below).
    readonly property string layoutState: PersonalizationConfig.barLayoutStateJson()

    // Horizontal windows must claim their exclusive zones before vertical
    // ones layout against them (dux ShellCore order): vertical hosts wait
    // until every horizontal host has windows.
    readonly property int horizontalWanted: JSON.parse(bar.layoutState).filter(entry => entry.enabled && entry.position !== "left" && entry.position !== "right").length
    property int horizontalReady: 0
    onHorizontalWantedChanged: bar.syncHorizontalReady()

    function syncHorizontalReady(): void {
        let ready = 0;
        for (let index = 0; index < hostRepeater.count; index += 1) {
            const delegate = hostRepeater.itemAt(index);
            if (delegate && delegate.hostReady && !delegate.entryVertical)
                ready += 1;
        }
        bar.horizontalReady = ready;
    }

    // Probe seam (scripts/dev/probe-bar.sh d4e): the instantiated host
    // topology — entry ids, routing and window counts.
    function probeHostReport(): string {
        const out = [];
        for (let index = 0; index < hostRepeater.count; index += 1) {
            const delegate = hostRepeater.itemAt(index);
            if (!delegate)
                continue;
            out.push({
                "id": delegate.modelData ? delegate.modelData.id : "",
                "enabled": delegate.modelData ? delegate.modelData.enabled === true : false,
                "position": delegate.modelData ? delegate.modelData.position : "",
                "windows": delegate.windowCount
            });
        }
        return JSON.stringify(out);
    }

    // Probe seam: a specific entry's first window (per-bar content checks).
    function probeHostWindow(id): var {
        for (let index = 0; index < hostRepeater.count; index += 1) {
            const delegate = hostRepeater.itemAt(index);
            if (delegate && delegate.modelData && delegate.modelData.id === id)
                return delegate.probeWindow ?? null;
        }
        return null;
    }

    // The Repeater needs an Item parent to materialize delegates (Scope is
    // non-visual); the hosts multiply layer-shell windows, never visual
    // children, so a bare container is enough.
    Item {
        id: hostContainer

        Repeater {
            id: hostRepeater

            model: JSON.parse(bar.layoutState)

            delegate: Item {
                id: barHost

                required property var modelData
                // Live entry binding: re-resolves whenever the store reassigns
                // (every mutation clone), so the window tree tracks its own
                // entry's axes without touching the settings-facing views.
                readonly property var barConfig: PersonalizationConfig.barConfigById(barHost.modelData.id)
                readonly property bool entryVertical: barHost.modelData.position === "left" || barHost.modelData.position === "right"
                // Windows exist only while the entry is enabled and the unit
                // gates pass (barOpen/screenLocked stay unit-global; per-entry
                // visibility is the `enabled` flag; vertical hosts wait for
                // every horizontal host — dux exclusive-zone claim order).
                readonly property bool windowsActive: barHost.modelData.enabled === true && GlobalStates.barOpen && !GlobalStates.screenLocked && (!barHost.entryVertical || bar.horizontalReady >= bar.horizontalWanted)
                // A host counts as ready once its window tree instantiated (the
                // same item-level readiness dux ShellCore counts).
                readonly property bool hostReady: hostWindows.status === Loader.Ready
                readonly property int windowCount: hostWindows.item ? hostWindows.item.windowCount : 0
                // Probe seam: this host's first window (content inspection
                // per entry; the Scope-level windowProbe takes the newest
                // registration, which follows the signature sort, not us).
                property var probeWindow: null

                onHostReadyChanged: bar.syncHorizontalReady()
                Component.onDestruction: bar.syncHorizontalReady()

                // Declared INSIDE the delegate: the body reads the
                // delegate-local barHost id — ids resolve lexically at the
                // declaration scope, never the instantiation site.
                Component {
                    id: hostWindowsComponent

                    Item {
                        id: barWindows

                        readonly property int windowCount: screenVariants.instances.length

                        Variants {
                            id: screenVariants

                            // For each monitor of THIS entry (the per-bar
                            // screenList; empty = every screen, no match falls
                            // back to every screen).
                            model: {
                                const screens = Quickshell.screens;
                                const list = barHost.barConfig?.axes?.screenList ?? [];
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

                                active: true
                                required property ShellScreen modelData
                                component: PanelWindow { // Bar window
                                    id: barRoot
                                    screen: barLoader.modelData

                                    // D4e: this window's entry (live binding; the defaults table
                                    // keeps geometry sane through a signature reshuffle).
                                    readonly property var barConfig: barHost.barConfig
                                    readonly property var axes: barRoot.barConfig?.axes ?? BarDefaults.DEFAULTS
                                    readonly property var styleContext: BarStyle.resolve(barRoot.axes, {
                                        gapsOut: Config.options.bar.m3.gapsOut,
                                        shellRadius: barRoot.shellRadius,
                                        centerOnly: barRoot.centerOnly
                                    })
                                    readonly property bool showBarBackground: barRoot.styleContext.backplate

                                    // D4c bar shell radius axis (see BarContent.shellRadius);
                                    // every screen-corner decorator below reads this alias.
                                    readonly property real shellRadius: PersonalizationConfig.resolvedBarShellRadius(Appearance.rounding.screenRounding, barRoot.axes)
                                    // D4c/D4f percent length + sideMargin (-1 Auto -> gapsOut on floating backplate).
                                    readonly property real sideMarginPx: {
                                        const percent = barRoot.axes.sideMarginPercent;
                                        if (percent > 0) {
                                            const span = barRoot.vertical ? (barRoot.screen?.height ?? 0) : (barRoot.screen?.width ?? 0);
                                            if (span > 0)
                                                return Math.round(span * percent / 100);
                                        }
                                        return PersonalizationConfig.resolvedBarSideMargin(barRoot.axes);
                                    }

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
                                    // D4d behavior axes (bar-config.md D4d). autoHideDelay is the
                                    // hide grace after the pointer leaves (0 = the pre-D4d
                                    // immediate slide); autoHideStrict (D4d-2) unpins the
                                    // popup-class holds (context menu, media popup) — the sidebar
                                    // holds stay pinned, those surfaces grow from the bar edge
                                    // geometrically; hideOnFullscreen raises the bar to Overlay
                                    // and forces the autoHide channel while a fullscreen toplevel
                                    // covers the output (default off = the pre-D4d Top layer).
                                    readonly property bool strictHide: barRoot.axes.autoHideStrict === true
                                    readonly property real hideDelay: barRoot.axes.autoHideDelay ?? 0
                                    readonly property bool hideOnFullscreenAxis: barRoot.axes.hideOnFullscreen === true
                                    // D4d click-through: the input mask shrinks to the three lane
                                    // rects (clicks on bar gaps fall through to the windows
                                    // below). Edge-scroll areas and scroll hints go dead in this
                                    // mode — registered boundary, they live in the gaps.
                                    readonly property bool clickThroughEnabled: barRoot.axes.clickThrough === true
                                    // D4d lane mask surfaces (BarContent/VerticalBarContent).
                                    readonly property var laneMaskLeft: barRoot.barContent ? barRoot.barContent.laneMaskLeft : null
                                    readonly property var laneMaskMiddle: barRoot.barContent ? barRoot.barContent.laneMaskMiddle : null
                                    readonly property var laneMaskRight: barRoot.barContent ? barRoot.barContent.laneMaskRight : null
                                    readonly property bool fullscreenAutoHide: barRoot.hideOnFullscreenAxis && CompositorDriver.available && CompositorDriver.fullscreenToplevelOnScreen(barRoot.outputName)
                                    // Reveal grace: while held, the slide-out stays parked even
                                    // though mustShow dropped (the pointer may come right back).
                                    // Initial false: changed handlers do not fire for initial
                                    // binding values, so a boot-time autoHide config must find
                                    // the bar already in the hidden half of the state.
                                    property bool hideHold: false
                                    // dux gapEnterSuppressed lineage (DBarBody): with
                                    // click-through the hidden bar's mask is the full band but
                                    // the revealed bar's mask is lanes-only, so a pointer over a
                                    // gap is unknowable. An enter only reveals once it reaches
                                    // the edge strip; anything else (including the spurious
                                    // enter generated by the mask expanding under a resting
                                    // pointer) keeps the bar hidden.
                                    property bool gapEnterSuppressed: false
                                    readonly property bool autoHideEnabled: (barRoot.axes.autoHide === true) || barRoot.fullscreenAutoHide
                                    readonly property bool pushWindowsWhenShown: Config.options?.bar?.autoHide?.pushWindows ?? false
                                    readonly property bool overviewOwnsEdge: GlobalStates.overviewOpen || CompositorDriver.inOverview
                                    readonly property string outputName: barRoot.screen?.name ?? ""
                                    readonly property bool materialHug: barRoot.styleContext.isLaneHug
                                    readonly property bool panelStyle: barRoot.styleContext.isSquare
                                    // B9.4: `edge` is the window-anchor truth; `vertical` is the
                                    // same fact in the form every ported widget already reads.
                                    readonly property string edge: barRoot.axes.position
                                    readonly property bool vertical: barRoot.edge === "left" || barRoot.edge === "right"
                                    readonly property bool deadPixel: Config.options.interactions.deadPixelWorkaround.enable
                                    readonly property bool anchoredTop: barRoot.edge === "top" || barRoot.vertical
                                    readonly property bool anchoredBottom: barRoot.edge === "bottom" || barRoot.vertical
                                    readonly property bool anchoredLeft: barRoot.edge === "left" || !barRoot.vertical
                                    readonly property bool anchoredRight: barRoot.edge === "right" || !barRoot.vertical
                                    readonly property real thickness: barRoot.vertical ? PersonalizationConfig.resolvedVerticalBarWidth(barRoot.axes) : PersonalizationConfig.resolvedBarHeight(barRoot.axes)
                                    // B9.5/D4f outer margins: edgeMargin 0 = flush, >0 = floating.
                                    readonly property real edgeMargin: barRoot.axes.edgeMargin
                                    readonly property real sideMargin: barRoot.sideMarginPx
                                    // The margins and the reserved exclusive zone share one pure
                                    // implementation (commons/BarGeometry.js) with the probe.
                                    readonly property var windowMargins: BarGeometry.margins(barRoot.edge, barRoot.vertical, barRoot.edgeMargin, barRoot.sideMarginPx, barRoot.autoHideEnabled, barRoot.deadPixel)
                                    readonly property real shownExclusiveZone: BarGeometry.exclusiveZone(barRoot.vertical, barRoot.axes.barThickness, barRoot.axes.verticalThickness, barRoot.styleContext.boostExtra, barRoot.edgeMargin)
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
                                    readonly property bool pointerShow: !overviewOwnsEdge && hoverRegion.containsMouse && !barRoot.gapEnterSuppressed
                                    property bool mustShow: pointerShow || superShow || interactionHold
                                    property bool reservationActive: false
                                    onMustShowChanged: {
                                        if (barRoot.mustShow) {
                                            hideHoldTimer.stop();
                                            barRoot.hideHold = true;
                                            // dux revealSettle lineage: input-mask updates lag the
                                            // slide transition, generating spurious enter/leave
                                            // pairs; hides wait until the mask settles.
                                            if (barRoot.clickThroughEnabled && barRoot.autoHideEnabled)
                                                revealSettle.restart();
                                        } else if (revealSettle.running) {
                                            // Deferred: re-evaluated when the settle fires.
                                        } else if (barRoot.autoHideEnabled && barRoot.hideDelay > 0) {
                                            hideHoldTimer.restart();
                                        } else {
                                            barRoot.hideHold = false;
                                        }
                                    }
                                    onAutoHideEnabledChanged: {
                                        if (barRoot.autoHideEnabled && !barRoot.mustShow && barRoot.hideDelay > 0)
                                            hideHoldTimer.restart();
                                        else
                                            barRoot.hideHold = barRoot.mustShow || !barRoot.autoHideEnabled;
                                        syncReservation();
                                    }

                                    // dux inEdgeStrip lineage: the reveal strip is a generous
                                    // slice of the band at the screen edge (never just the 2px
                                    // hover region), so a click-through reveal needs a real
                                    // edge approach, not a stray enter over a gap.
                                    function inEdgeStrip(): bool {
                                        const vertical = barRoot.vertical;
                                        const band = vertical ? barRoot.width : barRoot.height;
                                        const strip = Math.max(8, band * 0.15);
                                        const x = hoverRegion.mouseX;
                                        const y = hoverRegion.mouseY;
                                        switch (barRoot.edge) {
                                        case "bottom":
                                            return y >= band - strip;
                                        case "left":
                                            return x <= strip;
                                        case "right":
                                            return x >= band - strip;
                                        default:
                                            return y <= strip;
                                        }
                                    }

                                    Timer {
                                        id: hideHoldTimer
                                        interval: Math.max(0, barRoot.hideDelay)
                                        repeat: false
                                        onTriggered: barRoot.hideHold = false
                                    }

                                    Timer {
                                        id: revealSettle
                                        interval: 600
                                        repeat: false
                                        onTriggered: {
                                            if (!barRoot.mustShow) {
                                                if (barRoot.autoHideEnabled && barRoot.hideDelay > 0)
                                                    hideHoldTimer.restart();
                                                else
                                                    barRoot.hideHold = false;
                                            }
                                        }
                                    }

                                    exclusionMode: ExclusionMode.Ignore
                                    exclusiveZone: !autoHideEnabled ? shownExclusiveZone : (pushWindowsWhenShown && reservationActive ? shownExclusiveZone : 0)
                                    WlrLayershell.namespace: "quickshell:bar"
                                    // Upstream raised the bar to Overlay only while a Hyprland
                                    // special workspace sat over a fullscreen window. Niri has no
                                    // special workspace, so the bar stays on Top and fullscreen
                                    // windows cover it, which is what iNiR's own bar does too.
                                    // D4d exception: hideOnFullscreen deliberately raises the
                                    // bar to Overlay so the reveal channel stays alive above a
                                    // fullscreen toplevel (default off keeps the Top layer).
                                    WlrLayershell.layer: barRoot.fullscreenAutoHide ? WlrLayer.Overlay : WlrLayer.Top
                                    implicitHeight: barRoot.vertical ? 0 : (barRoot.thickness + barRoot.shellRadius)
                                    implicitWidth: barRoot.vertical ? (barRoot.thickness + barRoot.shellRadius) : 0
                                    // When Overlay-layer, bar shares a layer with the screen-corner click zones (ScreenCorners.qml)
                                    // and same-layer overlap is resolved by stacking, not layer priority - bar was winning and
                                    // swallowing the tiny corner-open hit rects. Carve them out of the bar's own mask so clicks
                                    // reach the corners underneath. Only relevant on the edge the bar and corners share.
                                    // The corner-open cutout only mattered while the bar was raised
                                    // to Overlay and shared a layer with the screen-corner click
                                    // zones. On Top layer the corners are already above it.
                                    property int cornerOpenCutHeight: (autoHideEnabled && !barRoot.vertical) ? Math.max(1, Config.options?.bar?.autoHide?.hoverRegionWidth ?? 2) : 0
                                    mask: Region {
                                        // D4d click-through: the full-bar hit region is replaced
                                        // by the three lane rects (empty lanes collapse away), so
                                        // clicks on the bar's gaps fall through to the windows
                                        // below — dux section masking lineage. The edge strip
                                        // stays so a hidden bar can still be revealed.
                                        Region {
                                            item: barRoot.clickThroughEnabled ? null : hoverMaskRegion
                                        }
                                        Region {
                                            item: barRoot.clickThroughEnabled ? barRoot.laneMaskLeft : null
                                        }
                                        Region {
                                            item: barRoot.clickThroughEnabled ? barRoot.laneMaskMiddle : null
                                        }
                                        Region {
                                            item: barRoot.clickThroughEnabled ? barRoot.laneMaskRight : null
                                        }
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
                                        else if (reservationActive && !barRoot.hideHold)
                                            reservationHideTimer.restart();
                                    }

                                    onPointerShowChanged: syncReservation()
                                    onInteractionHoldChanged: syncReservation()
                                    onPushWindowsWhenShownChanged: syncReservation()
                                    Component.onCompleted: {
                                        barHost.probeWindow = barRoot;
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
                                            if (!barRoot.pointerShow && !barRoot.interactionHold && !barRoot.hideHold)
                                                barRoot.reservationActive = false;
                                        }
                                    }

                                    Connections {
                                        target: GlobalStates
                                        function onActiveContextMenuCountChanged(): void {
                                            if (GlobalStates.activeContextMenuCount <= 0)
                                                barRoot.contextMenuHold = false;
                                            else if (barRoot.pointerShow && !barRoot.strictHide)
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
                                            else if (barRoot.pointerShow && !barRoot.strictHide)
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
                                        readonly property real strip: Math.max(1, Config.options?.bar?.autoHide?.hoverRegionWidth ?? 2)
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

                                        onContainsMouseChanged: {
                                            // dux gapEnterSuppressed lineage: see barRoot.gapEnterSuppressed.
                                            if (!containsMouse)
                                                barRoot.gapEnterSuppressed = false;
                                            else if (barRoot.clickThroughEnabled && barRoot.autoHideEnabled && !barRoot.mustShow)
                                                barRoot.gapEnterSuppressed = !barRoot.inEdgeStrip();
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
                                            visible: !barRoot.vertical && barRoot.styleContext.showCenterPillCorners
                                            x: barRoot.centerPillX - implicitSize
                                            implicitSize: barRoot.shellRadius
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
                                            // D4d: hideHold parks the slide-out through the
                                            // autoHideDelay grace.
                                            readonly property real slideOffset: barRoot.autoHideEnabled && !barRoot.mustShow && !barRoot.hideHold ? -barRoot.thickness : 0
                                            // Explicit geometry, never conditional anchors: QML does
                                            // not clear an anchor when the binding yields
                                            // `undefined`, so a top->left->top switch used to leave
                                            // the content 2519 wide / 1440 tall inside the window.
                                            x: barRoot.vertical ? ((barRoot.edge === "right" ? parent.width - width + slideOffset : slideOffset) + (barRoot.edge === "right" && barRoot.deadPixel ? -1 : 0)) : 0
                                            y: barRoot.vertical ? 0 : ((barRoot.edge === "bottom" ? parent.height - height + slideOffset : slideOffset) + (barRoot.edge === "bottom" && barRoot.deadPixel ? -1 : 0))
                                            width: barRoot.vertical ? barRoot.thickness : parent.width
                                            height: barRoot.vertical ? parent.height : barRoot.thickness
                                            Behavior on x {
                                                animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                                            }
                                            Behavior on y {
                                                animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                                            }
                                            sourceComponent: barRoot.vertical ? verticalContent : horizontalContent

                                            Component {
                                                id: horizontalContent
                                                BarContent {
                                                    barConfig: barRoot.barConfig
                                                }
                                            }

                                            Component {
                                                id: verticalContent
                                                VerticalBarContent {
                                                    barConfig: barRoot.barConfig
                                                }
                                            }
                                        }

                                        RoundCorner {
                                            id: rightPillCorner
                                            visible: !barRoot.vertical && barRoot.styleContext.showCenterPillCorners
                                            x: barRoot.centerPillX + barRoot.centerPillWidth
                                            implicitSize: barRoot.shellRadius
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
                                            visible: barRoot.vertical && barRoot.styleContext.showCenterPillCorners
                                            y: barRoot.centerPillY - implicitSize
                                            x: contentLoader.x + (barRoot.edge === "right" ? -implicitSize : contentLoader.width)
                                            implicitSize: barRoot.shellRadius
                                            color: Appearance.colors.colLayer0
                                            corner: barRoot.edge === "right" ? RoundCorner.CornerEnum.BottomRight : RoundCorner.CornerEnum.BottomLeft
                                        }

                                        RoundCorner {
                                            id: bottomPillCorner
                                            visible: barRoot.vertical && barRoot.styleContext.showCenterPillCorners
                                            y: barRoot.centerPillY + (barRoot.barContent?.centerPillHeight ?? 0)
                                            x: contentLoader.x + (barRoot.edge === "right" ? -implicitSize : contentLoader.width)
                                            implicitSize: barRoot.shellRadius
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
                                            width: barRoot.vertical ? barRoot.shellRadius : contentLoader.width
                                            height: barRoot.vertical ? contentLoader.height : barRoot.shellRadius
                                            active: barRoot.styleContext.showScreenDecorators

                                            sourceComponent: Item {
                                                implicitWidth: barRoot.shellRadius
                                                implicitHeight: barRoot.shellRadius
                                                readonly property color decoratorColor: barRoot.styleContext.decoratorUsesBackplate ? Appearance.colors.colLayer0 : "transparent"

                                                RoundCorner {
                                                    id: startCorner
                                                    visible: barRoot.styleContext.showStartDecorator || barRoot.leftLaneCount > 0
                                                    x: 0
                                                    y: barRoot.vertical ? 0 : (barRoot.edge === "bottom" ? parent.height - height : 0)
                                                    width: implicitSize
                                                    height: implicitSize
                                                    implicitSize: barRoot.shellRadius
                                                    color: parent.decoratorColor

                                                    corner: barRoot.vertical ? (barRoot.edge === "right" ? RoundCorner.CornerEnum.TopRight : RoundCorner.CornerEnum.TopLeft) : (barRoot.edge === "bottom" ? RoundCorner.CornerEnum.BottomLeft : RoundCorner.CornerEnum.TopLeft)
                                                }
                                                RoundCorner {
                                                    id: endCorner
                                                    visible: barRoot.styleContext.showEndDecorator || barRoot.rightLaneCount > 0
                                                    x: barRoot.vertical ? parent.width - width : 0
                                                    y: barRoot.vertical ? parent.height - height : (barRoot.edge === "bottom" ? 0 : parent.height - height)
                                                    width: implicitSize
                                                    height: implicitSize
                                                    implicitSize: barRoot.shellRadius
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
                }

                Loader {
                    id: hostWindows

                    active: barHost.windowsActive
                    onStatusChanged: bar.syncHorizontalReady()
                    sourceComponent: hostWindowsComponent
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import Quickshell
import Quickshell.Io
import Quickshell.Services.Mpris
import Quickshell.Services.Pipewire
import Quickshell.Wayland
import qs.services
import qs.commons
import qs.ui
import "../../clock"
import "../../media"
import "../../volume"
import "../../hub"
import "../../tools"
import "../recording"
import "../long"
import "../.."

Variants {
    id: styleSurface

    property bool detached: false
    property bool elongated: false
    readonly property bool splitRecording: detached && !elongated
    property int edgeMargin: 0
    property int maxPillRadius: 24
    property bool showAttachedEdgeCurves: !detached

    signal avatarEditRequested(var screen)

    function targetInstance() {
        if (instances.length === 0)
            return null;

        const outputName = String(CompositorDriver.currentOutput || "");
        if (outputName.length > 0) {
            for (let index = 0; index < instances.length; ++index) {
                const instance = instances[index];
                if (instance && instance.screen && instance.screen.name === outputName)
                    return instance;
            }
        }
        return instances[0];
    }

    function invoke(methodName) {
        const instance = targetInstance();
        if (!instance || typeof instance[methodName] !== "function")
            return "ISLAND_UNAVAILABLE";

        return instance[methodName]();
    }

    function cancelRecord(): string {
        return invoke("cancelRecord");
    }

    function closeAllOthers(): string {
        return invoke("closeAllOthers");
    }

    function hub(): string {
        return invoke("hub");
    }

    function dashboard(): string {
        return invoke("dashboard");
    }

    function lyrics(): string {
        return invoke("lyrics");
    }

    function tools(): string {
        return invoke("tools");
    }

    model: Quickshell.screens

    PanelWindow {
        id: islandWindow

        required property var modelData
        readonly property string edge: PersonalizationConfig.islandPosition
        readonly property bool horizontalEdge: edge === "top" || edge === "bottom"
        readonly property bool topEdge: edge === "top"
        readonly property bool bottomEdge: edge === "bottom"
        readonly property bool leftEdge: edge === "left"
        readonly property bool rightEdge: edge === "right"
        readonly property bool sidebarHasPriority: WidgetState.sidebarHasPriority(screen ? screen.name : "")
        property int edgeCurveAlong: styleSurface.showAttachedEdgeCurves ? 8 : 0
        property int edgeCurveDepth: styleSurface.showAttachedEdgeCurves ? 14 : 0
        property real edgeCurveSideControl: 0.58
        property real edgeCurveOuterControl: 0.42

        function cancelRecord(): string {
            return "RECORD_CANCELLED";
        }

        function closeAllOthers(): string {
            hoverIntent.cancel();
            root.showHub = false;
            root.showLyrics = false;
            root.showTools = false;
            root.expanded = false;
            root.hoverOpened = false;
            return "OTHERS_CLOSED";
        }

        function hub(): string {
            if (root.showHub) {
                root.showHub = false;
                return "HUB_CLOSED";
            }
            closeAllOthers();
            root.showHub = true;
            return "HUB_OPENED";
        }

        function dashboard(): string {
            if (root.showHub && root.hubTabIndex === 0) {
                root.showHub = false;
                return "DASHBOARD_CLOSED";
            }
            closeAllOthers();
            root.hubTabIndex = 0;
            root.showHub = true;
            return "DASHBOARD_OPENED";
        }

        function lyrics(): string {
            if (root.showLyrics) {
                root.showLyrics = false;
                return "LYRICS_CLOSED";
            }
            closeAllOthers();
            root.showLyrics = true;
            return "LYRICS_OPENED";
        }

        function tools(): string {
            if (root.showTools) {
                root.showTools = false;
                return "TOOLS_CLOSED";
            }
            closeAllOthers();
            root.showHub = false;
            root.showTools = true;
            return "TOOLS_OPENED";
        }

        screen: modelData
        color: "transparent"
        exclusiveZone: -1
        WlrLayershell.namespace: "nyxuri-shell-island"
        // The reservation surface controls floating; Top stays below fullscreen.
        WlrLayershell.layer: WlrLayer.Top
        WlrLayershell.exclusionMode: ExclusionMode.Ignore
        // On-demand focus lets desktop clicks leave the island and clicks on
        // the island focus it again. Hover previews never request keyboard input.
        WlrLayershell.keyboardFocus: root.keyboardInteractionActive && !islandWindow.sidebarHasPriority
                                     ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

        // The interactive surface spans the screen for expansion and animations.
        // Reserve only the resting island thickness on a separately edge-anchored
        // surface, so opening content never resizes the desktop's work area.
        PanelWindow {
            visible: !PersonalizationConfig.islandOverlay
            screen: islandWindow.screen
            readonly property real reservedThickness: styleSurface.edgeMargin + (styleSurface.elongated
                                                                                 && longFrame.item
                                                                                 ? longFrame.item.thickness :
                                                                                   islandWindow.horizontalEdge
                                                                                   ? horizontalLayout.collapsedHeight :
                                                                                     verticalLayout.collapsedWidth)
            implicitWidth: islandWindow.horizontalEdge ? 1 : reservedThickness
            implicitHeight: islandWindow.horizontalEdge ? reservedThickness : 1
            color: "transparent"
            exclusiveZone: reservedThickness
            WlrLayershell.layer: WlrLayer.Top
            WlrLayershell.namespace: "nyxuri-shell-island-reservation"
            WlrLayershell.exclusionMode: ExclusionMode.Normal
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            anchors {
                top: !islandWindow.bottomEdge
                bottom: !islandWindow.topEdge
                left: !islandWindow.rightEdge
                right: !islandWindow.leftEdge
            }
            mask: Region {}
        }

        PanelWindow {
            // Niri focuses newly mapped OnDemand surfaces. Keep that mapping
            // separate from the visible island so expansion never drops a frame.
            // After a desktop click, neither window requests focus again.
            visible: root.keyboardInteractionActive && !islandWindow.sidebarHasPriority
            screen: islandWindow.screen
            implicitWidth: 1
            implicitHeight: 1
            color: "transparent"
            exclusiveZone: -1
            WlrLayershell.namespace: "nyxuri-shell-island-keyboard"
            WlrLayershell.layer: WlrLayer.Top
            WlrLayershell.exclusionMode: ExclusionMode.Ignore
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
            anchors {
                top: true
                left: true
            }
            mask: Region {}

            Item {
                anchors.fill: parent
                focus: true
                Keys.forwardTo: root.isToolsMode ? [toolsWidget, root] : [root]

                // Shortcuts belong to their receiving window. Mouse interaction
                // focuses the visible island, where HubContent handles them.
                Shortcut {
                    enabled: root.isHubMode
                    sequence: "Tab"
                    onActivated: hub.cycleTab(1)
                }

                Shortcut {
                    enabled: root.isHubMode
                    sequence: "Shift+Tab"
                    onActivated: hub.cycleTab(-1)
                }
            }
        }

        anchors {
            top: true
            bottom: true
            left: true
            right: true
        }

        margins {
            top: 0
        }

        // ============================================================
        // 【视觉 Island bangs 本体】
        // ============================================================
        Item {
            id: maskContainer

            Item {
                id: backgroundVisual
                visible: !styleSurface.elongated && !(styleSurface.splitRecording
                                                      && root.recordingPresentationActive)
                // Give the compositing layer real shadow margins. Enlarging only
                // layer.sourceRect would rescale the island into its original bounds.
                x: -32
                y: -32
                width: parent.width + 64
                height: parent.height + 64
                opacity: root.color.a
                layer.enabled: opacity < 1
                readonly property color surfaceColor: Qt.rgba(root.color.r, root.color.g, root.color.b, 1)

                Item {
                    x: 32
                    y: 32
                    width: parent.width - 64
                    height: parent.height - 64
                    Item {
                        id: shadowSource

                        anchors.fill: parent

                        AttachedEdgeCurve {
                            id: shadowLeftTopCurve

                            visible: styleSurface.showAttachedEdgeCurves
                            edge: islandWindow.edge
                            after: false
                            along: islandWindow.edgeCurveAlong
                            depth: islandWindow.edgeCurveDepth
                            sideControl: islandWindow.edgeCurveSideControl
                            edgeControl: islandWindow.edgeCurveOuterControl
                            fillColor: "black"

                            anchors {
                                right: islandWindow.horizontalEdge ? rootShadow.left :
                                                                       islandWindow.rightEdge
                                                                       ? rootShadow.right : undefined
                                left: islandWindow.leftEdge ? rootShadow.left : undefined
                                bottom: !islandWindow.horizontalEdge ? rootShadow.top :
                                                                         islandWindow.bottomEdge
                                                                         ? rootShadow.bottom : undefined
                                top: islandWindow.topEdge ? rootShadow.top : undefined
                            }
                        }

                        Item {
                            id: rootShadow

                            width: root.width
                            height: root.height
                            state: islandWindow.edge
                            states: [
                                State {
                                    name: "top"

                                    AnchorChanges {
                                        target: rootShadow
                                        anchors.top: shadowSource.top
                                        anchors.bottom: undefined
                                        anchors.left: undefined
                                        anchors.right: undefined
                                        anchors.horizontalCenter: shadowSource.horizontalCenter
                                        anchors.verticalCenter: undefined
                                    }
                                },
                                State {
                                    name: "bottom"

                                    AnchorChanges {
                                        target: rootShadow
                                        anchors.top: undefined
                                        anchors.bottom: shadowSource.bottom
                                        anchors.left: undefined
                                        anchors.right: undefined
                                        anchors.horizontalCenter: shadowSource.horizontalCenter
                                        anchors.verticalCenter: undefined
                                    }
                                },
                                State {
                                    name: "left"

                                    AnchorChanges {
                                        target: rootShadow
                                        anchors.top: undefined
                                        anchors.bottom: undefined
                                        anchors.left: shadowSource.left
                                        anchors.right: undefined
                                        anchors.horizontalCenter: undefined
                                        anchors.verticalCenter: shadowSource.verticalCenter
                                    }
                                },
                                State {
                                    name: "right"

                                    AnchorChanges {
                                        target: rootShadow
                                        anchors.top: undefined
                                        anchors.bottom: undefined
                                        anchors.left: undefined
                                        anchors.right: shadowSource.right
                                        anchors.horizontalCenter: undefined
                                        anchors.verticalCenter: shadowSource.verticalCenter
                                    }
                                }
                            ]

                            SurfaceShape {
                                surfaceColor: "black"
                                topLeftRadius: rootSurface.topLeftRadius
                                topRightRadius: rootSurface.topRightRadius
                                bottomRightRadius: rootSurface.bottomRightRadius
                                bottomLeftRadius: rootSurface.bottomLeftRadius
                                cutoutVisible: rootSurface.cutoutVisible
                                cutoutX: rootSurface.cutoutX
                                cutoutY: rootSurface.cutoutY
                                cutoutWidth: rootSurface.cutoutWidth
                                cutoutHeight: rootSurface.cutoutHeight
                                cutoutRadius: rootSurface.cutoutRadius
                            }
                        }

                        AttachedEdgeCurve {
                            id: shadowRightTopCurve

                            visible: styleSurface.showAttachedEdgeCurves
                            edge: islandWindow.edge
                            after: true
                            along: islandWindow.edgeCurveAlong
                            depth: islandWindow.edgeCurveDepth
                            sideControl: islandWindow.edgeCurveSideControl
                            edgeControl: islandWindow.edgeCurveOuterControl
                            fillColor: "black"

                            anchors {
                                left: islandWindow.leftEdge ? rootShadow.left : (
                                                                    islandWindow.horizontalEdge
                                                                    ? rootShadow.right : undefined)
                                right: islandWindow.rightEdge ? rootShadow.right : undefined
                                top: islandWindow.topEdge ? rootShadow.top : (
                                                                  !islandWindow.horizontalEdge
                                                                  ? rootShadow.bottom : undefined)
                                bottom: islandWindow.bottomEdge ? rootShadow.bottom : undefined
                            }
                        }
                    }
                    // Keep the Canvas paintable without showing its black shadow source.
                    ShaderEffectSource {
                        id: shadowTexture

                        anchors.fill: shadowSource
                        sourceItem: shadowSource
                        hideSource: true
                        visible: false
                    }
                    DropShadow {

                        anchors.fill: shadowSource
                        source: shadowTexture
                        horizontalOffset: islandWindow.leftEdge ? 6 : islandWindow.rightEdge ? -6 : 0
                        verticalOffset: islandWindow.topEdge ? 6 : islandWindow.bottomEdge ? -6 : 0
                        radius: 20
                        samples: 32
                        color: "#80000000"
                        cached: false
                    }
                    AttachedEdgeCurve {
                        id: leftTopCurve

                        z: 1

                        visible: styleSurface.showAttachedEdgeCurves
                        edge: islandWindow.edge
                        after: false
                        along: islandWindow.edgeCurveAlong
                        depth: islandWindow.edgeCurveDepth
                        sideControl: islandWindow.edgeCurveSideControl
                        edgeControl: islandWindow.edgeCurveOuterControl
                        fillColor: backgroundVisual.surfaceColor

                        anchors {
                            right: islandWindow.horizontalEdge ? rootSurface.left :
                                                                   islandWindow.rightEdge
                                                                   ? rootSurface.right : undefined

                            left: islandWindow.leftEdge ? rootSurface.left : undefined
                            bottom: !islandWindow.horizontalEdge ? rootSurface.top :
                                                                     islandWindow.bottomEdge
                                                                     ? rootSurface.bottom : undefined
                            top: islandWindow.topEdge ? rootSurface.top : undefined
                        }

                        Connections {
                            function onColorChanged() {
                                leftTopCurve.requestPaint();
                            }

                            target: root
                        }
                    }
                    SurfaceShape {
                        id: rootSurface

                        z: 1
                        anchors.fill: null
                        x: root.x
                        y: root.y
                        width: root.width
                        height: root.height
                        surfaceColor: backgroundVisual.surfaceColor
                        topLeftRadius: styleSurface.detached || (!islandWindow.topEdge &&
                                                                 !islandWindow.leftEdge) ? root.radius : 0
                        topRightRadius: styleSurface.detached || (!islandWindow.topEdge &&
                                                                  !islandWindow.rightEdge) ? root.radius : 0
                        bottomRightRadius: styleSurface.detached || (!islandWindow.bottomEdge &&
                                                                     !islandWindow.rightEdge) ? root.radius :
                                                                                                  0
                        bottomLeftRadius: styleSurface.detached || (!islandWindow.bottomEdge &&
                                                                    !islandWindow.leftEdge) ? root.radius :
                                                                                                0
                        cutoutVisible: root.showDashboardKeyhole
                        cutoutX: dashboardKeyholeCutout.x
                        cutoutY: dashboardKeyholeCutout.y
                        cutoutWidth: dashboardKeyholeCutout.width
                        cutoutHeight: dashboardKeyholeCutout.height
                        cutoutRadius: dashboardKeyholeCutout.radius
                    }
                    AttachedEdgeCurve {
                        id: rightTopCurve

                        z: 1

                        visible: styleSurface.showAttachedEdgeCurves
                        edge: islandWindow.edge
                        after: true
                        along: islandWindow.edgeCurveAlong
                        depth: islandWindow.edgeCurveDepth
                        sideControl: islandWindow.edgeCurveSideControl
                        edgeControl: islandWindow.edgeCurveOuterControl
                        fillColor: backgroundVisual.surfaceColor

                        anchors {
                            left: islandWindow.leftEdge ? rootSurface.left : (islandWindow.horizontalEdge
                                                                                ? rootSurface.right :
                                                                                  undefined)

                            right: islandWindow.rightEdge ? rootSurface.right : undefined
                            top: islandWindow.topEdge ? rootSurface.top : (!islandWindow.horizontalEdge
                                                                             ? rootSurface.bottom : undefined)
                            bottom: islandWindow.bottomEdge ? rootSurface.bottom : undefined
                        }

                        Connections {
                            function onColorChanged() {
                                rightTopCurve.requestPaint();
                            }

                            target: root
                        }
                    }
                }
            }

            anchors.topMargin: islandWindow.topEdge ? styleSurface.edgeMargin : 0
            anchors.bottomMargin: islandWindow.bottomEdge ? styleSurface.edgeMargin : 0
            anchors.leftMargin: islandWindow.leftEdge ? styleSurface.edgeMargin : 0
            anchors.rightMargin: islandWindow.rightEdge ? styleSurface.edgeMargin : 0
            width: styleSurface.elongated && longFrame.item ? longFrame.item.implicitWidth : root.width + (
                                                                  islandWindow.horizontalEdge
                                                                  ? islandWindow.edgeCurveAlong * 2 : 0)
            height: styleSurface.elongated && longFrame.item ? longFrame.item.implicitHeight : root.height + (
                                                                   !islandWindow.horizontalEdge
                                                                   ? islandWindow.edgeCurveAlong * 2 : 0)
            state: islandWindow.edge
            states: [
                State {
                    name: "top"

                    AnchorChanges {
                        target: maskContainer
                        anchors.top: islandWindow.contentItem.top
                        anchors.bottom: undefined
                        anchors.left: undefined
                        anchors.right: undefined
                        anchors.horizontalCenter: islandWindow.contentItem.horizontalCenter
                        anchors.verticalCenter: undefined
                    }
                },
                State {
                    name: "bottom"

                    AnchorChanges {
                        target: maskContainer
                        anchors.top: undefined
                        anchors.bottom: islandWindow.contentItem.bottom
                        anchors.left: undefined
                        anchors.right: undefined
                        anchors.horizontalCenter: islandWindow.contentItem.horizontalCenter
                        anchors.verticalCenter: undefined
                    }
                },
                State {
                    name: "left"

                    AnchorChanges {
                        target: maskContainer
                        anchors.top: undefined
                        anchors.bottom: undefined
                        anchors.left: islandWindow.contentItem.left
                        anchors.right: undefined
                        anchors.horizontalCenter: undefined
                        anchors.verticalCenter: islandWindow.contentItem.verticalCenter
                    }
                },
                State {
                    name: "right"

                    AnchorChanges {
                        target: maskContainer
                        anchors.top: undefined
                        anchors.bottom: undefined
                        anchors.left: undefined
                        anchors.right: islandWindow.contentItem.right
                        anchors.horizontalCenter: undefined
                        anchors.verticalCenter: islandWindow.contentItem.verticalCenter
                    }
                }
            ]

            Loader {
                id: longFrame
                anchors.fill: parent
                active: styleSurface.elongated
                sourceComponent: LongIslandFrame {
                    screen: islandWindow.screen
                    edge: islandWindow.edge
                    expanded: !root.isCollapsedMode
                    targetWidth: root.targetW
                    targetHeight: root.targetH
                    childItem: root
                    cutoutItem: dashboardKeyholeCutout
                    cutoutVisible: root.showDashboardKeyhole
                    surfaceColor: root.color
                    onClockClicked: button => root.activateMouseAction(button === Qt.MiddleButton
                                                                       ? PersonalizationConfig.islandMiddleClickAction :
                                                                         PersonalizationConfig.islandLeftClickAction,
                                                                       true)
                    onMediaRequested: root.activateMouseAction("media", true)
                }
            }

            IslandHoverController {
                id: hoverIntent
                triggerHovered: styleSurface.elongated ? !!longFrame.item && longFrame.item.clockHovered :
                                                         surfaceHover.hovered
                surfaceHovered: surfaceHover.hovered || (styleSurface.elongated && !!longFrame.item
                                                         && longFrame.item.mainHovered)
                canOpen: root.isCollapsedMode && PersonalizationConfig.effectiveIslandHoverAction !== "none"
                previewOpen: root.hoverOpened
                openDelay: PersonalizationConfig.islandHoverOpenDelay
                closeDelay: PersonalizationConfig.islandHoverCloseDelay
                onOpenRequested: {
                    const action = PersonalizationConfig.effectiveIslandHoverAction;
                    root.activateMouseAction(action, false, true);
                    root.hoverOpened = true;
                }
                onCloseRequested: islandWindow.closeAllOthers()
            }

            Item {
                id: root

                property bool hoverOpened: false

                function activateMouseAction(action, toggle, fromHover = false) {
                    if (action === "none" || action === "peak" || root.contentPresentationActive
                            || root.isNotifMode || root.isVolumeMode)
                        return;
                    const tabs = {
                        dashboard: 0,
                        weather: 1
                    };
                    const isTab = Object.prototype.hasOwnProperty.call(tabs, action);
                    const alreadyOpen = action === "media" ? root.expanded : action === "lyrics"
                                                             ? root.showLyrics : action === "tools"
                                                               ? root.showTools : isTab && root.showHub
                                                                 && root.hubTabIndex === tabs[action];
                    if (toggle && alreadyOpen && root.hoverOpened) {
                        root.hoverOpened = false;
                        hoverIntent.cancel();
                        return;
                    }
                    islandWindow.closeAllOthers();
                    if (toggle && alreadyOpen)
                        return;
                    root.hoverOpened = fromHover;
                    if (action === "media")
                        root.expanded = true;
                    else if (action === "lyrics")
                        root.showLyrics = true;
                    else if (action === "tools")
                        root.showTools = true;
                    else if (isTab) {
                        root.hubTabIndex = tabs[action];
                        root.showHub = true;
                    }
                }

                HoverHandler {
                    id: surfaceHover
                    enabled: !styleSurface.elongated || (!!longFrame.item && longFrame.item.progress > 0.02)
                }

                TapHandler {
                    // A click turns a hover preview into a persistent keyboard
                    // interaction without consuming child controls' pointer events.
                    enabled: root.hoverOpened && !root.isCollapsedMode
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                    onTapped: root.hoverOpened = false
                }

                property bool showLyrics: false
                property bool expanded: false
                property bool showVolume: false
                property bool showHub: false
                property bool showTools: false
                readonly property bool recordingLaunchPending: styleSurface.elongated && showTools && (
                                                                   RecordingService.isSelecting
                                                                   || RecordingService.isStarting
                                                                   || AudioRecordingService.isStarting)
                property int hubTabIndex: 0
                property bool componentReady: false
                property bool pillStopFusionMinimumActive: false
                readonly property bool backendFinalizing: RecordingService.isFinalizing
                readonly property bool gifRecording: RecordingService.recordingType === "gif"
                readonly property bool stopPresentationActive: RecordingService.isStopPending || (
                                                                   styleSurface.splitRecording
                                                                   && pillStopFusionMinimumActive)
                readonly property bool isRecording: (RecordingService.isRecording || RecordingService.state
                                                     === "paused") && !stopPresentationActive
                readonly property bool isFinalizing: backendFinalizing || stopPresentationActive
                readonly property bool isRecordingMode: isRecording || isFinalizing
                property bool recordingExitActive: false
                readonly property bool recordingPresentationActive: isRecordingMode || recordingExitActive
                                                                    || recordingInfoProgress > 0.01
                                                                    || recordingActionProgress > 0.01
                                                                    || processingContentProgress > 0.01
                readonly property int audioPhaseHidden: 0
                readonly property int audioPhaseExpanded: 1
                readonly property int audioPhaseCollapsing: 2
                property int audioPresentationPhase: audioPhaseHidden
                readonly property bool audioSessionActive: AudioRecordingService.isActive
                readonly property bool audioPresentationActive: audioSessionActive || audioPresentationPhase
                                                                !== audioPhaseHidden
                readonly property bool audioGeometryActive: audioSessionActive || audioPresentationPhase
                                                            === audioPhaseExpanded
                readonly property bool contentPresentationActive: recordingPresentationActive
                                                                  || audioPresentationActive
                property bool isLyricsMode: showLyrics && !contentPresentationActive
                property bool isToolsMode: !contentPresentationActive && showTools && !isLyricsMode
                property bool isHubMode: !contentPresentationActive && showHub && !isToolsMode &&
                                         !isLyricsMode
                property bool isVolumeMode: !contentPresentationActive && showVolume && !expanded &&
                                            !isHubMode && !isToolsMode && !isLyricsMode
                property bool isNotifMode: !contentPresentationActive && NotificationService.hasNotifs &&
                                           !expanded && !showVolume && !isHubMode && !isToolsMode &&
                                           !isLyricsMode
                property bool isCollapsedMode: !contentPresentationActive && !expanded && !isNotifMode &&
                                               !isVolumeMode && !isLyricsMode && !isHubMode && !isToolsMode
                property bool isCollapsedHovered: PersonalizationConfig.effectiveIslandHoverAction
                                                  === "peak" && isCollapsedMode && root.hoverOpened
                readonly property bool escapeDismissActive: !contentPresentationActive && (expanded
                                                                                           || isLyricsMode
                                                                                           || isHubMode
                                                                                           || isToolsMode
                                                                                           || isCollapsedHovered)
                readonly property bool keyboardInteractionActive: escapeDismissActive && !hoverOpened &&
                                                                  !isCollapsedMode && !recordingLaunchPending
                onKeyboardInteractionActiveChanged: {
                    if (keyboardInteractionActive)
                        root.requestKeyboardFocus();
                }
                readonly property bool dashboardTabActive: isHubMode && hubTabIndex === 0
                readonly property string dashboardUptimeOwner: "island-dashboard:" + String(
                                                                   islandWindow.modelData.name || "default")
                // The hub remains visible while fading out after its mode is dismissed.
                // Keep its cutout and blur subtraction until the card is hidden too.
                readonly property bool showDashboardKeyhole: hub.currentIndex === 0 && hub.visible
                property real pillMorphProgress: 0
                property real recordingInfoProgress: 0
                property real recordingActionProgress: 0
                property real processingContentProgress: 0
                readonly property int pillEntryDuration: 900
                readonly property int pillFusionDuration: 820
                property int pillActiveFusionDuration: pillFusionDuration
                property int notifW: 380
                property int notifH: 20 + NotificationService.popupList.reduce((height, notif) => {
                    return height + (NotificationService.normalActions(notif).length > 0 ? 104 : 64);
                }, 0) + Math.max(0, NotificationService.popupList.length - 1) * 10
                property color color: BlurService.backgroundColor(mediaWidget.visible
                                                                  && mediaWidget.coverColors
                                                                  ? mediaWidget.surfaceColor :
                                                                    Appearance.colors.colLayer0)
                readonly property QtObject activeLayout: islandWindow.horizontalEdge ? horizontalLayout :
                                                                                         verticalLayout
                readonly property real recordingVisualWidth: styleSurface.splitRecording
                                                             && pillRecordingPresenter.item
                                                             ? pillRecordingPresenter.item.implicitWidth :
                                                               activeLayout.attachedRecordingWidth
                readonly property real recordingVisualHeight: styleSurface.splitRecording
                                                              && pillRecordingPresenter.item
                                                              ? pillRecordingPresenter.item.implicitHeight :
                                                                activeLayout.attachedRecordingHeight
                readonly property bool useRecordingBlurRegions: styleSurface.splitRecording
                                                                && root.recordingPresentationActive
                                                                && pillRecordingPresenter.item !== null
                readonly property var recordingBlurBackgroundItems: useRecordingBlurRegions
                                                                    ? pillRecordingPresenter.item.blurBackgroundItems :
                                                                      []
                property real targetW: isVolumeMode && keyboardOsd ? (islandWindow.horizontalEdge ? 260 :
                                                                                                      112) : activeLayout.targetWidth
                property real targetH: isVolumeMode && keyboardOsd ? (islandWindow.horizontalEdge ? 64 :
                                                                                                      144) : activeLayout.targetHeight
                property int targetR: styleSurface.detached ? Math.min(Math.min(targetW, targetH) / 2, styleSurface.maxPillRadius) :
                                                              12
                property int wDuration: IslandMotion.expandingDuration
                property int hDuration: IslandMotion.expandingDuration
                property int rDuration: IslandMotion.radiusDuration
                property var wBezier: IslandMotion.expandingBezier
                property var hBezier: IslandMotion.expandingBezier
                property var rBezier: IslandMotion.radiusBezier
                property real radius: targetR
                property var audioNode: Pipewire.defaultAudioSink ? Pipewire.defaultAudioSink.audio : null
                property var sourceAudioNode: Pipewire.defaultAudioSource ? Pipewire.defaultAudioSource.audio :
                                                                            null
                readonly property var sinkNode: Pipewire.defaultAudioSink
                readonly property var sourceNode: Pipewire.defaultAudioSource
                property real lastSinkVolume: -1
                property bool lastSinkMuted: false
                property string lastSinkId: ""
                property bool sinkInitialized: false
                property real lastSourceVolume: -1
                property bool lastSourceMuted: false
                property string lastSourceId: ""
                property bool sourceInitialized: false
                property string sliderMode: "volume"
                readonly property bool keyboardOsd: sliderMode === "capslock" || sliderMode === "numlock"
                property bool locksInitialized: false
                property bool previousCapsLock: false
                property bool previousNumLock: false
                property bool lockEnabled: false

                function updateKeyboardLocks() {
                    if (!KeyboardLockService.available) {
                        locksInitialized = false;
                        if (keyboardOsd)
                            showVolume = false;
                        return;
                    }
                    const caps = KeyboardLockService.capsLock;
                    const num = KeyboardLockService.numLock;
                    if (locksInitialized) {
                        if (caps !== previousCapsLock && PersonalizationConfig.islandCapsLockOsd) {
                            root.lockEnabled = caps;
                            root.triggerSliderOSD("capslock");
                        }
                        if (num !== previousNumLock && PersonalizationConfig.islandNumLockOsd) {
                            root.lockEnabled = num;
                            root.triggerSliderOSD("numlock");
                        }
                    }
                    previousCapsLock = caps;
                    previousNumLock = num;
                    locksInitialized = true;
                }

                function syncSinkState() {
                    if (!sinkNode || !sinkNode.ready || !audioNode)
                        return;
                    const currentSinkId = String(sinkNode.id || "");
                    if (!sinkInitialized || lastSinkId !== currentSinkId) {
                        lastSinkId = currentSinkId;
                        lastSinkVolume = audioNode.volume;
                        lastSinkMuted = audioNode.muted;
                        sinkInitialized = true;
                    }
                }

                function handleSinkVolumeChanged() {
                    if (!sinkNode || !sinkNode.ready || !audioNode)
                        return;
                    const currentSinkId = String(sinkNode.id || "");
                    if (!sinkInitialized || lastSinkId !== currentSinkId) {
                        syncSinkState();
                        return;
                    }
                    const currentVol = audioNode.volume;
                    if (Math.abs(currentVol - lastSinkVolume) > 0.0001) {
                        lastSinkVolume = currentVol;
                        root.triggerSliderOSD("volume");
                    }
                }

                function handleSinkMutedChanged() {
                    if (!sinkNode || !sinkNode.ready || !audioNode)
                        return;
                    const currentSinkId = String(sinkNode.id || "");
                    if (!sinkInitialized || lastSinkId !== currentSinkId) {
                        syncSinkState();
                        return;
                    }
                    const currentMuted = audioNode.muted;
                    if (currentMuted !== lastSinkMuted) {
                        lastSinkMuted = currentMuted;
                        root.triggerSliderOSD("volume");
                    }
                }

                function syncSourceState() {
                    if (!sourceNode || !sourceNode.ready || !sourceAudioNode)
                        return;
                    const currentSourceId = String(sourceNode.id || "");
                    if (!sourceInitialized || lastSourceId !== currentSourceId) {
                        lastSourceId = currentSourceId;
                        lastSourceVolume = sourceAudioNode.volume;
                        lastSourceMuted = sourceAudioNode.muted;
                        sourceInitialized = true;
                    }
                }

                function handleSourceVolumeChanged() {
                    if (!sourceNode || !sourceNode.ready || !sourceAudioNode)
                        return;
                    const currentSourceId = String(sourceNode.id || "");
                    if (!sourceInitialized || lastSourceId !== currentSourceId) {
                        syncSourceState();
                        return;
                    }
                    const currentVol = sourceAudioNode.volume;
                    if (Math.abs(currentVol - lastSourceVolume) > 0.0001) {
                        lastSourceVolume = currentVol;
                        root.triggerSliderOSD("mic");
                    }
                }

                function handleSourceMutedChanged() {
                    if (!sourceNode || !sourceNode.ready || !sourceAudioNode)
                        return;
                    const currentSourceId = String(sourceNode.id || "");
                    if (!sourceInitialized || lastSourceId !== currentSourceId) {
                        syncSourceState();
                        return;
                    }
                    const currentMuted = sourceAudioNode.muted;
                    if (currentMuted !== lastSourceMuted) {
                        lastSourceMuted = currentMuted;
                        root.triggerSliderOSD("mic");
                    }
                }

                readonly property var currentPlayer: MediaService.active

                function isHoverWidthMotion(nextW) {
                    return isCollapsedMode && Math.abs(nextW - width) <= IslandMotion.hoverWidthDelta;
                }

                function isHoverHeightMotion(nextH) {
                    return isCollapsedMode && Math.abs(nextH - height) <= IslandMotion.hoverHeightDelta;
                }

                function isHoverRadiusMotion(nextR) {
                    return isCollapsedMode && Math.abs(nextR - radius) <= IslandMotion.hoverRadiusDelta;
                }

                function closeIslandPopups() {
                    hoverIntent.cancel();
                    root.expanded = false;
                    root.showLyrics = false;
                    root.showVolume = false;
                    root.showHub = false;
                    root.showTools = false;
                    root.hoverOpened = false;
                    if (root.isNotifMode)
                        NotificationService.hideAllPopups();
                }

                function triggerSliderOSD(mode) {
                    if (root.contentPresentationActive || root.showHub || root.showTools || root.expanded
                            || root.showLyrics)
                        return;

                    root.sliderMode = mode;
                    root.showVolume = true;
                    volHideTimer.restart();
                }

                function triggerVolumeOSD() {
                    root.triggerSliderOSD("volume");
                }

                function requestKeyboardFocus() {
                    Qt.callLater(() => {
                        if (!root.keyboardInteractionActive)
                            return;

                        if (root.isToolsMode)
                            toolsWidget.forceActiveFocus();
                        else
                            root.forceActiveFocus();
                    });
                }

                readonly property string recordingConsumerOwner: "island-recording:" + String(
                                                                         islandWindow.screen ? islandWindow.screen.name : "default")
                readonly property string audioConsumerOwner: "island-audio:" + String(
                                                                    islandWindow.screen ? islandWindow.screen.name : "default")
                function syncRecordingConsumer() {
                    if (root.isToolsMode || RecordingService.isActive || root.recordingPresentationActive)
                        RecordingService.acquireConsumer(recordingConsumerOwner);
                    else
                        RecordingService.releaseConsumer(recordingConsumerOwner);
                }
                function syncAudioConsumer() {
                    if (root.isToolsMode || AudioRecordingService.isActive || root.audioPresentationActive)
                        AudioRecordingService.acquireConsumer(audioConsumerOwner);
                    else
                        AudioRecordingService.releaseConsumer(audioConsumerOwner);
                }
                onIsToolsModeChanged: {
                    root.syncRecordingConsumer();
                    root.syncAudioConsumer();
                    if (root.isToolsMode)
                        root.requestKeyboardFocus();
                }
                onRecordingPresentationActiveChanged: root.syncRecordingConsumer()
                onAudioPresentationActiveChanged: root.syncAudioConsumer()
                onDashboardTabActiveChanged: SystemIdentityService.setUptimeConsumer(root.dashboardUptimeOwner,
                                                                                     root.dashboardTabActive)
                Component.onDestruction: {
                    RecordingService.releaseConsumer(recordingConsumerOwner);
                    AudioRecordingService.releaseConsumer(audioConsumerOwner);
                    SystemIdentityService.setUptimeConsumer(root.dashboardUptimeOwner, false);
                }

                focus: root.keyboardInteractionActive
                Keys.onEscapePressed: event => {
                    WidgetState.closeAllPopups();
                    event.accepted = true;
                }
                state: islandWindow.edge
                // HubContent changes its own currentIndex when a tab is
                // clicked. Keep the two pieces of state synchronized
                // explicitly; a child assignment would otherwise break a
                // binding installed on HubContent.currentIndex.
                onHubTabIndexChanged: {
                    if (hub.currentIndex !== root.hubTabIndex)
                        hub.currentIndex = root.hubTabIndex;
                }
                clip: true
                z: 100
                width: styleSurface.elongated && longFrame.item ? longFrame.item.childWidth : targetW
                height: styleSurface.elongated && longFrame.item ? longFrame.item.childHeight : targetH
                opacity: styleSurface.elongated ? (longFrame.item ? longFrame.item.contentOpacity : 0) : 1
                visible: !styleSurface.elongated || (!!longFrame.item && longFrame.item.progress > 0)
                enabled: !styleSurface.elongated || (!!longFrame.item && longFrame.item.progress > 0.02)
                anchors.topMargin: styleSurface.elongated && islandWindow.topEdge && longFrame.item
                                   ? longFrame.item.childOffset : 0
                anchors.bottomMargin: styleSurface.elongated && islandWindow.bottomEdge && longFrame.item
                                      ? longFrame.item.childOffset : 0
                anchors.leftMargin: styleSurface.elongated && islandWindow.leftEdge && longFrame.item
                                    ? longFrame.item.childOffset : 0
                anchors.rightMargin: styleSurface.elongated && islandWindow.rightEdge && longFrame.item
                                     ? longFrame.item.childOffset : 0
                onAudioSessionActiveChanged: {
                    root.syncAudioConsumer();
                    if (root.audioSessionActive) {
                        if (styleSurface.elongated) {
                            root.hoverOpened = false;
                            hoverIntent.cancel();
                        }
                        root.audioPresentationPhase = root.audioPhaseExpanded;
                        root.expanded = false;
                        root.showLyrics = false;
                        root.showVolume = false;
                        root.showHub = false;
                        root.showTools = false;
                        if (root.componentReady)
                            audioRecordingHost.beginEntry();

                        return;
                    }
                    if (root.audioPresentationPhase === root.audioPhaseExpanded)
                        audioRecordingHost.beginExit();
                }
                onIsRecordingChanged: {
                    root.syncRecordingConsumer();
                    if (!root.isRecording)
                        return;

                    if (styleSurface.elongated) {
                        // Recording already owns the presentation here, so
                        // clearing Tools cannot collapse the existing island.
                        root.showTools = false;
                        root.showHub = false;
                        root.showLyrics = false;
                        root.showVolume = false;
                        root.expanded = false;
                        root.hoverOpened = false;
                        hoverIntent.cancel();
                    }
                    contentResetTimer.stop();
                    recordingPresentationOut.stop();
                    recordingActionOut.stop();
                    pillRecordingInfoOut.stop();
                    bangsRecordingInfoOut.stop();
                    processingContentIn.stop();
                    root.recordingExitActive = false;
                    recordingContentIn.restart();
                    if (styleSurface.splitRecording) {
                        pillGeometryExit.stop();
                        pillGeometryEntry.restart();
                    }
                }
                onIsFinalizingChanged: {
                    if (!root.isFinalizing)
                        return;

                    recordingContentIn.stop();
                    processingContentIn.stop();
                    recordingActionOut.restart();
                    if (styleSurface.splitRecording) {
                        pillGeometryEntry.stop();
                        root.pillActiveFusionDuration = Math.max(220, Math.round(root.pillFusionDuration
                                                                                 * root.pillMorphProgress));
                        pillRecordingInfoOut.restart();
                        pillGeometryExit.restart();
                    } else if (root.gifRecording) {
                        bangsRecordingInfoOut.restart();
                        processingContentIn.restart();
                    }
                }
                onBackendFinalizingChanged: {
                    if (root.gifRecording && root.backendFinalizing && (!styleSurface.splitRecording
                                                                        || root.pillMorphProgress <= 0.01)
                            && root.processingContentProgress < 0.99)
                        processingContentIn.restart();
                }
                onIsRecordingModeChanged: {
                    if (root.isRecordingMode)
                        return;

                    root.pillStopFusionMinimumActive = false;
                    pillRecordingInfoOut.stop();
                    bangsRecordingInfoOut.stop();
                    processingContentIn.stop();
                    if (!styleSurface.splitRecording) {
                        // Backend completion starts the geometry exit immediately;
                        // don't add a processing/fade-out presentation beforehand.
                        recordingContentIn.stop();
                        recordingActionOut.stop();
                        recordingPresentationOut.stop();
                        root.recordingInfoProgress = 0;
                        root.recordingActionProgress = 0;
                        root.processingContentProgress = 0;
                        root.recordingExitActive = false;
                        return;
                    }
                    root.recordingExitActive = true;
                    recordingPresentationOut.restart();
                }
                Component.onCompleted: {
                    root.syncRecordingConsumer();
                    root.syncAudioConsumer();
                    root.updateKeyboardLocks();
                    root.syncSinkState();
                    root.syncSourceState();
                    SystemIdentityService.setUptimeConsumer(root.dashboardUptimeOwner,
                                                            root.dashboardTabActive);
                    root.componentReady = true;
                    recordingContentIn.stop();
                    recordingPresentationOut.stop();
                    recordingActionOut.stop();
                    pillRecordingInfoOut.stop();
                    bangsRecordingInfoOut.stop();
                    processingContentIn.stop();
                    pillGeometryEntry.stop();
                    pillGeometryExit.stop();
                    root.recordingExitActive = false;
                    root.pillMorphProgress = styleSurface.splitRecording && root.isRecording ? 1 : 0;
                    root.recordingInfoProgress = root.isRecording || (!styleSurface.splitRecording
                                                                      && root.isFinalizing &&
                                                                      !root.gifRecording) ? 1 : 0;
                    root.recordingActionProgress = root.isRecording ? 1 : 0;
                    root.processingContentProgress = root.gifRecording && root.isFinalizing ? 1 : 0;
                    root.audioPresentationPhase = root.audioSessionActive ? root.audioPhaseExpanded :
                                                                            root.audioPhaseHidden;
                    if (root.audioSessionActive)
                        audioRecordingHost.beginEntry();
                }
                onTargetWChanged: {
                    if (root.audioPresentationPhase === root.audioPhaseCollapsing) {
                        wDuration = IslandMotion.audioCollapseDuration;
                        wBezier = IslandMotion.hoverBezier;
                        return;
                    }
                    if (targetW === root.activeLayout.audioWidth && root.audioGeometryActive) {
                        wDuration = IslandMotion.audioExpandDuration;
                        wBezier = IslandMotion.hoverBezier;
                        return;
                    }
                    if (root.isHoverWidthMotion(targetW)) {
                        wDuration = IslandMotion.hoverDuration;
                        wBezier = IslandMotion.hoverBezier;
                        return;
                    }
                    const isExpanding = targetW > width;
                    wDuration = isExpanding ? IslandMotion.expandingDuration :
                                              IslandMotion.shrinkingDuration;
                    wBezier = isExpanding ? IslandMotion.expandingBezier : IslandMotion.shrinkingBezier;
                }
                onTargetHChanged: {
                    if (root.audioPresentationPhase === root.audioPhaseCollapsing) {
                        hDuration = IslandMotion.audioCollapseDuration;
                        hBezier = IslandMotion.hoverBezier;
                        return;
                    }
                    if (targetH === root.activeLayout.audioHeight && root.audioGeometryActive) {
                        hDuration = IslandMotion.audioExpandDuration;
                        hBezier = IslandMotion.hoverBezier;
                        return;
                    }
                    if (root.isHoverHeightMotion(targetH)) {
                        hDuration = IslandMotion.hoverDuration;
                        hBezier = IslandMotion.hoverBezier;
                        return;
                    }
                    const isExpanding = targetH > height;
                    hDuration = isExpanding ? IslandMotion.expandingDuration :
                                              IslandMotion.shrinkingDuration;
                    hBezier = isExpanding ? IslandMotion.expandingBezier : IslandMotion.shrinkingBezier;
                }
                onTargetRChanged: {
                    if (root.isHoverRadiusMotion(targetR)) {
                        rDuration = IslandMotion.hoverDuration;
                        rBezier = IslandMotion.hoverBezier;
                    } else {
                        rDuration = IslandMotion.radiusDuration;
                        rBezier = IslandMotion.radiusBezier;
                    }
                }
                states: [
                    State {
                        name: "top"

                        AnchorChanges {
                            target: root
                            anchors.top: maskContainer.top
                            anchors.bottom: undefined
                            anchors.left: undefined
                            anchors.right: undefined
                            anchors.horizontalCenter: maskContainer.horizontalCenter
                            anchors.verticalCenter: undefined
                        }
                    },
                    State {
                        name: "bottom"

                        AnchorChanges {
                            target: root
                            anchors.top: undefined
                            anchors.bottom: maskContainer.bottom
                            anchors.left: undefined
                            anchors.right: undefined
                            anchors.horizontalCenter: maskContainer.horizontalCenter
                            anchors.verticalCenter: undefined
                        }
                    },
                    State {
                        name: "left"

                        AnchorChanges {
                            target: root
                            anchors.top: undefined
                            anchors.bottom: undefined
                            anchors.left: maskContainer.left
                            anchors.right: undefined
                            anchors.horizontalCenter: undefined
                            anchors.verticalCenter: maskContainer.verticalCenter
                        }
                    },
                    State {
                        name: "right"

                        AnchorChanges {
                            target: root
                            anchors.top: undefined
                            anchors.bottom: undefined
                            anchors.left: undefined
                            anchors.right: maskContainer.right
                            anchors.horizontalCenter: undefined
                            anchors.verticalCenter: maskContainer.verticalCenter
                        }
                    }
                ]

                HorizontalIslandLayout {
                    id: horizontalLayout

                    recordingActive: root.recordingPresentationActive
                    audioActive: root.audioGeometryActive
                    toolsActive: root.isToolsMode
                    hubActive: root.isHubMode
                    lyricsActive: root.isLyricsMode
                    expandedActive: root.expanded
                    expandedWidth: mediaWidget.panelWidth
                    expandedHeight: mediaWidget.panelHeight
                    volumeActive: root.isVolumeMode
                    notificationsActive: root.isNotifMode
                    collapsedHovered: root.isCollapsedHovered
                    recordingWidth: root.recordingVisualWidth
                    recordingHeight: root.recordingVisualHeight
                    toolsWidth: toolsWidget.implicitWidth
                    toolsHeight: toolsWidget.implicitHeight
                    hubWidth: hub.implicitWidth
                    hubHeight: hub.implicitHeight
                    lyricsWidth: lyricsWidget.implicitWidth
                    lyricsHeight: lyricsWidget.implicitHeight
                    notificationsWidth: root.notifW
                    notificationsHeight: root.notifH
                }

                VerticalIslandLayout {
                    id: verticalLayout

                    recordingActive: root.recordingPresentationActive
                    audioActive: root.audioGeometryActive
                    toolsActive: root.isToolsMode
                    hubActive: root.isHubMode
                    lyricsActive: root.isLyricsMode
                    expandedActive: root.expanded
                    expandedWidth: mediaWidget.panelWidth
                    expandedHeight: mediaWidget.panelHeight
                    volumeActive: root.isVolumeMode
                    notificationsActive: root.isNotifMode
                    collapsedHovered: root.isCollapsedHovered
                    recordingWidth: root.recordingVisualWidth
                    recordingHeight: root.recordingVisualHeight
                    toolsWidth: toolsWidget.implicitWidth
                    toolsHeight: toolsWidget.implicitHeight
                    hubWidth: hub.implicitWidth
                    hubHeight: hub.implicitHeight
                    lyricsWidth: lyricsWidget.implicitWidth
                    lyricsHeight: lyricsWidget.implicitHeight
                    notificationsWidth: root.notifW
                    notificationsHeight: root.notifH
                }

                ParallelAnimation {
                    id: recordingContentIn

                    NumberAnimation {
                        target: root
                        property: "processingContentProgress"
                        to: 0
                        duration: Appearance.animation.expressiveFastEffects.duration
                        easing.type: Appearance.animation.expressiveFastEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                    }

                    SequentialAnimation {
                        PauseAnimation {
                            duration: Appearance.animation.expressiveFastEffects.duration
                        }

                        ParallelAnimation {
                            NumberAnimation {
                                target: root
                                property: "recordingInfoProgress"
                                to: 1
                                duration: Appearance.animation.expressiveSlowEffects.duration
                                easing.type: Appearance.animation.expressiveSlowEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveSlowEffects.bezierCurve
                            }

                            NumberAnimation {
                                target: root
                                property: "recordingActionProgress"
                                to: 1
                                duration: Appearance.animation.expressiveSlowEffects.duration
                                easing.type: Appearance.animation.expressiveSlowEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveSlowEffects.bezierCurve
                            }
                        }
                    }
                }

                NumberAnimation {
                    id: pillGeometryEntry

                    target: root
                    property: "pillMorphProgress"
                    to: 1
                    duration: root.pillEntryDuration
                    easing.type: Easing.Linear
                }

                NumberAnimation {
                    id: recordingActionOut

                    target: root
                    property: "recordingActionProgress"
                    to: 0
                    duration: Appearance.animation.expressiveFastEffects.duration
                    easing.type: Appearance.animation.expressiveFastEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                }

                SequentialAnimation {
                    id: pillRecordingInfoOut

                    PauseAnimation {
                        duration: Math.max(0, root.pillActiveFusionDuration
                                           - Appearance.animation.expressiveSlowEffects.duration)
                    }

                    NumberAnimation {
                        target: root
                        property: "recordingInfoProgress"
                        to: 0
                        duration: Appearance.animation.expressiveSlowEffects.duration
                        easing.type: Appearance.animation.expressiveSlowEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveSlowEffects.bezierCurve
                    }
                }

                NumberAnimation {
                    id: bangsRecordingInfoOut

                    target: root
                    property: "recordingInfoProgress"
                    to: 0
                    duration: Appearance.animation.emphasizedAccel.duration
                    easing.type: Appearance.animation.emphasizedAccel.type
                    easing.bezierCurve: Appearance.animation.emphasizedAccel.bezierCurve
                }

                NumberAnimation {
                    id: pillGeometryExit

                    target: root
                    property: "pillMorphProgress"
                    to: 0
                    duration: root.pillActiveFusionDuration
                    easing.type: Easing.Linear
                    onFinished: {
                        const shouldShowProcessing = root.gifRecording && (root.backendFinalizing
                                                                           || RecordingService.isStopPending);
                        root.pillStopFusionMinimumActive = false;
                        if (shouldShowProcessing)
                            processingContentIn.restart();
                    }
                }

                NumberAnimation {
                    id: processingContentIn

                    target: root
                    property: "processingContentProgress"
                    to: root.gifRecording ? 1 : 0
                    duration: Appearance.animation.expressiveSlowEffects.duration
                    easing.type: Appearance.animation.expressiveSlowEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveSlowEffects.bezierCurve
                }

                ParallelAnimation {
                    id: recordingPresentationOut

                    onFinished: {
                        root.recordingExitActive = false;
                        contentResetTimer.restart();
                    }

                    NumberAnimation {
                        target: root
                        property: "recordingInfoProgress"
                        to: 0
                        duration: Appearance.animation.emphasizedAccel.duration
                        easing.type: Appearance.animation.emphasizedAccel.type
                        easing.bezierCurve: Appearance.animation.emphasizedAccel.bezierCurve
                    }

                    NumberAnimation {
                        target: root
                        property: "recordingActionProgress"
                        to: 0
                        duration: Appearance.animation.expressiveFastEffects.duration
                        easing.type: Appearance.animation.expressiveFastEffects.type
                        easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
                    }

                    NumberAnimation {
                        target: root
                        property: "processingContentProgress"
                        to: 0
                        duration: Appearance.animation.emphasizedAccel.duration
                        easing.type: Appearance.animation.emphasizedAccel.type
                        easing.bezierCurve: Appearance.animation.emphasizedAccel.bezierCurve
                    }
                }

                Timer {
                    id: contentResetTimer

                    interval: 60
                    onTriggered: {
                        if (root.recordingPresentationActive)
                            return;

                        recordingContentIn.stop();
                        recordingPresentationOut.stop();
                        recordingActionOut.stop();
                        pillRecordingInfoOut.stop();
                        bangsRecordingInfoOut.stop();
                        processingContentIn.stop();
                        pillGeometryEntry.stop();
                        pillGeometryExit.stop();
                        root.pillMorphProgress = 0;
                        root.recordingInfoProgress = 0;
                        root.recordingActionProgress = 0;
                        root.processingContentProgress = 0;
                    }
                }

                Rectangle {
                    id: dashboardKeyholeCutout

                    width: 340
                    height: 456
                    anchors.left: parent.horizontalCenter
                    anchors.leftMargin: hub.dashboardKeyholeCenterOffset + contentParallax.x
                    anchors.top: parent.top
                    anchors.topMargin: 132 + contentParallax.y
                    radius: 24
                    color: "transparent"
                    visible: root.showDashboardKeyhole
                }

                Loader {
                    anchors.fill: parent
                    active: mediaWidget.visible && mediaWidget.backgroundCover
                    opacity: mediaWidget.opacity
                    sourceComponent: MediaBackdrop {
                        artUrl: mediaWidget.artUrl
                        sourceSize: Qt.size(Math.ceil(Math.min(mediaWidget.panelWidth,
                                                               mediaWidget.panelHeight * 1.5) * 2), Math.ceil(
                                                mediaWidget.panelHeight * 2))
                        topLeftRadius: styleSurface.elongated && longFrame.item ? longFrame.item.childRadius :
                                                                                  rootSurface.topLeftRadius
                        topRightRadius: styleSurface.elongated && longFrame.item ? longFrame.item.childRadius :
                                                                                   rootSurface.topRightRadius
                        bottomLeftRadius: styleSurface.elongated && longFrame.item
                                          ? longFrame.item.childRadius : rootSurface.bottomLeftRadius
                        bottomRightRadius: styleSurface.elongated && longFrame.item
                                           ? longFrame.item.childRadius : rootSurface.bottomRightRadius
                    }
                }

                Connections {
                    target: KeyboardLockService
                    function onAvailabilityChanged() {
                        root.locksInitialized = false;
                        root.updateKeyboardLocks();
                    }
                    function onLockStateChanged() {
                        root.updateKeyboardLocks();
                    }
                }

                Connections {
                    target: PersonalizationConfig
                    function onIslandHoverActionChanged() {
                        hoverIntent.cancel();
                        if (root.hoverOpened)
                            islandWindow.closeAllOthers();
                    }
                    function onIslandCapsLockOsdChanged() {
                        if (!PersonalizationConfig.islandCapsLockOsd && root.sliderMode === "capslock")
                            root.showVolume = false;
                    }
                    function onIslandNumLockOsdChanged() {
                        if (!PersonalizationConfig.islandNumLockOsd && root.sliderMode === "numlock")
                            root.showVolume = false;
                    }
                }

                PwObjectTracker {
                    objects: [Pipewire.defaultAudioSink, Pipewire.defaultAudioSource]
                }

                Timer {
                    id: volHideTimer

                    interval: 2000
                    onTriggered: {
                        if (!root.keyboardOsd && volumeWidget.isInteractionActive)
                            restart();
                        else
                            root.showVolume = false;
                    }
                }

                Connections {
                    target: root.sinkNode
                    ignoreUnknownSignals: true
                    function onReadyChanged() {
                        root.syncSinkState();
                    }
                    function onIdChanged() {
                        root.syncSinkState();
                    }
                }

                Connections {
                    target: root.sourceNode
                    ignoreUnknownSignals: true
                    function onReadyChanged() {
                        root.syncSourceState();
                    }
                    function onIdChanged() {
                        root.syncSourceState();
                    }
                }

                Connections {
                    function onVolumeChanged() {
                        root.handleSinkVolumeChanged();
                    }

                    function onMutedChanged() {
                        root.handleSinkMutedChanged();
                    }

                    target: root.audioNode
                    ignoreUnknownSignals: true
                }

                Connections {
                    function onVolumeChanged() {
                        root.handleSourceVolumeChanged();
                    }

                    function onMutedChanged() {
                        root.handleSourceMutedChanged();
                    }

                    target: root.sourceAudioNode
                    ignoreUnknownSignals: true
                }

                Connections {
                    function onBrightnessChanged() {
                        root.triggerSliderOSD("brightness");
                    }

                    target: BrightnessService
                }

                MouseArea {
                    id: islandMouseArea

                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    enabled: !root.contentPresentationActive && !root.isNotifMode && !root.isVolumeMode
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                    onClicked: mouse => {
                        root.activateMouseAction(mouse.button === Qt.MiddleButton
                                                 ? PersonalizationConfig.islandMiddleClickAction :
                                                   PersonalizationConfig.islandLeftClickAction, true);
                        mouse.accepted = true;
                    }
                }

                Item {
                    id: staticCanvas

                    transform: Translate {
                        id: contentParallax

                        x: styleSurface.elongated && longFrame.item ? (islandWindow.leftEdge ? -1 :
                                                                                                 islandWindow.rightEdge
                                                                                                 ? 1 : 0)
                                                                      * longFrame.item.contentOffset : 0
                        y: styleSurface.elongated && longFrame.item ? (islandWindow.topEdge ? -1 :
                                                                                                islandWindow.bottomEdge
                                                                                                ? 1 : 0)
                                                                      * longFrame.item.contentOffset : 0
                    }
                    enabled: !styleSurface.elongated || root.opacity > 0.1
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 1600
                    height: 1200

                    KeyboardLockIndicator {
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: islandWindow.horizontalEdge ? 260 : 112
                        height: islandWindow.horizontalEdge ? 64 : 144
                        vertical: !islandWindow.horizontalEdge
                        capsLock: root.sliderMode === "capslock"
                        lockEnabled: root.lockEnabled
                        visible: root.isVolumeMode && root.keyboardOsd
                    }

                    VolumeContent {
                        id: volumeWidget

                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: root.activeLayout.volumeWidth
                        height: root.activeLayout.volumeHeight
                        vertical: !islandWindow.horizontalEdge
                        mode: root.sliderMode
                        audioNode: root.sliderMode === "volume" ? root.audioNode : root.sliderMode === "mic"
                                                                  ? root.sourceAudioNode : null
                        externalValue: BrightnessService.brightnessValue
                        iconName: root.sliderMode === "brightness" ? "brightness_medium" : ""
                        opacity: root.isVolumeMode && !root.keyboardOsd ? 1 : 0
                        visible: opacity > 0.01
                        onMoved: value => {
                            if (root.sliderMode === "brightness")
                                BrightnessService.setBrightness(value);
                        }

                        Behavior on opacity {
                            NumberAnimation {
                                duration: Appearance.animation.expressiveEffects.duration
                                easing.type: Appearance.animation.expressiveEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                            }
                        }
                    }

                    NotificationContent {
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.topMargin: 10
                        width: root.notifW - 20
                        height: root.notifH - 20
                        manager: NotificationService
                        opacity: root.isNotifMode ? 1 : 0
                        visible: opacity > 0.01

                        Behavior on opacity {
                            NumberAnimation {
                                duration: Appearance.animation.expressiveEffects.duration
                                easing.type: Appearance.animation.expressiveEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                            }
                        }
                    }

                    Item {
                        id: lyricsWidget
                        implicitWidth: 0
                        implicitHeight: 0
                        visible: false
                    }

                    // Keep the media surface alive for its exit fade, but do not
                    // construct MediaContent (and its position tracking) until it is
                    // actually wanted.  In particular, active must not be bound to
                    // wanted: that would destroy the item at the first frame of the
                    // fade-out.
                    Item {
                        id: mediaWidget

                        readonly property bool wanted: !root.contentPresentationActive && root.expanded
                                                       && !root.isLyricsMode && !root.isHubMode
                        property bool fadeHeld: false
                        property int lifecycleGeneration: 0
                        property int releaseGeneration: 0
                        readonly property bool loaded: mediaLoader.status === Loader.Ready
                        readonly property bool coverColors: loaded && mediaLoader.item.coverColors
                        readonly property bool backgroundCover: loaded && mediaLoader.item.backgroundCover
                        readonly property string artUrl: loaded ? mediaLoader.item.artUrl : ""
                        readonly property color surfaceColor: loaded ? mediaLoader.item.surfaceColor :
                                                                      Appearance.colors.colLayer0
                        readonly property real panelWidth: loaded ? mediaLoader.item.panelWidth :
                                                                    (backgroundCover ? 640 : 540)
                        readonly property real panelHeight: loaded ? mediaLoader.item.panelHeight :
                                                                     (backgroundCover ? 240 : 210)

                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.topMargin: 20
                        width: root.activeLayout.expandedWidth - 40
                        height: root.activeLayout.expandedHeight - 40
                        opacity: wanted && loaded ? 1 : 0
                        visible: fadeHeld && opacity > 0.01

                        onWantedChanged: {
                            lifecycleGeneration++;
                            if (wanted) {
                                releaseTimer.stop();
                                fadeHeld = true;
                            } else if (!loaded) {
                                // Abort a load that lost its consumer.  A late
                                // onLoaded must not resurrect this proxy.
                                releaseTimer.stop();
                                fadeHeld = false;
                            } else {
                                // Keep the loaded child for the exit fade, but
                                // bound its lifetime even if the animation is
                                // interrupted before onStopped runs.
                                releaseGeneration = lifecycleGeneration;
                                releaseTimer.restart();
                            }
                        }

                        Timer {
                            id: releaseTimer
                            interval: Appearance.animation.expressiveEffects.duration + 50
                            repeat: false
                            onTriggered: {
                                if (!mediaWidget.wanted && mediaWidget.opacity <= 0.01
                                        && mediaWidget.releaseGeneration === mediaWidget.lifecycleGeneration)
                                    mediaWidget.fadeHeld = false;
                            }
                        }

                        Behavior on opacity {
                            NumberAnimation {
                                duration: Appearance.animation.expressiveEffects.duration
                                easing.type: Appearance.animation.expressiveEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                                onStopped: {
                                    if (!mediaWidget.wanted && mediaWidget.opacity <= 0.01)
                                        mediaWidget.fadeHeld = false;
                                }
                            }
                        }

                        Loader {
                            id: mediaLoader
                            anchors.fill: parent
                            active: mediaWidget.fadeHeld
                            sourceComponent: MediaContent {
                                visible: mediaWidget.visible
                                opacity: mediaWidget.opacity
                                surfaceTopRightRadius: styleSurface.elongated && longFrame.item
                                                       ? longFrame.item.childRadius : rootSurface.topRightRadius
                            }
                            onLoaded: {
                                // A load can finish after wanted became false.
                                // Only a current consumer or an existing fade may
                                // enter; never re-arm a released proxy.
                                if (mediaWidget.wanted || mediaWidget.fadeHeld)
                                    mediaWidget.fadeHeld = true;
                                else
                                    mediaWidget.fadeHeld = false;
                            }
                        }
                    }

                    HubContent {
                        id: hub

                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: implicitWidth
                        height: implicitHeight
                        screen: islandWindow.screen
                        onCurrentIndexChanged: {
                            if (root.hubTabIndex !== currentIndex)
                                root.hubTabIndex = currentIndex;
                        }
                        Component.onCompleted: {
                            if (currentIndex !== root.hubTabIndex)
                                currentIndex = root.hubTabIndex;
                        }
                        onCloseRequested: root.showHub = false
                        onAvatarEditRequested: {
                            root.showHub = false;
                            styleSurface.avatarEditRequested(islandWindow.screen);
                        }
                        opacity: root.isHubMode ? 1 : 0
                        visible: opacity > 0.01

                        Behavior on opacity {
                            NumberAnimation {
                                duration: Appearance.animation.expressiveEffects.duration
                                easing.type: Appearance.animation.expressiveEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                            }
                        }
                    }

                    // Keep the public geometry/focus target stable while the tools
                    // subtree is absent. Backend sessions outlive this visual child.
                    FocusScope {
                        id: toolsWidget

                        readonly property bool wanted: root.isToolsMode || RecordingService.isActive
                                                       || AudioRecordingService.isActive
                        property bool fadeHeld: false
                        readonly property bool loaded: toolsLoader.status === Loader.Ready
                                                       && toolsLoader.item !== null
                        readonly property bool keyboardActive: root.isToolsMode && !root.recordingLaunchPending
                        readonly property bool vertical: !islandWindow.horizontalEdge
                        implicitWidth: loaded ? toolsLoader.item.implicitWidth : (vertical ? 72 : 480)
                        implicitHeight: loaded ? toolsLoader.item.implicitHeight : (vertical ? 480 : 72)
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: implicitWidth
                        height: implicitHeight
                        opacity: root.isToolsMode && loaded ? 1 : 0
                        visible: opacity > 0.01
                        focus: keyboardActive

                        onWantedChanged: {
                            if (wanted)
                                fadeHeld = true;
                            else if (opacity === 0 && !toolsFade.running)
                                fadeHeld = false;
                        }

                        Behavior on opacity {
                            NumberAnimation {
                                id: toolsFade
                                duration: Appearance.animation.expressiveEffects.duration
                                easing.type: Appearance.animation.expressiveEffects.type
                                easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                                onStopped: {
                                    if (!toolsWidget.wanted && toolsWidget.opacity === 0)
                                        toolsWidget.fadeHeld = false;
                                }
                            }
                        }

                        Loader {
                            id: toolsLoader

                            anchors.fill: parent
                            active: toolsWidget.wanted || toolsWidget.fadeHeld
                            focus: toolsWidget.keyboardActive
                            sourceComponent: ToolsContent {
                                keyboardActive: toolsWidget.keyboardActive
                                retainForRecording: styleSurface.elongated
                                vertical: toolsWidget.vertical
                                edge: islandWindow.edge
                                onRequestHideIsland: root.showTools = false
                                onRecordingRequested: {
                                    // Selection/startup keep the backend and tools alive;
                                    // cancellation leaves the existing selection usable.
                                    root.hoverOpened = false;
                                    hoverIntent.cancel();
                                }
                            }
                            onLoaded: {
                                // State/focus signals may have arrived before creation.
                                // Replay only UI consumer state, never stop a session.
                                root.syncRecordingConsumer();
                                root.syncAudioConsumer();
                                if (toolsWidget.keyboardActive)
                                    root.requestKeyboardFocus();
                            }
                        }
                    }
                }

                Connections {
                    function onTransientSurfacesDismissRequested() {
                        root.closeIslandPopups();
                    }

                    target: WidgetState
                }

                MouseArea {
                    id: collapsedInputArea

                    anchors.fill: parent
                    z: 10000
                    enabled: root.isCollapsedMode
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                    onClicked: mouse => {
                        root.activateMouseAction(mouse.button === Qt.MiddleButton
                                                 ? PersonalizationConfig.islandMiddleClickAction :
                                                   PersonalizationConfig.islandLeftClickAction, true);
                        mouse.accepted = true;
                    }
                }

                Behavior on width {
                    enabled: !styleSurface.elongated && !(styleSurface.splitRecording
                                                          && root.recordingPresentationActive
                                                          && islandWindow.horizontalEdge)

                    NumberAnimation {
                        duration: root.wDuration
                        easing.type: IslandMotion.type
                        easing.bezierCurve: root.wBezier
                    }
                }

                Behavior on height {
                    enabled: !styleSurface.elongated && !(styleSurface.splitRecording
                                                          && root.recordingPresentationActive &&
                                                          !islandWindow.horizontalEdge)

                    NumberAnimation {
                        duration: root.hDuration
                        easing.type: IslandMotion.type
                        easing.bezierCurve: root.hBezier
                    }
                }

                Behavior on radius {
                    NumberAnimation {
                        duration: root.rDuration
                        easing.type: IslandMotion.type
                        easing.bezierCurve: root.rBezier
                    }
                }
            }

            // The audio visual is a session-owned child, not a permanently resident
            // shell object. Keep its host (and therefore geometry) stable while the
            // visual fades, then let the Loader destroy it after the exit sequence.
            Item {
                id: audioRecordingHost

                parent: styleSurface.elongated ? root : maskContainer
                anchors.centerIn: root
                width: root.width
                height: root.height
                z: root.z + 3
                property bool fadeHeld: false
                readonly property bool wanted: root.audioPresentationActive || AudioRecordingService.isActive
                readonly property bool loaded: audioRecordingLoader.status === Loader.Ready
                                               && audioRecordingLoader.item !== null

                function isCurrent(instance) {
                    return instance !== null && audioRecordingLoader.item === instance;
                }

                function beginEntry() {
                    fadeHeld = true;
                    if (loaded && root.audioPresentationActive)
                        audioRecordingLoader.item.beginEntry();
                }

                function beginExit() {
                    if (loaded && isCurrent(audioRecordingLoader.item))
                        audioRecordingLoader.item.beginExit();
                }

                function finishExit(instance) {
                    if (!isCurrent(instance) || root.audioSessionActive)
                        return;
                    root.audioPresentationPhase = root.audioPhaseHidden;
                    fadeHeld = false;
                }

                visible: loaded && (root.audioPresentationActive || fadeHeld
                                    || audioRecordingLoader.item.contentProgress > 0.01)
                opacity: 1

                onWantedChanged: {
                    if (wanted)
                        fadeHeld = true;
                    else if (!loaded || audioRecordingLoader.item.contentProgress <= 0.01)
                        fadeHeld = false;
                }

                Loader {
                    id: audioRecordingLoader

                    anchors.fill: parent
                    active: audioRecordingHost.wanted || audioRecordingHost.fadeHeld
                    sourceComponent: AudioRecordingVisual {
                        id: audioVisual

                        sessionActive: root.audioPresentationActive
                        recording: AudioRecordingService.isRecording
                        stopping: AudioRecordingService.isStopPending
                        sourceNodeName: AudioRecordingService.sourceNodeName
                        captureSink: AudioRecordingService.captureSink
                        elapsedMs: AudioRecordingService.elapsedMs
                        vertical: !islandWindow.horizontalEdge
                        edge: islandWindow.edge
                        visible: root.audioPresentationActive || contentProgress > 0.01
                        opacity: 1
                        onStopRequested: AudioRecordingService.stop()
                        onCollapseRequested: {
                            if (audioRecordingHost.isCurrent(audioVisual) && !root.audioSessionActive)
                                root.audioPresentationPhase = root.audioPhaseCollapsing;
                        }
                        onExitFinished: audioRecordingHost.finishExit(audioVisual)
                    }
                    onLoaded: {
                        // The service can change while QML is compiling the child.
                        // Never replay an obsolete load into a newer session.
                        if (!audioRecordingHost.wanted) {
                            // Keep the active binding intact so a later session can
                            // create a fresh child after this one is released.
                            audioRecordingHost.fadeHeld = false;
                            return;
                        }
                        if (root.audioPresentationActive)
                            item.beginEntry();
                    }
                }
            }

            ClockContent {
                id: clockContent

                anchors.fill: root
                player: root.currentPlayer
                edge: islandWindow.edge
                opacity: !styleSurface.elongated && root.isCollapsedMode ? 1 : 0
                scale: 0.96 + 0.04 * opacity
                visible: opacity > 0.01
                z: root.z + 4

                transform: Translate {
                    y: (1 - clockContent.opacity) * 4
                }

                Behavior on opacity {
                    NumberAnimation {
                        duration: root.isCollapsedMode ? Appearance.animation.expressiveSlowEffects.duration :
                                                         Appearance.animation.expressiveFastEffects.duration
                        easing.type: root.isCollapsedMode ? Appearance.animation.expressiveSlowEffects.type :
                                                            Appearance.animation.expressiveFastEffects.type
                        easing.bezierCurve: root.isCollapsedMode
                                            ? Appearance.animation.expressiveSlowEffects.bezierCurve :
                                              Appearance.animation.expressiveFastEffects.bezierCurve
                    }
                }
            }

            Loader {
                id: pillRecordingPresenter

                anchors.fill: root
                active: styleSurface.splitRecording && root.recordingPresentationActive
                visible: active
                sourceComponent: islandWindow.horizontalEdge ? horizontalPillRecordingComponent :
                                                                 verticalPillRecordingComponent
                z: root.z + 2
            }

            Component {
                id: horizontalPillRecordingComponent

                HorizontalPillRecordingVisual {
                    active: root.recordingPresentationActive
                    recording: root.isRecording
                    finalizing: root.isFinalizing
                    recordingType: RecordingService.recordingType
                    elapsedMs: RecordingService.elapsedMs
                    morphProgress: root.pillMorphProgress
                    recordingInfoProgress: root.recordingInfoProgress
                    recordingActionProgress: root.recordingActionProgress
                    processingContentProgress: root.processingContentProgress
                    baseMainWidth: horizontalLayout.collapsedWidth
                    layoutHeight: horizontalLayout.collapsedHeight
                    edge: islandWindow.edge
                }
            }

            Component {
                id: verticalPillRecordingComponent

                VerticalPillRecordingVisual {
                    active: root.recordingPresentationActive
                    recording: root.isRecording
                    finalizing: root.isFinalizing
                    recordingType: RecordingService.recordingType
                    elapsedMs: RecordingService.elapsedMs
                    morphProgress: root.pillMorphProgress
                    recordingInfoProgress: root.recordingInfoProgress
                    recordingActionProgress: root.recordingActionProgress
                    processingContentProgress: root.processingContentProgress
                    baseMainHeight: verticalLayout.collapsedHeight
                    layoutWidth: verticalLayout.collapsedWidth
                    edge: islandWindow.edge
                }
            }

            Connections {
                function onStopRequested() {
                    if (!RecordingService.stop())
                        return;

                    root.pillStopFusionMinimumActive = true;
                }

                target: pillRecordingPresenter.item
            }

            BangsRecordingVisual {
                id: bangsRecordingVisual

                parent: styleSurface.elongated ? root : maskContainer
                anchors.centerIn: root
                width: root.width
                height: root.height
                opacity: entryProgress
                active: !styleSurface.splitRecording && root.recordingPresentationActive
                recording: !styleSurface.splitRecording && root.isRecording
                finalizing: !styleSurface.splitRecording && root.isFinalizing
                recordingType: RecordingService.recordingType
                elapsedMs: RecordingService.elapsedMs
                recordingInfoProgress: root.recordingInfoProgress
                recordingActionProgress: root.recordingActionProgress
                processingContentProgress: root.processingContentProgress
                vertical: !islandWindow.horizontalEdge
                edge: islandWindow.edge
                visible: !styleSurface.splitRecording && (active || opacity > 0.01)
                z: root.z + 2
                onStopRequested: RecordingService.stop()
            }

            CompositorBlurRegion {
                targetWindow: islandWindow
                backgroundItem: styleSurface.elongated || root.useRecordingBlurRegions ? null : root
                additionalBackgroundItems: styleSurface.elongated && longFrame.item
                                           ? longFrame.item.blurItems : root.recordingBlurBackgroundItems
                subtractedBackgroundItems: !root.showDashboardKeyhole ? [] : styleSurface.elongated
                                                                        && longFrame.item
                                                                        ? [longFrame.item.cutoutBlurItem] :
                                                                          [dashboardKeyholeCutout]
                postSubtractionBackgroundItems: root.showDashboardKeyhole && root.visible && root.opacity
                                                > 0.01 && hub.opacity > 0.01 ? hub.dashboardKeyholeGlassItems :
                                                                               []
                postSubtractionClipItem: styleSurface.elongated && longFrame.item
                                         ? longFrame.item.childBlurItem : root
                radius: root.radius
            }
        }

        mask: Region {
            Region {
                item: styleSurface.elongated ? (longFrame.item ? longFrame.item.mainItem : null) :
                                               maskContainer

                radius: styleSurface.elongated ? 21 : 0
            }
            Region {
                item: styleSurface.elongated && longFrame.item && longFrame.item.progress > 0.02 ? root : null
                radius: styleSurface.elongated && longFrame.item ? longFrame.item.childRadius : 0
            }

            HotCornerExclusionRegion {
                active: NiriConfigService.ready("hot-corners")
                cornerActions: PersonalizationConfig.hotCornerActions
                surfaceWidth: islandWindow.width
                surfaceHeight: islandWindow.height
            }
        }
    }

    component SurfaceShape: Canvas {

        required property color surfaceColor
        required property real topLeftRadius
        required property real topRightRadius
        required property real bottomRightRadius
        required property real bottomLeftRadius
        required property bool cutoutVisible
        required property real cutoutX
        required property real cutoutY
        required property real cutoutWidth
        required property real cutoutHeight
        required property real cutoutRadius

        function addRoundedRect(context, x, y, width, height, topLeft, topRight, bottomRight, bottomLeft) {
            const maxRadius = Math.min(width / 2, height / 2);
            const tl = Math.min(topLeft, maxRadius);
            const tr = Math.min(topRight, maxRadius);
            const br = Math.min(bottomRight, maxRadius);
            const bl = Math.min(bottomLeft, maxRadius);
            context.beginPath();
            context.moveTo(x + tl, y);
            context.lineTo(x + width - tr, y);
            context.quadraticCurveTo(x + width, y, x + width, y + tr);
            context.lineTo(x + width, y + height - br);
            context.quadraticCurveTo(x + width, y + height, x + width - br, y + height);
            context.lineTo(x + bl, y + height);
            context.quadraticCurveTo(x, y + height, x, y + height - bl);
            context.lineTo(x, y + tl);
            context.quadraticCurveTo(x, y, x + tl, y);
            context.closePath();
        }

        anchors.fill: parent
        antialiasing: true
        onPaint: {
            const context = getContext("2d");
            context.reset();
            context.clearRect(0, 0, width, height);
            addRoundedRect(context, 0, 0, width, height, topLeftRadius, topRightRadius, bottomRightRadius,
                           bottomLeftRadius);
            context.fillStyle = surfaceColor;
            context.fill();
            if (cutoutVisible) {
                context.globalCompositeOperation = "destination-out";
                addRoundedRect(context, cutoutX, cutoutY, cutoutWidth, cutoutHeight, cutoutRadius,
                               cutoutRadius, cutoutRadius, cutoutRadius);
                context.fillStyle = "white";
                context.fill();
                context.globalCompositeOperation = "source-over";
            }
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onSurfaceColorChanged: requestPaint()
        onTopLeftRadiusChanged: requestPaint()
        onTopRightRadiusChanged: requestPaint()
        onBottomRightRadiusChanged: requestPaint()
        onBottomLeftRadiusChanged: requestPaint()
        onCutoutVisibleChanged: requestPaint()
        onCutoutXChanged: requestPaint()
        onCutoutYChanged: requestPaint()
        onCutoutWidthChanged: requestPaint()
        onCutoutHeightChanged: requestPaint()
        onCutoutRadiusChanged: requestPaint()
    }
}

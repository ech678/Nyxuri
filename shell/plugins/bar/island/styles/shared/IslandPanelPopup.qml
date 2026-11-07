import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.commons
import qs.services
import qs.ui
import "../../hub"
import "../../tools"

// Anchored panel popup (B2-1): the hub and tools panels leave the island
// surface and open as an edge-anchored popup that grows from the capsule
// bounds, following the tree's TrayMenu PopupWindow paradigm. One popup per
// island surface (per screen); hub and tools are exclusive faces of the same
// shell, so a single popup carries both and the island surface keeps owning
// the open/close flags.
PopupWindow {
    id: root

    required property Item anchorItem
    required property string edge

    readonly property bool horizontalEdge: edge === "top" || edge === "bottom"
    property bool hubOpen: false
    property bool toolsOpen: false
    // True while the island presents recording/audio content: the popup hides
    // without closing, matching how the inline faces used to fade out.
    property bool suppressed: false
    property bool retainForRecording: false
    property bool recordingLaunchPending: false
    property int hubTabIndex: 0
    readonly property int popupPadding: 10

    readonly property bool open: (root.hubOpen || root.toolsOpen) && !root.suppressed

    signal closeRequested
    signal hubTabRequested(int index)
    signal avatarEditRequested(var screen)
    signal recordingRequested

    visible: root.open
    color: "transparent"
    grabFocus: ThemeService.isNiriSession

    implicitWidth: popupBackground.width + root.popupPadding * 2
    implicitHeight: popupBackground.height + root.popupPadding * 2

    // The island surface owns hubTabIndex; the popup content mirrors it in
    // both directions (init on creation, edits flow back through the signal).
    onHubTabIndexChanged: {
        if (hub.currentIndex !== root.hubTabIndex)
            hub.currentIndex = root.hubTabIndex;
    }

    onVisibleChanged: {
        if (!visible)
            return;

        entryScale.xScale = 0.72;
        entryScale.yScale = 0.72;
        entryWrapper.opacity = 0;
        entryAnimation.restart();
        keyScope.forceActiveFocus();
    }

    anchor {
        item: root.anchorItem
        rect.x: 0
        rect.y: 0
        rect.width: Math.max(1, root.anchorItem ? root.anchorItem.width : 1)
        rect.height: Math.max(1, root.anchorItem ? root.anchorItem.height : 1)
        edges: root.edge === "left" ? Edges.Right : root.edge === "right" ? Edges.Left : root.edge === "bottom" ? Edges.Top : Edges.Bottom
        gravity: root.edge === "left" ? Edges.Right : root.edge === "right" ? Edges.Left : root.edge === "bottom" ? Edges.Top : Edges.Bottom
        adjustment: root.horizontalEdge ? PopupAdjustment.SlideX : PopupAdjustment.SlideY
    }

    PanelWindow {
        visible: root.visible && ThemeService.isNiriSession
        screen: root.screen
        color: "transparent"
        exclusiveZone: 0
        WlrLayershell.layer: root.anchorItem && root.anchorItem.QsWindow.window ? root.anchorItem.QsWindow.window.WlrLayershell.layer : WlrLayer.Top
        WlrLayershell.namespace: "nyxuri-shell-island-panel-backdrop"
        WlrLayershell.exclusionMode: ExclusionMode.Ignore

        anchors {
            top: true
            bottom: true
            left: true
            right: true
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onClicked: root.closeRequested()
        }
    }

    FocusScope {
        id: keyScope

        anchors.fill: parent
        focus: root.visible
        Keys.onEscapePressed: event => {
            root.closeRequested();
            event.accepted = true;
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.BackButton | Qt.RightButton
            onClicked: event => {
                root.closeRequested();
                event.accepted = true;
            }
        }

        Item {
            id: entryWrapper

            anchors.fill: parent
            transform: Scale {
                id: entryScale

                // Grow from the capsule-facing corner of the popup.
                origin.x: root.edge === "left" ? root.popupPadding : root.edge === "right" ? root.width - root.popupPadding : root.width / 2
                origin.y: root.edge === "top" ? root.popupPadding : root.edge === "bottom" ? root.height - root.popupPadding : root.height / 2
            }

            StyledRectangularShadow {
                target: popupBackground
                opacity: popupBackground.opacity
            }

            SurfaceShape {
                id: popupBackground

                anchors.fill: null
                x: root.popupPadding
                y: root.popupPadding
                width: root.hubOpen ? hub.implicitWidth : tools.implicitWidth
                height: root.hubOpen ? hub.implicitHeight : tools.implicitHeight
                surfaceColor: BlurService.backgroundColor(Appearance.colors.colLayer0)
                topLeftRadius: 24
                topRightRadius: 24
                bottomRightRadius: 24
                bottomLeftRadius: 24
                cutoutVisible: root.hubOpen
                cutoutX: keyholeCutout.x
                cutoutY: keyholeCutout.y
                cutoutWidth: keyholeCutout.width
                cutoutHeight: keyholeCutout.height
                cutoutRadius: keyholeCutout.radius
            }

            Item {
                id: contentHost

                x: root.popupPadding
                y: root.popupPadding
                width: popupBackground.width
                height: popupBackground.height
                clip: true

                HubContent {
                    id: hub

                    anchors.fill: parent
                    screen: root.screen
                    visible: root.hubOpen
                    Component.onCompleted: {
                        if (currentIndex !== root.hubTabIndex)
                            currentIndex = root.hubTabIndex;
                    }
                    onCurrentIndexChanged: root.hubTabRequested(currentIndex)
                    onCloseRequested: root.closeRequested()
                    onAvatarEditRequested: root.avatarEditRequested(root.screen)
                }

                ToolsContent {
                    id: tools

                    anchors.fill: parent
                    keyboardActive: root.toolsOpen && !root.recordingLaunchPending
                    retainForRecording: root.retainForRecording
                    vertical: !root.horizontalEdge
                    edge: root.edge
                    visible: root.toolsOpen
                    onRequestHideIsland: root.closeRequested()
                    onRecordingRequested: root.recordingRequested()
                }

                // Geometry marker for the keyhole hole in the popup background;
                // the glass card renders above it through blur subtraction.
                Rectangle {
                    id: keyholeCutout

                    width: 340
                    height: 456
                    anchors.left: parent.horizontalCenter
                    anchors.leftMargin: hub.dashboardKeyholeCenterOffset
                    anchors.top: parent.top
                    anchors.topMargin: 132
                    radius: 24
                    color: "transparent"
                    visible: root.hubOpen
                }
            }

            ParallelAnimation {
                id: entryAnimation

                NumberAnimation {
                    target: entryWrapper
                    property: "opacity"
                    from: 0
                    to: 1
                    duration: Appearance.animation.expressiveEffects.duration
                    easing.type: Appearance.animation.expressiveEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                }

                NumberAnimation {
                    target: entryScale
                    property: "xScale"
                    from: 0.72
                    to: 1
                    duration: Appearance.animation.expressiveEffects.duration
                    easing.type: Appearance.animation.expressiveEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                }

                NumberAnimation {
                    target: entryScale
                    property: "yScale"
                    from: 0.72
                    to: 1
                    duration: Appearance.animation.expressiveEffects.duration
                    easing.type: Appearance.animation.expressiveEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveEffects.bezierCurve
                }
            }
        }
    }

    CompositorBlurRegion {
        targetWindow: root
        backgroundItem: popupBackground
        subtractedBackgroundItems: root.hubOpen ? [keyholeCutout] : []
        postSubtractionBackgroundItems: root.hubOpen && hub.visible ? hub.dashboardKeyholeGlassItems : []
        radius: 24
    }
}

pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.commons
import qs.ui
import qs.services
import "BarStyle.js" as BarStyle

LazyLoader {
    id: root

    property Item hoverTarget
    property bool hoverActivates: true
    property bool closeOnOutsideClick: false
    property bool popupHovered: false
    // D4d: the intent delay is the bar-level hoverPopoutDelay axis (150ms
    // default, D4d-1 decision — the old 400ms hardcode retired with it).
    property var widgetBar: null
    readonly property var barAxes: widgetBar ? widgetBar.axes : PersonalizationConfig.barAxes
    property int hoverOpenDelay: root.barAxes.hoverPopoutDelay
    // D4d: explicit-open path for click-driven popups (the lane overflow
    // button). The hover machinery stays untouched; pinnedOpen simply
    // forces active. Callers must move hosted items back OUT of the popup
    // content before clearing pinnedOpen — the window (and its content
    // tree) is destroyed on deactivate.
    property bool pinnedOpen: false
    default property Item contentItem
    property real popupBackgroundMargin: 0

    signal requestClose

    readonly property bool targetHovered: hoverTarget && (hoverTarget.containsMouse ?? hoverTarget.buttonHovered ?? false)

    // The popup stays up while the pointer is over the bar item OR over the popup
    // itself, with a grace period for the masked gap between them. Keying `active`
    // on the bar item alone made every popup close the moment you moved towards it.
    readonly property bool hoverWanted: root.hoverActivates && (root.targetHovered || root.popupHovered)
    property bool _hoverHold: false

    onHoverWantedChanged: {
        if (root.hoverWanted) {
            root.hoverCloseTimer.stop();
            if (!root._hoverHold)
                root.hoverOpenTimer.restart();
        } else {
            root.hoverOpenTimer.stop();
            root.hoverCloseTimer.restart();
        }
    }

    property Timer hoverOpenTimer: Timer {
        interval: root.hoverOpenDelay
        repeat: false
        onTriggered: {
            if (root.hoverWanted)
                root._hoverHold = true;
        }
    }

    // A property, not an inline child: the default property here is
    // `contentItem`, so a bare Timer never gets assigned and its id never exists.
    property Timer hoverCloseTimer: Timer {
        interval: 220
        repeat: false
        onTriggered: root._hoverHold = false
    }

    active: root._hoverHold || root.pinnedOpen

    onActiveChanged: {
        if (!root.active)
            root.popupHovered = false;
    }

    // B9.4: the bar edge is the single truth (end4 derived "right" from a
    // bottom bool, which sent a right-edge popup to the left side).
    // D4e: the owning bar's routing axes when threaded (multi-bar), else
    // the settings-facing entry.
    readonly property string barEdge: root.widgetBar ? root.barAxes.position : (Config.options?.bar?.edge ?? "top")
    readonly property bool barVertical: root.barEdge === "left" || root.barEdge === "right"
    // B9.5/D4f: popups start after the outer edge margin the bar reserves.
    readonly property real barEdgeMargin: root.widgetBar ? root.barAxes.edgeMargin : (Config.options?.bar?.edgeMargin ?? 5)
    readonly property real barThickness: (root.barVertical ? PersonalizationConfig.resolvedVerticalBarWidth(root.barAxes) : PersonalizationConfig.resolvedBarHeight(root.barAxes)) + root.barEdgeMargin

    PanelWindow {
        id: clickOutsideBackdrop
        visible: root.active && root.closeOnOutsideClick
        color: Qt.rgba(0, 0, 0, 1 / 255)
        exclusiveZone: 0
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.namespace: "quickshell:m3-popup-catcher"
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
            onClicked: root.requestClose()
        }
    }

    component: PanelWindow {
        id: popupWindow

        property Item innerContent: root.contentItem

        color: "transparent"
        anchors.left: root.barEdge !== "right"
        anchors.right: root.barEdge === "right"
        anchors.top: root.barEdge !== "bottom"
        anchors.bottom: root.barEdge === "bottom"

        implicitWidth: popupBackground.implicitWidth + Appearance.sizes.elevationMargin * 2 + root.popupBackgroundMargin
        implicitHeight: popupBackground.implicitHeight + Appearance.sizes.elevationMargin * 2 + root.popupBackgroundMargin

        readonly property real centerOffsetX: {
            const base = root.QsWindow?.mapFromItem(root.hoverTarget, ((root.hoverTarget?.width ?? 0) - popupBackground.implicitWidth) / 2, 0).x ?? Appearance.sizes.elevationMargin;
            const margin = Appearance.sizes.elevationMargin;
            const maxLeft = Math.max(margin, (popupWindow.screen?.width ?? popupBackground.implicitWidth) - popupBackground.implicitWidth - margin);
            return Math.max(margin, Math.min(base, maxLeft));
        }

        readonly property real centerOffsetY: {
            const base = root.QsWindow?.mapFromItem(root.hoverTarget, 0, ((root.hoverTarget?.height ?? 0) - popupBackground.implicitHeight) / 2).y ?? Appearance.sizes.elevationMargin;
            const margin = Appearance.sizes.elevationMargin;
            const maxTop = Math.max(margin, (popupWindow.screen?.height ?? popupBackground.implicitHeight) - popupBackground.implicitHeight - margin);
            return Math.max(margin, Math.min(base, maxTop));
        }

        mask: Region {
            item: popupBackground
        }
        exclusionMode: ExclusionMode.Ignore
        exclusiveZone: 0

        margins {
            left: {
                if (root.barEdge === "right")
                    return 0;
                if (root.barEdge === "left")
                    return root.barThickness;
                return popupWindow.centerOffsetX;
            }
            top: {
                if (root.barEdge === "bottom")
                    return 0;
                if (root.barEdge === "top")
                    return root.barThickness;
                return popupWindow.centerOffsetY;
            }
            right: root.barEdge === "right" ? root.barThickness : 0
            bottom: root.barEdge === "bottom" ? root.barThickness : 0
        }

        WlrLayershell.namespace: "quickshell:m3-popup"
        WlrLayershell.layer: WlrLayer.Overlay

        HoverHandler {
            onHoveredChanged: root.popupHovered = hovered
        }

        StyledRectangularShadow {
            target: popupBackground
        }

        Rectangle {
            id: popupBackground
            readonly property real margin: 8
            property bool shown: false

            anchors {
                fill: parent
                leftMargin: Appearance.sizes.elevationMargin + root.popupBackgroundMargin * (!popupWindow.anchors.left)
                rightMargin: Appearance.sizes.elevationMargin + root.popupBackgroundMargin * (!popupWindow.anchors.right)
                topMargin: Appearance.sizes.elevationMargin + root.popupBackgroundMargin * (!popupWindow.anchors.top)
                bottomMargin: Appearance.sizes.elevationMargin + root.popupBackgroundMargin * (!popupWindow.anchors.bottom)
            }

            implicitWidth: (popupWindow.innerContent?.implicitWidth ?? 0) + margin * 2
            implicitHeight: (popupWindow.innerContent?.implicitHeight ?? 0) + margin * 2

            color: Appearance.colors.colLayer1Base
            radius: Appearance.rounding.large + 5
            border.width: 1
            border.color: Appearance.colors.colLayer0Border
            opacity: shown ? 1 : 0
            scale: shown ? 1 : 0.94
            transformOrigin: root.barEdge === "bottom" ? Item.Bottom : root.barEdge === "left" ? Item.Left : root.barEdge === "right" ? Item.Right : Item.Top

            Behavior on opacity {
                enabled: Appearance.animationsEnabled
                NumberAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                }
            }
            Behavior on scale {
                enabled: Appearance.animationsEnabled
                NumberAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                    easing.type: Appearance.animation.elementMoveFast.type
                    easing.bezierCurve: Appearance.animation.elementMoveFast.bezierCurve
                }
            }

            Component.onCompleted: {
                if (popupWindow.innerContent) {
                    popupWindow.innerContent.parent = popupBackground;
                    popupWindow.innerContent.anchors.centerIn = popupBackground;
                }
                shown = true;
            }
        }
    }
}

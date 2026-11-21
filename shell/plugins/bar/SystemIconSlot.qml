// Fork & Trim: end4-pC modules/ii/bar/UtilButton.qml (via shell/plugins/bar/UtilButton.qml)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// D2 SystemIcons QS expansion (ROADMAP D-2):
//   - UtilButton 26↔54px hover expansion skeleton (200ms) with 150ms intent
//     delay to prevent jitter from rapid mouse sweeps;
//   - expanded area presents one line of status data (volume %, SSID, Bluetooth
//     device count, peripheral battery %, etc.);
//   - non-expandable / data-less slots (e.g. keyboard) maintain fixed 26px size;
//   - the hover capsule keeps the util-button language: material uses
//     primary/primaryForeground, non-material colLayer1Hover + contentColor;
//   - contentColor/contentColorOverridden carry BarGroup's per-widget style
//     override into the glyphs and data labels;
//   - `wheeled(delta)` exposes the scroll gesture (volume slot);
//   - clicking still triggers quicksettings sidebar or toggle actions.

import QtQuick
import Quickshell
import qs.commons
import qs.ui
import qs.services

Item {
    id: root

    signal clicked(event: var)
    signal wheeled(real delta)

    property alias iconText: symbol.text
    property bool isActive: false
    property bool forceHovered: false
    property bool forceExpanded: false
    property bool vertical: false
    property bool clickable: true
    property bool expandable: true
    property string toolTipText: ""
    property string dataText: ""
    // Stable identity for the runtime probe; user-visible nothing.
    property string slotKey: ""
    property color contentColor: Appearance.colors.colOnLayer1
    property bool contentColorOverridden: false
    property bool isMaterial: PersonalizationConfig.barIsMaterial
    default property alias content: contentHost.data

    readonly property bool hovered: mouseArea.containsMouse || root.forceHovered
    readonly property color resolvedContentColor: root.contentColorOverridden ? root.contentColor : (root.isMaterial ? M3Palette.pillInk("systemIcons") : Appearance.colors.colOnLayer1)
    readonly property int slotSize: 26
    readonly property int expandedSize: 54
    readonly property int intentDelay: 150

    readonly property bool canExpand: root.expandable && root.dataText.length > 0
    property bool intentHovered: false
    readonly property bool expanded: root.canExpand && (root.intentHovered || root.forceExpanded)

    Timer {
        id: intentTimer
        interval: root.intentDelay
        repeat: false
        onTriggered: {
            if (root.hovered) {
                root.intentHovered = true;
            }
        }
    }

    onHoveredChanged: {
        if (hovered) {
            if (root.forceHovered && root.intentDelay <= 0) {
                root.intentHovered = true;
            } else {
                intentTimer.restart();
            }
        } else {
            intentTimer.stop();
            root.intentHovered = false;
        }
    }

    implicitWidth: root.vertical ? root.slotSize : (root.expanded ? root.expandedSize : root.slotSize)
    implicitHeight: root.vertical ? (root.expanded ? root.expandedSize : root.slotSize) : root.slotSize

    Behavior on implicitWidth {
        NumberAnimation {
            duration: 200
            easing.type: Easing.BezierSpline
            easing.bezierCurve: Appearance.animationCurves.standard
        }
    }

    Behavior on implicitHeight {
        NumberAnimation {
            duration: 200
            easing.type: Easing.BezierSpline
            easing.bezierCurve: Appearance.animationCurves.standard
        }
    }

    Rectangle {
        id: capsule

        anchors.fill: parent
        radius: Appearance.rounding.full
        clip: true
        color: root.hovered ? (root.isMaterial ? M3Palette.primary : Appearance.colors.colLayer1Hover) : "transparent"

        Behavior on color {
            ColorAnimation {
                duration: Appearance.animation.elementMoveFast.duration
            }
        }

        Item {
            id: anchorBox

            anchors.left: parent.left
            anchors.top: parent.top
            width: root.slotSize
            height: root.slotSize

            MaterialSymbol {
                id: symbol

                anchors.centerIn: parent
                visible: root.iconText.length > 0
                iconSize: Appearance.sizes.barUtilIconSize
                fill: root.isActive ? 1 : 0
                color: root.hovered && root.isMaterial ? M3Palette.primaryForeground : root.resolvedContentColor

                Behavior on color {
                    ColorAnimation {
                        duration: Appearance.animation.elementMoveFast.duration
                    }
                }
            }

            // Non-icon content stays centred in the fixed slot. childrenRect keeps the
            // intrinsic width the child reports (xkb layout text, unread badge), so the
            // slot width never depends on it.
            Item {
                id: contentHost

                anchors.centerIn: parent
                width: childrenRect.width
                height: childrenRect.height
                visible: root.iconText.length === 0
            }
        }

        StyledText {
            id: label

            visible: root.canExpand
            opacity: root.expanded ? 1.0 : 0.0

            anchors {
                left: root.vertical ? parent.left : anchorBox.right
                right: parent.right
                top: root.vertical ? anchorBox.bottom : parent.top
                bottom: parent.bottom
                rightMargin: root.vertical ? 0 : 5
            }

            horizontalAlignment: root.vertical ? Text.AlignHCenter : Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            clip: true

            font.pixelSize: NexusStyle.font.labelSmall
            font.features: { "tnum": 1 }
            color: root.hovered && root.isMaterial ? M3Palette.primaryForeground : root.resolvedContentColor

            text: root.dataText

            Behavior on opacity {
                NumberAnimation {
                    duration: 150
                }
            }
            Behavior on color {
                ColorAnimation {
                    duration: Appearance.animation.elementMoveFast.duration
                }
            }
        }
    }

    MouseArea {
        id: mouseArea

        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: root.clickable ? (Qt.LeftButton | Qt.MiddleButton | Qt.RightButton) : Qt.NoButton
        onClicked: event => root.clicked(event)
        onWheel: event => {
            root.wheeled(event.angleDelta.y);
            event.accepted = true;
        }
    }

    M3ToolTip {
        text: root.toolTipText
        extraVisibleCondition: root.toolTipText.length > 0 && mouseArea.containsMouse
        alternativeVisibleCondition: extraVisibleCondition
        anchorEdges: Config.options?.bar?.bottom ?? false ? Edges.Top : Edges.Bottom
    }
}

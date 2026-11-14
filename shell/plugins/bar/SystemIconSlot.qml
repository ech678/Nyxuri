// Fork & Trim: end4-pC modules/ii/bar/UtilButton.qml (via shell/plugins/bar/UtilButton.qml)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for the Nyxuri status cluster:
//   - the slot is a fixed 26x26. end4's hover width expansion (26 -> 54) is
//     gone: hovering a status icon must never reflow the whole bar lane;
//   - the hover capsule keeps the util-button language: material uses
//     primary/primaryForeground, non-material colLayer1Hover + contentColor;
//   - contentColor/contentColorOverridden carry BarGroup's per-widget style
//     override into the glyphs;
//   - `wheeled(delta)` exposes the scroll gesture (volume slot);
//   - the default child slot puts non-icon content (xkb panel, unread badge)
//     inside the same 26px footprint instead of a width-swapping Loader.

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
    property bool vertical: false
    property bool clickable: true
    property string toolTipText: ""
    // Stable identity for the runtime probe; user-visible nothing.
    property string slotKey: ""
    property color contentColor: Appearance.colors.colOnLayer1
    property bool contentColorOverridden: false
    property bool isMaterial: PersonalizationConfig.barIsMaterial
    default property alias content: contentHost.data

    readonly property bool hovered: mouseArea.containsMouse || root.forceHovered
    readonly property color resolvedContentColor: root.contentColorOverridden ? root.contentColor : (root.isMaterial ? M3Palette.pillInk("systemIcons") : Appearance.colors.colOnLayer1)
    readonly property int slotSize: 26

    implicitWidth: root.slotSize
    implicitHeight: root.slotSize

    Rectangle {
        anchors.fill: parent
        radius: Appearance.rounding.full
        color: root.hovered ? (root.isMaterial ? M3Palette.primary : Appearance.colors.colLayer1Hover) : "transparent"

        Behavior on color {
            ColorAnimation {
                duration: Appearance.animation.elementMoveFast.duration
            }
        }
    }

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

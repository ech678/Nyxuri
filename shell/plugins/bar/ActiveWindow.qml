// Fork & Trim: end4-pC modules/ii/bar/ActiveWindow.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri (B8.5):
//   - Hyprland ToplevelManager / WM.* / SystemAppearance / AppSearch replaced
//     by the single compositor projection: CompositorDriver.focusedWindow,
//     activeWorkspaceForOutput and windowsForWorkspace.
//   - Upstream debug console.log block dropped.
//   - Upstream "biggest window" ranking has no Niri equivalent (window geometry
//     is not in the IPC payload), so the fallback is the first window of the
//     focused output's active workspace in scroll order.
//   - contentColor / contentColorOverridden kept so BarGroup's per-widget style
//     override can tint the text.

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Widgets
import qs.commons
import qs.services
import qs.ui

Item {
    id: root

    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool vertical: false

    readonly property string outputName: root.QsWindow.window?.screen?.name ?? ""
    readonly property var workspace: CompositorDriver.activeWorkspaceForOutput(root.outputName)
    readonly property var focusedWindow: CompositorDriver.focusedWindow
    readonly property bool focusingThisMonitor: root.focusedWindow !== null && Number(root.focusedWindow.workspaceId) === Number(root.workspace?.id)
    readonly property var primaryWindow: root.focusingThisMonitor ? root.focusedWindow : (CompositorDriver.windowsForWorkspace(root.workspace?.id ?? -1)[0] ?? null)

    readonly property string activeAppClass: root.primaryWindow?.appId ?? ""
    readonly property string activeTitle: root.primaryWindow?.title ?? ""
    readonly property string activeIcon: root.primaryWindow?.iconPath ?? ""
    readonly property string workspaceFallbackTitle: `${Translation.tr("Workspace")} ${root.workspace?.idx ?? 1}`

    readonly property color subtextColor: root.contentColorOverridden ? Qt.alpha(root.contentColor, 0.7) : Appearance.colors.colSubtext

    implicitWidth: root.vertical ? Appearance.sizes.verticalBarWidth : Math.min(colLayout.implicitWidth + 12, 280)
    implicitHeight: root.vertical ? 22 : Appearance.sizes.barHeight

    // Vertical
    Item {
        id: iconItem

        visible: root.vertical
        anchors.centerIn: parent
        implicitWidth: 22
        implicitHeight: 22

        IconImage {
            anchors.centerIn: parent
            source: root.activeIcon
            implicitSize: 18
            visible: root.activeIcon !== ""
        }
    }

    // Horizontal (end4: app class on top, window title below)
    ColumnLayout {
        id: colLayout

        visible: !root.vertical
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 6
        spacing: -4

        StyledText {
            Layout.fillWidth: true
            font.pixelSize: Appearance.font.pixelSize.smaller
            color: root.subtextColor
            elide: Text.ElideRight
            text: root.activeAppClass !== "" ? root.activeAppClass : Translation.tr("Desktop")
        }

        StyledText {
            Layout.fillWidth: true
            font.pixelSize: Appearance.font.pixelSize.small
            color: root.contentColor
            elide: Text.ElideRight
            text: root.activeTitle !== "" ? root.activeTitle : root.workspaceFallbackTitle
        }
    }
}

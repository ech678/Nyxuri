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
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

Item {
    id: root

    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool vertical: false
    property var widgetEntry: null
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    readonly property real maxWidth: BarWidgetDefaults.option("activeWindow", root.widgetEntry, "maxWidth")
    readonly property bool showIcon: BarWidgetDefaults.option("activeWindow", root.widgetEntry, "showIcon")
    readonly property bool compactMode: BarWidgetDefaults.option("activeWindow", root.widgetEntry, "compactMode")
    readonly property bool hideWhenEmpty: BarWidgetDefaults.option("activeWindow", root.widgetEntry, "hideWhenEmpty")
    readonly property bool barWidgetVisible: !root.hideWhenEmpty || root.activeTitle !== ""

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

    visible: root.barWidgetVisible
    implicitWidth: !root.barWidgetVisible ? 0 : root.vertical ? PersonalizationConfig.resolvedVerticalBarWidth(root.barAxes) : Math.min(rowWrap.implicitWidth + 12, root.maxWidth)
    implicitHeight: !root.barWidgetVisible ? 0 : root.vertical ? 22 : PersonalizationConfig.resolvedBarHeight(root.barAxes)

    // D4b click axes: transparent to the lane unless an action consumed
    // the click ("none" default swallows nothing, the handler is inert).
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        enabled: BarWidgetDefaults.option("activeWindow", root.widgetEntry, BarWidgetActions.axisForButton(Qt.LeftButton)) !== "none" || BarWidgetDefaults.option("activeWindow", root.widgetEntry, BarWidgetActions.axisForButton(Qt.MiddleButton)) !== "none" || BarWidgetDefaults.option("activeWindow", root.widgetEntry, BarWidgetActions.axisForButton(Qt.RightButton)) !== "none"
        onClicked: mouse => {
            mouse.accepted = BarWidgetActions.dispatchMouse("activeWindow", root.widgetEntry, mouse.button);
        }
    }

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

    // Horizontal (end4: app class on top, window title below, with optional icon & compact single-line mode)
    RowLayout {
        id: rowWrap

        visible: !root.vertical
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 6
        anchors.rightMargin: 4
        spacing: 6

        IconImage {
            Layout.alignment: Qt.AlignVCenter
            visible: root.showIcon && root.activeIcon !== ""
            source: root.activeIcon
            implicitSize: Math.round(16 * BarScale.iconFor(root.widgetBar))
        }

        ColumnLayout {
            id: colLayout

            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: -4

            StyledText {
                visible: !root.compactMode
                Layout.fillWidth: true
                font.pixelSize: NexusStyle.font.bodySmall * BarScale.fontFor(root.widgetBar)
                color: root.subtextColor
                elide: Text.ElideRight
                text: root.activeAppClass !== "" ? root.activeAppClass : Translation.tr("Desktop")
            }

            StyledText {
                Layout.fillWidth: true
                font.pixelSize: NexusStyle.font.bodyMedium * BarScale.fontFor(root.widgetBar)
                color: root.contentColor
                elide: Text.ElideRight
                text: root.activeTitle !== "" ? root.activeTitle : root.workspaceFallbackTitle
            }
        }
    }
}

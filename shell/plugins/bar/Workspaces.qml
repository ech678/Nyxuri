// Nyxuri Shell - Workspaces Widget (M3 unified)
// GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.commons
import qs.commons.i18n
import qs.ui
import qs.services

Item {
    id: root

    property string screenName: ""
    property bool vertical: Config.options?.bar?.vertical ?? false
    readonly property bool isMaterial: (Config.options?.bar?.m3?.cornerStyle ?? 0) === 3
    readonly property bool hasMultipleOutputs: (CompositorDriver.outputs?.count || 0) > 1

    implicitWidth: layout.implicitWidth
    implicitHeight: layout.implicitHeight

    function acceptsOutput(outputName) {
        if (root.screenName === "") return true;
        if (!root.hasMultipleOutputs && outputName === "") return true;
        return outputName === root.screenName;
    }

    RowLayout {
        id: layout
        anchors.centerIn: parent
        spacing: 6

        Repeater {
            id: workspaceRepeater
            model: CompositorDriver.workspaces

            delegate: Item {
                id: delegateRoot

                property bool belongsToScreen: root.acceptsOutput(model.output)
                property bool active: model.isActive
                property bool hasWindows: (model.windowCount ?? 0) > 0
                property bool isHovered: mouseArea.containsMouse

                visible: belongsToScreen
                implicitWidth: !belongsToScreen ? 0 : ((active || isHovered) ? 28 : 12)
                implicitHeight: !belongsToScreen ? 0 : 12

                Behavior on implicitWidth {
                    NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: parent.implicitWidth
                    height: parent.implicitHeight
                    radius: height / 2

                    color: delegateRoot.active
                        ? (root.isMaterial ? M3Palette.pillInk("workspaces") : Appearance.colors.colPrimary)
                        : delegateRoot.hasWindows
                            ? Appearance.colors.colOnSurface
                            : delegateRoot.isHovered
                                ? Appearance.colors.colLayer2Hover
                                : Appearance.colors.colLayer4

                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: CompositorDriver.focusWorkspaceById(model.id)
                }

                M3ToolTip {
                    visible: mouseArea.containsMouse
                    text: I18n.tr("Workspace ") + model.id + (delegateRoot.hasWindows ? I18n.tr("\nWindows: ") + model.windowCount : "")
                }
            }
        }
    }
}

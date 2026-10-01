pragma ComponentBehavior: Bound

import QtQuick
import Clavis.Niri
import qs.Common
import qs.Widgets.common

Item {
    id: root

    required property var screen
    property bool vertical: false

    implicitWidth: vertical ? 32 : workspaceRow.implicitWidth
    implicitHeight: vertical ? workspaceColumn.implicitHeight : 32

    Flow {
        id: workspaceRow
        visible: !root.vertical
        anchors.centerIn: parent
        spacing: 2
        Repeater {
            model: root.vertical ? null : Niri.workspaces
            delegate: WorkspaceNumber {}
        }
    }

    Column {
        id: workspaceColumn
        visible: root.vertical
        anchors.centerIn: parent
        spacing: 2
        Repeater {
            model: root.vertical ? Niri.workspaces : null
            delegate: WorkspaceNumber {}
        }
    }

    component WorkspaceNumber: Item {
        id: workspace
        required property var model
        readonly property bool belongsToScreen: !root.screen || model.output === root.screen.name || (
                                                    Niri.outputs.count <= 1 && model.output === "")
        visible: belongsToScreen
        width: visible ? 28 : 0
        height: visible ? 32 : 0
        Accessible.role: Accessible.Button
        Accessible.name: qsTr("Workspace %1").arg(model.name || model.index)
        Accessible.onPressAction: Niri.focusWorkspaceById(model.id)

        Text {
            anchors.centerIn: parent
            text: workspace.model.index
            color: workspace.model.isActive || pointer.containsMouse ? Appearance.colors.colPrimary :
                                                                       Appearance.colors.colOnSurfaceVariant
            font.family: Fonts.numeric
            font.pixelSize: 13
            font.weight: workspace.model.isActive ? Font.Bold : Font.Normal
        }

        MouseArea {
            id: pointer
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: Niri.focusWorkspaceById(workspace.model.id)
        }

        PopupToolTip {
            extraVisibleCondition: pointer.containsMouse
            text: qsTr("Workspace %1").arg(workspace.model.name || workspace.model.index)
            textFormat: Text.PlainText
        }
    }
}

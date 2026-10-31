import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Full-row toggle (Caelestia Nexus ToggleRow). Double-line text on the left,
// MD3 pill switch on the right; the press state layer covers the whole row —
// clicking the text toggles too, matching the Android expectation.
ConnectedRect {
    id: root

    property string text: ""
    property string subtext: ""
    property string icon: ""
    property alias checked: toggleItem.checked

    signal toggled

    function toggle(): void {
        if (!enabled)
            return;
        toggleItem.checked = !toggleItem.checked;
        root.toggled();
    }

    Layout.fillWidth: true
    implicitHeight: Math.max(column.implicitHeight, toggleItem.implicitHeight) + NexusStyle.padding.medium * 2

    StateLayer {
        id: stateLayer

        anchors.fill: parent
        layerRadius: (root.first || root.last) ? NexusStyle.rounding.extraLarge :
                                                 NexusStyle.rounding.extraSmall

        color: Appearance.m3colors.m3onSurface
        hovered: rowPress.containsMouse || toggleItem.hovered
        pressed: rowPress.pressed || toggleItem.pressed
    }

    // Below the content row in z: the switch keeps its own hit area, every
    // other click on the row toggles.
    MouseArea {
        id: rowPress

        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggle()
    }

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: NexusStyle.padding.largeIncreased
        anchors.rightMargin: NexusStyle.padding.largeIncreased
        spacing: NexusStyle.padding.small

        MaterialSymbol {
            visible: root.icon.length > 0
            Layout.preferredWidth: root.icon.length > 0 ? implicitWidth : 0
            text: root.icon
            iconSize: NexusStyle.icon.medium
            fill: 1
            color: Appearance.m3colors.m3onSurfaceVariant
        }

        ColumnLayout {
            id: column

            Layout.fillWidth: true
            spacing: 0

            StyledText {
                Layout.fillWidth: true
                text: root.text
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.bodyMedium
                elide: Text.ElideRight
            }

            StyledText {
                Layout.fillWidth: true
                visible: root.subtext.length > 0
                text: root.subtext
                color: Appearance.m3colors.m3outline
                font.pixelSize: NexusStyle.font.labelSmall
                elide: Text.ElideRight
            }
        }

        StyledSwitch {
            id: toggleItem

            onToggled: root.toggled()
        }
    }
}

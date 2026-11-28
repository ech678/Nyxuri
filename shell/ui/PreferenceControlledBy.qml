import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Follow / override / controlled-by status banner row (dux SettingsControlledBy
// lineage, Nexus ConnectedRect styling). Supports either a navigation action
// button (when another setting owns the value) or a follow/override toggle.
ConnectedRect {
    id: root

    property string icon: "tune"
    property string title: ""
    property string reason: ""
    property string actionLabel: ""
    property bool showSwitch: false
    property bool following: true

    signal actionClicked
    signal followToggled(bool follow)

    Layout.fillWidth: true
    implicitHeight: contentRow.implicitHeight + NexusStyle.padding.medium * 2
    color: Appearance.m3colors.m3secondaryContainer

    RowLayout {
        id: contentRow

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
            color: Appearance.m3colors.m3onSecondaryContainer
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            StyledText {
                Layout.fillWidth: true
                text: root.title
                color: Appearance.m3colors.m3onSecondaryContainer
                font.pixelSize: NexusStyle.font.bodyMedium
                font.weight: NexusStyle.font.titleWeight
                elide: Text.ElideRight
            }

            StyledText {
                Layout.fillWidth: true
                visible: root.reason.length > 0
                text: root.reason
                color: Appearance.m3colors.m3onSecondaryContainer
                opacity: 0.8
                font.pixelSize: NexusStyle.font.labelSmall
                wrapMode: Text.Wrap
            }
        }

        RippleButton {
            visible: root.actionLabel.length > 0
            buttonText: root.actionLabel
            buttonRadius: NexusStyle.rounding.full
            horizontalPadding: NexusStyle.padding.medium
            verticalPadding: NexusStyle.padding.extraSmall
            colBackground: Appearance.m3colors.m3primary
            colBackgroundHover: Appearance.m3colors.m3primary
            onClicked: root.actionClicked()

            contentItem: StyledText {
                text: root.actionLabel
                color: Appearance.m3colors.m3onPrimary
                font.pixelSize: NexusStyle.font.labelLarge
                font.weight: NexusStyle.font.labelLargeWeight
            }
        }

        StyledSwitch {
            visible: root.showSwitch
            checked: root.following
            onToggled: root.followToggled(checked)
        }
    }
}

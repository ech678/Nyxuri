import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.commons.i18n
import qs.ui

// Section label above a connected card group (Caelestia Nexus SectionHeader).
// `first` removes the top margin for the leading section of a page; the
// top margin compensates the owning ColumnLayout's own spacing so the gap
// between groups stays one spacing unit. Supports optional group/page-level
// reset and trailing action atoms.
RowLayout {
    id: root

    property bool first: false
    property alias text: label.text
    property bool showReset: false
    property string resetText: ""
    default property alias actions: actionsRow.data

    signal resetRequested

    Layout.fillWidth: true
    Layout.topMargin: first ? 0 : NexusStyle.padding.medium - ((parent as ColumnLayout)?.spacing ?? 0)
    Layout.bottomMargin: NexusStyle.padding.extraSmall
    Layout.leftMargin: NexusStyle.padding.extraSmall
    Layout.rightMargin: NexusStyle.padding.extraSmall
    spacing: NexusStyle.padding.extraSmall

    StyledText {
        id: label

        Layout.fillWidth: true
        color: Appearance.m3colors.m3onSurfaceVariant
        font.pixelSize: NexusStyle.font.labelMedium
        font.weight: NexusStyle.font.labelMediumWeight
        elide: Text.ElideRight
    }

    RowLayout {
        id: actionsRow

        spacing: NexusStyle.padding.extraSmall
    }

    IconButton {
        visible: root.showReset
        Layout.alignment: Qt.AlignVCenter
        width: NexusStyle.icon.small + NexusStyle.padding.small
        height: NexusStyle.icon.small + NexusStyle.padding.small
        controlSize: NexusStyle.icon.small + NexusStyle.padding.small
        iconSize: NexusStyle.icon.small
        iconName: "restart_alt"
        accessibleName: root.resetText.length > 0 ? root.resetText : I18n.tr("Reset")
        tooltipText: accessibleName
        onClicked: root.resetRequested()
    }
}

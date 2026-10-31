import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

// Section label above a connected card group (Caelestia Nexus SectionHeader).
// `first` removes the top margin for the leading section of a page; the
// top margin compensates the owning ColumnLayout's own spacing so the gap
// between groups stays one spacing unit.
StyledText {
    property bool first: false

    Layout.fillWidth: true
    Layout.topMargin: first ? 0 : NexusStyle.padding.medium - ((parent as ColumnLayout).spacing ?? 0)
    Layout.bottomMargin: NexusStyle.padding.extraSmall
    Layout.leftMargin: NexusStyle.padding.extraSmall

    color: Appearance.m3colors.m3onSurfaceVariant
    font.pixelSize: NexusStyle.font.labelMedium
    font.weight: NexusStyle.font.labelMediumWeight
    elide: Text.ElideRight
}

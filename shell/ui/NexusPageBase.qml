import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.commons.i18n

// Detail page scaffold (Caelestia Nexus PageBase): big title, optional
// subpage back arrow, one scrolling column of content capped at
// `maxContentWidth`. Pages declare a single content child (the default
// property) — typically a ColumnLayout anchored to cappedWidth. The back
// arrow emits backRequested; navigation state stays with the host (T3 M2).
ColumnLayout {
    id: root

    required property string title
    property bool isSubPage: false
    property real maxContentWidth: NexusStyle.maxContentWidth
    readonly property int cappedWidth: Math.min(maxContentWidth, width)
    readonly property alias flickable: flick

    // Pages built on this scaffold render their own big title — the hosting
    // window suppresses its interim route-title shim (old pre-M3 pages have
    // no title of their own and keep the shim).
    readonly property bool rendersPageTitle: root.title.length > 0

    default property Item contentChild

    signal backRequested

    spacing: NexusStyle.spacing.extraLargeIncreased

    // Block clicks from reaching the flickable's top margin so the title
    // area settles focus out of text fields instead of scrolling.
    MouseArea {
        z: 1
        visible: root.isSubPage || root.title.length > 0
        implicitWidth: header.implicitWidth
        implicitHeight: header.implicitHeight - Layout.bottomMargin
        Layout.bottomMargin: -flick.topMargin

        onClicked: root.forceActiveFocus()

        RowLayout {
            id: header

            spacing: NexusStyle.padding.medium

            IconButton {
                visible: root.isSubPage
                Layout.preferredWidth: root.isSubPage ? implicitWidth : 0
                variant: "tonal"
                iconName: "arrow_back"
                iconSize: NexusStyle.icon.medium
                accessibleName: I18n.tr("Go back")
                showTooltip: false
                onClicked: root.backRequested()
            }

            StyledText {
                Layout.fillWidth: true
                text: root.title
                color: Appearance.m3colors.m3onSurface
                font.pixelSize: NexusStyle.font.titleLarge
                font.weight: NexusStyle.font.titleWeight
                elide: Text.ElideRight
            }
        }
    }

    StyledFlickable {
        id: flick

        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.topMargin: -topMargin
        topMargin: NexusStyle.padding.medium
        bottomMargin: NexusStyle.padding.large

        contentHeight: root.contentChild ? root.contentChild.implicitHeight : 0
        contentItem.children: root.contentChild ? [root.contentChild] : []

        TapHandler {
            onTapped: root.forceActiveFocus()
        }
    }
}

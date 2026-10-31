pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services
import qs.commons.i18n
import qs.plugins.settings
import qs.ui

// Saved networks page (T3 M4): a connected-card list of the remembered Wi-Fi
// profiles inside the network config modal — same row shape as the nearby
// list on the network page, with a trailing chevron instead of lock glyphs.
Item {
    id: root

    signal detailRequested(var target)

    component SavedNetworkRow: ConnectedRect {
        id: savedRow

        required property var modelData
        required property int index

        readonly property string profileName: String(savedRow.modelData.name || "")
        readonly property string networkName: String(savedRow.modelData.ssid || savedRow.profileName)
        readonly property string secondaryText: {
            const details = [];
            if (savedRow.profileName.length > 0 && savedRow.profileName !== savedRow.networkName)
                details.push(savedRow.profileName);

            if (savedRow.modelData.autoconnect)
                details.push(I18n.tr("Connect automatically"));

            return details.join(" · ");
        }

        width: ListView.view.width
        height: savedRowLayout.implicitHeight + NexusStyle.padding.medium * 2
        first: savedRow.index === 0
        last: savedRow.index === savedList.count - 1

        StateLayer {
            anchors.fill: parent
            layerRadius: (savedRow.first || savedRow.last) ? NexusStyle.rounding.extraLarge :
                                                             NexusStyle.rounding.extraSmall
            color: Appearance.m3colors.m3onSurface
            hovered: rowPress.containsMouse
            pressed: rowPress.pressed
        }

        MouseArea {
            id: rowPress

            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.detailRequested(savedRow.modelData)
        }

        RowLayout {
            id: savedRowLayout

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: NexusStyle.padding.largeIncreased
            anchors.rightMargin: NexusStyle.padding.largeIncreased
            spacing: NexusStyle.padding.small

            MaterialSymbol {
                text: "bookmark"
                iconSize: NexusStyle.icon.medium
                fill: 1
                color: Appearance.m3colors.m3onSurfaceVariant
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                StyledText {
                    Layout.fillWidth: true
                    text: savedRow.networkName
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.bodyMedium
                    elide: Text.ElideRight
                }

                StyledText {
                    Layout.fillWidth: true
                    text: savedRow.secondaryText
                    color: Appearance.m3colors.m3outline
                    font.pixelSize: NexusStyle.font.labelSmall
                    elide: Text.ElideRight
                }
            }

            MaterialSymbol {
                text: "chevron_right"
                iconSize: NexusStyle.icon.small
                fill: 1
                color: Appearance.m3colors.m3onSurfaceVariant
            }
        }
    }

    InlineStatusBanner {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: NexusStyle.padding.small
        visible: NetworkService.savedWifiProfiles.length === 0
        message: I18n.tr("No saved networks")
    }

    StyledListView {
        id: savedList

        anchors.fill: parent
        anchors.margins: NexusStyle.padding.small
        visible: NetworkService.savedWifiProfiles.length > 0
        model: NetworkService.savedWifiProfiles
        spacing: NexusStyle.padding.extraSmall / 2
        boundsBehavior: Flickable.StopAtBounds
        fasterTouchpadScroll: true
        showVerticalScrollBar: true
        animateMovement: true

        delegate: SavedNetworkRow {}
    }
}

// Fork & Trim: end4-pC modules/ii/bar/StyledPopupHeaderRow.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui
import qs.services

Row {
    id: root
    required property var icon
    required property var label
    spacing: 5

    MaterialSymbol {
        anchors.verticalCenter: parent.verticalCenter
        fill: 0
        font.weight: Font.DemiBold
        text: root.icon
        iconSize: Appearance.font.pixelSize.large
        color: Appearance.colors.colOnSurfaceVariant
    }

    StyledText {
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        font {
            weight: Font.DemiBold
            pixelSize: Appearance.font.pixelSize.normal
        }
        color: Appearance.colors.colOnSurfaceVariant
    }
}

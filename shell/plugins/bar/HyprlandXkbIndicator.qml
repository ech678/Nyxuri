// Fork & Trim: iNiR modules/ii/barM3/HyprlandXkbIndicator.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Nyxuri trim: the file keeps its upstream visual shape (layout code + Caps +
// Num panel) but reads KeyboardIndicators, whose layout source is the Niri
// projection. Icon size is the bar baseline (17px) instead of `large` so the
// panel matches the util buttons.

import QtQuick
import QtQuick.Layouts
import qs.services
import qs.commons
import qs.ui

Loader {
    id: root

    property bool vertical: false
    property color color: Appearance.colors.colOnSurfaceVariant

    active: KeyboardIndicators.hasPanelIndicators
    visible: active
    Layout.preferredWidth: active && item ? item.implicitWidth : 0
    Layout.preferredHeight: active && item ? item.implicitHeight : 0

    sourceComponent: Item {
        implicitWidth: root.vertical ? indicatorColumn.implicitWidth : indicatorRow.implicitWidth
        implicitHeight: root.vertical ? indicatorColumn.implicitHeight : indicatorRow.implicitHeight

        Row {
            id: indicatorRow

            visible: !root.vertical
            anchors.centerIn: parent
            spacing: Appearance.sizes.spacingSmall

            MaterialSymbol {
                visible: KeyboardIndicators.capsLockVisible
                text: KeyboardIndicators.capsMaterialIcon
                iconSize: Appearance.sizes.barUtilIconSize
                fill: 1
                color: root.color
            }

            MaterialSymbol {
                visible: KeyboardIndicators.numLockVisible
                text: KeyboardIndicators.numMaterialIcon
                iconSize: Appearance.sizes.barUtilIconSize
                fill: 1
                color: root.color
            }

            StyledText {
                visible: KeyboardIndicators.layoutVisible
                horizontalAlignment: Text.AlignHCenter
                text: KeyboardIndicators.currentLayoutCodeInline
                font.pixelSize: Appearance.font.pixelSize.small
                color: root.color
            }
        }

        Column {
            id: indicatorColumn

            visible: root.vertical
            anchors.centerIn: parent
            spacing: Appearance.sizes.spacingSmall / 2

            MaterialSymbol {
                visible: KeyboardIndicators.capsLockVisible
                anchors.horizontalCenter: parent.horizontalCenter
                text: KeyboardIndicators.capsMaterialIcon
                iconSize: Appearance.sizes.barUtilIconSize
                fill: 1
                color: root.color
            }

            MaterialSymbol {
                visible: KeyboardIndicators.numLockVisible
                anchors.horizontalCenter: parent.horizontalCenter
                text: KeyboardIndicators.numMaterialIcon
                iconSize: Appearance.sizes.barUtilIconSize
                fill: 1
                color: root.color
            }

            StyledText {
                visible: KeyboardIndicators.layoutVisible
                horizontalAlignment: Text.AlignHCenter
                text: KeyboardIndicators.currentLayoutCodeMultiline
                font.pixelSize: text.includes("\n") ? Appearance.font.pixelSize.smallie : Appearance.font.pixelSize.small
                color: root.color
            }
        }
    }
}

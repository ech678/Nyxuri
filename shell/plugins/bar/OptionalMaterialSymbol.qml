// Fork & Trim: end4-pC modules/common/widgets/OptionalMaterialSymbol.qml
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.ui

Loader {
    id: root
    required property string icon
    property real iconSize: Appearance.font.pixelSize.larger
    Layout.alignment: Qt.AlignVCenter

    active: root.icon && root.icon.length > 0
    visible: active

    sourceComponent: Item {
        implicitWidth: materialSymbol.implicitWidth

        MaterialSymbol {
            id: materialSymbol
            anchors.centerIn: parent

            iconSize: root.iconSize
            color: root.toggled ? Appearance.colors.colOnPrimary : Appearance.colors.colOnSecondaryContainer
            text: root.icon
        }
    }
}

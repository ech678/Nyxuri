// Fork & Trim: end4-pC modules/ii/bar/PowerButton.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri: token names point at Appearance (the M3Palette bridge
// stays only in the widgets that need pill ink). The button opens the
// session unit through GlobalStates, same as before the re-fork.

import QtQuick
import qs.services
import qs.commons
import qs.ui
import M3Shapes

RippleButton {
    id: root
    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool isMaterial: Config.options.bar.cornerStyle === 3 || Config.options.bar.cornerStyle === 4
    property bool vertical: Config.options.bar.vertical
    property real buttonPadding: 5

    implicitWidth: isMaterial ? 32 : 22
    implicitHeight: implicitWidth

    buttonRadius: Appearance.rounding.full
    colBackground: isMaterial ? Appearance.colors.colPrimary : "transparent"
    colBackgroundHover: isMaterial ? Appearance.colors.colPrimaryHover : Appearance.colors.colLayer1Hover
    colRipple: isMaterial ? Appearance.colors.colPrimaryActive : Appearance.colors.colLayer1Active

    onPressed: {
        GlobalStates.sessionOpen = !GlobalStates.sessionOpen;
    }

    MaterialSymbol {
        anchors.centerIn: parent
        visible: !root.isMaterial
        text: "power_settings_new"
        iconSize: 18
        color: root.contentColor
    }

    MaterialShapeWrappedMaterialSymbol {
        anchors.centerIn: parent
        visible: root.isMaterial
        text: "power_settings_new"
        iconSize: Appearance.font.pixelSize.normal
        color: Appearance.colors.colOnPrimary
        colSymbol: Appearance.colors.colPrimary
        wrappedShape: MaterialShape.Shape.Cookie12Sided
        padding: 2
    }
}

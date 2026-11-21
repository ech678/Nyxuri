// Fork & Trim: end4-pC modules/ii/bar/PowerButton.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri: token names point at Appearance (the M3Palette bridge
// stays only in the widgets that need pill ink). The button toggles the
// session unit through ActionGateway (matching Mod+X).

import QtQuick
import Quickshell
import qs.services
import qs.commons
import qs.ui
import M3Shapes
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

RippleButton {
    id: root
    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool isMaterial: PersonalizationConfig.barIsMaterial
    property bool vertical: Config.options.bar.vertical
    property real buttonPadding: 5
    // D4b click axes: "default" stays the session toggle (Mod+X parity).
    property var widgetEntry: null

    implicitWidth: isMaterial ? Appearance.sizes.barPowerButtonSize : 22
    implicitHeight: implicitWidth

    buttonRadius: Appearance.rounding.full
    colBackground: isMaterial ? Appearance.colors.colPrimary : "transparent"
    colBackgroundHover: isMaterial ? Appearance.colors.colPrimaryHover : Appearance.colors.colLayer1Hover
    colRipple: isMaterial ? Appearance.colors.colPrimaryActive : Appearance.colors.colLayer1Active

    onClicked: mouse => {
        if (!BarWidgetActions.dispatchMouse("powerButton", root.widgetEntry, mouse.button))
            ActionGateway.requestSessionToggle(root.QsWindow.window?.screen);
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
        iconSize: NexusStyle.font.bodyLarge * BarScale.font
        color: Appearance.colors.colOnPrimary
        colSymbol: Appearance.colors.colPrimary
        wrappedShape: MaterialShape.Shape.Cookie12Sided
        padding: 2
    }
}

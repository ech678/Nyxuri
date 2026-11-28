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
import "BarStyle.js" as BarStyle

RippleButton {
    id: root
    property var widgetEntry: null
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool isMaterial: BarStyle.isTinted(root.barAxes)
    property bool vertical: root.barAxes.position === "left" || root.barAxes.position === "right"
    property real buttonPadding: 5

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
        iconSize: 18 * BarScale.iconFor(root.widgetBar)
        color: root.contentColor
    }

    MaterialShapeWrappedMaterialSymbol {
        anchors.centerIn: parent
        visible: root.isMaterial
        text: "power_settings_new"
        iconSize: NexusStyle.font.bodyLarge * BarScale.fontFor(root.widgetBar)
        color: Appearance.colors.colOnPrimary
        colSymbol: Appearance.colors.colPrimary
        wrappedShape: MaterialShape.Shape.Cookie12Sided
        padding: 2
    }
}

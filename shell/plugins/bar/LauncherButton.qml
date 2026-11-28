// Fork & Trim: end4-pC modules/ii/bar/LauncherButton.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri: the upstream press toggled GlobalStates.overviewOpen
// (a Hyprland-era fact this tree never writes). The button now asks the
// ActionGateway to toggle the launcher unit, so a disabled launcher fails
// visibly instead of toggling a stale global.

import QtQuick
import qs.services
import qs.commons
import qs.ui
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

RippleButton {
    id: root
    property var widgetEntry: null
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    property color contentColor: Appearance.colors.colOnLayer0
    property bool contentColorOverridden: false
    property bool vertical: root.barAxes.position === "left" || root.barAxes.position === "right"
    property bool isMaterial: root.barAxes.cornerStyle === 3 || root.barAxes.cornerStyle === 4

    implicitWidth: 22
    implicitHeight: 22

    buttonRadius: Appearance.rounding.full
    colBackground: isMaterial ? Appearance.colors.colPrimaryContainer : "transparent"
    colBackgroundHover: isMaterial ? Appearance.colors.colPrimaryContainerHover : Appearance.colors.colLayer1Hover
    colRipple: Appearance.colors.colLayer1Active
    colBackgroundToggled: "transparent"
    colBackgroundToggledHover: Appearance.colors.colSecondaryContainerHover
    colRippleToggled: Appearance.colors.colSecondaryContainerActive

    onPressed: mouse => {
        if (!BarWidgetActions.dispatchMouse("launcherButton", root.widgetEntry, mouse.button))
            ActionGateway.executeIntent({
                "target": "launcher"
            });
    }

    MaterialSymbol {
        anchors.centerIn: parent
        iconSize: 18 * BarScale.iconFor(root.widgetBar)
        text: "search"
        color: root.contentColor
    }
}

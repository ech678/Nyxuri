import QtQuick
import Quickshell
import qs.services
import qs.commons
import qs.ui
import "BarStyle.js" as BarStyle

RippleButton {
    id: root

    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    property bool vertical: root.barAxes.position === "left" || root.barAxes.position === "right"
    property bool isMaterial: BarStyle.isTinted(root.barAxes)
    readonly property string screenName: root.QsWindow.window?.screen?.name ?? ""

    implicitWidth: 32
    implicitHeight: 32
    buttonRadius: Appearance.rounding.full

    colBackground: isMaterial ? M3Palette.primaryContainer : "transparent"
    colBackgroundHover: isMaterial ? M3Palette.primaryContainerHover : Appearance.colors.colLayer1Hover
    colRipple: isMaterial ? M3Palette.primaryContainerActive : Appearance.colors.colLayer1Active
    colBackgroundToggled: isMaterial ? M3Palette.secondaryContainer : Appearance.colors.colSecondaryContainer
    colBackgroundToggledHover: isMaterial ? M3Palette.secondaryContainerHover : Appearance.colors.colSecondaryContainerHover
    colRippleToggled: isMaterial ? M3Palette.secondaryContainerActive : Appearance.colors.colSecondaryContainerActive
    toggled: ShellLayoutController.sidebarOpenAtSlot("right", screenName)

    onPressed: ShellLayoutController.toggleSidebarAtSlot("right", screenName)

    MaterialSymbol {
        anchors.centerIn: parent
        text: root.toggled ? "right_panel_close" : "right_panel_open"
        iconSize: (root.vertical ? 22 : 20) * BarScale.iconFor(root.widgetBar)
        color: !root.isMaterial
            ? Appearance.colors.colPrimary
            : root.toggled
                ? M3Palette.pillInk("sidebarToggle")
                : M3Palette.pillInk("rightSidebarButton")
    }
}

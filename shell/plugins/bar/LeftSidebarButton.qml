import QtQuick
import Quickshell
import qs.services
import qs.commons
import qs.ui

RippleButton {
    id: root
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    property bool showPing: false
    property bool vertical: root.barAxes.position === "left" || root.barAxes.position === "right"
    property bool isMaterial: root.barAxes.cornerStyle === 3
    property real buttonPadding: 5

    implicitWidth: 32
    implicitHeight: 32

    buttonRadius: Appearance.rounding.full
    colBackground: isMaterial ? M3Palette.primaryContainer : "transparent"
    colBackgroundHover: isMaterial ? M3Palette.primaryContainerHover : Appearance.colors.colLayer1Hover
    colRipple: isMaterial ? M3Palette.primaryContainerActive : Appearance.colors.colLayer1Active
    colBackgroundToggled: isMaterial ? M3Palette.secondaryContainer : Appearance.colors.colSecondaryContainer
    colBackgroundToggledHover: isMaterial ? M3Palette.secondaryContainerHover : Appearance.colors.colSecondaryContainerHover
    colRippleToggled: isMaterial ? M3Palette.secondaryContainerActive : Appearance.colors.colSecondaryContainerActive
    toggled: ShellLayoutController.sidebarOpenAtSlot("left",
        root.QsWindow.window?.screen?.name ?? "")

    onPressed: {
        ShellLayoutController.toggleSidebarAtSlot("left",
            root.QsWindow.window?.screen?.name ?? "");
    }

    Connections {
        target: Ai
        function onResponseFinished() {
            if (GlobalStates.sidebarLeftOpen) return;
            root.showPing = true;
        }
    }
    Connections {
        target: Booru
        function onResponseFinished() {
            if (GlobalStates.sidebarLeftOpen) return;
            root.showPing = true;
        }
    }
    Connections {
        target: GlobalStates
        function onSidebarLeftOpenChanged() {
            root.showPing = false;
        }
    }

    CustomIcon {
        id: distroIcon
        anchors.centerIn: parent
        width: (root.isMaterial ? (root.vertical ? 24 : 22) : 19.5) * BarScale.iconFor(root.widgetBar)
        height: (root.isMaterial ? (root.vertical ? 24 : 22) : 19.5) * BarScale.iconFor(root.widgetBar)
        // Config.options.custom.distroIcon/colorizeIcon do not exist in iNiR;
        // ported to the same source iNiR's own LeftSidebarButton uses.
        source: (Config.options?.bar?.topLeftIcon ?? "distro") === "distro"
            ? SystemInfo.distroIcon
            : `${Config.options?.bar?.topLeftIcon ?? "distro"}-symbolic`
        colorize: true
        color: !root.isMaterial
            ? Appearance.colors.colPrimary
            : root.toggled
                ? M3Palette.pillInk("sidebarToggle")
                : M3Palette.pillInk("leftSidebarButton")

        Rectangle {
            opacity: root.showPing ? 1 : 0
            visible: opacity > 0
            anchors {
                bottom: parent.bottom
                right: parent.right
                bottomMargin: -2
                rightMargin: -2
            }
            implicitWidth: 8
            implicitHeight: 8
            radius: Appearance.rounding.full
            color: Appearance.colors.colTertiary
            Behavior on opacity {
                animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
            }
        }
    }
}

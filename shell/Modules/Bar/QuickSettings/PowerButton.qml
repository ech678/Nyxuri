import QtQuick
import qs.Common
import qs.Widgets.common
import qs.app

BarCircularButton {
    id: root

    property var screen: null

    iconName: "power_settings_new"
    containerColor: "transparent"
    rippleColor: Appearance.colors.colOnSurface
    iconColor: Appearance.colors.colOnSurface
    tooltipText: qsTr("Power menu")
    onClicked: ActionGateway.requestSessionOpen(root.screen)
}

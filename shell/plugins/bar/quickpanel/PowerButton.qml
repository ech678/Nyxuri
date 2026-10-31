import QtQuick
import qs.commons
import qs.ui
import qs.app
import qs.commons.i18n

BarCircularButton {
    id: root

    property var screen: null

    iconName: "power_settings_new"
    containerColor: "transparent"
    rippleColor: Appearance.colors.colOnSurface
    iconColor: Appearance.colors.colOnSurface
    tooltipText: I18n.tr("Power menu")
    onClicked: ActionGateway.requestSessionOpen(root.screen)
}

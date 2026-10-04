import QtQuick
import qs.app
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n

BarCircularButton {
    id: root

    property string viewName: "info"
    property string sidebarIconName: "notifications"
    readonly property bool isActive: WidgetState.dashboardSidebarOpen && WidgetState.dashboardSidebarView
                                     === root.viewName

    function toggleView() {
        if (root.isActive) {
            WidgetState.dashboardSidebarOpen = false;
            return;
        }
        WidgetState.dashboardSidebarView = root.viewName;
        WidgetState.dashboardSidebarOpen = true;
    }

    selected: root.isActive
    iconName: root.sidebarIconName
    containerColor: "transparent"
    rippleColor: Appearance.colors.colOnSurface
    iconColor: Appearance.colors.colOnSurface
    tooltipText: root.viewName === "drawer" ? I18n.tr("Drawer") : I18n.tr("Notification center")
    onClicked: root.toggleView()
}

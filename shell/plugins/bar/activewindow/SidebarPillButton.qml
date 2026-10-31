import QtQuick
import qs.app
import qs.commons
import qs.ui
import qs.commons.i18n

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
    tooltipText: I18n.tr("Notification center")
    onClicked: root.toggleView()
}

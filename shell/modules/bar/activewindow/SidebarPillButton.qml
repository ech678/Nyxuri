import QtQuick
import qs.app
import qs.shared.theme
import qs.shared.controls

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
    tooltipText: root.viewName === "drawer" ? qsTr("Drawer") : qsTr("Notification center")
    onClicked: root.toggleView()
}

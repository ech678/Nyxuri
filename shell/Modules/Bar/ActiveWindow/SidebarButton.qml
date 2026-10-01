import QtQuick
import QtQuick.Layouts
import qs.Common
import qs.Services
import qs.Widgets.common

TopBarPill {
    id: root

    property bool vertical: false

    implicitHeight: vertical ? buttonRow.implicitHeight + 2 * Sizes.barPillHorizontalPadding :
                               Sizes.barPillThickness
    implicitWidth: vertical ? Sizes.barPillThickness : buttonRow.implicitWidth + 2
                              * Sizes.barPillHorizontalPadding

    GridLayout {
        id: buttonRow

        anchors.centerIn: parent
        rowSpacing: Sizes.barItemSpacing
        columnSpacing: Sizes.barItemSpacing
        columns: root.vertical ? 1 : 3

        SidebarPillButton {
            viewName: "info"
            sidebarIconName: "notifications"
        }

        SidebarPillButton {
            viewName: "drawer"
            sidebarIconName: "widgets"
        }

        SidebarWeatherButton {
            vertical: root.vertical
        }
    }
}

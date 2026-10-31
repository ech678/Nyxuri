import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui

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
        columns: root.vertical ? 1 : 2

        SidebarPillButton {
            viewName: "info"
            sidebarIconName: "notifications"
        }

        SidebarWeatherButton {
            vertical: root.vertical
        }
    }
}

import QtQuick
import Quickshell
import Quickshell.Services.SystemTray
import Quickshell.Widgets
import qs.shared.theme
import qs.app.services
import qs.shared.controls

MouseArea {
    id: root

    required property var modelData
    property var screen: null
    property string edge: "top"
    property var barVisualItem: null

    signal menuOpened(var qsWindow)
    signal menuClosed

    implicitWidth: Sizes.barControlCircleSize
    implicitHeight: Sizes.barControlCircleSize
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    acceptedButtons: Qt.LeftButton | Qt.RightButton

    function closeMenu() {
        if (menu.active && menu.item && typeof menu.item.close === "function")
            menu.item.close();
    }

    function closeOtherMenus() {
        if (!root.parent)
            return;

        const siblings = root.parent.children;
        for (let i = 0; i < siblings.length; i += 1) {
            const sibling = siblings[i];
            if (sibling === root)
                continue;
            if (typeof sibling.closeMenu === "function")
                sibling.closeMenu();
        }
    }

    onPressed: event => {
        if (event.button === Qt.LeftButton) {
            root.modelData.activate();
            root.closeMenu();
        } else if (event.button === Qt.RightButton) {
            if (root.modelData.hasMenu || root.modelData.menu) {
                if (menu.active && menu.item && typeof menu.item.close === "function") {
                    menu.item.close();
                } else {
                    root.closeOtherMenus();
                    menu.open();
                }
            }
        }
        event.accepted = true;
    }

    Loader {
        id: menu

        active: false

        function open() {
            menu.active = true;
        }

        sourceComponent: TrayMenu {
            Component.onCompleted: this.open()

            trayItemMenuHandle: root.modelData.menu
            trayItemId: root.modelData.id || ""
            anchorItem: root
            screen: root.screen
            edge: root.edge
            barVisualItem: root.barVisualItem

            onMenuOpened: window => root.menuOpened(window)
            onMenuClosed: {
                root.menuClosed();
                menu.active = false;
            }
        }
    }

    IconImage {
        id: trayIcon

        source: root.modelData.icon || ""
        anchors.centerIn: parent
        width: Sizes.barIconSize
        height: Sizes.barIconSize
        asynchronous: true
        mipmap: true
    }

    PopupToolTip {
        extraVisibleCondition: root.containsMouse
        text: TrayService.getTooltipForItem(root.modelData)
    }
}

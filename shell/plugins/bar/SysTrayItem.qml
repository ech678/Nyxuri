pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Services.SystemTray
import Quickshell.Widgets
import Qt5Compat.GraphicalEffects
import qs.services
import qs.commons
import qs.ui

MouseArea {
    id: root
    required property SystemTrayItem item
    property var widgetBar: null
    readonly property var barAxes: root.widgetBar ? root.widgetBar.axes : PersonalizationConfig.barAxes
    readonly property bool barVertical: root.barAxes.position === "left" || root.barAxes.position === "right"
    readonly property bool barAtEnd: root.barAxes.position === "bottom" || root.barAxes.position === "right"
    property bool targetMenuOpen: false
    // Injected by the SysTray delegates (D4b entry axes).
    property bool tintIcon: true
    property bool showItemId: false

    signal menuOpened(qsWindow: var)
    signal menuClosed

    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    implicitWidth: Math.round(20 * BarScale.iconFor(root.widgetBar))
    implicitHeight: Math.round(20 * BarScale.iconFor(root.widgetBar))
    onPressed: event => {
        switch (event.button) {
        case Qt.LeftButton:
            item.activate();
            break;
        case Qt.RightButton:
            if (item.hasMenu)
                if (menu.active && menu.item && typeof menu.item.close === "function")
                    menu.item.close();
                else
                    menu.open();
            break;
        }
        event.accepted = true;
    }
    onEntered: {
        tooltip.text = TrayService.getTooltipForItem(root.item, root.showItemId);
    }

    Loader {
        id: menu
        function open() {
            menu.active = true;
        }
        active: false
        sourceComponent: SysTrayMenu {
            Component.onCompleted: this.open()
            widgetBar: root.widgetBar
            trayItemMenuHandle: root.item.menu
            trayItemId: root.item.id
            anchor {
                window: root.QsWindow.window
                item: root
                gravity: root.barVertical ? (root.barAtEnd ? Edges.Left : Edges.Right) : (root.barAtEnd ? Edges.Top : Edges.Bottom)
                edges: root.barVertical ? (root.barAtEnd ? Edges.Left : Edges.Right) : (root.barAtEnd ? Edges.Top : Edges.Bottom)
                adjustment: root.barVertical ? PopupAdjustment.SlideY : PopupAdjustment.SlideX
            }
            onMenuOpened: window => root.menuOpened(window)
            onMenuClosed: {
                root.menuClosed();
                menu.active = false;
            }
        }
    }

    IconImage {
        id: trayIcon
        source: TrayService.getSafeIcon(root.item)
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
    }

    Loader {
        active: root.tintIcon
        anchors.fill: trayIcon
        sourceComponent: Item {
            Desaturate {
                id: desaturatedIcon
                visible: false
                anchors.fill: parent
                source: trayIcon
                desaturation: 0.8
            }
            ColorOverlay {
                anchors.fill: desaturatedIcon
                source: desaturatedIcon
                color: ColorUtils.transparentize(M3Palette.pillInk("sysTray"), 0.9)
            }
        }
    }

    M3ToolTip {
        id: tooltip
        extraVisibleCondition: root.containsMouse
        alternativeVisibleCondition: extraVisibleCondition
        anchorEdges: (!root.barAtEnd && !root.barVertical) ? Edges.Bottom : Edges.Top
    }
}

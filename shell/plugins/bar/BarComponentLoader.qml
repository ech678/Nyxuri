import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import "workspaces"
import "activewindow"
import "tray"
import "sysmonitor"
import "media"
import "quickpanel"
import "clock"
import "."

Item {
    id: root

    required property string componentId
    required property var screen
    required property var axis
    required property Item barVisualItem
    property bool vertical: false
    property int currentIndex: 0
    property int totalCount: 0

    implicitWidth: barGroup.implicitWidth
    implicitHeight: barGroup.implicitHeight

    readonly property Item item: widgetLoader.item

    function sourceComponentFor(id) {
        switch (id) {
        case "workspaces":
            return workspacesComponent;
        case "information":
            return informationComponent;
        case "activeWindow":
            return activeWindowComponent;
        case "media":
            return mediaComponent;
        case "tray":
            return trayComponent;
        case "systemMonitor":
            return systemMonitorComponent;
        case "quickSettings":
            return quickSettingsComponent;
        case "clock":
            return clockComponent;
        case "island":
            return islandComponent;
        case "divisor":
            return divisorComponent;
        default:
            return null;
        }
    }

    BarGroup {
        id: barGroup

        anchors.fill: parent
        vertical: root.vertical
        currentIndex: root.currentIndex
        totalCount: root.totalCount
        widgetName: root.componentId
        paintBackground: root.componentId !== "island"
        paintMaterialPill: root.barVisualItem && typeof root.barVisualItem.shouldPaintMaterialPill === "function" ? root.barVisualItem.shouldPaintMaterialPill(root.componentId) : false
        bgColor: root.barVisualItem && typeof root.barVisualItem.getMaterialPillColor === "function" ? root.barVisualItem.getMaterialPillColor(root.componentId) : Appearance.colors.colPrimaryContainer

        Loader {
            id: widgetLoader

            Layout.fillHeight: !root.vertical
            Layout.fillWidth: root.vertical
            sourceComponent: root.sourceComponentFor(root.componentId)
        }
    }

    Component {
        id: workspacesComponent

        Workspaces {
            screenName: root.screen.name
            vertical: root.vertical
        }
    }

    Component {
        id: informationComponent

        SidebarButton {
            vertical: root.vertical
        }
    }

    Component {
        id: activeWindowComponent

        ActiveWindow {
            maximumTitleWidth: root.vertical ? 250 : Math.max(48, Math.min(250, root.barVisualItem.width * 0.18))
            vertical: root.vertical
        }
    }

    Component {
        id: mediaComponent

        MediaBar {
            maximumTitleWidth: Math.max(48, Math.min(180, (root.vertical ? root.barVisualItem.height : root.barVisualItem.width) * 0.12))
            vertical: root.vertical
        }
    }

    Component {
        id: trayComponent

        Tray {
            screen: root.screen
            edge: root.axis.edge
            vertical: root.vertical
            barVisualItem: root.barVisualItem
        }
    }

    Component {
        id: systemMonitorComponent

        SysMonitor {
            flatIndicators: PersonalizationConfig.barShowValues
            showValues: PersonalizationConfig.barShowValues
            ownerId: "bar-sysmonitor:" + root.screen.name
            vertical: root.vertical
        }
    }

    Component {
        id: quickSettingsComponent

        QuickSettings {
            screen: root.screen
            vertical: root.vertical
        }
    }

    Component {
        id: clockComponent

        Clock {
            vertical: root.vertical
        }
    }

    Component {
        id: islandComponent

        Island {
            vertical: root.vertical
        }
    }

    Component {
        id: divisorComponent

        Divisor {
            vertical: root.vertical
        }
    }
}

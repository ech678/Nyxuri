import QtQuick
import qs.Services
import QtQuick.Layouts
import qs.Modules.Bar.Workspaces
import qs.Modules.Bar.ActiveWindow
import qs.Modules.Bar.Tray
import qs.Modules.Bar.SysMonitor
import qs.Modules.Bar.Media
import qs.Modules.Bar.QuickSettings

Loader {
    id: root

    required property string componentId
    required property var screen
    required property var axis
    required property Item barVisualItem
    property bool vertical: false

    sourceComponent: {
        switch (root.componentId) {
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
        default:
            return null;
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
            maximumTitleWidth: root.vertical ? 250 : Math.max(48, Math.min(250, root.barVisualItem.width
                                                                           * 0.18))
            vertical: root.vertical
        }
    }

    Component {
        id: mediaComponent

        MediaBar {
            maximumTitleWidth: Math.max(48, Math.min(180, (root.vertical ? root.barVisualItem.height :
                                                                           root.barVisualItem.width) * 0.12))
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
}

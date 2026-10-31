import QtQuick
import qs.services
import QtQuick.Layouts
import qs.plugins.bar.workspaces
import qs.plugins.bar.activewindow
import qs.plugins.bar.tray
import qs.plugins.bar.sysmonitor
import qs.plugins.bar.media
import qs.plugins.bar.quickpanel
import qs.plugins.bar.clock

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
        case "clock":
            return clockComponent;
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

    Component {
        id: clockComponent

        Clock {
            vertical: root.vertical
        }
    }
}

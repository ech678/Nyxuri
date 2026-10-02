import QtQuick
import qs.app.services
import QtQuick.Layouts
import qs.modules.bar.workspaces
import qs.modules.bar.activewindow
import qs.modules.bar.tray
import qs.modules.bar.sysmonitor
import qs.modules.bar.media
import qs.modules.bar.quicksettings
import qs.modules.bar.clock

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

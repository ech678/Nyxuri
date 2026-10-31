import QtQuick
import Quickshell
import Quickshell.Io
import qs.app

Scope {
    id: root

    property bool active: false
    property string targetScreenName: ""

    signal actionTriggered(string action)

    function open(screen) {
        screen = screen || (Quickshell.screens.length > 0 ? Quickshell.screens[0] : null);
        if (!screen || !screen.name)
            return false;

        root.targetScreenName = screen.name;
        root.active = true;
        return true;
    }

    function close() {
        if (!root.active)
            return false;

        root.active = false;
        root.targetScreenName = "";
        return true;
    }

    function toggle(screen) {
        return root.active ? root.close() : root.open(screen);
    }

    Connections {
        target: ActionGateway

        function onSessionOpenRequested(screen) {
            root.open(screen);
        }

        function onSessionCloseRequested() {
            root.close();
        }

        function onSessionToggleRequested(screen) {
            root.toggle(screen);
        }
    }

    // Unit-owned IPC surface (unit-model.md §6): the session unit's
    // power-menu exists exactly while the unit is loaded.
    IpcHandler {
        target: "power-menu"

        function open(): void {
            ActionGateway.requestSessionOpen();
        }

        function close(): void {
            ActionGateway.requestSessionClose();
        }

        function toggle(): void {
            ActionGateway.requestSessionToggle();
        }
    }

    Variants {
        model: Quickshell.screens

        delegate: Loader {
            id: sessionLoader

            required property var modelData

            active: root.active && (root.targetScreenName === "" || root.targetScreenName === modelData.name)

            sourceComponent: SessionPanel {
                targetScreen: sessionLoader.modelData

                onActionTriggered: action => {
                    root.actionTriggered(action);
                    root.close();
                    ActionGateway.powerAction(action, "session");
                }

                onDismissFinished: {
                    root.close();
                }
            }
        }
    }
}

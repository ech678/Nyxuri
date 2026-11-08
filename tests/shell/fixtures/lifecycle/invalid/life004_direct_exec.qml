import QtQuick
import Quickshell

Item {
    id: root

    function launchDirectly() {
        Quickshell.execDetached(["notify-send", "Bypassed Gateway"]);
    }
}

import QtQuick
import Quickshell

Item {
    id: root

    function launch() {
        Quickshell.execDetached(["should-be-ignored-because-vendor"]);
    }
}

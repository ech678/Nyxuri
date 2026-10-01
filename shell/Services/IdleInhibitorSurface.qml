import QtQuick
import Quickshell
import Quickshell.Wayland

PanelWindow {
    id: root

    visible: true
    screen: Quickshell.screens.length > 0 ? Quickshell.screens[0] : null
    implicitWidth: 1
    implicitHeight: 1
    color: "transparent"

    anchors {
        top: true
        left: true
    }

    exclusiveZone: 0
    mask: Region {}

    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "clavis-idle-inhibitor"
    WlrLayershell.exclusionMode: ExclusionMode.Ignore
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
}

import QtQuick
import Quickshell

Item {
    id: root

    property bool showing: false

    Loader {
        id: heavyPanelLoader
        active: true
        visible: root.showing
        sourceComponent: Rectangle {
            width: 400
            height: 300
        }
    }
}

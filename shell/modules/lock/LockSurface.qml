import QtQuick
import Quickshell.Wayland
import qs.shared.theme
import qs.app.services

WlSessionLockSurface {
    id: root

    required property WlSessionLock lock
    property var context: null
    property var snapshotProvider: null
    // Freeze the selection for this lock session.
    property string style: "default"
    color: root.style === "caelestia" ? Appearance.colors.colLayer0Base : "#15191D"

    function forceFieldFocus() {
        if (loader.item && typeof loader.item.forceAuthFocus === "function") {
            loader.item.forceAuthFocus();
        } else if (loader.item && typeof loader.item.focusAuth === "function") {
            loader.item.focusAuth();
        } else if (loader.item) {
            loader.item.forceActiveFocus();
        }
    }

    Connections {
        target: root.context
        ignoreUnknownSignals: true
        function onShouldReFocus() {
            root.forceFieldFocus();
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        onPressed: root.forceFieldFocus()
        onPositionChanged: root.forceFieldFocus()
    }

    Loader {
        id: loader
        anchors.fill: parent
        sourceComponent: root.style === "caelestia" ? caelestia : defaultStyle
        onLoaded: {
            Qt.callLater(root.forceFieldFocus);
        }
    }

    Component {
        id: caelestia
        CaelestiaLock {
            lock: root.lock
            context: root.context
            snapshotProvider: root.snapshotProvider
            screen: root.screen
        }
    }

    Component {
        id: defaultStyle
        DefaultLock {
            snapshotProvider: root.snapshotProvider
            lock: root.lock
            context: root.context
            screen: root.screen
        }
    }
}

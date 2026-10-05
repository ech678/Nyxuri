import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.app.services

// An explicit declaration attached to the actual section. The build consumes
// only this JSON literal; its ID is also the runtime registration key.
Item {
    id: root
    required property string declaration
    required property Item target
    readonly property var entry: JSON.parse(declaration)
    readonly property string title: {
        const language = Qt.uiLanguage;
        return SpotlightCatalog.title(entry.id);
    }
    property bool registerAnchor: true
    property bool wholePage: false
    property int requestSerial: -1
    property real highlightOpacity: 0
    visible: false
    width: 0
    height: 0

    function polishTarget() {
        const ancestors = [];
        for (let item = target; item; item = item.parent)
            ancestors.push(item);
        for (let index = ancestors.length - 1; index >= 0; --index)
            ancestors[index].ensurePolished();
    }

    function reveal(serial) {
        if (!target || !target.visible || target.width <= 0 || target.height <= 0)
            return false;
        requestSerial = serial;
        if (wholePage && target instanceof Flickable)
            target.contentY = target.originY;
        // Each enclosing scroll viewport is handled in its own coordinates.
        for (let item = target.parent; item; item = item.parent) {
            if (item instanceof Flickable) {
                item.cancelFlick();
                const point = target.mapToItem(item.contentItem, 0, 0);
                item.contentY = Math.max(item.originY, Math.min(point.y - Metrics.spacingM, item.originY + Math.max(0, item.contentHeight - item.height)));
            }
        }
        highlightOpacity = 1;
        hold.restart();
        return true;
    }
    Component.onCompleted: {
        if (registerAnchor)
            SettingsBackend.registerSearchAnchor(root);
    }
    Component.onDestruction: {
        if (registerAnchor)
            SettingsBackend.unregisterSearchAnchor(root);
    }
    Connections {
        target: root.target
        function onWidthChanged() {
            SettingsBackend.retrySearch();
        }
        function onHeightChanged() {
            SettingsBackend.retrySearch();
        }
        function onYChanged() {
            SettingsBackend.retrySearch();
        }
        function onVisibleChanged() {
            SettingsBackend.retrySearch();
        }
    }
    Connections {
        target: SettingsBackend
        function onSearchSerialChanged() {
            if (root.requestSerial !== SettingsBackend.searchSerial) {
                hold.stop();
                root.highlightOpacity = 0;
            }
        }
    }
    Item {
        parent: root.target
        // A layout may own target's children. Give its overlay container no
        // layout extent, and draw relative to target without layout anchors.
        width: 0
        height: 0
        Layout.maximumWidth: 0
        Layout.maximumHeight: 0
        z: 100
        Rectangle {
            x: -parent.x
            y: -parent.y
            width: root.target ? root.target.width : 0
            height: root.target ? root.target.height : 0
            radius: Metrics.cornerM
            color: Appearance.applyAlpha(Appearance.colors.colPrimary, 0.10)
            border.width: 1
            border.color: Appearance.applyAlpha(Appearance.colors.colPrimary, 0.38)
            opacity: root.highlightOpacity
            visible: opacity > 0
            Behavior on opacity {
                NumberAnimation {
                    duration: Appearance.animation.expressiveDefaultEffects.duration
                    easing.type: Appearance.animation.expressiveDefaultEffects.type
                    easing.bezierCurve: Appearance.animation.expressiveDefaultEffects.bezierCurve
                }
            }
        }
    }
    Timer {
        id: hold
        interval: 1100
        onTriggered: root.highlightOpacity = 0
    }
}

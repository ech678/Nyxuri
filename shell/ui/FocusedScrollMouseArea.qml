import QtQuick

// Fork & Trim: iNiR modules/common/widgets/FocusedScrollMouseArea.qml
// Tracks wheel scroll events for volume/brightness adjustment
MouseArea {
    id: root

    signal scrollUp(int delta)
    signal scrollDown(int delta)
    signal movedAway()
    signal rightClicked(point point)

    property bool hovered: false
    property real lastScrollX: 0
    property real lastScrollY: 0
    property bool trackingScroll: false
    property real moveThreshold: 20

    acceptedButtons: Qt.LeftButton | Qt.RightButton
    hoverEnabled: true

    onEntered: {
        root.hovered = true;
    }

    onExited: {
        root.hovered = false;
        root.trackingScroll = false;
    }

    onWheel: event => {
        if (event.angleDelta.y < 0)
            root.scrollDown(event.angleDelta.y);
        else if (event.angleDelta.y > 0)
            root.scrollUp(event.angleDelta.y);
        root.lastScrollX = event.x;
        root.lastScrollY = event.y;
        root.trackingScroll = true;
    }

    onPositionChanged: mouse => {
        if (root.trackingScroll) {
            const dx = mouse.x - root.lastScrollX;
            const dy = mouse.y - root.lastScrollY;
            if (Math.sqrt(dx * dx + dy * dy) > root.moveThreshold) {
                root.movedAway();
                root.trackingScroll = false;
            }
        }
    }
}

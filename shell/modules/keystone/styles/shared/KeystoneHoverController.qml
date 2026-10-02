import QtQuick

QtObject {
    id: root

    required property bool triggerHovered
    required property bool surfaceHovered
    required property bool canOpen
    required property bool previewOpen
    required property int openDelay
    required property int closeDelay

    signal openRequested
    signal closeRequested

    function cancel() {
        openTimer.stop();
        closeTimer.stop();
    }

    function updateHover() {
        if (!triggerHovered)
            openTimer.stop();
        if (triggerHovered || surfaceHovered) {
            closeTimer.stop();
            if (triggerHovered && canOpen && !previewOpen && !openTimer.running) {
                if (openDelay === 0)
                    openRequested();
                else
                    openTimer.start();
            }
        } else {
            openTimer.stop();
            if (previewOpen && !closeTimer.running) {
                if (closeDelay === 0)
                    closeRequested();
                else
                    closeTimer.start();
            }
        }
    }

    onTriggerHoveredChanged: updateHover()
    onSurfaceHoveredChanged: updateHover()
    onCanOpenChanged: {
        if (!canOpen)
            openTimer.stop();
    }
    onPreviewOpenChanged: {
        if (!previewOpen)
            cancel();
    }

    property Timer openTimer: Timer {
        interval: root.openDelay
        onTriggered: {
            if (root.triggerHovered && root.canOpen && !root.previewOpen)
                root.openRequested();
        }
    }

    property Timer closeTimer: Timer {
        interval: root.closeDelay
        onTriggered: {
            if (!root.triggerHovered && !root.surfaceHovered && root.previewOpen)
                root.closeRequested();
        }
    }
}

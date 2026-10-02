import QtQuick
import qs.Services

Item {
    id: root
    required property string fileUrl
    required property Item iconItem
    property bool dragged: false
    property bool nativeDragActive: false
    property QtObject dockHandoffTarget: null
    property int dockHandoffSerial: 0
    function registerDockHandoff(target, serial) {
        dockHandoffTarget = target;
        dockHandoffSerial = serial;
    }
    property var grab: null
    property var pendingDrop: null
    function deferDrop(operation) {
        pendingDrop = operation;
    }
    anchors.fill: parent
    Drag.dragType: Drag.Automatic
    Drag.supportedActions: Qt.CopyAction | Qt.MoveAction
    Drag.proposedAction: Qt.CopyAction
    Drag.mimeData: ({
                        "text/uri-list": fileUrl + "\r\n"
                    })
    Drag.hotSpot.x: iconItem.width / 2
    Drag.hotSpot.y: iconItem.height / 2
    Drag.onDragStarted: {
        nativeDragActive = true;
        DockService.externalDragActive = true;
        DockService.fileDragActive = true;
    }
    Drag.onDragFinished: Qt.callLater(root.release)
    function release() {
        if (dockHandoffTarget) {
            dockHandoffTarget.finishExternalHandoff(dockHandoffSerial);
            dockHandoffTarget = null;
        }
        const operation = pendingDrop;
        pendingDrop = null;
        nativeDragActive = false;
        grab = null;
        DockService.finishFileDrag(operation);
    }
    DragHandler {
        id: handler
        target: null
        onActiveChanged: {
            if (active) {
                root.dragged = true;
                root.iconItem.grabToImage(result => {
                    if (!handler.active)
                        return;
                    root.grab = result;
                    root.Drag.imageSource = result.url;
                    root.Drag.active = true;
                });
            }
        }
    }
    Component.onDestruction: {
        if (dockHandoffTarget)
            dockHandoffTarget.cancelExternalHandoff(dockHandoffSerial);
        if (nativeDragActive) {
            DockService.externalDragActive = false;
            DockService.fileDragActive = false;
        }
    }
}

import QtQuick
import QtQuick.Controls
import Quickshell
import qs.app.services
import qs.shared.controls

StyledListView {
    id: root

    property bool popup: false
    property int dragIndex: -1
    property real dragDistance: 0

    function resetDrag() {
        root.dragIndex = -1;
        root.dragDistance = 0;
    }

    spacing: 3
    animateMovement: false

    remove: Transition {}

    model: ScriptModel {
        values: root.popup ? NotificationService.popupAppNameList : NotificationService.appNameList
    }

    delegate: NotificationGroup {
        required property int index
        required property var modelData

        delegateIndex: index
        dragHost: root
        popup: root.popup
        width: ListView.view.width
        notificationGroup: root.popup ? NotificationService.popupGroupsByAppName[modelData] :
                                        NotificationService.groupsByAppName[modelData]
    }
}

// Forked from snowarch/iNiR modules/common/widgets/ResourceUsageMonitor.qml
// at 28365436c2a00d083d29503aacfc0b5b321d67c6 (GPL-3.0).
// Nyxuri adaptation: acquire the existing SystemMonitorService module lease
// instead of starting a second resource polling service.
pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import qs.services

QtObject {
    id: root
    property Item target: null
    property bool active: true
    property string ownerId: ""
    property list<string> modules: ["cpu", "memory", "disk"]
    readonly property bool monitoring: active && (!target || (target.visible
        && (!target.QsWindow.window || target.QsWindow.window.visible)))
    property string _instanceId: ""
    property bool _holding: false
    property string _heldOwner: ""
    property string _heldModules: ""

    function sync(): void {
        if (root._instanceId === "")
            root._instanceId = SystemMonitorService.allocateConsumerId("bar-resource");
        const owner = String(root.ownerId || "").trim();
        const leaseOwner = owner + ":" + root._instanceId;
        const wanted = root.monitoring && owner !== "";
        const moduleKey = JSON.stringify(root.modules);
        if (root._holding && (!wanted || root._heldOwner !== leaseOwner)) {
            SystemMonitorService.clearConsumer(root._heldOwner);
            root._holding = false;
            root._heldOwner = "";
            root._heldModules = "";
        }
        if (!wanted) return;
        if (root._holding && root._heldModules === moduleKey) return;
        SystemMonitorService.setConsumerModules(leaseOwner, Array.from(root.modules));
        root._holding = true;
        root._heldOwner = leaseOwner;
        root._heldModules = moduleKey;
    }

    onMonitoringChanged: sync()
    onOwnerIdChanged: sync()
    onModulesChanged: sync()
    Component.onCompleted: sync()
    Component.onDestruction: {
        if (root._holding)
            SystemMonitorService.clearConsumer(root._heldOwner);
    }
}

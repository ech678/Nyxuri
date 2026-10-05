import QtQuick
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls
import qs.shared.i18n
import qs.app.services

// Three-lane drag layout for the status bar. Ported from end4-pC's
// DashboardBarLayoutCard: three lanes (left / middle / right) plus an "available"
// pool. Widgets are dragged between lanes or dropped on the pool to remove them.
//
// The widget ids come from DashboardBarWidgets, which is restricted to widgets the
// bar actually renders (shell/modules/bar/BarComponentLoader.qml), so a dropped id
// always maps to a real component. The committed layout is written through
// PersonalizationConfig.setBarLayouts — the UI never assigns the config
// properties directly.
DashboardCard {
    id: root

    property string title: I18n.tr("Bar layout")
    property string icon: "view_week"
    property var tileShape: MaterialShapeCanvas.Shape.Gem

    // Static catalog of arrangeable widgets.
    DashboardBarWidgets {
        id: barWidgets
    }

    ListModel {
        id: leftModel
    }
    ListModel {
        id: middleModel
    }
    ListModel {
        id: rightModel
    }
    ListModel {
        id: poolModel
    }

    // Drag state shared across lanes and the pool.
    property var drag: null
    property string hoverLane: ""
    property int hoverIndex: 0
    property real dragWidth: 90
    property real pointerX: 0
    property real pointerY: 0
    property var lastSynced: ({
                                  left: "",
                                  middle: "",
                                  right: "",
                                  pool: ""
                              })

    function baseItems(laneId) {
        if (laneId === "left")
            return PersonalizationConfig.barLayoutLeft;
        if (laneId === "middle")
            return PersonalizationConfig.barLayoutMiddle;
        if (laneId === "right")
            return PersonalizationConfig.barLayoutRight;
        return [];
    }

    function availableItems() {
        const used = {};
        ["left", "middle", "right"].forEach(lane => {
            baseItems(lane).forEach(id => {
                used[id] = true;
            });
        });
        const out = [];
        barWidgets.all.forEach(w => {
            if (!used[w.id])
                out.push({
                             id: w.id,
                             gap: false
                         });
        });
        return out;
    }

    function desiredItems(laneId) {
        // No __gap__ row while dragging: inserting one changes the model
        // signature mid-drag, syncModel then clear()/re-appends and destroys the
        // delegate that owns the mouse grab — the drag dies and the card hangs.
        // The drop slot is drawn by each Chip instead (dropSlot below), so the
        // model stays identical to the config for the whole drag.
        return baseItems(laneId).map(id => ({
            id: id,
            gap: false
        }));
    }

        function syncModel(model, items, key) {
        const sig = items.map(it => it.id + (it.gap ? ":g" : "")).join(",");
        if (root.lastSynced[key] === sig)
        return;
        root.lastSynced[key] = sig;
        model.clear();
        items.forEach(it => model.append(it));
    }

        function refreshLanes() {
        syncModel(leftModel, desiredItems("left"), "left");
        syncModel(middleModel, desiredItems("middle"), "middle");
        syncModel(rightModel, desiredItems("right"), "right");
        syncModel(poolModel, availableItems(), "pool");
    }

        function laneHovered(laneId) {
        return root.drag !== null && root.hoverLane === laneId;
    }

        function beginDrag(widgetId, lane, slot, pos, width) {
        root.drag = {
        id: widgetId,
        from: lane,
        fromIndex: slot
    };
        root.dragWidth = width;
        root.pointerX = pos.x;
        root.pointerY = pos.y;
        root.updateHover();
        root.refreshLanes();
    }

        function containsPoint(lane, x, y) {
        const p = lane.mapFromItem(root, x, y);
        return p.x >= 0 && p.y >= 0 && p.x <= lane.width && p.y <= lane.height;
    }

        function insertIndex(lane, x, y) {
        let before = 0;
        for (let i = 0; i < lane.chipRepeater.count; i += 1) {
        const chip = lane.chipRepeater.itemAt(i);
        if (!chip || chip.isGap || chip.beingDragged)
        continue;
        const c = chip.mapToItem(root, chip.width / 2, chip.height / 2);
        const half = chip.height / 2;
        if (c.y < y - half || (Math.abs(c.y - y) <= half && c.x < x))
        before += 1;
    }
        return before;
    }

        function updateHover() {
        root.hoverLane = "";
        root.hoverIndex = 0;
        for (let i = 0; i < laneRepeater.count; i += 1) {
        const lane = laneRepeater.itemAt(i);
        if (root.containsPoint(lane, root.pointerX, root.pointerY)) {
        root.hoverLane = lane.laneId;
        root.hoverIndex = root.insertIndex(lane, root.pointerX, root.pointerY);
        return;
    }
    }
        if (root.containsPoint(poolRect, root.pointerX, root.pointerY))
        root.hoverLane = "tray";
    }

        function removeWidget(lane, slot) {
        if (lane === "tray" || lane === "")
        return;
        const cur = baseItems(lane).slice();
        if (slot < 0 || slot >= cur.length)
        return;
        cur.splice(slot, 1);
        const next = {
        left: baseItems("left").slice(),
        middle: baseItems("middle").slice(),
        right: baseItems("right").slice()
    };
        next[lane] = cur;
        PersonalizationConfig.setBarLayouts(next.left, next.middle, next.right);
        root.refreshLanes();
    }

        function finishDrag() {
        if (root.drag === null)
        return;
        const d = root.drag;
        // Capture before clearing: the callLater callback below runs after
        // hoverLane is reset, and reading root.hoverLane there always saw "".
        const dropLane = root.hoverLane;
        const dropIndex = root.hoverIndex;
        root.drag = null;
        console.warn("[barlayout] finishDrag from=", d.from, d.fromIndex, "id=", d.id, "hover=", dropLane,
        dropIndex);
        Qt.callLater(() => {
        const next = {
        left: baseItems("left").slice(),
        middle: baseItems("middle").slice(),
        right: baseItems("right").slice()
    };
        if (d.from !== "tray" && next[d.from])
        next[d.from].splice(d.fromIndex, 1);
        if (dropLane === "tray") {
        // Dropped on the pool: remove the widget entirely.
    } else if (dropLane === "left" || dropLane === "middle" || dropLane === "right") {
        next[dropLane].splice(dropIndex, 0, d.id);
    } else {
        // Dropped on empty space: cancel, keep the widget where it was.
        if (d.from !== "tray" && next[d.from])
        next[d.from].splice(d.fromIndex, 0, d.id);
    }
        const changed = PersonalizationConfig.setBarLayouts(next.left, next.middle, next.right);
        console.warn("[barlayout] next=", JSON.stringify(next), "changed=", changed, "cfg=", JSON.stringify(
        [PersonalizationConfig.barLayoutLeft, PersonalizationConfig.barLayoutMiddle,
        PersonalizationConfig.barLayoutRight]));
        root.refreshLanes();
    });
        root.hoverLane = "";
    }

        // ---- visual primitives -------------------------------------------------

        component Chip: Rectangle {
        property string widgetId: ""
        property string lane: ""
        property int slot: -1
        property bool isGap: false
        property bool ghost: false
        property bool interactive: true

        readonly property var info: barWidgets.byId(widgetId)
        readonly property bool beingDragged: !ghost && root.drag !== null && root.drag.id === widgetId

        implicitHeight: 34
        implicitWidth: isGap ? root.dragWidth : (beingDragged ? 0 : chipRow.implicitWidth + 24)
        radius: height / 2
        color: isGap ? "transparent" : (lane === "tray" ? Qt.rgba(1, 1, 1, 0.1) :
        Appearance.colors.colSecondaryContainer)

        border.width: isGap ? 2 : 0
        border.color: Appearance.colors.colPrimary
        opacity: beingDragged ? 0 : (isGap ? 0.7 : 1)
        Behavior on implicitWidth {
        NumberAnimation {
        duration: 160
        easing.type: Easing.OutCubic
    }
    }

        // Row, not RowLayout: chip width comes from chipRow.implicitWidth, and a
        // RowLayout that is also anchored has its implicit size computed by the
        // anchor rather than by its children — that collapses the chip to the
        // icon and clips the label.
        Row {
        id: chipRow

        visible: !isGap
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        MaterialSymbol {
        text: info.icon
        iconSize: 16
        color: Appearance.colors.colOnSecondaryContainer
    }

        StyledText {
        text: barWidgets.displayName(info)
        font.pixelSize: 12
        color: Appearance.colors.colOnSecondaryContainer
    }
    }

        // Drop indicator drawn at this chip slot while the pointer hovers its
        // lane. Slot numbers here are model coordinates, which since the __gap__
        // removal are the same as config coordinates — insertIndex and
        // d.fromIndex finally live in one coordinate system.
        Rectangle {
        visible: root.drag !== null && !ghost && !isGap && lane !== "tray" && root.laneHovered(lane) && slot
        === root.hoverIndex
        x: -parent.width / 2 - width / 2 - 3
        anchors.verticalCenter: parent.verticalCenter
        width: root.dragWidth
        height: parent.height
        radius: height / 2
        color: "transparent"
        border.width: 2
        border.color: Appearance.colors.colPrimary
        z: 60
    }

        MouseArea {
        id: mouseArea

        anchors.fill: parent
        enabled: interactive && !isGap
        preventStealing: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        onPressed: mouse => {
        if (mouse.button === Qt.RightButton) {
        root.removeWidget(lane, slot);
        return;
    }
        const p = root.mapFromItem(mouseArea, mouse.x, mouse.y);
        root.beginDrag(widgetId, lane, slot, p, width);
    }
        onPositionChanged: mouse => {
        if (!pressed || root.drag === null || root.drag.id !== widgetId)
        return;
        const p = root.mapFromItem(mouseArea, mouse.x, mouse.y);
        root.pointerX = p.x;
        root.pointerY = p.y;
        root.updateHover();
        root.refreshLanes();
    }
        onReleased: () => root.finishDrag()
        onCanceled: () => root.finishDrag()
    }
    }

        component Lane: Rectangle {
        id: laneRoot

        property string laneId: ""
        property string laneLabel: ""
        property var model: null
        property alias chipRepeater: repeater

        radius: 20
        color: root.laneHovered(laneId) ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.06)
        border.width: root.laneHovered(laneId) ? 2 : 0
        border.color: Appearance.colors.colPrimary
        Behavior on color {
        ColorAnimation {
        duration: 150
    }
    }

        ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        StyledText {
        text: laneLabel.toUpperCase()
        font.pixelSize: 12
        font.weight: Font.DemiBold
        font.letterSpacing: 1.2
        color: Appearance.colors.colSubtext
    }

        Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        Flickable {
        id: laneFlick
        anchors.fill: parent
        contentWidth: flow.implicitWidth
        contentHeight: flow.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Flow {
        id: flow

        width: parent.width
        spacing: 6
        move: Transition {
        NumberAnimation {
        properties: "x,y"
        duration: 200
        easing.type: Easing.OutBack
        easing.overshoot: 1.2
    }
    }

        Repeater {
        id: repeater

        model: laneRoot.model
        delegate: Chip {
        // ListModel roles bind directly; modelData is
        // undefined here and made every chip render the
        // byId(undefined) fallback (icon only, no label).
        widgetId: model.id
        lane: laneRoot.laneId
        slot: index
        isGap: model.gap === true
    }
    }
    }
    }

        StyledText {
        visible: laneRoot.model && laneRoot.model.count === 0
        text: I18n.tr("Drop here")
        font.pixelSize: 15
        color: Appearance.colors.colSubtext
        opacity: 0.6
        anchors.centerIn: parent
    }
    }
    }
    }

        // ---- layout ------------------------------------------------------------

        ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        RowLayout {
        spacing: 10

        MaterialShapeWrappedMaterialSymbol {
        wrappedShape: root.tileShape
        text: root.icon
        iconSize: 24
        fill: 1
        padding: 10
        color: Appearance.colors.colPrimary
        colSymbol: Appearance.colors.colOnPrimary
    }

        ColumnLayout {
        spacing: 2

        StyledText {
        text: root.title
        font.pixelSize: 19
        font.weight: Font.DemiBold
        color: Appearance.colors.colOnLayer1
    }

        StyledText {
        text: I18n.tr("Drag widgets between lanes to arrange the bar")
        font.pixelSize: 12
        color: Appearance.colors.colSubtext
    }
    }
    }

        RowLayout {
        id: lanesRow

        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 10

        Repeater {
        id: laneRepeater

        model: [
        {
        id: "left",
        label: I18n.tr("Left")
    },
        {
        id: "middle",
        label: I18n.tr("Middle")
    },
        {
        id: "right",
        label: I18n.tr("Right")
    }
        ]

        delegate: Lane {
        laneId: modelData.id
        laneLabel: modelData.label
        model: modelData.id === "left" ? leftModel : modelData.id === "middle" ? middleModel : rightModel
        Layout.fillWidth: true
        Layout.fillHeight: true
    }
    }
    }

        Rectangle {
        id: poolRect

        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(flowPool.implicitHeight + 48, 190)
        radius: 20
        color: Qt.rgba(1, 1, 1, 0.04)
        border.width: root.drag !== null && root.hoverLane === "tray" ? 2 : 1
        border.color: root.drag !== null && root.hoverLane === "tray" ? Appearance.colors.colError :
        Appearance.colors.colOutlineVariant

        ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        StyledText {
        text: I18n.tr("Available").toUpperCase()
        font.pixelSize: 12
        font.weight: Font.DemiBold
        font.letterSpacing: 1.2
        color: Appearance.colors.colSubtext
    }

        Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        Flickable {
        anchors.fill: parent
        contentWidth: flowPool.implicitWidth
        contentHeight: flowPool.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Flow {
        id: flowPool

        width: parent.width
        spacing: 6

        Repeater {
        model: poolModel
        delegate: Chip {
        widgetId: model.id
        lane: "tray"
        slot: index
    }
    }
    }
    }
    }
    }
    }
    }

        // Ghost chip that follows the pointer while dragging.
        Chip {
        visible: root.drag !== null
        ghost: true
        interactive: false
        widgetId: root.drag ? root.drag.id : ""
        z: 100
        scale: 1.06
        opacity: 0.95
        x: root.pointerX - width / 2
        y: root.pointerY - height / 2
    }

        // Follow config edits (own writes and external ones) — refreshLanes is no
        // longer driven solely by drag events.
        Connections {
        target: PersonalizationConfig

        function onBarLayoutLeftChanged() {
        root.refreshLanes();
    }

        function onBarLayoutMiddleChanged() {
        root.refreshLanes();
    }

        function onBarLayoutRightChanged() {
        root.refreshLanes();
    }
    }

        Component.onCompleted: root.refreshLanes()
    }

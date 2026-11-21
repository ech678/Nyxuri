import QtQuick
import QtQuick.Controls
import QtQuick.Window
import qs.commons
import qs.ui
import qs.commons.i18n

FocusScope {
    id: root

    property var options: []
    // Values are plain id strings OR bar lane entry objects
    // {widgetId, uid, enabled} (D4a). Entry values render an enabled toggle
    // and identify chips by uid so duplicate ids (spacers) stay distinct.
    property var values: []
    property string zone: ""
    property var dragCoordinator: null
    // Bar lanes allow the same widget more than once (spacers); pools
    // (quick settings) keep every id unique.
    property bool allowDuplicates: false
    property int highlightedIndex: 0
    property bool expanded: false
    property real fieldHeight: 40
    property real itemHeight: 40
    property real menuItemSpacing: 4
    property int maxVisibleItems: 6
    property real scrollTargetX: 0
    property real autoScrollVelocity: 0
    readonly property Item popupParentItem: root.Window.window ? root.Window.window.contentItem : null
    readonly property real menuPadding: 6
    readonly property real menuGap: 6
    readonly property var usedIds: {
        const used = [];
        const source = Array.isArray(root.values) ? root.values : [];
        for (let index = 0; index < source.length; index += 1) {
            const id = root.valueId(source[index]);
            if (used.indexOf(id) === -1)
                used.push(id);
        }
        return used;
    }
    readonly property var availableOptions: allowDuplicates ? options : options.filter(option => {
        return root.usedIds.indexOf(root.optionValue(option)) === -1;
    })
    readonly property int visibleMenuItemCount: Math.min(Math.max(1, maxVisibleItems), Math.max(1, availableOptions.length))
    readonly property real listTargetHeight: Math.max(itemHeight + menuPadding * 2, Math.ceil(availableOptions.length / 2) * (itemHeight + menuItemSpacing) + menuPadding * 2)
    readonly property bool dragActive: dragCoordinator && dragCoordinator.dragActive
    readonly property bool entryValues: {
        const source = Array.isArray(root.values) ? root.values : [];
        return source.length > 0 && source[0] && typeof source[0] === "object";
    }

    signal toggled(string componentId)
    signal removed(string entryKey)
    signal enabledToggled(string entryKey)

    function valueId(value) {
        return value && typeof value === "object" ? String(value.widgetId || "") : String(value || "");
    }

    function valueKey(value) {
        return value && typeof value === "object" ? String(value.uid || value.widgetId || "") : String(value || "");
    }

    function valueEnabled(value) {
        return !(value && typeof value === "object" && value.enabled === false);
    }

    function optionValue(option) {
        return option && typeof option === "object" ? String(option.value || "") : String(option || "");
    }

    function optionLabel(option) {
        return option && typeof option === "object" ? String(option.label || option.value || "") : String(option || "");
    }

    function optionIcon(option) {
        return option && typeof option === "object" ? String(option.icon || "widgets") : "widgets";
    }

    function labelFor(componentId) {
        for (let index = 0; index < root.options.length; index += 1) {
            if (root.optionValue(root.options[index]) === componentId)
                return root.optionLabel(root.options[index]);
        }
        return componentId;
    }

    function iconFor(componentId) {
        for (let index = 0; index < root.options.length; index += 1) {
            if (root.optionValue(root.options[index]) === componentId)
                return root.optionIcon(root.options[index]);
        }
        return "widgets";
    }

    function entryIndex(entryKey) {
        for (let index = 0; index < chipModel.count; index += 1) {
            if (chipModel.get(index).entryKey === entryKey)
                return index;
        }
        return -1;
    }

    function synchronizeEntries(entries) {
        const desiredKeys = entries.map(entry => {
            return entry.entryKey;
        });
        for (let index = chipModel.count - 1; index >= 0; index -= 1) {
            if (desiredKeys.indexOf(chipModel.get(index).entryKey) === -1)
                chipModel.remove(index);
        }
        for (let index = 0; index < entries.length; index += 1) {
            const entry = entries[index];
            const currentIndex = root.entryIndex(entry.entryKey);
            if (currentIndex < 0) {
                chipModel.insert(index, entry);
            } else {
                if (currentIndex !== index)
                    chipModel.move(currentIndex, index, 1);

                chipModel.setProperty(index, "componentId", entry.componentId);
                chipModel.setProperty(index, "enabled", entry.enabled);
                chipModel.setProperty(index, "placeholder", entry.placeholder);
            }
        }
    }

    function synchronizeValues() {
        if (root.dragActive)
            return;

        const entries = [];
        const source = Array.isArray(root.values) ? root.values : [];
        for (let index = 0; index < source.length; index += 1) {
            entries.push({
                "entryKey": root.valueKey(source[index]),
                "componentId": root.valueId(source[index]),
                "enabled": root.valueEnabled(source[index]),
                "placeholder": false
            });
        }
        root.synchronizeEntries(entries);
    }

    function showDropPreview(componentKey, sourceZone, targetZone, targetIndex) {
        const source = Array.isArray(root.values) ? root.values : [];
        const entries = [];
        for (let index = 0; index < source.length; index += 1) {
            const value = source[index];
            const isDraggedComponent = root.valueKey(value) === componentKey;
            const movingWithinThisZone = root.zone === sourceZone && root.zone === targetZone;
            if (isDraggedComponent && movingWithinThisZone)
                continue;

            if (isDraggedComponent && root.zone !== sourceZone)
                continue;

            entries.push({
                "entryKey": root.valueKey(value),
                "componentId": root.valueId(value),
                "enabled": root.valueEnabled(value),
                "placeholder": false
            });
        }
        if (root.zone === targetZone) {
            const insertionIndex = Math.max(0, Math.min(entries.length, targetIndex));
            const draggedId = root.dragCoordinator ? root.dragCoordinator.componentId : "";
            entries.splice(insertionIndex, 0, {
                "entryKey": "preview",
                "componentId": draggedId,
                "enabled": true,
                "placeholder": true
            });
        }
        root.synchronizeEntries(entries);
    }

    function clearDropPreview() {
        root.synchronizeValues();
        root.autoScrollVelocity = 0;
    }

    function insertionIndexAt(coordinatorItem, sceneX, sceneY) {
        const local = chipList.mapFromItem(coordinatorItem, sceneX, sceneY);
        const contentPosition = local.x + chipList.contentX;
        let insertionIndex = 0;
        for (let index = 0; index < chipModel.count; index += 1) {
            const delegateItem = chipList.itemAtIndex(index);
            if (!delegateItem || delegateItem.placeholder || delegateItem.isDragged)
                continue;

            if (contentPosition < delegateItem.x + delegateItem.width / 2)
                return insertionIndex;

            insertionIndex += 1;
        }
        return insertionIndex;
    }

    function containsScenePoint(coordinatorItem, sceneX, sceneY) {
        const local = root.mapFromItem(coordinatorItem, sceneX, sceneY);
        return local.x >= 0 && local.x <= root.width && local.y >= 0 && local.y <= root.height;
    }

    function updateAutoScroll(coordinatorItem, sceneX) {
        const local = chipViewport.mapFromItem(coordinatorItem, sceneX, 0);
        const edgeSize = 44;
        if (local.x < edgeSize && chipList.contentX > 0)
            root.autoScrollVelocity = -Math.min(8, (edgeSize - local.x) / edgeSize * 8);
        else if (local.x > chipViewport.width - edgeSize && chipList.contentX < root.maxContentX())
            root.autoScrollVelocity = Math.min(8, (local.x - chipViewport.width + edgeSize) / edgeSize * 8);
        else
            root.autoScrollVelocity = 0;
    }

    function stepAutoScroll() {
        if (root.autoScrollVelocity === 0)
            return;

        chipList.contentX = root.clampContentX(chipList.contentX + root.autoScrollVelocity);
        root.scrollTargetX = chipList.contentX;
    }

    function maxContentX() {
        return Math.max(0, chipList.contentWidth - chipList.width);
    }

    function clampContentX(value) {
        return Math.max(0, Math.min(value, root.maxContentX()));
    }

    function handleWheel(wheelEvent) {
        const pixelX = Number(wheelEvent.pixelDelta.x);
        const pixelY = Number(wheelEvent.pixelDelta.y);
        const angleX = Number(wheelEvent.angleDelta.x);
        const angleY = Number(wheelEvent.angleDelta.y);
        let delta = 0;
        if (isFinite(pixelX) && pixelX !== 0)
            delta = -pixelX;
        else if (isFinite(pixelY) && pixelY !== 0)
            delta = -pixelY;
        else if (isFinite(angleX) && angleX !== 0)
            delta = -angleX;
        else if (isFinite(angleY) && angleY !== 0)
            delta = -angleY;
        if (delta === 0)
            return;

        const base = scrollAnimation.running ? root.scrollTargetX : chipList.contentX;
        root.scrollTargetX = root.clampContentX(base + delta);
        chipList.contentX = root.scrollTargetX;
        wheelEvent.accepted = true;
    }

    function updatePopupGeometry() {
        if (!root.popupParentItem)
            return false;

        const origin = root.mapToItem(root.popupParentItem, 0, 0);
        const margin = 12;
        optionsPopup.width = root.width;
        optionsPopup.height = root.listTargetHeight;
        optionsPopup.x = Math.max(margin, Math.min(origin.x, root.popupParentItem.width - optionsPopup.width - margin));
        const belowY = origin.y + root.fieldHeight + root.menuGap;
        const aboveY = origin.y - optionsPopup.height - root.menuGap;
        optionsPopup.y = belowY + optionsPopup.height <= root.popupParentItem.height - margin ? belowY : Math.max(margin, aboveY);
        return true;
    }

    function openMenu() {
        if (!root.expanded && root.updatePopupGeometry()) {
            root.highlightedIndex = 0;
            root.expanded = true;
        }
    }

    function closeMenu() {
        root.expanded = false;
    }

    function toggleMenu() {
        if (root.expanded)
            root.closeMenu();
        else
            root.openMenu();
    }

    function moveHighlight(delta) {
        if (root.availableOptions.length === 0)
            return;

        root.highlightedIndex = (root.highlightedIndex + delta + root.availableOptions.length) % root.availableOptions.length;
    }

    function toggleHighlighted() {
        if (root.highlightedIndex < 0 || root.highlightedIndex >= root.availableOptions.length)
            return;

        root.toggled(root.optionValue(root.availableOptions[root.highlightedIndex]));
    }

    function handleKey(event) {
        if (!root.expanded) {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space || event.key === Qt.Key_Down) {
                root.openMenu();
                event.accepted = true;
            }
            return;
        }
        if (event.key === Qt.Key_Escape)
            root.closeMenu();
        else if (event.key === Qt.Key_Down)
            root.moveHighlight(1);
        else if (event.key === Qt.Key_Up)
            root.moveHighlight(-1);
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space)
            root.toggleHighlighted();
        else
            return;
        event.accepted = true;
    }

    implicitWidth: 360
    implicitHeight: fieldHeight
    activeFocusOnTab: true
    onValuesChanged: synchronizeValues()
    Component.onCompleted: synchronizeValues()
    Keys.onPressed: event => {
        return root.handleKey(event);
    }
    onExpandedChanged: {
        if (expanded) {
            updatePopupGeometry();
            optionsPopup.open();
        } else if (optionsPopup.visible) {
            optionsPopup.close();
        }
    }

    Rectangle {
        id: fieldFrame

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: root.fieldHeight
        clip: true
        color: root.expanded || fieldTap.pressed ? Appearance.colors.colLayer2Active : fieldHover.hovered ? Appearance.colors.colLayer2Hover : Appearance.colors.colLayer2

        Item {
            id: chipViewport

            clip: true

            anchors {
                left: parent.left
                right: arrowIcon.left
                top: parent.top
                bottom: parent.bottom
                leftMargin: 8
                rightMargin: 8
            }

            ListView {
                id: chipList

                anchors.fill: parent
                orientation: ListView.Horizontal
                spacing: 6
                model: chipModel
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: false

                Behavior on contentX {
                    enabled: !root.dragActive

                    NumberAnimation {
                        id: scrollAnimation

                        alwaysRunToEnd: false
                        duration: Appearance.animation.scroll.duration
                        easing.type: Appearance.animation.scroll.type
                        easing.bezierCurve: Appearance.animation.scroll.bezierCurve
                    }
                }

                delegate: Item {
                    id: chipDelegate

                    required property string entryKey
                    required property string componentId
                    required property bool placeholder
                    required property bool enabled
                    // D4a: identity is the entry uid (duplicate widget ids are
                    // legal), so only the dragged chip hides.
                    readonly property bool ownsActiveDrag: root.dragActive && root.dragCoordinator && root.dragCoordinator.componentUid === chipDelegate.entryKey && root.dragCoordinator.sourceZone === root.zone
                    readonly property bool isDragged: root.dragActive && root.dragCoordinator && root.dragCoordinator.componentUid === chipDelegate.entryKey && !placeholder
                    readonly property bool canToggleEnabled: root.entryValues && !placeholder
                    readonly property real naturalWidth: Math.max(88, chipLabel.implicitWidth + (chipDelegate.canToggleEnabled ? 94 : 70))

                    width: placeholder && root.dragCoordinator ? root.dragCoordinator.dragWidth : isDragged ? 0 : naturalWidth
                    height: chipList.height
                    opacity: isDragged ? 0 : 1

                    Rectangle {
                        id: chipSurface

                        width: chipDelegate.placeholder ? parent.width : chipDelegate.naturalWidth
                        height: 30
                        anchors.centerIn: parent
                        radius: Appearance.rounding.small
                        color: chipDelegate.placeholder ? Appearance.colors.colLayer2Active : chipHover.hovered ? Appearance.colors.colPrimaryContainerHover : Appearance.colors.colPrimaryContainer
                        // A disabled entry keeps its slot and geometry, only
                        // the surface recedes (D4a enabled axis).
                        opacity: chipDelegate.placeholder ? 0.45 : chipDelegate.enabled ? 1 : 0.45

                        MaterialSymbol {
                            id: chipIcon

                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.iconFor(chipDelegate.componentId)
                            iconSize: 17
                            fill: 1
                            color: Appearance.colors.colOnPrimaryContainer
                            visible: !chipDelegate.placeholder
                        }

                        Text {
                            id: chipLabel

                            text: root.labelFor(chipDelegate.componentId)
                            color: Appearance.colors.colOnPrimaryContainer
                            font.family: Fonts.ui
                            font.pixelSize: NexusStyle.font.bodySmall
                            font.weight: Font.Medium
                            visible: !chipDelegate.placeholder
                            elide: Text.ElideRight

                            anchors {
                                left: chipIcon.right
                                right: chipDelegate.canToggleEnabled ? enabledToggle.left : closeButton.left
                                leftMargin: 6
                                rightMargin: 4
                                verticalCenter: parent.verticalCenter
                            }
                        }

                        Item {
                            id: enabledToggle

                            anchors.right: closeButton.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: 24
                            height: 30
                            visible: chipDelegate.canToggleEnabled

                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: chipDelegate.enabled ? "visibility" : "visibility_off"
                                iconSize: 16
                                fill: 0
                                color: Appearance.colors.colOnPrimaryContainer
                            }

                            MouseArea {
                                id: enabledMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: mouse => {
                                    mouse.accepted = true;
                                    root.enabledToggled(chipDelegate.entryKey);
                                }
                            }
                        }

                        Item {
                            id: closeButton

                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            width: 30
                            height: 30
                            visible: !chipDelegate.placeholder

                            MaterialSymbol {
                                anchors.centerIn: parent
                                text: "close"
                                iconSize: 17
                                color: Appearance.colors.colOnPrimaryContainer
                            }

                            MouseArea {
                                id: closeMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: mouse => {
                                    mouse.accepted = true;
                                    root.removed(chipDelegate.entryKey);
                                }
                            }
                        }

                        HoverHandler {
                            id: chipHover
                        }

                        MouseArea {
                            enabled: !chipDelegate.placeholder
                            cursorShape: dragHandler.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                            onClicked: mouse => {
                                return mouse.accepted = true;
                            }

                            anchors {
                                left: parent.left
                                right: closeButton.left
                                top: parent.top
                                bottom: parent.bottom
                            }
                        }

                        DragHandler {
                            id: dragHandler

                            enabled: root.dragCoordinator !== null && (!chipDelegate.placeholder || chipDelegate.ownsActiveDrag) && (!closeMouse.containsMouse || chipDelegate.ownsActiveDrag) && (!enabledMouse.containsMouse || chipDelegate.ownsActiveDrag)
                            target: null
                            dragThreshold: 8
                            onActiveChanged: {
                                if (active)
                                    root.dragCoordinator.beginDrag(root, chipDelegate.entryKey, chipDelegate.componentId, root.labelFor(chipDelegate.componentId), root.iconFor(chipDelegate.componentId), chipDelegate.naturalWidth, centroid.scenePosition);
                                else if (root.dragCoordinator && root.dragCoordinator.dragActive && root.dragCoordinator.componentUid === chipDelegate.entryKey)
                                    root.dragCoordinator.finishDrag();
                            }
                            onTranslationChanged: {
                                if (active)
                                    root.dragCoordinator.updateDrag(centroid.scenePosition);
                            }
                        }
                    }
                }

                move: Transition {
                    ElementMoveAnimation {
                        property: "x"
                    }
                }

                moveDisplaced: Transition {
                    ElementMoveAnimation {
                        property: "x"
                    }
                }

                addDisplaced: Transition {
                    ElementMoveAnimation {
                        property: "x"
                    }
                }

                removeDisplaced: Transition {
                    ElementMoveAnimation {
                        property: "x"
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.NoButton
                onWheel: wheelEvent => {
                    return root.handleWheel(wheelEvent);
                }
            }
        }

        Text {
            visible: chipModel.count === 0
            text: I18n.tr("No components selected")
            color: Appearance.colors.colSubtext
            font.family: Fonts.ui
            font.pixelSize: NexusStyle.font.bodyMedium

            anchors {
                left: parent.left
                right: arrowIcon.left
                leftMargin: 14
                rightMargin: 8
                verticalCenter: parent.verticalCenter
            }
        }

        MaterialSymbol {
            id: arrowIcon

            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "expand_more"
            iconSize: 20
            color: Appearance.colors.colOnLayer2
            rotation: root.expanded ? 180 : 0

            Behavior on rotation {
                NumberAnimation {
                    duration: Appearance.animation.expressiveFastSpatial.duration
                    easing.type: Appearance.animation.expressiveFastSpatial.type
                    easing.bezierCurve: Appearance.animation.expressiveFastSpatial.bezierCurve
                }
            }
        }

        TapHandler {
            id: fieldTap

            gesturePolicy: TapHandler.ReleaseWithinBounds
            onTapped: {
                root.forceActiveFocus();
                root.toggleMenu();
            }
        }

        HoverHandler {
            id: fieldHover
        }

        Rectangle {
            height: root.expanded ? 2 : 1
            color: root.expanded ? Appearance.colors.colPrimary : Appearance.colors.colOutlineVariant

            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
            }
        }

        Behavior on color {
            ColorAnimation {
                duration: Appearance.animation.expressiveFastEffects.duration
                easing.type: Appearance.animation.expressiveFastEffects.type
                easing.bezierCurve: Appearance.animation.expressiveFastEffects.bezierCurve
            }
        }
    }

    ListModel {
        id: chipModel
    }

    Popup {
        id: optionsPopup

        parent: root.popupParentItem
        padding: 0
        modal: false
        dim: false
        focus: true
        closePolicy: Popup.CloseOnEscape
        onClosed: root.expanded = false

        background: Item {}

        contentItem: Rectangle {
            id: optionPoolCard

            clip: true
            radius: Appearance.rounding.normal
            color: Appearance.m3colors.m3surfaceContainerHigh

            Flickable {
                id: optionPool

                anchors.fill: parent
                anchors.margins: root.menuPadding
                contentWidth: width
                contentHeight: Math.max(height, optionFlow.childrenRect.height)
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                Flow {
                    id: optionFlow

                    width: optionPool.width
                    spacing: root.menuItemSpacing

                    Repeater {
                        model: root.availableOptions

                        delegate: Rectangle {
                            id: optionChip

                            required property var modelData
                            required property int index
                            readonly property string componentId: root.optionValue(modelData)
                            readonly property bool highlighted: index === root.highlightedIndex

                            width: Math.min(optionFlow.width, Math.max(88, optionLabel.implicitWidth + 52))
                            height: 30
                            radius: Appearance.rounding.small
                            color: optionTap.pressed ? Appearance.colors.colPrimaryContainerActive : optionHover.hovered || highlighted ? Appearance.colors.colPrimaryContainerHover : Appearance.colors.colPrimaryContainer

                            MaterialSymbol {
                                id: optionIcon

                                anchors.left: parent.left
                                anchors.leftMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                text: root.optionIcon(optionChip.modelData)
                                iconSize: 17
                                fill: 1
                                color: Appearance.colors.colOnPrimaryContainer
                            }

                            Text {
                                id: optionLabel

                                anchors.left: optionIcon.right
                                anchors.leftMargin: 6
                                anchors.right: parent.right
                                anchors.rightMargin: 12
                                anchors.verticalCenter: parent.verticalCenter
                                text: root.optionLabel(optionChip.modelData)
                                color: Appearance.colors.colOnPrimaryContainer
                                font.family: Fonts.ui
                                font.pixelSize: NexusStyle.font.bodySmall
                                font.weight: Font.Medium
                                elide: Text.ElideRight
                            }

                            HoverHandler {
                                id: optionHover

                                onHoveredChanged: {
                                    if (hovered)
                                        root.highlightedIndex = optionChip.index;
                                }
                            }

                            TapHandler {
                                id: optionTap

                                onTapped: root.toggled(optionChip.componentId)
                            }
                        }
                    }

                    Text {
                        visible: root.availableOptions.length === 0
                        width: optionFlow.width
                        height: root.itemHeight
                        text: I18n.tr("All widgets are in use")
                        color: Appearance.colors.colSubtext
                        font.family: Fonts.ui
                        font.pixelSize: NexusStyle.font.bodySmall
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        enter: Transition {
            NumberAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: Appearance.animation.standardDecel.duration
                easing.type: Appearance.animation.standardDecel.type
                easing.bezierCurve: Appearance.animation.standardDecel.bezierCurve
            }
        }
    }
}

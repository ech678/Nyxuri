pragma ComponentBehavior: Bound
import QtQuick
import qs.Common

FocusScope {
    id: root
    required property var controller
    property bool timeMode: false
    required property SpotlightStyle style
    property bool railExpanded: false
    property bool allSelected: false
    onActiveFocusChanged: if (!activeFocus)
                              allSelected = false
    onVisibleChanged: if (!visible)
                          allSelected = false

    function completeText() {
        const values = [];
        for (let i = 0; i < 4; ++i) {
            const item = fields.itemAt(i);
            values.push(item && item.input.text.length ? item.input.text : "…");
        }
        return values[0] + " " + values[1] + (timeMode ? " → " : " ≈ ") + values[2] + " " + values[3];
    }
    signal routedKey(var event)
    signal releasedKey(var event)
    signal exitRequested
    readonly property bool composing: {
        const item = fields.itemAt(controller.activeSlot);
        return item ? item.input.preeditText.length > 0 : false;
    }
    function focusSlot(selectAll) {
        if (!visible || !enabled || !controller.active)
            return;
        const item = fields.itemAt(controller.activeSlot);
        if (!item)
            return;
        item.input.forceActiveFocus();
        if (selectAll)
            item.input.selectAll();
        const left = item.x, right = left + item.width;
        viewport.contentX = Math.max(0, Math.min(viewport.contentWidth - viewport.width, left
                                                 < viewport.contentX ? left : right > viewport.contentX
                                                                       + viewport.width ? right
                                                                                          - viewport.width :
                                                                                          viewport.contentX));
    }
    Connections {
        target: root.controller
        function onFocusRequested(selectAll) {
            root.allSelected = false;
            Qt.callLater(() => root.focusSlot(selectAll));
        }
    }
    Flickable {
        id: viewport
        anchors.fill: parent
        clip: true
        contentWidth: row.implicitWidth
        contentHeight: height
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalFlick
        Rectangle {
            width: row.implicitWidth
            height: 24
            y: (viewport.height - height) / 2
            visible: root.allSelected
            color: Appearance.colors.colPrimary
        }
        Row {
            id: row
            spacing: 8
            height: viewport.height
            Repeater {
                id: fields
                model: 4
                delegate: Item {
                    id: slot
                    required property int index
                    property alias input: input
                    readonly property bool unit: index === 1 || index === 3
                    readonly property bool selected: root.controller.activeSlot === index
                    readonly property real textWidth: Math.min(Math.max(12, input.implicitWidth), Math.max(100,
                                                                                                           viewport.width
                                                                                                           * 0.5))
                    width: textWidth + (index === 1 ? 24 : 0)
                    height: row.height
                    Rectangle {
                        x: input.x
                        y: (slot.height - height) / 2
                        width: Math.min(input.contentWidth, input.width)
                        height: input.font.pixelSize + 4
                        visible: !root.allSelected && slot.selected && !input.selectedText.length
                                 && input.text.length > 0
                        color: Appearance.colors.colPrimary
                    }
                    Text {
                        x: slot.textWidth + 8
                        anchors.verticalCenter: parent.verticalCenter
                        visible: slot.index === 1
                        text: root.timeMode ? "→" : "≈"
                        font.pixelSize: 20
                        color: root.allSelected ? Appearance.colors.colOnPrimary :
                                                  Appearance.colors.colOnSurfaceVariant
                    }
                    TextInput {
                        id: input
                        width: slot.textWidth
                        height: parent.height
                        text: slot.selected && slot.unit && root.controller.choosing
                              && root.controller.editingUnit ? root.controller.draft : root.controller.value(
                                                                   slot.index)
                        color: root.allSelected || slot.selected ? Appearance.colors.colOnPrimary :
                                                                   Appearance.colors.colOnSurface
                        selectionColor: Appearance.colors.colPrimary
                        selectedTextColor: Appearance.colors.colOnPrimary
                        font.family: Fonts.ui
                        font.pixelSize: 20
                        verticalAlignment: TextInput.AlignVCenter
                        horizontalAlignment: TextInput.AlignLeft
                        clip: true
                        selectByMouse: true
                        activeFocusOnTab: false
                        maximumLength: slot.unit ? 128 : 1024
                        readOnly: !root.controller.editable(slot.index)
                        inputMethodHints: slot.unit || root.timeMode ? Qt.ImhNoPredictiveText :
                                                                       Qt.ImhFormattedNumbersOnly
                        Accessible.name: root.timeMode ? (slot.index === 0 ? qsTr("Source time") : slot.index
                                                                             === 1 ? qsTr("Source time zone") :
                                                                                     slot.index === 2 ? qsTr(
                                                                                                            "Target time") :
                                                                                                        qsTr("Target time zone")) :
                                                         (slot.index === 0 ? qsTr("Source amount") :
                                                                             slot.index === 1 ? qsTr(
                                                                                                    "Source currency") :
                                                                                                slot.index
                                                                                                === 2 ? qsTr(
                                                                                                            "Target amount") :
                                                                                                        qsTr("Target currency"))
                        onTextEdited: {
                            root.allSelected = false;
                            root.controller.edit(slot.index, text);
                        }
                        TapHandler {
                            onPressedChanged: if (pressed)
                                                  root.allSelected = false
                        }
                        onActiveFocusChanged: if (activeFocus && !slot.selected)
                                                  root.controller.activate(slot.index)
                        Keys.priority: Keys.BeforeItem
                        Keys.onPressed: event => {
                            if (preeditText.length) {
                                event.accepted = false;
                                return;
                            }
                            if (root.railExpanded) {
                                root.routedKey(event);
                                return;
                            }
                            const control = (event.modifiers & Qt.ControlModifier) !== 0;
                            if (control && event.key === Qt.Key_A) {
                                for (let i = 0; i < 4; ++i)
                                    fields.itemAt(i).input.deselect();
                                root.allSelected = true;
                                event.accepted = true;
                                return;
                            }
                            if (control && event.key === Qt.Key_C && root.allSelected) {
                                root.controller.copyText(root.completeText());
                                event.accepted = true;
                                return;
                            }
                            if (root.timeMode && root.allSelected && (event.key === Qt.Key_Backspace || event.key
                                                                      === Qt.Key_Delete)) {
                                root.controller.clearTemplate();
                                event.accepted = true;
                                return;
                            }
                            if (root.allSelected && event.key !== Qt.Key_Control && event.key
                                    !== Qt.Key_Shift) {

                                root.allSelected = false;
                                if (!control && (event.text.length || event.key === Qt.Key_Backspace))
                                    selectAll();
                            }
                            if (!control && (event.key === Qt.Key_Left || event.key === Qt.Key_Right)) {
                                root.controller.activate(slot.index + (event.key === Qt.Key_Left ? -1 : 1));
                                event.accepted = true;
                                return;
                            }
                            if (control && event.key === Qt.Key_C) {
                                if (selectionStart !== selectionEnd)
                                    copy();
                                else if (text.length && (slot.unit || slot.index
                                                         === root.controller.driverSide
                                                         || root.controller.answer)) {
                                    const position = cursorPosition;
                                    selectAll();
                                    copy();
                                    deselect();
                                    cursorPosition = position;
                                }
                                event.accepted = true;
                                return;
                            }
                            if (!control && event.key === Qt.Key_Backspace && !event.isAutoRepeat && !text.length
                                    && (!slot.unit || root.timeMode)) {
                                if (root.timeMode)
                                    root.controller.clearTemplate();
                                else
                                    root.exitRequested();
                                event.accepted = true;
                                return;
                            }
                            root.routedKey(event);
                        }
                        Keys.onReleased: event => root.releasedKey(event)
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: !slot.unit && !input.text.length && slot.index !== root.controller.driverSide
                        text: "…"
                        color: Appearance.colors.colOnSurfaceVariant
                        font.pixelSize: 20
                    }
                }
            }
        }
    }
}

import QtQuick
import qs.Services
import "../../Common/functions/SpotlightTemplates.js" as Templates

QtObject {
    id: root
    property string mode: ""
    property string templateKind: ""
    property string sourceZone: ""
    property string targetZone: "Asia/Tokyo"
    property string driverAmount: ""
    property bool seededTime: false
    property int driverSide: 0
    property int activeSlot: 0
    property string draft: ""
    property bool choosing: false
    property bool editingUnit: false
    property int selected: 0
    readonly property bool timeMode: mode === "time"
    readonly property bool active: timeMode
    readonly property bool choosingTemplate: active && !templateKind
    readonly property bool editing: active && !!templateKind
    readonly property bool nowTemplate: templateKind === "now"
    readonly property string expression: !editing ? "" : nowTemplate ? "now to " + targetZone :
                                                                       Templates.timeExpression(driverAmount,
                                                                                                driverSide
                                                                                                === 0 ? sourceZone :
                                                                                                        targetZone,
                                                                                                driverSide
                                                                                                === 0 ? targetZone :
                                                                                                        sourceZone)
    readonly property bool currentResult: editing && SpotlightToolService.tool === "time"
                                          && SpotlightToolService.query === expression
                                          && SpotlightToolService.canCopy
    readonly property string answer: currentResult && SpotlightToolService.result.target
                                     ? Templates.editableTime(SpotlightToolService.result.target.datetime) :
                                       ""
    readonly property var choices: {
        if (choosingTemplate)
            return [
                        {
                            text: qsTr("Now to a time zone"),
                            name: "",
                            kind: "now"
                        },
                        {
                            text: qsTr("Convert between two time zones"),
                            name: "",
                            kind: "pair"
                        }
                    ];
        if (!editing || !choosing)
            return [];
        const filter = draft.trim().toLowerCase();
        return (SpotlightToolService.catalogs.time || []).filter(item => !filter || (item.text + " "
                                                                                     + item.name).toLowerCase(
                                                                             ).includes(filter));
    }
    signal focusRequested(bool selectAll)
    signal templateSelectionRequested

    function reset() {
        templateKind = "";
        sourceZone = "";
        targetZone = "Asia/Tokyo";
        driverAmount = "";
        seededTime = false;
        driverSide = 0;
        activeSlot = 0;
        choosing = false;
        editingUnit = false;
        draft = "";
        selected = 0;
    }
    function clearTemplate() {
        reset();
        templateSelectionRequested();
    }
    function value(slot) {
        if (slot === 1)
            return nowTemplate || !sourceZone ? qsTr("Local time") : sourceZone;
        if (slot === 3)
            return targetZone;
        // Now is a display token; the pair keeps its captured local timestamp.
        if (slot === 0 && (nowTemplate || seededTime))
            return "Now";
        return !nowTemplate && slot === driverSide ? driverAmount : answer;
    }
    function editable(slot) {
        // A copied system tzfile may have no IANA name usable as a target.
        // Keep reverse editing read-only until an explicit source zone is known.
        return nowTemplate ? slot === 3 : slot !== 2 || !!sourceZone;
    }
    function activate(slot) {
        activeSlot = nowTemplate ? 3 : Math.max(0, Math.min(3, slot));
        choosing = activeSlot === 1 || activeSlot === 3;
        editingUnit = false;
        draft = "";
        selected = 0;
        focusRequested(true);
    }
    function edit(slot, value) {
        if (slot === 1 || slot === 3) {
            draft = value;
            editingUnit = true;
            choosing = true;
            selected = 0;
        } else if (!nowTemplate) {
            seededTime = false;
            driverSide = slot;
            driverAmount = value;
        }
    }
    function move(delta) {
        if (!choices.length)
            return false;
        selected = (selected + delta + choices.length) % choices.length;
        return true;
    }
    function choose(index) {
        const choice = choices[index];
        if (!choice)
            return false;
        if (choosingTemplate) {
            sourceZone = "";
            driverSide = 0;
            driverAmount = Qt.formatDateTime(new Date(), "yyyy-MM-dd hh:mm:ss");
            seededTime = true;
            templateKind = choice.kind;
            activate(nowTemplate ? 3 : 0);
        } else {
            if (activeSlot === 1)
                sourceZone = choice.text;
            else
                targetZone = choice.text;
            choosing = false;
            editingUnit = false;
            draft = "";
            focusRequested(true);
        }
        return true;
    }
    function dismiss() {
        if (!choosing)
            return false;
        choosing = false;
        editingUnit = false;
        draft = "";
        focusRequested(true);
        return true;
    }
    function copyText(value) {
        return SpotlightToolService.copyText(value);
    }
    function copyAnswer() {
        return currentResult && SpotlightToolService.copy();
    }
    onCurrentResultChanged: Qt.callLater(resolveLocalZone)
    function resolveLocalZone() {
        // An omitted source lets key-cli use the system's full transition rules.
        // Adopt its resolved IANA name for subsequent reverse conversions.
        if (currentResult && !nowTemplate && driverSide === 0 && !sourceZone) {
            const source = SpotlightToolService.result.source;
            if (source && source.zone && source.zone !== "system")
                sourceZone = source.zone;
        }
    }
    onChoicesChanged: selected = 0
}

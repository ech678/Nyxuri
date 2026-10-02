import QtQuick
import qs.Services
import "../../Common/functions/SpotlightCurrency.js" as Currency

QtObject {
    id: root
    property bool active: false
    property int activeSlot: 0
    property int driverSide: 0
    property string driverAmount: "1"
    property string sourceCurrency: "USD"
    property string targetCurrency: "EUR"
    property string draft: ""
    property bool choosing: false
    property bool editingUnit: false
    property int selected: 0
    readonly property string expression: active ? "1 " + sourceCurrency + " to " + targetCurrency : ""
    readonly property bool currencySlot: activeSlot === 1 || activeSlot === 3
    readonly property var choices: active && currencySlot && choosing ? Currency.candidates(
                                                                            SpotlightToolService.catalogs.currency
                                                                            || [], draft) : []
    readonly property string rate: active && SpotlightToolService.tool === "currency"
                                   && SpotlightToolService.query === expression
                                   && SpotlightToolService.canCopy && SpotlightToolService.result.base
                                   === sourceCurrency && SpotlightToolService.result.quote === targetCurrency
                                   && typeof SpotlightToolService.result.rate === "string"
                                   ? SpotlightToolService.result.rate : ""
    readonly property string answer: Currency.convert(driverAmount, rate, driverSide === 2)
    readonly property string amountError: driverAmount && !/^[+\-\.]$/.test(driverAmount) && !Currency.decimal(
                                              driverAmount) ? qsTr("Enter a valid amount") : ""
    signal focusRequested(bool selectAll)

    function reset(seed) {
        const initial = Currency.seed(seed);
        driverSide = 0;
        driverAmount = initial.amount;
        sourceCurrency = initial.from;
        targetCurrency = initial.to;
        activeSlot = 0;
        choosing = false;
        draft = "";
        editingUnit = false;
        selected = 0;
        focusRequested(true);
    }
    function editable(slot) {
        return true;
    }
    function value(slot) {
        if (slot === 1)
            return sourceCurrency;
        if (slot === 3)
            return targetCurrency;
        return slot === driverSide ? driverAmount : answer;
    }
    function activate(slot) {
        activeSlot = Math.max(0, Math.min(3, slot));
        choosing = currencySlot;
        draft = "";
        editingUnit = false;
        selected = 0;
        focusRequested(true);
    }
    function edit(slot, text) {
        if (slot === 1 || slot === 3) {
            draft = text;
            editingUnit = true;
            choosing = true;
            selected = 0;
        } else {
            driverSide = slot;
            driverAmount = text;
        }
    }
    function move(delta) {
        if (!choosing || !choices.length)
            return false;
        selected = (selected + delta + choices.length) % choices.length;
        return true;
    }
    function choose(index) {
        const candidate = choices[index];
        if (!candidate)
            return false;
        if (activeSlot === 1)
            sourceCurrency = candidate.text;
        else
            targetCurrency = candidate.text;
        choosing = false;
        draft = "";
        editingUnit = false;
        focusRequested(true);
        return true;
    }
    function dismiss() {
        if (!choosing)
            return false;
        choosing = false;
        draft = "";
        editingUnit = false;
        focusRequested(true);
        return true;
    }
    function copyText(value) {
        return SpotlightToolService.copyText(value);
    }
    function copyAnswer() {
        return !!answer && SpotlightToolService.copyText(answer);
    }
    onChoicesChanged: selected = 0
}

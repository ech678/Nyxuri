pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.Common
import "../Common/functions/SpotlightToolResponse.js" as ToolResponse

Singleton {
    id: root
    property bool active: false
    property string tool: ""
    property string query: ""
    property int instance: 0
    property int fold: -1
    property int generation: 0
    property var capabilities: null
    property bool capabilityKnown: false
    property var catalogs: ({})
    property var result: null
    property string state: "empty"
    property string error: ""
    property string feedback: ""
    property var request: null
    property bool exited: true
    property bool collected: true
    property int exitCode: 0
    property string output: ""
    property bool timedOut: false
    property int copyGeneration: -1
    readonly property var candidates: catalogs[tool] || []
    property var resultRequest: null
    readonly property bool canCopy: ToolResponse.copyable(result, resultRequest, active, state, generation,
                                                          instance)

    function errorMessage(value) {
        if (!value)
            return "";
        const messages = {
            dependency_missing: qsTr("qalc is unavailable"),
            invalid_expression: qsTr("Enter a supported expression"),
            calculation_failed: qsTr("The expression could not be calculated"),
            timeout: qsTr("Calculation timed out"),
            cancelled: qsTr("Calculation cancelled"),
            unsupported_currency: qsTr("Choose an ECB reference currency"),
            rate_unavailable: qsTr("Exchange rate unavailable; try again later"),
            nonexistent_time: qsTr("This local time does not exist"),
            timezone_unavailable: qsTr("Time zone data is unavailable for this zone"),
            invalid_time: qsTr("Enter a valid date and an unambiguous IANA time zone")
        };
        return messages[value.code] || qsTr("Tool request failed");
    }
    function invalidate() {
        generation++;
        result = null;
        resultRequest = null;
        error = "";
        feedback = "";
        debounce.stop();
        if (worker.running)
            worker.signal(15);
        if (!active) {
            state = "empty";
            return;
        }
        state = query.trim() ? "loading" : "empty";
        debounce.restart();
    }
    function parse(text, command) {
        try {
            const value = JSON.parse(text);
            return value && value.schemaVersion === 1 && value.command === command && typeof value.ok
                    === "boolean" && (value.ok ? value.error === null : value.error && typeof value.error.code
                                                 === "string") ? value : null;
        } catch (error) {
            return null;
        }
    }
    function start() {
        if (!active || worker.running || !exited || !collected)
            return;
        let action = !capabilityKnown ? "status" : !catalogs[tool] ? "catalog" : tool;
        if (capabilityKnown && (!capabilities || capabilities[tool] !== true)) {
            state = "unavailable";
            error = capabilities ? qsTr("This tool's dependency is unavailable") : qsTr(
                                       "Update key-cli to enable this tool");
            return;
        }
        if (action === tool && !query.trim()) {
            state = "empty";
            return;
        }
        request = {
            generation: generation,
            instance: instance,
            tool: tool,
            action: action
        };
        const argv = [Paths.stableKey, "tool", action];
        if (action === "catalog")
            argv.push(tool);
        else if (action !== "status") {
            argv.push("--expression=" + query);
            if (tool === "time" && fold >= 0)
                argv.push("--fold", String(fold));
        }
        exited = false;
        collected = false;
        output = "";
        timedOut = false;
        worker.command = argv;
        worker.running = true;
        deadline.restart();
    }
    function finish() {
        if (!exited || !collected || !request)
            return;
        deadline.stop();
        const pending = request;
        request = null;
        const value = parse(output, "tool." + pending.action);
        const current = active && ToolResponse.current(pending, generation, instance);
        if (pending.action === "status") {
            if (value && value.ok && value.capabilities) {
                capabilityKnown = true;
                capabilities = value.capabilities;
            } else if (current) {
                capabilityKnown = true;
                capabilities = null;
            }
        } else if (pending.action === "catalog" && value && value.ok && value.tool === pending.tool
                   && Array.isArray(value.candidates)) {
            catalogs = Object.assign({}, catalogs, {
                                         [pending.tool]: value.candidates.filter(candidate
                                                                                 => typeof candidate.text
                                                                                    === "string"
                                                                                    && typeof candidate.name
                                                                                    === "string")
                                     });
        } else if (current) {
            if (!value || timedOut) {
                state = "error";
                error = timedOut ? qsTr("Tool request timed out") : qsTr("The tool returned invalid data");
                return;
            }
            result = value;
            resultRequest = pending;
            state = ["empty", "incomplete", "valid", "ambiguous", "error", "unavailable"].includes(value.state)
                    ? value.state : "error";
            if (state === "valid" && (!value.ok || exitCode !== 0 || typeof value.answer !== "string")) {
                state = "error";
                result = null;
            }
            error = errorMessage(value.error);
            return;
        }
        if (current && pending.action === "catalog" && !catalogs[pending.tool]) {
            state = "error";
            error = qsTr("The tool returned invalid data");
            return;
        }
        if (active && !debounce.running)
            Qt.callLater(root.start);
    }
    function confirmFold(value) {
        if (state !== "ambiguous" || !result || !result.candidates.some(candidate => candidate.fold
                                                                                     === value))
            return;
        fold = value;
    }
    function copy() {
        if (!canCopy || copier.running)
            return false;
        return copyText(result.answer);
    }
    function copyText(value) {
        if (!active || !value || copier.running)
            return false;
        copyGeneration = generation;
        copier.command = ["wl-copy", "--", value];
        copier.running = true;
        return true;
    }
    onActiveChanged: invalidate()
    onToolChanged: {
        fold = -1;
        invalidate();
    }
    onQueryChanged: {
        fold = -1;
        invalidate();
    }
    onInstanceChanged: invalidate()
    onFoldChanged: invalidate()

    Timer {
        id: debounce
        interval: 160
        onTriggered: root.start()
    }
    Timer {
        id: deadline
        interval: 12000
        onTriggered: {
            root.timedOut = true;
            if (worker.running)
                worker.signal(15);
        }
    }
    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                root.output = text;
                root.collected = true;
                root.finish();
            }
        }
        onExited: code => {
            root.exitCode = code;
            root.exited = true;
            root.finish();
        }
    }
    Process {
        id: copier
        onExited: code => {
            if (root.active && root.copyGeneration === root.generation)
                root.feedback = code === 0 ? qsTr("Copied") : qsTr("Could not copy the result");
        }
    }
}

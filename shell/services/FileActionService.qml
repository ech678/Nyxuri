pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons

Singleton {
    id: root
    signal finished(string action, string path, var response)

    function run(action, path) {
        if ((action !== "open" && action !== "reveal") || typeof path !== "string" || !path.startsWith("/"))
            return;
        operation.createObject(root, {
                                   action,
                                   filePath: path
                               });
    }

    Component {
        id: operation
        Process {
            id: request
            required property string action
            required property string filePath
            command: [Paths.stableKey, "file", action, filePath, "--format", "json"]
            running: true
            property bool settled: false
            stdout: StdioCollector {
                id: output
            }
            function complete(response) {
                if (request.settled)
                    return;
                request.settled = true;
                root.finished(request.action, request.filePath, response);
                request.destroy();
            }
            onRunningChanged: {
                if (request.running || request.settled)
                    return;
                Qt.callLater(() => {
                    if (!request.settled)
                        request.complete(null);
                });
            }
            onExited: exitCode => {
                let response = null;
                try {
                    response = JSON.parse(output.text);
                    if (!response || response.schemaVersion !== 1 || response.command !== "file." + action
                            || typeof response.ok !== "boolean" || (exitCode !== 0 && response.ok) || (response.ok && (
                                                                                                           response.error
                                                                                                           !== null
                                                                                                           || typeof response.fileExists
                                                                                                           !== "boolean"
                                                                                                           || ["open",
                                                                                                               "reveal", "directory"].indexOf(
                                                                                                               response.mode)
                                                                                                           === -1)))
                        response = null;
                } catch (error) {}
                request.complete(response);
            }
        }
    }

    Component.onDestruction: {
        for (let i = 0; i < root.children.length; ++i) {
            const child = root.children[i];
            if (child && child.running !== undefined)
                child.running = false;
        }
    }
}

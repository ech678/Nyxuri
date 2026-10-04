pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.shared.theme
import qs.app
import qs.shared.i18n

Singleton {
    id: root

    readonly property string avatarPath: Paths.profileAvatar
    readonly property string avatarUrl: Paths.fileUrl(avatarPath) + "?revision=" + revision
    property int revision: 0
    property bool busy: false
    property string pendingSource: ""

    signal updateFinished(bool success, string message)

    function setAvatar(path) {
        const source = String(path || "");
        if (source === "" || busy) {
            if (source === "")
                updateFinished(false, I18n.tr("No valid avatar file selected"));
            return;
        }

        pendingSource = source;
        busy = true;
        copyProcess.command = ["cp", "--", source, avatarPath];
        copyProcess.running = true;
    }

    Process {
        id: copyProcess

        onExited: exitCode => {
            root.busy = false;
            if (exitCode === 0) {
                root.revision += 1;
                root.updateFinished(true, I18n.tr("Avatar updated"));
                ActionGateway.execute(["notify-send", "-a", "quickshell", "-u", "low", I18n.tr(
                                           "Avatar updated"), root.pendingSource], "avatar:update-success");
            } else {
                root.updateFinished(false, I18n.tr("Could not update avatar"));
                ActionGateway.execute(["notify-send", "-a", "quickshell", "-u", "critical", I18n.tr(
                                           "Avatar update failed"), root.pendingSource],
                                      "avatar:update-failed");
            }
            root.pendingSource = "";
        }
    }

    Component.onDestruction: {
        if (copyProcess)
            copyProcess.running = false;
        root.busy = false;
        root.pendingSource = "";
    }
}

pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import qs.shared.i18n

// Keystone color-picker action owner. Probes hyprpicker once, launches it via
// the Action Gateway, and reports a missing dependency instead of failing
// silently (execDetached cannot report a spawn failure).
Singleton {
    id: root

    property bool probeFinished: false
    property bool available: false

    function launch() {
        if (!root.probeFinished)
            return false;
        if (!root.available) {
            ActionGateway.execute(["notify-send", "-a", "Nyxuri Shell", "-u", "critical", I18n.tr(
                                       "Color picker unavailable"), I18n.tr("hyprpicker is missing")],
                                  "keystone:color-picker-degraded");
            return false;
        }
        return ActionGateway.execute(["hyprpicker", "-a"], "keystone:color-picker");
    }

    Process {
        id: probe

        // Constant argv through the shared probe helper; PATH lookup without
        // an inline shell string (LIFE004).
        command: ["bash", Paths.scriptPath("theme", "probe-tool.sh"), "hyprpicker"]
        onExited: exitCode => {
            root.available = exitCode === 0;
            root.probeFinished = true;
        }
    }

    Component.onCompleted: probe.running = true

    Component.onDestruction: {
        if (probe)
            probe.running = false;
    }
}

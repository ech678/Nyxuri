import QtQuick
import Quickshell
import StartupProbe

ShellRoot {
    id: root

    property int phase: 0
    property int dedupeRuns: 0
    property int failureRuns: 0
    property int retryRuns: 0

    function fail(reason) {
        console.error("STARTUP_PROBE_FAIL", reason);
        Qt.exit(1);
    }

    Timer {
        interval: 10
        repeat: true
        running: true

        onTriggered: {
            if (root.phase === 0) {
                const first = ShellStartupService.scheduleBackground("probe-dedupe", () => root.dedupeRuns++);
                const duplicate = ShellStartupService.scheduleBackground("probe-dedupe", ()
                                                                         => root.dedupeRuns++);
                if (!first || duplicate) {
                    root.fail("duplicate scheduling result was incorrect");
                    return;
                }
                root.phase = 1;
                return;
            }

            if (root.phase === 1 && root.dedupeRuns === 1) {
                if (ShellStartupService.scheduleBackground("probe-dedupe", () => root.dedupeRuns++)) {
                    root.fail("completed task was scheduled again");
                    return;
                }
                const accepted = ShellStartupService.scheduleBackground("probe-retry", () => {
                    root.failureRuns++;
                    throw new Error("expected startup probe failure");
                });
                if (!accepted) {
                    root.fail("initial failing task was rejected");
                    return;
                }
                root.phase = 2;
                return;
            }

            if (root.phase === 2 && ShellStartupService.backgroundMetrics.some(metric => metric.name
                                                                                         === "probe-retry"
                                                                                         && metric.error
                                                                                         !== "")) {
                if (root.failureRuns !== 1 || !ShellStartupService.scheduleBackground("probe-retry", ()
                                                                                      => root.retryRuns++)) {
                    root.fail("failed task could not be explicitly retried");
                    return;
                }
                root.phase = 3;
                return;
            }

            if (root.phase === 3 && root.retryRuns === 1) {
                if (root.dedupeRuns !== 1 || root.failureRuns !== 1 || ShellStartupService.scheduleBackground(
                            "probe-retry", () => root.retryRuns++)) {
                    root.fail("retry completion or duplicate guard was incorrect");
                    return;
                }
                console.log("STARTUP_PROBE_PASS duplicate_once=1 failed_retry=1");
                Qt.quit();
            }
        }
    }
}

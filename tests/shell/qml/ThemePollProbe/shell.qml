import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import qs.services

ShellRoot {
    id: root

    property int phase: 0
    property int observations: 0
    property double startedAt: Date.now()
    property double writtenAt: 0
    property bool startPreferences: false
    property bool late: Quickshell.env("THEME_POLL_LATE") === "1"
    property bool writeProbe: Quickshell.env("THEME_POLL_WRITE") === "1"

    function fail(reason) {
        console.error("THEME_POLL_PROBE_FAIL", reason);
        Qt.exit(1);
    }

    // Reading this fixture also proves that the real preferences FileView
    // has completed before the optional system poll is allowed to start.
    Component.onCompleted: {
        if (root.late) {
            ShellStartupService.recordFirstFrame();
            ShellStartupService.recordIpcReady();
            ShellStartupService.scheduleBackground("ui-theme-poll", () => UiPreferences.startSystemThemePolling());
        }
        root.startPreferences = true;
        console.log("THEME_POLL_INITIAL", UiPreferences.darkMode,
                    PersonalizationConfig.themeMode);
    }

    FileView {
        id: calls
        path: Quickshell.env("THEME_POLL_CALLS")
        printErrors: false
        blockLoading: true
    }

    Connections {
        target: root.startPreferences ? UiPreferences : null

        function onSystemThemeModeObserved(mode) {
            root.observations++;
            console.log("THEME_POLL_OBSERVED", mode, root.observations,
                        Date.now() - root.startedAt);
            if (root.observations === 1) {
                if (mode !== "light" || UiPreferences.darkMode)
                    root.fail("initial system observation changed the saved light palette");
                else if (root.late) {
                    console.log("THEME_POLL_PROBE_PASS late_ready=1");
                    Qt.quit();
                } else if (root.writeProbe) {
                    root.writtenAt = Date.now();
                    UiPreferences.setDarkMode(true);
                    root.phase = 3;
                } else {
                    changeSetting.running = true;
                    root.phase = 3;
                }
            } else if (root.observations === 2) {
                if (mode !== "dark" || !UiPreferences.darkMode)
                    root.fail("periodic poll did not observe the external dark setting");
                else if (root.writeProbe && (Date.now() - root.writtenAt < 300
                                            || UiPreferences.systemThemeLastError !== ""))
                    root.fail("theme write failed or skipped the 350ms debounce");
                else {
                    const tasks = ShellStartupService.backgroundMetrics.filter(
                        task => task.name === "ui-theme-poll");
                    if (tasks.length !== 1 || tasks[0].error !== "")
                        root.fail("poll startup task did not execute exactly once");
                    else {
                        console.log("THEME_POLL_PROBE_PASS gate=1 scheduled_once=1",
                                    root.writeProbe ? "write_debounce=1" : "external_change=1");
                        Qt.quit();
                    }
                }
            } else {
                root.fail("unexpected extra initial poll");
            }
        }
    }

    Process {
        id: changeSetting
        command: ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark"]
    }

    Timer {
        interval: 50
        repeat: true
        running: !root.late
        onTriggered: {
            calls.reload();
            if (root.phase === 0 && Date.now() - root.startedAt >= 300) {
                if (calls.text().trim() !== "" || root.observations !== 0)
                    return root.fail("system poll ran before FIRST_FRAME");
                if (!UiPreferences.preferencesReady || UiPreferences.spotlightSearchEngine !== "duckduckgo"
                        || UiPreferences.darkMode || PersonalizationConfig.themeMode !== "light")
                    return root.fail("mandatory preferences or initial palette not ready before gate");
                console.log("THEME_POLL_PRE_GATE preferences_ready=1 polls=0 palette=light");
                ShellStartupService.recordFirstFrame();
                root.phase = 1;
            } else if (root.phase === 1 && Date.now() - root.startedAt >= 600) {
                if (calls.text().trim() !== "" || root.observations !== 0)
                    return root.fail("system poll ran before IPC_READY");
                console.log("THEME_POLL_FIRST_FRAME polls=0");
                ShellStartupService.recordIpcReady();
                ShellStartupService.recordCoreReady();
                ShellStartupService.scheduleBackground("ui-theme-poll", () => UiPreferences.startSystemThemePolling());
                root.phase = 2;
            }
        }
    }

    Timer {
        interval: 65000
        running: true
        onTriggered: root.fail("timed out waiting for system theme observation")
    }
}

// Fork & Trim: iNiR services/DateTime.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri: the upstream singleton read `Config.options.time.*`
// (a key tree this tree does not carry) and used `Translation.locale` (the
// Nyxuri Translation singleton exposes no locale). Time formatting now comes
// from UiPreferences, which owns the 12/24-hour switch and already formats
// bar clocks; dates fall back to the shell locale.

pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons
import qs.services

/**
 * Date and time strings for the bar clock, island idle face and clock popup.
 */
Singleton {
    id: root

    SystemClock {
        id: clock

        precision: GlobalStates.screenLocked ? SystemClock.Seconds : SystemClock.Minutes
    }

    readonly property string time: UiPreferences.shortTime(clock.date)
    // Like time, but keeps :ss when the shell is locked — bar clocks stay
    // minute-precision in normal use.
    readonly property string timeDisplay: GlobalStates.screenLocked ? Qt.formatDateTime(clock.date, UiPreferences.useTwelveHourClock ? "hh:mm:ss AP" : "HH:mm:ss") : root.time
    readonly property string shortDate: Qt.formatDateTime(clock.date, "dd/MM")
    readonly property string date: Qt.formatDateTime(clock.date, "dddd, dd/MM")
    readonly property string longDate: root.date
    readonly property string collapsedCalendarFormat: Qt.formatDateTime(clock.date, "dd MMMM yyyy")
    property string uptime: "0h, 0m"

    Timer {
        id: uptimeTimer

        triggeredOnStart: true
        // Uptime doesn't change fast - 60s updates are sufficient and reduce I/O
        interval: 60000
        running: true
        repeat: true
        onTriggered: fileUptime.reload()
    }

    Component.onDestruction: uptimeTimer.stop()

    FileView {
        id: fileUptime

        path: "/proc/uptime"
        // reload() reads in the background: parsing right after it read nothing,
        // so every start said 0 m for a minute.
        onLoaded: {
            const uptimeSeconds = Number(fileUptime.text().split(" ")[0] ?? 0);

            // Convert seconds to days, hours, and minutes
            const days = Math.floor(uptimeSeconds / 86400);
            const hours = Math.floor((uptimeSeconds % 86400) / 3600);
            const minutes = Math.floor((uptimeSeconds % 3600) / 60);

            let formatted = "";
            if (days > 0)
                formatted += `${days}d`;
            if (hours > 0)
                formatted += `${formatted ? ", " : ""}${hours}h`;
            if (minutes > 0 || !formatted)
                formatted += `${formatted ? ", " : ""}${minutes}m`;
            root.uptime = formatted;
        }
    }
}

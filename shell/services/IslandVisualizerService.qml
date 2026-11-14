pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.services

// Lazy cava feed for the island's media face (B3-1). The upstream island owned
// a permanently running cava process through `GlobalStates.visualizerPoints`;
// the tree keeps cava as an on-demand consumer instead: the island acquires a
// lease only while its media face is actually visible and the track is
// playing, releasing it stops the process and clears points.
//
// Lease mechanics mirror MediaService.acquirePositionTracking — the same shape
// the bar already relies on, so the island is not a special case.
Singleton {
    id: root

    property var points: []
    property bool cavaAvailable: false

    readonly property bool live: root.subscribers > 0 && root.activePlayer !== null && root.activePlayer.isPlaying

    readonly property var activePlayer: MediaService.active

    property int subscribers: 0

    function acquire() {
        root.subscribers += 1;
        root.sync();
    }

    function release() {
        root.subscribers = Math.max(0, root.subscribers - 1);
        root.sync();
    }

    function sync() {
        cavaProc.running = root.live;
    }

    onLiveChanged: root.sync()

    Component.onCompleted: root.sync()

    Component.onDestruction: {
        cavaProc.running = false;
        root.points = [];
    }

    Process {
        id: cavaProc

        command: ["cava", "-p", Paths.scriptPath("media", "cava_raw_output_config.txt")]

        onExited: code => root.cavaAvailable = code === 0
        onRunningChanged: {
            root.cavaAvailable = running;
            if (!running)
                root.points = [];
        }

        stdout: SplitParser {
            onRead: data => root.points = data.split(";").map(p => parseFloat(p.trim())).filter(p => !isNaN(p))
        }
    }
}

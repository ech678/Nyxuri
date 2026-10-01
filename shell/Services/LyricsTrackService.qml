pragma Singleton

import QtQuick
import Quickshell
import Clavis.Lyrics

Singleton {
    id: root

    readonly property var player: MediaManager.active

    function playerIdentity(playerObject) {
        if (!playerObject)
            return "";

        const service = playerObject.dbusName || playerObject.busName
            || playerObject.identity || "";
        const uniqueId = playerObject.uniqueId === undefined
            ? "" : String(playerObject.uniqueId);
        return String(service) + ":" + uniqueId;
    }

    function sync() {
        const current = MediaManager.active;
        if (!current || !String(current.trackTitle || "").trim()) {
            Lyrics.clearTrack();
            return;
        }

        Lyrics.setTrack(
            String(current.trackArtist || ""),
            String(current.trackTitle || ""),
            String(current.trackAlbum || ""),
            Number(current.length) > 0 ? Number(current.length) : 0,
            root.playerIdentity(current)
        );
    }

    function initialize() {
        root.sync();
    }

    Component.onCompleted: root.sync()

    Connections {
        target: MediaManager

        function onActiveChanged() { root.sync(); }
    }

    Connections {
        target: root.player
        ignoreUnknownSignals: true

        function onTrackTitleChanged() { root.sync(); }
        function onTrackArtistChanged() { root.sync(); }
        function onTrackAlbumChanged() { root.sync(); }
        function onLengthChanged() { root.sync(); }
        function onUniqueIdChanged() { root.sync(); }
        function onIdentityChanged() { root.sync(); }
    }
}

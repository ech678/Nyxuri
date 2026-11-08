pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Services.Mpris
import qs.services

Singleton {
    id: root

    readonly property var activePlayer: MediaService.active ?? MediaService.primaryPlayer ?? null
    readonly property var players: MediaService.list

    function artUrlOf(player) {
        return player?.trackArtUrl ?? "";
    }

    function titleOf(player) {
        return player?.trackTitle ?? "";
    }

    function artistOf(player) {
        return player?.trackArtist ?? "";
    }

    function lengthOf(player) {
        return player?.length ?? 0;
    }

    function positionOf(player) {
        return player?.position ?? 0;
    }

    function previousForPlayer(player) {
        if (player && player.canGoPrevious) player.previous();
    }

    function nextForPlayer(player) {
        if (player && player.canGoNext) player.next();
    }

    function playPauseForPlayer(player) {
        if (player && player.canControl) player.playPause();
    }
}

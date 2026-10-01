import QtQuick
import Clavis.Lyrics

Item {
    id: root

    function clearTrack() {
        Lyrics.clearTrack();
    }

    function setTrack(artist, title, album, length, id) {
        Lyrics.setTrack(artist, title, album, length, id);
    }
}

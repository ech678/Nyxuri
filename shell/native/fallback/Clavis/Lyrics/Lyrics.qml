pragma Singleton
import QtQuick

QtObject {
    id: root

    readonly property string status: "unavailable"
    readonly property bool loading: false
    readonly property bool hasLyrics: false
    readonly property bool hasSynchronizedLyrics: false
    readonly property var lyrics: []
    readonly property var candidates: []
    readonly property var selectedCandidate: ({})
    readonly property string provider: ""
    readonly property string error: ""
    property double offsetMs: 0
    readonly property string trackArtist: ""
    readonly property string trackTitle: ""
    readonly property string trackAlbum: ""
    readonly property double trackDuration: 0
    readonly property string trackPlayerId: ""

    function clearTrack() {}
    function setTrack(artist, title, album, length, id) {}
    function indexForTime(pos) { return -1; }
}

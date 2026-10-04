pragma Singleton

import QtQuick
import Quickshell
import qs.app.services
import "lyrics/LyricsParser.js" as LyricsParser
import qs.shared.i18n

// Drives lyric fetching for whatever MediaService currently has playing.
//
// Layering: this file owns *state* (what is playing, which fetch is current,
// what we last received). LyricsBackend owns *transport* (spawning the
// fetcher script and turning its stdout into a signal). The split matters
// because the transport is the part that can hang on a network call, and
// keeping it in a separate Loader means a stuck fetch is visible in isolation
// rather than tangled into the state machine below.
//
// Fetch lifecycle per track change:
//   debounce -> generation++ -> backend.fetch(...) -> onLyrics(...)
// The generation counter is the guard against out-of-order replies: a slow
// fetch for the previous track must not overwrite the new track's lyrics.
Singleton {
    id: root

    // --- Track identity -----------------------------------------------------

    readonly property var player: MediaService.active
    readonly property string title: player && player.trackTitle ? String(player.trackTitle) : ""
    readonly property string artist: player && player.trackArtist ? String(player.trackArtist) : ""
    // MPRIS reports microseconds; the fetcher and every timestamp in this
    // service work in seconds.
    readonly property real durationSeconds: {
        const micros = player && player.length ? Number(player.length) : 0;
        return micros > 0 ? micros / 1000000 : 0;
    }

    // --- Fetch state --------------------------------------------------------

    // "idle" | "loading" | "ready" | "empty" | "error"
    property string state: "idle"
    property string source: "none"
    property bool matched: false
    property string errorMessage: ""

    // Raw lyric text as returned by the backend, plus the backend's own
    // alignment of translated lines. Parsing happens below so consumers never
    // touch either of these directly.
    property string _rawLyrics: ""
    property var _translationLines: []

    // Parsed output. Rebuilt only when the underlying text changes, because
    // parsing is O(lines) and the UI re-reads this on every position tick.
    property var lines: []

    // Bumped on every track change so a late reply can be discarded.
    property int _generation: 0
    property int _pendingGeneration: -1

    // User-adjustable timing trim, in milliseconds. Positive shifts lyrics
    // later. Exposed through the settings page.
    //
    // Backed by PersonalizationConfig so the value survives a restart and is
    // validated on load (a hand-edited config.json cannot push it out of
    // range). There is no separate local copy: two sources of truth here would
    // mean the settings page and the IPC `offset` command could disagree.
    property int offsetMs: PersonalizationConfig.lyricOffsetMs

    onOffsetMsChanged: {
        if (PersonalizationConfig.lyricOffsetMs !== root.offsetMs)
            PersonalizationConfig.setLyricOffsetMs(root.offsetMs);
    }

    // Locally interpolated playback clock, in seconds, pre-offset. Advanced by
    // the 20Hz timer and corrected against MPRIS by the 350ms timer. Kept
    // separate from MediaService.currentPosition so this service can run a
    // finer clock without changing what every other media surface consumes.
    property real _interpolatedSeconds: 0

    readonly property bool hasLyrics: lines.length > 0
    readonly property bool available: backendLoader.status === Loader.Ready && backendLoader.item !== null

    // Gates both position timers. Reading isPlaying through the service keeps
    // them from running against a paused or absent player.
    readonly property bool _isPlaying: {
        const player = MediaService.active;
        return player !== null && player.isPlaying === true;
    }

    // Snaps the interpolated clock to the player's real position. Called on
    // track change and on completion, where easing in from a stale value would
    // briefly show the wrong lyric.
    function _resetClock() {
        const player = MediaService.active;
        root._interpolatedSeconds = player ? Math.max(0, Number(player.position) || 0) : 0;
    }

    // Exposed as a named property rather than reaching through
    // `backendLoader.item` at each call site: qmllint resolves the member on a
    // typed property but not on Loader.item, which is untyped by design.
    readonly property var backend: backendLoader.item ? backendLoader.item : null

    // Index of the line covering the current playback position, or -1.
    //
    // Forward-only, and deliberately not a pure function of positionMs: real
    // KRC timelines are mostly gaps, so a stateless lookup flips between -1 and
    // the surrounding lines and the card blanks through the whole song. This
    // holds the last index and advances only when the next line has started.
    // `_lineIndex` is the tracked cursor; it re-syncs on track change and on
    // backwards seeks (see advanceLineIndex).
    property int _lineIndex: -1

    readonly property int currentLineIndex: root._lineIndex

    function _syncLineIndex() {
        const lines = root.lines;
        root._lineIndex = (lines && lines.length > 0) ? LyricsParser.advanceLineIndex(lines, root.positionMs,
                                                                                      root._lineIndex) : -1;
    }

    onPositionMsChanged: root._syncLineIndex()

    onLinesChanged: {
        root._lineIndex = -1;
        root._syncLineIndex();
    }

    // Playback position in ms, offset already applied. Rounded to avoid
    // re-evaluating the bindings above on sub-millisecond noise.
    //
    // Driven by `_interpolatedSeconds` rather than MediaService.currentPosition
    // directly. That shared tick runs at 250ms, which is fine for a progress
    // bar but not for word-level highlighting: KRC words are often 300-500ms,
    // so a 4Hz source skips words entirely and the sweep looks like a stutter.
    // The interpolation timers below advance this at 20Hz and re-sync.
    readonly property real positionMs: Math.round((root._interpolatedSeconds + root.offsetMs / 1000) * 1000)

    function _clear() {
        root._rawLyrics = "";
        root._translationLines = [];
        root.lines = [];
        root.source = "none";
        root.matched = false;
        root.errorMessage = "";
    }

    function _onTrackChanged() {
        root._generation += 1;
        if (root.title === "") {
            root.state = "idle";
            root._clear();
            return;
        }
        root.state = "loading";
        root._clear();
        trackDebounce.restart();
    }

    function _startFetch() {
        if (!root.available || root.title === "")
            return;
        const generation = root._generation;
        root._pendingGeneration = generation;
        root.backend.fetch(root.title, root.artist, root.durationSeconds, generation);
    }

    // Called by the backend once the fetcher exits.
    function _onLyrics(generation, payload) {
        // A reply for a superseded track is dropped. This is the only place
        // that can happen, so it is the only place that checks.
        if (generation !== root._generation)
            return;

        root._pendingGeneration = -1;
        if (!payload || typeof payload !== "object") {
            root.state = "error";
            root.errorMessage = I18n.tr("Lyric fetch returned no data");
            return;
        }

        const text = String(payload.lyrics || "");
        if (text.trim() === "") {
            root.state = "empty";
            return;
        }

        root.source = String(payload.source || "none");
        root.matched = !!payload.matched;
        root._rawLyrics = text;
        root._translationLines = Array.isArray(payload.translationLines) ? payload.translationLines : [];
        root.lines = LyricsParser.parse(text, root._translationLines);
        root.state = root.lines.length > 0 ? "ready" : "empty";
    }

    function _onFetchError(generation, message) {
        if (generation !== root._generation)
            return;
        root._pendingGeneration = -1;
        root.state = "error";
        root.errorMessage = message;
    }

    // Manual refetch, used by the settings page's refresh action. Bypasses the
    // cache so a wrong or stale entry can be shaken off.
    function refresh() {
        if (!root.available || root.title === "")
            return;
        const generation = root._generation;
        root._pendingGeneration = generation;
        root.state = "loading";
        root.backend.fetch(root.title, root.artist, root.durationSeconds, generation, true);
    }

    function setOffsetMs(value) {
        const next = Math.round(Number(value) || 0);
        if (next !== root.offsetMs)
            root.offsetMs = next;
    }

    // A track change also resets the clock: a new song starts near zero, and
    // easing away from the previous track's position would show the wrong line
    // for the first fraction of a second.
    onTitleChanged: {
        root._onTrackChanged();
        root._resetClock();
    }
    onArtistChanged: root._onTrackChanged()

    Component.onCompleted: {
        root._onTrackChanged();
        root._resetClock();
    }

    // Collapses the burst of metadata updates a track start produces. Media
    // players emit title, artist and length as separate MPRIS properties, so
    // fetching on each one would triple the request count per song.
    Timer {
        id: trackDebounce

        interval: 250
        repeat: false
        onTriggered: root._startFetch()
    }

    // Re-sync the interpolated clock against the authoritative MPRIS position.
    //
    // Runs at 350ms: frequent enough that the local clock never drifts far,
    // slow enough that the D-Bus round trip stays cheap. Only the lyric view
    // needs this precision, which is why it lives here rather than in
    // MediaService where every surface would pay for it.
    Timer {
        id: positionSyncTimer

        interval: 350
        repeat: true
        running: root._isPlaying

        onTriggered: {
            const player = MediaService.active;
            if (!player)
                return;
            const real = Math.max(0, Number(player.position) || 0);
            if (real <= 0)
                return;
            const drift = real - root._interpolatedSeconds;
            // Small drift is eased in so the sweep does not visibly jump;
            // anything larger is a seek or a stall and must snap.
            if (Math.abs(drift) > 0.5)
                root._interpolatedSeconds = real;
            else if (Math.abs(drift) > 0.05)
                root._interpolatedSeconds += drift * 0.4;
        }
    }

    // Local interpolation, 20Hz. This is what makes per-word colouring look
    // continuous: the sync timer above only corrects it three times a second,
    // which would read as visible steps between words.
    Timer {
        id: interpolationTimer

        interval: 50
        repeat: true
        running: root._isPlaying && root.hasLyrics

        onTriggered: root._interpolatedSeconds += interval / 1000
    }

    // Required by the lifecycle audit (LIFE002). Both position timers repeat,
    // so they must be stopped explicitly on teardown rather than left to the
    // QML engine's destruction order.
    Component.onDestruction: {
        trackDebounce.stop();
        positionSyncTimer.stop();
        interpolationTimer.stop();
    }

    Loader {
        id: backendLoader

        source: "lyrics/LyricsBackend.qml"

        // Signals are wired here rather than declared inside the loaded file so
        // LyricsService stays the single owner of fetch state. A backend that
        // is not ready simply drops the connection; nothing is fetched before
        // LyricsService decides to.
        Connections {
            target: backendLoader.item
            ignoreUnknownSignals: true

            function onLyrics(generation, payload) {
                root._onLyrics(generation, payload);
            }

            function onFetchFailed(generation, message) {
                root._onFetchError(generation, message);
            }
        }
    }
}

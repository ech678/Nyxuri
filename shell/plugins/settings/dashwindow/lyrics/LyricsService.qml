import QtQuick
import Quickshell
import qs.services
import "LyricsParser.js" as LyricsParser
import qs.commons.i18n

Item {
    id: root

    property bool active: false

    onActiveChanged: {
        if (root.active) {
            root._onTrackChanged();
            root._resetClock();
        } else {
            trackDebounce.stop();
            positionSyncTimer.stop();
            tickTimer.stop();
            if (backend && typeof backend.cancel === "function")
                backend.cancel();
        }
    }

    // --- Track identity -----------------------------------------------------

    readonly property var player: MediaService.active
    readonly property string title: player && player.trackTitle ? String(player.trackTitle) : ""
    readonly property string artist: player && player.trackArtist ? String(player.trackArtist) : ""
    // MPRIS reports microseconds; the fetcher and every timestamp in this
    // service work in seconds.
    // MPRIS reports track length in microseconds, but Quickshell's MprisPlayer
    // hands it over already divided by 1e6 for some backends and raw for
    // others. A real track is minutes long, so anything under ~100k is already
    // in seconds and anything above is microseconds — no track is 27 hours.
    readonly property real durationSeconds: {
        const raw = player && player.length ? Number(player.length) : 0;
        if (raw <= 0)
            return 0;
        return raw > 100000 ? raw / 1000000 : raw;
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

    // Playback clock as an anchor plus wall-clock extrapolation, following
    // dux-shell's LyricsController. Accumulating a delta every tick drifts: each
    // tick carries its own scheduling error and nothing ever cancels it, so the
    // lyric creeps ahead of the audio over a few minutes. An anchor is re-set
    // only on the events that actually move the clock — play/pause, seek, track
    // change — and the position is recomputed from Date.now() in between.
    property real _anchorSeconds: 0
    property double _anchorWallMs: 0
    property bool _anchorPlaying: false

    // Re-seat the anchor on the player's reported position.
    function _anchorTo(positionSeconds) {
        root._anchorSeconds = Math.max(0, Number(positionSeconds) || 0);
        root._anchorWallMs = Date.now();
        root._anchorPlaying = root._isPlaying;
    }

    // Clock reading, pre-offset, in seconds.
    readonly property real _clockSeconds: {
        if (!root._anchorPlaying || root._anchorWallMs <= 0)
            return root._anchorSeconds;
        return root._anchorSeconds + (Date.now() - root._anchorWallMs) / 1000;
    }

    readonly property bool hasLyrics: lines.length > 0
    readonly property bool available: backendLoader.status === Loader.Ready && backendLoader.item !== null

    // Gates both position timers. Reading isPlaying through the service keeps
    // them from running against a paused or absent player.
    readonly property bool _isPlaying: {
        const player = MediaService.active;
        return player !== null && player.isPlaying === true;
    }

    // Pausing must freeze the clock at the position it reached, and resuming
    // must restart from the player's position rather than from wherever the
    // wall-clock extrapolation had drifted to.
    on_IsPlayingChanged: root._resetClock()

    // Snap the anchor to the player's real position. Called on track change and
    // on completion, where easing in from a stale value would briefly show the
    // wrong lyric.
    function _resetClock() {
        const player = MediaService.active;
        root._anchorTo(player ? Number(player.position) || 0 : 0);
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

    // Playback position in ms, offset already applied.
    //
    // Derived from the anchored clock rather than MediaService.currentPosition,
    // whose shared tick runs at 250ms — fine for a progress bar, too coarse for
    // word highlighting, where KRC words are often 300-500ms. Re-reading the
    // anchor is free, so the tick timer only exists to invalidate this binding.
    readonly property real positionMs: {
        // Reading the revision is what makes this re-evaluate; the clock itself
        // is a pure function of the anchor and the wall clock.
        const _ = tickTimer.revision;
        return Math.round((root._clockSeconds + root.offsetMs / 1000) * 1000);
    }

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
        if (!root.active || root.title === "") {
            root.state = "idle";
            root._clear();
            return;
        }
        root.state = "loading";
        root._clear();
        trackDebounce.restart();
    }

    function _startFetch() {
        if (!root.active || !root.available || root.title === "")
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
        // `Array.isArray` is not reliable across the process boundary: a value
        // that survived JSON.parse inside the QML engine is not necessarily a
        // JS Array by the time it reaches a different component. Duck-type on
        // length instead.
        const rawLines = payload.translationLines;
        root._translationLines = (rawLines && typeof rawLines.length === "number" && rawLines.length >= 0)
                ? rawLines : [];
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
        if (root.active) {
            root._onTrackChanged();
            root._resetClock();
        }
    }
    onArtistChanged: {
        if (root.active)
            root._onTrackChanged();
    }

    Component.onCompleted: {
        if (root.active) {
            root._onTrackChanged();
            root._resetClock();
        }
    }

    Timer {
        id: trackDebounce

        interval: 250
        repeat: false
        onTriggered: root._startFetch()
    }

    // Corrects the anchor against MPRIS. Only a large disagreement re-seats it:
    // a small one is usually the player echoing a stale or floored position, and
    // following that would drag the lyric backwards. dux calls this the
    // "floored echo" case — some players floor Position to whole seconds on
    // pause and resume.
    Timer {
        id: positionSyncTimer

        interval: 350
        repeat: true
        running: root.active && root._isPlaying

        onTriggered: {
            const player = MediaService.active;
            if (!player)
                return;
            const real = Math.max(0, Number(player.position) || 0);
            if (real <= 0)
                return;
            // Within a second of a whole number and behind the clock: this is a
            // floored echo, not a seek. Ignore it.
            const lead = root._clockSeconds - real;
            const wholeSecond = Math.abs(real - Math.round(real)) < 0.05;
            if (wholeSecond && lead >= 0 && lead < 1.2)
                return;
            if (Math.abs(lead) > 0.5)
                root._anchorTo(real);
        }
    }

    // Invalidates the positionMs binding at 20Hz. The clock itself is derived
    // from the anchor, so this timer carries no state and cannot drift.
    Timer {
        id: tickTimer

        interval: 50
        repeat: true
        running: root.active && root._isPlaying && root.hasLyrics
        property int revision: 0
        onTriggered: tickTimer.revision++
    }

    Component.onDestruction: {
        trackDebounce.stop();
        positionSyncTimer.stop();
        tickTimer.stop();
        if (backend && typeof backend.cancel === "function")
            backend.cancel();
    }

    Loader {
        id: backendLoader

        source: "LyricsBackend.qml"
    }

    // Declared as a sibling of the Loader, not inside it: a Connections nested
    // in a Loader is created with the loaded item, so its `target` binding is
    // evaluated before `backendLoader.item` is assigned and never re-evaluates.
    // The result was a backend that fetched correctly and reported into
    // nothing.
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

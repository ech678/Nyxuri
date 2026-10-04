pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.app
import qs.shared.theme

// Cover-art colour extraction, entirely in QML.
//
// This used to delegate to a native Clavis.Media singleton that sampled the
// artwork in Oklab/Oklch and scored candidates. Upstream removed the native
// toolchain (R4-C-05 / R4-C-06), so extraction now goes through Quickshell's own
// ColorQuantizer — the control end4-pC's media page uses — which keeps the same
// three-step shape the dashboard expects: quantise to a dominant colour, hand it
// to CoverScheme, let CoverScheme expand it into the 14-key scheme.
//
// Two behaviours are kept from the previous implementation because the QML
// control does not provide them:
//   1. A debounce. A track start emits several artUrl updates in a burst.
//   2. Remote-cover resolution. ColorQuantizer reads local files only, and
//      kugou-tui reports http:// artUrls, so a fetch step is still required —
//      without it those players silently degraded to the fallback colour.
Singleton {
    id: root

    // Mirrors of the quantiser's output. Consumers read these; nobody sets them.
    property color primary: Appearance.colors.colPrimary
    property color onPrimary: Appearance.colors.colOnPrimary
    property color track: Appearance.colors.colPrimaryContainer

    // Tracks the last request so a re-emitted identical artUrl is a no-op.
    property string _pendingArtUrl: ""
    property color _pendingFallback: "transparent"

    // Set while a remote cover is being downloaded, so the debounce can tell
    // "waiting on the network" apart from "ready to extract".
    property bool _resolving: false

    // True when the source URL needs a fetch before the palette can read it.
    // A bare path or file:// is already local; qrc:/ is embedded.
    function _isRemote(url) {
        const lower = String(url).toLowerCase();
        return lower.startsWith("http://") || lower.startsWith("https://");
    }

    // MPRIS players report file:// URLs, but fetch_cover.py prints a bare
    // absolute path. Handing that straight to a QUrl property makes Qt treat it
    // as relative, which resolves to nothing and yields an empty palette.
    function _sourceFor(url) {
        const value = String(url || "").trim();
        if (value === "")
            return "";
        return value.startsWith("/") ? "file://" + value : value;
    }

    function _useFallback(fallback) {
        root.primary = fallback;
        root.onPrimary = Appearance.colors.colOnPrimary;
        root.track = Appearance.colors.colPrimaryContainer;
    }

    function extract(artUrl, fallback) {
        const nextUrl = String(artUrl || "").trim();
        const nextFallback = (fallback !== undefined && fallback !== null && Qt.color(fallback).valid)
              ? fallback : Appearance.colors.colPrimary;

        // Empty artUrl means "no cover" — restore the theme default right away
        // rather than leaving the previous track's accent on screen.
        if (nextUrl === "") {
            _pendingArtUrl = "";
            _resolving = false;
            quantizer.source = "";
            _useFallback(nextFallback);
            return;
        }

        if (nextUrl === _pendingArtUrl && nextFallback === _pendingFallback && !_resolving)
            return;

        _pendingArtUrl = nextUrl;
        _pendingFallback = nextFallback;

        if (_isRemote(nextUrl)) {
            // The fallback is applied immediately so a colour is on screen
            // while the download runs; the extracted colour replaces it.
            _useFallback(nextFallback);
            _resolving = true;
            resolveTimer.restart();
            return;
        }

        _resolving = false;
        debounce.restart();
    }

    // depth 0 asks for a single bucket, matching upstream. rescaleSize shrinks
    // the image before sampling: walking a full-resolution cover costs more and
    // does not change which colour dominates.
    ColorQuantizer {
        id: quantizer

        depth: 0
        rescaleSize: 8

        // Fires for both "new result" and "source cleared"; an empty list means
        // there is nothing to sample, so the fallback stays.
        onColorsChanged: {
            const colors = quantizer.colors;
            if (colors && colors.length > 0 && Qt.color(colors[0]).valid)
                root.primary = colors[0];
            else
                root.primary = root._pendingFallback;
        }
    }

    // 80ms is enough to collapse the burst of artUrl updates a track start
    // produces, while staying below the ~100ms threshold where a colour change
    // reads as delayed.
    Timer {
        id: debounce

        interval: 80
        repeat: false
        onTriggered: quantizer.source = root._sourceFor(root._pendingArtUrl)
    }

    // Remote-cover download. Runs out of process so the HTTP request cannot
    // block the shell's render thread.
    //
    // The script is content-addressed and caches to disk, so this costs one
    // network round trip per unique cover rather than per track change.
    Timer {
        id: resolveTimer

        interval: 120
        repeat: false
        onTriggered: {
            if (resolveProcess.running)
                resolveProcess.running = false;
            resolveProcess.command = ["python3", Paths.mediaScriptsDir + "/fetch_cover.py",
                                      root._pendingArtUrl];
            resolveProcess.running = true;
        }
    }

    Process {
        id: resolveProcess

        // Declared empty so a stray start cannot inherit the previous cover's
        // arguments.
        command: []

        stdout: StdioCollector {
            id: resolveStdout

            // The script is documented to emit a single JSON line, so the
            // parser can run as soon as the stream drains. Same reasoning as
            // LyricsBackend: reading .text from onExited races the pipe.
            waitForEnd: true
            onStreamFinished: root._onResolveComplete(resolveStdout.text)
        }

        onExited: (exitCode, exitStatus) => {
            // _onResolveComplete is the normal path; this only covers the case
            // where the script died without emitting anything, which would
            // otherwise leave _resolving stuck true and block every later
            // extraction for this track.
            if (root._resolving && exitCode !== 0)
                root._resolving = false;
        }
    }

    function _onResolveComplete(text) {
        root._resolving = false;
        const raw = String(text || "").trim();
        if (raw === "")
            return;
        // The payload is one JSON object on one line, but scan from the end so
        // a stray warning printed before it cannot defeat the parse.
        let payload = null;
        const lines = raw.split("\n");
        for (let i = lines.length - 1; i >= 0; i--) {
            const line = lines[i].trim();
            if (line.charAt(0) !== "{")
                continue;
            try {
                payload = JSON.parse(line);
                break;
            } catch (error) {
                continue;
            }
        }
        if (!payload)
            return;
        // An empty path means the download failed; the fallback colour set in
        // extract() stays in place, which is the documented degradation.
        const path = String(payload.path || "").trim();
        if (path === "")
            return;
        quantizer.source = root._sourceFor(path);
    }

    Component.onDestruction: {
        debounce.stop();
        resolveTimer.stop();
        if (resolveProcess.running)
            resolveProcess.running = false;
    }
}

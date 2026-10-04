import QtQuick
import Quickshell.Io
import qs.app
import qs.app.services
import qs.shared.i18n

// Transport for lyric fetches: spawns the fetcher script, parses its JSON, and
// reports back through a signal.
//
// Kept separate from LyricsService because this is the layer that touches the
// network. A fetch can legitimately take seconds on a cold cache, and if the
// process is slow, wedged, or returns junk, only this file needs to care —
// LyricsService just sees a result or an error.
//
// Every invocation is bounded by `timeoutTimer`. Squashing a hung fetch
// matters more than letting it complete: the alternative is a card stuck on
// "loading" until the next track change, and a stray process per song played.
Item {
    id: root

    // Emitted for a reply the caller still wants: (generation, payloadObject).
    signal lyrics(int generation, var payload)
    // Emitted when the fetch failed in a way the user should see.
    signal fetchFailed(int generation, string message)

    // Hard ceiling on one fetch. The script's own HTTP timeouts sum well below
    // this in the worst case (parallel probes + fallbacks), so hitting it means
    // something is genuinely stuck rather than merely slow.
    readonly property int fetchTimeoutMs: 12000

    property int _generation: -1

    // Set once a fetch has produced either a result or an error, so the second
    // of streamFinished/onExited cannot report again for the same run.
    property bool _settled: false

    function fetch(title, artist, durationSeconds, generation, refresh) {
        if (title === "")
            return;

        // A previous fetch for a different track is irrelevant now. Killing it
        // frees the slot for the new one and stops its output from arriving
        // after the replacement has already started.
        if (fetchProcess.running)
            fetchProcess.running = false;

        root._generation = generation;
        root._settled = false;

        // Argument order is fixed by the script's CLI: title, artist, duration.
        // Duration is passed as "0" rather than omitted so the positional
        // contract stays stable; the script reads it as "unknown".
        const argv = [title, artist, durationSeconds > 0 ? String(durationSeconds) : "0"];
        // Only forwarded when it differs from the script's own default, so the
        // cache key and behaviour for the common case stay byte-identical to
        // what earlier versions produced.
        if (PersonalizationConfig.lyricSource === "lrclib")
            argv.push("--source", "lrclib");
        if (refresh)
            argv.push("--refresh");
        fetchProcess.command = ["python3", Paths.lyricsScriptsDir + "/kugou_lyrics.py"].concat(argv);
        fetchProcess.running = true;
        timeoutTimer.restart();
    }

    Process {
        id: fetchProcess

        // Set per fetch by fetch(); declared empty so a stray start cannot
        // inherit the previous track's arguments.
        command: []

        // Parsing is driven by streamFinished, not onExited.
        //
        // exitCode arrives as soon as the child process is reaped, which can be
        // before the pipe has been drained. A KRC payload is ~20KB, so reading
        // `.text` from onExited raced the reader and could see a truncated or
        // empty buffer — the fetch would then report "malformed output" for a
        // response that was actually fine. waitForEnd makes the collector emit
        // only once the stream is complete, which is the ordering we need.
        stdout: StdioCollector {
            id: stdoutCollector

            waitForEnd: true
            onStreamFinished: root._onStdoutComplete(stdoutCollector.text)
        }

        // Collected so a non-zero exit can report why. Without this the UI can
        // only say "exited with code 1", which is useless when the real cause
        // is a Python traceback or a network timeout.
        stderr: StdioCollector {
            id: stderrCollector

            waitForEnd: true
        }

        // Matches the two-parameter form used by the other Process handlers in
        // this codebase; qmllint cannot resolve QProcess::ExitStatus and warns
        // regardless, so there is no gain in omitting the unused argument.
        onExited: (exitCode, exitStatus) => {
            timeoutTimer.stop();
            if (exitCode !== 0) {
                const detail = (stderrCollector.text || "").trim().split("\n").pop() || "";
                root._reportFailure(detail !== "" ? detail : I18n.tr("Lyric fetcher exited with code %1").arg(
                                        exitCode));
            } else if (!root._settled) {
                // Exit 0 but nothing was parsed: the script ran fine and simply
                // had no payload shape we recognise.
                root._reportFailure(I18n.tr("Lyric fetcher produced no output"));
            }
        }
    }

    // Turns the collected stdout into a payload and reports it.
    //
    // Called from the collector's streamFinished rather than from onExited, so
    // the buffer is known complete. Text is passed in rather than read back off
    // the collector, keeping this function independent of the Process scope.
    //
    // `_settled` guards against reporting twice for one fetch: streamFinished
    // and onExited are separate signals with no ordering guarantee, so both can
    // fire for a failing run.
    function _onStdoutComplete(text) {
        if (root._settled)
            return;

        const raw = String(text || "").trim();
        if (raw === "")
            return;

        // The script may print a diagnostic line before its JSON payload in
        // a future revision, so the last line that parses as an object
        // wins rather than assuming the whole stdout is JSON.
        let payload = null;
        const candidates = raw.split("\n");
        for (let i = candidates.length - 1; i >= 0; i--) {
            const line = candidates[i].trim();
            if (line.charAt(0) !== "{")
                continue;
            try {
                payload = JSON.parse(line);
                break;
            } catch (error) {
                continue;
            }
        }

        // A run that produced nothing parseable is reported by onExited, which
        // also has the exit code and stderr to explain why. Reporting here as
        // well would race it for the same fetch.
        if (!payload)
            return;

        root._settled = true;
        root.lyrics(root._generation, payload);
    }

    // Single funnel for failure reporting, so `_settled` is set in one place
    // and a late second signal cannot overwrite a real result.
    function _reportFailure(message) {
        if (root._settled)
            return;
        root._settled = true;
        root.fetchFailed(root._generation, message);
    }

    Timer {
        id: timeoutTimer

        interval: root.fetchTimeoutMs
        repeat: false
        onTriggered: {
            if (!fetchProcess.running)
                return;
            fetchProcess.running = false;
            root._reportFailure(I18n.tr("Lyric fetch timed out"));
        }
    }

    // Required by the lifecycle audit (LIFE002): a Process must be torn down
    // when its owner goes away. Without this the child outlives the item and
    // keeps writing to a collector that no longer has a reader.
    Component.onDestruction: {
        timeoutTimer.stop();
        if (fetchProcess)
            fetchProcess.running = false;
    }
}

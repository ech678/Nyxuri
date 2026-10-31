.pragma library

// Parses the two lyric formats the backend can return into one shape.
//
// KRC (Kugou) is the richer one: it carries per-word timing, so the dashboard
// card can highlight the word being sung rather than the whole line. LRC
// (lrclib) only has line-level stamps. Both are normalised here so the UI
// never has to branch on which backend served the track.
//
// Shape produced:
//   [{ startMs, endMs, text, translation, words: [{ startMs, endMs, text }] }]
//
// Timestamps are absolute milliseconds from track start. KRC stores word
// offsets relative to their line, so they are folded in during parsing and the
// UI can compare straight against the playback position.
//
// Live in a .js module rather than a QML singleton because the work is pure:
// no QObject, no signals, no bindings. The repository's QML test runner has no
// `qs` prefix resolution, so a singleton would be untestable, while a library
// module is importable straight from a TestCase.
//
// Translations are NOT decoded here. The backend already did that (see
// kugou_lyrics.py's decode_translation_lines) because base64 + UTF-8 handling
// is exact in Python and would otherwise drag the deprecated Qt.atob into the
// shell. It hands us a list aligned index-for-index with the timed lines.

// `[mm:ss.xxx]` / `[mm:ss]`, with KRC optionally appending a duration.
// Recreated per call: a module-level /g regex carries lastIndex across calls,
// which silently skips matches on the second invocation.
function lrcStampRegex() {
    return /\[(\d+):(\d+(?:[.:]\d+)?)\]/g;
}

// KRC word run. The third field is inter-word padding, unused for
// highlighting but required for the match to consume the whole tag.
function krcWordRegex() {
    return /<(\d+),(\d+),(-?\d+)>/g;
}

// Anchored, and matched with multiline semantics everywhere it is used.
//
// Without /m, `^` only matches at index 0, so this regex inspects the FIRST
// line of the payload and nothing else. Every real Kugou KRC opens with
// metadata tags (`[id:]`, `[ar:]`, `[ti:]`, `[by:]`, …) before the first timed
// line, so a non-multiline test always saw `[id:$00000000]`, concluded "not
// KRC", and routed the payload to the LRC parser — which finds no `[mm:ss]`
// stamps and returns an empty array. The result was a track that fetched,
// matched, parsed to zero lines, and rendered nothing at all.
var KRC_LINE_RE = /^\[(\d+),(\d+)\]/m;

function toMs(minutes, secondsText) {
    // KRC sometimes writes the fraction with a dot, LRC with a colon.
    var seconds = parseFloat(String(secondsText).replace(":", "."));
    return Math.round((Number(minutes) * 60 + seconds) * 1000);
}

// Strips the timing tags from a KRC line, leaving displayable text. Used when
// a line carries no word runs to accumulate from.
function krcPlainText(body) {
    return String(body).replace(/<\d+,\d+,-?\d+>/g, "");
}

// Credit / notice lines that Kugou emits as timed lyric rows.
//
// These are not lyrics: they are production credits ("作词：彭青", "Composed by
// …") and translation notices, tagged with real line timings. Left in, they
// occupy a lyric slot and get word-highlighted as though sung.
//
// The `[:：]` requirement is what keeps this safe: it only matches the
// credential *label* form, so a genuine lyric that happens to open with a
// single credit-ish character (e.g. "曲线救国") is not swallowed. The
// English branch requires "by" for the same reason.
function isCreditLine(text) {
    var value = String(text || "").trim();
    if (value === "")
        return false;
    if (/^(作词|作曲|编曲|原唱|制作人|混音|母带|吉他|贝斯|鼓|键盘|录音|监制|出品|发行|策划|统筹|设计|和声|弦乐|词|曲|演唱|歌手|OP|SP)\s*[:：]/.test(value))
        return true;
    if (/^(lyrics?|composed?|arranged?|produced?|mixed?|written)\s+by\s*[:：]/i.test(value))
        return true;
    return /^以下歌词翻译/.test(value) || /^本歌词由/.test(value);
}

// Splits a KRC body into timed lines with per-word timings.
function parseKrc(text, translations) {
    var rawLines = String(text || "").split("\n");
    var lines = [];
    // Translation rows are consumed only by lines that make it into the
    // output. Instrumental rows are skipped, and advancing the index for them
    // would misalign every translation after the first one.
    var translationIndex = 0;

    for (var i = 0; i < rawLines.length; i++) {
        // Kugou serves KRC with CRLF endings. Splitting on "\n" leaves a CR at
        // the end of every line, which the word scanner then absorbs into the
        // final word's text — so the rendered line picked up a trailing CR and
        // the last word's width was wrong. Strip it here, once, at the source.
        var raw = rawLines[i].replace(/\r+$/, "");
        var header = raw.match(KRC_LINE_RE);
        if (!header)
            continue;

        var lineStart = Number(header[1]);
        var lineDuration = Number(header[2]);
        var body = raw.slice(header[0].length);

        // KRC places each `<...>` tag BEFORE the text it times, so a word's
        // text is everything up to the next tag. Close each word when the
        // following tag arrives, then close the last one with the remainder.
        var wordRe = krcWordRegex();
        var words = [];
        var match = null;
        var previousTagEnd = 0;
        var scannedTo = 0;

        while ((match = wordRe.exec(body)) !== null) {
            if (words.length > 0)
                words[words.length - 1].text += body.slice(previousTagEnd, match.index);

            var offset = Number(match[1]);
            var duration = Number(match[2]);
            words.push({
                "startMs": lineStart + offset,
                "endMs": lineStart + offset + duration,
                "text": ""
            });
            previousTagEnd = match.index + match[0].length;
            scannedTo = previousTagEnd;
        }
        if (words.length > 0)
            words[words.length - 1].text += body.slice(scannedTo);

        var plain = words.length > 0 ? words.map(function (w) {
            return w.text;
        }).join("") : krcPlainText(body);

        // An instrumental break is encoded as a single empty word run. Skipped
        // so the card does not flash a blank row.
        if (plain.trim() === "" && words.length <= 1)
            continue;

        // Credits are embedded as ordinary timed lines by Kugou. Measured on
        // this machine: 26 of 695 timed lines across 9 of 12 cached KRC files,
        // so a typical track shows "作词：…" as if it were a lyric. Dropped
        // here rather than left to the UI, because the word timings would
        // otherwise be highlighted as though the credit were being sung.
        if (isCreditLine(plain))
            continue;

        var line = {
            "startMs": lineStart,
            "endMs": lineStart + lineDuration,
            "text": plain,
            "translation": "",
            "words": words
        };
        if (translationIndex < translations.length) {
            line.translation = String(translations[translationIndex] || "").trim();
            translationIndex += 1;
        }
        lines.push(line);
    }

    lines.sort(function (a, b) {
        return a.startMs - b.startMs;
    });
    return lines;
}

// Parses plain LRC: metadata tags first, then `[stamp]text` lines.
function parseLrc(text) {
    var rawLines = String(text || "").split("\n");
    var lines = [];

    for (var i = 0; i < rawLines.length; i++) {
        var raw = rawLines[i];
        // Container metadata: [ar:], [ti:], [offset:], [total:]...
        if (/^\[[a-zA-Z]+:/.test(raw))
            continue;

        // One LRC line may carry several stamps (a repeated chorus shares one
        // text block); each stamp becomes its own entry.
        var stampRe = lrcStampRegex();
        var stamps = [];
        var match = null;
        var lastStampEnd = 0;
        while ((match = stampRe.exec(raw)) !== null) {
            stamps.push(toMs(match[1], match[2]));
            lastStampEnd = match.index + match[0].length;
        }
        if (stamps.length === 0)
            continue;

        var content = raw.slice(lastStampEnd).trim();
        if (content === "")
            continue;

        for (var s = 0; s < stamps.length; s++) {
            lines.push({
                "startMs": stamps[s],
                "endMs": 0,
                "text": content,
                "translation": "",
                "words": []
            });
        }
    }

    lines.sort(function (a, b) {
        return a.startMs - b.startMs;
    });
    // LRC has no durations, so each line ends where the next begins. The final
    // line gets a fixed tail instead of ending immediately.
    for (var j = 0; j < lines.length; j++) {
        var next = lines[j + 1];
        lines[j].endMs = next ? next.startMs : lines[j].startMs + 5000;
    }
    return lines;
}

// A KRC payload carries timed lines with per-word runs. Both halves are
// matched with `/m` so they scan every line rather than only the first.
//
// Note the shape being tested for: the word run opens immediately after the
// line header (`[0,12514]<0,1137,0>你`). A tag looking like `<4,3>` can appear
// in plain prose, so the word-run half is what separates KRC from an LRC file
// that happens to contain a comma inside a metadata tag.
function looksLikeKrc(text) {
    return KRC_LINE_RE.test(text) && /^\[\d+,\d+\]<\d+,/m.test(text);
}

// Entry point. `translationLines` comes from the backend and is aligned with
// the KRC's timed lines; it is empty for LRC and untranslated tracks.
function parse(text, translationLines) {
    var source = String(text || "").trim();
    if (source === "")
        return [];
    var rows = Array.isArray(translationLines) ? translationLines : [];
    if (looksLikeKrc(source))
        return parseKrc(source, rows);
    return parseLrc(source);
}

// Index of the line covering `positionMs`, or -1 before the first line.
//
// Strictly interval-based: a position between two lines (an instrumental gap,
// or the intro before the first line) yields -1. Callers that must not blank
// the display use advanceLineIndex() below instead.
function lineIndexAt(lines, positionMs) {
    if (!lines || lines.length === 0)
        return -1;
    for (var i = 0; i < lines.length; i++) {
        if (positionMs >= lines[i].startMs && positionMs < lines[i].endMs)
            return i;
    }
    // Past every line's end: hold the last line rather than blanking the card
    // during a long outro.
    if (positionMs >= lines[lines.length - 1].endMs)
        return lines.length - 1;
    return -1;
}

// Forward-only index tracking for live playback, mirroring end4-pC's
// updateCurrentLine.
//
// Real KRC timelines are full of gaps: in one measured track 60 lines had 56
// gaps between them because line durations cover only the sung phrase, not the
// silence after it. A stateless lookup therefore oscillates `-1 -> 3 -> -1 ->
// 4` across those gaps, and the card blanks and re-appears for the whole song.
// Holding the last index until the next line actually starts keeps a lyric on
// screen continuously while still skipping over intro and instrumental gaps.
//
// `previousIndex` is returned unchanged when the position is in a gap; a
// position before the current line (a seek backwards) resets and rescans.
function advanceLineIndex(lines, positionMs, previousIndex) {
    if (!lines || lines.length === 0)
        return -1;
    var count = lines.length;
    var index = previousIndex;
    if (typeof index !== "number" || !isFinite(index) || index < -1 || index >= count)
        index = -1;
    // Backwards seek: the tracked line starts after the position, so the
    // forward-only cursor is meaningless and must be rebuilt from scratch.
    if (index >= 0 && lines[index].startMs > positionMs)
        index = -1;
    while (index + 1 < count && lines[index + 1].startMs <= positionMs)
        index += 1;
    return index;
}

// Index of the word being sung within `line`, or -1 when the line has no word
// timings or the position falls in a gap between words.
function wordIndexAt(line, positionMs) {
    if (!line || !line.words || line.words.length === 0)
        return -1;
    var words = line.words;
    for (var i = 0; i < words.length; i++) {
        if (positionMs >= words[i].startMs && positionMs < words[i].endMs)
            return i;
    }
    return positionMs >= words[words.length - 1].endMs ? words.length - 1 : -1;
}

// How far through `word` the playback is, as 0.0 .. 1.0.
//
// Mirrors kugou-tui's LyricWord::progress_at and end4-pC's wordProgress. Using
// a continuous ratio rather than a boolean is what makes the highlight sweep
// instead of snapping: the currently-sung word is drawn as a blend between the
// unsung and sung colours, so the boundary advances with the audio.
//
// Degenerate words (KRC does emit dur <= 0) fall back to a hard on/off at the
// word start, which is the honest rendering when there is no span to
// interpolate across.
function wordProgress(word, positionMs) {
    if (!word)
        return 0;
    var start = word.startMs;
    var dur = word.endMs - word.startMs;
    if (dur <= 0)
        return positionMs >= start ? 1 : 0;
    if (positionMs >= word.endMs)
        return 1;
    if (positionMs <= start)
        return 0;
    return (positionMs - start) / dur;
}

// Blends two "#rrggbb" colours by `t` (clamped to 0..1).
//
// Kept here rather than in the card so it is covered by the QML test runner —
// colour maths that silently produces an invalid string is the kind of defect
// that shows up as an invisible lyric rather than a crash.
function blendHex(from, to, t) {
    var k = t < 0 ? 0 : (t > 1 ? 1 : t);
    var a = parseHex(from);
    var b = parseHex(to);
    if (a === null || b === null)
        return String(to || from || "");
    var channel = function (lo, hi) {
        return Math.round(lo + (hi - lo) * k);
    };
    return "#" + hex2(channel(a[0], b[0])) + hex2(channel(a[1], b[1])) + hex2(channel(a[2], b[2]));
}

function parseHex(value) {
    var match = /^#?([0-9a-f]{6})$/i.exec(String(value || "").trim());
    if (!match)
        return null;
    var n = parseInt(match[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function hex2(value) {
    var text = Math.max(0, Math.min(255, value)).toString(16);
    return text.length < 2 ? "0" + text : text;
}

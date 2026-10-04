import QtQuick 2.15
import QtTest 1.3
import "../../modules/settings/dashboard/lyrics/LyricsParser.js" as LyricsParser

// Covers the lyric grammars and the position lookups the dashboard card drives
// every frame. The parser is a plain library module with no I/O, so it loads
// here directly — no shell singletons involved.
TestCase {
    name: "LyricsParser"

    readonly property string krcSample: "[0,13563]<0,1507,0>金<1507,1507,0>贵<3014,1507,0>晟\n"
                                        + "[43706,3220]<0,650,0>想<650,350,0>借<1000,410,0>天\n"
                                        + "[47316,4910]<0,490,0>抓<490,540,0>住<1030,300,0>云\n"

    readonly property string lrcSample: "[ar:金贵晟]\n" + "[ti:虹之间]\n" + "[00:43.706]想借天使的翅膀\n"
                                        + "[00:47.316]抓住云端的彩虹\n"

    // KRC carries per-word timings: each `<offset,duration,extra>` tag times
    // the text that follows it, with offsets relative to the line start.
    function test_krcParsesAbsoluteWordTimings() {
        const lines = LyricsParser.parse(krcSample, []);
        compare(lines.length, 3);

        const first = lines[0];
        compare(first.startMs, 0);
        compare(first.endMs, 13563);
        compare(first.text, "金贵晟");
        compare(first.words.length, 3);
        // First word starts at the line start; the second is offset by its
        // own 1507ms relative stamp.
        compare(first.words[0].startMs, 0);
        compare(first.words[0].endMs, 1507);
        compare(first.words[0].text, "金");
        compare(first.words[1].startMs, 1507);
        compare(first.words[1].text, "贵");
        compare(first.words[2].startMs, 3014);
        compare(first.words[2].endMs, 4521);
    }

    // Translation rows are matched by index, and the caller's rows must line
    // up with the emitted lines — an off-by-one here shows the wrong line's
    // translation for the whole song.
    function test_krcPairsTranslationsByIndex() {
        const lines = LyricsParser.parse(krcSample, ["", "想要借天使", "抓住云端"]);
        compare(lines[0].translation, "");
        compare(lines[1].translation, "想要借天使");
        compare(lines[2].translation, "抓住云端");
    }

    // LRC has no durations, so each line must end where the next begins;
    // otherwise only the final line would ever report as active.
    function test_lrcDerivesEndFromNextLineStart() {
        const lines = LyricsParser.parse(lrcSample, []);
        compare(lines.length, 2);

        compare(lines[0].startMs, 43706);
        compare(lines[0].endMs, 47316);
        compare(lines[0].text, "想借天使的翅膀");
        compare(lines[1].startMs, 47316);
        // The last line gets a fixed tail instead of collapsing to zero width.
        verify(lines[1].endMs > lines[1].startMs);
    }

    // Container tags like [ar:]/[ti:] must never surface as lyric lines.
    function test_lrcSkipsMetadataTags() {
        const lines = LyricsParser.parse(lrcSample, []);
        for (const line of lines)
            verify(!line.text.startsWith("ar:") && !line.text.startsWith("ti:"));
    }

    function test_lineIndexAtFindsCoveringLine() {
        const lines = LyricsParser.parse(lrcSample, []);
        compare(LyricsParser.lineIndexAt(lines, 43706), 0);
        compare(LyricsParser.lineIndexAt(lines, 47000), 0);
        compare(LyricsParser.lineIndexAt(lines, 47316), 1);
        // Before the first line (intro): nothing is highlighted.
        compare(LyricsParser.lineIndexAt(lines, 1000), -1);
        // Past the end: the last line is held rather than blanking the card.
        compare(LyricsParser.lineIndexAt(lines, 999999), 1);
    }

    function test_wordIndexAtFindsSungWord() {
        const lines = LyricsParser.parse(krcSample, []);
        const second = lines[1];
        compare(LyricsParser.wordIndexAt(second, second.words[0].startMs), 0);
        compare(LyricsParser.wordIndexAt(second, second.words[1].startMs), 1);
        compare(LyricsParser.wordIndexAt(second, second.words[1].endMs - 1), 1);
        // An LRC line has no word timings, so nothing can be highlighted.
        const lrcLines = LyricsParser.parse(lrcSample, []);
        compare(LyricsParser.wordIndexAt(lrcLines[0], 44000), -1);
    }

    // Empty input must produce an empty list rather than throwing, because it
    // is the normal state before the first fetch lands.
    function test_emptyInputYieldsNoLines() {
        compare(LyricsParser.parse("", []).length, 0);
        compare(LyricsParser.parse("   \n  ", []).length, 0);
        compare(LyricsParser.lineIndexAt([], 0), -1);
        compare(LyricsParser.wordIndexAt(null, 0), -1);
    }

    // Verbatim shape of a real Kugou response for an untimed track: UTF-8 BOM
    // on the first tag, CRLF endings, and a [language:] block that decodes to
    // an empty content array. The BOM must not become a lyric line, and the
    // empty translation block must not be treated as one.
    readonly property string kugouBomSample: "\ufeff[id:$00000000]\r\n" + "[ar:阿桑]\r\n" + "[ti:一直很安静]\r\n"
                                             + "[total:0]\r\n"
                                             + "[language:eyJjb250ZW50IjpbXSwidmVyc2lvbjoxfQ==]\r\n"
                                             + "[00:00.000]一直很安静\r\n" + "[00:05.000]空荡的街景\r\n"
                                             + "[00:10.000]想找个人放感情\r\n"

    function test_kugouBomAndEmptyTranslationBlock() {
        const lines = LyricsParser.parse(kugouBomSample, []);
        compare(lines.length, 3);
        compare(lines[0].text, "一直很安静");
        compare(lines[0].startMs, 0);
        compare(lines[0].translation, "");
        // CRLF endings must not leak a trailing CR into the rendered text.
        verify(lines[0].text.indexOf("\r") === -1);
        verify(lines[1].text.indexOf("\r") === -1);
    }

    // Instrumental breaks arrive as a timed line with no text at all. They are
    // dropped rather than rendered as a blank row, and a dropped row must not
    // consume a translation slot or every later translation shifts by one.
    function test_krcInstrumentalLineIsSkippedWithoutConsumingTranslation() {
        const sample = "[0,1000]啊\n" + "[5000,2000]\n" + "[9000,1000]<0,400,0>哦\n";
        const lines = LyricsParser.parse(sample, ["trans-0", "trans-1", "trans-2"]);
        compare(lines.length, 2);
        compare(lines[0].text, "啊");
        compare(lines[1].text, "哦");
        // The blank line was dropped, so index 1 keeps index 1's translation.
        compare(lines[0].translation, "trans-0");
        compare(lines[1].translation, "trans-1");
    }

    // Regression: every other KRC fixture here opens with a timed line, which is
    // not what Kugou actually returns. A real payload leads with metadata tags
    // ([id:]/[ar:]/[ti:]/[by:]) and only then starts the timed lines. Detection
    // used a non-multiline anchored regex, so it only ever inspected index 0,
    // saw `[id:$00000000]`, and routed the whole payload to the LRC parser —
    // which found no `[mm:ss]` stamps and returned zero rows. The card then
    // showed nothing at all for a track that had fetched and matched fine.
    readonly property string kugouMetadataFirstSample: "[id:$00000000]\n" + "[ar:何洁]\n" + "[ti:你是我的风景]\n"
                                                       + "[by:]\n"
                                                       + "[0,12514]<0,1137,0>你<1137,1138,0>是<2275,1138,0>我<3413,1137,0>的<4550,1138,0>风<5688,1138,0>景\n"
                                                       + "[12514,4551]<0,1138,0>词<1138,1137,0>：<2275,1138,0>彭<3413,1138,0>青\n"

    // Metadata tags must not stop detection, and the credit line that follows
    // them must be dropped while the real lyric is kept.
    function test_krcIsDetectedWhenMetadataTagsPrecedeTheTimedLines() {
        verify(LyricsParser.looksLikeKrc(kugouMetadataFirstSample));
        const lines = LyricsParser.parse(kugouMetadataFirstSample, []);
        compare(lines.length, 1);
        compare(lines[0].text, "你是我的风景");
        compare(lines[0].startMs, 0);
        compare(lines[0].endMs, 12514);
        compare(lines[0].words.length, 6);
        // Word timings are absolute: the 2nd char is 1137ms into the line.
        compare(lines[0].words[1].startMs, 1137);
    }

    // Credits arrive as ordinary timed lines. Measured on this machine, 26 of
    // 695 timed lines across 9 of 12 cached KRC files are credits, so without
    // this filter a typical track renders "作词：…" as if it were a lyric.
    function test_krcCreditLinesAreDropped() {
        const sample = "[0,1000]<0,500,0>作<500,500,0>词<0,0,0>：<0,0,0>彭青\n"
              + "[2000,1000]<0,900,0>真<900,100,0>正\n" + "[5000,1000]Composed by: Someone\n"
              + "[7000,1000]<0,900,0>歌<900,100,0>词\n";
        const lines = LyricsParser.parse(sample, []);
        compare(lines.length, 2);
        compare(lines[0].text, "真正");
        compare(lines[1].text, "歌词");
    }

    // The credit filter keys on the label form (`词：`), so a genuine lyric that
    // merely starts with a credit-ish character must survive. This is the
    // guard-rail that keeps the filter from eating real content.
    function test_creditFilterDoesNotEatLyricsStartingWithCreditorWord() {
        const sample = "[0,1000]<0,500,0>曲<500,500,0>线\n" + "[2000,1000]<0,500,0>词<500,500,0>不达意\n"
              + "[4000,1000]好好说话\n";
        const lines = LyricsParser.parse(sample, []);
        compare(lines.length, 3);
        compare(lines[0].text, "曲线");
        compare(lines[1].text, "词不达意");
        compare(lines[2].text, "好好说话");
    }

    // Same shape, but with the UTF-8 BOM and CRLF endings Kugou actually sends.
    // Both must survive detection: the BOM is stripped by the caller's trim(),
    // and the trailing CR must not stop the line header from matching.
    function test_krcIsDetectedWithBomAndCrlf() {
        const sample = "\ufeff[id:$00000000]\r\n" + "[ti:你是我的风景]\r\n"
              + "[0,12514]<0,1137,0>你<1137,1138,0>是\r\n" + "[12514,4551]<0,1138,0>词\r\n";
        verify(LyricsParser.looksLikeKrc(sample));
        const lines = LyricsParser.parse(sample, []);
        compare(lines.length, 2);
        compare(lines[0].text, "你是");
        verify(lines[0].text.indexOf("\r") === -1);
    }

    // A CRLF payload must not leak a carriage return into the rendered text of
    // the last word either, since the word scanner absorbs the remainder of the
    // line into the final word's text.
    function test_krcCrlfDoesNotLeakIntoWordText() {
        const sample = "[0,2000]<0,900,0>你<900,1000,0>好\r\n";
        const lines = LyricsParser.parse(sample, []);
        compare(lines.length, 1);
        compare(lines[0].text, "你好");
        compare(lines[0].words.length, 2);
        compare(lines[0].words[1].text, "好");
        verify(lines[0].words[1].text.indexOf("\r") === -1);
    }

    // Real KRC timelines are mostly gaps: line durations cover the sung phrase,
    // not the silence after it. A stateless lookup returns -1 inside every gap,
    // so the card blanks repeatedly. advanceLineIndex must hold the last line
    // and only move on when the next one has actually started.
    function test_advanceLineIndexHoldsThroughGaps() {
        const lines = [
                  {
                      startMs: 0,
                      endMs: 1000
                  },
                  {
                      startMs: 5000,
                      endMs: 6000
                  },
                  {
                      startMs: 9000,
                      endMs: 10000
                  }
              ];
        let index = -1;
        // Walking 1s at a time must never step backwards.
        let previous = -1;
        for (let t = 0; t <= 12000; t += 1000) {
            index = LyricsParser.advanceLineIndex(lines, t, index);
            verify(index >= previous);
            previous = index;
        }
        // And it must end on the last line rather than a gap sentinel.
        compare(index, 2);
    }

    function test_advanceLineIndexAdvancesAtLineStart() {
        const lines = [
                  {
                      startMs: 0,
                      endMs: 1000
                  },
                  {
                      startMs: 5000,
                      endMs: 6000
                  }
              ];
        let index = -1;
        index = LyricsParser.advanceLineIndex(lines, 0, index);
        compare(index, 0);
        // Inside the 1s-5s gap the tracked line is held, not cleared.
        index = LyricsParser.advanceLineIndex(lines, 3000, index);
        compare(index, 0);
        // The moment the next line starts, the cursor moves.
        index = LyricsParser.advanceLineIndex(lines, 5000, index);
        compare(index, 1);
    }

    // Before the first line there is nothing to hold, so the cursor stays at -1.
    function test_advanceLineIndexStaysNegativeDuringIntro() {
        const lines = [
                  {
                      startMs: 5000,
                      endMs: 6000
                  }
              ];
        compare(LyricsParser.advanceLineIndex(lines, 0, -1), -1);
        compare(LyricsParser.advanceLineIndex(lines, 4999, -1), -1);
        compare(LyricsParser.advanceLineIndex(lines, 5000, -1), 0);
    }

    // A seek backwards invalidates the forward-only cursor, which must be
    // rebuilt from the new position rather than staying stuck ahead of it.
    function test_advanceLineIndexRescansAfterBackwardsSeek() {
        const lines = [
                  {
                      startMs: 0,
                      endMs: 1000
                  },
                  {
                      startMs: 5000,
                      endMs: 6000
                  },
                  {
                      startMs: 9000,
                      endMs: 10000
                  }
              ];
        let index = LyricsParser.advanceLineIndex(lines, 9500, 2);
        compare(index, 2);
        // Seek back to the start: the cursor must not remain on line 2.
        index = LyricsParser.advanceLineIndex(lines, 0, index);
        compare(index, 0);
    }

    function test_advanceLineIndexHandlesEmptyAndInvalidInput() {
        compare(LyricsParser.advanceLineIndex([], 1000, 0), -1);
        compare(LyricsParser.advanceLineIndex(null, 1000, 0), -1);
        const lines = [
                  {
                      startMs: 0,
                      endMs: 1000
                  }
              ];
        // An out-of-range or non-finite cursor is discarded, not propagated.
        compare(LyricsParser.advanceLineIndex(lines, 0, 99), 0);
        compare(LyricsParser.advanceLineIndex(lines, 0, NaN), 0);
    }

    // The sweep: a word's progress must rise linearly across its span so the
    // highlight advances with the audio instead of snapping on at the start.
    function test_wordProgressRampsAcrossTheWord() {
        const word = {
            startMs: 1000,
            endMs: 2000
        };
        compare(LyricsParser.wordProgress(word, 0), 0);
        compare(LyricsParser.wordProgress(word, 1000), 0);
        compare(LyricsParser.wordProgress(word, 1500), 0.5);
        compare(LyricsParser.wordProgress(word, 2000), 1);
        compare(LyricsParser.wordProgress(word, 9999), 1);
    }

    // KRC does emit zero-duration words. There is no span to interpolate, so
    // the only honest rendering is a hard switch at the word start.
    function test_wordProgressDegradesOnZeroDurationWord() {
        const word = {
            startMs: 1000,
            endMs: 1000
        };
        compare(LyricsParser.wordProgress(word, 999), 0);
        compare(LyricsParser.wordProgress(word, 1000), 1);
        compare(LyricsParser.wordProgress(word, 1500), 1);
        compare(LyricsParser.wordProgress(null, 1000), 0);
    }

    function test_blendHexInterpolatesAndClamps() {
        compare(LyricsParser.blendHex("#000000", "#ffffff", 0), "#000000");
        compare(LyricsParser.blendHex("#000000", "#ffffff", 1), "#ffffff");
        compare(LyricsParser.blendHex("#000000", "#ffffff", 0.5), "#808080");
        // Out-of-range t is clamped rather than producing an invalid colour.
        compare(LyricsParser.blendHex("#000000", "#ffffff", -5), "#000000");
        compare(LyricsParser.blendHex("#000000", "#ffffff", 5), "#ffffff");
    }

    // A malformed colour must not yield a string like "#NaN" — Qt would then
    // render nothing at all, which shows up as a missing word rather than a
    // visible error. Falling back to the target colour keeps the text present.
    function test_blendHexRejectsMalformedColours() {
        compare(LyricsParser.blendHex("not-a-colour", "#ff0000", 0.5), "#ff0000");
        compare(LyricsParser.blendHex("#00ff00", "", 0.5), "#00ff00");
        compare(LyricsParser.blendHex("", "", 0.5), "");
    }
}

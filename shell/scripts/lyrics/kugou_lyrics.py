#!/usr/bin/env python3
"""Kugou KRC / lrclib lyric fetcher for the Nyxuri Shell dashboard card.

Emits one JSON document on stdout so the QML side never has to parse the raw
KRC container. The payload carries the lyric text verbatim (KRC or LRC) plus
the metadata the caller needs to decide whether to trust it:

    {"source": "kugou" | "lrclib" | "none",
     "matched": bool,          # search hit verified against title/artist
     "translation": "cjk" | "romaji" | "none",
     "lyrics": "<raw text>"}

Why the raw text and not a pre-parsed structure: the KRC and LRC grammars are
different enough that parsing them in Python would mean maintaining two parsers
here and a third one's worth of shape knowledge in QML. The QML side already
needs a parser for rendering; keeping a single implementation avoids the two
drifting apart.

Strategy, in order:
  1. Disk cache (only ever written for verified matches).
  2. Kugou's private mobile API, which is the only source that ships per-word
     timestamps alongside optional translations.
  3. lrclib.net, a public line-level LRC database, for anything Kugou misses.

Every network call here is best-effort: a failure degrades to the next source
rather than aborting, because a lyric fetch must never be able to wedge the
shell. Timeouts are aggressive for the same reason — the card is showing a
loading state for however long this takes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import threading
import urllib.parse
import zlib
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from nyxuri_paths import NyxuriPaths  # noqa: E402

CACHE_SUBDIR = "lyrics"

# Kugou's KRC container XORs the body after a 4-byte "krc1" magic. The key is
# fixed and public (it ships in every third-party client); the payload is
# zlib-compressed afterwards.
XOR_KEY = bytes((64, 71, 97, 119, 94, 50, 116, 71, 81, 54, 49, 45, 206, 210, 110, 105))

# Kugou rejects requests without a browser-ish UA. Nothing here is
# user-specific: there is no cookie, token, or account credential anywhere in
# this file.
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

# Written into a cached KRC whose translation block is romaji-only. Without it
# such a cache would look stale on every play and be refetched forever.
CACHE_NO_CJK_MARK = "[nyxuri:no-cjk-translation]"

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_LANGUAGE_RE = re.compile(r"\[language:([A-Za-z0-9+/=]*)\]")
_TIMED_LINE_RE = re.compile(r"\[\d+:\d+")


# --------------------------------------------------------------------------
# HTTP with per-thread keep-alive
#
# A song change fires several requests to the same two hosts (search, probe,
# download). On a fresh connection each of those pays a TCP+TLS handshake,
# which dominated the old latency. Connections are pooled per thread because
# this module probes hashes in parallel.
# --------------------------------------------------------------------------

_TLS = threading.local()


def _http_get(url: str, timeout: float, *, as_json: bool):
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path + (("?" + parsed.query) if parsed.query else "")
    scheme = f"{parsed.scheme}://{parsed.netloc}"

    pool = getattr(_TLS, "conns", None)
    if pool is None:
        pool = _TLS.conns = {}
    conn = pool.get(scheme)
    fresh = conn is None
    if fresh:
        cls = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
        conn = cls(parsed.netloc, timeout=timeout)

    body = ""
    try:
        conn.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="ignore")
        # A server that closes the socket makes the pooled entry unusable;
        # dropping it now means the next call reconnects instead of failing.
        if resp.will_close:
            conn.close()
            pool.pop(scheme, None)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        pool.pop(scheme, None)
        return None

    if not as_json:
        return body
    try:
        return json.loads(body)
    except Exception:
        return None


def http_json(url: str, timeout: float = 3.0):
    return _http_get(url, timeout, as_json=True)


# --------------------------------------------------------------------------
# Name handling and KRC decryption
# --------------------------------------------------------------------------


def clean_name(value: str) -> str:
    """Strip bracketed qualifiers that players append but Kugou omits.

    "Song (feat. X)" and "Song [Remastered]" are the same track upstream; a
    mismatch here is what makes an exact-name search come back empty.
    """
    if not value:
        return ""
    out = re.sub(r"\(feat\.[^)]*\)", "", value, flags=re.IGNORECASE)
    out = re.sub(r"\[feat\.[^\]]*\]", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\(remastered[^)]*\)", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\[remastered[^\]]*\]", "", out, flags=re.IGNORECASE)
    return out.strip()


def norm_text(value: str) -> str:
    """Lowercase, drop whitespace and punctuation — for fuzzy name matching."""
    return re.sub(r"[\s\W_]+", "", (value or "").lower())


def decrypt_krc(b64_content: str) -> str:
    """Decode a KRC container: base64 -> XOR -> zlib -> UTF-8.

    Some responses carry plain base64-encoded LRC instead of a KRC container
    (Kugou does this for certain older uploads), so the magic check is a
    discriminator rather than an assertion.
    """
    try:
        raw = bytearray(base64.b64decode(b64_content))
        if len(raw) <= 4:
            return ""
        if raw[:4] != b"krc1":
            try:
                plain = raw.decode("utf-8")
                if "[" in plain and "]" in plain:
                    return plain
            except Exception:
                pass

        for i in range(4, len(raw)):
            raw[i] ^= XOR_KEY[(i - 4) % len(XOR_KEY)]
        return zlib.decompress(bytes(raw[4:])).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def translation_kind(decrypted: str) -> str:
    """Classify the KRC's embedded [language:] payload.

    Kugou ships several KRC variants per hash: some embed a real Chinese
    translation, others only a romaji (mora-by-mora) transliteration. The
    romaji variant is useless for display, so it must not win the candidate
    race merely by arriving first.

    Returns "cjk", "romaji", or "none".
    """
    saw_romaji = False
    for b64 in _LANGUAGE_RE.findall(decrypted):
        try:
            padded = b64 + "=" * (-len(b64) % 4)
            payload = json.loads(base64.b64decode(padded).decode("utf-8"))
        except Exception:
            continue
        for block in payload.get("content", []):
            lines = [
                "".join(part) if isinstance(part, list) else str(part)
                for part in block.get("lyricContent", [])
            ]
            if not any(line.strip() for line in lines):
                continue
            if any(_CJK_RE.search(line) for line in lines):
                return "cjk"
            saw_romaji = True
    return "romaji" if saw_romaji else "none"


# --------------------------------------------------------------------------
# Candidate search
# --------------------------------------------------------------------------


def score_song(song: dict, title: str, artist: str, duration_sec: float) -> int:
    """How well a Kugou search hit matches the metadata we were given."""
    name = norm_text(song.get("songname"))
    singer = norm_text(song.get("singername"))
    want_title, want_artist = norm_text(title), norm_text(artist)

    score = 0
    if want_title and name:
        if name == want_title:
            score += 3
        elif want_title in name or name in want_title:
            score += 2
    if want_artist and singer:
        if singer == want_artist:
            score += 3
        elif want_artist in singer or singer in want_artist:
            score += 2
    # Duration is a tie-breaker only. KRC timelines routinely differ from the
    # MPRIS length by more than 10s, so treating it as a filter would empty
    # the candidate list for perfectly good matches.
    if duration_sec > 0 and song.get("duration"):
        try:
            if abs(float(song["duration"]) - duration_sec) <= 5:
                score += 1
        except (TypeError, ValueError):
            pass
    return score


def search_songs(keyword: str) -> list:
    data = http_json(
        "http://msearchcdn.kugou.com/api/v3/search/song"
        f"?keyword={urllib.parse.quote(keyword)}&page=1&pagesize=5"
    )
    if not isinstance(data, dict):
        return []
    return data.get("data", {}).get("info", []) or []


def _probe_hash(file_hash: str, sink: dict, lock: threading.Lock) -> None:
    """Resolve one audio hash to a krcs candidate list. Runs on a worker."""
    data = http_json(
        "http://krcs.kugou.com/search?ver=1&man=yes&client=mobi"
        f"&keyword=&duration=0&hash={file_hash}"
    )
    candidates = (data or {}).get("candidates", []) if isinstance(data, dict) else []
    if candidates:
        with lock:
            sink[file_hash] = candidates


def pick_candidates(songs: list, title: str, artist: str, duration_sec: float):
    """Rank hits, probe the top few hashes in parallel, return (candidates, matched).

    `matched` reports whether the best hit actually corresponds to the request.
    Callers must not cache anything that is not matched — one wrong cache write
    poisons a song until the cache is cleared by hand.

    Selection follows search rank, not response arrival order: hashes are
    probed concurrently, and "whichever came back first" once cached the wrong
    song's lyrics under the right key.
    """
    if not songs:
        return [], False

    ranked = sorted(songs, key=lambda s: score_song(s, title, artist, duration_sec), reverse=True)
    matched = score_song(ranked[0], title, artist, duration_sec) > 0

    hashes = [s.get("hash") for s in ranked[:3] if s.get("hash")]
    if not hashes:
        return [], matched

    sink: dict = {}
    lock = threading.Lock()
    workers = [threading.Thread(target=_probe_hash, args=(h, sink, lock), daemon=True) for h in hashes]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=4)

    for file_hash in hashes:
        if sink.get(file_hash):
            return sink[file_hash], matched
    return [], matched


def download_lyrics(candidates: list) -> str:
    """Fetch the best decryptable candidate, preferring one with a real translation.

    A romaji-only KRC is kept as a fallback for when no translated variant
    exists anywhere in the candidate list.
    """
    fallback = ""
    for best in candidates[:6]:
        cand_id = best.get("id")
        access_key = best.get("accesskey")
        if not cand_id or not access_key:
            continue

        fmt = best.get("fmt") or "krc"
        data = http_json(
            "http://krcs.kugou.com/download?ver=1&client=mobi"
            f"&id={cand_id}&accesskey={access_key}&fmt={fmt}&charset=utf8",
            timeout=4,
        )
        if not isinstance(data, dict):
            continue
        content_b64 = data.get("content", "")
        if not content_b64:
            continue

        decrypted = decrypt_krc(content_b64)
        if not decrypted or not has_timed_lines(decrypted):
            continue

        # Some downloads return the translation out-of-band instead of inside
        # the KRC. Splice it in so the caller sees one uniform container.
        trans_b64 = data.get("trans", "")
        if trans_b64 and "[language:" not in decrypted:
            try:
                raw_trans = base64.b64decode(trans_b64).decode("utf-8", errors="ignore")
                if raw_trans.strip().startswith("{") and "content" in raw_trans:
                    decrypted = f"{decrypted.strip()}\n[language:{trans_b64.strip()}]\n"
            except Exception:
                pass

        if translation_kind(decrypted) == "cjk":
            return decrypted
        if not fallback:
            fallback = decrypted
    return fallback


def fetch_kugou(title: str, artist: str, duration_sec: float):
    """Return (lyrics, matched) from Kugou. Unmatched lyrics are served but never cached."""
    # Some players report title and artist swapped (MoeKoeMusic does this);
    # trying both orders costs one extra search and rescues those cases.
    attempts = [(title, artist)]
    if artist and norm_text(artist) != norm_text(title):
        attempts.append((artist, title))

    for want_title, want_artist in attempts:
        keyword = f"{want_title} {want_artist}".strip()
        if not keyword:
            continue
        candidates, matched = pick_candidates(
            search_songs(keyword), want_title, want_artist, duration_sec
        )
        if not candidates:
            continue
        lyrics = download_lyrics(candidates)
        if lyrics:
            return lyrics, matched

    # Last resort: the plain krcs keyword search. Unreliable for many
    # artist/title combinations, and adding more than the first word makes it
    # miss songs the hash flow finds, so it stays deliberately narrow.
    first_word = (title.split(" ") or [""])[0]
    if first_word:
        data = http_json(
            "http://krcs.kugou.com/search?ver=1&man=yes&client=mobi"
            f"&keyword={urllib.parse.quote(first_word)}&duration=0&hash="
        )
        candidates = (data or {}).get("candidates", []) if isinstance(data, dict) else []
        if candidates:
            lyrics = download_lyrics(candidates)
            if lyrics:
                return lyrics, False
    return "", False


def fetch_lrclib(title: str, artist: str, duration_sec: float) -> str:
    """Public line-level LRC fallback. Weaker on Chinese catalogue, zero auth."""
    queries = []
    if duration_sec > 0:
        queries.append(
            "https://lrclib.net/api/get"
            f"?track_name={urllib.parse.quote(title)}&artist_name={urllib.parse.quote(artist)}"
            f"&duration={int(duration_sec)}"
        )
    queries.append(
        "https://lrclib.net/api/search"
        f"?track_name={urllib.parse.quote(title)}&artist_name={urllib.parse.quote(artist)}"
    )
    queries.append(f"https://lrclib.net/api/search?q={urllib.parse.quote(title + ' ' + artist)}")

    for url in queries:
        data = http_json(url, timeout=4)
        if isinstance(data, list) and data:
            data = data[0]
        if isinstance(data, dict):
            synced = (data.get("syncedLyrics") or "").strip()
            if synced:
                return synced
    return ""


def has_timed_lines(text: str) -> bool:
    """Reject garbage that would render as a single unsynced blob."""
    return bool(_TIMED_LINE_RE.search(text)) or bool(re.search(r"^\[\d+,\d+\]", text, re.M))


def decode_translation_lines(decrypted: str) -> list:
    """Decode the KRC `[language:]` payload into a list of translated lines.

    Returned positions line up 1:1 with the KRC's timed lines, so the QML
    parser can pair them by index. Empty strings mean "this line has no
    translation" (titles, credits, instrumental markers) and must be kept in
    place — dropping them would shift every subsequent line's translation.

    Decoding happens here rather than in QML for two reasons: Python's base64
    and JSON handling is exact for UTF-8, and it keeps the deprecated
    Qt.atob out of the shell's QML entirely.
    """
    for b64 in _LANGUAGE_RE.findall(decrypted):
        try:
            padded = b64 + "=" * (-len(b64) % 4)
            payload = json.loads(base64.b64decode(padded).decode("utf-8"))
        except Exception:
            continue
        for block in payload.get("content", []):
            rows = block.get("lyricContent", [])
            if not rows:
                continue
            lines = ["".join(part) if isinstance(part, list) else str(part) for part in rows]
            # A block of only-empty rows carries no information; keep looking
            # in case another block in the same payload does.
            if any(line.strip() for line in lines):
                return lines
    return []


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def cache_path(title: str, artist: str) -> Path:
    cache_dir = NyxuriPaths.from_environment().cache_home / CACHE_SUBDIR
    key = hashlib.md5(f"{title.lower()}_{artist.lower()}".encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.krc"


def emit(lyrics: str, source: str, matched: bool, kind: str) -> None:
    """Print the one JSON document the QML caller reads.

    `translationLines` is only populated for a verified CJK translation;
    romaji is a transliteration of the original text, not something to show
    under it, so it is reported in `translation` but left out of the payload.
    """
    lines = decode_translation_lines(lyrics) if (lyrics and kind == "cjk") else []
    sys.stdout.write(json.dumps(
        {
            "source": source,
            "matched": bool(matched),
            "translation": kind,
            "lyrics": lyrics,
            "translationLines": lines,
        },
        ensure_ascii=False,
    ))
    sys.stdout.flush()


def main() -> int:
    argv = list(sys.argv[1:])
    refresh = "--refresh" in argv
    argv = [a for a in argv if a != "--refresh"]
    # Backend selection. "kugou" (default) tries Kugou first and falls back to
    # lrclib; "lrclib" skips Kugou entirely, which is the escape hatch for both
    # a Kugou outage and a track Kugou matches to the wrong recording.
    source_pref = "kugou"
    if "--source" in argv:
        index = argv.index("--source")
        if index + 1 < len(argv):
            source_pref = "lrclib" if argv[index + 1] == "lrclib" else "kugou"
            del argv[index:index + 2]
        else:
            del argv[index]
    if not argv:
        emit("", "none", False, "none")
        return 0

    title = clean_name(argv[0])
    artist = clean_name(argv[1]) if len(argv) > 1 else ""
    duration = 0.0
    if len(argv) > 2:
        try:
            duration = float(argv[2])
        except ValueError:
            duration = 0.0

    if not title:
        emit("", "none", False, "none")
        return 0

    path = cache_path(title, artist)

    if not refresh and path.is_file() and path.stat().st_size > 10:
        try:
            cached = path.read_text(encoding="utf-8")
            # A romaji-only cache is a pick from the old candidate ordering;
            # refetch once to look for a translated variant. An empty payload
            # ("none") is legitimate and must not refetch on every play.
            stale = CACHE_NO_CJK_MARK not in cached and translation_kind(cached) == "romaji"
            if not stale:
                clean = cached.replace(CACHE_NO_CJK_MARK, "")
                emit(clean, "cache", True, translation_kind(clean))
                return 0
        except Exception:
            pass

    lyrics, matched = ("", False)
    if source_pref == "kugou":
        lyrics, matched = fetch_kugou(title, artist, duration)
    source = "kugou"
    if not lyrics:
        lyrics = fetch_lrclib(title, artist, duration)
        matched = bool(lyrics)  # lrclib matches on exact names, so a hit is a match
        source = "lrclib" if lyrics else "none"

    kind = translation_kind(lyrics) if lyrics else "none"

    # Cache only verified results. An unmatched pick is re-fetched next time
    # rather than locked in, which is what keeps --refresh able to recover.
    if lyrics and matched:
        try:
            payload = lyrics
            if kind == "romaji":
                payload = f"{lyrics.rstrip()}\n{CACHE_NO_CJK_MARK}\n"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
        except Exception:
            pass

    emit(lyrics, source if lyrics else "none", matched, kind)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

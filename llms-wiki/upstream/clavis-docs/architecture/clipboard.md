# Spotlight clipboard history

Clavis presents clipboard history through the public `key clipboard` JSON protocol.
key-cli owns capture, cliphist access, payload inspection and wl-copy restoration.
The two projects build and test independently.

## Data flow

- `key clipboard watch` maintains one wl-paste watcher and selects one useful
  representation per event: file lists, supported images, plain text, Markdown,
  HTML, other text types, then known textual application types.
- cliphist stores the selected bytes and owns deduplication, history limits and
  deletion. There is no Clavis clipboard database or MIME sidecar.
- `ClipboardService` calls `list`, `inspect`, `restore`, `delete` and `clear` using
  argument arrays. It validates `schemaVersion: 1`, command names and operation
  results. Detailed inspection is queued and cached for listed entries.
- `SpotlightClipboardProvider` derives searchable rows from the returned metadata.
  Titles and subtitles may be shortened for display, while restoration uses the
  saved payload in key-cli, never a UI summary.

## Literal text and MIME limits

Spotlight result titles and subtitles use `Text.PlainText`. Markdown, HTML, XML and
JSON source must remain literal text: no rich-text auto-detection, entity decoding,
Markdown renderer or embedded-image extraction. File metadata and image thumbnails
are separate presentations of payloads already classified by key-cli.

The existing `mimeAwareStore` and `mimeRestore` capabilities describe MIME-guided
capture and semantic restoration. New key-cli versions also advertise
`singleRepresentation: true`, `multiMime: false`, `originalMimePreserved: false`.
These additive fields are accepted by the existing capability check; they do not
require a new shell protocol version.

The original offer's MIME metadata is not archived. key-cli classifies decoded
bytes as an image, file list or literal UTF-8 text and restores one appropriate MIME
through wl-copy. Textual source normally returns as `text/plain;charset=utf-8`.
This is not a multi-MIME archive, and Clavis must not describe it as one.

A watcher callback and a subsequent query for a preferred MIME are not atomic.
key-cli retains supported captured stdin on offer-query/read failure and skips
sensitive events, but rapid copies can still replace an offer between queries.

## Default and Details presentations

Settings → Spotlight → Clipboard → Layout persists `spotlightClipboardStyle` as
`default` or `details`. Missing/invalid values select Default. Both use the same
provider, stable entry IDs, history limit and restore/delete/clear service calls.
Default retains its single-click restore behavior. Details uses single-click
selection, Enter to restore and close, Shift+Enter to restore and stay open, and
an explicit restore button. The compact history and preview scroll independently;
small available widths stack history above the preview without changing the preference.
The existing four modes, mode-button animation and shortcuts are retained.

Details creates only the selected content view. Selected inspection moves ahead
of queued background search inspections while the service keeps a single process.
Cached immutable payloads are reused; selecting a file reference or re-entering
Details refreshes its external metadata. Responses are keyed by ID and accepted
only while the entry is listed. Leaving Details destroys its heavy content and
cancels its pending request; an already running inspection can finish in the service.

Both presentations keep text literal. Details uses the existing `searchText` as
the untouched first 262144 Unicode code points, including indentation and empty
lines, with explicit truncation feedback. `characterCount` and `textLineCount`
refer to the complete decoded text; the latter includes empty and trailing lines,
counting CRLF as one separator and lone CR/LF as one each. Payload `byteSize` is
the stored representation's byte count. Older inspect responses omit unknown
statistics and use a Preview label when completeness cannot be established.
Selection copying is ordinary text copying; restoration always reads the complete
cliphist payload, including content beyond the preview limit.

Image payload previews use cached original bytes. Image file references remain
file references and load only supported local raster images after metadata inspection.
Qt Image uses aspect-fit and frame zero: static display of GIF/WebP never rewrites
animation bytes. Decode sizing is bounded and settled after resizing; unsupported,
damaged or excessive images show an unavailable state. No SVG, remote resource,
text-embedded URL, media player or document renderer is loaded.

File metadata describes the external file at inspection time, not a copy-time
snapshot. `files[].byteSize` with `sizeKnown` describes the referenced regular
file; top-level `byteSize` describes the URI payload. Directories are never scanned
for total size. Missing, unreadable and remote references have explicit states.
`modifiedTime` is Unix seconds, matching Files, and is adapted to JavaScript
milliseconds only for display. No copying timestamp or source application is inferred.

## File theme icons

Files results and Clipboard Details share `FileThemeIcon`, which resolves semantic
MIME names using Quickshell's current icon theme. Candidates are bounded: specific
MIME, MIME-family generic, then `text-x-generic`; directories use `folder`. Missing
names and resource-load failures both advance the fallback, ending in a Material
Symbol. Entry/theme changes reset failures. Theme icons keep their native colors
and normal small-resource cache; application icon resolution is separate.

Clipboard `files[].themeIcon` is a theme name, unlike its existing Material Symbol
`icon`. Old backends without the new field still use MIME/generic fallbacks.
Single files without a content preview show a centered icon and literal filename,
with the existing metadata and restore action below. A failed image-file preview
can fall back to that overview while retaining its unavailable message. Missing,
unreadable and remote-file states remain in metadata. Multiple files retain the
virtualized list; Default and the compact Details history retain their existing
appearance. This adds no content readers, media tools, file actions or background work.

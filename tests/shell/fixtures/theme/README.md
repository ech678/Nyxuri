# Theme fixtures (P4 theme contract)

Deterministic inputs and captured engine outputs backing the theme contract
tests. Regenerate only with the commands below so fixtures stay reproducible.

## Images

FFmpeg-generated, no external sources:

    ffmpeg -y -f lavfi -i "gradients=s=256x256:c0=0x3A6EA5:c1=0xC4553B:x0=0:y0=0:x1=256:y1=256:d=1" -frames:v 1 images/gradient.png
    ffmpeg -y -f lavfi -i "color=s=64x64:c=0x88D0EC:d=1" -frames:v 1 images/solid.png

## golden/*.json

`noctalia theme <image> --scheme <s> --both -o <file>` captured with Noctalia
5.2.1 (MIT). These are the golden reference for palette-contract tests; the
contract tests compare our engine output against them and skip with a note
when the reference engine is unavailable.

| file | image | scheme | note |
| --- | --- | --- | --- |
| solid-tonal-spot.json | solid | m3-tonal-spot | 50 M3 keys byte-identical to matugen `scheme-tonal-spot` |
| gradient-tonal-spot.json | gradient | m3-tonal-spot | extraction ±1/channel vs matugen |
| solid-content.json | solid | m3-content | 3 `on_*_container` keys diverge from matugen `scheme-content` (Noctalia tone post-processing) |
| gradient-content.json | gradient | m3-content | same divergence + extraction noise |

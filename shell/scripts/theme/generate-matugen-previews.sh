#!/usr/bin/env bash
# Per-scheme preview palettes for the dashboard theme picker. Runs one matugen
# extraction per scheme variant against a fixed source and collects the
# results into nyxuri/scheme-previews.json. Invoked detached by
# generate-matugen-colors.sh so the scheme-switch path never waits on it; also
# safe to run by hand. Best effort: any single-scheme failure is skipped, the
# picker falls back to the live palette.
set -uo pipefail

mode=dark
image_path=""
source_color=""

usage() {
    printf 'Usage: %s (--image PATH | --color HEX) [--mode dark|light]\n' "$0" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image) [[ $# -ge 2 ]] || { usage; exit 2; }; image_path=$2; shift 2 ;;
        --color) [[ $# -ge 2 ]] || { usage; exit 2; }; source_color=$2; shift 2 ;;
        --mode)  [[ $# -ge 2 ]] || { usage; exit 2; }; mode=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

if [[ -n "$image_path" && -n "$source_color" ]] \
    || [[ -z "$image_path" && -z "$source_color" ]]; then
    usage
    exit 2
fi
if [[ "$mode" != dark && "$mode" != light ]]; then
    usage
    exit 2
fi
generated_home="${NYXURI_SHELL_GENERATED_HOME:-}"
if [[ -z "$generated_home" ]]; then
    printf 'generated home is required (NYXURI_SHELL_GENERATED_HOME)\n' >&2
    exit 1
fi
if ! command -v matugen >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    exit 0
fi
if ! command -v mktemp >/dev/null 2>&1; then
    exit 0
fi
runtime_home="${TMPDIR:-/tmp}/nyxuri-previews"
mkdir -p -- "$runtime_home"
work=$(mktemp -d "$runtime_home/previews.XXXXXX")
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT

accepted=()

# matugen scheme values; the Noctalia-facing names map 1:1 for the m3-* family
# (see the scheme contract in the P4 ledger).
for scheme in scheme-tonal-spot scheme-content scheme-expressive scheme-fidelity \
              scheme-fruit-salad scheme-monochrome scheme-neutral scheme-rainbow scheme-vibrant; do
    common_args=(--mode "$mode" --type "$scheme" --json hex -q)
    if [[ -n "$image_path" ]]; then
        matugen --source-color-index 0 image "$image_path" "${common_args[@]}" \
            > "$work/$scheme.json" 2>/dev/null || continue
    else
        matugen color hex "$source_color" "${common_args[@]}" \
            > "$work/$scheme.json" 2>/dev/null || continue
    fi
    [[ -s "$work/$scheme.json" ]] || continue
    if ! jq -e '.colors | (type == "object" and (keys | length == 50))' "$work/$scheme.json" >/dev/null 2>&1; then
        continue
    fi
    reduced="$work/$scheme.reduced.json"
    if ! jq -c --arg id "$scheme" '{($id): (.colors | with_entries(.value = .value.default.color))}' \
            "$work/$scheme.json" > "$reduced" 2>/dev/null; then
        continue
    fi
    accepted+=("$reduced")
done

if [[ ${#accepted[@]} -eq 0 ]]; then
    exit 0
fi
mkdir -p -- "$generated_home/nyxuri"
target="$generated_home/nyxuri/scheme-previews.json"
staged="$generated_home/nyxuri/.scheme-previews.tmp"
if jq -S -s 'add' "${accepted[@]}" > "$staged" 2>/dev/null; then
    mv -f -- "$staged" "$target"
else
    rm -f -- "$staged"
fi

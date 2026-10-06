#!/usr/bin/env bash
# Palette generation: matugen is a pure color-extraction slot (P4 contract).
# One run emits every mode as JSON; this script assembles the two contract
# files and does no template rendering — application templates are rendered
# by the in-shell TemplateService from the written palettes.
#
# Outputs (under $generated_home/nyxuri/):
#   colors.json         50-key snake_case M3 palette for the active mode
#                       (the shell's hot-load contract, byte-compatible with
#                       the retired internal Tera template)
#   palette-modes.json  dark+light palettes plus source color; input for the
#                       Noctalia palette mirror and template rendering
#
# Status protocol on stdout (schemaVersion 1): core-ready | core-error.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mode=dark
scheme="scheme-tonal-spot"
image_path=""
source_color=""
dry_run=false
# assets shipped with @CLAVIS_GENERATED_HOME@-style placeholders once; since the
# Tera render path retired there is nothing to substitute — the shell always
# passes the real directory and the fallbacks keep manual CLI use working.
generated_home="${NYXURI_SHELL_GENERATED_HOME:-${CLAVIS_GENERATED_HOME:-}}"

usage() {
    printf 'Usage: %s (--image PATH | --color HEX) [--mode dark|light] [--scheme SCHEME] [--generated-home DIR] [--dry-run]\n' "$0" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            image_path=$2
            shift 2
            ;;
        --color)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            source_color=$2
            shift 2
            ;;
        --mode)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            mode=$2
            shift 2
            ;;
        --scheme)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            scheme=$2
            shift 2
            ;;
        --generated-home)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            generated_home=$2
            shift 2
            ;;
        --dry-run)
            dry_run=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
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
if [[ -z "$generated_home" ]]; then
    printf 'generated home is required (--generated-home or NYXURI_SHELL_GENERATED_HOME)\n' >&2
    exit 2
fi
if ! command -v matugen >/dev/null 2>&1; then
    printf 'matugen is required for palette extraction but was not found in PATH\n' >&2
    exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
    printf 'jq is required to assemble palettes but was not found in PATH\n' >&2
    exit 1
fi

runtime_dir=$(mktemp -d "${TMPDIR:-/tmp}/nyxuri-matugen.XXXXXX")
cleanup() { rm -rf -- "$runtime_dir"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM

common_args=(--mode "$mode" --type "$scheme" --json hex -q)
if [[ -n "$image_path" ]]; then
    matugen --source-color-index 0 image "$image_path" "${common_args[@]}" \
        > "$runtime_dir/palette.json" 2> "$runtime_dir/log"
else
    matugen color hex "$source_color" "${common_args[@]}" \
        > "$runtime_dir/palette.json" 2> "$runtime_dir/log"
fi

if ! jq -e '.colors | (type == "object" and (keys | length == 50) and .source_color)' \
    "$runtime_dir/palette.json" >/dev/null 2>&1; then
    printf 'matugen returned an unexpected palette shape\n' >&2
    tail -c 2000 -- "$runtime_dir/log" >&2 || true
    exit 1
fi

event() {
    jq -nc --arg event "$1" --arg error "${2:-}" '{schemaVersion: 1, event: $event, error: ($error | gsub("\u001b\\[[0-9;]*[A-Za-z]"; ""))}'
}

assemble() {
    jq -S '.colors | with_entries(.value = .value.default.color)' "$runtime_dir/palette.json"
}

assemble_modes() {
    jq -S --arg mode "$mode" --arg scheme "$scheme" '
        {schemaVersion: 1,
         mode: $mode,
         scheme: $scheme,
         source_color: .colors.source_color.default.color,
         dark: (.colors | with_entries(.value = .value.dark.color)),
         light: (.colors | with_entries(.value = .value.light.color))}' \
        "$runtime_dir/palette.json"
}

if [[ "$dry_run" == true ]]; then
    event core-ready
    exit 0
fi

target_dir="$generated_home/nyxuri"
mkdir -p -- "$target_dir"
if ! assemble > "$target_dir/.colors.tmp" 2>"$runtime_dir/assemble.log"; then
    rm -f -- "$target_dir/.colors.tmp"
    event core-error "$(tail -c 2000 "$runtime_dir/assemble.log" 2>/dev/null || echo "palette assembly failed")"
    exit 1
fi
if ! assemble_modes > "$target_dir/.palette-modes.tmp" 2>>"$runtime_dir/assemble.log"; then
    rm -f -- "$target_dir/.colors.tmp" "$target_dir/.palette-modes.tmp"
    event core-error "$(tail -c 2000 "$runtime_dir/assemble.log" 2>/dev/null || echo "palette assembly failed")"
    exit 1
fi
mv -f -- "$target_dir/.colors.tmp" "$target_dir/colors.json"
mv -f -- "$target_dir/.palette-modes.tmp" "$target_dir/palette-modes.json"
event core-ready

# Detached preview sweep: nine extra matugen runs must never sit on the
# scheme-switch path the user is waiting on. Best effort; the picker falls
# back to the live palette while the cache is missing or stale.
NYXURI_SHELL_GENERATED_HOME="$generated_home" \
    bash "$script_dir/generate-matugen-previews.sh" \
    ${image_path:+--image "$image_path"} ${source_color:+--color "$source_color"} \
    --mode "$mode" >/dev/null 2>&1 & disown

event finished

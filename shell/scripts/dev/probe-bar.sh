#!/usr/bin/env bash
# B8.6 bar runtime probe.
#
# Loads plugins/bar/BarContent.qml in an isolated temp shell and reports the
# evaluated lane geometry plus every active Loader's status. This is the
# runtime evidence the string-assertion tests cannot give: NaN layout chains,
# compiled-empty widgets and TypeError storms all show up here. It walks all
# six corner styles, the four borderless modes and the self-hiding widget lane
# (Media with no track) in both capsule paths.
#
# Usage:
#   probe-bar.sh [--json] [--session|--weston]
#
# Modes: auto (weston > current Wayland session), --session runs a second
# no-window qs on the developer's live compositor, --weston starts a private
# headless compositor. No Wayland at all exits 2 (skip), because Quickshell's
# services need a panel-window backend even for this windowless harness.
#
# Exit: 0 pass, 1 layout/log failure, 2 skipped (tool or compositor missing), 3 setup failure.
set -uo pipefail

script_dir=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
shell_root=$(CDPATH='' cd -- "${script_dir}/../.." && pwd)

json_mode=false
mode=auto
for arg in "$@"; do
    case ${arg} in
        --json) json_mode=true ;;
        --session) mode=session ;;
        --weston) mode=weston ;;
        -h | --help)
            sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            printf 'error: unknown option: %s\n' "${arg}" >&2
            exit 2
            ;;
    esac
done

skip() {
    printf 'SKIP: %s\n' "$1" >&2
    exit 2
}

command -v qs >/dev/null 2>&1 || skip "Quickshell qs is not installed"
command -v dbus-run-session >/dev/null 2>&1 || skip "dbus-run-session is not installed"
command -v python3 >/dev/null 2>&1 || skip "python3 is not installed"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/nyxuri-probe-bar.XXXXXX") || exit 3
runtime="${tmp}/runtime"
mkdir -p "${runtime}" "${tmp}/home" "${tmp}/config" "${tmp}/data" "${tmp}/state" "${tmp}/cache"
chmod 700 "${runtime}"

qs_pid=""
weston_pid=""

# shellcheck disable=SC2329  # invoked through trap
cleanup() {
    trap - EXIT INT TERM
    if [[ -n ${qs_pid} ]]; then
        kill -- -"${qs_pid}" 2>/dev/null || kill "${qs_pid}" 2>/dev/null || true
    fi
    if [[ -n ${weston_pid} ]]; then
        kill -- -"${weston_pid}" 2>/dev/null || kill "${weston_pid}" 2>/dev/null || true
    fi
    rm -rf -- "${tmp}"
}
trap cleanup EXIT INT TERM

cp -a "${shell_root}" "${tmp}/shell" || exit 3
cp "${shell_root}/scripts/dev/probe-bar.qml" "${tmp}/shell/shell.qml" || exit 3

export HOME="${tmp}/home"
export XDG_CONFIG_HOME="${tmp}/config"
export XDG_DATA_HOME="${tmp}/data"
export XDG_STATE_HOME="${tmp}/state"
export XDG_CACHE_HOME="${tmp}/cache"
export QML_IMPORT_PATH="${tmp}/shell/ui/shapes${QML_IMPORT_PATH:+:${QML_IMPORT_PATH}}"
export QML2_IMPORT_PATH="${tmp}/shell/ui/shapes${QML2_IMPORT_PATH:+:${QML2_IMPORT_PATH}}"
export NYXURI_PROBE_SHELL="${tmp}/shell"
export QT_QPA_PLATFORMTHEME=""
unset NIRI_SOCKET DISPLAY

if [[ ${mode} == auto ]]; then
    if command -v weston >/dev/null 2>&1; then
        mode=weston
    elif [[ -n ${WAYLAND_DISPLAY:-} ]]; then
        mode=session
    else
        skip "no Wayland compositor (install weston or run --session in a graphical session)"
    fi
fi

case ${mode} in
    weston)
        command -v weston >/dev/null 2>&1 || skip "weston is not installed"
        export XDG_RUNTIME_DIR="${runtime}"
        export WAYLAND_DISPLAY=nyxuri-probe-bar
        export QT_QPA_PLATFORM=wayland
        export QT_QUICK_BACKEND=software
        setsid weston --backend=headless --renderer=pixman --no-config \
            --socket=nyxuri-probe-bar --idle-time=0 >"${tmp}/weston.log" 2>&1 &
        weston_pid=$!
        for _ in $(seq 1 100); do
            [[ -e "${runtime}/nyxuri-probe-bar" ]] && break
            kill -0 "${weston_pid}" 2>/dev/null || {
                printf 'error: private weston did not start\n' >&2
                tail -n 20 "${tmp}/weston.log" >&2 || true
                exit 3
            }
            sleep 0.1
        done
        ;;
    session)
        [[ -n ${WAYLAND_DISPLAY:-} ]] || skip "no WAYLAND_DISPLAY for --session"
        export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
        ;;
esac

setsid dbus-run-session -- qs -p "${tmp}/shell" >"${tmp}/qs.log" 2>&1 &
qs_pid=$!

ipc() {
    qs -p "${tmp}/shell" ipc call bar-probe "$@" 2>/dev/null
}

ready=false
for _ in $(seq 1 150); do
    if [[ $(ipc ping) == PONG ]]; then
        ready=true
        break
    fi
    if ! kill -0 "${qs_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.1
done
if [[ ${ready} != true ]]; then
    printf 'error: bar probe did not come up (mode=%s)\n' "${mode}" >&2
    tail -n 40 "${tmp}/qs.log" >&2 || true
    exit 3
fi

layouts="${tmp}/layouts.jsonl"
borderless="${tmp}/borderless.tsv"
media_hidden="${tmp}/media-hidden.tsv"
: >"${layouts}"
: >"${borderless}"
: >"${media_hidden}"
# Wait until the harness has loaded BarContent against a ready settings store.
for _ in $(seq 1 150); do
    if ipc layout 2>/dev/null | grep -q '"ready":true'; then
        break
    fi
    sleep 0.1
done
for style in 0 1 2 3 4 5; do
    if ! ipc cornerStyle "${style}" >/dev/null; then
        printf 'error: could not set cornerStyle %s\n' "${style}" >&2
        exit 3
    fi
    if ! ipc reload >/dev/null; then
        printf 'error: could not reload the bar for cornerStyle %s\n' "${style}" >&2
        exit 3
    fi
    sleep 0.6
    if ! ipc layout >>"${layouts}"; then
        printf 'error: layout probe failed for cornerStyle %s\n' "${style}" >&2
        exit 3
    fi
    printf '\n' >>"${layouts}"
done

# Borderless modes share the group chrome. Exercise them on a non-material
# style so the segmented 1px border and transparent branch actually render.
ipc cornerStyle 1 >/dev/null || true
for border_mode in pills separated segmented transparent; do
    if ! ipc borderless "${border_mode}" >/dev/null; then
        printf 'error: could not set borderless %s\n' "${border_mode}" >&2
        exit 3
    fi
    ipc reload >/dev/null || true
    sleep 0.5
    printf '%s\t%s\n' "${border_mode}" "$(ipc layout)" >>"${borderless}"
done
ipc borderless pills >/dev/null || true

# Self-hiding widget contract: a lane whose only widget reports
# barWidgetVisible=false must collapse to zero in both the plain and material
# capsule paths (commit 14a56e1).
for style in 1 3; do
    ipc cornerStyle "${style}" >/dev/null || true
    if ! ipc scene mediaOnly >/dev/null; then
        printf 'error: could not switch to the media-only layout\n' >&2
        exit 3
    fi
    ipc reload >/dev/null || true
    sleep 0.6
    printf '%s\t%s\n' "${style}" "$(ipc layout)" >>"${media_hidden}"
done
ipc cornerStyle 1 >/dev/null || true
ipc scene default >/dev/null || true
ipc reload >/dev/null || true
sleep 0.5

osd_state=""
if ipc osd volume >/dev/null 2>&1; then
    sleep 0.2
    osd_state=$(ipc layout 2>/dev/null || true)
    ipc osd "" >/dev/null 2>&1 || true
fi

keyboard_osd_state=""
if ipc keyboardFlip >/dev/null 2>&1; then
    sleep 0.2
    keyboard_osd_state=$(ipc layout 2>/dev/null || true)
fi

island_off_state=""
if ipc islandEnabled false >/dev/null 2>&1; then
    ipc reload >/dev/null 2>&1 || true
    sleep 0.5
    island_off_state=$(ipc layout 2>/dev/null || true)
    ipc islandEnabled true >/dev/null 2>&1 || true
    ipc reload >/dev/null 2>&1 || true
    sleep 0.5
fi

python3 - "${layouts}" "${borderless}" "${media_hidden}" "${tmp}/qs.log" "${json_mode}" "${mode}" "${osd_state}" "${keyboard_osd_state}" "${island_off_state}" <<'PY'
import json
import re
import sys

(layouts_path, borderless_path, media_hidden_path, log_path, json_mode, mode,
 osd_state, keyboard_osd_state, island_off_state) = sys.argv[1:10]


def load_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            key, _, payload = line.partition("\t")
            rows.append((key, json.loads(payload)))
    return rows


def load_layouts(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


layouts = load_layouts(layouts_path)
borderless = load_tsv(borderless_path)
media_hidden = load_tsv(media_hidden_path)
try:
    with open(log_path, encoding="utf-8", errors="replace") as handle:
        log = handle.read()
except OSError:
    log = ""

patterns = (
    r"TypeError", r"ReferenceError", r"is not a type", r"compiled empty",
    r"Cannot assign", r"is not defined", r"Unable to assign",
)
hits = []
for pattern in patterns:
    for match in re.finditer(pattern, log):
        line = log.count("\n", 0, match.start()) + 1
        snippet = log.splitlines()[line - 1].strip()
        hits.append({"pattern": pattern, "line": line, "text": snippet[:300]})
        if len(hits) >= 12:
            break

osd = json.loads(osd_state) if osd_state.strip() else {}
osd_ok = osd.get("islandState") == "osd" and (osd.get("island") or {}).get("width", 0) > 0
keyboard_osd = json.loads(keyboard_osd_state) if keyboard_osd_state.strip() else {}
keyboard_osd_ok = keyboard_osd.get("islandState") == "osd"
island_off = json.loads(island_off_state) if island_off_state.strip() else {}
island_off_ok = bool(island_off) and island_off.get("island") is None and not island_off.get("lanes", {}).get("middle")

# A media-only lane whose widget reports barWidgetVisible=false must evaluate
# to zero width. Non-zero means the old 10px capsule padding came back.
media_cases = []
media_ok = len(media_hidden) == 2
for style, entry in media_hidden:
    geometry = entry.get("geometry", {})
    left_width = geometry.get("leftWidth")
    center_width = geometry.get("centerWidth")
    lane_ok = (entry.get("ok") is True
               and isinstance(left_width, (int, float)) and abs(left_width) <= 0.5
               and isinstance(center_width, (int, float)) and abs(center_width) <= 0.5
               and entry.get("island") is None)
    media_cases.append({
        "cornerStyle": style,
        "leftWidth": left_width,
        "centerWidth": center_width,
        "ok": lane_ok,
    })
    media_ok = media_ok and lane_ok

borderless_modes = [key for key, _ in borderless]
borderless_ok = (borderless_modes == ["pills", "separated", "segmented", "transparent"]
                 and all(entry.get("ok") and entry.get("borderless") == key
                         for key, entry in borderless))

ok = (len(layouts) == 6 and all(entry.get("ok") for entry in layouts) and not hits
      and borderless_ok and media_ok and osd_ok and keyboard_osd_ok and island_off_ok)
report = {
    "ok": ok,
    "mode": mode,
    "styles": layouts,
    "borderless": {
        "ok": borderless_ok,
        "modes": borderless_modes,
    },
    "mediaHidden": {
        "ok": media_ok,
        "cases": media_cases,
    },
    "osd": {
        "ok": osd_ok,
        "islandState": osd.get("islandState", ""),
    },
    "keyboardOsd": {
        "ok": keyboard_osd_ok,
        "islandState": keyboard_osd.get("islandState", ""),
    },
    "islandOff": {
        "ok": island_off_ok,
        "middle": island_off.get("lanes", {}).get("middle", []),
    },
    "logErrors": hits,
}
if json_mode == "true":
    print(json.dumps(report, separators=(",", ":")))
else:
    print(json.dumps(report, indent=2))
sys.exit(0 if ok else 1)
PY
status=$?
if ((status != 0)); then
    printf 'probe-bar: failed; qs log tail:\n' >&2
    tail -n 40 "${tmp}/qs.log" >&2 || true
fi
exit "${status}"

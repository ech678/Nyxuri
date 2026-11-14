#!/usr/bin/env bash
# B8.6 bar runtime probe.
#
# Loads plugins/bar/BarContent.qml in an isolated temp shell and reports the
# evaluated lane geometry plus every active Loader's status. This is the
# runtime evidence the string-assertion tests cannot give: NaN layout chains,
# compiled-empty widgets and TypeError storms all show up here. It walks all
# six corner styles, the four borderless modes, the self-hiding widget lane
# (Media with no track) in both capsule paths, the tray surface (fake
# StatusNotifierItems -> pin/unpin -> overflow arrow -> persisted config),
# and the B9.7 settled-settings sweep (background/autohide/divider/util
# buttons/resources/number presets/screen filter + reservation round trip).
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
command -v dbus-daemon >/dev/null 2>&1 || skip "dbus-daemon is not installed"
command -v python3 >/dev/null 2>&1 || skip "python3 is not installed"
python3 -c "import dbus, gi" >/dev/null 2>&1 || skip "python3 dbus/gi is required for the tray probe"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/nyxuri-probe-bar.XXXXXX") || exit 3
runtime="${tmp}/runtime"
mkdir -p "${runtime}" "${tmp}/home" "${tmp}/config" "${tmp}/data" "${tmp}/state" "${tmp}/cache"
chmod 700 "${runtime}"

qs_pid=""
weston_pid=""
sni_pid=""
bus_pid=""

# shellcheck disable=SC2329  # invoked through trap
cleanup() {
    trap - EXIT INT TERM
    if [[ -n ${qs_pid} ]]; then
        kill -- -"${qs_pid}" 2>/dev/null || kill "${qs_pid}" 2>/dev/null || true
    fi
    if [[ -n ${sni_pid} ]]; then
        kill "${sni_pid}" 2>/dev/null || true
    fi
    if [[ -n ${weston_pid} ]]; then
        kill -- -"${weston_pid}" 2>/dev/null || kill "${weston_pid}" 2>/dev/null || true
    fi
    if [[ -n ${bus_pid} ]]; then
        kill "${bus_pid}" 2>/dev/null || true
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

setsid dbus-daemon --session --fork --print-address=1 --print-pid=1 >"${tmp}/bus.txt" || {
    printf 'error: could not start a private session bus\n' >&2
    exit 3
}
DBUS_SESSION_BUS_ADDRESS=$(sed -n 1p "${tmp}/bus.txt")
export DBUS_SESSION_BUS_ADDRESS
bus_pid=$(sed -n 2p "${tmp}/bus.txt")
[[ -n ${DBUS_SESSION_BUS_ADDRESS} && -n ${bus_pid} ]] || {
    printf 'error: private session bus printed no address/pid\n' >&2
    exit 3
}

setsid qs -p "${tmp}/shell" >"${tmp}/qs.log" 2>&1 &
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
island_restored_state=""
island_migration=""
idle_face_state=""
if ipc islandInLayout false >/dev/null 2>&1; then
    ipc reload >/dev/null 2>&1 || true
    sleep 0.5
    island_off_state=$(ipc layout 2>/dev/null || true)
    island_migration=$(ipc islandLayoutMigration 2>/dev/null || true)
    ipc islandInLayout true >/dev/null 2>&1 || true
    ipc reload >/dev/null 2>&1 || true
    sleep 0.8
    island_restored_state=$(ipc layout 2>/dev/null || true)
    for _ in $(seq 1 20); do
        idle_face_state=$(ipc idleFace 2>/dev/null || true)
        [[ ${idle_face_state} == *'"found":true'* ]] && break
        sleep 0.1
    done
    idle_face_no_avatar=""
    if ipc islandAvatar false >/dev/null 2>&1; then
        sleep 0.4
        idle_face_no_avatar=$(ipc idleFace 2>/dev/null || true)
        ipc islandAvatar true >/dev/null 2>&1 || true
        sleep 0.4
    fi
fi

# B9.2 status cluster: fixed 26px slots, then two fake peripherals (one low,
# one critical) so the repeat slots have runtime evidence without hardware.
system_icons_state=""
system_icons_fake=""
system_icons_reset=""
if ipc systemIcons >/dev/null 2>&1; then
    sleep 0.2
    system_icons_state=$(ipc systemIcons 2>/dev/null || true)
    ipc systemIconsFakeDevices >/dev/null 2>&1 || true
    sleep 0.3
    system_icons_fake=$(ipc systemIcons 2>/dev/null || true)
    ipc systemIconsResetDevices >/dev/null 2>&1 || true
    sleep 0.3
    system_icons_reset=$(ipc systemIcons 2>/dev/null || true)
fi

# B9.6 visual baseline: right-click style chain (store write -> BarGroup
# contentColor binding -> widget), the fixed-slot workspaces model, and the
# island middle-frame hug (+8 on float, -4 on the plain style) with the
# capsule going transparent on the plain centre-only bar.
b96_override=""
b96_reset=""
b96_hug_float=""
b96_hug_plain=""
if ipc cornerStyle 1 >/dev/null 2>&1; then
    sleep 0.3
    ipc scene default >/dev/null 2>&1 || true
    sleep 0.5
    if ipc b96Style true >/dev/null 2>&1; then
        sleep 0.4
        b96_override=$(ipc b96Dump 2>/dev/null || true)
        ipc b96Style false >/dev/null 2>&1 || true
        sleep 0.3
        b96_reset=$(ipc b96Dump 2>/dev/null || true)
    fi
    if ipc scene centerIsland >/dev/null 2>&1; then
        sleep 0.8
        b96_hug_float=$(ipc b96Dump 2>/dev/null || true)
        ipc cornerStyle 0 >/dev/null 2>&1 || true
        sleep 0.5
        b96_hug_plain=$(ipc b96Dump 2>/dev/null || true)
        ipc cornerStyle 1 >/dev/null 2>&1 || true
    fi
    ipc scene default >/dev/null 2>&1 || true
fi

# B9.7 settled-settings sweep: every key that left §1.7 gets one runtime
# proof (bridge passthrough + the consumer actually reacting), then resets.
b97_baseline=""
b97_bg_off=""
b97_divider=""
b97_util_on=""
b97_util_off=""
b97_res_on=""
b97_res_off=""
b97_han=""
b97_roman=""
b97_screen_named=""
b97_screen_empty=""
b97_persisted=false
if ipc cornerStyle 1 >/dev/null 2>&1; then
    ipc scene default >/dev/null 2>&1 || true
    ipc reload >/dev/null 2>&1 || true
    sleep 0.5
    b97_baseline=$(ipc b97Dump 2>/dev/null || true)
    # Show background: Float + non-material paints colLayer0; off -> transparent.
    if ipc b97Set barShowBackground false >/dev/null 2>&1; then
        sleep 0.4
        b97_bg_off=$(ipc b97Dump 2>/dev/null || true)
        ipc b97Set barShowBackground true >/dev/null 2>&1 || true
        sleep 0.3
    fi
    # Divider: the space style reads the settled width (end4 spinbox).
    if ipc scene divisorLeft >/dev/null 2>&1; then
        sleep 0.5
        ipc b97Set barDividerStyle '"space"' >/dev/null 2>&1 || true
        ipc b97Set barDividerSpacing 20 >/dev/null 2>&1 || true
        sleep 0.4
        b97_divider=$(ipc b97Dump 2>/dev/null || true)
        ipc b97Set barDividerStyle '"rect"' >/dev/null 2>&1 || true
        ipc b97Set barDividerSpacing 4 >/dev/null 2>&1 || true
        ipc scene default >/dev/null 2>&1 || true
        sleep 0.4
    fi
    # Util buttons: material path exposes tooltips; the keyboard slot must
    # disappear with its settled toggle.
    if ipc cornerStyle 3 >/dev/null 2>&1; then
        ipc scene utilOnly >/dev/null 2>&1 || true
        ipc reload >/dev/null 2>&1 || true
        sleep 0.8
        ipc b97Set barShowKeyboardToggle true >/dev/null 2>&1 || true
        sleep 0.4
        b97_util_on=$(ipc b97Dump 2>/dev/null || true)
        ipc b97Set barShowKeyboardToggle false >/dev/null 2>&1 || true
        sleep 0.4
        b97_util_off=$(ipc b97Dump 2>/dev/null || true)
        ipc b97Set barShowKeyboardToggle false >/dev/null 2>&1 || true
        ipc scene default >/dev/null 2>&1 || true
        ipc cornerStyle 1 >/dev/null 2>&1 || true
        ipc reload >/dev/null 2>&1 || true
        sleep 0.6
    fi
    # Resources: the swap meter follows its settled toggle (shipped default
    # is off, so flip it on first and restore the default after).
    if ipc scene monitorOnly >/dev/null 2>&1; then
        sleep 0.8
        ipc b97Set barShowSwap true >/dev/null 2>&1 || true
        sleep 0.5
        b97_res_on=$(ipc b97Dump 2>/dev/null || true)
        ipc b97Set barShowSwap false >/dev/null 2>&1 || true
        sleep 0.5
        b97_res_off=$(ipc b97Dump 2>/dev/null || true)
        ipc scene default >/dev/null 2>&1 || true
        ipc reload >/dev/null 2>&1 || true
        sleep 0.6
    fi
    # Number presets: the workspace labels re-render through the bridge.
    if ipc b97Set barWorkspaceNumberStyle '"han"' >/dev/null 2>&1; then
        sleep 0.5
        b97_han=$(ipc b97Dump 2>/dev/null || true)
        ipc b97Set barWorkspaceNumberStyle '"roman"' >/dev/null 2>&1 || true
        sleep 0.5
        b97_roman=$(ipc b97Dump 2>/dev/null || true)
        ipc b97Set barWorkspaceNumberStyle '"normal"' >/dev/null 2>&1 || true
        sleep 0.4
    fi
    # Screen filter: unknown name must fall back to every screen (one-screen
    # harness proves the fallback path, not the multi-monitor filtering).
    if ipc b97Set barScreenList '["probe-no-such-screen"]' >/dev/null 2>&1; then
        sleep 0.4
        b97_screen_named=$(ipc layout 2>/dev/null || true)
        ipc b97Set barScreenList '[]' >/dev/null 2>&1 || true
        sleep 0.4
        b97_screen_empty=$(ipc layout 2>/dev/null || true)
    fi
    b97_persisted=false
    if grep -q 'showBackground' "${tmp}/config/nyxuri/config.toml" 2>/dev/null; then
        b97_persisted=true
    fi
fi

# Tray surface (B9.1): publish fake StatusNotifierItems on the probe's own
# session bus, then let the widget pin/unpin against the real store.
tray_initial=""
tray_hidden=""
tray_closed=""
tray_reset=""
tray_persisted=false
tray_skip_reason=""
sni_log="${tmp}/fake-sni.log"
if python3 "${script_dir}/fake-sni.py" 3 >"${sni_log}" 2>&1 &
then
    sni_pid=$!
    tray_ready=false
    for _ in $(seq 1 100); do
        if grep -q '^READY' "${sni_log}" 2>/dev/null; then
            tray_ready=true
            break
        fi
        kill -0 "${sni_pid}" 2>/dev/null || break
        sleep 0.1
    done
    if [[ ${tray_ready} == true ]]; then
        ipc reload >/dev/null 2>&1 || true
        sleep 1.5
        tray_initial=$(ipc tray 2>/dev/null || true)
        hidden_id=$(python3 - "${tray_initial}" <<'PY' 2>/dev/null || true
import json, sys
data = json.loads(sys.argv[1])
print(data["widget"]["pinned"][0] if data.get("widget") and data["widget"]["pinned"] else "")
PY
)
        if [[ -n ${hidden_id} ]]; then
            ipc trayHide "${hidden_id}" >/dev/null 2>&1 || true
            sleep 0.5
            tray_hidden=$(ipc tray 2>/dev/null || true)
            ipc trayClose >/dev/null 2>&1 || true
            tray_closed=$(ipc tray 2>/dev/null || true)
            if grep -q 'pinnedItems' "${tmp}/config/nyxuri/config.toml" 2>/dev/null; then
                tray_persisted=true
            fi
            ipc trayReset >/dev/null 2>&1 || true
            sleep 0.5
            tray_reset=$(ipc tray 2>/dev/null || true)
        else
            tray_skip_reason="no pinned tray item to hide"
        fi
    else
        tray_skip_reason="fake StatusNotifierItem publisher did not start"
    fi
else
    tray_skip_reason="fake-sni.py could not be launched"
fi

# B9.4 vertical bar: left and right edges, non-material and material capsule
# paths, then a populated centre-only scene. The island is filtered out of the
# vertical layout, so the default scene must evaluate to an empty middle lane.
vertical_file="${tmp}/vertical.tsv"
: >"${vertical_file}"
margins_state=""
for edge in left right; do
    if ! ipc edge "${edge}" >/dev/null; then
        printf 'error: could not switch the bar to the %s edge\n' "${edge}" >&2
        exit 3
    fi
    for style in 1 3; do
        ipc cornerStyle "${style}" >/dev/null || true
        ipc scene default >/dev/null || true
        ipc reload >/dev/null || true
        sleep 0.7
        printf '%s\t%s\tdefault\t%s\n' "${edge}" "${style}" "$(ipc layout)" >>"${vertical_file}"
    done
    ipc cornerStyle 1 >/dev/null || true
    ipc scene centerOnly >/dev/null || true
    ipc reload >/dev/null || true
    sleep 1.4
    printf '%s\t%s\tcenterOnly\t%s\n' "${edge}" "1" "$(ipc layout)" >>"${vertical_file}"
done
# B9.5 margins ride the same pure geometry the window binds.
if ipc edge top >/dev/null 2>&1; then
    ipc cornerStyle 1 >/dev/null 2>&1 || true
    ipc scene default >/dev/null 2>&1 || true
    ipc reload >/dev/null 2>&1 || true
    sleep 0.6
    margins_state=$(ipc margins 2>/dev/null || true)
fi

# B9.4 window phase: load the real Bar.qml (PanelWindow + content) and walk
# top -> left -> right -> bottom -> top. The top->left->top round trip is the
# regression gate for conditional-anchor leftovers: content must return to the
# bar thickness instead of keeping the screen-width/height it had.
window_file="${tmp}/window.tsv"
: >"${window_file}"
if ipc windowMode true >/dev/null 2>&1; then
    window_ready=false
    for _ in $(seq 1 80); do
        if ipc windowDump 2>/dev/null | grep -q '"found":true'; then
            window_ready=true
            break
        fi
        sleep 0.2
    done
    if [[ ${window_ready} == true ]]; then
        for edge in top left right bottom top; do
            ipc edge "${edge}" >/dev/null 2>&1 || true
            sleep 0.9
            printf '%s\t%s\n' "${edge}" "$(ipc windowDump 2>/dev/null || true)" >>"${window_file}"
        done
        # B9.7 autohide: the window reservation must collapse to zero while
        # the toggle is on and restore after it flips back.
        if ipc b97Set barAutoHide true >/dev/null 2>&1; then
            sleep 0.6
            printf 'autohide-on\t%s\n' "$(ipc windowDump 2>/dev/null || true)" >>"${window_file}"
            ipc b97Set barAutoHide false >/dev/null 2>&1 || true
            sleep 0.6
            printf 'autohide-off\t%s\n' "$(ipc windowDump 2>/dev/null || true)" >>"${window_file}"
        fi
    else
        printf 'error: bar window probe did not come up\n' >&2
        exit 3
    fi
    ipc windowMode false >/dev/null 2>&1 || true
    ipc edge top >/dev/null 2>&1 || true
fi

python3 - "${layouts}" "${borderless}" "${media_hidden}" "${tmp}/qs.log" "${json_mode}" "${mode}" "${osd_state}" "${keyboard_osd_state}" "${island_off_state}" "${tray_initial}" "${tray_hidden}" "${tray_closed}" "${tray_reset}" "${tray_persisted}" "${tray_skip_reason}" "${system_icons_state}" "${system_icons_fake}" "${system_icons_reset}" "${island_restored_state}" "${island_migration}" "${idle_face_state}" "${idle_face_no_avatar}" "${vertical_file}" "${margins_state}" "${window_file}" "${b96_override}" "${b96_reset}" "${b96_hug_float}" "${b96_hug_plain}" "${b97_baseline}" "${b97_bg_off}" "${b97_divider}" "${b97_util_on}" "${b97_util_off}" "${b97_res_on}" "${b97_res_off}" "${b97_han}" "${b97_roman}" "${b97_screen_named}" "${b97_screen_empty}" "${b97_persisted}" <<'PY'
import json
import re
import sys

(layouts_path, borderless_path, media_hidden_path, log_path, json_mode, mode,
 osd_state, keyboard_osd_state, island_off_state, tray_initial, tray_hidden,
 tray_closed, tray_reset, tray_persisted, tray_skip_reason, system_icons_state,
 system_icons_fake, system_icons_reset, island_restored_state, island_migration,
 idle_face_state, idle_face_no_avatar, vertical_path, margins_state, window_path,
 b96_override, b96_reset, b96_hug_float, b96_hug_plain, b97_baseline, b97_bg_off,
 b97_divider, b97_util_on, b97_util_off, b97_res_on, b97_res_off, b97_han,
 b97_roman, b97_screen_named, b97_screen_empty, b97_persisted) = sys.argv[1:42]


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
island_off_ok = bool(island_off) and island_off.get("island") is None and not island_off.get("lanes", {}).get("middle") and island_off.get("islandInLayout") is False
island_restored = json.loads(island_restored_state) if island_restored_state.strip() else {}
island_restored_ok = bool(
    island_restored
    and island_restored.get("island") is not None
    and "island" in island_restored.get("lanes", {}).get("middle", [])
    and island_restored.get("islandInLayout") is True
)
island_migration_state = json.loads(island_migration) if island_migration.strip() else {}
seeded = island_migration_state.get("seeded", {})
kept_empty = island_migration_state.get("keptEmpty", {})
legacy_off = island_migration_state.get("legacyOff", {})
island_migration_ok = bool(
    seeded.get("middle") == ["island"]
    and kept_empty.get("middle") == []
    and legacy_off.get("middle") == []
)
idle_face = json.loads(idle_face_state) if idle_face_state.strip() else {}
idle_face_no_avatar = json.loads(idle_face_no_avatar) if idle_face_no_avatar.strip() else {}
idle_face_ok = bool(
    idle_face.get("found") is True
    and idle_face.get("islandState") == "idle"
    and isinstance(idle_face.get("idleWidth"), (int, float))
    and idle_face.get("idleWidth") > 0
)
if idle_face.get("showAvatar") is not False:
    idle_face_ok = idle_face_ok and not (idle_face.get("avatarReady") and idle_face.get("avatarFallback")) and (idle_face.get("avatarReady") or idle_face.get("avatarFallback"))
if idle_face.get("satellite") == "clock":
    idle_face_ok = idle_face_ok and idle_face.get("clockVisible") is True and idle_face.get("clockWidth", 0) > 0 and idle_face.get("clockHeight", 0) > 0
# The avatar is optional: hiding it must drop it from the idle face and shrink
# the pill by exactly its block.
avatar_optional_ok = bool(
    idle_face.get("showAvatar") is True
    and idle_face_no_avatar.get("found") is True
    and idle_face_no_avatar.get("showAvatar") is False
    and idle_face_no_avatar.get("idleWidth", 0) < idle_face.get("idleWidth", 0) - 1
)

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

def load_tsv_rows(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            rows.append((parts[:-1], json.loads(parts[-1])))
    return rows


# B9.4: vertical bar geometry. Both edges, both capsule paths, and a populated
# centre-only scene; the island must be filtered out of the vertical layout.
vertical_rows = load_tsv_rows(vertical_path)
vertical_cases = []
vertical_ok = len(vertical_rows) == 6
widths = {}
for key, entry in vertical_rows:
    if len(key) != 3:
        vertical_ok = False
        continue
    edge, style, scene_name = key
    geometry = entry.get("geometry") or {}
    lanes = entry.get("lanes") or {}
    row_ok = bool(
        entry.get("ok") is True
        and entry.get("vertical") is True
        and entry.get("edge") == edge
        and entry.get("island") is None
        and isinstance(geometry.get("width"), (int, float))
        and geometry.get("width", 0) > 0
        and abs(geometry.get("height", 0) - 1440) <= 1
    )
    if scene_name == "default":
        row_ok = row_ok and not lanes.get("middle") and geometry.get("topHeight", 0) > 0 and geometry.get("bottomHeight", 0) > 0
        widths[(edge, style)] = geometry.get("width")
    else:
        row_ok = row_ok and lanes.get("middle") == ["clock"] and geometry.get("centerHeight", 0) > 0
    vertical_cases.append({
        "edge": edge,
        "cornerStyle": style,
        "scene": scene_name,
        "width": geometry.get("width"),
        "height": geometry.get("height"),
        "centerY": geometry.get("centerY"),
        "centerHeight": geometry.get("centerHeight"),
        "topHeight": geometry.get("topHeight"),
        "bottomHeight": geometry.get("bottomHeight"),
        "middle": lanes.get("middle"),
        "pending": entry.get("pending"),
        "failed": entry.get("failed"),
        "ok": row_ok,
    })
    vertical_ok = vertical_ok and row_ok
# The style boost must reach the vertical axis too (Float adds 5x2).
float_width = widths.get(("left", "1"))
material_width = widths.get(("left", "3"))
boost_ok = bool(
    isinstance(float_width, (int, float)) and isinstance(material_width, (int, float))
    and abs(float_width - material_width - 10) <= 0.01
    and widths.get(("right", "1")) == float_width
    and widths.get(("right", "3")) == material_width
)
vertical_ok = vertical_ok and boost_ok

# B9.5: the outer-margin math every edge shares with the window binds.
margins_report = json.loads(margins_state) if margins_state.strip() else {}
margin_cases = margins_report.get("cases", [])
base_bar_height = margins_report.get("baseBarHeight")
base_vertical_width = margins_report.get("baseVerticalBarWidth")
margin_style = margins_report.get("cornerStyle", 0)
style_extra = 5 if margin_style == 1 else (-6 if margin_style == 2 else (4 if margin_style in (4, 5) else 0))
margin_by_key = {(case.get("edge"), case.get("tier")): case for case in margin_cases}


def margin_box(edge, tier):
    return (margin_by_key.get((edge, tier)) or {}).get("box") or {}


margin_ok = bool(
    len(margin_cases) == 12
    and margin_box("top", 0) == {"top": 0, "bottom": 0, "left": 0, "right": 0}
    and margin_box("top", 12) == {"top": 12, "bottom": 0, "left": 12, "right": 12}
    and margin_box("bottom", 12) == {"top": 0, "bottom": 12, "left": 12, "right": 12}
    and margin_box("left", 24) == {"top": 24, "bottom": 24, "left": 24, "right": 0}
    and margin_box("right", 24) == {"top": 24, "bottom": 24, "left": 0, "right": 24}
    and all(abs(case.get("exclusiveZone", 0) - ((base_vertical_width if case.get("vertical") else base_bar_height) + style_extra + case.get("tier", 0))) <= 0.01 for case in margin_cases)
)

borderless_modes = [key for key, _ in borderless]
borderless_ok = (borderless_modes == ["pills", "separated", "segmented", "transparent"]
                 and all(entry.get("ok") and entry.get("borderless") == key
                         for key, entry in borderless))

tray_initial_state = json.loads(tray_initial) if tray_initial.strip() else {}
tray_hidden_state = json.loads(tray_hidden) if tray_hidden.strip() else {}
tray_closed_state = json.loads(tray_closed) if tray_closed.strip() else {}
tray_reset_state = json.loads(tray_reset) if tray_reset.strip() else {}
tray_items = tray_initial_state.get("items", [])


def tray_widget(state):
    return state.get("widget") or {}


initial_widget = tray_widget(tray_initial_state)
hidden_widget = tray_widget(tray_hidden_state)
closed_widget = tray_widget(tray_closed_state)
reset_widget = tray_widget(tray_reset_state)
tray_ok = bool(
    tray_initial_state
    and tray_hidden_state
    and tray_reset_state
    and len(tray_items) >= 3
    # Fresh config with pin-by-default: nothing overflows, every active item
    # sits in the bar (the passive fake item stays filtered out).
    and initial_widget.get("unpinnedCount") == 0
    and initial_widget.get("overflowVisible") is False
    and initial_widget.get("pinnedCount") >= 2
    # Hiding one item moves it behind the arrow, and the arrow appears.
    and len(hidden_widget.get("unpinned", [])) == 1
    and hidden_widget.get("overflowVisible") is True
    and hidden_widget.get("pinnedCount") == initial_widget.get("pinnedCount", 0) - 1
    # closeOverflowMenu is the outside-click handler's target.
    and closed_widget.get("overflowOpen") is False
    # Pin state lands in the persisted config file.
    and tray_persisted == "true"
    # Reset clears the hidden list again.
    and reset_widget.get("unpinnedCount") == 0
    and reset_widget.get("overflowVisible") is False
)
tray_report = {
    "ok": tray_ok,
    "skipped": tray_skip_reason,
    "items": [item.get("id", "") for item in tray_items],
    "persisted": tray_persisted == "true",
    "initial": initial_widget,
    "hidden": hidden_widget,
    "closed": closed_widget.get("overflowOpen"),
    "reset": reset_widget,
}

# B9.2: every status is a fixed 26px slot. Hidden slots keep their width, only
# `visible` changes, so the group width is exactly slots+spacing+padding.
system_icons = json.loads(system_icons_state) if system_icons_state.strip() else {}
system_icons_fake_state = json.loads(system_icons_fake) if system_icons_fake.strip() else {}
system_icons_reset_state = json.loads(system_icons_reset) if system_icons_reset.strip() else {}

slots = system_icons.get("slots", [])
visible_slots = [slot for slot in slots if slot.get("visible")]
fixed_slots_ok = bool(slots) and all(
    abs(slot.get("width", 0) - 26) <= 0.01 and abs(slot.get("implicitWidth", 0) - 26) <= 0.01
    for slot in slots
)
tooltips_ok = bool(visible_slots) and all(slot.get("tooltip") for slot in visible_slots)
monotonic_ok = all(
    visible_slots[index]["x"] < visible_slots[index + 1]["x"]
    for index in range(len(visible_slots) - 1)
)
spacing = 2 if system_icons.get("material") else 4
padding = 12 if system_icons.get("material") else 4
expected_group_width = len(visible_slots) * 26 + max(0, len(visible_slots) - 1) * spacing + padding
group_width_ok = abs(system_icons.get("groupWidth", 0) - expected_group_width) <= 0.5

fake_slots = [slot for slot in system_icons_fake_state.get("slots", []) if slot.get("visible")]
reset_slots = [slot for slot in system_icons_reset_state.get("slots", []) if slot.get("visible")]
probe_slots = [slot for slot in fake_slots if slot.get("key") == "peripheral"]
peripheral_ok = bool(
    system_icons.get("found") is True
    and system_icons_fake_state.get("found") is True
    and system_icons_reset_state.get("found") is True
    and fixed_slots_ok
    and tooltips_ok
    and monotonic_ok
    and group_width_ok
    # Two injected peripherals (one low, one critical) in fixed slots with
    # tooltips; the notification slot may also appear because the low-battery
    # notification lands in the probe's own notification server.
    and len(probe_slots) == 2
    and all(slot.get("width") == 26 for slot in probe_slots)
    and all(slot.get("tooltip") for slot in probe_slots)
    and sum(1 for slot in probe_slots if slot.get("critical")) == 1
    # Reset removes the injected devices again.
    and not [slot for slot in reset_slots if slot.get("key") == "peripheral"]
)
system_icons_report = {
    "ok": peripheral_ok,
    "material": system_icons.get("material"),
    "groupWidth": system_icons.get("groupWidth"),
    "expectedGroupWidth": expected_group_width,
    "visibleIcons": [slot.get("icon", "") for slot in visible_slots],
    "slotCount": len(slots),
    "fixedSlots": fixed_slots_ok,
    "tooltips": tooltips_ok,
    "monotonic": monotonic_ok,
    "fakeIcons": [slot.get("icon", "") for slot in probe_slots],
    "fakeCritical": sum(1 for slot in probe_slots if slot.get("critical")),
    "fakeVisibleCount": len(fake_slots),
    "resetVisibleCount": len(reset_slots),
    "probeWidths": [slot.get("width") for slot in probe_slots],
}

# B9.4 window geometry: both axes on every edge, plus the exact round trip
# that used to leave the bar invisible after top -> left -> top. B9.7 appends
# the autohide reservation rows to the same file.
window_rows = load_tsv_rows(window_path)
autohide_rows = {row[0][0]: row[1] for row in window_rows if row[0] and str(row[0][0]).startswith("autohide-")}
window_rows = [row for row in window_rows if not (row[0] and str(row[0][0]).startswith("autohide-"))]
window_cases = []
window_ok = len(window_rows) == 5
top_snapshots = []
for key, entry in window_rows:
    edge_name = key[0] if key else ""
    if entry.get("found") is not True:
        window_ok = False
        window_cases.append({"edge": edge_name, "found": False, "ok": False})
        continue
    expected = entry.get("expected") or {}
    window_box = entry.get("window") or {}
    content_box = entry.get("content") or {}
    vertical = entry.get("vertical") is True
    bar_height = expected.get("barHeight", 0)
    vertical_width = expected.get("verticalBarWidth", 0)
    rounding = expected.get("screenRounding", 0)
    lanes = entry.get("lanes") or {}
    if vertical:
        # left edge sits at x=0, right edge at the far end of the window.
        edge_x = 0 if edge_name == "left" else window_box.get("w", 0) - content_box.get("w", 0)
        row_ok = bool(
            abs(window_box.get("w", 0) - (vertical_width + rounding)) <= 1
            and abs(content_box.get("w", 0) - vertical_width) <= 1
            and abs(content_box.get("h", 0) - window_box.get("h", 0)) <= 1
            and abs(content_box.get("offsetX", -1) - edge_x) <= 1
            and abs(content_box.get("offsetY", -1)) <= 1
            and lanes.get("top", 0) > 0
            and lanes.get("bottom", 0) > 0
            and entry.get("middle") == []
        )
    else:
        # top edge sits at y=0, bottom edge below the corner-rounding band.
        edge_y = 0 if edge_name == "top" else window_box.get("h", 0) - content_box.get("h", 0)
        row_ok = bool(
            abs(window_box.get("h", 0) - (bar_height + rounding)) <= 1
            and abs(content_box.get("h", 0) - bar_height) <= 1
            and abs(content_box.get("w", 0) - window_box.get("w", 0)) <= 1
            and abs(content_box.get("offsetY", -1) - edge_y) <= 1
            and abs(content_box.get("offsetX", -1)) <= 1
        )
    if edge_name == "top":
        top_snapshots.append((window_box, content_box))
    window_cases.append({
        "edge": edge_name,
        "vertical": vertical,
        "window": window_box,
        "content": content_box,
        "middle": entry.get("middle"),
        "ok": row_ok,
    })
    window_ok = window_ok and row_ok

round_trip_ok = len(top_snapshots) == 2 and top_snapshots[0] == top_snapshots[1]
window_ok = window_ok and round_trip_ok

# B9.7 autohide rows: the reservation collapses while the toggle is on and
# restores (positive zone) after it flips back.
autohide_on_row = autohide_rows.get("autohide-on") or {}
autohide_off_row = autohide_rows.get("autohide-off") or {}
autohide_ok = bool(
    autohide_on_row.get("found") is True
    and autohide_on_row.get("autoHide") is True
    and autohide_on_row.get("exclusiveZone") == 0
    and autohide_off_row.get("found") is True
    and autohide_off_row.get("autoHide") is False
    and (autohide_off_row.get("exclusiveZone") or 0) > 0
)
window_ok = window_ok and autohide_ok

# B9.6: style-editor chain, fixed-slot workspaces and the island hug.
def _b96(json_blob):
    try:
        data = json.loads(json_blob) if json_blob else {}
    except (ValueError, TypeError):
        data = {}
    return data if data.get("ready") is True else {}

override = _b96(b96_override)
reset = _b96(b96_reset)
hug_float = _b96(b96_hug_float)
hug_plain = _b96(b96_hug_plain)
override_style = override.get("style") or {}
reset_widget = reset.get("widget") or {}
hug_float_pill = hug_float.get("centerPill") or {}
hug_plain_pill = hug_plain.get("centerPill") or {}

override_ok = bool(
    override_style.get("hasOverride") is True
    and override_style.get("groupContentColor") == override_style.get("expectedOnPrimary")
    and (override.get("widget") or {}).get("contentColorOverridden") is True
    and (override.get("widget") or {}).get("contentColor") == override_style.get("expectedOnPrimary")
)
ws = reset.get("widget") or {}
# Dynamic slots (iNiR dynamicCount semantics): the bar shows exactly the
# workspaces niri reports on the output — with no compositor behind the
# probe exactly one placeholder slot renders.
ws_ok = bool(
    ws.get("hasContentColorProps") is True
    and ws.get("contentColorOverridden") is False
    and ws.get("style") == "default"
    and ws.get("slotLength") == 26
    and ws.get("slotWidth") == 26
    and ws.get("shown") == max((ws.get("existingMaxIdx") or 0), 1)
    and ws.get("fakeWorkspace") == -9999
    and abs(ws.get("implicitWidth", 0) - 26 * (ws.get("shown") or 0)) <= 0.01
)
hug_float_ok = bool(
    hug_float_pill.get("middleRowWidth", 0) > 0
    and abs(hug_float_pill.get("width", 0) - (hug_float_pill.get("middleRowWidth", 0) + 8)) <= 0.01
    and (hug_float.get("islandCapsule") or {}).get("layer0") is True
    and (hug_float.get("islandCapsule") or {}).get("transparent") is False
)
hug_plain_ok = bool(
    hug_plain.get("cornerStyle") == 0
    and hug_plain_pill.get("middleRowWidth", 0) > 0
    and abs(hug_plain_pill.get("width", 0) - (hug_plain_pill.get("middleRowWidth", 0) - 4)) <= 0.01
    and (hug_plain.get("islandCapsule") or {}).get("transparent") is True
)
b96_ok = override_ok and ws_ok and hug_float_ok and hug_plain_ok

# B9.7 settled-settings sweep: bridge passthrough + the live consumer reacting.
def _b97(json_blob):
    try:
        data = json.loads(json_blob) if json_blob else {}
    except (ValueError, TypeError):
        data = {}
    return data if data.get("ready") is True else {}


b97_baseline = _b97(b97_baseline)
b97_bg_off = _b97(b97_bg_off)
b97_divider = _b97(b97_divider)
b97_util_on = _b97(b97_util_on)
b97_util_off = _b97(b97_util_off)
b97_res_on = _b97(b97_res_on)
b97_res_off = _b97(b97_res_off)
b97_han = _b97(b97_han)
b97_roman = _b97(b97_roman)


def _layout_ok(blob):
    try:
        data = json.loads(blob) if blob else {}
    except (ValueError, TypeError):
        return False
    return bool(data.get("ready") is True and data.get("ok") is True and data.get("failed") == [] and data.get("pending") == [])


b97_baseline_bridge = b97_baseline.get("bridge") or {}
b97_bg_bridge = b97_bg_off.get("bridge") or {}


def _rgb(hex_color):
    """Alpha-normalized tail of '#rrggbb' / '#aarrggbb' for value comparison."""
    digits = str(hex_color).lstrip("#")
    return digits[-6:].lower() if len(digits) >= 6 else ""


baseline_layer0 = _rgb(b97_baseline.get("colLayer0"))
background_ok = bool(
    b97_baseline_bridge.get("showBackground") is True
    and baseline_layer0
    and _rgb((b97_baseline.get("background") or {}).get("color")) == baseline_layer0
    and b97_bg_bridge.get("showBackground") is False
    and _rgb((b97_bg_off.get("background") or {}).get("color")) == "000000"
)

divider_bridge = (b97_divider.get("bridge") or {})
divider = b97_divider.get("divisor") or {}
divider_ok = bool(
    divider_bridge.get("dividerStyle") == "space"
    and divider_bridge.get("dividerSpacing") == 20
    and divider.get("spacing") == 20
    and divider.get("width") == 20
    and divider.get("height", 0) > 0
)

buttons_on = set(b97_util_on.get("buttons") or [])
buttons_off = set(b97_util_off.get("buttons") or [])
icons_on = set(b97_util_on.get("buttonIcons") or [])
icons_off = set(b97_util_off.get("buttonIcons") or [])
# Locale-independent: the keyboard slot is identified by its icon, the two
# untranslated tooltips anchor the rest of the fixed slots.
util_ok = bool(
    (b97_util_on.get("bridge") or {}).get("utilKeyboard") is True
    and "keyboard" in icons_on
    and "screenshot_region" in icons_on
    and "Take screenshot" in buttons_on
    and (b97_util_off.get("bridge") or {}).get("utilKeyboard") is False
    and "keyboard" not in icons_off
    and "screenshot_region" in icons_off
)

swap_on = b97_res_on.get("swapNodes") or []
swap_off = b97_res_off.get("swapNodes") or []
resources_ok = bool(
    (b97_res_on.get("bridge") or {}).get("resourceSwap") is True
    and len(swap_on) >= 1
    and all(node.get("shown") is True for node in swap_on)
    and (b97_res_off.get("bridge") or {}).get("resourceSwap") is False
    and len(swap_off) >= 1
    and all(node.get("shown") is False for node in swap_off)
)

number_ok = bool(
    (b97_han.get("bridge") or {}).get("numberStyle") == "han"
    and len(b97_han.get("han") or []) >= 1
    and not b97_han.get("roman")
    and (b97_roman.get("bridge") or {}).get("numberStyle") == "roman"
    and len(b97_roman.get("roman") or []) >= 1
    and not b97_roman.get("han")
)

screen_ok = _layout_ok(b97_screen_named) and _layout_ok(b97_screen_empty)
b97_ok = background_ok and divider_ok and util_ok and resources_ok and number_ok and screen_ok and autohide_ok and b97_persisted == "true" and autohide_ok

ok = (len(layouts) == 6 and all(entry.get("ok") for entry in layouts) and not hits
      and borderless_ok and media_ok and osd_ok and keyboard_osd_ok and island_off_ok
      and island_restored_ok and island_migration_ok and idle_face_ok
      and avatar_optional_ok
      and tray_ok and peripheral_ok and vertical_ok and margin_ok and window_ok
      and b96_ok and b97_ok)
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
    "islandRestored": {
        "ok": island_restored_ok,
        "middle": island_restored.get("lanes", {}).get("middle", []),
    },
    "islandMigration": {
        "ok": island_migration_ok,
        "seeded": seeded.get("middle", []),
        "keptEmpty": kept_empty.get("middle", []),
        "legacyOff": legacy_off.get("middle", []),
    },
    "idleFace": {
        "ok": idle_face_ok,
        "satellite": idle_face.get("satellite", ""),
        "idleWidth": idle_face.get("idleWidth"),
        "showAvatar": idle_face.get("showAvatar"),
        "noAvatarWidth": idle_face_no_avatar.get("idleWidth"),
        "avatarOptional": avatar_optional_ok,
        "clockVisible": idle_face.get("clockVisible"),
        "clockWidth": idle_face.get("clockWidth"),
        "avatarReady": idle_face.get("avatarReady"),
        "avatarFallback": idle_face.get("avatarFallback"),
    },
    "vertical": {
        "ok": vertical_ok,
        "boost": boost_ok,
        "cases": vertical_cases,
    },
    "windowProbe": {
        "ok": window_ok,
        "roundTrip": round_trip_ok,
        "cases": window_cases,
    },
    "margins": {
        "ok": margin_ok,
        "baseBarHeight": base_bar_height,
        "baseVerticalBarWidth": base_vertical_width,
        "cornerStyle": margin_style,
        "cases": margin_cases,
    },
    "tray": tray_report,
    "systemIcons": system_icons_report,
    "b96": {
        "ok": b96_ok,
        "override": {
            "ok": override_ok,
            "groupContentColor": override_style.get("groupContentColor"),
        },
        "workspaces": {
            "ok": ws_ok,
            "shown": ws.get("shown"),
            "slotWidth": ws.get("slotWidth"),
            "implicitWidth": ws.get("implicitWidth"),
        },
        "hug": {
            "ok": hug_float_ok and hug_plain_ok,
            "floatWidth": hug_float_pill.get("width"),
            "floatMiddleRow": hug_float_pill.get("middleRowWidth"),
            "plainWidth": hug_plain_pill.get("width"),
            "plainMiddleRow": hug_plain_pill.get("middleRowWidth"),
            "capsuleTransparent": (hug_plain.get("islandCapsule") or {}).get("transparent"),
            "capsuleLayer0OnFloat": (hug_float.get("islandCapsule") or {}).get("layer0"),
        },
    },
    "b97": {
        "ok": b97_ok,
        "background": {
            "ok": background_ok,
            "baseline": (b97_baseline.get("background") or {}).get("color"),
            "off": (b97_bg_off.get("background") or {}).get("color"),
        },
        "divider": {
            "ok": divider_ok,
            "style": divider.get("style"),
            "spacing": divider.get("spacing"),
            "width": divider.get("width"),
        },
        "utilButtons": {
            "ok": util_ok,
            "on": sorted(icons_on),
            "off": sorted(icons_off),
        },
        "resources": {
            "ok": resources_ok,
            "bridgeOn": b97_res_on.get("bridge"),
            "bridgeOff": b97_res_off.get("bridge"),
            "nodesOn": b97_res_on.get("resourceNodes"),
            "nodesOff": b97_res_off.get("resourceNodes"),
            "swapOn": swap_on,
            "swapOff": swap_off,
        },
        "numbers": {
            "ok": number_ok,
            "han": sorted((b97_han.get("han") or []))[:6],
            "roman": sorted((b97_roman.get("roman") or []))[:6],
        },
        "screenFilter": {
            "ok": screen_ok,
        },
        "persisted": b97_persisted == "true",
        "autohide": {
            "ok": autohide_ok,
            "onZone": autohide_on_row.get("exclusiveZone"),
            "offZone": autohide_off_row.get("exclusiveZone"),
        },
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

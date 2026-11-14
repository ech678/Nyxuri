#!/usr/bin/env bash
# B8.6 bar runtime probe.
#
# Loads plugins/bar/BarContent.qml in an isolated temp shell and reports the
# evaluated lane geometry plus every active Loader's status. This is the
# runtime evidence the string-assertion tests cannot give: NaN layout chains,
# compiled-empty widgets and TypeError storms all show up here. It walks all
# six corner styles, the four borderless modes, the self-hiding widget lane
# (Media with no track) in both capsule paths, and the tray surface (fake
# StatusNotifierItems -> pin/unpin -> overflow arrow -> persisted config).
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

python3 - "${layouts}" "${borderless}" "${media_hidden}" "${tmp}/qs.log" "${json_mode}" "${mode}" "${osd_state}" "${keyboard_osd_state}" "${island_off_state}" "${tray_initial}" "${tray_hidden}" "${tray_closed}" "${tray_reset}" "${tray_persisted}" "${tray_skip_reason}" "${system_icons_state}" "${system_icons_fake}" "${system_icons_reset}" "${island_restored_state}" "${island_migration}" "${idle_face_state}" <<'PY'
import json
import re
import sys

(layouts_path, borderless_path, media_hidden_path, log_path, json_mode, mode,
 osd_state, keyboard_osd_state, island_off_state, tray_initial, tray_hidden,
 tray_closed, tray_reset, tray_persisted, tray_skip_reason, system_icons_state,
 system_icons_fake, system_icons_reset, island_restored_state, island_migration,
 idle_face_state) = sys.argv[1:22]


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
idle_face_ok = bool(
    idle_face.get("found") is True
    and idle_face.get("islandState") == "idle"
    and isinstance(idle_face.get("idleWidth"), (int, float))
    and idle_face.get("idleWidth") > 0
    and not (idle_face.get("avatarReady") and idle_face.get("avatarFallback"))
    and (idle_face.get("avatarReady") or idle_face.get("avatarFallback"))
)
if idle_face.get("satellite") == "clock":
    idle_face_ok = idle_face_ok and idle_face.get("clockVisible") is True and idle_face.get("clockWidth", 0) > 0 and idle_face.get("clockHeight", 0) > 0

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

ok = (len(layouts) == 6 and all(entry.get("ok") for entry in layouts) and not hits
      and borderless_ok and media_ok and osd_ok and keyboard_osd_ok and island_off_ok
      and island_restored_ok and island_migration_ok and idle_face_ok
      and tray_ok and peripheral_ok)
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
        "clockVisible": idle_face.get("clockVisible"),
        "clockWidth": idle_face.get("clockWidth"),
        "avatarReady": idle_face.get("avatarReady"),
        "avatarFallback": idle_face.get("avatarFallback"),
    },
    "tray": tray_report,
    "systemIcons": system_icons_report,
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

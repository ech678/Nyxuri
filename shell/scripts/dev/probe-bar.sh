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

# NYXURI_PROBE_KEEP=1 keeps the staged tree for post-mortem inspection.
if [[ ${NYXURI_PROBE_KEEP:-0} == 1 ]]; then
    unset -f cleanup
    printf 'probe tree kept at: %s\n' "${tmp}" >&2
fi
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
# D4a boot evidence: the store state the first layout sweep sees.
ipc d4aBootState >&2 2>/dev/null || true
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

d2_immediate_state=""
d2_settled_state=""
d2_unhover_state=""
if ipc systemIconsHoverSlot volume >/dev/null 2>&1; then
    d2_immediate_state=$(ipc systemIcons 2>/dev/null || true)
    sleep 0.4
    d2_settled_state=$(ipc systemIcons 2>/dev/null || true)
    ipc systemIconsUnhoverSlot volume >/dev/null 2>&1 || true
    sleep 0.3
    d2_unhover_state=$(ipc systemIcons 2>/dev/null || true)
fi

# D4a: entry engine (live geometry + injection), version-chain migration and
# the minimal-write serializer, all through the same store the UI uses. Set
# and dump are separate IPC rounds so delegate rebuild settles first.
d4a_entries_spacers=""
d4a_entries_disabled=""
d4a_singletons=""
d4a_migration_state=""
d4a_persistence_state=""
if ipc d4aEntriesSet spacers >/dev/null 2>&1; then
    sleep 0.6
    d4a_entries_spacers=$(ipc d4aEntriesDump 2>/dev/null || true)
    sleep 0.4
fi
if ipc d4aEntriesSet disabledOnly >/dev/null 2>&1; then
    sleep 0.6
    d4a_entries_disabled=$(ipc d4aEntriesDump 2>/dev/null || true)
    sleep 0.4
fi
if ipc d4aSingletons >/dev/null 2>&1; then
    d4a_singletons=$(ipc d4aSingletons 2>/dev/null || true)
fi
if ipc d4aMigration >/dev/null 2>&1; then
    d4a_migration_state=$(ipc d4aMigration 2>/dev/null || true)
fi
if ipc d4aPersistence >/dev/null 2>&1; then
    d4a_persistence_state=$(ipc d4aPersistence 2>/dev/null || true)
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
    # Divider: the space style reads the settled width (end4 spinbox). D4b:
    # style/spacing are separator entry axes (d4bSet), not flat keys.
    if ipc scene divisorLeft >/dev/null 2>&1; then
        sleep 0.5
        ipc d4bSet separator style '"space"' >/dev/null 2>&1 || true
        ipc d4bSet separator spacing 20 >/dev/null 2>&1 || true
        sleep 0.4
        b97_divider=$(ipc b97Dump 2>/dev/null || true)
        ipc d4bSet separator style '"rect"' >/dev/null 2>&1 || true
        ipc d4bSet separator spacing 4 >/dev/null 2>&1 || true
        ipc scene default >/dev/null 2>&1 || true
        sleep 0.4
    fi
    # Util buttons: material path exposes tooltips; the keyboard slot must
    # disappear with its settled toggle.
    if ipc cornerStyle 3 >/dev/null 2>&1; then
        ipc scene utilOnly >/dev/null 2>&1 || true
        ipc reload >/dev/null 2>&1 || true
        sleep 0.8
        ipc d4bSet utilButtons keyboardToggle true >/dev/null 2>&1 || true
        sleep 0.4
        b97_util_on=$(ipc b97Dump 2>/dev/null || true)
        ipc d4bSet utilButtons keyboardToggle false >/dev/null 2>&1 || true
        sleep 0.4
        b97_util_off=$(ipc b97Dump 2>/dev/null || true)
        ipc d4bSet utilButtons keyboardToggle false >/dev/null 2>&1 || true
        ipc scene default >/dev/null 2>&1 || true
        ipc cornerStyle 1 >/dev/null 2>&1 || true
        ipc reload >/dev/null 2>&1 || true
        sleep 0.6
    fi
    # Resources: the swap meter follows its settled toggle (shipped default
    # is off, so flip it on first and restore the default after).
    if ipc scene monitorOnly >/dev/null 2>&1; then
        sleep 0.8
        ipc d4bSet systemMonitor swap true >/dev/null 2>&1 || true
        sleep 0.5
        b97_res_on=$(ipc b97Dump 2>/dev/null || true)
        ipc d4bSet systemMonitor swap false >/dev/null 2>&1 || true
        sleep 0.5
        b97_res_off=$(ipc b97Dump 2>/dev/null || true)
        ipc scene default >/dev/null 2>&1 || true
        ipc reload >/dev/null 2>&1 || true
        sleep 0.6
    fi
    # Number presets: the workspace labels re-render through the entry.
    if ipc d4bSet workspaces numberStyle '"han"' >/dev/null 2>&1; then
        sleep 0.5
        b97_han=$(ipc b97Dump 2>/dev/null || true)
        ipc d4bSet workspaces numberStyle '"roman"' >/dev/null 2>&1 || true
        sleep 0.5
        b97_roman=$(ipc b97Dump 2>/dev/null || true)
        ipc d4bSet workspaces numberStyle '"normal"' >/dev/null 2>&1 || true
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
    # Minimal write (D4a/D4b): default-equal entries collapse, so
    # write-through is proven with one axis pushed off its default (the
    # override lands as a flat entry key in config.toml). The default lane
    # carries the quickSettings id (same component as utilButtons).
    ipc d4bSet quickSettings micToggle true >/dev/null 2>&1 || true
    sleep 0.3
    if grep -q 'micToggle' "${tmp}/config/nyxuri/config.toml" 2>/dev/null; then
        b97_persisted=true
    fi
    ipc d4bSet quickSettings micToggle false >/dev/null 2>&1 || true
fi

# D4b: per-instance engine — v4 migration (flat keys + [time].dateFormat
# fold onto entries), duplicate-instance isolation, and the click-action
# vocabulary (closed ids, argv-only commands).
d4b_migration_state=""
d4b_instances_state=""
d4b_click_vocabulary=""
if ipc d4bMigration >/dev/null 2>&1; then
    d4b_migration_state=$(ipc d4bMigration 2>/dev/null || true)
fi
if ipc d4bInstances >/dev/null 2>&1; then
    d4b_instances_state=$(ipc d4bInstances 2>/dev/null || true)
fi
if ipc d4bClickVocabulary >/dev/null 2>&1; then
    d4b_click_vocabulary=$(ipc d4bClickVocabulary 2>/dev/null || true)
fi

# D4c: v5 migration + sentinel resolution + fusion roles.
d4c_migration_state=""
d4c_sentinels_state=""
d4c_roles_state=""
if ipc d4cMigration >/dev/null 2>&1; then
    d4c_migration_state=$(ipc d4cMigration 2>/dev/null || true)
fi
if ipc d4cSentinels >/dev/null 2>&1; then
    d4c_sentinels_state=$(ipc d4cSentinels 2>/dev/null || true)
fi
if ipc d4cRoles >/dev/null 2>&1; then
    d4c_roles_state=$(ipc d4cRoles 2>/dev/null || true)
fi

# D4d: behavior axes round-trip + the overflow engine (resolver unit run,
# then the live cramped stage with a popup cycle, then the reset restore).
d4d_behavior_state=""
d4d_overflow_resolve_state=""
d4d_overflow_cramped_state=""
d4d_overflow_reset_state=""
if ipc d4dBehavior >/dev/null 2>&1; then
    d4d_behavior_state=$(ipc d4dBehavior 2>/dev/null || true)
fi
if ipc d4dOverflowResolve >/dev/null 2>&1; then
    d4d_overflow_resolve_state=$(ipc d4dOverflowResolve 2>/dev/null || true)
fi
if ipc d4dOverflowScene 300 300 >/dev/null 2>&1; then
    d4d_overflow_cramped_state=$(ipc d4dOverflowDump 2>/dev/null || true)
    ipc d4dOverflowReset >/dev/null 2>&1 || true
    d4d_overflow_reset_state=$(ipc d4dOverflowDump 2>/dev/null || true)
fi

# D4e e1: multi-bar storage (add/round-trip/isolation/delete guards) and
# the rebuild signature (style-stable, routing-sensitive).
d4e_store_state=""
d4e_signature_state=""
d4e_migration_v6_state=""
d4e_windows_two_state=""
d4e_windows_off_state=""
d4e_windows_clean_state=""
if ipc d4eStore >/dev/null 2>&1; then
    d4e_store_state=$(ipc d4eStore 2>/dev/null || true)
fi
if ipc d4eSignature >/dev/null 2>&1; then
    d4e_signature_state=$(ipc d4eSignature 2>/dev/null || true)
fi
if ipc d4eMigrationV6 >/dev/null 2>&1; then
    d4e_migration_v6_state=$(ipc d4eMigrationV6 2>/dev/null || true)
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
# The edge switch waits for the window to actually flip orientation (up to 6s)
# instead of a fixed sleep — under a loaded session the compositor-side
# resize can outrun a static 0.9s budget (2026-11-21, D1 session).
wait_edge_window() {
    # Poll the actual window box aspect (not the config-derived `vertical`
    # flag): the compositor-side resize lags the config flip.
    local want_vertical="$1"
    local dump vertical
    for _ in $(seq 1 30); do
        dump=$(ipc windowDump 2>/dev/null || true)
        vertical=$(printf '%s' "${dump}" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except ValueError:
    print(""); raise SystemExit
w = int((d.get("window") or {}).get("w") or 0)
h = int((d.get("window") or {}).get("h") or 0)
if not w or not h or d.get("found") is not True:
    print("")
else:
    print(str(h > w).lower())' 2>/dev/null || true)
        if [[ ${vertical} == "${want_vertical}" ]]; then
            return 0
        fi
        sleep 0.2
    done
    return 1
}
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
            case ${edge} in
                left | right) wait_edge_window true >/dev/null 2>&1 || true ;;
                *) wait_edge_window false >/dev/null 2>&1 || true ;;
            esac
            # The aspect flips before the anchor/exclusive-zone settles; give
            # the offset geometry its own beat before dumping.
            sleep 0.6
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
        # D4e e2: multi-bar window topology (two bars -> disable -> clean).
        if ipc d4eWindowsSet two >/dev/null 2>&1; then
            sleep 0.6
            d4e_windows_two_state=$(ipc d4eWindowsDump 2>/dev/null || true)
        fi
        if ipc d4eWindowsSet off >/dev/null 2>&1; then
            sleep 0.6
            d4e_windows_off_state=$(ipc d4eWindowsDump 2>/dev/null || true)
        fi
        if ipc d4eWindowsSet clean >/dev/null 2>&1; then
            sleep 0.6
            d4e_windows_clean_state=$(ipc d4eWindowsDump 2>/dev/null || true)
        fi
    else
        printf 'error: bar window probe did not come up\n' >&2
        exit 3
    fi
    ipc windowMode false >/dev/null 2>&1 || true
    ipc edge top >/dev/null 2>&1 || true
fi

# D1 quick fixes + B-10: island media matrix, weather/visualizer leases and
# the date format key. All config-driven — no MPRIS player exists in the
# harness, and the null player is itself the lease-idle state worth pinning.
d1_island_media_file="${tmp}/d1-island-media.tsv"
: >"${d1_island_media_file}"
for controls in false true; do
    for style in dots wave none; do
        printf '%s\t%s\t%s\n' "${controls}" "${style}" "$(ipc islandMediaFace "${controls}" "${style}" 2>/dev/null || true)" >>"${d1_island_media_file}"
        sleep 0.2
    done
done
# The early ipc replies warm the (cold-compiled) widget; only the late
# captures feed the python report.
ipc weatherLease on >/dev/null 2>&1 || true
sleep 0.8
d1_weather_on_late=$(ipc weatherLease on 2>/dev/null || true)
ipc weatherLease off >/dev/null 2>&1 || true
sleep 0.6
d1_weather_off_late=$(ipc weatherLease off 2>/dev/null || true)
d1_visualizer_on=""
for _ in $(seq 1 8); do
    d1_visualizer_on=$(ipc visualizerLease on 2>/dev/null || true)
    [[ ${d1_visualizer_on} == *'"found":true'* ]] && break
    sleep 0.4
done
sleep 0.4
d1_visualizer_on_late=$(ipc visualizerLease on 2>/dev/null || true)
sleep 0.5
d1_visualizer_off_late=$(ipc visualizerLease off 2>/dev/null || true)
d1_date_fmt=$(ipc dateFormatProbe "ddd, dd/MM" 2>/dev/null || true)
d1_date_reset=$(ipc dateFormatProbe "" 2>/dev/null || true)
# Media fill contract: media-only lane (no player in the harness, so this
# pins the hidden-collapse and wiring; the visible-path overflow proof rides
# the real-machine screenshot pass).
ipc scene mediaOnly >/dev/null 2>&1 || true
ipc cornerStyle 3 >/dev/null 2>&1 || true
ipc reload >/dev/null 2>&1 || true
sleep 0.8
d1_media_geom=$(ipc mediaGeometry 2>/dev/null || true)
# Restore the shipped layout so the persisted config stays canonical.
ipc cornerStyle 1 >/dev/null 2>&1 || true
ipc scene default >/dev/null 2>&1 || true
ipc reload >/dev/null 2>&1 || true

python3 - "${layouts}" "${borderless}" "${media_hidden}" "${tmp}/qs.log" "${json_mode}" "${mode}" "${osd_state}" "${keyboard_osd_state}" "${island_off_state}" "${tray_initial}" "${tray_hidden}" "${tray_closed}" "${tray_reset}" "${tray_persisted}" "${tray_skip_reason}" "${system_icons_state}" "${system_icons_fake}" "${system_icons_reset}" "${island_restored_state}" "${island_migration}" "${idle_face_state}" "${idle_face_no_avatar}" "${vertical_file}" "${margins_state}" "${window_file}" "${b96_override}" "${b96_reset}" "${b96_hug_float}" "${b96_hug_plain}" "${b97_baseline}" "${b97_bg_off}" "${b97_divider}" "${b97_util_on}" "${b97_util_off}" "${b97_res_on}" "${b97_res_off}" "${b97_han}" "${b97_roman}" "${b97_screen_named}" "${b97_screen_empty}" "${b97_persisted}" "${d1_island_media_file}" "${d1_weather_on_late}" "${d1_weather_off_late}" "${d1_visualizer_on_late}" "${d1_visualizer_off_late}" "${d1_date_fmt}" "${d1_date_reset}" "${d1_media_geom}" "${d2_immediate_state}" "${d2_settled_state}" "${d2_unhover_state}" "${d4a_entries_spacers}" "${d4a_entries_disabled}" "${d4a_singletons}" "${d4a_migration_state}" "${d4a_persistence_state}" "${d4b_migration_state}" "${d4b_instances_state}" "${d4b_click_vocabulary}" "${d4c_migration_state}" "${d4c_sentinels_state}" "${d4c_roles_state}" "${d4d_behavior_state}" "${d4d_overflow_resolve_state}" "${d4d_overflow_cramped_state}" "${d4d_overflow_reset_state}" "${d4e_store_state}" "${d4e_signature_state}" "${d4e_migration_v6_state}" "${d4e_windows_two_state}" "${d4e_windows_off_state}" "${d4e_windows_clean_state}" <<'PY'
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
 b97_roman, b97_screen_named, b97_screen_empty, b97_persisted,
 d1_island_media_path, d1_weather_on, d1_weather_off, d1_visualizer_on,
 d1_visualizer_off, d1_date_fmt, d1_date_reset, d1_media_geom,
 d2_immediate_state, d2_settled_state, d2_unhover_state,
 d4a_entries_spacers, d4a_entries_disabled, d4a_singletons,
 d4a_migration_state, d4a_persistence_state, d4b_migration_state,
 d4b_instances_state, d4b_click_vocabulary, d4c_migration_state,
 d4c_sentinels_state, d4c_roles_state, d4d_behavior_state,
 d4d_overflow_resolve_state, d4d_overflow_cramped_state,
 d4d_overflow_reset_state, d4e_store_state, d4e_signature_state, d4e_migration_v6_state,
 d4e_windows_two_state, d4e_windows_off_state, d4e_windows_clean_state) = sys.argv[1:74]


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
# D1 three-segment geometry: the clock cluster sits in the pill's optical
# centre (the old right-packed layout left it uncentered).
if isinstance(idle_face.get("clockCenterX"), (int, float)) and isinstance(idle_face.get("faceWidth"), (int, float)) and idle_face["faceWidth"] > 0:
    idle_face_ok = idle_face_ok and abs(idle_face["clockCenterX"] - idle_face["faceWidth"] / 2) <= 0.75
else:
    idle_face_ok = False
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
            try:
                rows.append((parts[:-1], json.loads(parts[-1])))
            except ValueError:
                # Empty/failed ipc payload: keep the row keyed with an empty
                # report so consumers fail their own assertions instead of
                # crashing the whole probe.
                rows.append((parts[:-1], {}))
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

# D1: island media matrix (controls x style), weather/visualizer leases and
# the date format key. The harness has no MPRIS player and (usually) no cava
# binary — the null player is exactly the lease-idle state worth pinning.
d1_matrix_rows = load_tsv_rows(d1_island_media_path)
d1_matrix = {}
for key, entry in d1_matrix_rows:
    if len(key) == 2:
        d1_matrix[(str(key[0]).lower(), str(key[1]))] = entry
matrix_expectations = {
    # (controls, style): (controlsVisible, waveVisible, dotsVisible)
    ("false", "dots"): (False, False, True),
    ("false", "wave"): (False, True, False),
    ("false", "none"): (False, False, False),
    ("true", "dots"): (True, False, False),
    ("true", "wave"): (True, True, False),
    ("true", "none"): (True, False, False),
}
island_matrix_ok = len(d1_matrix) == 6
for state, expected in matrix_expectations.items():
    entry = d1_matrix.get(state) or {}
    actual = (entry.get("controlsVisible"), entry.get("waveVisible"), entry.get("dotsVisible"))
    if entry.get("found") is not True or actual != expected:
        island_matrix_ok = False
    # No player playing -> no cava lease in any state.
    if entry.get("waveCavaActive") is True or entry.get("cavaSubscribers", 0) != 0:
        island_matrix_ok = False

def _d1_json(blob):
    try:
        return json.loads(blob) if blob else {}
    except (ValueError, TypeError):
        return {}

d1_weather_on_state = _d1_json(d1_weather_on)
d1_weather_off_state = _d1_json(d1_weather_off)
d1_visualizer_on_state = _d1_json(d1_visualizer_on)
d1_visualizer_off_state = _d1_json(d1_visualizer_off)
d1_date_fmt_state = _d1_json(d1_date_fmt)
d1_date_reset_state = _d1_json(d1_date_reset)
d1_media_geom_state = _d1_json(d1_media_geom)

weather_lease_ok = bool(
    d1_weather_on_state.get("leaseCount", 0) >= 1
    and d1_weather_off_state.get("leaseCount") == 0
)
# Mount/unmount lifecycle: the widget instantiates in the lane and leaves no
# lease behind after removal. (The mount-time subscriber count is timing-
# dependent — the acquire lands on a later polish tick — so only the release
# side is pinned to zero.)
visualizer_lease_ok = bool(
    d1_visualizer_on_state.get("found") is True
    and d1_visualizer_off_state.get("found") is not True
    and d1_visualizer_off_state.get("subscribers") == 0
)
# "ddd, dd/MM" renders like "Fri, 28/08"; the reset returns to the stock long
# weekday form and the short date stays on its own fixed pattern.
date_format_ok = bool(
    re.fullmatch(r"[A-Za-z]{3}, \d{2}/\d{2}", str(d1_date_fmt_state.get("date", ""))) is not None
    and re.fullmatch(r"\d{2}/\d{2}", str(d1_date_fmt_state.get("shortDate", ""))) is not None
    and d1_date_reset_state.get("format", "x") == ""
    and re.fullmatch(r"\d{2}/\d{2}", str(d1_date_reset_state.get("shortDate", ""))) is not None
    and d1_date_reset_state.get("date") != d1_date_fmt_state.get("date")
)
# The fill contract: whenever the widget is visible its row never paints
# wider than the widget box (the overflow bug). Hidden collapses to zero.
media_geometry_ok = bool(
    d1_media_geom_state.get("found") is True
    and (
        d1_media_geom_state.get("visible") is not True
        or (
            d1_media_geom_state.get("overflow") is False
            and d1_media_geom_state.get("rowAssignedWidth", -1) <= d1_media_geom_state.get("widgetWidth", 0) + 0.5
        )
    )
)
d1_ok = island_matrix_ok and weather_lease_ok and visualizer_lease_ok and date_format_ok and media_geometry_ok

# D2: SystemIcons QS hover expansion (26 <-> 54px, 200ms) with 150ms intent delay
# and status data lines (volume %, SSID, Bluetooth count).
d2_immediate = json.loads(d2_immediate_state) if d2_immediate_state.strip() else {}
d2_settled = json.loads(d2_settled_state) if d2_settled_state.strip() else {}
d2_unhover = json.loads(d2_unhover_state) if d2_unhover_state.strip() else {}

def find_system_slot(tree, key):
    for s in tree.get("slots", []):
        if s.get("key") == key:
            return s
    return {}

d2_vol_imm = find_system_slot(d2_immediate, "volume")
d2_vol_set = find_system_slot(d2_settled, "volume")
d2_vol_unh = find_system_slot(d2_unhover, "volume")
d2_wifi = find_system_slot(system_icons, "wifi")
d2_bt = find_system_slot(system_icons, "bluetooth")
d2_kbd = find_system_slot(system_icons, "keyboard")

intent_delay_ok = bool(
    d2_immediate.get("found") is True
    and d2_vol_imm.get("expanded") is False
    and d2_vol_imm.get("width", 0) <= 26.5
)
expansion_width_ok = bool(
    d2_settled.get("found") is True
    and d2_vol_set.get("expanded") is True
    and abs(d2_vol_set.get("width", 0) - 54) <= 1.0
)
unhover_collapse_ok = bool(
    d2_unhover.get("found") is True
    and d2_vol_unh.get("expanded") is False
    and abs(d2_vol_unh.get("width", 0) - 26) <= 0.5
)
data_text_ok = bool(
    ("%" in str(d2_vol_set.get("dataText", "")) or "Muted" in str(d2_vol_set.get("dataText", "")))
    and str(d2_wifi.get("dataText", "")).strip() != ""
    and str(d2_bt.get("dataText", "")).strip() != ""
    and d2_kbd.get("expandable") is False
)
d2_ok = intent_delay_ok and expansion_width_ok and unhover_collapse_ok and data_text_ok

# D4a: entry engine + version-chain migration + minimal write.
d4a_spacers = json.loads(d4a_entries_spacers) if d4a_entries_spacers.strip() else {}
d4a_disabled = json.loads(d4a_entries_disabled) if d4a_entries_disabled.strip() else {}
d4a_singleton_state = json.loads(d4a_singletons) if d4a_singletons.strip() else {}
d4a_migration = json.loads(d4a_migration_state) if d4a_migration_state.strip() else {}
d4a_persistence = json.loads(d4a_persistence_state) if d4a_persistence_state.strip() else {}
d4a_entries_ok = bool(
    d4a_spacers.get("disabledNotInstantiated") is True
    and d4a_spacers.get("spacerCount") == 2
    and d4a_spacers.get("overrideInjected") is True
    and d4a_spacers.get("defaultSize") is True
    and d4a_disabled.get("disabledNotInstantiated") is True
    and d4a_disabled.get("laneCollapsed") is True
    and d4a_disabled.get("spacerCount") == 0
    and d4a_singleton_state.get("singletonDropped") is True
)
d4a_migration_ok = bool(
    d4a_migration.get("changed") is True
    and d4a_migration.get("version") == 6
    and d4a_migration.get("aliasResolved") is True
    and d4a_migration.get("islandSeeded") is True
    and d4a_migration.get("legacyStripped") is True
    and d4a_migration.get("idempotent") is True
)
d4a_persistence_ok = bool(
    d4a_persistence.get("defaultEmpty") is True
    and d4a_persistence.get("singleKey") is True
    and d4a_persistence.get("restoredEmpty") is True
    and d4a_persistence.get("enabledViewDropsDisabled") is True
    and d4a_persistence.get("configVersion") == 6
    and isinstance(d4a_persistence.get("disabledSparse"), list)
)
d4a_ok = d4a_entries_ok and d4a_migration_ok and d4a_persistence_ok

# D4b: v4 migration + duplicate-instance isolation + click vocabulary.
d4b_migration = json.loads(d4b_migration_state) if d4b_migration_state.strip() else {}
d4b_instances = json.loads(d4b_instances_state) if d4b_instances_state.strip() else {}
d4b_click = json.loads(d4b_click_vocabulary) if d4b_click_vocabulary.strip() else {}
d4b_migration_ok = bool(
    d4b_migration.get("changed") is True
    and d4b_migration.get("version") == 6
    and d4b_migration.get("workspacesFolded") is True
    and d4b_migration.get("workspacesDefaultsSkipped") is True
    and d4b_migration.get("separatorFolded") is True
    and d4b_migration.get("utilButtonsFolded") is True
    and d4b_migration.get("systemMonitorFolded") is True
    and d4b_migration.get("trayFolded") is True
    and d4b_migration.get("trayPinListKept") is True
    and d4b_migration.get("clockDateFormatFolded") is True
    and d4b_migration.get("globalsStripped") is True
    and d4b_migration.get("idempotent") is True
)
d4b_instances_ok = bool(
    d4b_instances.get("isolated") is True
    and d4b_instances.get("defaultCollapsedToString") is True
)
d4b_click_ok = bool(
    d4b_click.get("closed") is True
    and d4b_click.get("unknownFallsBack") is True
    and d4b_click.get("noneConsumes") is True
    and d4b_click.get("commandNeedsArgv") is True
    and d4b_click.get("axisForButtons") == ["clickAction", "middleClickAction", "rightClickAction"]
)
d4b_ok = d4b_migration_ok and d4b_instances_ok and d4b_click_ok

# D4c: v5 migration + sentinel resolution + fusion roles.
d4c_migration = json.loads(d4c_migration_state) if d4c_migration_state.strip() else {}
d4c_sentinels = json.loads(d4c_sentinels_state) if d4c_sentinels_state.strip() else {}
d4c_roles = json.loads(d4c_roles_state) if d4c_roles_state.strip() else {}
d4c_migration_ok = bool(
    d4c_migration.get("changed") is True
    and d4c_migration.get("version") == 6
    and d4c_migration.get("positionFolded") is True
    and d4c_migration.get("cornerStyleFolded") is True
    and d4c_migration.get("borderlessFolded") is True
    and d4c_migration.get("thicknessFolded") is True
    and d4c_migration.get("edgeMarginFolded") is True
    and d4c_migration.get("defaultsSkipped") is True
    and d4c_migration.get("activeModeStyleFolded") is True
    and d4c_migration.get("otherModeStyleDropped") is True
    and d4c_migration.get("flatStripped") is True
    and d4c_migration.get("trayKept") is True
    and d4c_migration.get("idempotent") is True
)
d4c_sentinels_ok = bool(
    d4c_sentinels.get("baselinePositive") is True
    and d4c_sentinels.get("explicitOverrides") is True
    and d4c_sentinels.get("restoredBaseline") is True
    and d4c_sentinels.get("insetBaseline") is True
    and d4c_sentinels.get("widgetPaddingBaseline") is True
    and d4c_sentinels.get("radiusAuto") is True
    and d4c_sentinels.get("radiusSquare") is True
    and d4c_sentinels.get("radiusOverride") is True
    and d4c_sentinels.get("fontScaleLive") is True
)
d4c_roles_ok = bool(
    d4c_roles.get("runFused") is True
    and d4c_roles.get("hiddenReShapes") is True
    and d4c_roles.get("spacerBreaks") is True
    and d4c_roles.get("liveRoles") is not None
)
d4c_ok = d4c_migration_ok and d4c_sentinels_ok and d4c_roles_ok

d4d_behavior = json.loads(d4d_behavior_state) if d4d_behavior_state.strip() else {}
d4d_overflow_resolve = json.loads(d4d_overflow_resolve_state) if d4d_overflow_resolve_state.strip() else {}
d4d_overflow_cramped = json.loads(d4d_overflow_cramped_state) if d4d_overflow_cramped_state.strip() else {}
d4d_overflow_reset = json.loads(d4d_overflow_reset_state) if d4d_overflow_reset_state.strip() else {}
d4d_behavior_ok = bool(
    d4d_behavior.get("defaultsPreserved") is True
    and d4d_behavior.get("delayLive") is True
    and d4d_behavior.get("strictLive") is True
    and d4d_behavior.get("fullscreenLive") is True
    and d4d_behavior.get("clickThroughLive") is True
    and d4d_behavior.get("hoverDelayLive") is True
    and d4d_behavior.get("sparseDeviationsOnly") is True
    and d4d_behavior.get("reset") is True
)
d4d_overflow_resolve_ok = bool(
    d4d_overflow_resolve.get("pinnedStays") is True
    and d4d_overflow_resolve.get("autoDefault") is True
    and d4d_overflow_resolve.get("alwaysVocabulary") is True
    and d4d_overflow_resolve.get("priorityFallback") is True
    and d4d_overflow_resolve.get("alwaysHidden") is True
    and d4d_overflow_resolve.get("barNeverHides") is True
    and d4d_overflow_resolve.get("lowPriorityYieldsFirst") is True
    and d4d_overflow_resolve.get("hysteresisRestores") is True
    and d4d_overflow_resolve.get("alwaysStaysHidden") is True
)
d4d_overflow_cramped_ok = bool(
    d4d_overflow_cramped.get("ready") is True
    and isinstance(d4d_overflow_cramped.get("hiddenIds"), list)
    and len(d4d_overflow_cramped.get("hiddenIds", [])) > 0
    and d4d_overflow_cramped.get("buttonFound") is True
    and isinstance(d4d_overflow_cramped.get("popupCycle"), dict)
    and d4d_overflow_cramped.get("popupCycle", {}).get("relocated") is True
    and d4d_overflow_cramped.get("popupCycle", {}).get("restored") is True
)
d4d_overflow_reset_ok = bool(
    d4d_overflow_reset.get("ready") is True
    and d4d_overflow_reset.get("hiddenIds") == []
)
d4d_ok = d4d_behavior_ok and d4d_overflow_resolve_ok and d4d_overflow_cramped_ok and d4d_overflow_reset_ok

d4e_store = json.loads(d4e_store_state) if d4e_store_state.strip() else {}
d4e_signature = json.loads(d4e_signature_state) if d4e_signature_state.strip() else {}
d4e_migration_v6 = json.loads(d4e_migration_v6_state) if d4e_migration_v6_state.strip() else {}
d4e_migration_v6_ok = bool(
    d4e_migration_v6.get("changed") is True
    and d4e_migration_v6.get("version") == 6
    and d4e_migration_v6.get("foldedOnEntry") is True
    and d4e_migration_v6.get("defaultsSkipped") is True
    and d4e_migration_v6.get("clockKept") is True
    and d4e_migration_v6.get("flatStripped") is True
    and d4e_migration_v6.get("emptyIslandDeleted") is True
    and d4e_migration_v6.get("idempotent") is True
)
d4e_store_ok = bool(
    # singleNull/bar1PristineIdentity are emitted for diagnostics only:
    # earlier probe sections legitimately leave axis deviations behind, so
    # pristine single-bar state is pinned by d4aPersistence, not here.
    d4e_store.get("twoCount") == 2
    and d4e_store.get("secondMiddle") == []
    and d4e_store.get("islandOwners") == ["default"]
    and d4e_store.get("uidUnique") is True
    and d4e_store.get("sparseIds") == ["default", "bar2"]
    and d4e_store.get("bar2HasPosition") is True
    and d4e_store.get("bar2HasClockOverride") is True
    and d4e_store.get("roundTripIds") == ["default", "bar2"]
    and d4e_store.get("roundTripIslandOwners") == ["default"]
    and d4e_store.get("islandBlockedMove") is True
    and d4e_store.get("islandBlockedAdd") is True
    and d4e_store.get("defaultRightUntouched") is True
    and d4e_store.get("defaultPositionUntouched") is True
    and d4e_store.get("refusedDefault") is True
    and d4e_store.get("backToOne") is True
    and d4e_store.get("refusedLast") is True
)
d4e_signature_ok = bool(
    d4e_signature.get("styleStable") is True
    and d4e_signature.get("positionMoved") is True
    and d4e_signature.get("disableMoved") is True
    and d4e_signature.get("twoEntries") is True
)
d4e_windows_two = json.loads(d4e_windows_two_state) if d4e_windows_two_state.strip() else {}
d4e_windows_off = json.loads(d4e_windows_off_state) if d4e_windows_off_state.strip() else {}
d4e_windows_clean = json.loads(d4e_windows_clean_state) if d4e_windows_clean_state.strip() else {}
_two_hosts = d4e_windows_two.get("hosts", [])
_off_hosts = d4e_windows_off.get("hosts", [])
_clean_hosts = d4e_windows_clean.get("hosts", [])
def _by_id(hosts, host_id):
    for host in hosts:
        if host.get("id") == host_id:
            return host
    return {}
d4e_windows_two_ok = bool(
    len(_two_hosts) == 2
    and _by_id(_two_hosts, "default").get("position") == "top" and _by_id(_two_hosts, "default").get("windows", 0) >= 1
    and _by_id(_two_hosts, "bar2").get("position") == "bottom" and _by_id(_two_hosts, "bar2").get("windows", 0) >= 1
    # The second bar's own window: bottom edge, its OWN clock-only lanes,
    # and its OWN thickness (50) & fontScale (1.1) & iconScale (1.25).
    and d4e_windows_two.get("secondEdge") == "bottom"
    and d4e_windows_two.get("firstHeight", 0) > 0
    and d4e_windows_two.get("secondHeight", 0) > d4e_windows_two.get("firstHeight", 0)
    and d4e_windows_two.get("firstIconScale") == 1.0
    and d4e_windows_two.get("secondIconScale") == 1.25
    and d4e_windows_two.get("firstFontScale") == 1.0
    and d4e_windows_two.get("secondFontScale") == 1.1
    and d4e_windows_two.get("secondLeftIds") == ["clock"]
    and d4e_windows_two.get("secondRightIds") == []
)
d4e_windows_off_ok = bool(
    len(_off_hosts) == 2
    and _by_id(_off_hosts, "bar2").get("enabled") is False and _by_id(_off_hosts, "bar2").get("windows") == 0
    and _by_id(_off_hosts, "default").get("windows", 0) >= 1
)
d4e_windows_clean_ok = bool(
    len(_clean_hosts) == 1
    and _by_id(_clean_hosts, "default").get("windows", 0) >= 1
)
d4e_ok = d4e_store_ok and d4e_signature_ok and d4e_migration_v6_ok and d4e_windows_two_ok and d4e_windows_off_ok and d4e_windows_clean_ok

ok = (len(layouts) == 6 and all(entry.get("ok") for entry in layouts) and not hits
      and borderless_ok and media_ok and osd_ok and keyboard_osd_ok and island_off_ok
      and island_restored_ok and island_migration_ok and idle_face_ok
      and avatar_optional_ok
      and tray_ok and peripheral_ok and vertical_ok and margin_ok and window_ok
      and b96_ok and b97_ok and d1_ok and d2_ok and d4a_ok and d4b_ok and d4c_ok and d4d_ok and d4e_ok)
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
        "clockCenterX": idle_face.get("clockCenterX"),
        "faceWidth": idle_face.get("faceWidth"),
        "statusWidth": idle_face.get("statusWidth"),
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
    "d1": {
        "ok": d1_ok,
        "islandMatrix": {
            "ok": island_matrix_ok,
            "cases": {f"{controls}|{style}": {
                "showControls": entry.get("showControls"),
                "style": entry.get("style"),
                "controlsVisible": entry.get("controlsVisible"),
                "waveVisible": entry.get("waveVisible"),
                "dotsVisible": entry.get("dotsVisible"),
                "waveCavaActive": entry.get("waveCavaActive"),
                "cavaSubscribers": entry.get("cavaSubscribers"),
            } for (controls, style), entry in sorted(d1_matrix.items())},
        },
        "weatherLease": {
            "ok": weather_lease_ok,
            "on": d1_weather_on_state.get("leaseCount"),
            "off": d1_weather_off_state.get("leaseCount"),
        },
        "visualizerLease": {
            "ok": visualizer_lease_ok,
            "on": {"found": d1_visualizer_on_state.get("found"), "subscribers": d1_visualizer_on_state.get("subscribers")},
            "off": {"found": d1_visualizer_off_state.get("found"), "subscribers": d1_visualizer_off_state.get("subscribers")},
        },
        "dateFormat": {
            "ok": date_format_ok,
            "formatted": d1_date_fmt_state.get("date"),
            "reset": d1_date_reset_state.get("date"),
            "shortDate": d1_date_fmt_state.get("shortDate"),
        },
        "mediaGeometry": {
            "ok": media_geometry_ok,
            "visible": d1_media_geom_state.get("visible"),
            "widgetWidth": d1_media_geom_state.get("widgetWidth"),
            "rowAssignedWidth": d1_media_geom_state.get("rowAssignedWidth"),
            "rowImplicitWidth": d1_media_geom_state.get("rowImplicitWidth"),
            "overflow": d1_media_geom_state.get("overflow"),
        },
    },
    "d2": {
        "ok": d2_ok,
        "intentDelay": intent_delay_ok,
        "expansionWidth": expansion_width_ok,
        "unhoverCollapse": unhover_collapse_ok,
        "dataText": data_text_ok,
        "volumeExpandedWidth": d2_vol_set.get("width"),
        "volumeDataText": d2_vol_set.get("dataText"),
    },
    "d4a": {
        "ok": d4a_ok,
        "entries": {
            "ok": d4a_entries_ok,
            "disabledNotInstantiated": d4a_spacers.get("disabledNotInstantiated") and d4a_disabled.get("disabledNotInstantiated"),
            "laneCollapsed": d4a_disabled.get("laneCollapsed"),
            "laneLeftWidthRaw": d4a_disabled.get("laneLeftWidthRaw"),
            "laneStateRaw": d4a_disabled.get("laneLeftFilledRaw"),
            "spacerCount": d4a_spacers.get("spacerCount"),
            "spacerWidths": d4a_spacers.get("spacerWidths"),
            "singletonDropped": d4a_singleton_state.get("singletonDropped"),
        },
        "migration": {
            "ok": d4a_migration_ok,
            "version": d4a_migration.get("version"),
            "aliasResolved": d4a_migration.get("aliasResolved"),
            "islandSeeded": d4a_migration.get("islandSeeded"),
            "legacyStripped": d4a_migration.get("legacyStripped"),
            "idempotent": d4a_migration.get("idempotent"),
        },
        "persistence": {
            "ok": d4a_persistence_ok,
            "defaultEmpty": d4a_persistence.get("defaultEmpty"),
            "singleKey": d4a_persistence.get("singleKey"),
            "restoredEmpty": d4a_persistence.get("restoredEmpty"),
            "enabledViewDropsDisabled": d4a_persistence.get("enabledViewDropsDisabled"),
            "disabledSparse": d4a_persistence.get("disabledSparse"),
            "configVersion": d4a_persistence.get("configVersion"),
        },
    },
    "d4b": {
        "ok": d4b_ok,
        "migration": {
            "ok": d4b_migration_ok,
            "version": d4b_migration.get("version"),
            "workspacesFolded": d4b_migration.get("workspacesFolded"),
            "separatorFolded": d4b_migration.get("separatorFolded"),
            "utilButtonsFolded": d4b_migration.get("utilButtonsFolded"),
            "systemMonitorFolded": d4b_migration.get("systemMonitorFolded"),
            "trayFolded": d4b_migration.get("trayFolded"),
            "trayPinListKept": d4b_migration.get("trayPinListKept"),
            "clockDateFormatFolded": d4b_migration.get("clockDateFormatFolded"),
            "globalsStripped": d4b_migration.get("globalsStripped"),
            "idempotent": d4b_migration.get("idempotent"),
        },
        "instances": {
            "ok": d4b_instances_ok,
            "isolated": d4b_instances.get("isolated"),
            "defaultCollapsedToString": d4b_instances.get("defaultCollapsedToString"),
            "sparseLeft": d4b_instances.get("sparseLeft"),
        },
        "clickVocabulary": {
            "ok": d4b_click_ok,
            "ids": d4b_click.get("ids"),
            "commandNeedsArgv": d4b_click.get("commandNeedsArgv"),
        },
    },
    "d4c": {
        "ok": d4c_ok,
        "migration": {
            "ok": d4c_migration_ok,
            "version": d4c_migration.get("version"),
            "positionFolded": d4c_migration.get("positionFolded"),
            "thicknessFolded": d4c_migration.get("thicknessFolded"),
            "activeModeStyleFolded": d4c_migration.get("activeModeStyleFolded"),
            "otherModeStyleDropped": d4c_migration.get("otherModeStyleDropped"),
            "trayKept": d4c_migration.get("trayKept"),
            "idempotent": d4c_migration.get("idempotent"),
        },
        "sentinels": {
            "ok": d4c_sentinels_ok,
            "restoredBaseline": d4c_sentinels.get("restoredBaseline"),
            "radiusSquare": d4c_sentinels.get("radiusSquare"),
            "radiusOverride": d4c_sentinels.get("radiusOverride"),
            "fontScaleLive": d4c_sentinels.get("fontScaleLive"),
        },
        "roles": {
            "ok": d4c_roles_ok,
            "runFused": d4c_roles.get("runFused"),
            "hiddenReShapes": d4c_roles.get("hiddenReShapes"),
            "spacerBreaks": d4c_roles.get("spacerBreaks"),
        },
    },
    "d4d": {
        "ok": d4d_ok,
        "behavior": {
            "ok": d4d_behavior_ok,
            "defaultsPreserved": d4d_behavior.get("defaultsPreserved"),
            "sparseDeviationsOnly": d4d_behavior.get("sparseDeviationsOnly"),
            "reset": d4d_behavior.get("reset"),
        },
        "overflowResolve": {
            "ok": d4d_overflow_resolve_ok,
            "alwaysHidden": d4d_overflow_resolve.get("alwaysHidden"),
            "lowPriorityYieldsFirst": d4d_overflow_resolve.get("lowPriorityYieldsFirst"),
            "hysteresisRestores": d4d_overflow_resolve.get("hysteresisRestores"),
        },
        "overflowLive": {
            "ok": d4d_overflow_cramped_ok,
            "hiddenIds": d4d_overflow_cramped.get("hiddenIds"),
            "buttonFound": d4d_overflow_cramped.get("buttonFound"),
            "popupCycle": d4d_overflow_cramped.get("popupCycle"),
            "resetCleared": d4d_overflow_reset_ok,
        },
    },
    "d4e": {
        "ok": d4e_ok,
        "store": {
            "ok": d4e_store_ok,
            "sparseIds": d4e_store.get("sparseIds"),
            "islandOwners": d4e_store.get("islandOwners"),
            "roundTripIds": d4e_store.get("roundTripIds"),
            "islandBlockedMove": d4e_store.get("islandBlockedMove"),
            "defaultPositionUntouched": d4e_store.get("defaultPositionUntouched"),
        },
        "signature": {
            "ok": d4e_signature_ok,
            "styleStable": d4e_signature.get("styleStable"),
            "positionMoved": d4e_signature.get("positionMoved"),
            "disableMoved": d4e_signature.get("disableMoved"),
        },
        "migrationV6": {
            "ok": d4e_migration_v6_ok,
            "version": d4e_migration_v6.get("version"),
            "foldedOnEntry": d4e_migration_v6.get("foldedOnEntry"),
            "emptyIslandDeleted": d4e_migration_v6.get("emptyIslandDeleted"),
            "idempotent": d4e_migration_v6.get("idempotent"),
        },
        "windows": {
            "ok": d4e_windows_two_ok and d4e_windows_off_ok and d4e_windows_clean_ok,
            "two": {
                "ok": d4e_windows_two_ok,
                "hosts": d4e_windows_two.get("hosts"),
                "secondEdge": d4e_windows_two.get("secondEdge"),
                "firstHeight": d4e_windows_two.get("firstHeight"),
                "secondHeight": d4e_windows_two.get("secondHeight"),
                "firstIconScale": d4e_windows_two.get("firstIconScale"),
                "secondIconScale": d4e_windows_two.get("secondIconScale"),
                "secondLeftIds": d4e_windows_two.get("secondLeftIds"),
            },
            "off": {
                "ok": d4e_windows_off_ok,
                "hosts": d4e_windows_off.get("hosts"),
            },
            "clean": {
                "ok": d4e_windows_clean_ok,
                "hosts": d4e_windows_clean.get("hosts"),
            },
        },
    },
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

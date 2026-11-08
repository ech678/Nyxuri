#!/bin/sh
set -eu

test "${NYXURI_CONTAINER:-}" = 1 || {
    printf '%s\n' 'Run this probe in the pinned benchmark container.' >&2
    exit 2
}

workspace=${1:-/workspace}
output=${2:-/results/spotlight-topk}
probe_root=$(mktemp -d /tmp/nyxuri-spotlight-topk.XXXXXX)
mkdir -p "$output"
cp -R "$workspace/shell" "$probe_root/shell"
cp "$workspace/shell/tests/qml/SpotlightTopKProbe/shell.qml" "$probe_root/shell/shell.qml"

export HOME="$probe_root/home"
export XDG_CACHE_HOME="$probe_root/cache"
export XDG_CONFIG_HOME="$probe_root/config"
export XDG_DATA_HOME="$probe_root/data"
export XDG_STATE_HOME="$probe_root/state"
export XDG_RUNTIME_DIR="$probe_root/runtime"
export WAYLAND_DISPLAY=nyxuri-topk-wayland
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export QSG_RHI_BACKEND=software
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

weston --backend=headless --renderer=pixman --no-config --socket="$WAYLAND_DISPLAY" --idle-time=0 \
    > "$output/weston.log" 2>&1 &
weston_pid=$!
preserve_runtime_logs() {
    if test -d "$probe_root/runtime/quickshell"; then
        cp -R "$probe_root/runtime/quickshell" "$output/quickshell-logs"
    fi
    if test -d "$probe_root/cache/quickshell/crashes"; then
        cp -R "$probe_root/cache/quickshell/crashes" "$output/quickshell-crashes"
    fi
}
cleanup() {
    preserve_runtime_logs
    kill "$weston_pid" 2>/dev/null || true
}
trap cleanup EXIT
for _ in $(seq 1 200); do
    test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" && break
    sleep 0.05
done
test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"

timeout --kill-after=2s 30s qs -p "$probe_root/shell" --no-duplicate > "$output/probe.log" 2>&1 || {
    cat "$output/probe.log"
    exit 1
}
grep -q '^.*SPOTLIGHT_TOPK_PROBE_PASS ' "$output/probe.log"
cat "$output/probe.log"

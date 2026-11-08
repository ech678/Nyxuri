#!/bin/sh
set -eu

test "${NYXURI_CONTAINER:-}" = 1 || {
    printf '%s\n' 'Run this probe only inside its pinned private container.' >&2
    exit 2
}

workspace=${1:-/workspace}
output=${2:-/results}
probe_root=$(mktemp -d /tmp/nyxuri-font-cache.XXXXXX)
mkdir -p "$output"
qt5compat_qml=$(find /nix/store -path '*/qt5compat-*/lib/qt-6/qml' -type d -print -quit)

for mode in baseline cached; do
    shell_dir="$probe_root/$mode/shell"
    mkdir -p "$(dirname "$shell_dir")"
    cp -R "$workspace/shell" "$shell_dir"
    cp "$workspace/shell/tests/qml/FontFamilyCacheProbe/shell.qml" "$shell_dir/shell.qml"
    if test "$mode" = baseline; then
        source=/results/FontService.before.qml
    else
        source="$workspace/shell/services/FontService.qml"
    fi
    python3 "$workspace/shell/tests/qml/FontFamilyCacheProbe/instrument.py" \
        "$source" "$shell_dir/services/FontService.qml" "$mode"

    export HOME="$probe_root/home-$mode"
    export XDG_CACHE_HOME="$probe_root/cache-$mode"
    export XDG_CONFIG_HOME="$probe_root/config-$mode"
    export XDG_DATA_HOME="$probe_root/data-$mode"
    export XDG_STATE_HOME="$probe_root/state-$mode"
    export XDG_RUNTIME_DIR="$probe_root/runtime-$mode"
    export WAYLAND_DISPLAY="nyxuri-font-cache-$mode"
    export QT_QPA_PLATFORM=wayland
    export QT_QUICK_BACKEND=software
    export QSG_RHI_BACKEND=software
    export QML_IMPORT_PATH="$shell_dir/tests/qml:$shell_dir:$qt5compat_qml:$shell_dir/ui/shapes"
    export QML2_IMPORT_PATH="$QML_IMPORT_PATH"
    export XDG_CURRENT_DESKTOP=""
    unset NIRI_SOCKET
    mkdir -p "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" \
        "$XDG_STATE_HOME" "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"

    weston --backend=headless --renderer=pixman --no-config --socket="$WAYLAND_DISPLAY" \
        --idle-time=0 > "$output/weston-$mode.log" 2>&1 &
    weston_pid=$!
    cleanup_weston() {
        kill "$weston_pid" 2>/dev/null || true
        wait "$weston_pid" 2>/dev/null || true
    }
    trap cleanup_weston EXIT HUP INT TERM
    for _ in $(seq 1 200); do
        test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" && break
        sleep 0.05
    done
    test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"
    if ! timeout --kill-after=2s 30s dbus-run-session \
            --config-file="$workspace/shell/scripts/dev/benchmark-dbus-session.conf" -- \
            qs -p "$shell_dir" --no-duplicate > "$output/probe-$mode.log" 2>&1; then
        cat "$output/probe-$mode.log"
        exit 1
    fi
    grep -q '^.*FONT_FAMILY_CACHE_PASS ' "$output/probe-$mode.log"
    cleanup_weston
    trap - EXIT HUP INT TERM
done

cat "$output/probe-baseline.log" "$output/probe-cached.log"

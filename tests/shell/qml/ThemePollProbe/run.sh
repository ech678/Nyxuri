#!/bin/sh
set -eu

# Run only inside the pinned benchmark Podman/Nix environment. The root is
# copied so qs.* resolves the real service tree without touching host config.
test "${NYXURI_CONTAINER:-}" = 1 || {
    printf '%s\n' 'Run this probe in the pinned benchmark container.' >&2
    exit 2
}
workspace=${1:-/workspace}
output=${2:-/results/theme-poll}
mkdir -p "$output"
probe_dir=$(mktemp -d /tmp/nyxuri-theme-poll.XXXXXX)
cp -R "$workspace/shell" "$probe_dir/shell"
cp "$workspace/shell/tests/qml/ThemePollProbe/shell.qml" "$probe_dir/shell/shell.qml"
mkdir -p "$probe_dir/bin" "$probe_dir/config" "$probe_dir/runtime"
chmod 700 "$probe_dir/runtime"
export XDG_RUNTIME_DIR="$probe_dir/runtime"
export NYXURI_SHELL_CONFIG_HOME="$probe_dir/config"
export NYXURI_BIN_HOME="$probe_dir/bin"
export THEME_POLL_CALLS="$probe_dir/calls"
export THEME_POLL_SETTING="$probe_dir/setting"
export PATH="$probe_dir/bin:$PATH"
export WAYLAND_DISPLAY=nyxuri-theme-poll-wayland
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export QSG_RHI_BACKEND=software
qt5compat_qml=$(find /nix/store -path '*/qt5compat-*/lib/qt-6/qml' -type d -print -quit)
export QML2_IMPORT_PATH="$qt5compat_qml:$probe_dir/shell/ui/shapes"
export QML_IMPORT_PATH="$QML2_IMPORT_PATH"
cp "$workspace/shell/tests/qml/ThemePollProbe/gsettings" "$probe_dir/bin/gsettings"
cp "$workspace/shell/tests/qml/ThemePollProbe/nyxuri" "$probe_dir/bin/nyxuri"
chmod +x "$probe_dir/bin/gsettings" "$probe_dir/bin/nyxuri"
weston --backend=headless --renderer=pixman --no-config --socket="$WAYLAND_DISPLAY" --idle-time=0 \
    > "$output/weston.log" 2>&1 &
weston_pid=$!
trap 'kill "$weston_pid" 2>/dev/null || true' EXIT
for _ in $(seq 1 200); do
    test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" && break
    sleep 0.05
done
test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"

for scenario in gated late write; do
    printf '%s\n' '{"theme":{"mode":"light"}}' > "$probe_dir/config/config.json"
    printf '%s\n' '{"spotlightSearchEngine":"duckduckgo"}' > "$probe_dir/config/ui-preferences.json"
    printf '%s\n' prefer-light > "$THEME_POLL_SETTING"
    : > "$THEME_POLL_CALLS"
    export THEME_POLL_LATE=0 THEME_POLL_WRITE=0
    if test "$scenario" = late; then export THEME_POLL_LATE=1; fi
    if test "$scenario" = write; then export THEME_POLL_WRITE=1; fi
    if timeout 70 qs -p "$probe_dir/shell" --no-duplicate > "$output/$scenario.log" 2>&1; then
        test "$(grep -c THEME_POLL_PROBE_PASS "$output/$scenario.log")" = 1
    else
        cat "$output/$scenario.log"
        exit 1
    fi
    cp "$THEME_POLL_CALLS" "$output/$scenario.calls"
    cat "$output/$scenario.log"
done

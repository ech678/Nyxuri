#!/bin/sh
set -eu

test "${NYXURI_CONTAINER:-}" = 1 || {
    printf '%s\n' 'Run this probe only inside the pinned private benchmark container.' >&2
    exit 2
}

workspace=${1:-/workspace}
output=${2:-/results/notification-connections}
probe_root=$(mktemp -d /tmp/nyxuri-notification-connections.XXXXXX)
shell_dir="$probe_root/shell"
mkdir -p "$output"
cp -R "$workspace/shell" "$shell_dir"
cp "$workspace/shell/tests/qml/NotificationConnectionsProbe/shell.qml" "$shell_dir/shell.qml"

export HOME="$probe_root/home"
export XDG_CACHE_HOME="$probe_root/cache"
export XDG_CONFIG_HOME="$probe_root/config"
export XDG_DATA_HOME="$probe_root/data"
export XDG_STATE_HOME="$probe_root/state"
export XDG_RUNTIME_DIR="$probe_root/runtime"
export NYXURI_SHELL_STATE_HOME="$XDG_STATE_HOME/nyxuri"
export WAYLAND_DISPLAY=nyxuri-notification-connections-wayland
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export QSG_RHI_BACKEND=software
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" \
    "$XDG_STATE_HOME/nyxuri/notifications" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

python3 -c 'import json,sys; n=2000; json.dump([{"notificationId":1000000+i,"localKind":"","filePath":"","appIcon":"/tmp/notification-fixture/icon.svg","appName":"Representative Application","body":"B"*256,"desktopEntry":"representative-application.desktop","image":"/tmp/notification-fixture/image.png","receivedAt":1762548900000+i,"summary":"Representative notification summary","urgency":1} for i in range(n)],open(sys.argv[1],"w"),separators=(",",":"))' \
    "$NYXURI_SHELL_STATE_HOME/notifications/notifications.json"

qt5compat_qml=$(find /nix/store -path '*/qt5compat-*/lib/qt-6/qml' -type d -print -quit)
export QML_IMPORT_PATH="$shell_dir/tests/qml:$shell_dir:$qt5compat_qml:$shell_dir/ui/shapes"
export QML2_IMPORT_PATH="$QML_IMPORT_PATH"

weston --backend=headless --renderer=pixman --no-config --socket="$WAYLAND_DISPLAY" \
    --idle-time=0 > "$output/weston.log" 2>&1 &
weston_pid=$!
cleanup() {
    kill "$weston_pid" 2>/dev/null || true
    wait "$weston_pid" 2>/dev/null || true
}
trap cleanup EXIT
for _ in $(seq 1 300); do
    test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" && break
    sleep 0.05
done
test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"

if ! timeout --kill-after=2s 30s dbus-run-session \
        --config-file="$workspace/shell/scripts/dev/benchmark-dbus-session.conf" -- \
        qs -p "$shell_dir" --no-duplicate > "$output/probe.log" 2>&1; then
    cat "$output/probe.log"
    exit 1
fi
cleanup
trap - EXIT
grep -q '^.*NOTIFICATION_CONNECTIONS_PASS ' "$output/probe.log"
cat "$output/probe.log"

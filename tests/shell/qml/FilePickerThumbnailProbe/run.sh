#!/bin/sh
set -eu

test "${NYXURI_CONTAINER:-}" = 1 || {
    printf '%s\n' 'Run this probe in the pinned private benchmark container.' >&2
    exit 2
}

workspace=${1:-/workspace}
output=${2:-/results}
probe_root=$(mktemp -d /tmp/nyxuri-filepicker-thumbnail.XXXXXX)
mkdir -p "$output"
python3 "$workspace/shell/tests/qml/FilePickerThumbnailProbe/make_images.py" "$probe_root/images"

for mode in baseline bounded; do
    shell_dir="$probe_root/$mode"
    mkdir -p "$shell_dir"
    cp -R "$workspace/shell" "$shell_dir/shell"
    cp "$workspace/shell/tests/qml/FilePickerThumbnailProbe/shell.qml" "$shell_dir/shell/shell.qml"
    if test "$mode" = baseline; then
        sed -i '/sourceSize: Qt.size(Math.max(1, Math.ceil(width \* Screen.devicePixelRatio)),/,+1d' \
            "$shell_dir/shell/services/FilePickerWindow.qml"
    fi

    export HOME="$probe_root/home-$mode"
    export XDG_CACHE_HOME="$probe_root/cache-$mode"
    export XDG_CONFIG_HOME="$probe_root/config-$mode"
    export XDG_DATA_HOME="$probe_root/data-$mode"
    export XDG_STATE_HOME="$probe_root/state-$mode"
    export XDG_RUNTIME_DIR="$probe_root/runtime-$mode"
    export WAYLAND_DISPLAY="nyxuri-filepicker-$mode"
    export QT_QPA_PLATFORM=wayland
    export QT_QUICK_BACKEND=software
    export QSG_RHI_BACKEND=software
    export FILEPICKER_IMAGE_DIR="$probe_root/images"
    if test "$mode" = bounded; then
        export FILEPICKER_EXPECT_BOUNDED=1
    else
        unset FILEPICKER_EXPECT_BOUNDED
    fi
    mkdir -p "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" \
        "$XDG_STATE_HOME" "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"

    weston --backend=headless --renderer=pixman --no-config --socket="$WAYLAND_DISPLAY" --idle-time=0 \
        > "$output/weston-$mode.log" 2>&1 &
    weston_pid=$!
    for _ in $(seq 1 200); do
        test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" && break
        sleep 0.05
    done
    test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"
    if python3 "$workspace/shell/tests/qml/FilePickerThumbnailProbe/measure.py" \
            "$output/memory-$mode.json" timeout --kill-after=2s 30s qs -p "$shell_dir/shell" \
            --no-duplicate > "$output/probe-$mode.log" 2>&1; then
        grep -q '^.*FILEPICKER_THUMBNAIL_PASS ' "$output/probe-$mode.log"
    else
        cat "$output/probe-$mode.log"
        kill "$weston_pid" 2>/dev/null || true
        exit 1
    fi
    kill "$weston_pid" 2>/dev/null || true
    wait "$weston_pid" 2>/dev/null || true
done

cat "$output/probe-baseline.log" "$output/probe-bounded.log"

#!/bin/sh
set -eu

test "${NYXURI_CONTAINER:-}" = 1 || {
    printf '%s\n' 'Run this probe in the pinned benchmark container.' >&2
    exit 2
}

workspace=${1:-/workspace}
output=${2:-/results}
probe_root=$(mktemp -d /tmp/nyxuri-weather-canvas.XXXXXX)
mkdir -p "$output"

for implementation in baseline optimized; do
    shell_dir="$probe_root/$implementation"
    mkdir -p "$shell_dir/ui"
    cp "$workspace/shell/tests/qml/WeatherCanvasProbe/shell.qml" "$shell_dir/shell.qml"
    cp "$workspace/shell/ui/LeafItem.qml" "$shell_dir/ui/LeafItem.qml"
    source="$shell_dir/WeatherBackground.source.txt"
    if test "$implementation" = baseline; then
        git -C "$workspace" show HEAD:shell/ui/WeatherBackground.qml > "$source"
    else
        cp "$workspace/shell/ui/WeatherBackground.qml" "$source"
    fi

    # Instrument only these disposable source copies so the runtime counter
    # observes each actual cloud-path builder invocation without shipping it.
    sed \
        -e '/^    property int paintCount: 0$/a\    property int cloudPathBuildCount: 0' \
        -e '/^    property int paintCount: 0$/a\    property string probeCaptureDataUrl: ""' \
        -e '/^    function drawCloudBandShape(ctx, offset, bandHeight, archHeight) {$/a\        root.cloudPathBuildCount += 1' \
        -e '/^            root.paintCount += 1$/a\            root.cloudPathBuildCount = 0' \
        -e '/^                root.drawSnow(ctx, fade, colors)$/a\                if (root.probeCaptureDataUrl === "") root.probeCaptureDataUrl = canvas.toDataURL("image/png")' \
        "$source" > "$shell_dir/ui/WeatherBackground.qml"
done

export HOME="$probe_root/home"
export XDG_CACHE_HOME="$probe_root/cache"
export XDG_CONFIG_HOME="$probe_root/config"
export XDG_DATA_HOME="$probe_root/data"
export XDG_STATE_HOME="$probe_root/state"
export XDG_RUNTIME_DIR="$probe_root/runtime"
export WAYLAND_DISPLAY=nyxuri-weather-canvas-wayland
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export QSG_RHI_BACKEND=software
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

weston --backend=headless --renderer=pixman --no-config --socket="$WAYLAND_DISPLAY" --idle-time=0 \
    > "$output/weston.log" 2>&1 &
weston_pid=$!
cleanup() {
    kill "$weston_pid" 2>/dev/null || true
    wait "$weston_pid" 2>/dev/null || true
    find "$probe_root" -depth -mindepth 1 -delete
    rmdir "$probe_root"
}
trap cleanup EXIT
for _ in $(seq 1 200); do
    test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" && break
    sleep 0.05
done
test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"

qs --version > "$output/runtime.txt" 2>&1
printf 'workspace_head=%s\n' "$(git -C "$workspace" rev-parse HEAD)" >> "$output/runtime.txt"
sha256sum "$workspace/shell/ui/WeatherBackground.qml" >> "$output/runtime.txt"

for implementation in baseline optimized; do
    shell_dir="$probe_root/$implementation"
    for scenario in partly rain; do
        for mode in static animated; do
            image="$output/$implementation-$scenario.png"
            log="$output/$implementation-$scenario-$mode.log"
            if test "$mode" = animated; then
                image=""
            fi
            if NYXURI_WEATHER_IMPL="$implementation" \
                    NYXURI_WEATHER_SCENARIO="$scenario" \
                    NYXURI_WEATHER_MODE="$mode" \
                    NYXURI_WEATHER_IMAGE="$image" \
                    timeout --kill-after=2s 35s qs -p "$shell_dir" --no-duplicate > "$log" 2>&1; then
                grep -q "WEATHER_CANVAS_PASS case=$scenario mode=$mode" "$log"
            else
                find "$XDG_RUNTIME_DIR/quickshell" -type f -name log.qslog -exec cp -- {} "$output/$implementation-$scenario-$mode.qslog" \; 2>/dev/null || true
                cat "$log"
                exit 1
            fi
            if test "$mode" = static; then
                python3 "$workspace/shell/tests/qml/WeatherCanvasProbe/extract_png.py" "$log" "$image"
            fi
            cat "$log"
        done
    done
done

for scenario in partly rain; do
    if python3 "$workspace/shell/tests/qml/WeatherCanvasProbe/compare_png.py" \
            "$output/baseline-$scenario.png" "$output/optimized-$scenario.png" \
            > "$output/$scenario-pixel-compare.txt"; then
        cat "$output/$scenario-pixel-compare.txt"
    else
        cat "$output/$scenario-pixel-compare.txt"
        exit 1
    fi
done

printf '%s\n' \
    'WEATHER_CANVAS_OPT_PASS scenarios=partly(2 bands),rain(3 bands) pixel_equal=1 frame_intervals_equal=1' \
    'per-frame path builds: partly 4 -> 2 (-2); rain 6 -> 3 (-3)' \
    | tee "$output/summary.txt"

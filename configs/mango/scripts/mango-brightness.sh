#!/usr/bin/env bash
# ==============================================================================
# Brightness controls for Mango (mango-brightness.sh)
# Laptop panel via Noctalia/brightnessctl, external DDC panel via ddcutil.
# ==============================================================================

set -uo pipefail

dir="${1:-}"
case "$dir" in
    up|down) ;;
    *)
        printf 'usage: mango-brightness.sh up|down\n' >&2
        exit 2
        ;;
esac

noctalia_ok=false
if command -v noctalia >/dev/null 2>&1; then
    if noctalia msg "brightness-${dir}" 2>/dev/null; then
        noctalia_ok=true
    fi
fi

connector=""
if command -v mmsg >/dev/null 2>&1; then
    connector="$(mmsg get cursorpos 2>/dev/null | jq -r '.monitor' 2>/dev/null || true)"
fi

backlight_dir="${NYXURI_BACKLIGHT_DIR:-${NYXNIRI_BACKLIGHT_DIR:-/sys/class/backlight}}"
has_backlight=false
if [ -d "$backlight_dir" ]; then
    for dev in "$backlight_dir"/*; do
        if [ -e "$dev" ]; then
            has_backlight=true
            break
        fi
    done
fi

if [ "$noctalia_ok" = false ] && [ "$has_backlight" = true ] && command -v brightnessctl >/dev/null 2>&1; then
    step="${NYXURI_BRIGHTNESS_STEP:-5%}"
    if [ "$dir" = "up" ]; then
        brightnessctl -q set "+${step}" 2>/dev/null || true
    else
        brightnessctl -q -n 2 set "${step}-" 2>/dev/null || true
    fi
fi

if [ -n "$connector" ] && command -v ddcutil >/dev/null 2>&1; then
    ddc_step="${NYXURI_DDC_STEP:-10}"
    op="+"
    [ "$dir" = "down" ] && op="-"
    ddcutil --noverify setvcp 10 "${op}${ddc_step}" 2>/dev/null || true
fi

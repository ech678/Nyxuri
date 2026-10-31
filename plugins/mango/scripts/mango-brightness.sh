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

backlight_dir="${NYXURI_BACKLIGHT_DIR:-/sys/class/backlight}"
has_backlight=false
if [ -d "$backlight_dir" ]; then
    for dev in "$backlight_dir"/*; do
        if [ -e "$dev" ]; then
            has_backlight=true
            break
        fi
    done
fi

is_internal=false
case "$connector" in
    eDP-*|LVDS-*|DSI-*)
        is_internal=true
        ;;
    "")
        if [ "$has_backlight" = true ]; then
            is_internal=true
        fi
        ;;
esac

if [ "$is_internal" = true ]; then
    if [ "$noctalia_ok" = false ] && command -v brightnessctl >/dev/null 2>&1; then
        step="${NYXURI_BRIGHTNESS_STEP:-5%}"
        if [ "$dir" = "up" ]; then
            brightnessctl -q set "+${step}" 2>/dev/null || true
        else
            brightnessctl -q -n 2 set "${step}-" 2>/dev/null || true
        fi
    fi
    exit 0
fi

# Unknown connector on a machine that already has a sysfs backlight: treat
# as internal so NVIDIA laptops do not hit an I2C timeout on every keypress.
if [ -z "$connector" ] && [ "$has_backlight" = true ]; then
    exit 0
fi

noctalia_ddc=false
conf="${XDG_CONFIG_HOME:-$HOME/.config}/noctalia/noctalia-config.toml"
if [ -f "$conf" ] && grep -E '^[[:space:]]*enable_ddcutil[[:space:]]*=[[:space:]]*true\b' "$conf" >/dev/null 2>&1; then
    noctalia_ddc=true
fi
# Noctalia already owns DDC on this host; do not apply a second step.
if [ "$noctalia_ddc" = true ]; then
    exit 0
fi

if ! command -v ddcutil >/dev/null 2>&1; then
    exit 0
fi

ddc_step="${NYXURI_DDC_STEP:-10}"
op="+"
[ "$dir" = "down" ] && op="-"
ddcutil --noverify setvcp 10 "${op}${ddc_step}" 2>/dev/null || true

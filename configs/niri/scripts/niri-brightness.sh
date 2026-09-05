#!/usr/bin/env bash
# Brightness keys: laptop backlight via Noctalia, external DDC via ddcutil.
#
# NyxNiri keeps Noctalia [brightness] enable_ddcutil = false so the shell
# does not scan I2C at startup (NVIDIA hang). Internal panels also do not
# speak DDC/CI, so the old niri bind (`ddcutil setvcp 10 ± 10`) was a no-op
# on laptops. This script restores both paths without turning DDC discovery
# back on inside Noctalia.

set -uo pipefail

dir="${1:-}"
case "$dir" in
    up|down) ;;
    *)
        printf 'usage: niri-brightness.sh up|down\n' >&2
        exit 2
        ;;
esac

if command -v noctalia >/dev/null 2>&1; then
    noctalia msg "brightness-${dir}" || true
fi

connector=""
if command -v niri >/dev/null 2>&1; then
    connector="$(niri msg focused-output 2>/dev/null | sed -n '1s/.*(\([^)]*\))$/\1/p')"
fi

case "$connector" in
    eDP-*|LVDS-*|DSI-*)
        exit 0
        ;;
esac

backlight_dir="${NYXNIRI_BACKLIGHT_DIR:-/sys/class/backlight}"
has_backlight=false
if [ -d "$backlight_dir" ]; then
    for dev in "$backlight_dir"/*; do
        if [ -e "$dev" ]; then
            has_backlight=true
            break
        fi
    done
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

if [ "$dir" = up ]; then
    ddcutil setvcp 10 + 10 >/dev/null 2>&1 || true
else
    ddcutil setvcp 10 - 10 >/dev/null 2>&1 || true
fi

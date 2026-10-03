#!/usr/bin/env bash
set -euo pipefail

if command -v brightnessctl >/dev/null 2>&1; then
    out=$(brightnessctl -m -c backlight info 2>/dev/null | head -n1 || true)
    if [ -n "$out" ]; then
        echo "$out"
        exit 0
    fi
fi

if [ -d /sys/class/backlight ]; then
    for d in /sys/class/backlight/*; do
        if [ -d "$d" ]; then
            b=$(cat "$d/brightness" 2>/dev/null || true)
            m=$(cat "$d/max_brightness" 2>/dev/null || true)
            dev=$(basename "$d")
            if [ -n "$b" ] && [ -n "$m" ]; then
                echo "$dev,backlight,$b,0,$m"
                exit 0
            fi
        fi
    done
fi

echo ""

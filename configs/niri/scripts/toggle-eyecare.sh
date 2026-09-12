#!/bin/bash
# NyxNiri EyeCare One-shot Self-Healing Toggle & Sync Script
# Zero background process besides wlsunset itself. Runs in < 2ms then exits.
#
# shellcheck disable=SC2317  # commands invoked via ||/&& intentional control flow
set -uo pipefail

# Ensure strict serialization to prevent any race conditions during rapid toggles or startup.
exec 9> "${XDG_RUNTIME_DIR:-/tmp}/nyxniri-${UID}-eyecare.lock"
flock -w 5 9 || exit 1
#
# On/off state is derived from where effects.kdl points (eyecare target = ON)
# rather than tracked in a separate state file or inferred from the wlsunset
# process. effects.kdl survives niri restarts and is reset to Normal only by a
# config redeploy, so it is the persistent source of truth; wlsunset is the
# fragile runtime side (it can die or be missing on a fresh install) and is
# reconciled to the symlink state in --sync, so a dead wlsunset can never
# trap the toggle in EyeCare mode.

NIRI_DIR="$HOME/.config/niri"
EFFECTS_LINK="$NIRI_DIR/effects.kdl"
NORMAL_EFFECTS="$NIRI_DIR/effects_normal.kdl"
EYECARE_EFFECTS="$NIRI_DIR/effects_eyecare.kdl"

# Desired EyeCare warm color temperature (in Kelvin: 5500K for subtle natural warmth)
EYECARE_TEMP=5500

# Log for reload failures / self-healing events (empty on success)
LOG_FILE="${XDG_RUNTIME_DIR:-/tmp}/nyxniri-eyecare.log"

HAS_NOCTALIA=false
if command -v noctalia >/dev/null 2>&1; then
    HAS_NOCTALIA=true
fi

CURRENTLY_ON=false
if [ "$(readlink "$EFFECTS_LINK" 2>/dev/null)" = "$EYECARE_EFFECTS" ]; then
    CURRENTLY_ON=true
fi

# Point effects.kdl at the given target, then explicitly reload niri so
# window opacity/blur pick it up even if the file watcher misses the symlink
# swap. Safe to call repeatedly/idempotently.
apply_effects() {
    local target
    if [ "$1" = "on" ]; then
        target="$EYECARE_EFFECTS"
    else
        target="$NORMAL_EFFECTS"
    fi

    ln -sfn "$target" "$EFFECTS_LINK"
    if [ "$(readlink "$EFFECTS_LINK" 2>/dev/null)" != "$target" ]; then
        echo "$(date '+%F %T') [eyecare] symlink swap failed (target=$target)" >> "$LOG_FILE"
    fi

    if command -v niri >/dev/null 2>&1; then
        if ! niri msg action load-config-file >>"$LOG_FILE" 2>&1; then
            sleep 0.2
            niri msg action load-config-file >>"$LOG_FILE" 2>&1 || true
        fi
    fi
}

# --sync: idempotent reconciliation only (no toggling). Called from niri's
# spawn-at-startup so a niri restart re-aligns wlsunset with whatever
# effects.kdl actually points to (the persistent state), instead of staying
# stuck on a stale process state until the next manual toggle.
# Deterministic rebuild: unconditionally drop any leftover warm engine (a
# wlsunset orphaned by a previous session still matches pgrep but its gamma
# connection died with the old niri), then start a fresh one if EyeCare is ON.
# This keeps EyeCare consistent across logout/login on the persisted symlink.
if [ "${1:-}" = "--sync" ]; then
    link_target="$(readlink "$EFFECTS_LINK" 2>/dev/null || true)"
    if [ "$link_target" != "$EYECARE_EFFECTS" ] && [ "$link_target" != "$NORMAL_EFFECTS" ]; then
        # effects.kdl missing/broken (manual deletion): recreate as Normal.
        ln -sfn "$NORMAL_EFFECTS" "$EFFECTS_LINK"
        CURRENTLY_ON=false
        echo "$(date '+%F %T') [eyecare] healed broken effects.kdl -> Normal" >> "$LOG_FILE"
        if command -v niri >/dev/null 2>&1; then
            niri msg action load-config-file >>"$LOG_FILE" 2>&1 || true
        fi
    fi
    # 阻塞等待 1 秒，确保 Wayland 和 Noctalia IPC 完全启动
    sleep 1
    if [ "$HAS_NOCTALIA" = "true" ]; then
        noctalia msg nightlight-disable 2>/dev/null || true
    fi
    pkill -x wlsunset 2>/dev/null || true
    if [ "$CURRENTLY_ON" = "true" ]; then
        if command -v wlsunset >/dev/null 2>&1; then
            nohup wlsunset -T 6500 -t "$EYECARE_TEMP" -d 0.3 -S 00:00 -s 00:00 >/dev/null 2>&1 9>&- &
        fi
    fi
    exit 0
fi

# 1. Pre-execution Self-Healing: Force Noctalia to release Wayland gamma lock
if [ "$HAS_NOCTALIA" = "true" ]; then
    noctalia msg nightlight-disable 2>/dev/null || true
fi
pkill -x wlsunset 2>/dev/null || true

IS_TURNING_ON=false

if [ "$CURRENTLY_ON" = "true" ]; then
    # --- Turning EyeCare Mode OFF ---
    apply_effects off
else
    # --- Turning EyeCare Mode ON ---
    apply_effects on
    IS_TURNING_ON=true
fi

# 3. Smoothly ramp color temperature over 0.3s without GPU pipeline tearing
if [ "$IS_TURNING_ON" = "true" ]; then
    sleep 0.05
    nohup wlsunset -T 6500 -t "$EYECARE_TEMP" -d 0.3 -S 00:00 -s 00:00 >/dev/null 2>&1 9>&- &
fi

# 4. Visual Notification
if [ "$IS_TURNING_ON" = "true" ]; then
    notify-send -t 2000 "Eye Care : On"
else
    notify-send -t 2000 "Eye Care : Off"
fi

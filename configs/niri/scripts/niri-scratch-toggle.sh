#!/bin/bash
# NyxNiri Multi-App Scratchpad Toggle
# Controls floating scratchpad lifecycle for Kitty, Mission Center, Nautilus, and custom apps.

# shellcheck disable=SC2317
set -uo pipefail

TARGET_APP="${1:-kitty}"

# ── Serialization Lock ──────────────────────────────────────────────
LOCK_NAME=$(printf '%s' "$TARGET_APP" | tr -c 'a-zA-Z0-9_' '_')
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/nyxniri-scratch-${LOCK_NAME}.lock"
flock -n 9 || exit 0

case "$TARGET_APP" in
    kitty|terminal|Kitty|Terminal)
        APP_ID="scratchpad"
        TMUX_SESSION="scratch"

        ACTIVE_WS=$(niri msg -j workspaces 2>/dev/null \
            | jq -r '(.[] | select(.is_focused == true) | .id) // (.[] | select(.is_active == true) | .id)' \
            | head -n1)

        read -r win_id win_ws < <(niri msg -j windows 2>/dev/null \
            | jq -r --arg id "$APP_ID" \
                '.[] | select(.app_id == $id) | "\(.id) \(.workspace_id)"' \
            | head -n1)

        spawn_kitty() {
            if command -v tmux >/dev/null 2>&1; then
                niri msg action spawn -- \
                    kitty --app-id "$APP_ID" --title "Scratchpad" \
                    tmux new-session -A -D -s "$TMUX_SESSION" \
                    "fish -C 'function fish_greeting; end' -C 'set -g fish_history scratchpad'" \
                    \; set-option status off \
                    \; set-option mouse on \
                    \; set-option history-limit 50000
            else
                niri msg action spawn -- \
                    kitty --app-id "$APP_ID" --title "Scratchpad"
            fi
        }

        if [ -z "${win_id:-}" ]; then
            spawn_kitty
        elif [ -n "$ACTIVE_WS" ] && [ -n "${win_ws:-}" ] && [ "$win_ws" != "$ACTIVE_WS" ]; then
            # Relocate from other workspace to current active workspace
            niri msg action close-window --id "$win_id"
            sleep 0.05
            spawn_kitty
        else
            # On current workspace -> toggle off
            niri msg action close-window --id "$win_id"
        fi
        ;;

    missioncenter|monitor|"mission center"|"Mission Center"|MissionCenter)
        APP_ID="io.missioncenter.MissionCenter"

        ACTIVE_WS=$(niri msg -j workspaces 2>/dev/null \
            | jq -r '(.[] | select(.is_focused == true) | .id) // (.[] | select(.is_active == true) | .id)' \
            | head -n1)

        read -r win_id win_ws < <(niri msg -j windows 2>/dev/null \
            | jq -r --arg id "$APP_ID" \
                '.[] | select(.app_id == $id) | "\(.id) \(.workspace_id)"' \
            | head -n1)

        if [ -z "${win_id:-}" ]; then
            if command -v missioncenter >/dev/null 2>&1; then
                niri msg action spawn -- missioncenter
            elif command -v flatpak >/dev/null 2>&1 && flatpak info io.missioncenter.MissionCenter >/dev/null 2>&1; then
                niri msg action spawn -- flatpak run io.missioncenter.MissionCenter
            fi
        elif [ -n "$ACTIVE_WS" ] && [ -n "${win_ws:-}" ] && [ "$win_ws" != "$ACTIVE_WS" ]; then
            niri msg action focus-window --id "$win_id"
        else
            niri msg action close-window --id "$win_id"
        fi
        ;;

    nautilus|files|Nautilus|Files)
        APP_ID="org.gnome.Nautilus"

        ACTIVE_WS=$(niri msg -j workspaces 2>/dev/null \
            | jq -r '(.[] | select(.is_focused == true) | .id) // (.[] | select(.is_active == true) | .id)' \
            | head -n1)

        read -r win_id win_ws < <(niri msg -j windows 2>/dev/null \
            | jq -r --arg id "$APP_ID" \
                '.[] | select(.app_id == $id) | "\(.id) \(.workspace_id)"' \
            | head -n1)

        if [ -z "${win_id:-}" ]; then
            niri msg action spawn -- nautilus --new-window
        elif [ -n "$ACTIVE_WS" ] && [ -n "${win_ws:-}" ] && [ "$win_ws" != "$ACTIVE_WS" ]; then
            niri msg action focus-window --id "$win_id"
        else
            niri msg action close-window --id "$win_id"
        fi
        ;;

    wallpaper|wallpapers|"wallpaper-picker"|WallpaperPicker|*wallpaper-picker.py)
        if [ -f "$HOME/.config/niri/scripts/wallpaper-picker.py" ]; then
            niri msg action spawn -- "$HOME/.config/niri/scripts/wallpaper-picker.py"
        elif [ -f "${BASH_SOURCE%/*}/wallpaper-picker.py" ]; then
            niri msg action spawn -- "${BASH_SOURCE%/*}/wallpaper-picker.py"
        else
            niri msg action spawn -- wallpaper-picker.py
        fi
        ;;


    *)
        # Custom command or script execution
        if [[ "$TARGET_APP" =~ ^~.* ]]; then
            TARGET_APP="${TARGET_APP/#\~/$HOME}"
        fi
        if [ "$TARGET_APP" = "clean-cache.py" ] && [ -x "$HOME/.config/fish/clean-cache.py" ]; then
            TARGET_APP="$HOME/.config/fish/clean-cache.py"
        fi

        # If it is clean-cache or interactive terminal tool, launch inside floating scratchpad terminal
        if [ "$TARGET_APP" = "$HOME/.config/fish/clean-cache.py" ] || [[ "$TARGET_APP" == *clean-cache.py* ]]; then
            niri msg action spawn -- kitty --app-id "scratchpad" -e /bin/bash "$TARGET_APP"
        elif [ -x "$TARGET_APP" ] || command -v "$TARGET_APP" >/dev/null 2>&1; then
            niri msg action spawn -- "$TARGET_APP"
        else
            # No shell-string execution: menu cmds are data, not commands to
            # interpret. Wrap anything fancier in a script and point cmd at it.
            printf 'niri-scratch-toggle: refusing to run "%s" as a shell command\n' "$TARGET_APP" >&2
        fi
        ;;
esac


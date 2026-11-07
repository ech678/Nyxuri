#!/bin/bash
# Nyxuri multi-app scratchpad toggle
# Controls floating scratchpad lifecycle for Kitty, Mission Center, Nautilus, and custom apps.

# shellcheck disable=SC2317
set -uo pipefail

is_plugin_enabled() {
    local pid="$1"
    local state_root="${XDG_STATE_HOME:-$HOME/.local/state}"
    local state_file="$state_root/nyxuri/state.json"
    [ ! -r "$state_file" ] && [ -r "$state_root/NyxNiri/state.json" ] && state_file="$state_root/NyxNiri/state.json"
    [ -r "$state_file" ] || return 0
    if command -v jq >/dev/null 2>&1; then
        local st
        st=$(jq -r --arg p "$pid" '.plugins[$p].state // empty' "$state_file" 2>/dev/null)
        [ "$st" != "disabled" ] && return 0
        return 1
    fi
    python3 -c "import json, sys; d=json.load(open('$state_file')).get('plugins', {}).get('$pid', {}); sys.exit(1 if d.get('state') == 'disabled' else 0)" 2>/dev/null
}

find_action_tool() {
    local target_act="$1"
    local data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
    local config_home="${XDG_CONFIG_HOME:-$HOME/.config}"

    # 1. Search living and data paths for third-party Nyxuri plugins
    local dir
    for dir in "$config_home/nyxuri/plugins" "$data_home/nyxuri/plugins"; do
        [ -d "$dir" ] || continue
        for p in "$dir"/*; do
            [ -d "$p" ] || continue
            is_plugin_enabled "${p##*/}" || continue
            for exe in "$p"/*"$target_act"* "$p"/tools/*"$target_act"*; do
                [ -f "$exe" ] || continue
                case "$exe" in *.toml|*.json|*.txt|*.md|*.bak|*.backup*|*~) continue ;; esac
                if [ -x "$exe" ] || [[ "$exe" == *.py || "$exe" == *.sh ]]; then
                    printf "%s" "$exe"
                    return 0
                fi
            done
        done
    done

    # 2. Legacy Noctalia tools (only if noctalia is enabled)
    if is_plugin_enabled "noctalia" && [ -d "$config_home/noctalia/tools" ]; then
        for exe in "$config_home/noctalia/tools"/*"$target_act"*; do
            [ -f "$exe" ] || continue
            case "$exe" in *.toml|*.json|*.txt|*.md|*.bak|*.backup*|*~) continue ;; esac
            if [ -x "$exe" ] || [[ "$exe" == *.py || "$exe" == *.sh ]]; then
                local base="${exe##*/}"
                local stem="${base%.*}"
                is_plugin_enabled "$stem" || continue
                printf "%s" "$exe"
                return 0
            fi
        done
    fi

    # 3. Command on PATH
    if command -v "$target_act" >/dev/null 2>&1; then
        command -v "$target_act"
        return 0
    fi
    return 1
}

TARGET_APP="${1:-kitty}"

# ── Serialization Lock ──────────────────────────────────────────────
LOCK_NAME=$(printf '%s' "$TARGET_APP" | tr -c 'a-zA-Z0-9_' '_')
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/nyxuri-${UID}-scratch-${LOCK_NAME}.lock"
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
        if [ -f "$HOME/.config/noctalia/tools/wallpaper-picker.py" ]; then
            niri msg action spawn -- "$HOME/.config/noctalia/tools/wallpaper-picker.py"
        elif [ -f "$(dirname "${BASH_SOURCE[0]}")/../../noctalia/tools/wallpaper-picker.py" ]; then
            niri msg action spawn -- "$(dirname "${BASH_SOURCE[0]}")/../../noctalia/tools/wallpaper-picker.py"
        else
            niri msg action spawn -- wallpaper-picker.py
        fi
        ;;

    translate|translate-settings|Translate)
        # Settings TUI in the floating scratchpad Kitty; the popup itself is Alt+E.
        tool="$(find_action_tool "translate")"
        if [ -z "$tool" ]; then
            tool="${XDG_CONFIG_HOME:-$HOME/.config}/noctalia/tools/orbit-translate.py"
            fallback_base="${tool##*/}"
            fallback_stem="${fallback_base%.*}"
            if ! is_plugin_enabled "$fallback_stem"; then
                echo "Translate tool not found or disabled." >&2
                exit 1
            fi
        fi
        niri msg action spawn -- kitty --app-id "scratchpad" --title "Translate" \
            -e "$tool" --settings
        ;;

    clean|clean-cache.py|\~/.config/fish/clean-cache.py|"$HOME/.config/fish/clean-cache.py")
        # Older preserved Orbit menus still carry the former script path.
        niri msg action spawn -- kitty --app-id "scratchpad" -e nyxuri clean
        ;;

    *)
        # Custom command or script execution
        if [[ "$TARGET_APP" =~ ^~.* ]]; then
            TARGET_APP="${TARGET_APP/#\~/$HOME}"
        fi
        if [ -x "$TARGET_APP" ] || command -v "$TARGET_APP" >/dev/null 2>&1; then
            niri msg action spawn -- "$TARGET_APP"
        else
            # No shell-string execution: menu cmds are data, not commands to
            # interpret. Wrap anything fancier in a script and point cmd at it.
            printf 'niri-scratch-toggle: refusing to run "%s" as a shell command\n' "$TARGET_APP" >&2
        fi
        ;;
esac

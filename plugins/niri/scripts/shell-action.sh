#!/usr/bin/env bash
# ==============================================================================
# Nyxuri shell action gateway (shell-action.sh)
# Unified dispatch gateway decoupling desktop shell actions from compositor keybinds.
# ==============================================================================

set -euo pipefail

action="${1:-}"

state_root="${XDG_STATE_HOME:-$HOME/.local/state}"
state_file="$state_root/nyxuri/state.json"
if [ ! -r "$state_file" ] && [ -r "$state_root/NyxNiri/state.json" ]; then
    state_file="$state_root/NyxNiri/state.json"
fi
active_shell="noctalia"
if [ -r "$state_file" ]; then
    if grep -Eq '"active_shell"[[:space:]]*:[[:space:]]*"(nyxuri-shell|custom)"' "$state_file" 2>/dev/null; then
        active_shell="nyxuri-shell"
    fi
fi

if [ "$active_shell" = "nyxuri-shell" ] || [ "$active_shell" = "custom" ]; then
    custom_shell_bin="${NYXURI_CUSTOM_SHELL_BIN:-}"
    if [ -z "$custom_shell_bin" ] && [ -r "$state_file" ]; then
        custom_bin_json=$(grep -o '"custom_shell_bin"[[:space:]]*:[[:space:]]*"[^"]*"' "$state_file" 2>/dev/null | head -n 1 | sed 's/.*"[[:space:]]*:[[:space:]]*"//;s/"//' || true)
        if [ -n "$custom_bin_json" ]; then
            custom_shell_bin="$custom_bin_json"
        fi
    fi

    if [ -z "$custom_shell_bin" ] && command -v nyxuri-shell >/dev/null 2>&1; then
        custom_shell_bin=$(command -v nyxuri-shell)
    fi

    if [ -n "$custom_shell_bin" ] && [ ! -x "$custom_shell_bin" ]; then
        healed="${custom_shell_bin%/bin/nyxuri-shell}/nyxuri-shell"
        if [ -x "$healed" ]; then
            custom_shell_bin="$healed"
        fi
    fi

    if [ -n "$custom_shell_bin" ] && [ -x "$custom_shell_bin" ]; then
        exec "$custom_shell_bin" --action "$action"
    else
        echo "Warning: Nyxuri shell binary is missing or not executable (${custom_shell_bin:-none}), falling back to Noctalia." >&2
    fi
fi

is_plugin_enabled() {
    local pid="$1"
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
    local config_home="$HOME/.config"

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

case "$action" in
    launcher)
        exec noctalia msg panel-toggle launcher
        ;;
    session)
        exec noctalia msg panel-toggle session
        ;;
    settings)
        exec noctalia msg settings-toggle
        ;;
    clipboard)
        exec noctalia msg panel-toggle clipboard
        ;;
    lock)
        exec noctalia msg session lock
        ;;
    wallpaper-random)
        exec noctalia msg wallpaper-random
        ;;
    wallpaper-picker)
        tool="$(find_action_tool "wallpaper-picker")" || {
            echo "Wallpaper picker tool not found or disabled." >&2
            exit 1
        }
        if [ -x "$tool" ]; then
            exec "$tool"
        fi
        exec python3 "$tool"
        ;;
    radial-launcher)
        tool="$(find_action_tool "launcher")" || {
            echo "Launcher tool not found or disabled." >&2
            exit 1
        }
        if [ -x "$tool" ]; then
            exec "$tool"
        fi
        exec python3 "$tool"
        ;;
    translate)
        tool="$(find_action_tool "translate")" || {
            echo "Translate tool not found or disabled." >&2
            exit 1
        }
        if [ -x "$tool" ]; then
            exec "$tool"
        fi
        exec python3 "$tool"
        ;;
    *)
        echo "Unknown shell action: $action" >&2
        echo "Usage: $0 {launcher|session|settings|clipboard|lock|wallpaper-random|wallpaper-picker|radial-launcher|translate}" >&2
        exit 1
        ;;
esac

#!/usr/bin/env bash
# ==============================================================================
# NyxNiri Shell Action Gateway (shell-action.sh)
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
    if grep -q '"active_shell"[[:space:]]*:[[:space:]]*"custom"' "$state_file" 2>/dev/null; then
        active_shell="custom"
    fi
fi

if [ "$active_shell" = "custom" ]; then
    custom_shell_bin="${NYXURI_CUSTOM_SHELL_BIN:-${NYXNIRI_CUSTOM_SHELL_BIN:-}}"
    if [ -z "$custom_shell_bin" ] && [ -r "$state_file" ]; then
        custom_bin_json=$(grep -o '"custom_shell_bin"[[:space:]]*:[[:space:]]*"[^"]*"' "$state_file" 2>/dev/null | head -n 1 | sed 's/.*"[[:space:]]*:[[:space:]]*"//;s/"//' || true)
        if [ -n "$custom_bin_json" ]; then
            custom_shell_bin="$custom_bin_json"
        fi
    fi

    if [ -n "$custom_shell_bin" ] && [ -x "$custom_shell_bin" ]; then
        exec "$custom_shell_bin" --action "$action"
    else
        echo "Warning: Custom shell binary is missing or not executable (${custom_shell_bin:-none}), falling back to Noctalia." >&2
    fi
fi

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
        tools_dir="${XDG_CONFIG_HOME:-$HOME/.config}/noctalia/tools"
        if [ -x "$tools_dir/wallpaper-picker.py" ]; then
            exec "$tools_dir/wallpaper-picker.py"
        fi
        exec python3 "$tools_dir/wallpaper-picker.py"
        ;;
    radial-launcher)
        tools_dir="${XDG_CONFIG_HOME:-$HOME/.config}/noctalia/tools"
        if [ -x "$tools_dir/orbit-launcher.py" ]; then
            exec "$tools_dir/orbit-launcher.py"
        fi
        exec python3 "$tools_dir/orbit-launcher.py"
        ;;
    *)
        echo "Unknown shell action: $action" >&2
        echo "Usage: $0 {launcher|session|settings|clipboard|lock|wallpaper-random|wallpaper-picker|radial-launcher}" >&2
        exit 1
        ;;
esac

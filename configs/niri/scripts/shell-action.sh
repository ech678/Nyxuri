#!/usr/bin/env bash
# ==============================================================================
# NyxNiri Shell Action Gateway (shell-action.sh)
# Unified dispatch gateway decoupling desktop shell actions from compositor keybinds.
# ==============================================================================

set -euo pipefail

action="${1:-}"

state_root="${XDG_STATE_HOME:-$HOME/.local/state}"
state_file="$state_root/NyxNiri/state.json"
active_shell="noctalia"
if [ -r "$state_file" ]; then
    if grep -q '"active_shell"[[:space:]]*:[[:space:]]*"custom"' "$state_file" 2>/dev/null; then
        active_shell="custom"
    fi
fi

if [ "$active_shell" = "custom" ]; then
    : "${NYXNIRI_CUSTOM_SHELL_BIN:?active_shell=custom requires NYXNIRI_CUSTOM_SHELL_BIN}"
    if [ ! -x "$NYXNIRI_CUSTOM_SHELL_BIN" ]; then
        echo "Custom shell is not executable: $NYXNIRI_CUSTOM_SHELL_BIN" >&2
        exit 1
    fi
    exec "$NYXNIRI_CUSTOM_SHELL_BIN" --action "$action"
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
    *)
        echo "Unknown shell action: $action" >&2
        echo "Usage: $0 {launcher|session|settings|clipboard|lock|wallpaper-random}" >&2
        exit 1
        ;;
esac

#!/usr/bin/env bash
# ==============================================================================
# NyxNiri Shell Action Gateway (shell-action.sh)
# Unified dispatch gateway decoupling desktop shell actions from compositor keybinds.
# ==============================================================================

set -euo pipefail

action="${1:-}"

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

#!/usr/bin/env bash
# ==============================================================================
# NyxNiri Session Shell Gateway (session-shell.sh)
# Launches desktop shell and cleans up leftover compositor session scopes.
# ==============================================================================

set -euo pipefail

systemctl --user stop 'app-niri-noctalia-*.scope' >/dev/null 2>&1 || true

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
        exec "$custom_shell_bin"
    else
        (
            sleep 2
            notify-send -u critical -a "Nyxuri" "Nyxuri Desktop Shell" \
                "自研 Shell 启动失败，已平滑回退至 Noctalia\nCustom shell failed to launch, fell back to Noctalia."
        ) >/dev/null 2>&1 &
        echo "Custom shell (${custom_shell_bin:-<unset>}) is not executable, falling back to Noctalia" >&2
    fi
fi
exec noctalia

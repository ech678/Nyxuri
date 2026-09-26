#!/usr/bin/env bash
# ==============================================================================
# NyxNiri Session Shell Gateway (session-shell.sh)
# Launches desktop shell and cleans up leftover compositor session scopes.
# ==============================================================================

set -euo pipefail

systemctl --user stop 'app-niri-noctalia-*.scope' >/dev/null 2>&1 || true

state_root="${XDG_STATE_HOME:-$HOME/.local/state}"
state_file="$state_root/NyxNiri/state.json"
active_shell="noctalia"
if [ -r "$state_file" ]; then
    if grep -q '"active_shell"[[:space:]]*:[[:space:]]*"custom"' "$state_file" 2>/dev/null; then
        active_shell="custom"
    fi
fi

if [ "$active_shell" = "custom" ]; then
    if [ -z "${NYXNIRI_CUSTOM_SHELL_BIN:-}" ] && [ -r "$state_file" ]; then
        custom_bin_json=$(grep -o '"custom_shell_bin"[[:space:]]*:[[:space:]]*"[^"]*"' "$state_file" 2>/dev/null | head -n 1 | sed 's/.*"[[:space:]]*:[[:space:]]*"//;s/"//' || true)
        if [ -n "$custom_bin_json" ]; then
            NYXNIRI_CUSTOM_SHELL_BIN="$custom_bin_json"
        fi
    fi

    if [ -n "${NYXNIRI_CUSTOM_SHELL_BIN:-}" ] && [ -x "$NYXNIRI_CUSTOM_SHELL_BIN" ]; then
        exec "$NYXNIRI_CUSTOM_SHELL_BIN"
    else
        (
            sleep 2
            notify-send -u critical -a "NyxNiri" "NyxNiri Desktop Shell" \
                "自研 Shell 启动失败，已平滑回退至 Noctalia\nCustom shell failed to launch, fell back to Noctalia."
        ) >/dev/null 2>&1 &
        echo "Custom shell (${NYXNIRI_CUSTOM_SHELL_BIN:-<unset>}) is not executable, falling back to Noctalia" >&2
    fi
fi
exec noctalia

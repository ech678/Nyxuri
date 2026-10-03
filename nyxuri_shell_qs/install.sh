#!/usr/bin/env bash
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
LIB_DIR="${HOME}/.local/share/nyxuri-shell-qs"
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nyxuri-shell-qs"

mkdir -p "$BIN_DIR" "$LIB_DIR" "$CONF_DIR"

cp -f "$SELF_DIR/shell.qml" "$LIB_DIR/" 2>/dev/null
cp -f "$SELF_DIR/Theme.qml" "$LIB_DIR/" 2>/dev/null
cp -f "$SELF_DIR/Capsule.qml" "$LIB_DIR/" 2>/dev/null
cp -f "$SELF_DIR/Bar.qml" "$LIB_DIR/" 2>/dev/null
cp -f "$SELF_DIR/Panel.qml" "$LIB_DIR/" 2>/dev/null
cp -f "$SELF_DIR/Orbit.qml" "$LIB_DIR/" 2>/dev/null
cp -f "$SELF_DIR/Osd.qml" "$LIB_DIR/" 2>/dev/null

rm -rf "$LIB_DIR/core" "$LIB_DIR/panels"
cp -r "$SELF_DIR/core" "$LIB_DIR/core"
cp -r "$SELF_DIR/panels" "$LIB_DIR/panels"

if [ ! -f "$CONF_DIR/groups.json" ]; then
    printf '{\n  "groups": []\n}\n' > "$CONF_DIR/groups.json"
fi

cat > "$BIN_DIR/nyxuri-shell-qs" <<'LAUNCHER'
#!/usr/bin/env bash
set -uo pipefail

SELF="$0"
LIB="${HOME}/.local/share/nyxuri-shell-qs"
QS="${NYXURI_QS_BIN:-}"

if [ -z "$QS" ]; then
    for c in quickshell qs; do
        if command -v "$c" >/dev/null 2>&1; then QS="$(command -v "$c")"; break; fi
    done
fi
if [ -z "$QS" ]; then
    for c in /usr/local/bin/quickshell /usr/bin/quickshell /opt/quickshell/bin/quickshell; do
        if [ -x "$c" ]; then QS="$c"; break; fi
    done
fi
if [ -z "$QS" ]; then
    echo "nyxuri-shell-qs: quickshell binary not found" >&2
    exit 1
fi

running() {
    pgrep -f "quickshell.*-p[[:space:]]*$LIB" >/dev/null 2>&1
}

dispatch() {
    "$QS" -p "$LIB" ipc call nyxuri open "$1" >/dev/null 2>&1
}

case "${1:-}" in
    --action)
        action="${2:-}"
        if [ -z "$action" ]; then
            echo "nyxuri-shell-qs: missing action" >&2
            exit 2
        fi
        if ! running; then
            NYXURI_QS_ACTION="" setsid "$QS" -p "$LIB" >/dev/null 2>&1 &
            for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
                sleep 0.15
                running && break
            done
            sleep 0.4
        fi
        dispatch "$action"
        exit 0
        ;;
    --toggle)
        action="${2:-}"
        if ! running; then
            NYXURI_QS_ACTION="" setsid "$QS" -p "$LIB" >/dev/null 2>&1 &
            for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
                sleep 0.15
                running && break
            done
            sleep 0.4
        fi
        "$QS" -p "$LIB" ipc call nyxuri toggle "$action" >/dev/null 2>&1
        exit 0
        ;;
    --status)
        if running; then
            echo "running"
            "$QS" -p "$LIB" ipc call nyxuri status 2>/dev/null || true
        else
            echo "stopped"
        fi
        exit 0
        ;;
    --stop)
        pkill -f "quickshell.*-p[[:space:]]*$LIB" >/dev/null 2>&1
        exit 0
        ;;
    --restart)
        pkill -f "quickshell.*-p[[:space:]]*$LIB" >/dev/null 2>&1
        sleep 0.5
        exec "$QS" -p "$LIB"
        ;;
    --daemon)
        exec "$QS" -p "$LIB" -d
        ;;
    --ipc)
        shift
        exec "$QS" -p "$LIB" ipc "$@"
        ;;
    --help|-h)
        cat <<EOF
nyxuri-shell-qs - Quickshell desktop shell

usage:
  nyxuri-shell-qs                 run in foreground
  nyxuri-shell-qs --daemon        run detached
  nyxuri-shell-qs --action NAME   run action (starts shell if needed)
  nyxuri-shell-qs --toggle NAME   toggle a panel
  nyxuri-shell-qs --status        print running state
  nyxuri-shell-qs --stop          stop the shell
  nyxuri-shell-qs --restart       restart the shell

actions:
  launcher session settings clipboard lock
  wallpaper-random wallpaper-picker radial-launcher
  notifications tray sysmon calendar
  volume-up volume-down volume-mute
  workspace-next workspace-prev quit
EOF
        exit 0
        ;;
    "")
        exec "$QS" -p "$LIB"
        ;;
    *)
        exec "$QS" -p "$LIB" "$@"
        ;;
esac
LAUNCHER

chmod +x "$BIN_DIR/nyxuri-shell-qs"

cat > "$BIN_DIR/nyxuri-shell-qs-session" <<'SESSION'
#!/usr/bin/env bash
set -uo pipefail
LIB="${HOME}/.local/share/nyxuri-shell-qs"
QS="${NYXURI_QS_BIN:-}"
if [ -z "$QS" ]; then
    for c in quickshell qs; do
        if command -v "$c" >/dev/null 2>&1; then QS="$(command -v "$c")"; break; fi
    done
fi
if [ -z "$QS" ]; then
    echo "nyxuri-shell-qs-session: quickshell binary not found" >&2
    exit 1
fi
exec "$QS" -p "$LIB"
SESSION

chmod +x "$BIN_DIR/nyxuri-shell-qs-session"

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/nyxuri"
mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/state.json"

if [ -f "$STATE_FILE" ]; then
    python3 - "$STATE_FILE" "$BIN_DIR/nyxuri-shell-qs-session" <<'PY'
import json, sys
path, binp = sys.argv[1], sys.argv[2]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    data = {}
data["active_shell"] = "custom"
data["custom_shell_bin"] = binp
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY
fi

echo "installed:"
echo "  $BIN_DIR/nyxuri-shell-qs"
echo "  $BIN_DIR/nyxuri-shell-qs-session"
echo "  $LIB_DIR"
if [ -f "$STATE_FILE" ]; then
    echo "  registered as custom shell in $STATE_FILE"
fi
echo
echo "run now:  nyxuri-shell-qs"
echo "detached: nyxuri-shell-qs --daemon"
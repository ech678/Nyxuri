#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/nyxuri-shell"
ENTRY="${SRC_DIR}/nyxuri_shell/__main__.py"

if [ ! -f "$ENTRY" ]; then
    echo "[x] source incomplete: $ENTRY missing" >&2
    exit 1
fi

mkdir -p "$BIN_DIR"

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 -I -c 'import sys; sys.path.insert(0, "${SRC_DIR}"); sys.argv[0] = "nyxuri-shell"; from nyxuri_shell.daemon import main; sys.exit(main())' "\$@"
EOF
chmod 755 "$LAUNCHER"

echo "[+] installed launcher: $LAUNCHER"
echo "[+] repo: $SRC_DIR"

if command -v nyxuri >/dev/null 2>&1; then
    nyxuri shell set custom "$LAUNCHER"
    echo "[+] registered with nyxuri: shell set custom $LAUNCHER"
else
    echo "[!] nyxuri not found; register manually: nyxuri shell set custom $LAUNCHER"
fi

echo
echo "next:"
echo "  nyxuri-shell              start the shell"
echo "  nyxuri-shell --no-ui      start headless"
echo "  nyxuri-shell launcher     run one action through the gateway"
echo "  nyxuri-shell --status     print current state"

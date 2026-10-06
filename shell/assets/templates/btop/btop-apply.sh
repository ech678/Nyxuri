#!/usr/bin/env bash
# Nyxuri btop theme hook — vendored from Noctalia 5.2.1 (MIT), brand-adapted.
# Points btop's color_theme at the rendered nyxuri theme and reloads btop.
set -euo pipefail

config_file="${XDG_CONFIG_HOME:-$HOME/.config}/btop/btop.conf"

if [ ! -f "$config_file" ]; then
    echo "Warning: btop config file not found at $config_file" >&2
    exit 0
fi

write_if_changed() {
    local target="$1" tmp="$2"
    if ! cmp -s "$target" "$tmp"; then
        cat "$tmp" >"$target"
    fi
    rm -f "$tmp"
}

if grep -qE '^color_theme\s*=\s*"nyxuri"' "$config_file"; then
    :
elif grep -qE '^color_theme\s*=' "$config_file"; then
    tmp_file="$(mktemp "${config_file}.tmp.XXXXXX")"
    sed -E 's/^color_theme\s*=.*/color_theme = "nyxuri"/' "$config_file" >"$tmp_file"
    write_if_changed "$config_file" "$tmp_file"
else
    [ -s "$config_file" ] && [ -n "$(tail -c1 "$config_file")" ] && echo >>"$config_file"
    echo 'color_theme = "nyxuri"' >>"$config_file"
fi

if pgrep -x btop >/dev/null; then
    pkill -SIGUSR2 -x btop
fi

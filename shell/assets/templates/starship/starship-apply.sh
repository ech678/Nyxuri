#!/usr/bin/env bash
# Nyxuri starship palette hook — vendored from Noctalia 5.2.1 (MIT),
# brand-adapted to nyxuri and extended to strip either managed palette block,
# so starship.toml never accumulates a second block when the dual shells
# alternate ownership of this file.
# shellcheck disable=SC2016,SC2088
set -euo pipefail

palette_file="${XDG_CACHE_HOME:-$HOME/.cache}/nyxuri/starship-palette.toml"
marker_begin="# >>> NYXURI STARSHIP PALETTE >>>"
marker_end="# <<< NYXURI STARSHIP PALETTE <<<"
# Co-managed file invariant: a previous Noctalia render leaves its own block
# behind; stripping it keeps exactly one palette block in the file.
legacy_begin="# >>> NOCTALIA STARSHIP PALETTE >>>"
legacy_end="# <<< NOCTALIA STARSHIP PALETTE <<<"

expand_tilde() {
    case "$1" in
        "~") printf '%s' "$HOME" ;;
        # The pattern must stay quoted: bash tilde-expands an unquoted one inside ${1#...},
        # which turns it into $HOME/ and strips nothing.
        "~/"*) printf '%s' "$HOME/${1#"~/"}" ;;
        *) printf '%s' "$1" ;;
    esac
}

read_env_value() {
    awk -F= -v env_name="$1" '$1 == env_name { sub(/^[^=]*=/, ""); print; exit }'
}

# grep over every /proc/*/environ instead of a stat(1) fork and a tr|awk pipeline
# per process: the same first-match-in-path-order result for a fraction of the cost.
# find and xargs feed the paths in batches sized under ARG_MAX, so the path list never
# has to fit into one execve argument vector the way a shell glob passed as argv does.
# grep -m1 counts per file, so the winner is decided by path order alone; sort restores
# the strcoll order the glob produced, which keeps the choice deterministic even though
# xargs runs grep once per batch.
# No uid filter is needed: /proc/PID/environ is mode 0400 and gated by the ptrace
# access check, so an unreadable entry is simply skipped.
discover_starship_config_from_procfs() {
    # The pipeline suppresses stderr so that an unreadable environ stays quiet, which
    # would also hide a missing tool as an empty result. Check for them up front instead.
    local tool
    for tool in find sort xargs grep; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            echo "Warning: $tool is required to read STARSHIP_CONFIG from /proc" >&2
            return 1
        fi
    done

    local value
    value=$(
        find /proc -mindepth 2 -maxdepth 2 -path '/proc/[0-9]*/environ' -print0 2>/dev/null |
            sort -z |
            xargs -0 -r grep -zhoam1 '^STARSHIP_CONFIG=.*' 2>/dev/null |
            tr '\0' '\n' | head -n 1 || true
    )
    value=${value#STARSHIP_CONFIG=}
    if [ -n "$value" ]; then
        expand_tilde "$value"
        return 0
    fi
    return 1
}

discover_starship_config() {
    if [ -n "${STARSHIP_CONFIG:-}" ]; then
        expand_tilde "$STARSHIP_CONFIG"
        return 0
    fi

    # The shell applies templates from its own process tree, which does not inherit
    # shell-only exports from .bashrc/.zshrc. Recover STARSHIP_CONFIG from the user session.
    if command -v systemctl >/dev/null 2>&1; then
        local from_systemd
        from_systemd=$(
            systemctl --user show-environment 2>/dev/null | read_env_value STARSHIP_CONFIG || true
        )
        if [ -n "$from_systemd" ]; then
            expand_tilde "$from_systemd"
            return 0
        fi
    fi

    local discovered
    if discovered=$(discover_starship_config_from_procfs); then
        printf '%s' "$discovered"
        return 0
    fi

    printf '%s' "${XDG_CONFIG_HOME:-$HOME/.config}/starship.toml"
}

config_file=$(discover_starship_config)

if [ ! -f "$palette_file" ]; then
    echo "Error: Starship palette file not found at $palette_file" >&2
    exit 1
fi

mkdir -p "$(dirname "$config_file")"

tmp_file="$(mktemp "${config_file}.tmp.XXXXXX")"
cleanup() {
    rm -f "$tmp_file"
}
trap cleanup EXIT

# Build the desired starship.toml into a temp file (never sed -i the live path).
# ! -f covers a missing path and a dangling symlink (write-through creates the target).
if [ ! -f "$config_file" ]; then
    {
        echo 'palette = "nyxuri"'
        echo ""
        echo "$marker_begin"
        cat "$palette_file"
        echo "$marker_end"
    } >"$tmp_file"
else
    # Strip the previous managed palette blocks (nyxuri or noctalia) and any
    # palette= line, keep the rest.
    body_file="$(mktemp "${config_file}.body.XXXXXX")"
    cleanup_body() {
        rm -f "$tmp_file" "$body_file"
    }
    trap cleanup_body EXIT

    awk -v nb="$marker_begin" -v ne="$marker_end" -v lb="$legacy_begin" -v le="$legacy_end" '
        $0 == nb || $0 == lb { in_block = 1; next }
        in_block {
            if ($0 == ne || $0 == le) {
                in_block = 0
            }
            next
        }
        /^palette[[:space:]]*=/ { next }
        { print }
    ' "$config_file" >"$body_file"

    # Drop trailing blank lines so the leading newline below does not accumulate.
    sed -i -e :a -e '/^\n*$/{$d;N;ba}' "$body_file"

    {
        if grep -qE '^"\$schema"' "$body_file"; then
            awk '
                /^"\$schema"/ {
                    print
                    if (!inserted) {
                        print "palette = \"nyxuri\""
                        inserted = 1
                    }
                    next
                }
                { print }
            ' "$body_file"
        else
            echo 'palette = "nyxuri"'
            cat "$body_file"
        fi
        echo ""
        echo "$marker_begin"
        cat "$palette_file"
        echo "$marker_end"
    } >"$tmp_file"

    rm -f "$body_file"
    trap cleanup EXIT
fi

# Only touch the live path when content actually changes. Write through a symlink
# instead of replacing it with a regular file via mv/sed -i.
if [ ! -e "$config_file" ] && [ ! -L "$config_file" ]; then
    mv "$tmp_file" "$config_file"
    trap - EXIT
elif ! cmp -s "$config_file" "$tmp_file"; then
    cat "$tmp_file" >"$config_file"
fi

#!/usr/bin/env bash
set -u

kind="${1:?missing theme kind}"
shift

case "$kind" in
    icon)
        excluded='^(icons|default|hicolor|locolor)$'
        require_cursor=false
        ;;
    cursor)
        gsettings get org.gnome.desktop.interface cursor-theme 2>/dev/null \
            | sed "s/'//g" \
            | sed 's/^/SYSDEFAULT:/' || true
        excluded='^(icons|default|hicolor)$'
        require_cursor=true
        ;;
    *)
        exit 2
        ;;
esac

for directory in "$@"; do
    [[ -d "$directory" ]] || continue
    for theme in "$directory"/*/; do
        [[ -d "$theme" ]] || continue
        if [[ "$require_cursor" == true && ! -d "$theme/cursors" ]]; then
            continue
        fi
        basename "$theme"
    done
done | grep -Ev "$excluded" | sort -u

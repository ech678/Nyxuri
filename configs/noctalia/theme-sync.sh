#!/usr/bin/env bash
# ==============================================================================
# NyxNiri System Theme Dispatcher & Bus (theme-sync.sh)
# High-robustness, atomic, zero-entropy theme synchronization engine.
# ==============================================================================

set -uo pipefail

# 1. Portability: Overridable theme configuration variables
GTK_THEME_DARK="${NYXNIRI_GTK_THEME_DARK:-adw-gtk3-dark}"
GTK_THEME_LIGHT="${NYXNIRI_GTK_THEME_LIGHT:-adw-gtk3}"
KVANTUM_THEME_DARK="${NYXNIRI_KVANTUM_DARK:-KvLibadwaitaDark}"
KVANTUM_THEME_LIGHT="${NYXNIRI_KVANTUM_LIGHT:-KvLibadwaita}"
DEFAULT_FALLBACK_MODE="${NYXNIRI_DEFAULT_MODE:-dark}"

# 2. Concurrency Lock: Prevent race conditions from rapid toggles or startup hooks
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/nyxniri-${UID}-theme-sync.lock"
exec 9>"$LOCK_FILE"
flock -w 5 9 || {
    echo "[!] Theme sync locked by another process. Skipping." >&2
    exit 0
}

# 3. Atomic INI Setting Updater (Safe against whitespace, regex chars, and powerloss)
atomic_update_ini() {
    local file="$1"
    local key="$2"
    local val="$3"

    local dir
    dir="$(dirname "$file")"
    mkdir -p "$dir" 2>/dev/null || true

    local tmp_file
    tmp_file=$(mktemp "$dir/.ini.XXXXXX") || return 1

    local key_found=0
    local has_settings_header=0
    # Escape regex special chars in key for the [[ =~ ]] match below.
    local escaped_key
    escaped_key=$(printf '%s' "$key" | sed 's/[][\.^$*+?(){}|/]/\\&/g')

    if [ -f "$file" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ "$line" =~ ^\[Settings\] ]]; then
                has_settings_header=1
                printf '%s\n' "$line" >> "$tmp_file"
                continue
            fi
            if [[ "$line" =~ ^[[:space:]]*${escaped_key}[[:space:]]*= ]]; then
                printf '%s\n' "${key}=${val}" >> "$tmp_file"
                key_found=1
            else
                printf '%s\n' "$line" >> "$tmp_file"
            fi
        done < "$file"
    fi

    if [ "$key_found" -eq 0 ]; then
        if [ "$has_settings_header" -eq 0 ] && [ ! -s "$tmp_file" ]; then
            printf '%s\n' "[Settings]" > "$tmp_file"
        fi
        printf '%s\n' "${key}=${val}" >> "$tmp_file"
    fi

    chmod 644 "$tmp_file" 2>/dev/null || true
    mv -f "$tmp_file" "$file"
}

# 4. Safe GSettings / dconf Setter
set_system_theme() {
    local scheme="$1"
    local gtk_theme="$2"

    if command -v gsettings >/dev/null 2>&1; then
        gsettings set org.gnome.desktop.interface color-scheme "$scheme" 2>/dev/null || true
        gsettings set org.gnome.desktop.interface gtk-theme "$gtk_theme" 2>/dev/null || true
    elif command -v dconf >/dev/null 2>&1; then
        dconf write /org/gnome/desktop/interface/color-scheme "'$scheme'" 2>/dev/null || true
        dconf write /org/gnome/desktop/interface/gtk-theme "'$gtk_theme'" 2>/dev/null || true
    fi
}

# 5. Multi-Tier Theme Mode Resolution Pipeline
ACTION="${1:-}"

# Handle 'status' query
if [ "$ACTION" = "status" ]; then
    curr_scheme="unknown"
    if command -v gsettings >/dev/null 2>&1; then
        curr_scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null | tr -d "'" || echo "unknown")
    fi
    noctalia_mode="unknown"
    if command -v noctalia >/dev/null 2>&1; then
        noctalia_mode=$(noctalia msg theme-mode-get 2>/dev/null || echo "unknown")
    fi
    echo "Current Scheme: $curr_scheme | Noctalia Mode: $noctalia_mode"
    exit 0
fi

# Handle 'toggle'
if [ "$ACTION" = "toggle" ]; then
    if command -v noctalia >/dev/null 2>&1 && noctalia msg status >/dev/null 2>&1; then
        noctalia msg theme-mode-toggle 2>/dev/null || true
        # Read back the new mode so the rest of this script (gsettings broadcast,
        # INI sync, kitty reload) runs for the toggled mode. Previously this
        # branch exit 0'd here, leaving gsettings stale until the Noctalia hook
        # asynchronously caught up — Chrome/Edge/Kitty dark/light lagged.
        sleep 0.3
        TARGET_MODE=$(noctalia msg theme-mode-get 2>/dev/null || echo "")
        if [ "$TARGET_MODE" = "auto" ] || [ -z "$TARGET_MODE" ]; then
            TARGET_MODE="$DEFAULT_FALLBACK_MODE"
        fi
    else
        curr_scheme="prefer-dark"
        if command -v gsettings >/dev/null 2>&1; then
            curr_scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null | tr -d "'" || echo "prefer-dark")
        fi
        if [ "$curr_scheme" = "prefer-dark" ]; then
            TARGET_MODE="light"
        else
            TARGET_MODE="dark"
        fi
    fi
elif [ "$ACTION" = "dark" ] || [ "$ACTION" = "light" ]; then
    TARGET_MODE="$ACTION"
    if command -v noctalia >/dev/null 2>&1 && noctalia msg status >/dev/null 2>&1; then
        noctalia msg theme-mode-set "$ACTION" 2>/dev/null || true
        sleep 0.2
    fi
else
    # Derived from hook environment, Noctalia IPC, or system query
    TARGET_MODE="${NOCTALIA_THEME_MODE:-}"
    if [ -z "$TARGET_MODE" ] && command -v noctalia >/dev/null 2>&1; then
        TARGET_MODE=$(noctalia msg theme-mode-get 2>/dev/null || echo "")
    fi
    if [ "$TARGET_MODE" = "auto" ] || [ -z "$TARGET_MODE" ]; then
        if command -v gsettings >/dev/null 2>&1; then
            curr_scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null | tr -d "'" || echo "")
            if [ "$curr_scheme" = "prefer-light" ] || [ "$curr_scheme" = "default" ]; then
                TARGET_MODE="light"
            elif [ -n "$curr_scheme" ]; then
                TARGET_MODE="dark"
            else
                TARGET_MODE="$DEFAULT_FALLBACK_MODE"
            fi
        else
            TARGET_MODE="$DEFAULT_FALLBACK_MODE"
        fi
    fi
fi

# Normalize Target Parameters
if [ "$TARGET_MODE" = "light" ]; then
    SCHEME_VAL="prefer-light"
    GTK_THEME="$GTK_THEME_LIGHT"
    DARK_PREF="false"
    KVANTUM_THEME="$KVANTUM_THEME_LIGHT"
else
    SCHEME_VAL="prefer-dark"
    GTK_THEME="$GTK_THEME_DARK"
    DARK_PREF="true"
    KVANTUM_THEME="$KVANTUM_THEME_DARK"
fi

# 6. Broadcast to GSettings / XDG Desktop Portal
# Must run before kitty hot-reload: apps wait on this signal to switch dark/light.
# gtk.css (M3 widget colors) is re-rendered by Noctalia itself after its palette
# updates (~6s); we must NOT call config-reload/templates-apply here — doing so
# races the palette update and renders with stale colors, and config-reload
# actually slows the palette update down.
set_system_theme "$SCHEME_VAL" "$GTK_THEME"

# 7. Atomic Sync to GTK 3.0 & GTK 4.0 INI Files
# gtk-application-prefer-dark-theme is deprecated in GTK4 (libadwaita prints a
# warning), but Brave/Chromium reads it at startup to detect dark mode. We keep
# writing it for both GTK3 and GTK4 — the warning is cosmetic and does not
# affect libadwaita, which relies on portal color-scheme + @media CSS instead.
atomic_update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-application-prefer-dark-theme" "$DARK_PREF"
atomic_update_ini "$HOME/.config/gtk-3.0/settings.ini" "gtk-theme-name" "$GTK_THEME"
atomic_update_ini "$HOME/.config/gtk-4.0/settings.ini" "gtk-application-prefer-dark-theme" "$DARK_PREF"
atomic_update_ini "$HOME/.config/gtk-4.0/settings.ini" "gtk-theme-name" "$GTK_THEME"

# Clean up any legacy or stale GTK CSS overrides that break Libadwaita/Nautilus
# Note: gtk.css is now managed by Noctalia user templates (nyxniri_gtk3/gtk4),
# which do not contain the legacy markers below and will not be removed.
for css_dir in "$HOME/.config/gtk-4.0" "$HOME/.config/gtk-3.0"; do
    if [ -f "$css_dir/noctalia.css" ]; then
        rm -f "$css_dir/noctalia.css" 2>/dev/null || true
    fi
    if [ -f "$css_dir/gtk.css" ] && grep -E -q "libadwaita\.css|noctalia\.css|iNiR theming" "$css_dir/gtk.css" 2>/dev/null; then
        rm -f "$css_dir/gtk.css" 2>/dev/null || true
    fi
    # gtk-dark.css symlink imports libadwaita.css (110 @define-color), which
    # loads AFTER gtk.css and overwrites M3 colors. Must remove it.
    if [ -L "$css_dir/gtk-dark.css" ]; then
        rm -f "$css_dir/gtk-dark.css" 2>/dev/null || true
    fi
done

# 8. Hot-Reload Running Applications Live
# Kitty terminal hot reload
if command -v pkill >/dev/null 2>&1; then
    pkill -SIGUSR1 -x kitty 2>/dev/null || true
fi

# Kvantum Qt theme synchronization (silent INI update only if theme directory exists)
if [ -d "/usr/share/Kvantum/$KVANTUM_THEME" ] || [ -d "$HOME/.config/Kvantum/$KVANTUM_THEME" ]; then
    atomic_update_ini "$HOME/.config/Kvantum/kvantum.kvconfig" "theme" "$KVANTUM_THEME"
fi

# Keep the fixed-blue glow's dark/light details in sync. Dynamic glow is
# rendered by Noctalia's template post_hook and intentionally stays out here.
GLOW_DIR="$HOME/.config/niri"
GLOW_ACTIVE="$HOME/.config/NyxNiri/presets/niri.active"
if [ -f "$GLOW_ACTIVE" ] && [ "$(cat "$GLOW_ACTIVE" 2>/dev/null)" = "glow" ]; then
    GLOW_SOURCE="$GLOW_DIR/layout-${TARGET_MODE}.kdl"
    GLOW_DEST="$GLOW_DIR/layout.kdl"
    if [ -f "$GLOW_SOURCE" ] && { [ ! -f "$GLOW_DEST" ] || ! cmp -s "$GLOW_SOURCE" "$GLOW_DEST"; }; then
        tmp=$(mktemp "${GLOW_DEST}.XXXXXX") || exit 0
        cp "$GLOW_SOURCE" "$tmp" && mv -f "$tmp" "$GLOW_DEST"
        if command -v niri >/dev/null 2>&1; then
            niri msg action load-config-file >/dev/null 2>&1 || true
        fi
    fi
fi

# 9. Feedback for Interactive CLI Invocations
if [ -t 1 ] && [ -n "$ACTION" ]; then
    echo "Theme synced to: $TARGET_MODE (Scheme: $SCHEME_VAL, GTK: $GTK_THEME)"
fi

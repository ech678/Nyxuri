#!/bin/bash
set -uo pipefail

# Ensure noctalia is available
if ! command -v noctalia >/dev/null 2>&1; then
    exit 1
fi

WP=$(noctalia msg wallpaper-get 2>/dev/null || true)

# Only process video files to avoid infinite loops
if [[ -n "$WP" && -f "$WP" && "$WP" =~ \.(mp4|webm|mkv|mov|gif)$ ]]; then
    if ! command -v ffmpeg >/dev/null 2>&1; then
        exit 1
    fi

    # Define user-specific thumbnail path in a secure/private location
    THUMB_DIR="${XDG_RUNTIME_DIR:-/tmp/noctalia-$UID}"
    mkdir -p "$THUMB_DIR"
    chmod 700 "$THUMB_DIR" 2>/dev/null || true
    THUMB_PATH="$THUMB_DIR/mpvpaper_thumb.jpg"

    # Generate thumbnail
    if timeout 30 ffmpeg -y -i "$WP" -ss 00:00:01 -vframes 1 "$THUMB_PATH" 2>/dev/null; then
        # Set the thumbnail as wallpaper to extract colors and provide a static background
        noctalia msg wallpaper-set "$THUMB_PATH" 2>/dev/null || true
    fi
fi

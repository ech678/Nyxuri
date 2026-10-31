#!/bin/bash
set -uo pipefail
# Hook to synchronize mpvpaper's video wallpaper with Noctalia's native wallpaper and theme.

# Check dependencies
for cmd in jq ffmpeg inotifywait noctalia; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: Required command '$cmd' is missing." >&2
        exit 1
    fi
done

ASSIGNMENTS_FILE="$HOME/.local/state/noctalia/mpvpaper/assignments.json"

# Signal trap for clean termination
trap 'exit 0' INT TERM

process_assignments() {
    local VIDEO_PATH THUMB_NAME THUMB_PATH CURRENT_WP
    # Extract the first video path using jq
    if [ ! -f "$ASSIGNMENTS_FILE" ]; then
        return
    fi
    
    VIDEO_PATH=$(jq -r '.assignments // . | to_entries | .[0].value // empty' "$ASSIGNMENTS_FILE" 2>/dev/null || true)
    
    if [[ -n "$VIDEO_PATH" && -f "$VIDEO_PATH" ]]; then
        # Check if it's a video
        if [[ "$VIDEO_PATH" =~ \.(mp4|webm|mkv|mov|gif)$ ]]; then
            # Generate a hash-based filename for the thumbnail to avoid re-generating for the same video
            THUMB_NAME=$(printf '%s' "$VIDEO_PATH" | md5sum | awk '{print $1}')
            THUMB_PATH="$HOME/.cache/noctalia/mpvpaper/${THUMB_NAME}.jpg"
            
            mkdir -p "$(dirname "$THUMB_PATH")"
            
            # Generate thumbnail if it doesn't exist
            if [ ! -f "$THUMB_PATH" ]; then
                local tmp_thumb="${THUMB_PATH%.jpg}.tmp.$$.jpg"
                if timeout 30 ffmpeg -y -i "$VIDEO_PATH" -ss 00:00:01 -vframes 1 "$tmp_thumb" 2>/dev/null; then
                    mv "$tmp_thumb" "$THUMB_PATH"
                else
                    rm -f "$tmp_thumb"
                fi
            fi
            
            # Set it as the native Noctalia wallpaper
            if [ ! -f "$THUMB_PATH" ]; then
                return
            fi
            CURRENT_WP=$(noctalia msg wallpaper-get 2>/dev/null || true)
            if [ "$CURRENT_WP" != "$THUMB_PATH" ]; then
                noctalia msg wallpaper-set "$THUMB_PATH" 2>/dev/null || true
            fi
        fi
    fi
}

# Ensure assignments file and directory exist so inotifywait doesn't fail immediately
mkdir -p "$(dirname "$ASSIGNMENTS_FILE")"
touch "$ASSIGNMENTS_FILE"

process_assignments

# Watch directory instead of single file for atomic write safety
while inotifywait -q -e close_write,moved_to "$(dirname "$ASSIGNMENTS_FILE")" 2>/dev/null; do
    process_assignments
done

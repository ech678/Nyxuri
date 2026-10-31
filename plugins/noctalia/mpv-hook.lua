-- mpv Lua script to sync video wallpaper to Noctalia native wallpaper
local msg = require 'mp.msg'

local function on_file_loaded()
    local path = mp.get_property("path")
    if not path or path == "" then 
        msg.warn("No file path found.")
        return 
    end
    
    -- Filter out non-video files
    local lpath = path:lower()
    if not (lpath:match("%.mp4$") or lpath:match("%.webm$") or lpath:match("%.mkv$") or lpath:match("%.mov$") or lpath:match("%.gif$")) then
        return
    end

    -- Get home and cache directories dynamically (no hardcoded path)
    local home = os.getenv("HOME")
    if not home or home == "" then
        msg.error("HOME environment variable is not set. Cannot determine cache directory.")
        return
    end

    local cache_base = os.getenv("XDG_CACHE_HOME")
    if not cache_base or cache_base == "" then
        cache_base = home .. "/.cache"
    end
    
    local cache_dir = cache_base .. "/noctalia/mpvpaper"
    
    -- Shell escape function for security and handling special characters (e.g. spaces, quotes)
    local function shell_escape(s)
        return "'" .. string.gsub(s, "'", "'\\''") .. "'"
    end

    local esc_cache_dir = shell_escape(cache_dir)
    local esc_path = shell_escape(path)
    
    -- Command to safely generate thumbnail using MD5 hash (avoid collisions) and set wallpaper
    local cmd = string.format([=[
        # Check dependencies
        if ! command -v ffmpeg >/dev/null 2>&1; then
            echo "mpv-hook error: ffmpeg not found in PATH" >&2
            exit 1
        fi
        if ! command -v noctalia >/dev/null 2>&1; then
            echo "mpv-hook error: noctalia not found in PATH" >&2
            exit 1
        fi

        # Set variables
        cache_dir=%s
        input_path=%s

        # Create cache directory
        mkdir -p "$cache_dir" || { echo "mpv-hook error: failed to create cache directory" >&2; exit 1; }

        # Compute unique dest filename using md5sum of path to prevent UTF-8 name collisions
        clean_name=$(echo -n "$input_path" | md5sum | awk '{print $1}')
        dest="$cache_dir/${clean_name}.jpg"

        # Generate thumbnail if it does not exist
        if [ ! -f "$dest" ]; then
            ffmpeg -y -i "$input_path" -ss 00:00:01 -vframes 1 "$dest" >/dev/null 2>&1
            if [ $? -ne 0 ]; then
                echo "mpv-hook error: ffmpeg failed to extract frame" >&2
                exit 1
            fi
        fi

        # Apply native wallpaper to trigger color extraction
        if [ -f "$dest" ]; then
            noctalia msg wallpaper-set "$dest" >/dev/null 2>&1
            if [ $? -ne 0 ]; then
                echo "mpv-hook error: noctalia msg wallpaper-set failed" >&2
                exit 1
            fi
        else
            echo "mpv-hook error: thumbnail file not found: $dest" >&2
            exit 1
        fi
    ]=], esc_cache_dir, esc_path)
    
    msg.info("Syncing wallpaper colors for: " .. path)
    
    -- Run asynchronously
    mp.commandv("run", "sh", "-c", cmd)
end

mp.register_event("file-loaded", on_file_loaded)

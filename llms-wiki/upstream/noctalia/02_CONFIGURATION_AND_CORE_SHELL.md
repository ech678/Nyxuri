# Noctalia: Configuration System & Core Shell Settings

This document provides a complete technical specification of Noctalia's configuration layers, load order, file inclusion mechanism, config CLI tools, global `[shell]` / `[storage]` / `[keybinds]` / `[osd]` / `[lockscreen]` tables, and date/time formatting tokens.

---

## 1. Configuration Mechanics & Storage Layers

Noctalia uses a two-layer configuration system with three distinct storage owners:

### 1.1 Storage Locations & Owners

| Layer / Purpose | Path | Description & Permissions |
|-----------------|------|---------------------------|
| **User Base Config** | `~/.config/noctalia/*.toml`<br>(or `$NOCTALIA_CONFIG_HOME`, `$XDG_CONFIG_HOME/noctalia/`) | Hand-written, declarative dotfiles. Noctalia reads and merges all root `*.toml` files alphabetically. |
| **GUI Overrides** | `~/.local/state/noctalia/settings.toml`<br>(or `$NOCTALIA_STATE_HOME`, `$XDG_STATE_HOME/noctalia/`) | Written by Settings UI & runtime actions. Loads last and overrides hand-written values. |
| **Internal UI State** | `~/.local/state/noctalia/state.toml` | App-managed state (last values, window positions, active choices). |
| **Storage Master Key** | Desktop Secret Service or `key_file` | Master key for encrypted clipboard history & calendar cache. |
| **Calendar Event Cache** | `$XDG_CACHE_HOME/noctalia/calendar/events.enc` | Encrypted local calendar cache. |
| **Custom Palettes** | `~/.config/noctalia/palettes/` | User custom JSON palette files. |
| **Local Plugins** | `~/.local/share/noctalia/plugins/` | Manually installed or local developer plugins. |
| **Plugin Cache/Materialized** | `~/.local/state/noctalia/plugins/` | Git source cache and materialized runtime plugins. |

### 1.2 Load Order & Precedence Rule

Configuration resolves in the following strict order (later entries win):
1. **Built-in Defaults**
2. **User Hand-written Files (`~/.config/noctalia/`)**:
   - Files included via `[include]` are loaded first as a base.
   - The file doing the including merges on top of its included files.
3. **GUI-managed Overrides (`~/.local/state/noctalia/settings.toml`)**:
   - Always wins over hand-written files.
   - When a GUI setting is changed back to match the underlying file value, the redundant key is removed.

Both layers are watched for file changes and **hot-reloaded** live.

### 1.3 `[include]` Table & Profile Switching

```toml
# ~/.config/noctalia/config.toml
[include]
# autoload: when true (default), all other *.toml in config root still load.
# Set autoload = false to load ONLY this file and its explicit includes (profile switching).
autoload = false

files = [
  "widgets/",                  # Loads all *.toml inside widgets/ (sorted, non-recursive)
  "bars/top.toml",             # Single relative file
  "~/.config/shared/base.toml", # Supports ~, $VAR, ${VAR} expansion
]

[theme]
mode = "dark"
```
- **Precedence**: The including file overrides the included files.
- **Cycles**: Includes are checked for recursion and loaded at most once.
- **Scope**: `[include]` is ignored inside `settings.toml`.

### 1.4 CLI Tools: Validation & Export

- **Validate configuration** (reports errors and deprecation warnings with file, line, and column):
  ```bash
  noctalia config validate             # checks merged config + settings.toml
  noctalia config validate ./custom/   # checks custom directory
  noctalia config validate ./file.toml # checks single file (e.g. in CI or NixOS build)
  ```
  - **Errors** (exit status `1`): syntax errors, missing include files, invalid enum/types.
  - **Warnings** (exit status `0`): unknown keys, clamped values, migrated deprecated keys.

- **Export configuration**:
  ```bash
  noctalia config export > user-config.toml      # Merged user config (excludes defaults)
  noctalia config export full > full-config.toml # Full effective config (includes all defaults)
  ```

---

## 2. Core Configuration Reference

### 2.1 `[storage]` - Master Key Management
```toml
[storage]
key_source = "secret-service" # "secret-service" | "file"
key_file   = ""               # Absolute path to 64-character hex key file (required when key_source = "file")
```
- When using `key_source = "file"`, create the key via:
  ```bash
  umask 077 && head -c 32 /dev/urandom | xxd -p -c 64 > ~/.config/noctalia/storage.key
  ```

---

### 2.2 `[shell]` - Global UI & Desktop Settings
```toml
[shell]
# --- Sizing, Font & Locale ---
corner_radius_scale   = 1.0             # 0 = square, 1 = default, 2 = extra rounded
font_family           = "sans-serif"    # Pango font family (Fontconfig handles fallback)
lang                  = ""              # Empty = auto-detect ($LANG); BCP-47 (zh-Hans, pt-BR) or POSIX
time_format           = "{:%H:%M}"      # Fallback time format for shell UI
date_format           = "%A, %x"        # Fallback date format for shell UI

# --- Borders & Shadows ---
button_borders        = true            # Draw outlines on buttons
input_borders         = true            # Draw outlines on inputs (focus ring still appears if false)
popup_borders         = true            # Draw outlines on context menus, dropdowns, tray menus
card_borders          = true            # Draw outlines on section cards in panels/settings
popup_shadows         = true            # Cast drop shadows behind popups and dropdowns

# --- General Flags & Integration ---
offline_mode          = false           # Disables all outgoing HTTP requests (weather, catalogs, etc.)
# panel_anchor_bar    = "main"          # Default bar to attach panels to when opened without bar context
external_ip_enabled   = false           # Resolve public WAN IP for network tab & tooltip
telemetry_enabled     = false           # Anonymous startup telemetry ping (disabled by default)
setup_wizard_enabled  = true            # Show first-run wizard if .setup-complete is missing
polkit_agent          = false           # Register native Polkit authentication agent
password_style        = "default"       # "default" (circle-filled) | "random" (cycles glyphs)
avatar_path           = "~/Pictures/avatar.png" # User avatar (also updates AccountsService IconFile)
settings_show_advanced = true           # Show advanced settings by default in Settings UI
settings_window_translucent = false     # Translucent background on Settings window
show_location         = true            # Show weather location / coordinates text

# --- App Launching & Execution ---
launch_apps_as_systemd_services = false # Run apps as transient systemd scopes (requires shell under systemd user unit)
launch_apps_custom_command = ""         # Wrapper for launched apps ($CMD is replaced, e.g. "uwsm-app -- $CMD")
screen_time_enabled   = false           # Track per-app usage time for Control Center

# --- App Icon Colorization ---
app_icon_colorize     = false           # Tint application bitmap icons to match palette
app_icon_color        = "on_surface"    # Color role or hex color (#RRGGBB)

# --- Clipboard History ---
clipboard_enabled     = true            # Master switch for clipboard history & panel
clipboard_keep_from_closed_apps = true  # Keep live selection after source app closes
clipboard_history_max_entries = 100     # Maximum unpinned history entries (10-10000)
clipboard_confirm_clear_history = true  # Confirm before clearing unpinned history
clipboard_auto_paste  = "auto"          # "off" | "auto" (Ctrl+V for images, Ctrl+Shift+V for text) | "ctrl_v" | "ctrl_shift_v" | "shift_insert"
clipboard_image_action_command = ""     # External action for images (e.g. "satty -f -", "gimp {path}")

# --- Graphics & Context ---
shared_gl_context     = true            # Share GPU textures across surfaces (startup-only)
disable_mipmaps       = false           # Disable texture mipmaps if scaling artifacts appear

# --- Compositor-Specific ---
niri_overview_type_to_launch_enabled = false # Niri: open launcher on typing in overview

[shell.keyboard_layout.custom_labels]
"German (Neo 2)" = "Neo2"
"English (US)"   = "EN"
```

---

### 2.3 `[shell.animation]` & `[shell.shadow]`
```toml
[shell.animation]
enabled = true
speed   = 1.0   # 1.0 = normal, 0.5 = 2x slower, 2.0 = 2x faster

[shell.shadow]
direction = "down"  # "center" | "up" | "down" | "left" | "right" | "up_left" | "up_right" | "down_left" | "down_right"
alpha     = 0.55    # Shadow opacity multiplier (blur is fixed at 12px)
```

---

### 2.4 `[shell.panel]` - Panel Placement & Styling
```toml
[shell.panel]
transparency_mode     = "solid"     # "solid" | "soft" | "glass" (controls floating panel & card translucency)
borders               = true        # Draw outline on floating panel surfaces
shadow                = true        # Cast [shell.shadow] from panel surfaces
list_item_background  = false       # Draw filled rounded background behind launcher / clipboard items
floating_layer         = "overlay"   # "overlay" (above fullscreen) | "top"

# Placement: "attached" (anchored to bar edge) | "floating"
launcher_placement       = "floating"
clipboard_placement      = "floating"
control_center_placement = "attached"
wallpaper_placement      = "attached"
session_placement        = "attached"
polkit_placement         = "floating"

# Position when placement = "floating": "auto" | "center" | "top_left" | "top_right" | "bottom_left" | "bottom_right" | ...
launcher_position        = "center"
clipboard_position       = "center"
polkit_position          = "center"
control_center_position  = "auto"
wallpaper_position       = "auto"
session_position         = "auto"

floating_offset          = 8        # Gap in logical pixels from bar or screen edge

# Open near clicked widget instead of centering along the bar:
open_near_click_control_center = false
open_near_click_launcher       = false
open_near_click_clipboard      = false
open_near_click_wallpaper      = false
open_near_click_session        = false
```

---

### 2.5 `[shell.launcher]` - Application Launcher & Search
```toml
[shell.launcher]
categories                = true   # Show category filter bar (Tab toggles)
show_icons                = true   # Show application icons
show_app_origin_indicator = true   # Show Flatpak/Snap/Nix/AppImage badges
compact                   = false  # Smaller icons, tighter padding, hide subtitles
app_grid                  = false  # Multi-column grid when results are apps only
show_app_actions          = false  # Searchable .desktop actions (e.g. "New Private Window")
sort_by_usage             = true   # Boost frequently used apps & show "Recently Used"
pinned                    = []     # Desktop entry IDs shown first when opened empty
fetch_exchange_rates      = true   # Background currency rates for math evaluations
provider_prefix           = "/"    # Common prefix character (e.g. "/")
auto_paste                = "auto" # Auto paste after copy activation

# Built-in Providers:
[shell.launcher.providers.calculator]
prefix = "calc"   # Triggers on "/calc"
global = true     # Also evaluate math in un-prefixed search

[shell.launcher.providers.emoji]
prefix = "emo"    # Triggers on "/emo"

[shell.launcher.providers.session]
prefix = "session"
global = false

[shell.launcher.providers.wallpaper]
prefix = "wall"

[shell.launcher.providers.windows]
prefix = "win"

# Custom Dmenu Provider Example:
[shell.launcher.dmenu.entry.ssh]
command = "awk '/^Host /{print $2}' ~/.ssh/config" # Emits candidates (one per line, optional title\tdesc)
exec    = "foot ssh {selection}"                  # Runs on selection ({selection} substituted)
prefix  = "ssh"                                   # Triggers on "/ssh"
glyph   = "server"                                # Tabler icon name
global  = false

# Plugin Launcher Provider Override:
[shell.launcher.providers."author/plugin:entry"]
prefix = "custom"
global = true
```

---

### 2.6 `[shell.screen_corners]` & `[hot_corners]`
```toml
[shell.screen_corners]
enabled = false   # Overlay black rounded corners on screens
size    = 32      # Radius in logical pixels (1-100)

[hot_corners]
enabled  = false
delay_ms = 0      # Hover delay before triggering (0 = immediate)

# Actions: "none" | "launcher" | "window-switcher" | "control-center" | "command"
[hot_corners.top_left]
action = "none"

[hot_corners.bottom_right]
action  = "command"
command = "noctalia msg session lock"
```

---

### 2.7 `[shell.screenshot]` & `[shell.privacy]`
```toml
[shell.screenshot]
save_to_file         = true                        # Save PNG file
directory            = ""                          # Output folder (empty = ~/Pictures)
filename_pattern     = ""                          # strftime format (empty = screenshot_%Y%m%d_%H%M%S)
copy_to_clipboard    = true                        # Copy PNG to clipboard
freeze_screen        = true                        # Freeze desktop before region select
confirm_region       = false                       # Confirm region with Enter/Space
remember_last_region = false                       # Pre-select last captured region
show_cursor          = false                       # Include mouse pointer
pipe_to_command      = false                       # Pipe PNG bytes to stdin of command
pipe_command         = "satty -f -"                # Command receives image via stdin ($NOCTALIA_SCREENSHOT_PATH is exported)

[shell.privacy]
mic_filter_regex    = "" # Regex: ignore matching apps for microphone indicator
cam_filter_regex    = "" # Regex: ignore matching processes for camera indicator
screen_filter_regex = "" # Regex: ignore matching apps for screen share indicator

[shell.mpris]
blacklist = ["playerctld"] # Case-insensitive player bus names / tokens to hide
```

---

### 2.8 `[accessibility]` & `[osd]`
```toml
[accessibility]
ui_scale      = 1.0    # Content scale for panels and non-bar surfaces
high_contrast = false  # High-contrast mode (forces pure black dark theme)

[osd]
position          = "top_center" # "top_right" | "top_left" | "top_center" | "bottom_right" | "bottom_left" | "bottom_center" | "center_right" | "center_left"
position_vertical = "top_center"
orientation       = "horizontal" # "horizontal" | "vertical" (for volume/brightness sliders)
scale             = 1.0          # OSD size multiplier
background_opacity = 0.97
border            = true
offset_x          = 20
offset_y          = 8
monitors          = []           # Connector names (empty = all outputs)

[osd.kinds]
volume             = true # Master volume OSD
volume_output      = true # Speaker volume
volume_input       = true # Mic volume
brightness         = true # Display brightness
wifi               = true # WiFi toggle
bluetooth          = true # Bluetooth toggle
power_profile      = true # Power profile
caffeine           = true # Idle inhibitor
nightlight         = true # Night light
dnd                = true # Do Not Disturb
lock_keys          = true # Caps/Num/Scroll lock
keyboard_layout    = true # Layout change
media              = true # MPRIS track changes
privacy            = true # Mic/camera/share start/stop
keyboard_backlight = true # Keyboard backlight
```

---

### 2.9 `[lockscreen]` - Session Lock
```toml
[lockscreen]
enabled              = true   # Master switch for session lock (ext-session-lock-v1)
lock_before_suspend  = true   # Lock on logind PrepareForSleep before suspend/hibernate
fingerprint          = true   # Allow PAM fingerprint auth
allow_empty_password = false  # Allow empty password submit (for security keys)
blurred_desktop      = false  # Capture desktop before lock and use as background (requires screencopy)
blur_intensity       = 0.5    # 0.0 (none) to 1.0 (max)
tint_intensity       = 0.3    # Surface color tint over background (0.0 to 1.0)
wallpaper            = ""     # Custom image path (empty = output desktop wallpaper)
monitors             = []     # Outputs to show lockscreen on (empty = all)
```

---

### 2.10 `[keybinds]` - Surface & UI Navigation Key Chords
Chords format: `key`, `modifier+key`, `modifier+modifier+key`. Modifiers allowed: `ctrl`, `shift`, `alt`. (`super` is rejected as it belongs to the compositor).

```toml
[keybinds]
validate     = ["return", "kp_enter"]
cancel       = ["escape"]
left         = ["left"]
right        = ["right"]
up           = ["up"]
down         = ["down"]
tab_next     = ["tab"]
tab_previous = ["shift+tab", "iso_left_tab"]
copy         = ["ctrl+c"]
save         = ["ctrl+s"]
delete       = ["del"]
```

---

### 2.11 `[shell.session]` - Power & Session Panel
```toml
[shell.session]
grid           = false # Multi-row grid layout
grid_columns   = 3     # Columns per row when grid = true (1-5)
show_shortcuts = true  # Show numeric shortcuts (1-5) on badges

[shell.session.power]
# Global overrides for built-in power commands:
suspend  = "sudo -n zzz"
reboot   = "sudo -n reboot"
shutdown = "sudo -n poweroff"

# Custom Session Actions List (omitting keeps default 5 actions):
[[shell.session.actions]]
action            = "lock"
command           = "" # Optional command override
shortcut          = "1"
variant           = "default"

[[shell.session.actions]]
action            = "logout"
shortcut          = "2"

[[shell.session.actions]]
action            = "suspend"
shortcut          = "3"

[[shell.session.actions]]
action            = "reboot"
shortcut          = "4"
variant           = "secondary"

[[shell.session.actions]]
action            = "shutdown"
shortcut          = "5"
variant           = "destructive"
countdown_seconds = 5 # Delayed activation with cancel timer

[[shell.session.actions]]
action            = "command"
label             = "Hyprlock"
glyph             = "lock"
command           = "hyprlock"
variant           = "outline"
```

---

### 2.12 `[shell.greeter_sync]` - Noctalia Greeter Sync
```toml
[shell.greeter_sync]
auto_sync         = true                 # Auto sync appearance when wallpaper/theme/font change
privilege_command = "ghostty -e pkexec" # Custom privilege escalation command (e.g. for seatd without logind)
```

---

## 3. Date & Time Format Tokens Reference

Tokens can be specified as bare `strftime` patterns (`%H:%M`) or C++ chrono fields (`{:%H:%M}`).

### 3.1 Time Tokens
| Token | Meaning |
|-------|---------|
| `%H` | Hour (24-hour, `00`–`23`) |
| `%k` | Hour (24-hour, space-padded ` 0`–`23`) |
| `%I` | Hour (12-hour, `01`–`12`) |
| `%l` | Hour (12-hour, space-padded ` 1`–`12`) |
| `%M` | Minute (`00`–`59`) |
| `%S` | Second (`00`–`60`) |
| `%p` / `%P` | AM/PM / lowercase am/pm |
| `%R` | Equivalent to `%H:%M` |
| `%T` | Equivalent to `%H:%M:%S` |
| `%r` | Locale 12-hour time (`%I:%M:%S %p`) |
| `%X` | Locale time representation |
| `%z` / `%Z` | Timezone numeric offset (`-0400`) / Timezone name |
| `%s` | Unix epoch seconds |

### 3.2 Date & Week Tokens
| Token | Meaning |
|-------|---------|
| `%Y` / `%y` | 4-digit year (`2026`) / 2-digit year (`26`) |
| `%m` / `%d` | Month (`01`–`12`) / Day of month (`01`–`31`) |
| `%B` / `%b` | Full localized month / Abbreviated month |
| `%A` / `%a` | Full localized weekday / Abbreviated weekday |
| `%u` / `%w` | ISO weekday (`1`=Mon..`7`=Sun) / Weekday (`0`=Sun..`6`=Sat) |
| `%F` | ISO date (`%Y-%m-%d`) |
| `%x` / `%c` | Locale date representation / Locale date & time representation |
| `%j` | Day of year (`001`–`366`) |
| `%V` / `%W` / `%U` | ISO week number / Mon-start week / Sun-start week |

### 3.3 Modifiers (placed between `%` and token, e.g. `%-d`, `%_d`)
- `-` : Do not pad numeric output (`%-I:%M %p` -> `9:05 AM`)
- `_` : Space-pad numeric output
- `0` : Zero-pad numeric output
- `^` : Convert alphabetic output to uppercase (`%^B` -> `MAY`)
- `\n` : Literal newline
- `%%` : Literal `%`

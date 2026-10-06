# Noctalia: Surfaces & Background Services

This document provides a comprehensive technical reference for Noctalia's desktop surfaces (Dock, Launcher, Control Center, Wallpaper & Backdrop, Desktop Widgets, Lockscreen Widgets) and background services (Audio, Battery, Brightness, Calendar, Idle, Location, Night Light, Notifications, System Monitor, Weather, and Automation Hooks).

---

## 1. Desktop Surfaces

### 1.1 `[dock]` - Standalone Application Dock
A macOS-style application dock supporting pins, running applications, magnification, and auto-hide.

```toml
[dock]
enabled             = false      # Set true to activate dock
position            = "bottom"   # "top" | "bottom" | "left" | "right"
active_monitor_only = false      # Show only apps/windows from the active monitor
monitors            = []         # Connector names to display on (empty = all outputs)

icon_size           = 48         # Base icon size in pixels
main_axis_padding   = 16         # Padding along icon row
cross_axis_padding  = 8          # Padding perpendicular to icon row
item_spacing        = 6          # Spacing between dock icons
background_opacity  = 0.88
border              = "outline"  # Border color role or hex
border_width        = 0.0        # Outline width in px (0 disables)
shadow              = true       # Cast global [shell.shadow]
radius              = 16         # Corner radius
concave_edge_corners = true      # Flared screen-edge corners (requires margin_edge = 0)
margin_ends         = 0          # Main-axis margin from screen ends
margin_edge         = 0          # Float distance from screen edge

show_running        = true       # Show running unpinned apps
auto_hide           = false      # Slide out on mouse leave
smart_auto_hide     = false      # Auto-hide when windows are on active workspace
reserve_space       = true       # Reserve compositor exclusive zone
layer               = "top"      # "top" | "overlay"

active_scale        = 1.0        # Focused app scale multiplier (0.1–1.75)
inactive_scale      = 0.85       # Unfocused app scale multiplier (0.1–1.0)
magnification       = true       # macOS-style icon magnification on hover
magnification_scale = 1.45       # Max scale multiplier at pointer center (1.0–2.0)
active_opacity      = 1.0
inactive_opacity    = 0.85
show_instance_count = true       # Window count badge when app has 2+ windows
show_dots           = false      # Running-indicator dots below app icons

launcher_position   = "none"     # "none" | "start" | "end" (launcher button on dock)
launcher_icon       = "grid-dots"# Tabler glyph
launcher_custom_image = ""
launcher_custom_image_colorize = false

pinned = ["firefox", "code", "kitty"] # Desktop IDs / StartupWMClass / App Name
```

- **Pinned matching order**: Desktop entry ID stem -> `StartupWMClass` -> App `Name` -> Full `.desktop` path.
- **Reordering**: Drag-and-drop pinned icons (hold for 300ms) persists new order to `settings.toml`.

---

### 1.2 `[control_center]` - Control Center Panel & Shortcuts

#### Sidebar & Layout
```toml
[control_center]
sidebar              = "compact" # "full" (icons+text) | "compact" (icons only) | "none"
sidebar_section      = "compact" # Sidebar mode when opened directly to a subtab
width                = 700       # Full-sidebar width in pixels (600–1200)
show_shortcut_labels = true      # Text labels under Home shortcut tiles
show_session_button  = true      # Session actions button in Home header
hidden_tabs          = []        # List of context IDs to hide (e.g. ["monitor", "weather"])

[control_center.calendar]
show_events_card  = true         # Show day's event list beside month grid
show_week_numbers = false        # ISO 8601 week numbers in month grid
event_date_format = "%A %e %B"   # Date heading strftime format
event_time_format = "%H:%M"      # Event start time format
```

#### Sidebar Tab Context IDs (for IPC: `noctalia msg panel-toggle control-center <context>`):
- `home`, `media`, `audio`, `monitor` (brightness), `system`, `network`, `bluetooth`, `weather`, `calendar`, `notifications`, `screen-time`, `power`.

#### Home Shortcuts (`[[control_center.shortcuts]]`)
```toml
# Up to 6 shortcuts shown on the Home tab.
# Default if omitted: ["wifi", "bluetooth", "caffeine", "nightlight", "notification", "power_profile"]

[[control_center.shortcuts]]
type = "wifi"            # Left: toggle WiFi | Right: open network tab

[[control_center.shortcuts]]
type = "bluetooth"       # Left: toggle BT | Right: open bluetooth tab

[[control_center.shortcuts]]
type = "nightlight"      # Left: toggle | Right: toggle force

[[control_center.shortcuts]]
type = "notification"    # Left: toggle DND | Right: open notifications tab

[[control_center.shortcuts]]
type = "caffeine"        # Left: toggle idle inhibitor

[[control_center.shortcuts]]
type = "power_profile"   # Left: cycle profile | Right: open system tab
```
Available shortcut types: `wifi`, `bluetooth`, `nightlight`, `notification`, `dark_mode`, `caffeine`, `audio`, `mic_mute`, `power_profile`, `media`, `weather`, `system`, `screen_time`, `keyboard_layout`, `screen_recorder`, `wallpaper`, `session`, `clipboard`.

---

### 1.3 `[wallpaper]` & `[backdrop]` - Wallpaper & Overview Backdrop

```toml
[wallpaper]
enabled                  = true
fill_mode                = "crop"    # "center" | "crop" | "fit" | "stretch" | "repeat" | "span"
fill_color               = "#111111" # Fallback/border color role or hex
transition               = ["fade", "wipe", "disc", "stripes", "zoom", "honeycomb"]
transition_duration      = 1500      # Milliseconds
edge_smoothness          = 0.3       # 0.0 - 1.0
transition_on_startup    = false     # Fade in on initial shell launch
directory                = "~/Pictures/Wallpapers"
directory_light          = "~/Pictures/Wallpapers/Light"
directory_dark           = "~/Pictures/Wallpapers/Dark"
per_monitor_directories  = false

[wallpaper.default]
path = "~/Pictures/Wallpapers/default.png"

[wallpaper.automation]
enabled          = false
interval_seconds = 1800
order            = "random" # "random" | "alphabetical"
recursive        = true

# Per-Monitor Override:
[wallpaper.monitor.DP-2]
enabled   = true
directory = "~/Pictures/Wallpapers/Vertical"

# Declarative Wallpaper Favorites:
[[wallpaper.favorite]]
path             = "~/Pictures/Wallpapers/mountain.jpg"
theme_mode       = "dark"
palette_source   = "wallpaper"
wallpaper_scheme = "m3-content"

# Overview Backdrop (for Niri overview layer):
[backdrop]
enabled        = false
blur_intensity = 0.5    # 0.0 (none) to 1.0 (max)
tint_intensity = 0.3    # Surface color tint over backdrop (0.0 to 1.0)
```

---

### 1.4 `[desktop_widgets]` & `[lockscreen_widgets]`

On-desktop and lockscreen widgets render as individual Layer Shell surfaces on the `Bottom` layer.

#### Common Geometry Schema
```toml
[desktop_widgets]
enabled = true

[desktop_widgets.widget.<id>]
type       = "clock"      # Widget kind
output     = "DP-1"       # Monitor connector
cx         = 960.0        # Center X position in logical px
cy         = 540.0        # Center Y position in logical px
box_width  = 0.0          # 0.0 = auto-fit content
box_height = 0.0          # 0.0 = auto-fit content
rotation   = 0.0          # Radians
flip_x     = false
flip_y     = false
enabled    = true

[desktop_widgets.widget.<id>.settings]
# Common Background Settings:
background         = true
background_color   = "surface"
background_opacity = 0.8
background_radius  = 12.0
background_padding = 10.0
# Text Settings:
color              = "on_surface"
font_family        = ""
shadow             = true
```

#### Available Desktop/Lockscreen Widget Kinds:
1. **`clock`**: `clock_style = "digital"|"analog"`, `format = "{:%H:%M}"`, `center_text = false`, `circle = true` (analog dial), `timezone = ""`
2. **`calendar`**: `show_events = true`, `show_week_numbers = false`, `font_family = ""`
3. **`audio_visualizer`**: `bands = 32`, `mirrored = true`, `centered = true`, `show_when_idle = true`, `color_1 = "primary"`, `color_2 = "secondary"`
4. **`fancy_audio_visualizer`**: `visualization_mode = "bars_rings"|"bars"|"wave"|"rings"|"wave_rings"|"all"`, `sensitivity = 1.5`, `rotation_speed = 0.5`, `bar_width = 0.6`, `wave_thickness = 1.0`, `ring_opacity = 0.8`, `inner_diameter = 0.7`, `bloom_intensity = 0.5`, `fade_when_idle = true`, `primary_color = "primary"`, `secondary_color = "secondary"`
5. **`weather`**: `show_forecast = false`, `forecast_days = 3`
6. **`media_player`**: `layout = "horizontal"|"vertical"`, `hide_when_no_media = true`
7. **`button`**: `glyph = "terminal"`, `label = "Terminal"`, `command = "foot"`, `variant = "default"|"primary"|"secondary"|"outline"|"ghost"|"destructive"`, `hover_background = "hover"`
8. **`sticker`**: `image_path = "/path/to/image.png"`, `opacity = 1.0` (Supports PNG, JPG, WebP, SVG, animated GIF)
9. **`label`**: `title = "Heading"`, `description = "Body text"`, `opacity = 1.0`
10. **`volume`**: `device = "output"|"input"`, `fill_color = "primary"`, `track_color = "on_surface_variant"`, `show_device = true`, `scroll_step = 5`
11. **`sysmon`**: `display = "graph"|"gauge"`, `stat = "cpu_usage"`, `stat2 = "cpu_temp"`, `gauge_layout = "horizontal"|"vertical"`, `interface = ""`
12. **`login_box`** (*Lockscreen only*, fixed ID `lockscreen-login-box@<output>`): `layout = "regular"|"compact"`, `show_session_buttons = true`, `show_media = true`, `show_weather = true`, `show_unlock_hint = true`, `show_caps_lock = true`, `show_keyboard_layout = true`, `show_login_button = true`, `background_color = "surface_variant"`, `background_opacity = 0.88`, `background_radius = 12.0`, `input_opacity = 1.0`, `input_radius = 6.0`, `center_password_text = false`

---

## 2. Background Services

### 2.1 `[audio]` - PipeWire & UI Sounds
```toml
[audio]
enable_overdrive    = false # Allow volume up to 150% (instead of 100%)
enable_sounds       = false # Master switch for shell UI sound effects
sound_volume        = 0.5   # Global UI sound volume (0.0–1.0)
volume_change_sound = ""    # Custom path (empty = default sounds/volume-change.wav)
notification_sound  = ""    # Custom path (empty = default sounds/notification.wav)
```

### 2.2 `[battery]` - UPower Thresholds & Escalation
```toml
[battery]
warning_threshold = 10 # Percentage for low-battery warning (0 disables)

# Per-device warning thresholds (for peripherals/headsets):
[battery.device."/org/freedesktop/UPower/devices/headset_dev_00_11_22_33_44_55"]
warning_threshold = 15
```
- **System Battery Escalating Warnings**:
  - At `warning_threshold` (10%): Normal notification.
  - At 5%: Critical notification.
  - At 2%: Persistent critical notification (stays until plugged or dismissed).
  - Warnings bypass DND (sound stays muted).

### 2.3 `[brightness]` - Backlight & DDC/CI
```toml
[brightness]
enable_ddcutil     = false # Enable DDC/CI monitor discovery
ignore_mmids       = []    # Monitor model IDs to skip in ddcutil (e.g. ["ACI-ROG_PG279Q-10220"])
minimum_brightness = 0.0   # Floor clamp (0.0 to 1.0) to prevent total black screen
sync_all_monitors  = false # Sync all monitors when one changes

[brightness.monitor.eDP-1]
backend          = "backlight"      # "auto" | "none" | "backlight" | "ddcutil"
backlight_device = "intel_backlight"# Sysfs device name or path
```

### 2.4 `[calendar]` - CalDAV & Google Sync
```toml
[calendar]
enabled         = true
refresh_minutes = 15

# iCloud CalDAV:
[calendar.account.personal_icloud]
type      = "caldav"
name      = "Personal iCloud"
provider  = "icloud"
username  = "me@example.com" # Apple ID (password stored in Secret Service via Settings UI)
calendars = []              # Empty = all discovered calendars

# Custom CalDAV with File-backed Password:
[calendar.account.home_nextcloud]
type              = "caldav"
name              = "Nextcloud"
provider          = "custom"
server_url        = "https://cloud.example.com/remote.php/dav/"
username          = "myuser"
credential_source = "file"
password_file     = "/run/agenix/noctalia-caldav" # Absolute path

# Google Calendar (OAuth via Settings -> Connect):
[calendar.account.work_google]
type = "google"
name = "Work"

# Public ICS URL:
[calendar.account.holidays]
type       = "ics"
name       = "Holidays"
server_url = "https://example.com/calendar.ics" # webcal:// and https:// supported
color      = "primary"
```

### 2.5 `[idle]` - Compositor Idle Management
Backed by Wayland `ext_idle_notifier_v1`.
```toml
[idle]
behavior_order          = ["lock", "screen-off", "suspend"]
pre_action_fade_seconds = 2.0 # Fullscreen dim before executing idle action (0 disables)

[idle.behavior.lock]
timeout = 600
action  = "lock" # Native action
enabled = true

[idle.behavior.screen-off]
timeout = 660
action  = "screen_off" # Powers down display via DPMS, wakes on return
enabled = true

[idle.behavior.suspend]
timeout             = 900
action              = "suspend" # or "lock_and_suspend"
lock_before_suspend = true

[idle.behavior.custom]
timeout        = 48
action         = "command"
command        = "notify-send 'Idle' 'Session idle'"
resume_command = "notify-send 'Idle' 'Welcome back'"
```

### 2.6 `[location]` - Geolocation & Solar Calculations
Single source of position for Weather, Night Light, and Theme `auto`.
```toml
[location]
auto_locate = false         # Resolve approximate coordinates from IP via api.noctalia.dev
address     = "Berlin, DE"  # Geocoded when auto_locate = false
# latitude  = 52.5200       # Manual coordinates
# longitude = 13.4050

# Custom Schedule (overrides solar sunrise/sunset for Night Light & Theme):
custom_schedule = false
sunset          = "20:30"   # HH:MM
sunrise         = "07:30"   # HH:MM
```

### 2.7 `[nightlight]` - Color Temperature Adjustment
Backed by `wlr-gamma-control`.
```toml
[nightlight]
enabled           = false
force             = false # Always-on override (ignores sunrise/sunset schedule)
temperature_day   = 6500  # Kelvin (must be > temperature_night by >= 100)
temperature_night = 4000  # Kelvin
```
- A 1-hour smooth fade is centered around astronomical sunrise and sunset (30 min before to 30 min after).

### 2.8 `[notification]` - Desktop Notifications Daemon
Claims `org.freedesktop.Notifications`.
```toml
[notification]
enable_daemon           = true        # Master daemon switch
show_app_name           = true
show_actions            = true
position                = "top_right" # "top_right" | "top_left" | "top_center" | "bottom_right" | "bottom_left" | "bottom_center"
layer                   = "top"       # "top" | "overlay"
scale                   = 1.0
background_opacity      = 0.97
border                  = true
offset_x                = 20
offset_y                = 8
monitors                = []          # Empty = all outputs
collapse_on_dismiss     = true        # Slide remaining toasts together
max_visible             = 0           # Max simultaneous toasts (0 = unconstrained)
history_retention_hours = 0           # Auto-delete history older than N hours (0 = forever)

# Per-Sender / Content Filters (First match in filter_order wins):
filter_order = ["rhythmbox", "quiet_logs"]

[notification.filter.rhythmbox]
enabled           = true
match             = "rhythmbox"               # App name / desktop-entry / category token
match_content     = "now playing"             # Regex matching summary or body
show_toast        = true
save_history      = false                     # Suppress writing to Control Center history
play_sound        = false
bypass_dnd        = false                     # Show even during DND
allow_permanent   = true                      # Allow persistent (0-timeout) toasts
override_duration = 5000                     # Force display duration in ms
allowed_urgencies = ["normal", "critical"]   # "low", "normal", "critical"
```

### 2.9 `[system.monitor]` - Hardware Metric Sampling
Centralized sampler for CPU, GPU, RAM, Disk, and Network.
```toml
[system.monitor]
enabled              = true
cpu_temp_sensor_path = ""   # Explicit sysfs path (empty = auto-detect k10temp/coretemp)
cpu_poll_seconds     = 2.0  # CPU usage, frequency, temp, load averages (0 disables)
gpu_poll_seconds     = 5.0  # GPU metrics (probes run only while displayed)
memory_poll_seconds  = 2.0  # RAM usage
network_poll_seconds = 3.0  # Download/upload rates
disk_poll_seconds    = 10.0 # Disk usage and swap usage

# Global Value Highlighting Thresholds (tints sysmon widgets toward highlight_color):
cpu_usage_activity_threshold = 50 # %
cpu_usage_critical_threshold = 90 # %
cpu_temp_activity_threshold  = 60 # °C
cpu_temp_critical_threshold  = 85 # °C
ram_pct_activity_threshold   = 60 # %
ram_pct_critical_threshold   = 90 # %
gpu_temp_activity_threshold  = 60 # °C
gpu_temp_critical_threshold  = 85 # °C
net_rx_activity_threshold    = 1  # MB/s
net_rx_critical_threshold    = 50 # MB/s
```

### 2.10 `[weather]` - Open-Meteo Weather Service
```toml
[weather]
enabled         = true
refresh_minutes = 30
unit            = "metric" # "metric" (°C, km/h) | "imperial" (°F, mph)
effects         = true     # Visual rain/snow animations in UI
```

---

## 3. Automation & Event Hooks (`[hooks]`)

Hooks execute shell commands or IPC commands upon internal shell events. Values are passed via environment variables.

```toml
[hooks]
# Fired once after startup (IPC ready):
started = "systemctl --user start noctalia-ready.target"

# Fired on wallpaper change (sets $NOCTALIA_WALLPAPER_PATH, $NOCTALIA_WALLPAPER_CONNECTOR):
wallpaper_changed = "logger -t noctalia \"Wallpaper on $NOCTALIA_WALLPAPER_CONNECTOR: $NOCTALIA_WALLPAPER_PATH\""

# Fired after theme palette resolution:
colors_changed = [
  "systemctl --user reload foot-server.service",
  "logger -t noctalia 'palette colors changed'",
]

# Fired on theme mode toggle (sets $NOCTALIA_THEME_MODE, $NOCTALIA_THEME_MODE_PREVIOUS):
theme_mode_changed = "logger -t noctalia \"Theme mode changed to: $NOCTALIA_THEME_MODE\""

# Session Lock Events:
session_locked   = ["playerctl pause", "noctalia msg bar-hide"]
session_unlocked = ["noctalia msg bar-show", "noctalia msg dpms-on"]

# Power Sequences:
logging_out   = "logger -t noctalia 'Logout started'"
rebooting     = "systemctl --user stop my-service.service"
shutting_down = "systemctl --user stop my-service.service"

# Radio Toggles:
wifi_enabled       = "logger -t noctalia 'WiFi on'"
wifi_disabled      = "logger -t noctalia 'WiFi off'"
bluetooth_enabled  = "logger -t noctalia 'Bluetooth on'"
bluetooth_disabled = "logger -t noctalia 'Bluetooth off'"

# Battery Events (sets $NOCTALIA_BATTERY_PERCENT, $NOCTALIA_BATTERY_STATE):
battery_charging           = "notify-send 'Battery' 'Charging'"
battery_discharging        = "notify-send 'Battery' 'Discharging'"
battery_plugged            = "notify-send 'Battery' 'Plugged in'"
battery_percentage_changed = "logger -t noctalia \"Battery: $NOCTALIA_BATTERY_PERCENT% ($NOCTALIA_BATTERY_STATE)\""

# Power Profile Events (sets $NOCTALIA_POWER_PROFILE, $NOCTALIA_POWER_PROFILE_ORIGIN):
power_profile_changed = "logger -t noctalia \"Power profile: $NOCTALIA_POWER_PROFILE\""
```

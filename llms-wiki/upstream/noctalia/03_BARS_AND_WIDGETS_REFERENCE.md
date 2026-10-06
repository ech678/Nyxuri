# Noctalia: Bars Architecture & Complete Widget Catalog

This document provides a comprehensive technical reference for Noctalia's status bars, widget action/gesture dispatching system, capsule styling, and the complete parameters for all 28+ built-in widgets.

---

## 1. Bar Configuration & Multi-Monitor Architecture

Bars are defined as subtables under `[bar.<name>]`. Each configured bar spawns across all connected monitors by default, and can be customized per output with `[bar.<name>.monitor.<match>]`.

### 1.1 `[bar.<name>]` Configuration Table

```toml
[bar]
order = ["main"]                 # Creation order for layer-shell surfaces (for exclusive-zone layout)

[bar.default]
position           = "top"       # "top" | "bottom" | "left" | "right"
enabled            = true
auto_hide          = false       # Slide out when mouse leaves; reveal from edge trigger strip
smart_auto_hide    = false       # Visible on empty active workspace, auto-hide when windows are present
show_on_workspace_switch = true  # Briefly reveal hidden bar on workspace switch
reserve_space      = true        # Request exclusive zone from compositor (push windows away)
layer              = "top"       # "top" | "overlay" (overlay appears above fullscreen apps)

thickness          = 34          # Cross-axis size in pixels (height for horiz, width for vert)
background_opacity = 1.0         # 0.0 (transparent) to 1.0 (opaque)
border             = "outline"   # Color role or #RRGGBB for bar outline
border_width       = 0.0         # Outline width in pixels (0 disables)
shadow             = true        # Cast global [shell.shadow]
contact_shadow     = false       # Dark gradient between attached panels and bar (depth at seam)
panel_overlap      = 1           # Logical px attached panels overlap the bar edge to hide seam

# Corner Radii:
radius             = 12          # Global fallback corner radius
radius_top_left    = 12
radius_top_right   = 12
radius_bottom_left = 12
radius_bottom_right = 12
concave_edge_corners = true      # Carve screen-edge corners inward (requires margin_edge = 0)

# Margins & Insets:
margin_ends        = 100         # Main-axis inset from screen ends (creates floating island)
margin_edge        = 0           # Distance from screen edge (positive floats bar away from edge)
margin_opposite_edge = 0         # Extra reserved space on inward side of bar
padding            = 14          # Main-axis padding from bar ends to start/end sections
widget_spacing     = 6           # Spacing between widgets within a lane
hover_highlight    = true        # Soft foreground tint on widget hover
scale              = 1.0         # Content scale multiplier for icons and text
font_weight        = 500         # CSS font weight 100-1000 for widget labels
font_family        = ""          # Font family for bar widgets (empty = inherits shell font)

# Default Capsule Styling for All Widgets on this Bar:
capsule            = false
capsule_fill       = "surface_variant"
capsule_thickness  = 0.76        # Fraction of bar thickness (1.0 = full thickness)
capsule_radius     = 8.0         # Omit for auto pill radius
capsule_opacity    = 1.0
capsule_padding    = 6

# Widget Lanes:
start  = ["launcher", "wallpaper", "workspaces"]
center = ["clock"]
end    = ["media", "tray", "notifications", "clipboard", "network", "bluetooth", "volume", "brightness", "battery", "control-center", "session"]
```

### 1.2 Per-Monitor Overrides (`[bar.<name>.monitor.<match>]`)

```toml
[bar.default.monitor.dp1]
match              = "DP-1"     # Exact connector ("DP-1") or substring of monitor description ("DELL")
position           = "bottom"
thickness          = 40
start              = ["workspaces"]
center             = ["clock"]
end                = ["tray", "volume", "battery"]
```
- First match wins in file order.
- Overrides any bar-level setting (geometry, styling, lanes, dead zone).

---

## 2. Widget Actions & Gesture Dispatch System

Every bar widget (and the bar dead zone) can bind gestures to actions via an `actions` table.

### 2.1 Gestures & Scroll Repetition

| Gesture Key | Input Event |
|-------------|-------------|
| `left` | Left click |
| `right` | Right click |
| `middle` | Middle click |
| `back` | Mouse thumb button back |
| `forward` | Mouse thumb button forward |
| `scroll_up` | Wheel / touchpad up |
| `scroll_down` | Wheel / touchpad down |
| `scroll_left` | Wheel / touchpad left |
| `scroll_right` | Wheel / touchpad right |

- **Scroll repetition (`scroll_repeat`)**:
  - `"auto"` (default): navigation/cycle commands trigger once per gesture; ramp commands (volume, brightness) trigger per step.
  - `"gesture"`: triggers once per continuous swipe gesture.
  - `"steps"`: triggers on every quantized wheel detent step.

### 2.2 Action Forms & Resolution Precedence

| Action Syntax | Behavior |
|---------------|----------|
| `<ipc-command> [args]` | Executes internal Noctalia IPC command (e.g. `"panel-toggle launcher"`, `"volume-up"`) |
| `exec <command line>` | Spawns external shell command (e.g. `"exec kitty"`, `"exec notify-send 'hi'"`) |
| `none` | Disables / unbinds the gesture |

**Binding Precedence (later wins)**:
1. Built-in defaults (middle click opens widget settings)
2. Widget type defaults (left click opens default panel)
3. Bar-level actions `[bar.<name>.actions]`
4. Widget-specific actions `[widget.<name>.actions]`

**Reserved Gestures** (cannot be rebound at widget level):
- `workspaces`: `left` (activates clicked workspace)
- `taskbar`: `left` (activates window), `middle` (closes window)
- `tray`: `left` (activates item), `right` (opens item menu)
- `screenshot`: `right` (opens anchored capture menu)

### 2.3 Dead Zone Actions
The unpopulated space of the bar (e.g. margin insets) can trigger gestures:
```toml
[bar.default.dead_zone.actions]
left        = "panel-toggle launcher"
right       = "panel-toggle control-center" # Default right click
middle      = "exec foot"
scroll_up   = "volume-up"
scroll_down = "volume-down"
```

---

## 3. Widget Capsule & Capsule Groups

### 3.1 Shared Capsule Properties

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `capsule` | bool | `false` | Enable pill background |
| `capsule_fill` | string | `"surface_variant"` | Background color role or hex `#RRGGBB` |
| `capsule_foreground` | string | *unset* | Default icon + label color for capped widgets |
| `capsule_radius` | number | *auto pill* | Corner radius (0-80 logical px) |
| `capsule_padding` | number | `6` | Inner padding in logical px |
| `capsule_opacity` | number | `1.0` | Opacity multiplier (0.0–1.0) |
| `capsule_border` | string | *omitted* | Border color role or hex |
| `interactive` | bool | `true` (spacer: `false`) | When false, pointer events pass through to bar |
| `scale` | number | `1.0` | Multiplies bar scale (0.2–2.5) |

### 3.2 Capsule Groups (`[[bar.<name>.capsule_group]]`)

Groups multiple widgets into a single shared pill container:
```toml
[bar.default]
end = ["clock", "group:status_group", "session"]

[[bar.default.capsule_group]]
id                  = "status_group"
members             = ["network", "bluetooth", "volume"]
fill                = "surface_variant"
padding             = 6.0
opacity             = 0.95
enabled             = true
accordion           = true       # Collapse to 1st widget, expand on hover
accordion_direction = "end"      # "end" | "start"
widget_spacing      = 8
```

---

## 4. Built-in Widgets Reference Catalog (28+ Widgets)

### 4.1 Layout & Windows

#### 1. `active_window`
Shows active window icon and title for the current monitor.
```toml
[widget.active_window]
min_length       = 80               # Min width in px
max_length       = 260              # Max width in px
icon_size        = 14               # Icon size in px
title_scroll     = "none"           # "none" | "always" | "on_hover"
display          = "icon_and_text"  # "icon_and_text" | "icon_only" | "text_only"
show_empty_label = false            # Show "No active window" when none focused
```

#### 2. `clock`
Displays current time and date.
```toml
[widget.clock]
format          = "{:%H:%M}\n{:%d/%m}" # Horizontal format string
vertical_format = "{:%H\n%M}"          # Vertical bar format string
tooltip_format  = "{:%A, %B %d, %Y}"   # Hover tooltip format
timezone        = ""                   # e.g. "Europe/Berlin" or "UTC" (empty = local)
```

#### 3. `spacer`
Gaps between widgets or invisible interactive hot zones.
```toml
[widget.spacer]
length      = 8     # Pixel length
interactive = false # Set true to enable clicks/scrolls via .actions
```

#### 4. `taskbar`
Running and pinned application list with optional workspace grouping.
```toml
[widget.taskbar]
pinned                    = ["firefox", "kitty"] # Desktop entry IDs
pinned_opacity            = 0.5                  # Opacity for non-running pins
group_by_workspace        = false                # Group into workspace capsules
show_all_outputs          = false                # Show windows from all monitors
only_active_workspace     = false                # Show only active workspace windows
icon_scale                = 1.0                  # Icon size scaling (0.1–2.0)
item_spacing              = 4                    # Spacing between flat items (0–48)
show_window_title         = false                # Show titles on horizontal bars
window_title_max_width    = 100                  # Max title width in px
taskbar_max_width         = 8192                 # Total width budget
show_workspace_label      = true                 # Show workspace tag on group capsules
minimal                   = false                # Text-only workspace labels
workspace_label_placement = "corner"             # "corner" | "centered" | "inside"
hide_empty_workspaces     = false                # Hide empty workspace capsules
workspace_group_capsule   = true                 # Draw capsule around workspace group
workspace_group_content   = "icons"              # "icons" | "count" | "dots"
group_single_icon_per_app = false                # Collapse multi-window apps to one tile
show_active_indicator     = true                 # Active dot below focused window
active_indicator_color    = "primary"            # Color role or hex
active_opacity            = 1.0                  # Active window icon opacity
inactive_opacity          = 1.0                  # Inactive window icon opacity
focused_color             = "primary"            # Active workspace disc color
occupied_color            = "secondary"          # Occupied workspace disc color
empty_color               = "secondary"          # Empty workspace disc color
urgent_color              = "error"              # Urgent workspace disc color
focused_output_only       = false                # Only highlight active on focused monitor
```

#### 5. `text`
Static or fixed text label.
```toml
[widget.hostname]
type = "text"
text = "noctalia"
```

#### 6. `workspaces`
Workspace switcher with animated pills, minimal text, or Focus Hint styles.
```toml
[widget.workspaces]
style                      = "regular"       # "regular" | "minimal" | "focus_hint"
show_labels                = true            # Show numbers/names
label_source               = "id"            # "id" | "name"
max_label_chars            = 1               # Max non-numeric characters before truncation
pill_scale                 = 1.0             # Cross-axis thickness multiplier
active_pill_size           = 2.2             # Main-axis length multiple for active pill
inactive_pill_size         = 1.0             # Main-axis length multiple for inactive pills
focused_color              = "primary"       # Focused workspace pill fill
occupied_color             = "secondary"     # Occupied workspace pill fill
empty_color                = "secondary"     # Empty workspace pill fill
urgent_color               = "error"         # Urgent workspace pill fill
change_color_on_hover      = true            # Tint on mouse hover
focused_output_only        = false           # Only highlight on focused monitor
labels_only_when_occupied  = false           # Only label occupied and active tags
hide_when_empty            = false           # Hide empty workspaces
show_all_outputs           = false           # Show all monitors' workspaces
```

---

### 4.2 Audio, Media & Information

#### 7. `audio_visualizer`
Audio spectrum visualizer from PipeWire monitor stream.
```toml
[widget.audio_visualizer]
width           = 56        # Spectrum width in pixels
bands           = 16        # Number of frequency bands
mirrored        = true      # Mirror spectrum around center line
centered        = true      # Center bars on cross-axis
show_when_idle  = false     # Keep visible when no media is playing
color_1         = "primary" # Gradient start color role
color_2         = "primary" # Gradient end color role
```

#### 8. `media`
MPRIS player track title and album art.
```toml
[widget.media]
album_art_only     = false  # Show only circular album art
hide_album_art     = false  # Hide album artwork
hide_artist        = false  # Hide artist name (show title only)
artist_first       = false  # "Artist - Title" instead of "Title - Artist"
min_length         = 80     # Min width in px
max_length         = 220    # Max width in px
art_size           = 16     # Album art diameter in px
title_scroll       = "none" # "none" | "always" | "on_hover"
hide_when_no_media = false  # Hide when no player is active
```

#### 9. `volume`
PipeWire audio output (speaker) or input (microphone) volume controller.
```toml
[widget.volume]
device                 = "output"       # "output" (sink) | "input" (source/mic)
glyph                  = ""             # Custom icon (empty = dynamic volume icons)
mute_glyph             = ""             # Custom muted icon
effects_profile_glyphs = { Gaming = "device-gamepad" } # EasyEffects profile glyph map
custom_image           = ""             # Path to custom image
custom_image_colorize  = false          # Tint image with volume color
show_label             = true           # Show volume percentage text
mute_color             = "error"        # Color role when muted
hide_when_inactive     = false          # (Input only) hide when no app is capturing
```

#### 10. `weather`
Current weather conditions from Open-Meteo backend.
```toml
[widget.weather]
max_length       = 160 # Max text width in px
show_condition   = true # Show text description (e.g. "Overcast")
show_temperature = true # Show temperature (e.g. "22°C")
```

---

### 4.3 System & Hardware

#### 11. `battery`
Battery status from UPower.
```toml
[widget.battery]
device             = "auto"      # "auto" (system battery) | "BAT0" | object path
display_mode       = "glyph"     # "none" | "glyph" | "graphic" (animated battery box)
show_label         = true        # Show text percentage
label_content      = "percent"   # "percent" | "time" remaining | power "rate"
hide_when_plugged  = false       # Hide on AC power
hide_when_full     = false       # Hide at 100%
warning_color      = "error"     # Color below warning threshold
```

#### 12. `bluetooth`
Bluetooth adapter state and connected device.
```toml
[widget.bluetooth]
show_label                   = false # Show connected device name
hide_when_no_connected_device = false # Hide when no device is connected
```

#### 13. `brightness`
Display brightness percentage and adjustment.
```toml
[widget.brightness]
show_label = true # Show brightness percentage text
```

#### 14. `keyboard_layout`
XKB keyboard layout indicator and cycler.
```toml
[widget.keyboard_layout]
hide_when_single_layout = false     # Hide if only 1 layout is configured
show_glyph              = true      # Show keyboard icon
glyph                   = "keyboard"
custom_image            = ""
custom_image_colorize   = false
show_label              = true      # Show layout text
display                 = "short"   # "short" (compact code) | "full" (full name)
```

#### 15. `lock_keys`
Caps Lock, Num Lock, and Scroll Lock state.
```toml
[widget.lock_keys]
display          = "short" # "short" ("C N S") | "full" ("Caps Num Scroll")
show_caps_lock   = true
show_num_lock    = true
show_scroll_lock = false
hide_when_off    = false   # Hide indicator when key is off
```

#### 16. `network`
NetworkManager connection status (Wi-Fi SSID/signal, Ethernet, VPN).
```toml
[widget.network]
show_label     = true      # Show SSID or interface name
vpn_status     = "replace" # "replace" (shield icon) | "both" | "hidden"
show_vpn_label = false     # Show VPN name
```

#### 17. `power_profile`
Power profile indicator and switcher (Performance, Balanced, Power-saver).
```toml
[widget.power_profile]
# Uses shared widget properties. Left-click steps forward, right-click steps back.
```

#### 18. `privacy`
PipeWire audio/camera/screen capture indicator.
```toml
[widget.privacy]
hide_inactive  = false     # Hide when no captures are active
icon_spacing   = 4         # Pixel gap between icons (0–48)
active_color   = "primary" # Color while active
inactive_color = "outline" # Color while idle
```

#### 19. `sysmon`
Single resource monitor (CPU, RAM, Disk, Temp, Network rates).
```toml
[widget.sysmon]
stat                  = "cpu_usage" # See service stats: cpu_usage, ram_used, disk_used_pct, net_rx, net_tx...
path                  = "/"         # Mount path for disk stats
interface             = ""          # Interface for net_rx/net_tx (empty = total)
network_speed_unit    = "auto"      # "auto" | "kb" | "mb"
network_speed_compact = false       # Show "1.2M" instead of "1.2 MB/s"
visualization         = "gauge"     # "gauge" | "graph" | "none"
show_value            = true        # Show numeric text value
label_show_units      = true        # Include %, GiB, °C
label_min_width       = 0.0         # Min width in px
show_glyph            = true
glyph                 = ""          # Empty = default stat glyph
custom_image          = ""
custom_image_colorize = false
glyph_position        = "before"    # "before" | "after"
highlight_color       = "error"     # Color when exceeding critical threshold
```

#### 20. `tray`
StatusNotifierItem system tray icons.
```toml
[widget.tray]
hidden                 = []    # Bus names/tokens to hide
pinned                 = []    # Items always kept on bar when drawer = true
hide_passive           = true  # Hide items with Passive status
match_adjacent_spacing = false # Widen icon gaps to match neighboring widgets
drawer                 = false # Open tray in collapsible drawer panel
drawer_columns         = 3     # Icons per row in drawer (1–5)
drawer_item_size       = 20    # Icon size in drawer (8–64 px)
detached_panel         = false # Open drawer as floating panel
```

---

### 4.4 Quick Toggles

#### 21. `caffeine`
Compositor idle inhibitor toggle (`zwp_idle_inhibit_manager_v1`).
```toml
[widget.caffeine]
# Uses shared widget properties. Click toggles idle inhibitor.
```

#### 22. `nightlight`
Night light schedule and force toggle (`zwlr_gamma_control_unstable_v1`).
```toml
[widget.nightlight]
# Left-click toggles on/off. Right-click toggles force-override.
```

#### 23. `theme_mode`
Dark and light theme toggle.
```toml
[widget.theme_mode]
# Click toggles dark/light mode.
```

---

### 4.5 Buttons & Panels

#### 24. `clipboard`
Opens clipboard history panel.
```toml
[widget.clipboard]
glyph                 = "clipboard"
custom_image          = ""
custom_image_colorize = false
```

#### 25. `control_center`
Opens Control Center panel.
```toml
[widget.control-center]
glyph                 = "noctalia"
custom_image          = ""
custom_image_colorize = false
```

#### 26. `custom_button`
Customizable button with icon/image, label, and custom action bindings.
```toml
[widget.custom_button]
glyph                 = "heart"
custom_image          = ""
custom_image_colorize = false
label                 = "My Action"
tooltip               = "Run script"

[widget.custom_button.actions]
left  = "exec my-script.sh"
right = "volume-mute"
```

#### 27. `launcher`
Opens application search and runner panel.
```toml
[widget.launcher]
glyph                 = "search"
custom_image          = ""
custom_image_colorize = false
```

#### 28. `notifications`
Notification count badge and DND toggle.
```toml
[widget.notifications]
hide_when_no_unread = false # Hide when 0 unread notifications
```

#### 29. `screenshot`
Region and display capture tool.
```toml
[widget.screenshot]
glyph                 = "screenshot"
custom_image          = ""
custom_image_colorize = false

[widget.screenshot.actions]
left = "screenshot-region" # or "screenshot-fullscreen"
```

#### 30. `session`
Opens power and logout menu.
```toml
[widget.session]
glyph                 = "shutdown"
custom_image          = ""
custom_image_colorize = false
```

#### 31. `settings`
Opens Noctalia Settings application window.
```toml
[widget.settings]
glyph                 = "settings"
custom_image          = ""
custom_image_colorize = false
```

#### 32. `wallpaper`
Opens wallpaper browser panel.
```toml
[widget.wallpaper]
glyph                 = "wallpaper-selector"
custom_image          = ""
custom_image_colorize = false
```

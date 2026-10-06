# Umbriel Wayland Compositor: Technical Reference & Configuration

This document provides a comprehensive technical reference for **Umbriel**, a polished Wayland compositor developed in C++23 based on wlroots and SceneFX. It features scrolling and dwindle tiling layouts, per-output workspaces, hotplugging, per-output scratchpads, multi-level submaps, window/layer rules, SceneFX blur/shadows, and native Noctalia desktop shell integration.

---

## 1. Overview & Startup Architecture

- **Compositor binary**: `umbriel`
- **Session launcher**: `start-umbriel` (integrates with systemd `--user` and `environment.d`)
- **Portal backend**: `xdg-desktop-portal-umbriel` (screen casting, region/window capture)
- **X11 support**: `xwayland-satellite`
- **Config directory**: `~/.config/umbriel/config.toml` (supports `[include]` files)

---

## 2. Global Configuration Model (`config.toml`)

```toml
# ~/.config/umbriel/config.toml

[include]
files = ["appearance.toml", "keybinds.toml", "rules.toml"] # Relative paths, ~, $VAR supported

[general]
autostart         = ["noctalia --daemon", "kitty"] # Shell commands run once on startup
mod_key           = "Super"                       # "Super" | "Alt" | "Ctrl" | "Shift" (Mod alias in keybinds)
xwayland          = true                          # Spawn xwayland-satellite
show_cheatsheet   = true                          # Keybinds cheatsheet overlay on launch
focus_on_activate = false                         # When false, window requests mark urgent instead of stealing focus

[environment]
GTK_THEME            = "adw-gtk3-dark"
QT_QPA_PLATFORMTHEME = "qt6ct"

[workspaces]
back_and_forth = true # Re-selecting active workspace toggles to previously active workspace

[colors]
background       = "#141419F0"
text_primary     = "#E8E8EAFF"
text_muted       = "#8A8A92FF"
accent_primary   = "#7AA3FFFF"
accent_secondary = "#F5C96BFF"
warning          = "#F5C96BFF"
error            = "#FF6B6BFF"

[appearance]
prefer_no_csd               = true        # Request server-side decorations (xdg-decoration)
border_width                = 2           # Inner border in logical px (0–100)
outer_border_width          = 0           # Secondary outer border in px (0–100)
corner_radius               = 10          # Corner radius (0–500; 0 disables)
border_focused              = "#7AA3FFFF" # #RRGGBB or #RRGGBBAA
border_unfocused            = "#292933FF"
scratchpad_border_focused   = "#E5C07BFF" # Dedicated scratchpad focused border
scratchpad_border_unfocused = "#5C4A2AFF"
outer_border_color          = "#1A1A1FFF"
insert_hint_color           = "#7FC8FF80" # Drop-target preview during window drag
backdrop_color              = "#000000FF" # Background for fullscreen gaps
animation_ms                = 200         # Animation duration in ms (1–10000)

[appearance.blur]
enabled    = true  # Master switch (individual surfaces opt in via rules)
optimized  = true  # Cache one background blur per output
passes     = 3     # Blur passes (0–8)
radius     = 5     # Blur radius (0–100)
noise      = 0.02  # Noise overlay (0.0–1.0)
brightness = 0.9   # 0.0–2.0
contrast   = 0.9   # 0.0–2.0
saturation = 1.1   # 0.0–2.0

[appearance.shadow]
enabled  = true
softness = 10         # Gaussian blur sigma in px (0–200)
offset_x = 2          # -200 to 200
offset_y = 2          # -200 to 200
color    = "#0000007F"

[overview]
zoom                 = 0.5         # Workspace zoom scale (0.1–0.75)
background_tint      = "#10101430" # Tint composited over desktop
workspace_background = "#00000044" # Pill background behind each workspace preview

[hot_corners.top_left]
enabled  = true
delay_ms = 500
action   = "overview-open"

[layout]
mode          = "scrolling"         # "scrolling" | "dwindle"
gap           = 8                   # Inter-window gap in px (0–500)
width_presets = [0.333, 0.5, 0.667] # Fraction steps for window-cycle-width

[layout.scrolling]
default_width_fraction = 0.5  # Column initial width (0.1–1.0)
center_underfull_strip = true # Center strip when narrower than viewport
```

---

## 3. Input Configuration (`[input]`)

```toml
[input]
middle_click_paste = false # Toggle primary-selection paste

[input.keyboard]
layout       = "us,cz"               # XKB layouts (comma-separated)
variant      = ",qwertz"
options      = "grp:alt_shift_toggle"# XKB options
repeat_rate  = 25                    # Hz (0 disables)
repeat_delay = 600                   # ms

[input.touchpad]
tap            = true
natural_scroll = true

[input.mouse]
natural_scroll    = false
accel_profile     = "flat" # "flat" | "adaptive" | "custom <step> <p1> <p2>..."
sensitivity       = 0.0    # -1.0 to 1.0
scroll_wheel_step = 60     # Pixels per scroll step

[input.cursor]
theme            = "Bibata-Modern-Ice"
size             = 24
hardware_cursor  = true
hide_when_typing = false
hide_timeout_ms  = 0       # ms before hiding inactive cursor (0 disables)

[input.focus]
follows_mouse            = false
follows_mouse_max_scroll = 0.5 # Max viewport widths scrolled by mouse hover focus

[input.tablet]
enabled               = true
map_to_output         = "DP-1" # Confine pen area to output (or map_to_focused_window = true)
left_handed           = false
calibration_matrix    = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]

# Per-Device Hardware Overrides:
[[input.device]]
name        = "Acme Split Keyboard" # Exact name from libinput list-devices
layout      = "us"
repeat_rate = 40
```

---

## 4. Outputs & Workspace Layout Overrides (`[output.<name>]`)

```toml
[output.DP-1]
mode       = "3840x2160@165" # WIDTHxHEIGHT[@HZ]
position   = [0, 0]          # [x, y] layout coordinates
scale      = 1.25            # Output scaling (0.25–4.0)
transform  = "normal"        # normal | 90 | 180 | 270 | flipped | flipped-90
vrr        = "fullscreen"    # "disabled" | "always" | "fullscreen"
workspaces = 5               # "dynamic" | count (int) | ["WEB", "CHAT", "CODE"]
enabled    = true

# Per-Workspace Rule Overrides:
[[workspace]]
output                                = "DP-1"
name                                  = "CODE" # Or index = 1
layout.mode                           = "scrolling"
layout.gap                            = 4
layout.scrolling.default_width_fraction = 0.667
```

---

## 5. Keybinds, Submaps & Noctalia Integration (`[keybinds]`)

Keybinds syntax: `"Modifier+Key" = "action[:argument]"` (or table form for `repeat = false`).

### 5.1 Common Actions Catalog

| Action Syntax | Description |
|---|---|
| `spawn:<command>` | Run shell command (e.g. `"spawn:kitty"`, `"spawn:noctalia msg ..."`). |
| `workspace-switch:<name[/output]>` | Switch to named/numbered workspace. |
| `window-move-to-workspace:<name>` | Move focused window to workspace. |
| `window-set-width:<frac>` | Set scrolling column width (0.1–1.0). |
| `window-modify-width:<delta>` | Adjust width fraction (e.g. `-0.1`, `+0.1`). |
| `workspace-set-layout:<scrolling\|dwindle\|toggle>` | Switch layout algorithm dynamically on active workspace. |
| `window-focus-left` / `right` / `up` / `down` | Directional window focus. |
| `column-move-left` / `right` | Reorder column along the strip. |
| `window-move-up` / `down` | Move window within its column stack. |
| `window-consume-left` | Pull window into left column. |
| `window-expel-right` | Pop window out to a new column on the right. |
| `window-cycle-width` | Cycle column width through `layout.width_presets`. |
| `window-toggle-floating` | Toggle floating state. |
| `window-toggle-pinned` | Pin floating window above fullscreen / across workspaces. |
| `window-toggle-fullscreen` | Toggle fullscreen mode. |
| `window-toggle-maximize` | Expand column to full viewport width. |
| `window-close` | Close focused window. |
| `overview-toggle` / `overview-open` | Toggle/open animated overview. |
| `cheatsheet-toggle` | Toggle keybinds cheatsheet overlay. |
| `keyboard-layout-next` | Switch to next XKB keymap layout. |
| `session-quit` / `session-quit:skip-confirmation` | Exit Wayland session. |

### 5.2 Scratchpad Actions
| Action | Description |
|---|---|
| `window-move-to-scratchpad[:output]` | Move focused window to output scratchpad. |
| `scratchpad-toggle[:output]` | Toggle visibility of output's scratchpad windows. |
| `window-restore-from-scratchpad[:output]` | Restore scratchpad window back to its workspace. |
| `scratchpad-focus-next[:output]` | Cycle focus among visible scratchpad windows. |

### 5.3 Submaps (Modal Keybind Layers)
```toml
[keybinds]
"Mod+S" = "submap:capture"

"submap[capture],1"      = "spawn:grim ~/screenshot.png"
"submap[capture],2"      = "submap:region"
"submap[capture],Escape" = "submap:reset"

"submap[region],R"       = "spawn:grim -g '$(slurp)' ~/region.png"
"submap[region],Escape"  = "submap:reset"

"Escape" = "submap:reset" # Global emergency reset
```

### 5.4 Noctalia Shell Keybind Examples
```toml
[keybinds]
"Mod"             = "spawn:noctalia msg panel-toggle launcher"
"Mod+V"           = "spawn:noctalia msg panel-toggle clipboard"
"Mod+W"           = "spawn:noctalia msg panel-toggle wallpaper"
"Mod+X"           = "spawn:noctalia msg bar-toggle"
"Mod+P"           = "spawn:noctalia msg screenshot-region"
"Mod+Shift+P"     = "spawn:noctalia msg screenshot-fullscreen"
"Mod+Shift+W"     = "spawn:noctalia msg desktop-widgets-toggle-edit"
"Mod+Escape"      = "spawn:noctalia msg panel-toggle session"
```

---

## 6. Window & Layer Rules

### 6.1 Window Rules (`[[window_rule]]`)

```toml
# Blur all windows
[[window_rule]]
blur = true

# Floating rules for utility apps
[[window_rule]]
match.app_id     = "^(qalculate-gtk|org\\.pulseaudio\\.pavucontrol|pavucontrol)$"
default_floating = true
default_size     = [800, 600]
default_position = { x = 0, y = 0, anchor = "center" } # center | top_left | bottom_right ...

# Browser default sizing in scrolling layout
[[window_rule]]
match.app_id  = "^(firefox|zen-alpha|chromium)$"
default_width = 0.75

# Terminal opacity & narrow columns
[[window_rule]]
match.app_id  = "^(kitty|foot|Alacritty)$"
default_width = 0.33
opacity       = 0.95

# Game rule: Force VRR on focused output
[[window_rule]]
match.app_id = "^(steam_app_[0-9]+|gamescope)$"
vrr          = "always"
```

### 6.2 Layer Rules (`[[layer_rule]]`)

```toml
# Enable blur for Noctalia shell layer surfaces
[[layer_rule]]
match.namespace   = "^noctalia-(bar-[^\"]+|notification|dock|panel|attached-panel|osd|desktop-widget-[^\"]*)$"
blur              = true
blur_ignore_alpha = 0.5  # Skip blur on fully transparent areas
blur_popups       = true # Blur child dropdown menus
```

# Noctalia Greeter: Architecture, Configuration & Integration

This document provides a comprehensive technical reference for **Noctalia Greeter**, a modern Wayland login manager built for `greetd` with native wlroots compositor integration and visual synchronization with the Noctalia shell.

---

## 1. Architecture & Greetd Setup

Noctalia Greeter runs as a standalone client inside its dedicated wlroots compositor (`noctalia-greeter-compositor`), managed by the `greetd` display manager daemon.

### 1.1 `greetd` Configuration (`/etc/greetd/config.toml`)

```toml
[default_session]
command = "/usr/bin/noctalia-greeter-session"
user    = "greeter"
```

#### Command-line Arguments
```toml
# Pass default session and default user to skip user picker:
command = "/usr/bin/noctalia-greeter-session -- --session 'Hyprland (uwsm-managed)' --user lysec"
```
- Note: Session name must match the desktop entry `Name=` field (not `.desktop` basename). Discover valid names via `noctalia-greeter sessions`.

### 1.2 System Dependencies
- `greetd`: Session launcher daemon
- `accountsservice` (`accounts-daemon`): Supplies user avatar images (`IconFile`) from `org.freedesktop.Accounts`
- `polkit` (`pkexec` or `run0`): Required for appearance sync from Noctalia desktop

---

## 2. Configuration Model (`greeter.toml` vs `sync.toml`)

The greeter configuration resides under `/var/lib/noctalia-greeter/`:

1. **`greeter.toml` (Authoritative Admin Config)**: Declarative file (NixOS `programs.noctalia-greeter.settings`). Never overwritten by Sync or login UI. Takes precedence over `sync.toml`.
2. **`sync.toml` (Sync & UI Mutable State)**: Managed by Noctalia's Sync Now feature and UI selections (remembered last user, last session, last scheme).
3. **`wallpaper*`**: Sync-installed wallpaper image files.

---

## 3. Full `greeter.toml` Specification

```toml
# /var/lib/noctalia-greeter/greeter.toml

[session]
default = "niri"              # Exact Name= from desktop entry (e.g. "niri", "Hyprland (uwsm-managed)")

[user]
default = "ray"               # Username from /etc/passwd to open directly into password prompt

[appearance]
scheme              = "Synced" # "Synced" | "Noctalia" | "Catppuccin" | etc.
password_style      = "random" # "default" (dots) | "random" (cycling glyph shapes)
hide_logo           = false    # Hide Noctalia logo
theme_mode          = "dark"   # "dark" | "light"
corner_radius_scale = 1.0
font_family         = "Inter"

# Declarative Palette (Overrides Sync when complete):
[appearance.palette]
primary            = "#fff59b"
on_primary         = "#0e0e43"
secondary          = "#a9aefe"
on_secondary       = "#0e0e43"
tertiary           = "#9BFECE"
on_tertiary        = "#0e0e43"
error              = "#FD4663"
on_error           = "#0e0e43"
surface            = "#070722"
on_surface         = "#f3edf7"
surface_variant    = "#11112d"
on_surface_variant = "#7c80b4"
outline            = "#21215F"
shadow             = "#070722"
hover              = "#9BFECE"
on_hover           = "#0e0e43"

# Default Wallpaper:
[appearance.wallpaper]
path       = "/var/lib/noctalia-greeter/wallpaper.webp"
fill_mode  = "crop"           # "center" | "crop" | "fit" | "stretch" | "repeat"
fill_color = "#070722"

# Per-Connector Wallpaper:
[appearance.wallpapers.DP-1]
path      = "/var/lib/noctalia-greeter/wallpaper-DP-1.webp"
fill_mode = "crop"

[output]
name       = "DP-2"                         # Pin greeter to single connector (omit to show on all)
layout     = "DP-1:0,0; DP-2:2560,0"        # Multi-monitor coordinates in logical px
width      = 5120                           # Physical DRM mode width
height     = 2160                           # Physical DRM mode height
transforms = "DP-1:normal; HDMI-A-1:270"    # normal | 90 | 180 | 270 | flipped
scales     = "DP-1:1; DP-2:1.25"            # Per-output scaling matching desktop session
scale      = 1.5                            # Global forced UI scale override

[idle]
timeout = 300                               # Screen blank timeout in seconds (0 disables, max 86400)

[cursor]
theme = "Bibata-Modern-Ice"
size  = 24
path  = "/usr/share/icons"                  # Icon search path

[keyboard]
layout  = "us,cz"                           # XKB layout code(s)
variant = ",qwertz"
options = "grp:alt_shift_toggle"
numlock = true                              # Enable Num Lock on startup

[auth]
allow_empty_password = false                # Allow empty submit for fprintd / smartcard PAM
```

---

## 4. Desktop Appearance Synchronization

When Noctalia Shell is running, navigate to **Settings → Security → Noctalia Greeter → Sync Now** (or enable **Auto-Sync Greeter**):

### 4.1 Synced Attributes
- Active wallpaper image (including multi-monitor per-output wallpapers).
- Active theme palette & theme mode (`dark`/`light`).
- Shell font family (`[shell].font_family`).
- Corner radius scale (`[shell].corner_radius_scale`).
- Display layout, scales, and rotation (`[output].layout`, `[output].scales`, `[output].transforms`).
- Power actions & commands (`[shell.session.power]`).

### 4.2 Non-interactive Polkit Sync Command
```sh
pkexec noctalia-greeter-apply-appearance "$XDG_RUNTIME_DIR/noctalia-greeter-sync"
```

---

## 5. Keyboard Navigation & Helper CLI

### 5.1 Keyboard Shortcuts
- `Tab` / `Shift+Tab`: Navigate between controls
- `↑` / `↓`: Navigate user / session lists
- `Enter`: Submit password / confirm selection
- `Space`: Toggle focused control
- `Esc`: Back to user list / close menu
- `F3`: Open session selector
- `F7`: Open color scheme selector
- `Ctrl+Alt+F1`..`F12`: Switch Linux Virtual Terminal (TTY)

### 5.2 Helper CLI Commands
```sh
# List valid session names (exact strings for [session].default / --session):
noctalia-greeter sessions

# List connected Wayland outputs (for [output].name / [output].layout):
noctalia-greeter outputs
```

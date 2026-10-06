# Noctalia Shell, Greeter & Umbriel: Complete LLM Reference Manual (All-In-One)

> This document is a complete, single-file compilation of all Noctalia v5+, Noctalia Greeter, and Umbriel Compositor technical reference manuals, audited and verified for LLM comprehension.

---



<!-- ==================== BEGIN FILE: 00_INDEX.md ==================== -->

# Noctalia Ecosystem: Comprehensive LLM Documentation Index & Knowledge Map

This documentation set provides an authoritative, complete, and dense technical reference for **Noctalia v5+**, **Noctalia Greeter**, and the **Umbriel Compositor**. All legacy v4 (Quickshell/QML) obsolete documentation has been audited line-by-line and purged.

---

## 1. System Architecture Overview

```
+-----------------------------------------------------------------------------+
|                          WAYLAND COMPOSITOR LAYER                           |
|  +---------------------------+  +----------------------------------------+  |
|  |    Umbriel Compositor     |  |    External Compositors                |  |
|  |  (C++23 / wlroots/SceneFX)|  |    (Niri, Hyprland, Sway, Mango, etc.) |  |
|  +-------------+-------------+  +-------------------+--------------------+  |
|                | zwlr_layer_shell_v1                |                       |
|                +------------------+-----------------+                       |
+-----------------------------------|-----------------------------------------+
                                    |
+-----------------------------------v-----------------------------------------+
|                        NOCTALIA DESKTOP SHELL (v5+)                         |
|  +-----------------------------------------------------------------------+  |
|  | Core Shell Engine (C++23 / OpenGL ES 2.0 / FreeType / HarfBuzz / EGL) |  |
|  +-----------------------------------------------------------------------+  |
|  | Surfaces: Bars | Dock | App Launcher | Control Center | Notifications |  |
|  |           Desktop Widgets | Lock Screen | Window Switcher (Alt+Tab)   |  |
|  +-----------------------------------------------------------------------+  |
|  | Background Services: Audio (PipeWire), Battery (UPower), Brightness,  |  |
|  |                      Calendar (CalDAV/Google), Idle (ext-idle),       |  |
|  |                      Night Light (gamma), SysMon, Weather (OpenMeteo) |  |
|  +-----------------------------------------------------------------------+  |
|  | Automation & Theming: TemplateEngine, Material 3 Palettes, Hooks     |  |
|  +-----------------------------------------------------------------------+  |
|  | Plugin Engine: Isolated Luau VMs, API Levels 3-28, Declarative `ui.*` |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------+-----------------------------------------+
                                    |
+-----------------------------------v-----------------------------------------+
|                          NOCTALIA GREETER LAYER                             |
|  +-----------------------------------------------------------------------+  |
|  |  greetd -> noctalia-greeter-session -> noctalia-greeter-compositor    |  |
|  |  Appearance sync from shell via Polkit -> /var/lib/noctalia-greeter/  |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
```

---

## 2. Documentation Volume Breakdown

| Volume | File | Core Content & Coverage |
|---|---|---|
| **01** | [`01_GETTING_STARTED_AND_COMPOSITORS.md`](01_GETTING_STARTED_AND_COMPOSITORS.md) | Package installation (Arch, Fedora, openSUSE, Gentoo, Void, Debian/Ubuntu, Guix, NixOS), Compositor configuration (Niri, Hyprland, Sway/Scroll, Mango, Labwc, KDE Plasma), Systemd services, Daemons, Troubleshooting. |
| **02** | [`02_CONFIGURATION_AND_CORE_SHELL.md`](02_CONFIGURATION_AND_CORE_SHELL.md) | Config layering (`~/.config/noctalia/*.toml` vs `settings.toml`), Profiles, `[storage]`, `[shell]`, `[shell.animation]`, `[shell.shadow]`, `[shell.panel]`, `[shell.launcher]`, `[hot_corners]`, `[shell.screenshot]`, `[shell.privacy]`, `[accessibility]`, `[osd]`, `[lockscreen]`, `[keybinds]`, `[shell.session]`, Date/Time format tokens. |
| **03** | [`03_BARS_AND_WIDGETS_REFERENCE.md`](03_BARS_AND_WIDGETS_REFERENCE.md) | `[bar.<name>]` layout & geometry, Multi-monitor overrides, Gesture dispatching system (`actions` table, `scroll_repeat`), Capsules & Capsule Groups, Complete parameter tables for **all 28+ built-in widgets**. |
| **04** | [`04_SURFACES_AND_SERVICES.md`](04_SURFACES_AND_SERVICES.md) | `[dock]`, `[control_center]` & shortcuts, `[wallpaper]` & `[backdrop]`, `[desktop_widgets]` & `[lockscreen_widgets]`, 10 background services (Audio, Battery, Brightness, Calendar, Idle, Location, Night Light, Notifications, Sysmon, Weather), Event `[hooks]`. |
| **05** | [`05_THEMING_PALETTES_AND_TEMPLATES.md`](05_THEMING_PALETTES_AND_TEMPLATES.md) | `[theme]`, 16 core color roles, JSON palette schema, Template Engine syntax (`<* *>` and `{{ }}`), 48 Material color tokens, Terminal tokens, Color/string filters, `[theme.templates]` config, App integrations (GTK, Qt, Foot, Umbriel). |
| **06** | [`06_IPC_COMMANDS_AND_CLI.md`](06_IPC_COMMANDS_AND_CLI.md) | Complete reference for all `noctalia msg <command>` calls: Shell/Session/Settings, Bars & Panels, Dock, Desktop/Lockscreen widgets, Notifications, Clipboard, Media, Wallpaper, Theme, Screenshots, System Controls (Volume, Brightness, Radios, Power), Plugin IPC. |
| **07** | [`07_PLUGIN_DEVELOPMENT_AND_LUAU_API.md`](07_PLUGIN_DEVELOPMENT_AND_LUAU_API.md) | Plugin architecture, API levels 3–28 ledger, `plugin.toml` manifest, 6 entry kinds (`widget`, `shortcut`, `launcher_provider`, `desktop_widget`, `panel`, `service`), Lifecycle callbacks, `noctalia.*` runtime API, Declarative `ui.*` component system. |
| **08** | [`08_NOCTALIA_GREETER.md`](08_NOCTALIA_GREETER.md) | Noctalia Greeter architecture for `greetd`, `/var/lib/noctalia-greeter/` state (`greeter.toml` admin config vs `sync.toml` state), Desktop appearance synchronization via Polkit (`noctalia-greeter-apply-appearance`), CLI & Keyboard shortcuts. |
| **09** | [`09_UMBRIEL_COMPOSITOR.md`](09_UMBRIEL_COMPOSITOR.md) | Umbriel Wayland Compositor (C++23/wlroots/SceneFX), `config.toml`, Scrolling and Dwindle layouts, Multi-monitor outputs, Workspace models, Keybinds, Submaps, Scratchpads, Window Rules & Layer Rules. |
| **ALL**| [`NOCTALIA_ALL_IN_ONE.md`](NOCTALIA_ALL_IN_ONE.md) | Complete, single-file compilation of all documentation volumes for single-pass LLM context loading. |

---

## 3. Fast Reference: Paths & Precedence

### 3.1 File Locations
- **Declarative User Config**: `~/.config/noctalia/*.toml` (or `$NOCTALIA_CONFIG_HOME`, `$XDG_CONFIG_HOME/noctalia/`)
- **State & Runtime Overrides (GUI / IPC writes)**: `~/.local/state/noctalia/settings.toml`
- **Cached Community Palettes**: `~/.local/state/noctalia/community-palettes/`
- **Cached Community Templates**: `~/.local/state/noctalia/community-templates/`
- **Plugin Persistent Data**: `~/.local/state/noctalia/plugins/<author>/<plugin>/`
- **Encrypted Storage Cache**: `~/.cache/noctalia/` (clipboard, calendar events)
- **Greeter Config**: `/var/lib/noctalia-greeter/greeter.toml` (admin) & `/var/lib/noctalia-greeter/sync.toml` (runtime)
- **Umbriel Compositor Config**: `~/.config/umbriel/config.toml`

### 3.2 Key Differences: v4 (Legacy Quickshell) vs v5 (Native C++)
| Aspect | v4 (Deprecated / Purged) | v5+ (Current Standard) |
|---|---|---|
| **Core Architecture** | QML / JavaScript / Quickshell | Native C++23 / OpenGL ES 2.0 / EGL |
| **Configuration Format** | JSON / QML properties | TOML (`~/.config/noctalia/*.toml`) |
| **State Storage** | `settings.json` | `settings.toml` |
| **Plugin Language** | QML files | Luau scripts (`.luau`) with declarative `ui.*` trees |
| **IPC Mechanism** | Socket scripts | `noctalia msg <cmd>` / Unix Domain Socket |
| **Theming System** | Color scheme JSONs | Material 3 Color Roles / TemplateEngine (`<* *>` and `{{ }}`) |
| **Wayland Protocol** | Plasma / Quickshell wrappers | Native `wlr_layer_shell_v1`, `ext_idle_notifier_v1`, `wlr_screencopy_unstable_v1`, `wlr_gamma_control` |


<!-- ==================== END FILE: 00_INDEX.md ==================== -->


---


<!-- ==================== BEGIN FILE: 01_GETTING_STARTED_AND_COMPOSITORS.md ==================== -->

# Noctalia: Installation, Runtime & Compositor Integrations

This document provides a comprehensive, LLM-optimized guide for installing, running, configuring Wayland compositors for, and troubleshooting Noctalia (v5+).

---

## 1. Overview & Architecture

Noctalia (v5+) is a modern, standalone desktop shell written in native C++ and OpenGL ES.
- **Runtime**: Native C++ binary (`noctalia`), OpenGL ES rendering, Layer Shell protocol.
- **IPC Architecture**: Controlled via UNIX socket / CLI with `noctalia msg <command>`.
- **Scripting Engine**: Embedded Luau runtime with declarative `ui.*` components.
- **Configuration Format**: Standard TOML located at `~/.config/noctalia/*.toml` (declarative) and `~/.local/state/noctalia/settings.toml` (GUI overrides).

---

## 2. Package Installation

### 2.1 Distribution Packages

- **Arch Linux** (`extra` repo):
  ```bash
  sudo pacman -S noctalia
  ```

- **Fedora** (Fedora 44+ in default repos; git builds via Copr):
  ```bash
  # Stable (Fedora 44+)
  sudo dnf install noctalia

  # Git master snapshot (LionHeartP Copr)
  sudo dnf copr enable lionheartp/Hyprland
  sudo dnf install noctalia-git
  ```

- **openSUSE** (OBS `home:neifua:Noctalia` for Tumbleweed & Slowroll; Leap 16.0 is unsupported due to sdbus-c++ < 2.0 requirement):
  ```bash
  # Tumbleweed repo
  sudo zypper addrepo --refresh --name noctalia-v5 https://download.opensuse.org/repositories/home:neifua:Noctalia/openSUSE_Tumbleweed/home:neifua:Noctalia.repo
  sudo zypper refresh
  sudo zypper install noctalia      # Stable
  # or: sudo zypper install noctalia-git  # Unstable

  # Slowroll repo
  sudo zypper addrepo --refresh --name noctalia-v5 https://download.opensuse.org/repositories/home:neifua:Noctalia/openSUSE_Slowroll/home:neifua:Noctalia.repo
  sudo zypper refresh
  sudo zypper install noctalia
  ```

- **Gentoo** (GURU overlay):
  ```bash
  # Unmask package
  echo "gui-apps/noctalia **" | sudo tee -a /etc/portage/package.accept_keywords/noctalia
  # (Optional: mask live ebuild to use versioned releases <=gui-apps/noctalia-9999)
  emerge --ask gui-apps/noctalia
  ```

- **Void Linux** (Custom XBPS repo):
  ```bash
  echo "repository=https://repo.voiders.dev" | sudo tee /etc/xbps.d/10-voiders-community.conf
  sudo xbps-install -S
  sudo xbps-install noctalia
  # Note: Ensure sdbus-c++ is installed if runtime issues occur.
  ```

- **Debian / Ubuntu** (Official APT repository for Debian Trixie/Sid, Ubuntu 26.04+ on `amd64` / `arm64`):
  ```bash
  # 1. Install signing key
  wget https://pkg.noctalia.dev/deb/nickh-archive-keyring.deb && sudo dpkg -i nickh-archive-keyring.deb

  # 2. Add sources list (choose one)
  # Debian Trixie:
  sudo wget -O /etc/apt/sources.list.d/noctalia-trixie.sources https://pkg.noctalia.dev/deb/noctalia-trixie.sources
  # Debian Sid:
  sudo wget -O /etc/apt/sources.list.d/noctalia-unstable.sources https://pkg.noctalia.dev/deb/noctalia-unstable.sources
  # Ubuntu 26.04:
  sudo wget -O /etc/apt/sources.list.d/noctalia-resolute.sources https://pkg.noctalia.dev/deb/noctalia-resolute.sources

  # 3. Install
  sudo apt update && sudo apt install noctalia
  ```

- **GNU Guix** (Guix Channel `(noctalia)` with package `noctalia-git`):
  ```scheme
  ;; Add to ~/.config/guix/channels.scm:
  (list (channel
          (name 'noctalia)
          (url "https://github.com/noctalia-dev/noctalia")
          (branch "main"))
        %default-guix-channel)
  ```
  After `guix pull`, install via `guix install noctalia-git` or declare `(use-modules (noctalia))` in home / system configuration.

---

### 2.2 NixOS Configuration

To use full hardware features in Noctalia on NixOS (WiFi, Bluetooth, Power profiles, Battery), ensure system services are active:
```nix
networking.networkmanager.enable = true;
hardware.bluetooth.enable = true;
services.power-profiles-daemon.enable = true; # or services.tuned.enable = true;
services.upower.enable = true;
```

#### Flake Setup & Binary Cache (Cachix)
```nix
# flake.nix
{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    # Use the cachix branch to track the latest pre-built cached commit:
    noctalia.url = "github:noctalia-dev/noctalia/cachix";
  };

  # Binary Cache Settings:
  nixConfig = {
    extra-substituters = [ "https://noctalia.cachix.org" ];
    extra-trusted-public-keys = [ "noctalia.cachix.org-1:pCOR47nnMEo5thcxNDtzWpOxNFQsBRglJzxWPp3dkU4=" ];
  };

  outputs = { self, nixpkgs, noctalia, ... }@inputs: {
    # NixOS System configuration
    nixosConfigurations.myhostname = nixpkgs.lib.nixosSystem {
      specialArgs = { inherit inputs; };
      modules = [
        ./configuration.nix
        noctalia.nixosModules.default # Optional NixOS system module
      ];
    };
  };
}
```

#### NixOS Module Options
```nix
programs.noctalia = {
  enable = true;
  # Automatically enables NetworkManager, Bluetooth, UPower, and power-profiles-daemon:
  recommendedServices.enable = true;
};
```

#### Home Manager Module
```nix
{ inputs, pkgs, ... }:
{
  imports = [
    inputs.noctalia.homeModules.default
  ];

  programs.noctalia = {
    enable = true;

    # Optional systemd integration:
    # (Note: if enabled, also set launch_apps_as_systemd_services = true in shell config)
    # systemd.enable = true;

    # Declarative settings (converts Nix attrset to TOML, or can be a path to a .toml file):
    settings = {
      theme = {
        mode = "dark";
        source = "builtin";
        builtin = "Catppuccin";
      };

      wallpaper = {
        enabled = true;
        default.path = "/home/user/Pictures/wallpapers/default.png";
      };
    };
  };
}
```

---

### 2.3 Manual Build from Source

Build dependencies required:
- Build tools: `meson`, `gcc`/`g++`, `just`, `git`, `pkg-config`
- Wayland / Graphics: `wayland`, `wayland-protocols`, `libglvnd` (EGL/GLES), `freetype2`, `fontconfig`, `cairo`, `pango`, `harfbuzz`, `libxkbcommon`, `glib2`
- Security & System: `libsecret`, `libsodium`, `sdbus-c++` (>= v2.0), `libpipewire-0.3`, `wireplumber-0.5`, `polkit` (`polkit-agent-1`, `polkit-gobject-1`), `pam`
- Network & Formats: `curl`, `libwebp`, `libjxl`, `libsndfile`, `librsvg`, `libqalculate`, `libxml2`, `md4c`, `tomlplusplus`, `nlohmann-json`, `stb`
- Performance allocator (optional but recommended): `jemalloc`
- Vendored within repo (no system pkg needed): `Wuffs`, `Luau`, `fzy`, Material Color Utilities.

```bash
git clone https://github.com/noctalia-dev/noctalia --branch main
cd noctalia

# Release Mode Build & Install:
just configure release        # builds into build-release/
just build release
sudo just install release     # default prefix is /usr/local

# Custom Prefix Install (e.g. to ~/.local):
just configure release "$HOME/.local"
just build release
just install release

# Debug Mode:
just configure
just build
just run
```

---

## 3. Running Noctalia

### 3.1 Invocation Methods
- **Standard execution**: `noctalia`
- **Daemon mode** (returns after shell initialization is complete): `noctalia --daemon`
  - Recommended for compositors or scripts that wait for the process to be ready before proceeding.
- **Systemd user service**: Can run as `systemd --user` unit.
  - Recommended shell setting: `launch_apps_as_systemd_services = true` under `[shell]`. This ensures child applications launched by Noctalia are isolated and not killed when the shell service restarts.

### 3.2 Uninstallation & Cleanup
```bash
# Remove manual build files (if installed to ~/.local):
rm ~/.local/bin/noctalia
rm -rf ~/.local/share/noctalia

# Remove configuration, state, and caches:
rm -rf ~/.config/noctalia
rm -rf ~/.local/state/noctalia
rm -rf ~/.cache/noctalia
```

---

## 4. Wayland Compositor Integrations

### 4.1 Niri (`~/.config/niri/config.kdl`)

```kdl
// 1. Autostart
spawn-at-startup "noctalia"

// 2. Window Rules
window-rule {
  geometry-corner-radius 20
  clip-to-geometry true
}

// Floating Noctalia settings window
window-rule {
  match app-id="dev.noctalia.Noctalia"
  open-floating true
  default-column-width { fixed 1080; }
  default-window-height { fixed 920; }
}

debug {
  honor-xdg-activation-with-invalid-serial
}

// 3. Keybinds
binds {
  Mod+Space     { spawn-sh "noctalia msg panel-toggle launcher"; }
  Mod+S         { spawn-sh "noctalia msg panel-toggle control-center"; }
  Mod+Comma     { spawn-sh "noctalia msg settings-toggle"; }
  Alt+Tab       { spawn-sh "noctalia msg window-switcher"; }

  XF86AudioRaiseVolume  { spawn-sh "noctalia msg volume-up"; }
  XF86AudioLowerVolume  { spawn-sh "noctalia msg volume-down"; }
  XF86AudioMute         { spawn-sh "noctalia msg volume-mute"; }
  XF86MonBrightnessUp   { spawn-sh "noctalia msg brightness-up"; }
  XF86MonBrightnessDown { spawn-sh "noctalia msg brightness-down"; }
}

// 4. Blur Rules (Niri >= 26.04)
window-rule {
  background-effect {
    blur true
    xray false
  }
}

layer-rule {
  match namespace="^noctalia-(bar-[^\"]+|notification|dock|panel|attached-panel|osd)$"
  background-effect {
    xray false
    // To disable blur on Noctalia surfaces, uncomment:
    // blur false
  }
}

layer-rule {
  match namespace="noctalia-window-switcher"
  background-effect {
    blur true
    xray false
  }
}

blur {
  passes 2
  offset 3.0
  noise 0.03
  saturation 1.0
}

// 5. Overview & Wallpaper Options:
// Option 1: Blurred Overview Wallpaper (requires [niri/backdrop] enabled in Noctalia)
layer-rule {
  match namespace="^noctalia-backdrop"
  place-within-backdrop true
}

// 6. Laptop Lid Switch Handling (Lock & Suspend):
switch-events {
  lid-close { spawn "noctalia" "msg" "session" "lock-and-suspend"; }
}
```

---

### 4.2 Hyprland (`~/.config/hypr/hyprland.lua`)

```lua
local mainMod = "SUPER"
local ipc = "noctalia msg "

-- 1. Autostart
hl.on("hyprland.start", function()
  hl.exec_cmd("noctalia")
end)

-- 2. General Decoration & Shadow
hl.config({
  general = {
    gaps_in = 5,
    gaps_out = 10,
  },
  decoration = {
    rounding = 20,
    rounding_power = 2,
    shadow = {
      enabled = true,
      range = 4,
      render_power = 3,
      color = 0xee1a1a1a,
    },
    blur = {
      enabled = true,
      size = 3,
      passes = 2,
      vibrancy = 0.1696,
    },
  },
})

-- 3. Persistent Workspaces
hl.workspace_rule({ workspace = "1", monitor = "DP-1", persistent = true, default_name = "web" })
hl.workspace_rule({ workspace = "2", monitor = "DP-1", persistent = true, default_name = "code" })
hl.workspace_rule({ workspace = "3", monitor = "DP-1", persistent = true, default_name = "chat" })
hl.workspace_rule({ workspace = "4", monitor = "DP-1", persistent = true, default_name = "game" })
hl.workspace_rule({ workspace = "5", monitor = "DP-1", persistent = true, default_name = "design" })

-- 4. IPC Keybinds
hl.bind(mainMod .. "+Space", hl.dsp.exec_cmd(ipc .. "panel-toggle launcher"))
hl.bind(mainMod .. "+S", hl.dsp.exec_cmd(ipc .. "panel-toggle control-center"))
hl.bind(mainMod .. "+comma", hl.dsp.exec_cmd(ipc .. "settings-toggle"))
hl.bind("ALT + Tab", hl.dsp.exec_cmd(ipc .. "window-switcher"))

hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd(ipc .. "volume-up"))
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd(ipc .. "volume-down"))
hl.bind("XF86AudioMute", hl.dsp.exec_cmd(ipc .. "volume-mute"))
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd(ipc .. "brightness-up"))
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(ipc .. "brightness-down"))

-- 5. Window Rules
hl.window_rule({
  match = { class = "dev.noctalia.Noctalia" },
  float = true,
  size = { 1080, 920 },
})

-- 6. Layer Blur Rules (Disable Hyprland's layer animation to use Noctalia's native animation)
hl.layer_rule({
  name = "noctalia",
  match = {
    namespace = "^noctalia-(bar-.+|notification|dock|panel|attached-panel|osd|window-switcher)$",
  },
  no_anim = true,
  ignore_alpha = 0.5,
  blur = true,
  blur_popups = true,
})
```

---

### 4.3 Sway / Scroll (`~/.config/sway/config`)

```bash
# 1. Autostart
exec noctalia

# 2. IPC Binds
set $ipc noctalia msg

bindsym $mod+space exec $ipc panel-toggle launcher
bindsym $mod+s exec $ipc panel-toggle control-center
bindsym $mod+comma exec $ipc settings-toggle

bindsym --locked XF86AudioRaiseVolume exec $ipc volume-up
bindsym --locked XF86AudioLowerVolume exec $ipc volume-down
bindsym --locked XF86AudioMute exec $ipc volume-mute
bindsym --locked XF86MonBrightnessUp exec $ipc brightness-up
bindsym --locked XF86MonBrightnessDown exec $ipc brightness-down
```

---

### 4.4 Mango (`~/.config/mango/config.conf`)

```ini
# 1. Autostart
exec-once=noctalia

# 2. Blur and Shadow Tuning (disable layer blur and layer shadows in Mango, rely on Noctalia's drop shadows)
blur=1
blur_layer=0
blur_optimized=1
blur_params_num_passes=2
blur_params_radius=5
blur_params_noise=0.02
blur_params_brightness=0.9
blur_params_contrast=0.9
blur_params_saturation=1.0
layer_animations=0

shadows=1
layer_shadows=0
shadow_only_floating=0
shadows_size=4
shadows_blur=12
shadows_position_x=2
shadows_position_y=2
shadowscolor=0x000000ff

# 3. Keybinds
bind=SUPER,space,spawn,noctalia msg panel-toggle launcher
bind=SUPER,s,spawn,noctalia msg panel-toggle control-center
bind=SUPER,comma,spawn,noctalia msg settings-toggle

bind=NONE,XF86AudioRaiseVolume,spawn,noctalia msg volume-up
bind=NONE,XF86AudioLowerVolume,spawn,noctalia msg volume-down
bind=NONE,XF86AudioMute,spawn,noctalia msg volume-mute
bind=NONE,XF86MonBrightnessUp,spawn,noctalia msg brightness-up
bind=NONE,XF86MonBrightnessDown,spawn,noctalia msg brightness-down
```

---

### 4.5 Labwc (`~/.config/labwc/`)

- **Autostart** (`~/.config/labwc/autostart`):
  ```bash
  noctalia
  ```

- **Configuration & Keybinds** (`~/.config/labwc/rc.xml`):
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <labwc_config>
    <core>
      <gap>10</gap>
    </core>
    <windowSwitcher preview="no" outlines="yes">
      <osd style="thumbnail"/>
    </windowSwitcher>

    <keyboard>
      <default />
      <keybind key="W-space"><action name="Execute"><command>noctalia msg panel-toggle launcher</command></action></keybind>
      <keybind key="W-s"><action name="Execute"><command>noctalia msg panel-toggle control-center</command></action></keybind>
      <keybind key="W-,"><action name="Execute"><command>noctalia msg settings-toggle</command></action></keybind>

      <keybind key="XF86AudioRaiseVolume"><action name="Execute"><command>noctalia msg volume-up</command></action></keybind>
      <keybind key="XF86AudioLowerVolume"><action name="Execute"><command>noctalia msg volume-down</command></action></keybind>
      <keybind key="XF86AudioMute"><action name="Execute"><command>noctalia msg volume-mute</command></action></keybind>
      <keybind key="XF86MonBrightnessUp"><action name="Execute"><command>noctalia msg brightness-up</command></action></keybind>
      <keybind key="XF86MonBrightnessDown"><action name="Execute"><command>noctalia msg brightness-down</command></action></keybind>
    </keyboard>
  </labwc_config>
  ```

- **DPMS Idle Support via wlopm**:
  ```toml
  # In ~/.config/noctalia/config.toml:
  [idle.behavior.screen-off]
  timeout = 600
  command = "wlopm --off DP-1"
  resume_command = "wlopm --on DP-1"
  ```

---

### 4.6 KDE Plasma (KWin) Limitations & Status

Noctalia can run on KDE Plasma as a layer-shell UI, but KWin lacks many standard wlroots protocols:

| Feature | Plasma / KWin Status | Notes |
|---------|---------------------|-------|
| Bars, Panels, Dock, Launcher, CC | ✅ Supported | Standard Layer Shell |
| System Tray | ✅ Supported | Plasma StatusNotifier implementation |
| Workspaces | ✅ Supported | `org_kde_plasma_virtual_desktop` protocol |
| Taskbar / Dock Window Tracking | ⚠️ Degraded | Uses injected KWin D-Bus script instead of foreign-toplevel protocol |
| Clipboard History & Auto-Paste | ❌ Unavailable | KWin lacks `ext-data-control` & `zwp_virtual_keyboard_v1` |
| Noctalia Screenshots | ❌ Unavailable | KWin lacks `zwlr-screencopy-unstable-v1` |
| Live Lock Screen Blur Background | ❌ Unavailable | Needs screencopy protocol |
| Night Light | ❌ Unavailable | Needs `zwlr-gamma-control-unstable-v1` |
| Screen Time Tracker | ❌ Broken / Incomplete | Relies on foreign-toplevel protocol |
| Keyboard Layout Widget | ❌ No backend | No compositor backend exposed |
| Wallpaper Overview Backdrop | ❌ Unavailable | Niri-only feature |

---

## 5. Troubleshooting & FAQ

1. **Why is hand-written configuration ignored?**
   - Noctalia loads `~/.config/noctalia/*.toml` first, then overrides it with `~/.local/state/noctalia/settings.toml` (written by Settings GUI).
   - If settings conflict, `settings.toml` wins. Inspect or clear `~/.local/state/noctalia/settings.toml`.

2. **How to configure multiple instances of the same widget?**
   - In TOML, define a custom name with an explicit `type`:
     ```toml
     [bar.default]
     end = ["sysmon-cpu", "sysmon-mem"]

     [widget.sysmon-cpu]
     type = "sysmon"
     metric = "cpu"

     [widget.sysmon-mem]
     type = "sysmon"
     metric = "memory"
     ```

3. **How to change the first day of the week in Calendar?**
   - First day of the week is determined directly by the system `LC_TIME` locale, not by a Noctalia configuration setting.

4. **Why is the battery widget missing?**
   - Battery detection relies on `upower`. Ensure the UPower daemon is active (`services.upower.enable = true` on NixOS).

5. **Lockscreen PAM Authentication**:
   - Authenticates using the `/etc/pam.d/login` service file. Ensure PAM modules (e.g. fingerprint, security keys) are configured in `/etc/pam.d/login`.

6. **Lockscreen before Suspend**:
   - Noctalia holds a `logind` sleep delay inhibitor and locks before suspend by default.
   - To disable auto-lock on suspend, set `[lockscreen] lock_before_suspend = false`.

7. **NetworkManager + wpa_supplicant D-Bus permissions**:
   - If NetworkManager cannot talk to wpa_supplicant, add the `wheel` group policy to `/etc/dbus-1/system.d/wpa_supplicant.conf` and ensure wpa_supplicant runs with `-u`.


<!-- ==================== END FILE: 01_GETTING_STARTED_AND_COMPOSITORS.md ==================== -->


---


<!-- ==================== BEGIN FILE: 02_CONFIGURATION_AND_CORE_SHELL.md ==================== -->

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


<!-- ==================== END FILE: 02_CONFIGURATION_AND_CORE_SHELL.md ==================== -->


---


<!-- ==================== BEGIN FILE: 03_BARS_AND_WIDGETS_REFERENCE.md ==================== -->

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


<!-- ==================== END FILE: 03_BARS_AND_WIDGETS_REFERENCE.md ==================== -->


---


<!-- ==================== BEGIN FILE: 04_SURFACES_AND_SERVICES.md ==================== -->

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


<!-- ==================== END FILE: 04_SURFACES_AND_SERVICES.md ==================== -->


---


<!-- ==================== BEGIN FILE: 05_THEMING_PALETTES_AND_TEMPLATES.md ==================== -->

# Noctalia: Theming, Color Palettes & Template Engine

This document provides a comprehensive technical reference for Noctalia's theme engine, 16 core color roles, custom palette JSON schemas, template syntax (`<* *>` and `{{ }}`), color filters, and application theming integration.

---

## 1. Theme Configuration (`[theme]`)

```toml
[theme]
mode              = "dark"        # "dark" | "light" | "auto" (follows solar schedule in [location])
source            = "builtin"     # "builtin" | "wallpaper" | "community" | "custom"
builtin           = "Noctalia"    # Bundled palette name
community_palette = "Oxocarbon"   # Community palette from api.noctalia.dev
custom_palette    = "MyPalette"   # Filename in ~/.config/noctalia/palettes/ (without .json)
wallpaper_scheme  = "m3-content"  # Algorithm when source = "wallpaper"
pure_black_dark   = false         # Replace dark background roles with #000000 (OLED mode)
```

### 1.1 Palette Sources
1. **`builtin`**: Compiled-in presets: `Ayu`, `Catppuccin`, `Dracula`, `Eldritch`, `Gruvbox`, `Kanagawa`, `Noctalia`, `Nord`, `Rosé Pine`, `Tokyo-Night`.
2. **`wallpaper`**: Material 3 / Custom algorithmic palette derived from current wallpaper image.
   - Schemes: `m3-tonal-spot` (default M3), `m3-content` (higher chroma), `m3-fruit-salad`, `m3-rainbow`, `m3-monochrome`, `vibrant`, `faithful`, `soft`, `dysfunctional`, `muted`.
3. **`community`**: Downloaded from `https://api.noctalia.dev/palette/<name>` and cached in `~/.local/state/noctalia/community-palettes/`. Auto-syncs on MD5 hash updates.
4. **`custom`**: Loaded from `~/.config/noctalia/palettes/<name>.json`.

---

## 2. Color Roles & Palette JSON Specification

### 2.1 The 16 Core Color Roles

| Role Name (`snake_case`) | Internal Key | Description |
|--------------------------|--------------|-------------|
| `primary` | `mPrimary` | Primary accent for buttons, highlights, active states |
| `on_primary` | `mOnPrimary` | Text/icons on top of `primary` |
| `secondary` | `mSecondary` | Secondary accent |
| `on_secondary` | `mOnSecondary` | Text/icons on top of `secondary` |
| `tertiary` | `mTertiary` | Tertiary accent |
| `on_tertiary` | `mOnTertiary` | Text/icons on top of `tertiary` |
| `error` | `mError` | Error/destructive action color |
| `on_error` | `mOnError` | Text/icons on top of `error` |
| `surface` | `mSurface` | Main surface/background |
| `on_surface` | `mOnSurface` | Primary text and icons on `surface` |
| `surface_variant` | `mSurfaceVariant` | Secondary surface (cards, capsules, panel tiles) |
| `on_surface_variant` | `mOnSurfaceVariant` | Subdued text/icons on `surface_variant` |
| `outline` | `mOutline` | Borders, dividers, subtle outlines |
| `shadow` | `mShadow` | Drop shadow tint |
| `hover` | `mHover` | Hover/interactive highlight fill |
| `on_hover` | `mOnHover` | Text/icons on hover surfaces |

### 2.2 Custom Palette File Schema (`palettes/<name>.json`)

```json
{
  "dark": {
    "mPrimary": "#a6e22e",
    "mOnPrimary": "#272822",
    "mSecondary": "#66d9ef",
    "mOnSecondary": "#272822",
    "mTertiary": "#f92672",
    "mOnTertiary": "#272822",
    "mError": "#f92672",
    "mOnError": "#272822",
    "mSurface": "#272822",
    "mOnSurface": "#f8f8f2",
    "mSurfaceVariant": "#3e3d32",
    "mOnSurfaceVariant": "#a6e22e",
    "mOutline": "#75715e",
    "mShadow": "#272822",
    "mHover": "#3a3a32",
    "mOnHover": "#f8f8f2",
    "terminal": {
      "background": "#272822",
      "foreground": "#f8f8f2",
      "cursor": "#f8f8f2",
      "cursorText": "#272822",
      "selectionBg": "#f8f8f2",
      "selectionFg": "#272822",
      "normal": {
        "black": "#272822", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#f8f8f2"
      },
      "bright": {
        "black": "#75715e", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#f9f8f5"
      }
    }
  },
  "light": {
    "mPrimary": "#a6e22e",
    "mOnPrimary": "#f8f8f2",
    "mSecondary": "#66d9ef",
    "mOnSecondary": "#f8f8f2",
    "mTertiary": "#f92672",
    "mOnTertiary": "#f8f8f2",
    "mError": "#f92672",
    "mOnError": "#f8f8f2",
    "mSurface": "#f8f8f2",
    "mOnSurface": "#272822",
    "mSurfaceVariant": "#e6e1dc",
    "mOnSurfaceVariant": "#272822",
    "mOutline": "#a6e22e",
    "mShadow": "#d8d8d8",
    "mHover": "#e6e1dc",
    "mOnHover": "#272822",
    "terminal": {
      "background": "#f8f8f2",
      "foreground": "#272822",
      "cursor": "#272822",
      "cursorText": "#f8f8f2",
      "selectionBg": "#272822",
      "selectionFg": "#f8f8f2",
      "normal": {
        "black": "#f8f8f2", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#272822"
      },
      "bright": {
        "black": "#d8d8d2", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#1e1e19"
      }
    }
  }
}
```

---

## 3. Template Engine Specification

The Noctalia `TemplateEngine` generates external application themes (e.g. Foot, Alacritty, GTK, Qt, Neovim, Discord).

### 3.1 Syntax Rules

- **Inline Expressions**: `{{ ... }}`
- **Block Directives**: `<* ... *>` (supports `for`, `endfor`, `if`, `else`, `endif`)
- **Standalone Block Trimming**: Lines containing only a block tag with whitespace are stripped from output.

### 3.2 Token Access Syntax

```text
{{ colors.<name>.<mode>.<format> }}
```
- `<name>`: Any Material 3 role (e.g. `primary`, `surface_container_high`), terminal token (e.g. `terminal_background`, `terminal_normal_red`), or custom color token.
- `<mode>`: `default` (active theme mode), `dark`, or `light`.
- `<format>`: `hex` (`#RRGGBB`), `hex_stripped` (`RRGGBB`), `rgb` (`rgb(r, g, b)`), `rgb_csv` (`r,g,b`), `rgba` (`rgba(r, g, b, a)`), `hsl` (`hsl(h, s%, l%)`), `hsla`, `red`, `green`, `blue`, `alpha`, `hue`, `saturation`, `lightness`.

### 3.3 Built-in Color Tokens
- **Primary**: `primary`, `on_primary`, `primary_container`, `on_primary_container`, `primary_fixed`, `primary_fixed_dim`, `on_primary_fixed`, `on_primary_fixed_variant`
- **Secondary**: `secondary`, `on_secondary`, `secondary_container`, `on_secondary_container`, `secondary_fixed`, `secondary_fixed_dim`, `on_secondary_fixed`, `on_secondary_fixed_variant`
- **Tertiary**: `tertiary`, `on_tertiary`, `tertiary_container`, `on_tertiary_container`, `tertiary_fixed`, `tertiary_fixed_dim`, `on_tertiary_fixed`, `on_tertiary_fixed_variant`
- **Error**: `error`, `on_error`, `error_container`, `on_error_container`
- **Surface**: `surface`, `on_surface`, `surface_variant`, `on_surface_variant`, `surface_dim`, `surface_bright`, `surface_container_lowest`, `surface_container_low`, `surface_container`, `surface_container_high`, `surface_container_highest`
- **Outline & Utility**: `outline`, `outline_variant`, `shadow`, `scrim`
- **Inverse**: `inverse_surface`, `inverse_on_surface`, `inverse_primary`
- **Background**: `background`, `on_background`
- **Terminal Tokens**: `terminal_foreground`, `terminal_background`, `terminal_cursor`, `terminal_cursor_text`, `terminal_selection_fg`, `terminal_selection_bg`, `terminal_normal_black` .. `white`, `terminal_bright_black` .. `white`.

### 3.4 Filters Reference

| Filter | Syntax | Description |
|--------|--------|-------------|
| `grayscale` | `{{ ... \| grayscale }}` | Converts color to grayscale using luminance |
| `invert` | `{{ ... \| invert }}` | Inverts RGB channels |
| `set_alpha` | `{{ ... \| set_alpha 0.5 }}` | Sets alpha (0.0–1.0) |
| `set_lightness` | `{{ ... \| set_lightness 80 }}` | Sets HSL lightness (0–100) |
| `set_hue` | `{{ ... \| set_hue 180 }}` | Sets absolute hue (0–360) |
| `rotate_hue` | `{{ ... \| rotate_hue 30 }}` | Rotates hue relative degrees |
| `set_saturation`| `{{ ... \| set_saturation 50 }}` | Sets HSL saturation (0–100) |
| `lighten` | `{{ ... \| lighten 10 }}` | Adds percentage points to lightness |
| `darken` | `{{ ... \| darken 10 }}` | Subtracts percentage points from lightness |
| `saturate` | `{{ ... \| saturate 10 }}` | Adds percentage points to saturation |
| `desaturate` | `{{ ... \| desaturate 10 }}` | Subtracts percentage points from saturation |
| `auto_lightness`| `{{ ... \| auto_lightness 15 }}`| Lightens dark colors, darkens light colors |
| `blend` | `{{ ... \| blend: "#ff0000", 0.5 }}` | Interpolates toward target color |
| `harmonize` | `{{ ... \| harmonize: "#00ff88" }}`| Nudges hue toward color (max 15°) |
| `to_color` | `{{ "#ffaa00" \| to_color \| darken 10 }}` | Converts string to color for subsequent filters |
| `replace` | `{{ mode \| replace: "dark", "night" }}` | String replacement |
| `snake_case`, `kebab_case`, `camel_case`, `pascal_case`, `lower_case` | `{{ "Foo Bar" \| snake_case }}` | Casing conversions |

### 3.5 Loops & Conditionals

```text
<* for name, value in colors *>
{{ name }} = {{ value.default.hex }}
<* endfor *>

<* if {{ loop.first }} *>
# Header
<* else *>
# Item
<* endif *>

# Tonal palettes direct access & iteration:
{{ palettes.primary.40.hex }}
<* for tone in palettes.secondary *>
{{ tone.default }}
<* endfor *>

# Numeric ranges:
<* for i in 0..16 *>
color{{ i }} = ...
<* endfor *>
```

---

## 4. App Theming Configuration (`[theme.templates]`)

```toml
[theme.templates]
enable_builtin_templates   = true
builtin_ids                = ["gtk3", "gtk4", "qt", "kcolor_scheme", "foot", "alacritty", "umbriel"]
enable_community_templates = true
community_ids              = ["discord", "neovim", "obsidian"]

# Custom Colors Definitions:
[theme.templates.custom_colors.warning]
color       = "#f97316"
color_dark  = "#f97316"
color_light = "#c2410c"
blend       = true       # Harmonize with active palette

# User-Defined Custom Template:
[theme.templates.user.my_app]
input_path           = "$XDG_CONFIG_HOME/noctalia/templates/my-app.css"
output_path          = "$XDG_CONFIG_HOME/my-app/theme.css"
output_path_dynamic  = ""                       # Optional shell command yielding extra paths
input_path_modes     = { dark = "./d.css", light = "./l.css" }
pre_hook             = ""                       # Shell command before writing
post_hook            = "pkill -USR1 my-app"     # Shell command after writing
post_action          = ""                       # "kde-color-scheme"
requires_path        = ""                       # Skip template if path does not exist
enabled              = true
```

### 4.1 CLI Tools for Theming

```sh
# Render a single template file:
noctalia theme ~/Pictures/wall.png -r template.in:output.out

# Process a template config:
noctalia theme ~/Pictures/wall.png -c templates.toml

# List all available built-in, community, and user templates:
noctalia theme --list-templates

# Process shipped built-in templates:
noctalia theme ~/Pictures/wall.png --builtin-config
```


<!-- ==================== END FILE: 05_THEMING_PALETTES_AND_TEMPLATES.md ==================== -->


---


<!-- ==================== BEGIN FILE: 06_IPC_COMMANDS_AND_CLI.md ==================== -->

# Noctalia: IPC Commands & CLI Reference

This document provides a comprehensive technical reference for Noctalia's Inter-Process Communication (IPC) system. All commands are executed via `noctalia msg <command>` from terminals, compositor keybinds, scripts, or hooks.

---

## 1. Shell, Session & Settings Commands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `status` | *(none)* | Print basic shell runtime state as JSON. |
| `log-level-status` | *(none)* | Print current console log level (`debug`, `info`, `warn`, `error`). |
| `log-level-set` | `<debug\|info\|warn\|error>` | Set the console log level dynamically for the running session. |
| `config-reload` | *(none)* | Hot-reload the merged Noctalia config stack immediately. |
| `settings-open` | `[context]` | Open/focus settings window (optional section: e.g. `bar`, `dock`). |
| `settings-open-plugin` | `<author/plugin>` | Open settings window directly at a specific plugin. |
| `settings-close` | *(none)* | Close settings window. |
| `settings-toggle` | `[context]` | Toggle settings window on/off. |
| `window-switcher` | *(none)* | Open Alt+Tab window switcher overlay on preferred monitor. |
| `window-switcher close` | *(none)* | Dismiss window switcher overlay (`hide` is an alias). |
| `session lock` | *(none)* | Lock the current Wayland session. |
| `session suspend` | *(none)* | Suspend the system without locking first. |
| `session lock-and-suspend` | *(none)* | Lock session, then suspend immediately once locked. |
| `session logout` | *(none)* | End the graphical session (compositor-native). |
| `session reboot` | *(none)* | Reboot the machine. |
| `session shutdown` | *(none)* | Power off the machine. |

---

## 2. Surfaces, Bars & Panels Commands

### 2.1 Bar Management
| Command | Arguments | Description |
|---------|-----------|-------------|
| `bar-show` | `[bar-name] [monitor]` | Reveal matching bar instances. Omit args to reveal all. |
| `bar-hide` | `[bar-name] [monitor]` | Hide matching bar and block edge reveal until next show. |
| `bar-toggle` | `[bar-name] [monitor]` | Toggle visibility of matching bar instances. |
| `bar-reserve-toggle` | `[bar-name] [monitor]` | Toggle compositor exclusive zone reservation. |
| `bar-auto-hide-set` | `<on\|off\|smart> [bar] [mon]` | Switch auto-hide mode temporarily at runtime. |
| `bar-layer-set` | `<top\|overlay> [bar] [mon]` | Move bar to `top` or `overlay` layer (above fullscreen). |

### 2.2 Panels
| Command | Arguments | Description |
|---------|-----------|-------------|
| `panel-open` | `<id> [context]` | Open panel without toggling if already open. |
| `panel-close` | `[id]` | Close active panel or named panel. |
| `panel-toggle launcher` | `[query]` | Toggle App Launcher (optional search pre-fill, e.g. `"/wall"`). |
| `panel-toggle session` | *(none)* | Toggle Session power menu. |
| `panel-toggle clipboard` | *(none)* | Toggle Clipboard history panel. |
| `panel-toggle wallpaper` | *(none)* | Toggle Wallpaper picker panel. |
| `panel-toggle control-center` | `[tab]` | Toggle Control Center (optional tab context: `media`, `audio`, etc.). |
| `panel-toggle <author/plugin:entry>` | `[context]` | Toggle plugin-defined panel entry. |

### 2.3 Dock
| Command | Description |
|---------|-------------|
| `dock-show` | Reveal dock on all outputs and save state. |
| `dock-hide` | Hide dock on all outputs and save state. |
| `dock-toggle` | Toggle dock visibility on all outputs. |
| `dock-reload` | Reload dock configuration and pinned lists. |

### 2.4 Desktop & Lockscreen Widgets
| Command | Description |
|---------|-------------|
| `desktop-widgets-edit` | Enter interactive desktop widget layout editor. |
| `desktop-widgets-exit` | Exit desktop widget layout editor. |
| `desktop-widgets-toggle-edit` | Toggle desktop widget editor mode. |
| `desktop-widgets-show` | Temporarily show desktop widgets (runtime override). |
| `desktop-widgets-hide` | Temporarily hide and destroy desktop widgets. |
| `desktop-widgets-toggle` | Toggle desktop widgets visibility. |
| `lockscreen-widgets-edit` | Enter interactive lockscreen widget editor (unlocked session). |
| `lockscreen-widgets-exit` | Exit lockscreen widget editor. |
| `lockscreen-widgets-toggle-edit`| Toggle lockscreen widget editor mode. |

---

## 3. Media, UI, Notifications & Theming Commands

### 3.1 Notifications
| Command | Arguments | Description |
|---------|-----------|-------------|
| `notification-dnd-set` | `<on\|off>` | Set Do Not Disturb mode. |
| `notification-dnd-toggle`| *(none)* | Toggle Do Not Disturb mode. |
| `notification-dnd-status`| *(none)* | Print current DND status (`on` / `off`). |
| `notification-show` | `<summary> [body]` | Send internal toast notification. |
| `notification-show` | `'<json-payload>'` | Send rich notification (`app_name`, `summary`, `body`, `urgency`, `timeout_ms`, `icon`, etc.). |
| `notification-invoke-latest`| *(none)* | Activate default action of most recent notification toast. |
| `notification-clear-active` | *(none)* | Dismiss all visible on-screen toasts. |
| `notification-clear-history`| *(none)* | Delete all notification history entries in Control Center. |

### 3.2 Clipboard
| Command | Arguments | Description |
|---------|-----------|-------------|
| `clipboard-clear` | *(none)* | Clear clipboard history (pinned items survive). |
| `clipboard-copy` | `<text>` | Copy text into system clipboard (max 64 KiB). |
| `clipboard-text` | *(none)* | Output latest clipboard text item to stdout. |

### 3.3 Media (MPRIS)
| Command | Description |
|---------|-------------|
| `media previous` | Previous track on active player. |
| `media next` | Next track on active player. |
| `media toggle` | Toggle play/pause on active player. |
| `media play` | Resume playback on active player. |
| `media pause` | Pause active player. |
| `media stop` | Stop active player and dismiss from widget. |
| `media previous-player` | Cycle active MPRIS player backward. |
| `media next-player` | Cycle active MPRIS player forward. |

### 3.4 Wallpaper
| Command | Arguments | Description |
|---------|-----------|-------------|
| `wallpaper-random` | `[connector]` | Pick random wallpaper (all monitors or specified output). |
| `wallpaper-next` | `[connector]` | Advance to next wallpaper in directory order. |
| `wallpaper-previous` | `[connector]` | Go back to previous wallpaper in directory order. |
| `wallpaper-get` | `[connector]` | Print active wallpaper path (default or specific output). |
| `wallpaper-set` | `[connector] <path>` | Set wallpaper image or `color:#HEX` (all or specific output). |

### 3.5 Theming
| Command | Arguments | Description |
|---------|-----------|-------------|
| `theme-mode-get` | *(none)* | Print resolved mode (`dark` or `light`). |
| `theme-mode-toggle` | *(none)* | Toggle dark/light theme mode. |
| `theme-mode-set` | `<dark\|light\|auto>` | Persist and set theme mode. |
| `color-scheme-get` | *(none)* | Print active source and palette name. |
| `color-scheme-set` | `<source> <name>` | Set palette (e.g. `builtin Noctalia`, `wallpaper m3-content`). |
| `templates-apply` | *(none)* | Force re-render of all configured theme templates. |

### 3.6 Screenshots (`wlr-screencopy`)
| Command | Arguments | Description |
|---------|-----------|-------------|
| `screenshot-region` | *(none)* | Interactive region capture. |
| `screenshot-fullscreen` | *(none)* | Capture focused monitor. |
| `screenshot-fullscreen` | `pick` | Display picker (multi-monitor) or immediate capture. |
| `screenshot-fullscreen` | `<connector>` | Capture specific output (e.g. `DP-1`, `HDMI-A-1`). |
| `screenshot-fullscreen` | `all` | Capture entire virtual desktop across all monitors into 1 image. |

---

## 4. System Controls & Hardware IPC

### 4.1 Volume & Microphone
| Command | Arguments | Description |
|---------|-----------|-------------|
| `volume-set` | `<val>` | Set output volume (`65`, `65%`, `0.65`). Clamped to 100% (150% with overdrive). |
| `volume-up` | `[step]` | Raise output volume (default 5%, or custom e.g. `10`). |
| `volume-down` | `[step]` | Lower output volume (default 5%). |
| `volume-mute` | *(none)* | Toggle output mute. |
| `volume-osd` | `[val]` | Show volume OSD (at current level or custom value). |
| `mic-volume-set` | `<val>` | Set microphone input volume (`0.5`, `50%`). |
| `mic-volume-up` | `[step]` | Raise microphone volume. |
| `mic-volume-down` | `[step]` | Lower microphone volume. |
| `mic-mute` | *(none)* | Toggle microphone mute. |
| `mic-volume-osd` | `[val]` | Show microphone OSD. |

### 4.2 Brightness & Night Light
| Command | Arguments | Description |
|---------|-----------|-------------|
| `brightness-set` | `[target] <val>` | Set brightness (`brightness-set 65`, `brightness-set DP-1 0.65`, `brightness-set * 40%`). |
| `brightness-up` | `[target] [step]`| Raise brightness (default monitor or specific output). |
| `brightness-down` | `[target] [step]`| Lower brightness. |
| `brightness-osd` | `<val>` | Show brightness OSD at value. |
| `brightness-list-backlight-devices` | *(none)* | List available kernel sysfs backlight devices. |
| `nightlight-enable` | *(none)* | Enable scheduled night light. |
| `nightlight-disable`| *(none)* | Disable scheduled night light. |
| `nightlight-toggle` | *(none)* | Toggle scheduled night light. |
| `nightlight-force-toggle` | *(none)* | Force night temperature on/off (overriding schedule). |

### 4.3 Wireless, Caffeine & Power
| Command | Arguments | Description |
|---------|-----------|-------------|
| `wifi-enable` / `wifi-disable` / `wifi-toggle` | *(none)* | Control NetworkManager Wi-Fi radio. |
| `wifi-status` | *(none)* | Print `on` or `off`. |
| `bluetooth-enable` / `bluetooth-disable` / `bluetooth-toggle` | *(none)* | Control Bluetooth adapter. |
| `bluetooth-status` | *(none)* | Print `on` or `off`. |
| `caffeine-enable` / `caffeine-disable` / `caffeine-toggle` | *(none)* | Control Wayland idle inhibitor. |
| `power-set` | `<profile>` | Activate named UPower power profile (`performance`, `balanced`, `power-saver`). |
| `power-cycle` | *(none)* | Cycle to next available power profile. |
| `dpms-on` / `dpms-off` | *(none)* | Power on/off connected monitors. |
| `osd-enable` / `osd-disable` / `osd-toggle` | *(none)* | Runtime control for OSD overlay popups. |

---

## 5. Plugin IPC & Plugin Management

### 5.1 Dispatching Events to Plugins
```sh
noctalia msg plugin <author/plugin:entry> <target[:bar-name]> <event> [payload]
```
- `<target>`: `focused`, `all` (required for singletons like services/panels), `<connector>` (e.g. `DP-1`), or bar-qualified (e.g. `focused:default`, `DP-1:top`).
- Dispatches event to the Lua/Luau `onIpc(event, payload)` callback.

```sh
# Examples:
noctalia msg plugin noctalia/screen_recorder:service all toggle
noctalia msg plugin noctalia/screen_recorder:service all start focused
noctalia msg plugin noctalia/example:hello focused set "New text"
```

### 5.2 Plugin CLI Management
| Command | Description |
|---------|-------------|
| `plugins list` | List all discovered plugins and their enabled status. |
| `plugins enable <author/plugin>` | Enable a plugin. |
| `plugins disable <author/plugin>`| Disable a plugin. |
| `plugins update <source>` | Update plugin repository (e.g. `official`). |
| `plugins source list` | List configured plugin repository sources. |
| `plugins source add <name> <git\|path> <url\|dir>` | Add a git or local directory plugin source. |
| `plugins source remove <name>` | Remove a plugin repository source. |


<!-- ==================== END FILE: 06_IPC_COMMANDS_AND_CLI.md ==================== -->


---


<!-- ==================== BEGIN FILE: 07_PLUGIN_DEVELOPMENT_AND_LUAU_API.md ==================== -->

# Noctalia: Plugin Development & Luau API Reference

This document provides a comprehensive technical reference for developing plugins for Noctalia v5+. Plugins in Noctalia run as isolated Luau VMs communicating with the C++ host through declarative UI trees and the `noctalia.*` runtime API.

---

## 1. Plugin API Version Ledger (Levels 3 to 28)

Every plugin **must** declare `plugin_api = N` in `plugin.toml`.

| Level | Introduced In | Feature Key | Capability Description |
|---|---|---|---|
| **3** | `v5.0.0-beta.3` | `api-declaration` | Mandatory `plugin_api` compatibility declaration (replaces legacy `min_noctalia`). |
| **4** | `v5.0.0-beta.4` | `http-stream` | `noctalia.httpStream()` for streaming HTTP responses (e.g. SSE). |
| **5** | `v5.0.0-beta.4` | `drag-and-drop` | `ui.dragSource()` and `ui.dropZone()` for declarative panel drag and drop. |
| **6** | `v5.0.0-beta.4` | `string-map-setting` | The `string_map` plugin setting type in manifests. |
| **7** | `v5.0.0-beta.4` | `allow-insecure-tls` | `allow_insecure_tls` HTTP request option. |
| **8** | `v5.0.0-beta.4` | `dismiss-on-outside-click` | `dismiss_on_outside_click` panel entry option. |
| **9** | `v5.0.0-beta.5` | `ui-callback-closures` | Luau closures directly in UI tree callback props (e.g. `onClick = function() ... end`). |
| **10** | `v5.0.0-beta.5` | `keyboard-focus` | `keyboard_focus = "on_demand"|"exclusive"|"none"` on panel entries. |
| **11** | `v5.0.0-beta.5` | `persistent-panel` | `persistent = true` panel entry option (stays open alongside other panels). |
| **12** | `v5.0.0-beta.5` | `system-stats` | `noctalia.systemStats()`, `noctalia.cpuCores()`, and `noctalia.nowMs()`. |
| **13** | `v5.0.0-beta.5` | `panel-capture-keys` | `capture_keys` panel manifest option and `onKey(chord, pressed)` callback. |
| **14** | `v5.0.0-beta.5` | `widget-gesture-actions` | `[widget.actions]` table in manifest for default gesture bindings. |
| **15** | `v5.0.0-beta.6` | `open-settings` | `noctalia.openSettings()` opens settings directly at the calling plugin. |
| **16** | `v5.0.0-beta.6` | `extended-system-stats`| Per-interface network rates, sample timestamps, and `noctalia.diskMounts()`/`diskStats()`. |
| **17** | `v5.0.0-beta.7` | `service-lifecycle` | `onEnable()` hook and `onExit(signal, reason)` where reason is `"reload"|"disable"|"uninstall"|"shutdown"`. |
| **18** | `v5.0.0-beta.7` | `panel-frame-tick` | `panel.setNeedsFrameTick(bool)` delivering `onFrameTick(deltaMs)` to open panels. |
| **19** | `v5.0.0-beta.7` | `format-time-timezone` | IANA timezone support in `noctalia.formatTime`, `noctalia.isValidTimezone()`, and `timeFormat()`/`dateFormat()`. |
| **20** | `v5.0.0-beta.7` | `sound` | `noctalia.sound.load()` and `noctalia.sound.play()` for plugin UI audio. |
| **21** | `v5.0.0-beta.8` | `plugin-ui-props` | `ui.markdown`, `submitOnEnter` on `ui.input`, `stickToBottom`/`onScroll`/`scrollToBottomRev` on `ui.scroll`. |
| **22** | `v5.0.0-beta.8` | `module-require` | `require("./path.luau")` loads relative Luau modules with entry-local cache and hot-reload. |
| **23** | `v5.0.0-beta.8` | `async-file-read` | `noctalia.readFileAsync(path, callback)` for bounded non-blocking reads. |
| **24** | `v5.0.0-beta.9` | `direct-argv` | Argument-array form of `noctalia.runAsync({ "cmd", "arg1" }, cb)` avoiding shell parsing. |
| **25** | `v5.0.0-beta.9` | `wallpaper-mask` | `noctalia.wallpaperPath(connector)` and `noctalia.setWallpaperMask(connector, mask)`. |
| **26** | `v5.0.0-beta.9` | `get-setting` | `noctalia.getSetting(path)` reading effective shell config by TOML dotted path. |
| **27** | `v5.0.0-beta.9` | `input-frame-visibility`| `frameVisible` on `ui.input` for frameless inline text inputs. |
| **28** | `v5.0.0-beta.9` | `panel-context-menu` | `panel.openContextMenu(request)` for native popup context menus. |

---

## 2. Plugin Manifest (`plugin.toml`) & Schema

```toml
id          = "author/my_plugin" # Globally unique ID
name        = "My Plugin"
version     = "1.0.0"            # Semantic MAJOR.MINOR.PATCH
plugin_api  = 28                 # Oldest API level required
author      = "Author Name"
license     = "MIT"
description = "Plugin description."
icon        = "puzzle"           # Tabler glyph
tags        = ["utility"]
dependencies= ["curl"]           # External CLI tools (informational)

# Plugin-level Shared Settings (editable in Settings -> Plugins):
[[setting]]
key             = "refresh_rate"
type            = "int"          # string | string_list | string_map | bool | int | double | select | file | folder | glyph | color
label_key       = "settings.refresh_rate.label" # Translation key in translations/en.json
description_key = "settings.refresh_rate.desc"
default         = 10
min             = 1
max             = 60

# 1. Bar Widget Entry:
[[widget]]
id    = "main_bar_widget"
entry = "widget.luau"

  [widget.actions]
  right = "panel-toggle author/my_plugin:main_panel"

  [[widget.setting]]
  key       = "show_icon"
  type      = "bool"
  label_key = "settings.show_icon.label"
  default   = true

# 2. Control Center Shortcut Entry:
[[shortcut]]
id    = "cc_toggle"
entry = "shortcut.luau"

# 3. Launcher Provider Entry:
[[launcher_provider]]
id                        = "search_provider"
entry                     = "launcher.luau"
prefix                    = "my" # Triggers as /my <query>
glyph                     = "search"
include_in_global_search  = false
debounce_ms               = 150

# 4. Desktop Widget Entry:
[[desktop_widget]]
id    = "desk_widget"
entry = "desktop.luau"

# 5. Pop-up Panel Entry:
[[panel]]
id                       = "main_panel"
entry                    = "panel.luau"
width                    = 400            # px or "fill"
height                   = 300            # px or "fill"
placement                = "floating"     # "attached" | "floating"
position                 = "center"       # "auto" | "center" | "top_right" etc.
open_near_click          = false
dismiss_on_outside_click = true
keyboard_focus           = "on_demand"    # "on_demand" | "exclusive" | "none"
persistent               = false          # Survives other panels opening
capture_keys             = ["space", "ctrl+r"]

# 6. Headless Service Entry:
[[service]]
id    = "bg_service"
entry = "service.luau"
```

---

## 3. Entry Lifecycle & Global Callbacks

| Global Callback | Applicable Entry Types | When Triggered |
|---|---|---|
| `update()` | Widget, Desktop, Panel, Service | Every `noctalia.setUpdateInterval(ms)` |
| `onClick()` / `onRightClick()` | Widget, Shortcut | Pointer clicks (unless overridden by `actions`) |
| `onMiddleClick()` | Widget | Middle click (unless overridden) |
| `onScroll(axis, steps, startsGesture)` | Widget | Wheel / touchpad scroll (`axis="vertical"\|"horizontal"`) |
| `onQuery(text)` | Launcher Provider | User input behind the prefix |
| `onActivate(id)` | Launcher Provider | User selects a result item |
| `onOpen(context)` / `onClose()` | Panel | Panel opened / closed |
| `onKey(chord, pressed)` | Panel | Key declared in `capture_keys` pressed (`pressed=true/false`) |
| `onFrameTick(deltaMs)` | Desktop Widget, Panel | Every rendered frame when `setNeedsFrameTick(true)` |
| `onIpc(event, payload)` | All Entries | `noctalia msg plugin <id> <target> <event> [payload]` |
| `onConfigChanged()` | Service | Plugin setting was edited (avoids full VM restart) |
| `onEnable()` | Service | Plugin explicitly enabled in plugin manager |
| `onOutputsChanged()` | Service | Connected monitors or display geometries changed |
| `onExit(signal, reason)` | All Entries | VM about to be destroyed (`reason="reload"\|"disable"\|"uninstall"\|"shutdown"`) |

---

## 4. `noctalia.*` Host Runtime API

### 4.1 System, Time & Configuration
- `noctalia.setUpdateInterval(ms: number)`: Set timer cadence for `update()`.
- `noctalia.log(msg: string)`: Write to Noctalia log with plugin prefix.
- `noctalia.isDarkMode(): boolean`: True if active theme is dark.
- `noctalia.getConfig(key: string): any`: Read declared setting for calling entry.
- `noctalia.getSetting(path: string): any`: Read effective shell configuration (e.g. `"bar.default.position"`).
- `noctalia.focusedOutputName(): string?`: Connector name of focused output.
- `noctalia.nowMs(): number`: Unix epoch wall-clock milliseconds.
- `noctalia.formatTime(fmt: string, unixSec?: number, tz?: string): string`: Format time using Noctalia tokens.
- `noctalia.notify(title: string, body?: string)`: Show info notification toast.
- `noctalia.notifyError(title: string, body?: string)`: Show error notification toast.
- `noctalia.copyToClipboard(text: string, mime?: string): boolean`: Copy to clipboard.
- `noctalia.clipboardText(): string?`: Get active clipboard text.
- `noctalia.openSettings()`: Open settings window at calling plugin.

### 4.2 System Monitor & Hardware Stats
- `noctalia.systemStats(): table?`: Returns snapshot table:
  - `cpu.usagePercent`, `cpu.tempC`, `cpu.freqMhz`, `cpu.maxFreqMhz`
  - `ram.usagePercent`, `ram.usedMb`, `ram.totalMb`
  - `swap.usedMb`, `swap.totalMb`
  - `gpu.tempC`, `gpu.usagePercent`, `gpu.vramUsedBytes`, `gpu.vramTotalBytes`
  - `net.rxBytesPerSec`, `net.txBytesPerSec`, `net.interfaces`
  - `loadAvg` (`[1, 5, 15]`)
- `noctalia.cpuCores(): number[]?`: Per-core usage percentage array.
- `noctalia.diskMounts(): { path: string, source: string, filesystem: string }[]`: Block storage mounts.
- `noctalia.diskStats(path: string): { usagePercent: number, totalBytes: number, freeBytes: number, availableBytes: number }?`

### 4.3 Subprocesses & Filesystem
- `noctalia.runAsync(cmdOrArgv: string | string[], cb?: (res: { exitCode: number, stdout: string, stderr: string }) -> ())`: Run process.
- `noctalia.runStream(cmd: string, onLine: (line: string) -> ())`: Long-lived streaming process stdout.
- `noctalia.runInTerminal(cmd: string)`: Run command inside user's preferred terminal emulator.
- `noctalia.commandExists(name: string): boolean`: Check if binary exists on `$PATH`.
- `noctalia.readFile(path: string): string?, string?`: Synchronous file read.
- `noctalia.readFileAsync(path: string, cb: (content: string?, err: string?) -> ())`: Asynchronous non-blocking file read.
- `noctalia.writeFile(path: string, content: string): boolean, string?`: Write file.
- `noctalia.mkdirAll(path: string): boolean, string?`: Create directory recursively.
- `noctalia.pluginDir(): string`: Directory containing plugin files.
- `noctalia.pluginDataDir(): string`: Persistent user state directory (`~/.local/state/noctalia/plugins/<id>`).
- `noctalia.loadFont(path: string): string?, string?`: Register custom font and return its family name.

### 4.4 Networking & Audio
- `noctalia.http(req: { url: string, method?: string, body?: string, headers?: string[], allow_insecure_tls?: boolean }, cb: (res: { ok: boolean, status: number, body: string }) -> ())`: Async HTTP.
- `noctalia.httpStream(req: table, onLine: (line: string) -> (), onClose: (res: { ok: boolean, status: number }) -> ()): { stop: () -> () }?`: SSE/Stream.
- `noctalia.download(url: string, dest: string, cb: (ok: boolean) -> ())`: Download file.
- `noctalia.sound.load(name: string, path: string, onLoaded: (ok: boolean, err?: string) -> ())`: Load sound effect.
- `noctalia.sound.play(name: string)`: Play loaded sound.

### 4.5 State Sharing & Utility
- `noctalia.state.set(key: string, value: any)`: Publish data across entries in this plugin.
- `noctalia.state.get(key: string): any`: Read shared plugin state.
- `noctalia.state.watch(key: string, fn: (val: any) -> ())`: Subscribe to state changes.
- `noctalia.json.encode(val: any, pretty?: boolean): string?` / `noctalia.json.decode(str: string): any?`
- `noctalia.tr(key: string, subst?: table): string` / `noctalia.trp(key: string, count: number, subst?: table): string`
- `noctalia.fuzzyScore(pattern: string, text: string): number?`

---

## 5. Declarative UI System (`ui.*`)

Desktop widgets (`desktopWidget.render(tree)`), Panels (`panel.render(tree)`), and Bar Widgets (`barWidget.render(tree)`) build UI using `ui.*` components.

### 5.1 Component Constructors & Props

| Component | Props |
|---|---|
| `ui.column` / `ui.row` | `gap`, `padding`, `paddingH`, `paddingV`, `align` (`"start"\|"center"\|"end"\|"stretch"`), `justify` (`"start"\|"center"\|"end"\|"space_between"`), `fill` (color), `radius`, `border`, `borderWidth`, `minWidth`, `minHeight`, `onClick`, `onHover` |
| `ui.scroll` | Column props plus `stickToBottom` (bool), `onScroll` (cb), `scrollToBottomRev` (number) |
| `ui.label` | `text`, `fontSize`, `color`, `fontWeight` (`"thin"`..`"heavy"`), `fontFamily`, `baseline` (`"text"\|"textFixedHeight"\|"inkCentered"\|"pictographic"`), `maxWidth`, `maxLines`, `textAlign` |
| `ui.glyph` | `name` (Tabler/Nerd glyph name), `size`, `color` |
| `ui.image` | `path`, `width`, `height`, `radius`, `fit` (`"contain"\|"cover"\|"stretch"`), `border`, `borderWidth`, `onClick`, `onHover` |
| `ui.box` | `fill`, `radius`, `border`, `borderWidth`, `width`, `height`, `onClick`, `onHover` |
| `ui.separator` | `thickness`, `color`, `spacing`, `orientation` (`"auto"\|"horizontal"\|"vertical"`) |
| `ui.spacer` | `flexGrow` (expands to fill available lane space) |
| `ui.progress` | `progress` (0.0–1.0), `fill`, `track`, `radius`, `width`, `height` |
| `ui.button` | `text`, `glyph`, `fontSize`, `glyphSize`, `variant` (`"default"\|"primary"\|"secondary"\|"destructive"\|"outline"\|"ghost"`), `controlSize` (`"sm"\|"md"\|"lg"`), `tooltip`, `enabled`, `selected`, `onClick`, `onRightClick`, `onHover` |
| `ui.graph` | `values`, `values2` (0.0–1.0 arrays), `color`, `color2`, `lineWidth`, `fillOpacity`, `width`, `height` |
| `ui.toggle` | `checked` (bool), `enabled`, `onChange` (cb receiving `"true"`/`"false"`) |
| `ui.slider` | `min`, `max`, `step`, `value`, `controlSize`, `enabled`, `onChange`, `onDragEnd` |
| `ui.select` | `options` (string[]), `selectedIndex`, `placeholder`, `controlSize`, `enabled`, `onChange` |
| `ui.input` | `value` (initial), `placeholder`, `password` (bool), `multiline` (bool), `submitOnEnter` (bool), `frameVisible` (bool), `focus` (bool), `enabled`, `onChange`, `onSubmit` |
| `ui.markdown` | `text` (markdown string), `width`, `height` |
| `ui.dragSource` | `dragType`, `payload`, `previewAncestor`, `liftFromLayout`, `enabled`, `tooltip` |
| `ui.dropZone` | `accepts` (string[]), `value`, `onDrop` (cb), `direction`, `expandOnDrag`, `hitSlop` |

### 5.2 Common Props on All Controls
- `width`, `height`, `flexGrow` (number)
- `opacity` (number 0.0–1.0)
- `visible` (boolean)
- `key` (reconciliation identity key for preserved list items)


<!-- ==================== END FILE: 07_PLUGIN_DEVELOPMENT_AND_LUAU_API.md ==================== -->


---


<!-- ==================== BEGIN FILE: 08_NOCTALIA_GREETER.md ==================== -->

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


<!-- ==================== END FILE: 08_NOCTALIA_GREETER.md ==================== -->


---


<!-- ==================== BEGIN FILE: 09_UMBRIEL_COMPOSITOR.md ==================== -->

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


<!-- ==================== END FILE: 09_UMBRIEL_COMPOSITOR.md ==================== -->


---

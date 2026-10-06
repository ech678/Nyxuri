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

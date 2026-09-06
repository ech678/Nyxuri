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

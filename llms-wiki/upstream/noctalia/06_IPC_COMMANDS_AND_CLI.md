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

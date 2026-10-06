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

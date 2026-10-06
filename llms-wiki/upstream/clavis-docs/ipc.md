# IPC

Shell 生命周期可使用 `key-cli`；新增快捷键直接调用 Quickshell IPC：

```bash
key shell
qs -c clavis ipc show
qs -c clavis ipc call TARGET METHOD [ARGUMENTS...]
```

对应的 Quickshell 调用为：

```text
key shell                 → qs -c clavis -n
key shell --daemon        → qs -c clavis -n -d
key shell --kill          → qs -c clavis kill
key shell --log           → qs -c clavis log
key ipc show              → qs -c clavis ipc show
key ipc call A B ...      → qs -c clavis ipc call A B ...
```

Niri 快捷键和脚本不写裸 `quickshell ipc`，也不写用户源码路径。Shell 内部直接使用
Quickshell API 的地方不需要机械地经过 CLI。

托管快捷键写为独立 argv，不经过 shell 字符串或每次按键的配置 helper：

```kdl
spawn "qs" "-c" "clavis" "ipc" "call" "keystone" "hub"
```

`key ipc call` 的标准既有绑定可以识别为同一 Clavis 动作，但保留原文本。
录屏、录音、剪贴板继续使用各自的 `key` 接口。
动作目录根据实际 IpcHandler 注册维护；需参数的方法保留显式参数模板。
首次在快捷键页面点击“设置”创建缺失的 binds.kdl 时，写入以下默认键位。
全部使用 `spawn "qs" "-c" "clavis" "ipc" "call" ...`，并设置 `repeat=false`。
`Mod` 跟随 Niri 的主修饰键（通常为 Super）。

| 快捷键 | 功能 | IPC target / method / arguments |
| --- | --- | --- |
| Mod+Space | Spotlight 搜索 | spotlight toggle |
| Mod+Slash | 快捷键配置图 | shortcut-map toggle |
| Mod+Shift+Space | 网页搜索 | spotlight web |
| Mod+Alt+V | 剪贴板历史 | spotlight openMode clipboard |
| Mod+Alt+W | 壁纸选择 | spotlight openMode wallpapers |
| Mod+N | 通知与信息侧栏 | sidebar toggle dashboard |
| Mod+A | 快捷设置侧栏 | sidebar toggle quicksettings |
| Mod+Ctrl+Comma | 设置中心 | control-center toggle general |
| Mod+Shift+W | Keystone 主面板 | keystone hub |
| Mod+Shift+T | 工具面板 | keystone tools |
| Alt+Shift+L | 锁屏 | lock open |

这些键避开 Niri 常用窗口、工作区、截图和媒体控制。首次接入前按有效 include 链
检查物理键位占用（含 Mod/Super 别名），发现冲突则拒绝写入并列出键名；用户可释放
这些键，或自行创建自定义 binds.kdl 后接入。任意第三方配置都可能占用默认键，不能
保证对所有配置天然无冲突。已有文件即使为空也不补写，升级不恢复用户删改的绑定。
安装只部署程序；不会自动改写用户 Niri 配置。

目录维护依据：[niri 键绑定](https://niri-wm.github.io/niri/Configuration:-Key-Bindings.html)、
[默认配置](https://github.com/niri-wm/niri/blob/main/resources/default-config.kdl)、
[可绑定动作定义](https://github.com/niri-wm/niri/blob/main/niri-config/src/binds.rs) 与
[Quickshell IpcHandler](https://quickshell.org/docs/v0.3.0/types/Quickshell.Io/IpcHandler/)。
托管片段按 [niri include 顺序](https://niri-wm.github.io/niri/Configuration:-Include.html)
处理覆盖。目录随程序部署，运行时只在本机验证动作支持，不联网下载。

快捷键配置图独立于设置中心加载，使用 `qs -c clavis ipc call shortcut-map toggle`
打开或关闭；也提供无参数的 `open` 和 `close`。账户页按钮与 IPC 共用同一个弹层。

侧栏 IPC 的参数按内容区分：`dashboard` 表示信息、抽屉和天气侧栏，`quicksettings`
表示快捷设置侧栏。通用设置 → 侧边栏中可独立选择各自的屏幕位置，默认仍为信息侧栏在左、快捷设置在右。
不同侧可同时打开；同侧时，点击另一组按钮会自动收起当前侧栏，待其退出后展开新的侧栏，
无需手动关闭。连续切换以最后一次请求为准，再次点击待展开侧栏可取消展开，Esc 可关闭全部。
将已打开的两组调整到同侧时，保留最近打开的一组。
`open`、`close`、`toggle` 均接受上述参数，返回 `DASHBOARD_OPEN/CLOSED` 或
`QUICKSETTINGS_OPEN/CLOSED`。旧参数 `left`、`right` 继续分别指向信息和快捷设置内容，
返回值保持 `LEFT_OPEN/CLOSED`、`RIGHT_OPEN/CLOSED`；它们不随实际位置重新解释。
已有用户绑定无需改写，快捷键页面会将旧参数识别为对应的内容动作。

灵动岛歌词界面通过 `qs -c clavis ipc call keystone lyrics` 切换展开与收起，返回
`LYRICS_OPENED` / `LYRICS_CLOSED`。两种样式均作用于当前输出（无匹配时使用首个屏幕），
展开时收起其他灵动岛面板。快捷键设置提供歌词动作占位，不绑定默认快捷键。

### Spotlight Files

`qs -c clavis ipc call spotlight openMode files` and
`qs -c clavis ipc call spotlight files` open Files and focus its input. Repeated
calls keep it open. Existing Apps/Wallpapers/Clipboard and web methods remain.

Ctrl+1/2/3/4 selects Apps/Wallpapers/Clipboard/Files. Tab expands the four-mode rail; subsequent Tab/Shift+Tab cycle it, and Enter selects a mode. In Files, Enter opens the selected file or enters
the folder; Ctrl+Enter requests selection in a file manager. Holding Ctrl immediately shows
the selected result's containing path; the right-click menu also exposes Open
and Show in file manager. Clipboard retains Shift+Enter.

Search uses the public `key file` capability through `${CLAVIS_KEY:-key}`. Install
fd plus key-cli supporting `file.status`/`file.search`; there is no invented
minimum release version. HOME is the default root, with fd's normal ignore/hidden
rules and no directory-symlink traversal. Queries are literal and case-insensitive;
slash-containing queries match paths. A 180 ms debounce feeds at most 50 results
from 400 candidates with a 3-second search budget. Limited searches are identified
in the UI. Empty input does not enumerate HOME.

Open uses the system default association and blocks launching executable content.
Reveal first requests FileManager1 selection, then falls back to opening the
parent directory without promising selection. Failures keep Spotlight open.

Settings → keyboard shortcuts includes **Spotlight: Find files** as an unbound
action. Bind/save it using the existing editor if desired; no default global
shortcut is added and existing user bindings are preserved.

### Spotlight Search (default)

`spotlight open`, the opening branch of `spotlight toggle`, `spotlight search`,
and `spotlight openMode search` enter Search. `open` and `search` are idempotent:
when Search is visible they focus it. A new session starts with an empty input
and no results panel. To open the application Grid/List directly, use
`qs -c clavis ipc call spotlight openMode apps`.

Ctrl+0 or the search icon returns to Search and preserves ordinary search text. Tool parameters and command drafts are cleared.
Ctrl+1/2/3/4 still opens Apps/Wallpapers/Clipboard/Files; Tab expands and cycles
the same four satellite buttons. Ctrl+K enters Web, and Esc from Web restores the previous
mode, including Search. The existing modal/rail/clear-input/close Esc priority and
IME composition handling remain. No new global key is installed.

Nonempty input searches the already loaded Apps directory, static Settings and
Actions catalogs, and `WallpaperService.wallpapers`, in that order. Groups display
with one responsive row of app icons/names and wallpaper thumbnails/names, and
up to two Settings/Actions entries each, with no category expansion. Up/Down moves between rows; Left/Right moves within
a tile row. There is no separate input/result navigation state; Esc follows the
shared modal/rail/clear-input/close behavior.
The last two rows
are explicit **Search files for…** and **Search the web for…** actions. Files is
queried only after entering its dedicated mode; Web opens only after activation.
Clipboard content, live web results and file results are not aggregated.

Search does not refresh or scan wallpaper folders. Files added externally become
visible after the existing startup, directory-change or dedicated wallpaper-page
refresh. There is no file index service or “enable indexing” setting.

Settings results release Spotlight before opening/focusing the existing Settings
window. Stable page/subpage IDs and section anchors support scroll and brief
highlight after loading and layout. Later requests replace earlier ones; leaving
the page or closing the window cancels pending navigation. A missing or hidden
section reports that it is unavailable.

Actions reuse fixed Clavis shortcuts and business functions. Power opens the
existing confirmation menu. Parameter templates, raw compositor commands,
queries, duplicate navigation aliases and the reserved no-op `cancelRecord` are
not exposed as executable Search results. No shell expression is evaluated.
See [search catalog maintenance](architecture/spotlight-search.md).

### Spotlight commands and temporary tools

`spotlight commands` and `spotlight openMode commands` are idempotent public
entries. Explicit IPC mode navigation clears temporary tools/overrides through
the same session controller as local navigation; it does not change user keys.

All 16 command-palette actions are also callable as
`qs -c clavis ipc call spotlight command NAME`, using the slash name without `/`
(e.g. `calc`, `fx`, `time`, `light`, `dark`, `find-settings`, `actions`, `map`).
This returns `OK` or `INVALID_COMMAND`; scoped layout/order overrides are rejected.
Tools open a fresh session; theme, Settings and map actions also work while
Spotlight is closed. Existing dedicated IPC entry points remain compatible.
Every palette action has a permanent row in Settings → Shortcuts, reusing existing
rows where available. The new rows start unassigned and add no default bindings.

Type `>` to enter the command palette immediately (`>calc` filters Calculator).
Slash drafts stay in their base mode. Enter executes an exact command; slash input has no suggestion list. Unknown commands
never fall through to content activation. `\/etc` and `\>hello` are literal
searches. Tool parameters are not reparsed as top-level commands.

| Command | Behavior |
| --- | --- |
| `/default`, `/apps`, `/wallpaper` (`/wallpapers`), `/clipboard`, `/files`, `/commands` | Base mode navigation |
| `/search` (`/web`) | Web tool, not default Search |
| `/calc`, `/fx` (`/currency`), `/time` (`/tz`) | Calculator, currency, time zone |
| `/find-settings`, `/actions` | Settings-only / IPC action-only search |
| `/light`, `/dark`, `/settings`, `/map` | Apply theme, open Settings, open standalone location map |
| `/list`, `/grid`, `/smart`, `/most-used`, `/recent` (`/recently-used`), `/name` | Apps-only temporary presentation |
| `/compact`, `/detail` (`/details`) | Clipboard-only temporary presentation |

Tool commands accept trailing input, e.g. `/calc (120 + 80) * 0.85` or
`/fx 100 USD to CNY`. The first Enter only enters the tool. A later Enter copies
its valid result (Web submits); it does not close calculation tools.

Empty-input Backspace removes the current tool, then the most recent presentation
override. It requires a fresh press in the search input, no selection/preedit or
modal dialog. Holding Backspace cannot unwind the stack. Theme changes
and other completed actions are never undone. Closing clears temporary state.

Tab and Shift+Tab always navigate the mode rail; they never complete input.
Ctrl editing shortcuts and Files Ctrl+Enter retain their previous behavior.

Currency opens with four independent slots: amount, currency, amount, currency,
separated by ≈. Left/Right select adjacent slots without wrapping. Clicking a
slot activates it; typing replaces the selected value. The last edited amount
is the driver; currency changes preserve that side. `/fx 100 USD to CNY` seeds
the slots, while `/fx` defaults to 1 USD → EUR.

Only active currency slots show locally filtered candidates. Up/Down select and
Enter confirms without copying. Tab/Shift+Tab retain mode-rail navigation.
Ctrl+C copies the current slot (an explicit text selection takes priority).
Ctrl+A highlights the whole four-slot expression; Ctrl+C then copies that expression.
With candidates closed, Enter copies the derived amount without its currency.
A fresh Backspace in an empty amount slot leaves Currency.

Only the confirmed pair requests `key tool currency --expression="1 USD to EUR"`.
Amount edits and direction changes reuse that rate locally, using decimal-string
arithmetic. Reverse conversion rounds half-even to 24 decimal places. Pending or
invalid dependent amounts cannot be copied. Existing generation checks reject
old pair results, and current driver state determines which amount is derived.

Time opens a searchable list of templates from local time to every available
time zone. “Change source” chooses a different source zone. Select a template
with Enter, then type a time (`0930`, `9`, `09:30`, or a date and time). Clearing
the input and pressing Backspace again returns to template selection. Another
fresh Backspace on the empty selector leaves the tool. DST ambiguity and invalid
times still use the existing explicit result/error flow.

### Sidebar weather and drawer

`qs -c clavis ipc call sidebar open weather` and `sidebar open drawer` select the
respective dashboard tab and open its sidebar, following the configured edge.
Open/close remain explicit IPC operations. Spotlight Actions and permanent
unassigned shortcut rows instead use `sidebar toggle weather` / `sidebar toggle drawer`.
Toggling the already open target tab closes it; a closed sidebar or a different
active tab opens the requested tab. No default key is installed.

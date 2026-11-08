# Nyxuri Shell 启动闭包与资源所有者

> 本页是 Nyxuri Shell 当前启动装配、条件加载与资源生命周期的源码索引，以 `shell/` 源码和行为测试为准；静态声明不代表运行时实例或活跃资源。

## 证据边界

本次使用 [`singleton_inventory.py`](../../shell/scripts/dev/singleton_inventory.py) 与 [`resource_inventory.py`](../../shell/scripts/dev/resource_inventory.py) 扫描当前 `shell/` 源树。输出均标记 `runtime_claims=false`：共扫描 **512** 个 QML 文件；单例扫描得到 **85** 条 `pragma Singleton` 声明和 **24** 个 `qmldir` alias；资源扫描得到 **406** 条 `Timer`、`Process`、`FileView`、`Connections` 声明。这些是源码记录数，不是实例数、启动数或存活数。扫描也包含 `archive/` 与 `tests/fixtures/`，不能据此判断当前应用装载了哪些对象。

生成器是词法扫描器，不求值 QML 绑定、不沿运行时引用解析对象，也不测量窗口、Canvas、layer、文件访问或进程状态。运行时 `ShellStartupService.qmlCensus()` 只记录 `SlotHost` Loader 委托和显式调用 `registerQmlResource()` 的服务资源；其返回状态明确为 `partial`，Canvas/layer 不受支持。因而本页把“源码保证的创建边”和“实际运行态”分开写。见 [`ShellStartupService.qml`](../../shell/services/ShellStartupService.qml#L123) 的 census 实现与 [`partial` 状态](../../shell/services/ShellStartupService.qml#L168)。

## 启动闭包

`shell.qml` 静态导入 `QtQuick`、`Quickshell`、`qs.app`、`qs.commons`、`qs.commons.cards`、`qs.commons.i18n`、`qs.services`、`qs.ui`，随后创建 `ShellRoot` 和 `AppShell`。顶层共享层导入是供动态插件解析共享模块的注册闭包；导入模块不等于实例化其中每个 Singleton。见 [`shell.qml` imports](../../shell/shell.qml#L10) 与 [`ShellRoot` 创建边](../../shell/shell.qml#L24)。

`AppShell.qml` 再导入 app/services/commons 与相对的 settings、dashboard infotools、wallpaper 模块，并直接创建 `SlotHost`、`HotCorners`、宿主级 `Binding`、`Connections` 和 IPC handler。它不按名称创建 12 个单元根组件。Shortcut Map 是单独的边：`ShortcutMap.qml` 的 Loader 只在 `ShortcutMapService.visible` 为真时激活。见 [`AppShell` qs imports](../../shell/app/AppShell.qml#L4)、[`AppShell` relative imports](../../shell/app/AppShell.qml#L6)、[`commons` import](../../shell/app/AppShell.qml#L9)、[`SlotHost` 创建边](../../shell/app/AppShell.qml#L58)、[`HotCorners` 创建边](../../shell/app/AppShell.qml#L74)、[`Binding`](../../shell/app/AppShell.qml#L95)、[`Connections`](../../shell/app/AppShell.qml#L104)、[`Shortcut Map` Loader](../../shell/app/AppShell.qml#L115)、[IPC handlers](../../shell/app/AppShell.qml#L129) 和 [`test_plugin_manifests.py`](../../shell/tests/test_plugin_manifests.py#L91)。

插件入口的装配链是：`PluginRegistry` 从 manifest 派生每个 UI kind 的 mount row；`SlotHost` 的 `Repeater` 以 `PluginRegistry.units` 为 model，为 row 建立 Loader；manifest validator 先校验 entry point，再生成绝对 `file://` URL，Loader 使用该 `entryUrl`。Loader 的激活条件是 `StateProjection.primed && slotActive(modelData) && !suppressed`，所以初次账本投影未落定时不会挂载。源码测试也锁定了这一闭包与 file URL 形态。见 [`PluginRegistry.qml`](../../shell/services/PluginRegistry.qml#L104)、[`PluginManifest.js` 入口校验](../../shell/services/PluginManifest.js#L100)、[`PluginManifest.js` URL 构造](../../shell/services/PluginManifest.js#L510)、[`SlotHost.qml`](../../shell/app/SlotHost.qml#L41) 和 [`test_plugin_manifests.py`](../../shell/tests/test_plugin_manifests.py#L89)。

| 一方单元 | 插槽 | manifest 入口 |
| --- | --- | --- |
| wallpaper | `surface:desktop` | [`WallpaperBackground.qml`](../../shell/plugins/wallpaper/manifest.toml#L10) |
| desktopcards | `surface:desktop` | [`DesktopCardHost.qml`](../../shell/plugins/desktopcards/manifest.toml#L10) |
| bar | `edge` | [`Bar.qml`](../../shell/plugins/bar/manifest.toml#L10) |
| dock | `edge` | [`DockHost.qml`](../../shell/plugins/dock/manifest.toml#L10) |
| keystone | `island` | [`Keystone.qml`](../../shell/plugins/keystone/manifest.toml#L10) |
| notifications | `popup:notification` | [`NotificationPopupHost.qml`](../../shell/plugins/notifications/manifest.toml#L10) |
| regionselector | `overlay` | [`RegionSelector.qml`](../../shell/plugins/regionselector/manifest.toml#L10) |
| sidebars | `drawer` | [`SidebarHostWindow.qml`](../../shell/plugins/sidebars/manifest.toml#L10) |
| lock | `overlay` | [`Lock.qml`](../../shell/plugins/lock/manifest.toml#L10) |
| launcher | `overlay` | [`LauncherHost.qml`](../../shell/plugins/launcher/manifest.toml#L10) |
| session | `overlay` | [`SessionHost.qml`](../../shell/plugins/session/manifest.toml#L10) |
| settings | `overlay` | [`SettingsHost.qml`](../../shell/plugins/settings/manifest.toml#L14) |

槽仲裁也是激活条件的一部分：已禁用单元不激活，唯独已持有的 lock 会延迟卸载到解锁；keystone 启用时占有 `popup:notification`，通知入口让位。Loader 编译失败最多自愈两轮，再抑制到下一次 unit 状态变更。它们是代码定义的装载策略，不是本页已运行 Quickshell 后观测到的对象树。见 [`SlotHost.qml`](../../shell/app/SlotHost.qml#L29) 和 [`test_plugin_manifests.py`](../../shell/tests/test_plugin_manifests.py#L97)。

还存在嵌套的条件边：settings 的 control-center/dashboard LazyLoader 分别由 `active` 和展示模式门控，页面 Loader 在路由选择后装载；`WeatherService` 在该 singleton 被解析后通过 backend Loader 装载天气 backend；歌词 backend 随 `LyricsService` 组件存在，但请求与计时由 active/播放态控制。这些都不应和根级 12 个 manifest 入口混为一谈。见 [`SettingsHost.qml`](../../shell/plugins/settings/SettingsHost.qml#L168)、[`SettingsPageHost.qml`](../../shell/plugins/settings/SettingsPageHost.qml#L128)、[`WeatherService.qml`](../../shell/services/WeatherService.qml#L86)、[`LyricsService.qml`](../../shell/plugins/settings/dashwindow/lyrics/LyricsService.qml#L253)。

## 启动阶段

`AppShell.Component.onCompleted` 记录 `READY`，再通过 `Qt.callLater` 依次记录 `FIRST_FRAME`、`IPC_READY`，随后把非 gate 工作排入串行后台队列：`theme-colors`、`fonts`、`i18n`、`system-identity`、`ui-theme-poll`。队列逐项让出 event loop；这些任务不是 `IPC_READY` 的前置条件。`ShellStartupService` 去重 queued/running/completed 任务、捕获并记录失败，并在销毁时取消队列。Shell IPC 暴露 stage/status/metrics，但静态计时点不能替代真实启动计时。见 [`AppShell.qml`](../../shell/app/AppShell.qml#L37)、[`ShellStartupService.qml`](../../shell/services/ShellStartupService.qml#L9)、[`ShellStartupService.qml`](../../shell/services/ShellStartupService.qml#L204)、[`AppShell.qml`](../../shell/app/AppShell.qml#L176)。

## 所有者与释放边界

| 所有者 / 消费者类别 | 资源边界与源码例子 |
| --- | --- |
| 宿主装配与投影 | `SlotHost` 持有每个 Repeater 委托的 Loader；委托创建/销毁时登记/移除 census 记录。禁用或仲裁让位通过 Loader 生命周期卸载单元根。 [`SlotHost.qml`](../../shell/app/SlotHost.qml#L69) · [`ShellStartupService.qml`](../../shell/services/ShellStartupService.qml#L44) |
| 合成器 singleton | `NiriDriver` 声明 socket、重连/输出更新 timers 及输出、电源、版本 probe processes；连接取决于 `isNiri`，重连由 socket 状态触发。销毁时撤销显式资源记录、停止 timers/processes 并断开两个 socket。静态存在这些声明不表示当前环境有 Niri、socket 已连接或 probe 正在运行。 [`NiriDriver.qml`](../../shell/services/NiriDriver.qml#L66) · [`NiriDriver.qml` teardown](../../shell/services/NiriDriver.qml#L871) |
| 租约式共享服务 | `SystemMonitorService` 按 consumer owner 合并模块租约；有效模块集合为空时停流，有订阅时启动/替换采样进程。bar、lock、dashboard/system cards 是实际调用方；这些组件在销毁时清除各自租约。 [`SystemMonitorService.qml`](../../shell/services/SystemMonitorService.qml#L102) · [`SystemMonitorService.qml` zero-lease branch](../../shell/services/SystemMonitorService.qml#L153) · [`SysMonitor.qml` release](../../shell/plugins/bar/sysmonitor/SysMonitor.qml#L78) · [`Lock.qml` lease / release](../../shell/plugins/lock/Lock.qml#L121) · [`DashboardHomePage.qml` lease](../../shell/plugins/settings/dashwindow/DashboardHomePage.qml#L149) · [`SystemCardService.qml` leases](../../shell/services/SystemCardService.qml#L250) · [`SystemCardService.qml` release](../../shell/services/SystemCardService.qml#L280) |
| 播放状态订阅 | `MediaService` 的位置 Timer 只有在订阅者存在、播放器存在且播放中并支持 position 时运行；最后一个订阅释放后清位置值。`MediaContent` 是已知订阅者。 [`MediaService.qml`](../../shell/services/MediaService.qml#L39) · [`MediaService.qml` timer gate](../../shell/services/MediaService.qml#L72) · [`MediaContent.qml`](../../shell/plugins/keystone/media/MediaContent.qml#L395) |
| 功能服务 singleton | `WeatherService` 通过 backend Loader 延迟到服务解析边界；`WallpaperService` 的自动切换 timers 只在桌面非激活、自动切换开启且模式匹配时运行。wallpaper 视觉入口归 unit Loader，但宿主仍导入并调用 `WallpaperService` 承担 wallpaper IPC/主题能力，因此不能把 unit off 推断成该服务一并销毁。 [`WeatherService.qml`](../../shell/services/WeatherService.qml#L86) · [`WallpaperService.qml` timer gate](../../shell/plugins/wallpaper/WallpaperService.qml#L653) · [`AppShell.qml`](../../shell/app/AppShell.qml#L209) |
| 搜索与页面组件 | `SpotlightSearchService` 只在 URL 查询时启动浏览器 handler process/query timeout，匹配窗口后用短轮询 focus timer；`FileSearchService` 的 debounce/search/status/action process 由 active/query/请求驱动，销毁时停 timer 并终止 process。`LyricsService` 是 dashboard 页面中的组件：同步/插值 timer 受 active、播放态与歌词存在门控，停用/销毁会停 timers 并 cancel backend。 [`SpotlightSearchService.qml`](../../shell/plugins/launcher/SpotlightSearchService.qml#L38) · [`FileSearchService.qml`](../../shell/plugins/launcher/FileSearchService.qml#L73) · [`FileSearchService.qml`](../../shell/plugins/launcher/FileSearchService.qml#L267) · [`LyricsService.qml` sync timer gate](../../shell/plugins/settings/dashwindow/lyrics/LyricsService.qml#L253) · [`LyricsService.qml` interpolation timer gate](../../shell/plugins/settings/dashwindow/lyrics/LyricsService.qml#L275) · [`LyricsService.qml` teardown](../../shell/plugins/settings/dashwindow/lyrics/LyricsService.qml#L280) |
| 设备操作服务 | `NetworkService` / `BluetoothService` 分别按 scan/discovery owner 管理设备扫描；面板持有租约，释放后重新汇总是否应扫描。写配置、forget、手动 scan/discovery 和单项 operation timers 是有限期操作资源；服务销毁时停止 timers、清 owner 并关闭扫描。它们的源码声明本身不代表扫描或操作正在进行。 [`NetworkService.qml` lease](../../shell/services/NetworkService.qml#L430) · [`NetworkContent.qml`](../../shell/plugins/sidebars/quicksettings/NetworkContent.qml#L65) · [`NetworkService.qml` timer registration](../../shell/services/NetworkService.qml#L953) · [`NetworkService.qml` teardown](../../shell/services/NetworkService.qml#L960) · [`BluetoothService.qml` lease](../../shell/services/BluetoothService.qml#L286) · [`BluetoothContent.qml`](../../shell/plugins/sidebars/quicksettings/BluetoothContent.qml#L63) · [`BluetoothService.qml` operation timers](../../shell/services/BluetoothService.qml#L581) · [`BluetoothService.qml` teardown](../../shell/services/BluetoothService.qml#L446) |
| 主题操作服务 | `ThemeService` 在 startup background 队列中接收颜色刷新；服务完成时还会探测主题、应用设置并尝试从当前 wallpaper 生成色板。图标/光标探测和色板生成各有 `Process`，只有相应函数启动时才运行；不能将声明数当作冷启动进程数。 [`AppShell.qml`](../../shell/app/AppShell.qml#L50) · [`ThemeService.qml`](../../shell/services/ThemeService.qml#L412) · [`ThemeService.qml`](../../shell/services/ThemeService.qml#L480) · [`ThemeService.qml`](../../shell/services/ThemeService.qml#L505) |

## 运行时核验边界

源码和契约测试能证明装配表达式、门控条件、显式注册/注销调用点；静态生成器不能证明某条 Loader 已激活、服务 singleton 已解析、某个租约当前持有、Process 正在运行或 teardown 已在真实会话中完成。需要回答这些问题时，应读取运行中 Shell 的 `shell` IPC metrics / `qmlCensus`，并对目标开关或消费者做实际开关验证；census 本身也只覆盖明确登记的部分，不能当成完整 QObject、窗口或内核资源快照。

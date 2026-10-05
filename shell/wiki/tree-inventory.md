# Nyxuri Shell 全树结构清单与迁移映射

> 契约依据：[ROADMAP.md](../ROADMAP.md) R4-C 结构收敛与全面去 C++。
> 本清单覆盖 `app/`、`modules/`、`shared/`、`native/`、`bin/`、`packaging/` 六大代码分支。
> 逐文件标定 `保留`、`移动`、`合并`、`删除`、`阻断` 处置动作，记录所有者、消费者、I/O 与副作用。

---

## 1. 统计概览

- **现存文件总数**：562 个（基线 631 文件；R4-C-01 物理删除 2 个冗余代理，迁入 12 个服务；R4-C-02 物理删除 8 个僵尸代码与假桩，重命名 8 个服务/按钮/工具）
- **分层分布**：
  - `app/`：43 个文件
  - `modules/`：391 个文件
  - `shared/`：125 个文件
  - `native/`：0 个文件
  - `bin/`：0 个文件
  - `packaging/`：3 个文件
- **处置状态分布**：
  - **保留**：532 个文件
  - **合并**：1 个文件
  - **移动**：21 个文件
  - **重命名**：8 个文件

---

## 2. R4-C-02 功能域内聚重组执行记录

| 原文件路径 | 处置动作 | 目标路径 | 处置原因与验收结果 |
|---|---|---|---|
| `app/services/AudioRecordingService.qml` | **移动** | `modules/keystone/tools/AudioRecordingService.qml` | 仅 keystone 消费的音频录制后台 |
| `app/services/AudioSpectrum.qml` | **删除** | `-` | 纯假桩空壳，已物理删除并解除调用点假绑定 |
| `app/services/AutostartService.qml` | **移动** | `modules/settings/AutostartService.qml` | 仅 settings 自启动页消费的配置服务 |
| `app/services/AwwwWallpaperService.qml` | **移动** | `modules/wallpaper/AwwwWallpaperService.qml` | awww 外部壁纸后端服务 |
| `app/services/Brightness.qml` | **重命名** | `app/services/BrightnessService.qml` | 确立 Service 后缀并消除与 Bar 按钮同名冲突 |
| `app/services/DesktopPresentationService.qml` | **移动** | `modules/desktopcards/DesktopPresentationService.qml` | 桌面卡片呈现视口与坐标变换服务 |
| `app/services/DisplayConfigService.qml` | **移动** | `modules/settings/DisplayConfigService.qml` | 仅 settings 显示设置页消费的显示配置服务 |
| `app/services/FileSearchService.qml` | **移动** | `modules/launcher/FileSearchService.qml` | 仅 launcher 消费的专属文件检索后台 |
| `app/services/InfoDrawerState.qml` | **移动** | `modules/sidebars/dashboard/infotools/InfoDrawerState.qml` | 侧边栏抽屉与计时器持久化状态 |
| `app/services/MediaManager.qml` | **重命名** | `app/services/MediaService.qml` | 确立 Service 后缀命名法典 |
| `app/services/MediaPalette.qml` | **移动** | `modules/keystone/media/MediaPalette.qml` | 仅 keystone 消费的媒体色板辅助 |
| `app/services/NetworkInterfaceHistoryService.qml` | **移动** | `modules/systemcards/NetworkInterfaceHistoryService.qml` | 仅 systemcards 消费的网络流量历史服务 |
| `app/services/NotificationManager.qml` | **重命名** | `app/services/NotificationService.qml` | 确立 Service 后缀命名法典 |
| `app/services/QuickToggleConfig.qml` | **移动** | `modules/quicksettings/QuickToggleConfig.qml` | 仅 quicksettings 消费的快捷开关配置 |
| `app/services/RecordingService.qml` | **移动** | `modules/keystone/tools/RecordingService.qml` | 仅 keystone 消费的屏幕录制后台 |
| `app/services/SpotlightSearchService.qml` | **移动** | `modules/launcher/SpotlightSearchService.qml` | 仅 launcher 消费的聚焦搜索执行后台 |
| `app/services/SpotlightToolService.qml` | **移动** | `modules/launcher/SpotlightToolService.qml` | 仅 launcher 消费的数学/时区工具后台 |
| `app/services/SystemCardDragSession.qml` | **移动** | `modules/desktopcards/SystemCardDragSession.qml` | 桌面卡片手势拖放会话 |
| `app/services/SystemCardDragState.js` | **移动** | `modules/desktopcards/SystemCardDragState.js` | 桌面卡片拖放状态机纯函数 |
| `app/services/Time.qml` | **重命名** | `app/services/TimeService.qml` | 确立 Service 后缀命名法典 |
| `app/services/TimerService.qml` | **移动** | `modules/sidebars/dashboard/infotools/TimerService.qml` | 侧边栏抽屉番茄钟与秒表计时服务 |
| `app/services/TodoService.qml` | **移动** | `modules/sidebars/dashboard/infotools/TodoService.qml` | 仅 sidebars 消费的待办事项服务 |
| `app/services/TrayService.qml` | **移动** | `modules/bar/tray/TrayService.qml` | 仅 bar 托盘消费的系统托盘服务 |
| `app/services/Volume.qml` | **重命名** | `app/services/VolumeService.qml` | 确立 Service 后缀命名法典 |
| `app/services/WallpaperPaletteSession.qml` | **移动** | `modules/wallpaper/WallpaperPaletteSession.qml` | 壁纸取色与调色会话 |
| `app/services/WallpaperSceneService.qml` | **移动** | `modules/wallpaper/WallpaperSceneService.qml` | 壁纸视差与视口场景服务 |
| `app/services/WallpaperService.qml` | **移动** | `modules/wallpaper/WallpaperService.qml` | 壁纸功能域核心服务 |
| `app/services/WeatherPlugin.qml` | **重命名** | `app/services/WeatherService.qml` | 消除伪插件名并确立 Service 命名法典 |
| `app/services/WindowPreviewService.qml` | **删除** | `-` | 纯假桩空壳，已物理删除并解除调用点假绑定 |
| `app/services/weather/WeatherBackend.qml` | **合并** | `app/services/WeatherService.qml` | 9 行纯 Loader 壳，待合并入天气组件或 R4-C-05 消除 |
| `modules/bar/quicksettings/Brightness.qml` | **重命名** | `modules/bar/quicksettings/BrightnessButton.qml` | 消除与服务同名冲突 |
| `modules/dock/preview/DockCaptureImage.qml` | **删除** | `-` | 假预览空壳，已物理删除 |
| `modules/keystone/lyrics/HorizontalLyricsLayout.qml` | **删除** | `-` | 废弃歌词僵尸代码，已物理删除 |
| `modules/keystone/lyrics/LyricsAlbumArt.qml` | **删除** | `-` | 废弃歌词僵尸代码，已物理删除 |
| `modules/keystone/lyrics/LyricsContent.qml` | **删除** | `-` | 废弃歌词僵尸代码，已物理删除 |
| `modules/keystone/lyrics/LyricsSpectrum.qml` | **删除** | `-` | 废弃歌词僵尸代码，已物理删除 |
| `modules/keystone/lyrics/VerticalLyricsLayout.qml` | **删除** | `-` | 废弃歌词僵尸代码，已物理删除 |
| `modules/keystone/tools/ToolsBackend.qml` | **删除** | `-` | 纯转发代理，直连录制服务，取色走 ActionGateway |
| `modules/settings/SplitMenuButton.qml` | **删除** | `-` | 重复包装壳，直接使用 shared/controls/SplitMenuButton |
| `modules/sidebars/dashboard/infotools/calendar_layout.js` | **重命名** | `modules/sidebars/dashboard/infotools/CalendarLayout.js` | 对齐全库 PascalCase.js 命名法典 |

---

## 3. 逐层结构清单与实时映射

### app/ （共 43 文件）

| 文件路径 | 处置状态 | 归属 (Owner) | 消费者 (Consumers) | I/O | 副作用 | 目标路径 / 说明 |
|---|---|---|---|---|---|---|
| `app/ActionGateway.qml` | **保留** | `app` | app, modules/bar, modules/dock, modules/keystone, modules/launcher, modules/quicksettings, modules/session, modules/settings, modules/sidebars | 属性(4)/信号(8)/方法(15) | execDetached | 功能域自治代码 |
| `app/AppShell.qml` | **保留** | `app` | 内部/自包含 | 方法(37) | 无 | 功能域自治代码 |
| `app/Paths.qml` | **保留** | `app` | app, modules/bar, modules/keystone, modules/launcher, modules/lock, modules/quicksettings, modules/settings, modules/sidebars, modules/wallpaper | 属性(33)/方法(5) | Env | 功能域自治代码 |
| `app/WidgetState.qml` | **保留** | `app` | app, modules/bar, modules/keystone, modules/quicksettings, modules/settings, modules/sidebars, modules/wallpaper | 属性(7)/信号(1)/方法(2) | 无 | 功能域自治代码 |
| `app/services/ApplicationService.qml` | **保留** | `app` | app, modules/bar, modules/dock, modules/launcher, modules/notifications, modules/settings, modules/sidebars | 属性(6)/方法(13) | GatewayExec | 功能域自治代码 |
| `app/services/AvatarService.qml` | **保留** | `app` | modules/keystone, modules/lock, modules/settings, modules/sidebars | 属性(5)/信号(1)/方法(1) | GatewayExec, Process | 功能域自治代码 |
| `app/services/BluetoothService.qml` | **保留** | `app` | modules/bar, modules/keystone, modules/quicksettings, modules/settings, modules/sidebars | 属性(29)/信号(3)/方法(44) | Timer | 功能域自治代码 |
| `app/services/BlurService.qml` | **保留** | `app` | modules/bar, modules/desktopcards, modules/dock, modules/filepicker, modules/keystone, modules/launcher, modules/lock, modules/settings, modules/sidebars, modules/systemcards | 属性(10)/信号(2)/方法(9) | Process | 功能域自治代码 |
| `app/services/BrightnessService.qml` | **重命名** | `app` | app, modules/bar, modules/keystone, modules/quicksettings, modules/sidebars | 属性(21)/信号(2)/方法(23) | Process, Timer | 已由 app/services/Brightness.qml 重命名，遵循命名法典与内聚规范 |
| `app/services/ClipboardService.qml` | **保留** | `app` | modules/launcher, modules/settings | 属性(48)/信号(6)/方法(24) | Process | 功能域自治代码 |
| `app/services/DefaultApplicationsService.qml` | **保留** | `app` | modules/launcher, modules/settings | 属性(27)/信号(1)/方法(36) | Process, FileView | 功能域自治代码 |
| `app/services/DisplayColor.qml` | **保留** | `app` | modules/quicksettings, modules/settings | 属性(16)/信号(1)/方法(6) | Process, Timer, FileView | 功能域自治代码 |
| `app/services/DockService.qml` | **保留** | `app` | modules/dock, modules/launcher, modules/settings | 属性(39)/信号(1)/方法(32) | Process, Timer, FileView, Env | 功能域自治代码 |
| `app/services/FileActionService.qml` | **保留** | `app` | app | 属性(2)/信号(1)/方法(1) | Process | 功能域自治代码 |
| `app/services/FontService.qml` | **保留** | `app` | app, modules/settings | 属性(20)/方法(8) | 无 | 功能域自治代码 |
| `app/services/I18nService.qml` | **保留** | `app` | app, modules/keystone, modules/settings, modules/sidebars, modules/systemcards | 属性(5)/方法(7) | FileView, Env | 功能域自治代码 |
| `app/services/IdleInhibitorSurface.qml` | **保留** | `app` | app | - | 无 | 功能域自治代码 |
| `app/services/IdleService.qml` | **保留** | `app` | app, modules/quicksettings, modules/sidebars | 属性(29)/信号(4)/方法(19) | GatewayExec, Process, FileView | 功能域自治代码 |
| `app/services/KeyboardLockService.qml` | **保留** | `app` | app, modules/keystone, modules/lock, modules/settings | 属性(8)/信号(2)/方法(2) | Process, Timer | 功能域自治代码 |
| `app/services/MatugenTemplateService.qml` | **保留** | `app` | app, modules/settings | 属性(13)/信号(3)/方法(9) | Process, Timer, FileView | 功能域自治代码 |
| `app/services/MediaService.qml` | **重命名** | `app` | modules/bar, modules/dock, modules/keystone, modules/lock, modules/settings | 属性(3)/方法(9) | Timer | 已由 app/services/MediaManager.qml 重命名，遵循命名法典与内聚规范 |
| `app/services/NetworkManagerExtras.qml` | **保留** | `app` | app | 属性(17)/方法(7) | Process | 功能域自治代码 |
| `app/services/NetworkService.qml` | **保留** | `app` | modules/bar, modules/keystone, modules/lock, modules/quicksettings, modules/settings, modules/sidebars, modules/systemcards | 属性(70)/信号(8)/方法(57) | Timer | 功能域自治代码 |
| `app/services/NiriConfigService.qml` | **保留** | `app` | app, modules/bar, modules/hotcorners, modules/keystone, modules/settings, modules/sidebars, modules/wallpaper | 属性(21)/信号(1)/方法(10) | Process, FileView, Env | 功能域自治代码 |
| `app/services/NiriService.qml` | **保留** | `app` | app, modules/bar, modules/dock, modules/hotcorners, modules/keystone, modules/settings, modules/wallpaper | 属性(35)/信号(6)/方法(73) | Process, Timer, Env, IPC/Wayland | 功能域自治代码 |
| `app/services/NotificationService.qml` | **重命名** | `app` | modules/keystone, modules/lock, modules/notifications, modules/settings, modules/sidebars | 属性(28)/信号(5)/方法(34) | Process, Timer, FileView | 已由 app/services/NotificationManager.qml 重命名，遵循命名法典与内聚规范 |
| `app/services/PersonalizationConfig.qml` | **保留** | `app` | app, modules/bar, modules/desktopcards, modules/hotcorners, modules/keystone, modules/launcher, modules/lock, modules/notifications, modules/quicksettings, modules/settings, modules/sidebars, modules/wallpaper | 属性(157)/信号(1)/方法(148) | Process, Timer, FileView, Env | 功能域自治代码 |
| `app/services/PopupInputRegionService.qml` | **保留** | `app` | modules/desktopcards, modules/settings, modules/systemcards | 属性(1)/方法(3) | 无 | 功能域自治代码 |
| `app/services/PowerService.qml` | **保留** | `app` | modules/bar, modules/keystone, modules/lock, modules/settings, modules/systemcards | 属性(13)/方法(1) | 无 | 功能域自治代码 |
| `app/services/RegionSelectionService.qml` | **保留** | `app` | modules/keystone, modules/regionselector | 属性(7)/信号(2)/方法(3) | Timer | 功能域自治代码 |
| `app/services/ShellStartupService.qml` | **保留** | `app` | app | 属性(7)/信号(1)/方法(6) | 无 | 功能域自治代码 |
| `app/services/ShortcutMapService.qml` | **保留** | `app` | app, modules/settings | 属性(2)/方法(3) | 无 | 功能域自治代码 |
| `app/services/SpotlightAppUsage.qml` | **保留** | `app` | app, modules/launcher | 属性(6)/方法(4) | Process, FileView | 功能域自治代码 |
| `app/services/SpotlightCatalog.qml` | **保留** | `app` | app, modules/launcher, modules/settings | 属性(9)/信号(1)/方法(9) | GatewayExec | 功能域自治代码 |
| `app/services/SystemCardService.qml` | **保留** | `app` | app, modules/desktopcards, modules/settings, modules/sidebars | 属性(12)/信号(2)/方法(32) | 无 | 功能域自治代码 |
| `app/services/SystemIdentityService.qml` | **保留** | `app` | app, modules/keystone, modules/lock, modules/settings, modules/sidebars, modules/systemcards | 属性(32)/方法(8) | Process, Timer, FileView, Env | 功能域自治代码 |
| `app/services/SystemMonitorService.qml` | **保留** | `app` | app, modules/bar, modules/keystone, modules/lock, modules/settings, modules/sidebars, modules/systemcards | 属性(65)/方法(33) | Process, Timer, Env | 功能域自治代码 |
| `app/services/ThemeService.qml` | **保留** | `app` | app, modules/bar, modules/dock, modules/launcher, modules/lock, modules/notifications, modules/quicksettings, modules/settings, modules/sidebars, modules/wallpaper | 属性(22)/信号(1)/方法(44) | Process, FileView, Env | 功能域自治代码 |
| `app/services/TimeService.qml` | **重命名** | `app` | modules/bar, modules/settings, modules/sidebars | 属性(4)/方法(1) | Timer | 已由 app/services/Time.qml 重命名，遵循命名法典与内聚规范 |
| `app/services/UiPreferences.qml` | **保留** | `app` | app, modules/bar, modules/keystone, modules/launcher, modules/lock, modules/notifications, modules/quicksettings, modules/settings, modules/sidebars, modules/systemcards, modules/wallpaper | 属性(46)/方法(52) | Process, Timer, FileView, Env | 功能域自治代码 |
| `app/services/VolumeService.qml` | **重命名** | `app` | modules/bar, modules/keystone, modules/quicksettings, modules/sidebars | 属性(19)/信号(1)/方法(26) | 无 | 已由 app/services/Volume.qml 重命名，遵循命名法典与内聚规范 |
| `app/services/WeatherService.qml` | **重命名** | `app` | app, modules/bar, modules/keystone, modules/lock, modules/settings, modules/sidebars, modules/systemcards | 属性(36)/信号(2)/方法(8) | 无 | 已由 app/services/WeatherPlugin.qml 重命名，遵循命名法典与内聚规范 |
| `app/services/weather/WeatherBackend.qml` | **合并** | `app` | app, modules/settings | 属性(24)/信号(2)/方法(14) | Timer | 9 行纯 Loader 壳，待合并入天气组件或 R4-C-05 消除 |

### modules/ （共 391 文件）

| 文件路径 | 处置状态 | 归属 (Owner) | 消费者 (Consumers) | I/O | 副作用 | 目标路径 / 说明 |
|---|---|---|---|---|---|---|
| `modules/bar/Bar.qml` | **保留** | `bar` | app, modules/keystone, modules/settings, shared/controls | 属性(4) | 无 | 功能域自治代码 |
| `modules/bar/BarAxis.qml` | **保留** | `bar` | modules/bar | 属性(8) | 无 | 功能域自治代码 |
| `modules/bar/BarComponentLoader.qml` | **保留** | `bar` | modules/bar | 属性(4) | 无 | 功能域自治代码 |
| `modules/bar/BarContent.qml` | **保留** | `bar` | modules/bar | 属性(10) | 无 | 功能域自治代码 |
| `modules/bar/BarSection.qml` | **保留** | `bar` | modules/bar | 属性(3) | 无 | 功能域自治代码 |
| `modules/bar/HorizontalBarContent.qml` | **保留** | `bar` | modules/bar | - | 无 | 功能域自治代码 |
| `modules/bar/HorizontalBarWindow.qml` | **保留** | `bar` | modules/bar | 属性(5) | 无 | 功能域自治代码 |
| `modules/bar/VerticalBarContent.qml` | **保留** | `bar` | modules/bar | - | 无 | 功能域自治代码 |
| `modules/bar/VerticalBarWindow.qml` | **保留** | `bar` | modules/bar | 属性(5) | 无 | 功能域自治代码 |
| `modules/bar/activewindow/ActiveWindow.qml` | **保留** | `bar` | modules/bar | 属性(11)/方法(3) | 无 | 功能域自治代码 |
| `modules/bar/activewindow/SidebarButton.qml` | **保留** | `bar` | modules/bar | 属性(1) | 无 | 功能域自治代码 |
| `modules/bar/activewindow/SidebarPillButton.qml` | **保留** | `bar` | modules/bar | 属性(3)/方法(1) | 无 | 功能域自治代码 |
| `modules/bar/activewindow/SidebarWeatherButton.qml` | **保留** | `bar` | modules/bar | 属性(7)/方法(1) | 无 | 功能域自治代码 |
| `modules/bar/clock/Clock.qml` | **保留** | `bar` | modules/bar, modules/settings, modules/systemcards | 属性(3) | 无 | 功能域自治代码 |
| `modules/bar/clock/qmldir` | **保留** | `bar` | 内部/自包含 | - | 无 | 功能域自治代码 |
| `modules/bar/media/MediaBar.qml` | **保留** | `bar` | modules/bar, modules/keystone | 属性(7)/方法(2) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/Battery.qml` | **保留** | `bar` | app, modules/bar, modules/keystone, modules/settings, modules/sidebars, modules/systemcards | 属性(7)/方法(3) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/BluetoothButton.qml` | **保留** | `bar` | modules/bar | 属性(2) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/BrightnessButton.qml` | **重命名** | `bar` | modules/bar | 属性(5) | 无 | 已由 modules/bar/quicksettings/Brightness.qml 重命名，遵循命名法典与内聚规范 |
| `modules/bar/quicksettings/Microphone.qml` | **保留** | `bar` | app, modules/bar, modules/keystone, modules/quicksettings, modules/settings, modules/sidebars | 属性(3) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/Network.qml` | **保留** | `bar` | app, modules/bar, modules/keystone, modules/lock, modules/quicksettings, modules/settings, modules/sidebars, modules/systemcards, packaging | 属性(3)/方法(1) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/PowerButton.qml` | **保留** | `bar` | modules/bar | 属性(1) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/QuickSettings.qml` | **保留** | `bar` | modules/bar, modules/sidebars | 属性(3)/方法(1) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/SettingsButton.qml` | **保留** | `bar` | modules/bar | 属性(2) | 无 | 功能域自治代码 |
| `modules/bar/quicksettings/Volume.qml` | **保留** | `bar` | app, modules/bar, modules/keystone, modules/sidebars | 属性(3) | 无 | 功能域自治代码 |
| `modules/bar/sysmonitor/ResourcePie.qml` | **保留** | `bar` | modules/bar | 属性(17) | 无 | 功能域自治代码 |
| `modules/bar/sysmonitor/SysMonitor.qml` | **保留** | `bar` | modules/bar, modules/keystone | 属性(25)/方法(4) | 无 | 功能域自治代码 |
| `modules/bar/tray/Tray.qml` | **保留** | `bar` | app, modules/bar, modules/keystone | 属性(19)/方法(7) | 无 | 功能域自治代码 |
| `modules/bar/tray/TrayItem.qml` | **保留** | `bar` | modules/bar | 属性(4)/信号(2)/方法(3) | 无 | 功能域自治代码 |
| `modules/bar/tray/TrayMenu.qml` | **保留** | `bar` | modules/bar | 属性(12)/信号(2)/方法(3) | 无 | 功能域自治代码 |
| `modules/bar/tray/TrayMenuEntry.qml` | **保留** | `bar` | modules/bar | 属性(10)/信号(2) | 无 | 功能域自治代码 |
| `modules/bar/tray/TrayService.qml` | **移动** | `bar` | modules/bar | 属性(12)/方法(7) | Process, FileView | 已由 app/services/TrayService.qml 移动，遵循命名法典与内聚规范 |
| `modules/bar/workspaces/Workspaces.qml` | **保留** | `bar` | app, modules/bar, modules/keystone, modules/settings | 属性(8)/方法(1) | 无 | 功能域自治代码 |
| `modules/desktopcards/DesktopCard.qml` | **保留** | `desktopcards` | modules/desktopcards, modules/sidebars | 属性(13)/方法(3) | 无 | 功能域自治代码 |
| `modules/desktopcards/DesktopCardCanvas.qml` | **保留** | `desktopcards` | modules/desktopcards, modules/wallpaper | 属性(48)/信号(3)/方法(34) | 无 | 功能域自治代码 |
| `modules/desktopcards/DesktopCardGridOverlay.qml` | **保留** | `desktopcards` | modules/desktopcards | 属性(4) | 无 | 功能域自治代码 |
| `modules/desktopcards/DesktopCardHost.qml` | **保留** | `desktopcards` | app, modules/desktopcards, modules/wallpaper, shared/utils | 属性(17)/信号(2)/方法(26) | 无 | 功能域自治代码 |
| `modules/desktopcards/DesktopCardLayout.js` | **保留** | `desktopcards` | modules/desktopcards, modules/sidebars | 方法(35) | 无 | 功能域自治代码 |
| `modules/desktopcards/DesktopPresentationService.qml` | **移动** | `desktopcards` | modules/desktopcards, modules/sidebars | 属性(1)/方法(7) | 无 | 已由 app/services/DesktopPresentationService.qml 移动，遵循命名法典与内聚规范 |
| `modules/desktopcards/SystemCardDragSession.qml` | **移动** | `desktopcards` | modules/desktopcards, modules/sidebars | 属性(34)/信号(3)/方法(16) | 无 | 已由 app/services/SystemCardDragSession.qml 移动，遵循命名法典与内聚规范 |
| `modules/desktopcards/SystemCardDragState.js` | **移动** | `desktopcards` | modules/desktopcards | 方法(9) | 无 | 已由 app/services/SystemCardDragState.js 移动，遵循命名法典与内聚规范 |
| `modules/dock/DesktopFiles.qml` | **保留** | `dock` | app, modules/dock | 属性(3)/信号(3)/方法(7) | 无 | 功能域自治代码 |
| `modules/dock/DockBubble.js` | **保留** | `dock` | modules/dock | 方法(6) | 无 | 功能域自治代码 |
| `modules/dock/DockBubbleSurface.qml` | **保留** | `dock` | modules/dock | 属性(12)/方法(1) | 无 | 功能域自治代码 |
| `modules/dock/DockDragVisual.qml` | **保留** | `dock` | modules/dock | 属性(8)/方法(5) | 无 | 功能域自治代码 |
| `modules/dock/DockFanBlur.qml` | **保留** | `dock` | modules/dock | 属性(6)/方法(4) | 无 | 功能域自治代码 |
| `modules/dock/DockFileArtwork.qml` | **保留** | `dock` | modules/dock | 属性(7) | 无 | 功能域自治代码 |
| `modules/dock/DockFileDrag.qml` | **保留** | `dock` | modules/dock | 属性(6)/方法(3) | 无 | 功能域自治代码 |
| `modules/dock/DockFileIcon.qml` | **保留** | `dock` | modules/dock | 属性(3) | 无 | 功能域自治代码 |
| `modules/dock/DockFilePopup.qml` | **保留** | `dock` | modules/dock | 属性(37)/信号(1)/方法(9) | 无 | 功能域自治代码 |
| `modules/dock/DockFileTile.qml` | **保留** | `dock` | modules/dock | 属性(12)/信号(1) | 无 | 功能域自治代码 |
| `modules/dock/DockFolderFan.qml` | **保留** | `dock` | modules/dock | 属性(28)/信号(3) | 无 | 功能域自治代码 |
| `modules/dock/DockFolderMenu.qml` | **保留** | `dock` | modules/dock | 属性(13)/信号(2)/方法(11) | 无 | 功能域自治代码 |
| `modules/dock/DockFolderModel.qml` | **保留** | `dock` | modules/dock | 属性(8)/方法(6) | 无 | 功能域自治代码 |
| `modules/dock/DockHost.qml` | **保留** | `dock` | app | 属性(3) | 无 | 功能域自治代码 |
| `modules/dock/DockItem.qml` | **保留** | `dock` | modules/dock | 属性(33)/信号(8)/方法(1) | 无 | 功能域自治代码 |
| `modules/dock/DockLayout.js` | **保留** | `dock` | modules/dock | 方法(11) | 无 | 功能域自治代码 |
| `modules/dock/DockMedia.js` | **保留** | `dock` | modules/dock | 方法(3) | 无 | 功能域自治代码 |
| `modules/dock/DockModel.js` | **保留** | `dock` | app | 方法(21) | 无 | 功能域自治代码 |
| `modules/dock/DockMotion.js` | **保留** | `dock` | modules/dock | 方法(1) | 无 | 功能域自治代码 |
| `modules/dock/DockPreviewPopup.qml` | **保留** | `dock` | modules/dock | 属性(34)/信号(1)/方法(6) | Process | 功能域自治代码 |
| `modules/dock/DockSurface.qml` | **保留** | `dock` | modules/dock | 属性(72)/方法(32) | Timer | 功能域自治代码 |
| `modules/dock/DockWindowCard.qml` | **保留** | `dock` | modules/dock | 属性(13)/信号(2) | 无 | 功能域自治代码 |
| `modules/filepicker/FilePickerWindow.qml` | **保留** | `filepicker` | modules/keystone, modules/settings, modules/sidebars | 属性(65)/信号(2)/方法(19) | Timer | 功能域自治代码 |
| `modules/hotcorners/HotCorners.qml` | **保留** | `hotcorners` | app | 属性(5)/信号(1) | 无 | 功能域自治代码 |
| `modules/keystone/Keystone.qml` | **保留** | `keystone` | app, modules/dock, modules/keystone, modules/settings, shared/theme | 属性(1)/方法(9) | 无 | 功能域自治代码 |
| `modules/keystone/KeystoneMotion.qml` | **保留** | `keystone` | modules/keystone | 属性(20) | 无 | 功能域自治代码 |
| `modules/keystone/clock/ClockContent.qml` | **保留** | `keystone` | modules/keystone, modules/settings | 属性(29)/方法(6) | Timer | 功能域自治代码 |
| `modules/keystone/dashboard/CalendarCard.qml` | **保留** | `keystone` | modules/keystone | 属性(7)/方法(2) | 无 | 功能域自治代码 |
| `modules/keystone/dashboard/DashboardClock.qml` | **保留** | `keystone` | modules/keystone | 属性(6)/方法(1) | Timer | 功能域自治代码 |
| `modules/keystone/dashboard/DashboardContent.qml` | **保留** | `keystone` | modules/keystone, modules/settings | 属性(10)/信号(2) | 无 | 功能域自治代码 |
| `modules/keystone/dashboard/DashboardPomodoroCard.qml` | **保留** | `keystone` | modules/keystone | 属性(4)/方法(2) | 无 | 功能域自治代码 |
| `modules/keystone/dashboard/DashboardWeatherCard.qml` | **保留** | `keystone` | modules/keystone | 属性(5)/方法(8) | Timer | 功能域自治代码 |
| `modules/keystone/dashboard/KeyholeCard.qml` | **保留** | `keystone` | modules/keystone | 属性(2) | 无 | 功能域自治代码 |
| `modules/keystone/dashboard/UserCard.qml` | **保留** | `keystone` | modules/keystone, modules/settings | 属性(6)/信号(1)/方法(2) | 无 | 功能域自治代码 |
| `modules/keystone/hub/HubContent.qml` | **保留** | `keystone` | modules/keystone | 属性(8)/信号(2)/方法(1) | 无 | 功能域自治代码 |
| `modules/keystone/media/CaelestiaCover.qml` | **保留** | `keystone` | modules/keystone | 属性(14) | 无 | 功能域自治代码 |
| `modules/keystone/media/MediaBackdrop.qml` | **保留** | `keystone` | modules/keystone | 属性(5) | 无 | 功能域自治代码 |
| `modules/keystone/media/MediaContent.qml` | **保留** | `keystone` | modules/keystone | 属性(20)/方法(3) | 无 | 功能域自治代码 |
| `modules/keystone/media/MediaCover.qml` | **保留** | `keystone` | modules/keystone | 属性(4) | 无 | 功能域自治代码 |
| `modules/keystone/media/MediaPalette.qml` | **移动** | `keystone` | modules/keystone, modules/settings | 属性(2)/方法(5) | Process, Timer | 已由 app/services/MediaPalette.qml 移动，遵循命名法典与内聚规范 |
| `modules/keystone/styles/bangs/Bangs.qml` | **保留** | `keystone` | app, modules/keystone | - | 无 | 功能域自治代码 |
| `modules/keystone/styles/long/Long.qml` | **保留** | `keystone` | app, modules/keystone, modules/settings, modules/sidebars | - | 无 | 功能域自治代码 |
| `modules/keystone/styles/long/LongIslandFrame.qml` | **保留** | `keystone` | modules/keystone | 属性(49)/信号(2)/方法(5) | 无 | 功能域自治代码 |
| `modules/keystone/styles/long/LongStatusBar.qml` | **保留** | `keystone` | modules/keystone | 属性(12)/信号(2) | 无 | 功能域自治代码 |
| `modules/keystone/styles/long/LongStatusItem.qml` | **保留** | `keystone` | modules/keystone | 属性(19)/信号(1)/方法(3) | 无 | 功能域自治代码 |
| `modules/keystone/styles/long/LongWorkspaces.qml` | **保留** | `keystone` | 内部/自包含 | 属性(4) | 无 | 功能域自治代码 |
| `modules/keystone/styles/pill/Pill.qml` | **保留** | `keystone` | app, modules/keystone, modules/settings, modules/systemcards, shared/controls, shared/theme | - | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/AudioRecordingVisual.qml` | **保留** | `keystone` | modules/keystone | 属性(10)/信号(3)/方法(2) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/AudioStopButton.qml` | **保留** | `keystone` | modules/keystone | 属性(2)/信号(1) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/AudioWaveform.qml` | **保留** | `keystone` | modules/keystone | 属性(17)/方法(7) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/BangsRecordingVisual.qml` | **保留** | `keystone` | modules/keystone | 属性(13)/信号(1) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/HorizontalPillRecordingVisual.qml` | **保留** | `keystone` | modules/keystone | 属性(27)/信号(1)/方法(4) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/PillMorphSurface.qml` | **保留** | `keystone` | modules/keystone | 属性(9) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/ProcessingSpiralIndicator.qml` | **保留** | `keystone` | modules/keystone | - | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/RecordingFormat.js` | **保留** | `keystone` | modules/keystone | 方法(1) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/VerticalPillRecordingVisual.qml` | **保留** | `keystone` | modules/keystone | 属性(27)/信号(1)/方法(4) | 无 | 功能域自治代码 |
| `modules/keystone/styles/recording/VerticalRecordingStatusLabel.qml` | **保留** | `keystone` | modules/keystone | 属性(4) | 无 | 功能域自治代码 |
| `modules/keystone/styles/shared/HorizontalKeystoneLayout.qml` | **保留** | `keystone` | modules/keystone | 属性(31) | 无 | 功能域自治代码 |
| `modules/keystone/styles/shared/KeyboardLockIndicator.qml` | **保留** | `keystone` | modules/keystone | 属性(5) | 无 | 功能域自治代码 |
| `modules/keystone/styles/shared/KeystoneHoverController.qml` | **保留** | `keystone` | modules/keystone | 属性(6)/信号(2)/方法(2) | Timer | 功能域自治代码 |
| `modules/keystone/styles/shared/KeystoneSurface.qml` | **保留** | `keystone` | modules/keystone | 属性(99)/信号(1)/方法(38) | Timer | 功能域自治代码 |
| `modules/keystone/styles/shared/VerticalKeystoneLayout.qml` | **保留** | `keystone` | modules/keystone | 属性(31) | 无 | 功能域自治代码 |
| `modules/keystone/tools/AudioRecordingService.qml` | **移动** | `keystone` | modules/keystone | 属性(28)/信号(2)/方法(5) | GatewayExec, Process, Timer | 已由 app/services/AudioRecordingService.qml 移动，遵循命名法典与内聚规范 |
| `modules/keystone/tools/RecordingService.qml` | **移动** | `keystone` | modules/keystone | 属性(24)/信号(3)/方法(7) | Process, Timer | 已由 app/services/RecordingService.qml 移动，遵循命名法典与内聚规范 |
| `modules/keystone/tools/ToolsContent.qml` | **保留** | `keystone` | modules/keystone | 属性(11)/信号(2)/方法(3) | GatewayExec | 功能域自治代码 |
| `modules/keystone/volume/VolumeContent.qml` | **保留** | `keystone` | modules/keystone | 属性(22)/信号(2)/方法(1) | 无 | 功能域自治代码 |
| `modules/keystone/weather/FrostedMapSurface.qml` | **保留** | `keystone` | 内部/自包含 | 属性(3) | 无 | 功能域自治代码 |
| `modules/keystone/weather/MapLegend.qml` | **保留** | `keystone` | 内部/自包含 | 属性(1)/方法(1) | 无 | 功能域自治代码 |
| `modules/keystone/weather/MoonIcon.qml` | **保留** | `keystone` | 内部/自包含 | 属性(1) | 无 | 功能域自治代码 |
| `modules/keystone/weather/WeatherAQIIndicator.qml` | **保留** | `keystone` | modules/keystone | 属性(1)/方法(3) | 无 | 功能域自治代码 |
| `modules/keystone/weather/WeatherContent.qml` | **保留** | `keystone` | modules/keystone | 属性(18)/方法(12) | Timer | 功能域自治代码 |
| `modules/keystone/weather/WeatherCurrent.qml` | **保留** | `keystone` | modules/keystone | 属性(6)/信号(1)/方法(3) | 无 | 功能域自治代码 |
| `modules/keystone/weather/WeatherFiveDayForecast.qml` | **保留** | `keystone` | modules/keystone | 属性(2)/方法(3) | 无 | 功能域自治代码 |
| `modules/keystone/weather/WeatherMoonPhase.qml` | **保留** | `keystone` | 内部/自包含 | 属性(4)/方法(3) | 无 | 功能域自治代码 |
| `modules/keystone/weather/WeatherParameters.qml` | **保留** | `keystone` | modules/keystone | 属性(6)/方法(3) | 无 | 功能域自治代码 |
| `modules/keystone/weather/WeatherSunriseSunset.qml` | **保留** | `keystone` | modules/keystone | 属性(3)/方法(2) | Timer | 功能域自治代码 |
| `modules/launcher/FileSearchService.qml` | **移动** | `launcher` | modules/launcher | 属性(27)/信号(1)/方法(9) | Process, Timer | 已由 app/services/FileSearchService.qml 移动，遵循命名法典与内聚规范 |
| `modules/launcher/LauncherHost.qml` | **保留** | `launcher` | app | 属性(5)/方法(6) | 无 | 功能域自治代码 |
| `modules/launcher/LauncherWindow.qml` | **保留** | `launcher` | modules/launcher | 属性(55)/方法(47) | Timer | 功能域自治代码 |
| `modules/launcher/SpotlightAppDrag.qml` | **保留** | `launcher` | modules/launcher | 属性(8)/方法(4) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightAppGrid.qml` | **保留** | `launcher` | modules/launcher | 属性(7)/信号(2) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightAppOrder.js` | **保留** | `launcher` | app, modules/launcher | 方法(9) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightAppProvider.qml` | **保留** | `launcher` | modules/launcher | 属性(5)/方法(6) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightClipboardDetails.qml` | **保留** | `launcher` | modules/launcher | 属性(19)/信号(2)/方法(7) | Timer | 功能域自治代码 |
| `modules/launcher/SpotlightClipboardProvider.qml` | **保留** | `launcher` | modules/launcher | 属性(9)/信号(3)/方法(28) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightCommandProvider.qml` | **保留** | `launcher` | modules/launcher | 属性(6) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightCommands.js` | **保留** | `launcher` | app, modules/launcher | 方法(6) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightConversionEditor.qml` | **保留** | `launcher` | modules/launcher | 属性(10)/信号(3)/方法(3) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightCurrency.js` | **保留** | `launcher` | modules/launcher | 方法(11) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightCurrencyController.qml` | **保留** | `launcher` | modules/launcher | 属性(16)/信号(1)/方法(10) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightFileProvider.qml` | **保留** | `launcher` | modules/launcher | 属性(5)/信号(1)/方法(4) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightLocalSearch.js` | **保留** | `launcher` | modules/launcher | 方法(16) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightModeMorphSurface.qml` | **保留** | `launcher` | modules/launcher | 属性(23)/方法(10) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightResultsPanel.qml` | **保留** | `launcher` | modules/launcher | 属性(68)/信号(11)/方法(6) | Timer | 功能域自治代码 |
| `modules/launcher/SpotlightSearch.js` | **保留** | `launcher` | app, modules/launcher | 方法(3) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightSearchBar.qml` | **保留** | `launcher` | modules/launcher | 属性(39)/信号(7)/方法(11) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightSearchProvider.qml` | **保留** | `launcher` | modules/launcher | 属性(8)/信号(3)/方法(12) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightSearchResults.qml` | **保留** | `launcher` | modules/launcher | 属性(11)/信号(2)/方法(3) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightSearchService.qml` | **移动** | `launcher` | modules/launcher | 属性(6)/方法(7) | Process, Timer | 已由 app/services/SpotlightSearchService.qml 移动，遵循命名法典与内聚规范 |
| `modules/launcher/SpotlightSearchTile.qml` | **保留** | `launcher` | modules/launcher | 属性(6)/信号(2) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightSession.js` | **保留** | `launcher` | modules/launcher | 方法(10) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightSessionController.qml` | **保留** | `launcher` | modules/launcher | 属性(14)/信号(5)/方法(9) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightStyle.qml` | **保留** | `launcher` | modules/launcher | 属性(74)/方法(3) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightTemplateController.qml` | **保留** | `launcher` | modules/launcher | 属性(21)/信号(2)/方法(12) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightTemplates.js` | **保留** | `launcher` | modules/launcher | 方法(2) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightToolPanel.qml` | **保留** | `launcher` | modules/launcher | 属性(12)/信号(1) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightToolResponse.js` | **保留** | `launcher` | modules/launcher | 方法(2) | 无 | 功能域自治代码 |
| `modules/launcher/SpotlightToolService.qml` | **移动** | `launcher` | modules/launcher | 属性(23)/方法(8) | Process, Timer | 已由 app/services/SpotlightToolService.qml 移动，遵循命名法典与内聚规范 |
| `modules/launcher/SpotlightWallpaperProvider.qml` | **保留** | `launcher` | modules/launcher | 属性(8)/方法(6) | 无 | 功能域自治代码 |
| `modules/lock/CaelestiaLock.qml` | **保留** | `lock` | modules/lock | 属性(19)/方法(6) | IPC/Wayland | 功能域自治代码 |
| `modules/lock/DefaultLock.qml` | **保留** | `lock` | modules/lock | 属性(12)/方法(2) | IPC/Wayland | 功能域自治代码 |
| `modules/lock/DefaultLockContent.qml` | **保留** | `lock` | modules/lock | 属性(17)/方法(3) | Timer | 功能域自治代码 |
| `modules/lock/DefaultLockStatus.qml` | **保留** | `lock` | modules/lock | 属性(8)/方法(2) | 无 | 功能域自治代码 |
| `modules/lock/Lock.qml` | **保留** | `lock` | app, modules/keystone, modules/lock, modules/session, modules/settings, modules/sidebars, packaging, shared/theme | 属性(9)/信号(4)/方法(5) | IPC/Wayland | 功能域自治代码 |
| `modules/lock/LockContent.qml` | **保留** | `lock` | modules/lock | 属性(17)/方法(6) | Timer | 功能域自治代码 |
| `modules/lock/LockContext.qml` | **保留** | `lock` | 内部/自包含 | 属性(3)/信号(2)/方法(1) | 无 | 功能域自治代码 |
| `modules/lock/LockSurface.qml` | **保留** | `lock` | modules/lock | 属性(3) | IPC/Wayland | 功能域自治代码 |
| `modules/lock/PreLockCapture.qml` | **保留** | `lock` | modules/lock | 属性(11)/信号(3)/方法(13) | Process, Timer, IPC/Wayland | 功能域自治代码 |
| `modules/lock/README.md` | **保留** | `lock` | modules/keystone, modules/settings, modules/wallpaper, packaging, shared/utils | - | 无 | 功能域自治代码 |
| `modules/lock/cards/AuthCard.qml` | **保留** | `lock` | modules/lock | 属性(12)/信号(1)/方法(2) | 无 | 功能域自治代码 |
| `modules/lock/cards/LockFetchCard.qml` | **保留** | `lock` | modules/lock | 属性(20)/方法(2) | 无 | 功能域自治代码 |
| `modules/lock/cards/MediaCard.qml` | **保留** | `lock` | modules/lock | 属性(14)/信号(1) | 无 | 功能域自治代码 |
| `modules/lock/cards/MottoCard.qml` | **保留** | `lock` | 内部/自包含 | - | 无 | 功能域自治代码 |
| `modules/lock/cards/NotificationCard.qml` | **保留** | `lock` | modules/lock | 属性(6)/方法(2) | 无 | 功能域自治代码 |
| `modules/lock/cards/SystemGrid.qml` | **保留** | `lock` | modules/bar, modules/lock | 属性(9) | 无 | 功能域自治代码 |
| `modules/lock/cards/WeatherCard.qml` | **保留** | `lock` | modules/lock | 属性(21)/方法(5) | Timer | 功能域自治代码 |
| `modules/lock/pam/password.conf` | **保留** | `lock` | app, modules/lock, modules/sidebars, shared/controls | - | 无 | 功能域自治代码 |
| `modules/notifications/NotificationContent.qml` | **保留** | `notifications` | modules/keystone, modules/notifications | 属性(7)/方法(2) | 无 | 功能域自治代码 |
| `modules/notifications/NotificationPopupHost.qml` | **保留** | `notifications` | app | 属性(7) | 无 | 功能域自治代码 |
| `modules/quicksettings/QuickSettingsSurface.qml` | **保留** | `quicksettings` | modules/sidebars | 属性(21)/方法(13) | 无 | 功能域自治代码 |
| `modules/quicksettings/QuickSliders.qml` | **保留** | `quicksettings` | modules/quicksettings | 属性(10) | 无 | 功能域自治代码 |
| `modules/quicksettings/QuickToggleConfig.qml` | **移动** | `quicksettings` | modules/quicksettings | 属性(4)/方法(7) | Process, FileView | 已由 app/services/QuickToggleConfig.qml 移动，遵循命名法典与内聚规范 |
| `modules/regionselector/RegionSelectionWindow.qml` | **保留** | `regionselector` | modules/regionselector | 属性(15)/方法(2) | 无 | 功能域自治代码 |
| `modules/regionselector/RegionSelector.qml` | **保留** | `regionselector` | app | 属性(1) | 无 | 功能域自治代码 |
| `modules/session/SessionHost.qml` | **保留** | `session` | app | 属性(3)/信号(1)/方法(6) | 无 | 功能域自治代码 |
| `modules/session/SessionPanel.qml` | **保留** | `session` | modules/session | 属性(7)/信号(3)/方法(2) | 无 | 功能域自治代码 |
| `modules/settings/AccountPage.qml` | **保留** | `settings` | modules/settings, modules/sidebars | 属性(14)/信号(1)/方法(8) | 无 | 功能域自治代码 |
| `modules/settings/AddNetworkPage.qml` | **保留** | `settings` | modules/settings | 属性(6)/信号(1)/方法(4) | 无 | 功能域自治代码 |
| `modules/settings/AdvancedPage.qml` | **删除** | `settings` | - | - | - | R8 架构扁平化：Matugen 模板管理并入 ThemePage.qml，路由重定向 |
| `modules/settings/AppBrowserPopup.qml` | **保留** | `settings` | modules/settings | 属性(8)/信号(1)/方法(7) | 无 | 功能域自治代码 |
| `modules/settings/AutostartPage.qml` | **保留** | `settings` | modules/settings | 属性(4)/方法(5) | 无 | 功能域自治代码 |
| `modules/settings/AutostartService.qml` | **移动** | `settings` | modules/settings | 属性(18)/信号(1)/方法(29) | Process, FileView | 已由 app/services/AutostartService.qml 移动，遵循命名法典与内聚规范 |
| `modules/settings/BarLayoutDragCoordinator.qml` | **保留** | `settings` | modules/settings | 属性(12)/信号(1)/方法(7) | 无 | 功能域自治代码 |
| `modules/settings/BezierCurveEditor.qml` | **保留** | `settings` | modules/settings | 属性(26)/信号(2)/方法(42) | GatewayExec | 功能域自治代码 |
| `modules/settings/BezierCurveLayerEditor.qml` | **保留** | `settings` | modules/settings | 属性(48)/信号(3)/方法(45) | GatewayExec | 功能域自治代码 |
| `modules/settings/BluetoothDevicePage.qml` | **保留** | `settings` | modules/settings | 属性(6)/信号(1)/方法(4) | 无 | 功能域自治代码 |
| `modules/settings/BluetoothPairingPage.qml` | **保留** | `settings` | modules/settings | 属性(5)/信号(1)/方法(6) | 无 | 功能域自治代码 |
| `modules/settings/ClockSliderSetting.qml` | **保留** | `settings` | modules/settings | 属性(9)/信号(2) | 无 | 功能域自治代码 |
| `modules/settings/ConnectedDevicesPage.qml` | **保留** | `settings` | modules/settings | 属性(4)/信号(2)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/ControlCenterWindow.qml` | **保留** | `settings` | app, modules/settings | 属性(16)/信号(1)/方法(14) | Timer | 功能域自治代码 |
| `modules/settings/CursorThemeSelect.qml` | **保留** | `settings` | modules/settings | 属性(3)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/DefaultAppsPage.qml` | **保留** | `settings` | modules/settings | 属性(9) | 无 | 功能域自治代码 |
| `modules/settings/DisplayAdvancedSettings.qml` | **保留** | `settings` | modules/settings | 属性(3)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/DisplayChoice.qml` | **保留** | `settings` | modules/settings | 属性(3)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/DisplayColumnWidths.qml` | **保留** | `settings` | modules/settings | 属性(5)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/DisplayConfigService.qml` | **移动** | `settings` | modules/settings | 属性(20)/方法(14) | Process, Timer | 已由 app/services/DisplayConfigService.qml 移动，遵循命名法典与内聚规范 |
| `modules/settings/DisplayConfiguration.js` | **保留** | `settings` | modules/settings | 方法(13) | 无 | 功能域自治代码 |
| `modules/settings/DisplayConfigurationPage.qml` | **保留** | `settings` | modules/settings | 属性(8)/方法(7) | 无 | 功能域自治代码 |
| `modules/settings/DisplayHotCornerSettings.qml` | **保留** | `settings` | modules/settings | 属性(6) | 无 | 功能域自治代码 |
| `modules/settings/DisplayLayoutCanvas.qml` | **保留** | `settings` | modules/settings | 属性(14)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/DisplayOverlays.qml` | **保留** | `settings` | app | 属性(1) | 无 | 功能域自治代码 |
| `modules/settings/DisplaySchedule.js` | **保留** | `settings` | app | 方法(4) | 无 | 功能域自治代码 |
| `modules/settings/DisplaysPage.qml` | **保留** | `settings` | modules/settings | 属性(5)/方法(2) | 无 | 功能域自治代码 |
| `modules/settings/DockPage.qml` | **保留** | `settings` | modules/settings | - | 无 | 功能域自治代码 |
| `modules/settings/EdgePositionSelector.qml` | **保留** | `settings` | modules/settings | 属性(1)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/FloatingActionButton.qml` | **保留** | `settings` | modules/settings | 属性(5)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/GammaControlPage.qml` | **保留** | `settings` | modules/settings, modules/sidebars | 属性(5)/方法(2) | 无 | 功能域自治代码 |
| `modules/settings/GeneralBarPage.qml` | **保留** | `settings` | modules/settings | 属性(1) | 无 | 功能域自治代码 |
| `modules/settings/GeneralEffectsPage.qml` | **删除** | `settings` | - | - | - | 合并入 ThemePage（透明与模糊分组合并至主题设置） |
| `modules/settings/GeneralOverviewPage.qml` | **删除** | `settings` | - | - | - | R8 架构扁平化：平铺至 16 个一级分类，移除概览中间层 |
| `modules/settings/GeneralPage.qml` | **删除** | `settings` | - | - | - | R8 架构扁平化：拆解为独立一级路由，移除多层嵌套容器 |
| `modules/settings/GeneralSidebarPage.qml` | **保留** | `settings` | modules/settings | 属性(5)/方法(3) | 无 | 功能域自治代码 |
| `modules/settings/GeneralSliderSetting.qml` | **保留** | `settings` | modules/settings | 属性(7)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/GeneralSubpageHeader.qml` | **保留** | `settings` | modules/settings | 属性(3)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/HorizontalClockPage.qml` | **保留** | `settings` | modules/settings | 属性(8)/方法(5) | 无 | 功能域自治代码 |
| `modules/settings/HorizontalClockPreview.qml` | **保留** | `settings` | modules/settings | 属性(9) | 无 | 功能域自治代码 |
| `modules/settings/KeystonePage.qml` | **保留** | `settings` | modules/settings | 属性(16)/信号(1)/方法(7) | 无 | 功能域自治代码 |
| `modules/settings/KeystoneSection.qml` | **保留** | `settings` | modules/settings | 属性(3) | 无 | 功能域自治代码 |
| `modules/settings/LanguageAndRegionPage.qml` | **保留** | `settings` | modules/settings | 属性(2)/信号(1)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/LocationPicker.qml` | **保留** | `settings` | modules/settings | 属性(6)/方法(9) | 无 | 功能域自治代码 |
| `modules/settings/MatugenTemplateAddWindow.qml` | **保留** | `settings` | modules/settings | 属性(3)/方法(3) | 无 | 功能域自治代码 |
| `modules/settings/MiniMaterialWaveLine.qml` | **保留** | `settings` | modules/settings | 属性(17)/方法(3) | 无 | 功能域自治代码 |
| `modules/settings/NavigationRailButton.qml` | **保留** | `settings` | modules/settings | 属性(12) | 无 | 功能域自治代码 |
| `modules/settings/NavigationRailExpandButton.qml` | **保留** | `settings` | modules/settings | 属性(1)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/NavigationRailTabArray.qml` | **保留** | `settings` | modules/settings | 属性(7)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/NetworkConfigWindow.qml` | **保留** | `settings` | modules/settings | 属性(4)/方法(5) | 无 | 功能域自治代码 |
| `modules/settings/NetworkPage.qml` | **保留** | `settings` | modules/settings | 属性(17)/方法(13) | Timer | 功能域自治代码 |
| `modules/settings/NetworkProfileEditor.qml` | **保留** | `settings` | modules/settings | 属性(25)/信号(1)/方法(9) | 无 | 功能域自治代码 |
| `modules/settings/NiriActionNames.js` | **保留** | `settings` | modules/settings | 方法(2) | 无 | 功能域自治代码 |
| `modules/settings/ProfileBannerEditor.qml` | **保留** | `settings` | modules/settings | 属性(3)/方法(4) | 无 | 功能域自治代码 |
| `modules/settings/SavedNetworksPage.qml` | **保留** | `settings` | modules/settings | 属性(4)/信号(1) | 无 | 功能域自治代码 |
| `modules/settings/SettingsBackend.qml` | **保留** | `settings` | modules/settings | 属性(11)/方法(15) | GatewayExec, Timer | 功能域自治代码 |
| `modules/settings/SettingsHost.qml` | **保留** | `settings` | app, modules/settings | 属性(5)/方法(9) | 无 | 功能域自治代码 |
| `modules/settings/SettingsPageHost.qml` | **保留** | `settings` | modules/settings | 属性(16)/信号(1)/方法(3) | 无 | 功能域自治代码 |
| `modules/settings/SettingsPanelStyleCard.qml` | **保留** | `settings` | modules/settings | 属性(3) | 无 | 功能域自治代码 |
| `modules/settings/SettingsSearchAnchor.qml` | **保留** | `settings` | modules/settings | 属性(7)/方法(7) | Timer | 功能域自治代码 |
| `modules/settings/ShortcutKeySymbols.js` | **保留** | `settings` | modules/settings | 方法(1) | 无 | 功能域自治代码 |
| `modules/settings/ShortcutKeycap.qml` | **保留** | `settings` | modules/settings | 属性(5) | 无 | 功能域自治代码 |
| `modules/settings/ShortcutMap.qml` | **保留** | `settings` | app | 属性(10)/信号(1)/方法(3) | 无 | 功能域自治代码 |
| `modules/settings/ShortcutsPage.qml` | **保留** | `settings` | modules/settings | 属性(30)/信号(4)/方法(22) | 无 | 功能域自治代码 |
| `modules/settings/SpotlightPage.qml` | **保留** | `settings` | modules/settings | 方法(1) | 无 | 功能域自治代码 |
| `modules/settings/ThemePage.qml` | **保留** | `settings` | modules/settings | 属性(34)/信号(4)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/WallpaperColorPicker.qml` | **保留** | `settings` | modules/settings, modules/sidebars | 属性(5)/方法(4) | 无 | 功能域自治代码 |
| `modules/settings/WallpaperFileBrowser.qml` | **保留** | `settings` | modules/settings | 信号(2) | 无 | 功能域自治代码 |
| `modules/settings/WallpaperPage.qml` | **保留** | `settings` | modules/settings, shared/controls | 属性(34)/信号(6)/方法(6) | 无 | 功能域自治代码 |
| `modules/settings/WeatherMapBridge.qml` | **保留** | `settings` | 内部/自包含 | 属性(8)/信号(1)/方法(4) | 无 | 功能域自治代码 |
| `modules/settings/WeatherServiceApiKeyCard.qml` | **保留** | `settings` | 内部/自包含 | 属性(16)/方法(4) | 无 | 功能域自治代码 |
| `modules/settings/WizardHeader.qml` | **保留** | `settings` | modules/settings | 属性(4)/信号(2) | 无 | 功能域自治代码 |
| `modules/settings/ZenPaletteEditor.qml` | **保留** | `settings` | modules/settings | 属性(24)/信号(1)/方法(5) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/Dashboard.qml` | **保留** | `settings` | app, modules/keystone, modules/settings | 属性(5)/信号(1)/方法(5) | Timer | 功能域自治代码 |
| `modules/settings/dashboard/DashboardComboCard.qml` | **保留** | `settings` | modules/settings | 属性(8) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardContent.qml` | **保留** | `settings` | modules/keystone, modules/settings | 属性(33)/信号(3)/方法(10) | Timer | 功能域自治代码 |
| `modules/settings/dashboard/DashboardHomePage.qml` | **保留** | `settings` | modules/settings | 属性(29)/方法(3) | Timer | 功能域自治代码 |
| `modules/settings/dashboard/DashboardLyricsPane.qml` | **保留** | `settings` | modules/settings | 属性(11)/方法(6) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardMediaPage.qml` | **保留** | `settings` | modules/settings | 属性(11)/方法(2) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardMediaState.qml` | **保留** | `settings` | modules/settings | 属性(5)/方法(2) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardPaletteCard.qml` | **保留** | `settings` | modules/settings | 属性(16) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardSelectCard.qml` | **保留** | `settings` | modules/settings | 属性(9) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardSettingsCatalog.qml` | **保留** | `settings` | modules/settings | 属性(2)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardSettingsPage.qml` | **保留** | `settings` | modules/settings | 属性(19)/方法(9) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardSliderCard.qml` | **保留** | `settings` | modules/settings | 属性(10) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardSpinCard.qml` | **保留** | `settings` | modules/settings | 属性(8)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardStyleCard.qml` | **保留** | `settings` | modules/settings | 属性(8) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardTextCard.qml` | **保留** | `settings` | modules/settings | 属性(8) | Timer | 功能域自治代码 |
| `modules/settings/dashboard/DashboardThemesPage.qml` | **保留** | `settings` | modules/settings | 属性(11)/方法(1) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardToggleCard.qml` | **保留** | `settings` | modules/settings | 属性(7) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardWallpaperToolsCard.qml` | **保留** | `settings` | modules/settings | 属性(4)/信号(2) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/DashboardWallpapersPage.qml` | **保留** | `settings` | modules/settings | 属性(13)/方法(4) | Timer | 功能域自治代码 |
| `modules/settings/dashboard/SettingsControlCatalog.qml` | **保留** | `settings` | modules/settings | 属性(1)/方法(6) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/WeatherIcons.js` | **保留** | `settings` | modules/settings | 方法(1) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/lyrics/LyricsBackend.qml` | **保留** | `settings` | modules/keystone, modules/settings | 属性(3)/信号(3)/方法(4) | Process, Timer | 功能域自治代码 |
| `modules/settings/dashboard/lyrics/LyricsParser.js` | **保留** | `settings` | modules/settings | 方法(16) | 无 | 功能域自治代码 |
| `modules/settings/dashboard/lyrics/LyricsService.qml` | **保留** | `settings` | modules/settings | 属性(23)/方法(11) | Timer | 功能域自治代码 |
| `modules/settings/dashboard/qmldir` | **保留** | `settings` | 内部/自包含 | - | 无 | 功能域自治代码 |
| `modules/settings/generated/SearchCatalog.js` | **保留** | `settings` | app | 方法(2) | 无 | 功能域自治代码 |
| `modules/settings/settings-routes.json` | **保留** | `settings` | 内部/自包含 | - | 无 | 功能域自治代码 |
| `modules/sidebars/SidebarHostWindow.qml` | **保留** | `sidebars` | app, modules/desktopcards | 属性(7)/方法(13) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/DailyAirQualityTrendPane.qml` | **保留** | `sidebars` | modules/sidebars | 属性(17)/方法(15) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/DailyForecastTrendCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(29)/方法(24) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/DailyWindTrendPane.qml` | **保留** | `sidebars` | modules/sidebars | 属性(18)/方法(13) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/DashboardSidebar.qml` | **保留** | `sidebars` | modules/sidebars | 属性(17)/信号(1)/方法(6) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/DashboardSidebarContent.qml` | **保留** | `sidebars` | modules/sidebars | 属性(23)/信号(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/DrawerView.qml` | **保留** | `sidebars` | modules/desktopcards, modules/sidebars | 属性(23)/方法(20) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/HourlyAirQualityTrendPane.qml` | **保留** | `sidebars` | modules/sidebars | 属性(19)/方法(15) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/HourlyForecastTrendCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(21)/方法(19) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/HourlyWindTrendPane.qml` | **保留** | `sidebars` | modules/sidebars | 属性(16)/方法(13) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/InfoView.qml` | **保留** | `sidebars` | modules/sidebars | 属性(3)/信号(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/ProfileHeaderCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(1)/信号(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherAnimatedValue.qml` | **保留** | `sidebars` | modules/sidebars | 属性(8)/方法(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherAqiCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(5) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherArcGauge.qml` | **保留** | `sidebars` | modules/sidebars | 属性(7)/方法(3) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherAstroCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(18)/方法(18) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherBlob.qml` | **保留** | `sidebars` | modules/sidebars | 属性(8)/方法(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherChartMath.js` | **保留** | `sidebars` | modules/sidebars | 方法(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherHumidityCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(6)/方法(7) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherInsightCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(8) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherMetricCard.qml` | **保留** | `sidebars` | 内部/自包含 | 属性(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherMetricMenu.qml` | **保留** | `sidebars` | modules/sidebars | 属性(4)/信号(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherMetricTrendPane.qml` | **保留** | `sidebars` | modules/sidebars | 属性(26)/方法(25) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherPrecipitationCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(11)/方法(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherPressureCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(6)/方法(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherRevealCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(23)/方法(3) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherTemperatureNormalLine.qml` | **保留** | `sidebars` | modules/sidebars | 属性(10) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherTrendChart.qml` | **保留** | `sidebars` | 内部/自包含 | 属性(4)/方法(12) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherUvCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(5) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherView.qml` | **保留** | `sidebars` | modules/sidebars | 属性(18)/方法(29) | Timer | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherVisibilityCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(3)/方法(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WeatherWindCard.qml` | **保留** | `sidebars` | modules/sidebars | 属性(15)/方法(6) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/WindDirectionGlyph.qml` | **保留** | `sidebars` | modules/sidebars | 属性(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/drawer/DrawerGridLayout.js` | **保留** | `sidebars` | app, modules/sidebars, modules/systemcards | 方法(16) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/drawer/DrawerGridTile.qml` | **保留** | `sidebars` | modules/sidebars | 属性(6)/信号(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/drawer/SystemLoadingState.qml` | **保留** | `sidebars` | modules/sidebars | 属性(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/drawer/SystemUnavailableState.qml` | **保留** | `sidebars` | modules/sidebars | 属性(3)/信号(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/CalendarLayout.js` | **重命名** | `sidebars` | modules/sidebars | 方法(2) | 无 | 已由 modules/sidebars/dashboard/infotools/calendar_layout.js 重命名，遵循命名法典与内聚规范 |
| `modules/sidebars/dashboard/infotools/CalendarWidget.qml` | **保留** | `sidebars` | modules/sidebars | 属性(15)/方法(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/InfoDrawerState.qml` | **移动** | `sidebars` | modules/sidebars | 属性(16)/方法(8) | Process, Timer, FileView | 已由 app/services/InfoDrawerState.qml 移动，遵循命名法典与内聚规范 |
| `modules/sidebars/dashboard/infotools/InfoToolDrawer.qml` | **保留** | `sidebars` | modules/sidebars | 属性(11)/方法(5) | Timer | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/PomodoroTimer.qml` | **保留** | `sidebars` | modules/sidebars | - | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/Stopwatch.qml` | **保留** | `sidebars` | modules/sidebars | 属性(6)/方法(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/TaskList.qml` | **保留** | `sidebars` | modules/sidebars | 属性(9) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/TimerService.qml` | **移动** | `sidebars` | modules/keystone, modules/sidebars | 属性(14)/方法(17) | GatewayExec, Timer | 已由 app/services/TimerService.qml 移动，遵循命名法典与内聚规范 |
| `modules/sidebars/dashboard/infotools/TimerWidget.qml` | **保留** | `sidebars` | modules/sidebars | 属性(3)/方法(2) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/TodoService.qml` | **移动** | `sidebars` | app, modules/settings, modules/sidebars | 属性(5)/方法(7) | Process, FileView | 已由 app/services/TodoService.qml 移动，遵循命名法典与内聚规范 |
| `modules/sidebars/dashboard/infotools/TodoWidget.qml` | **保留** | `sidebars` | modules/sidebars | 属性(7)/方法(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/ToolSecondaryTabBar.qml` | **保留** | `sidebars` | modules/sidebars | 属性(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/infotools/ToolSecondaryTabButton.qml` | **保留** | `sidebars` | modules/sidebars | 属性(3) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/DragManager.qml` | **保留** | `sidebars` | modules/sidebars | 属性(10)/信号(1)/方法(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationActionButton.qml` | **保留** | `sidebars` | modules/sidebars | 属性(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationAppIcon.qml` | **保留** | `sidebars` | modules/sidebars | - | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationCenterCard.qml` | **保留** | `sidebars` | 内部/自包含 | - | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationGroup.qml` | **保留** | `sidebars` | modules/sidebars | 属性(23)/方法(4) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationGroupExpandButton.qml` | **保留** | `sidebars` | modules/sidebars | 属性(3) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationItem.qml` | **保留** | `sidebars` | modules/sidebars | 属性(18)/信号(1)/方法(3) | Timer | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationList.qml` | **保留** | `sidebars` | modules/sidebars | 属性(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationListView.qml` | **保留** | `sidebars` | modules/sidebars | 属性(5)/方法(1) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationStatusButton.qml` | **保留** | `sidebars` | modules/sidebars | 属性(7) | 无 | 功能域自治代码 |
| `modules/sidebars/dashboard/notifications/NotificationUtils.qml` | **保留** | `sidebars` | modules/sidebars | 方法(2) | 无 | 功能域自治代码 |
| `modules/sidebars/quicksettings/AudioContent.qml` | **保留** | `sidebars` | modules/sidebars | 属性(6) | 无 | 功能域自治代码 |
| `modules/sidebars/quicksettings/BluetoothContent.qml` | **保留** | `sidebars` | modules/sidebars | 属性(20)/方法(9) | Timer | 功能域自治代码 |
| `modules/sidebars/quicksettings/IdleContent.qml` | **保留** | `sidebars` | modules/sidebars | 属性(11)/方法(2) | Timer | 功能域自治代码 |
| `modules/sidebars/quicksettings/MicrophoneContent.qml` | **保留** | `sidebars` | modules/sidebars | 属性(4) | 无 | 功能域自治代码 |
| `modules/sidebars/quicksettings/NetworkContent.qml` | **保留** | `sidebars` | modules/sidebars | 属性(28)/方法(10) | Timer | 功能域自治代码 |
| `modules/sidebars/quicksettings/NightModeContent.qml` | **保留** | `sidebars` | modules/sidebars | - | 无 | 功能域自治代码 |
| `modules/sidebars/quicksettings/QuickSettings.qml` | **保留** | `sidebars` | modules/bar, modules/sidebars | 属性(13)/方法(1) | 无 | 功能域自治代码 |
| `modules/sidebars/quicksettings/QuickSettingsSidebar.qml` | **保留** | `sidebars` | modules/sidebars | 属性(11)/方法(6) | 无 | 功能域自治代码 |
| `modules/sidebars/quicksettings/SettingsContent.qml` | **保留** | `sidebars` | modules/sidebars | - | 无 | 功能域自治代码 |
| `modules/systemcards/ExpressiveMetricTile.qml` | **保留** | `systemcards` | modules/systemcards | 属性(16) | 无 | 功能域自治代码 |
| `modules/systemcards/NetworkInterfaceHistoryService.qml` | **移动** | `systemcards` | modules/systemcards | 属性(3)/方法(6) | 无 | 已由 app/services/NetworkInterfaceHistoryService.qml 移动，遵循命名法典与内聚规范 |
| `modules/systemcards/SidebarCookieClock.qml` | **保留** | `systemcards` | modules/systemcards | 属性(10) | Timer | 功能域自治代码 |
| `modules/systemcards/SystemBatteryTank.qml` | **保留** | `systemcards` | modules/systemcards | 属性(12)/方法(3) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemCalendarCard.qml` | **保留** | `systemcards` | modules/systemcards | 属性(6) | Timer | 功能域自治代码 |
| `modules/systemcards/SystemCardCatalog.js` | **保留** | `systemcards` | app, modules/systemcards | 方法(7) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemCardContent.qml` | **保留** | `systemcards` | modules/desktopcards, modules/sidebars | 属性(15)/信号(2)/方法(8) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemCardGeometry.js` | **保留** | `systemcards` | app, modules/desktopcards, modules/sidebars | 方法(5) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemCardGrid.js` | **保留** | `systemcards` | modules/desktopcards, modules/sidebars, modules/systemcards | 方法(5) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemCardGridGuides.qml` | **保留** | `systemcards` | modules/desktopcards, modules/sidebars | 属性(1) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemCardPlacement.js` | **保留** | `systemcards` | modules/desktopcards, modules/sidebars, modules/systemcards | 方法(12) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemCardState.js` | **保留** | `systemcards` | app | 方法(27) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemClockCard.qml` | **保留** | `systemcards` | modules/systemcards | 属性(16)/方法(1) | Timer | 功能域自治代码 |
| `modules/systemcards/SystemLiquidMetricCard.qml` | **保留** | `systemcards` | modules/systemcards | 属性(11) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemNetworkCard.qml` | **保留** | `systemcards` | modules/systemcards | 属性(21)/信号(1) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemSparkline.qml` | **保留** | `systemcards` | modules/systemcards | 属性(16)/方法(4) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemStorageCard.qml` | **保留** | `systemcards` | modules/systemcards | 属性(18)/信号(1) | 无 | 功能域自治代码 |
| `modules/systemcards/SystemWeatherCard.qml` | **保留** | `systemcards` | modules/systemcards | 属性(3) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/BigHourNumbers.qml` | **保留** | `systemcards` | modules/systemcards | 属性(3) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/BubbleDate.qml` | **保留** | `systemcards` | modules/systemcards | 属性(4) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/CookieBody.qml` | **保留** | `systemcards` | modules/systemcards | 属性(3) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/CookieFace.qml` | **保留** | `systemcards` | modules/systemcards | 属性(4) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/DateIndicator.qml` | **保留** | `systemcards` | modules/systemcards | 属性(6) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/Dots.qml` | **保留** | `systemcards` | modules/settings, modules/systemcards | 属性(3) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/HourHand.qml` | **保留** | `systemcards` | modules/systemcards | 属性(6) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/HourMarks.qml` | **保留** | `systemcards` | modules/systemcards | 属性(4) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/Lines.qml` | **保留** | `systemcards` | modules/launcher, modules/systemcards | 属性(7) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/MinuteHand.qml` | **保留** | `systemcards` | modules/systemcards | 属性(4) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/MinuteMarks.qml` | **保留** | `systemcards` | modules/systemcards | 属性(1) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/RectangleDate.qml` | **保留** | `systemcards` | modules/systemcards | 属性(1) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/RotatingDate.qml` | **保留** | `systemcards` | modules/systemcards | 属性(7) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/SecondHand.qml` | **保留** | `systemcards` | modules/systemcards | 属性(6) | 无 | 功能域自治代码 |
| `modules/systemcards/cookieclock/TimeColumn.qml` | **保留** | `systemcards` | modules/systemcards | 属性(10) | 无 | 功能域自治代码 |
| `modules/wallpaper/AwwwWallpaperService.qml` | **移动** | `wallpaper` | modules/settings, modules/wallpaper | 属性(24)/方法(21) | Process, Timer, Env | 已由 app/services/AwwwWallpaperService.qml 移动，遵循命名法典与内聚规范 |
| `modules/wallpaper/DesktopWallpaper.qml` | **保留** | `wallpaper` | modules/wallpaper | 属性(5) | 无 | 功能域自治代码 |
| `modules/wallpaper/OverviewWallpaper.qml` | **保留** | `wallpaper` | modules/wallpaper | 属性(6)/方法(1) | 无 | 功能域自治代码 |
| `modules/wallpaper/ProfileWallpaper.qml` | **保留** | `wallpaper` | modules/settings, modules/sidebars | 属性(3) | 无 | 功能域自治代码 |
| `modules/wallpaper/WallpaperBackground.qml` | **保留** | `wallpaper` | app | - | 无 | 功能域自治代码 |
| `modules/wallpaper/WallpaperImageViewport.qml` | **保留** | `wallpaper` | modules/lock, modules/settings, modules/wallpaper | 属性(19)/信号(1)/方法(3) | 无 | 功能域自治代码 |
| `modules/wallpaper/WallpaperPaletteSession.qml` | **移动** | `wallpaper` | modules/settings, modules/sidebars, modules/wallpaper | 属性(11)/信号(1)/方法(7) | 无 | 已由 app/services/WallpaperPaletteSession.qml 移动，遵循命名法典与内聚规范 |
| `modules/wallpaper/WallpaperSceneService.qml` | **移动** | `wallpaper` | modules/desktopcards, modules/wallpaper | 属性(48)/方法(15) | 无 | 已由 app/services/WallpaperSceneService.qml 移动，遵循命名法典与内聚规范 |
| `modules/wallpaper/WallpaperService.qml` | **移动** | `wallpaper` | app, modules/desktopcards, modules/launcher, modules/lock, modules/settings, modules/sidebars, modules/wallpaper | 属性(25)/方法(85) | Process, Timer | 已由 app/services/WallpaperService.qml 移动，遵循命名法典与内聚规范 |
| `modules/wallpaper/WallpaperTransitionSurface.qml` | **保留** | `wallpaper` | modules/wallpaper | 属性(119)/信号(1)/方法(11) | Timer | 功能域自治代码 |
| `modules/wallpaper/ZenPaletteRenderer.qml` | **保留** | `wallpaper` | modules/settings, modules/wallpaper | 属性(6) | 无 | 功能域自治代码 |

### shared/ （共 125 文件）

| 文件路径 | 处置状态 | 归属 (Owner) | 消费者 (Consumers) | I/O | 副作用 | 目标路径 / 说明 |
|---|---|---|---|---|---|---|
| `shared/controls/AccountProfileHeader.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars | 属性(20)/信号(5)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ActionButton.qml` | **保留** | `shared/controls` | modules/launcher, modules/settings, modules/sidebars, shared/controls | 属性(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ApplicationVolumeRow.qml` | **保留** | `shared/controls` | 内部/自包含 | 属性(5)/信号(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ArcGauge.qml` | **保留** | `shared/controls` | modules/bar | 属性(13) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/AttachedEdgeCurve.qml` | **保留** | `shared/controls` | modules/dock, modules/keystone | 属性(7)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/BarActionButton.qml` | **保留** | `shared/controls` | modules/bar, shared/controls | 属性(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/BarCircularButton.qml` | **保留** | `shared/controls` | modules/bar | 属性(12)/信号(4) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/BarLabelButton.qml` | **保留** | `shared/controls` | modules/bar | 属性(9)/信号(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/BluetoothDeviceIcon.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars | 方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/BrailleSpinner.qml` | **保留** | `shared/controls` | modules/keystone, shared/controls | 属性(10)/方法(1) | Timer | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ButtonLabel.qml` | **保留** | `shared/controls` | modules/settings, shared/controls | 属性(10) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/CircularProgress.qml` | **保留** | `shared/controls` | modules/settings | 属性(14) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/CompositorBlurRegion.qml` | **保留** | `shared/controls` | modules/bar, modules/desktopcards, modules/dock, modules/filepicker, modules/keystone, modules/launcher, modules/notifications, modules/session, modules/settings, modules/sidebars, shared/controls | 属性(24)/方法(14) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/DashboardCard.qml` | **保留** | `shared/controls` | modules/settings | 属性(12)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/EdgeRevealSurface.qml` | **保留** | `shared/controls` | modules/sidebars | 属性(5)/信号(1)/方法(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ElementMoveAnimation.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars, shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/FileThemeIcon.qml` | **保留** | `shared/controls` | modules/dock, modules/launcher | 属性(17)/方法(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/FlipCard.qml` | **保留** | `shared/controls` | modules/settings | 信号(1)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/HotCornerExclusionRegion.qml` | **保留** | `shared/controls` | modules/bar, modules/keystone, modules/sidebars | 属性(8)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/IconButton.qml` | **保留** | `shared/controls` | modules/bar, modules/dock, modules/keystone, modules/launcher, modules/lock, modules/settings, modules/sidebars, shared/controls | 属性(15) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/InlineBusyIndicator.qml` | **保留** | `shared/controls` | modules/dock, modules/lock, modules/settings | 属性(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/InlineStatusBanner.qml` | **保留** | `shared/controls` | modules/dock, modules/settings, modules/sidebars, shared/controls | 属性(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/LeafItem.qml` | **保留** | `shared/controls` | shared/controls | 属性(15)/信号(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ListPagination.qml` | **保留** | `shared/controls` | modules/sidebars | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialCard.qml` | **保留** | `shared/controls` | modules/settings | 属性(5) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialDialog.qml` | **保留** | `shared/controls` | modules/launcher, modules/settings, modules/sidebars | 属性(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialFilledTextField.qml` | **保留** | `shared/controls` | modules/settings | 属性(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialLoadingIndicator.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars, shared/controls | 属性(7)/方法(10) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialRadioGroup.qml` | **保留** | `shared/controls` | 内部/自包含 | 属性(16)/信号(1)/方法(4) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialShapeCanvas.qml` | **保留** | `shared/controls` | modules/settings, shared/controls | 属性(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialShapeWrappedMaterialSymbol.qml` | **保留** | `shared/controls` | modules/settings | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialSlider.qml` | **保留** | `shared/controls` | modules/settings | 属性(32)/信号(2)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialSplitSlider.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars, shared/controls | 属性(40)/方法(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialStepper.qml` | **保留** | `shared/controls` | modules/settings | 属性(8)/信号(1)/方法(1) | Timer | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialSymbol.qml` | **保留** | `shared/controls` | modules/bar, modules/dock, modules/filepicker, modules/keystone, modules/launcher, modules/lock, modules/quicksettings, modules/session, modules/settings, modules/sidebars, modules/systemcards, shared/controls | 属性(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialTextField.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars, shared/controls | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MaterialWaveProgressBar.qml` | **保留** | `shared/controls` | modules/keystone | 属性(23)/信号(1)/方法(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MediaControlBar.qml` | **保留** | `shared/controls` | modules/keystone | 属性(30)/信号(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MediaSourceIcon.qml` | **保留** | `shared/controls` | modules/bar | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/MeteoIcon.qml` | **保留** | `shared/controls` | modules/keystone, modules/sidebars | 属性(8)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/NiriSetupPrompt.qml` | **保留** | `shared/controls` | modules/settings | 属性(6)/信号(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/NotificationVisual.qml` | **保留** | `shared/controls` | modules/lock, modules/notifications, modules/sidebars | 属性(16)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/OutlinedTextField.qml` | **保留** | `shared/controls` | modules/settings | 属性(13)/信号(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/PageTransitionLayer.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars | 属性(4) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/PlayPauseButton.qml` | **保留** | `shared/controls` | modules/lock, shared/controls | 属性(24)/信号(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/PopupToolTip.qml` | **保留** | `shared/controls` | modules/bar, modules/keystone, shared/controls | 属性(17)/方法(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/QuickMaterialSlider.qml` | **保留** | `shared/controls` | modules/quicksettings, shared/controls | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/QuickToggleButton.qml` | **保留** | `shared/controls` | modules/quicksettings | 属性(31)/信号(3)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/QuickToggleGroup.qml` | **保留** | `shared/controls` | modules/quicksettings | 属性(7)/方法(5) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/RippleButton.qml` | **保留** | `shared/controls` | modules/bar, modules/filepicker, modules/keystone, modules/notifications, modules/settings, modules/sidebars, shared/controls | 属性(22)/方法(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/RippleEffect.qml` | **保留** | `shared/controls` | modules/lock, modules/sidebars, shared/controls | 属性(11)/方法(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SearchSelectMenuField.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars | 属性(36)/信号(1)/方法(21) | Timer | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SettingsActionRow.qml` | **保留** | `shared/controls` | modules/settings | 属性(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SettingsRow.qml` | **保留** | `shared/controls` | modules/quicksettings, modules/settings, modules/sidebars, shared/controls | 属性(7)/信号(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SettingsSection.qml` | **保留** | `shared/controls` | modules/quicksettings, modules/settings, modules/sidebars | 属性(9) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SidebarFlickable.qml` | **保留** | `shared/controls` | modules/quicksettings, modules/settings, modules/sidebars | 属性(16)/信号(1)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SidebarStagger.qml` | **保留** | `shared/controls` | modules/sidebars | 属性(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SortableMultiSelectField.qml` | **保留** | `shared/controls` | modules/settings | 属性(28)/信号(2)/方法(24) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/SplitMenuButton.qml` | **保留** | `shared/controls` | modules/settings, modules/systemcards | 属性(32)/信号(1)/方法(10) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StateLayer.qml` | **保留** | `shared/controls` | shared/controls | 属性(12) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledButtonGroup.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars | 属性(34)/信号(1)/方法(9) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledFlickable.qml` | **保留** | `shared/controls` | modules/launcher, modules/notifications, modules/settings, modules/sidebars, shared/controls | 属性(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledGridView.qml` | **保留** | `shared/controls` | modules/filepicker | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledListView.qml` | **保留** | `shared/controls` | modules/lock, modules/notifications, modules/settings, modules/sidebars, shared/controls | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledMenu.qml` | **保留** | `shared/controls` | modules/desktopcards, modules/dock, modules/settings, modules/sidebars | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledMenuItem.qml` | **保留** | `shared/controls` | modules/desktopcards, modules/dock, modules/settings, modules/sidebars | 属性(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledRectangularShadow.qml` | **保留** | `shared/controls` | modules/bar, modules/notifications, modules/sidebars, shared/controls | 属性(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledScrollBar.qml` | **保留** | `shared/controls` | modules/dock, modules/launcher, modules/settings, shared/controls | 属性(1) | Timer | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledSwitch.qml` | **保留** | `shared/controls` | modules/settings, modules/sidebars | 属性(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledText.qml` | **保留** | `shared/controls` | modules/lock, modules/notifications, modules/settings, modules/sidebars | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledToolTip.qml` | **保留** | `shared/controls` | modules/bar, modules/dock, modules/filepicker, modules/keystone, modules/launcher, modules/settings, modules/sidebars, shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/StyledToolTipContent.qml` | **保留** | `shared/controls` | shared/controls | 属性(8) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ThemeIcon.qml` | **保留** | `shared/controls` | modules/dock, modules/launcher, modules/settings, shared/controls | 属性(2)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ThinReadOnlySlider.qml` | **保留** | `shared/controls` | modules/settings | 属性(4) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/ToolCircularProgress.qml` | **保留** | `shared/controls` | modules/keystone, modules/sidebars | 属性(10) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/Toolbar.qml` | **保留** | `shared/controls` | modules/settings | 属性(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/TopBarPill.qml` | **保留** | `shared/controls` | modules/bar | 属性(4) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/TopBarPillBackground.qml` | **保留** | `shared/controls` | shared/controls | 属性(3)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/VolumeSlider.qml` | **保留** | `shared/controls` | modules/sidebars | 属性(9)/信号(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/WallpaperActions.qml` | **保留** | `shared/controls` | modules/settings, shared/controls | 属性(7)/信号(3) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/WaveProgressBar.qml` | **保留** | `shared/controls` | modules/keystone | 属性(24)/信号(1)/方法(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/WavyLine.qml` | **保留** | `shared/controls` | shared/controls | 属性(4) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/WeatherBackground.qml` | **保留** | `shared/controls` | modules/keystone, modules/sidebars | 属性(32)/方法(65) | Timer | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/WheelScrollController.qml` | **保留** | `shared/controls` | modules/launcher, modules/settings, shared/controls | 属性(13)/方法(5) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/WidgetPanel.qml` | **保留** | `shared/controls` | modules/quicksettings, modules/sidebars | 属性(7) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/LICENSE` | **保留** | `shared/controls` | packaging | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/MaterialShapes.js` | **保留** | `shared/controls` | shared/controls | 方法(72) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/README.md` | **保留** | `shared/controls` | modules/keystone, modules/settings, modules/wallpaper, packaging, shared/utils | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/ShapeCanvas.qml` | **保留** | `shared/controls` | shared/controls | 属性(9) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/geometry/Offset.js` | **保留** | `shared/controls` | shared/controls | 方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/graphics/Matrix.js` | **保留** | `shared/controls` | shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/CornerRounding.js` | **保留** | `shared/controls` | shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/Cubic.js` | **保留** | `shared/controls` | app, shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/Feature.js` | **保留** | `shared/controls` | shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/FeatureMapping.js` | **保留** | `shared/controls` | shared/controls | 方法(5) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/FloatMapping.js` | **保留** | `shared/controls` | shared/controls | 方法(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/Morph.js` | **保留** | `shared/controls` | shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/Point.js` | **保留** | `shared/controls` | shared/controls | 方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/PolygonMeasure.js` | **保留** | `shared/controls` | shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/RoundedCorner.js` | **保留** | `shared/controls` | shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/RoundedPolygon.js` | **保留** | `shared/controls` | shared/controls | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/controls/shapes/shapes/Utils.js` | **保留** | `shared/controls` | shared/controls | 方法(8) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/i18n/I18n.qml` | **保留** | `shared/i18n` | app, modules/bar, modules/desktopcards, modules/dock, modules/filepicker, modules/keystone, modules/launcher, modules/lock, modules/notifications, modules/quicksettings, modules/regionselector, modules/session, modules/settings, modules/sidebars, modules/systemcards, modules/wallpaper, shared/controls, shared/i18n, shared/utils | 属性(5)/方法(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/i18n/Translations.js` | **保留** | `shared/i18n` | modules/launcher, modules/settings, shared/i18n, shared/utils | 方法(5) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/i18n/qmldir` | **保留** | `shared/i18n` | 内部/自包含 | - | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/Animations.qml` | **保留** | `shared/theme` | modules/lock, modules/settings, modules/sidebars, shared/controls, shared/theme | 属性(81) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/Appearance.qml` | **保留** | `shared/theme` | app, modules/bar, modules/desktopcards, modules/dock, modules/filepicker, modules/keystone, modules/launcher, modules/lock, modules/notifications, modules/quicksettings, modules/regionselector, modules/session, modules/settings, modules/sidebars, modules/systemcards, modules/wallpaper, shared/controls, shared/theme | 属性(46)/方法(5) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/CoverScheme.qml` | **保留** | `shared/theme` | modules/keystone, modules/settings | 属性(2)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/Fonts.qml` | **保留** | `shared/theme` | app, modules/bar, modules/dock, modules/filepicker, modules/keystone, modules/launcher, modules/lock, modules/notifications, modules/regionselector, modules/session, modules/settings, modules/sidebars, modules/systemcards, shared/controls, shared/theme | 属性(9)/方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/Metrics.qml` | **保留** | `shared/theme` | modules/bar, modules/hotcorners, modules/launcher, modules/lock, modules/quicksettings, modules/settings, modules/sidebars, shared/controls, shared/theme | 属性(51) | IPC/Wayland | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/Resources.qml` | **保留** | `shared/theme` | app, shared/controls | 属性(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/Sizes.qml` | **保留** | `shared/theme` | modules/bar, modules/dock, modules/lock, modules/notifications, shared/controls | 属性(20) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/theme/Typography.qml` | **保留** | `shared/theme` | modules/bar, modules/dock, modules/quicksettings, modules/settings, modules/sidebars, modules/systemcards, shared/controls, shared/theme | 属性(49) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/AwwwCommand.js` | **保留** | `shared/utils` | modules/wallpaper | 方法(19) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/DateFormat.js` | **保留** | `shared/utils` | modules/keystone, modules/sidebars, modules/systemcards | 方法(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/FileUtils.js` | **保留** | `shared/utils` | modules/launcher | 方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/RecordingState.js` | **保留** | `shared/utils` | modules/keystone | 方法(2) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/SidebarPolicy.js` | **保留** | `shared/utils` | app, modules/sidebars, modules/wallpaper | 方法(6) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/SystemFormat.js` | **保留** | `shared/utils` | modules/bar, modules/keystone, modules/settings, modules/systemcards | 方法(14) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/TimeUtils.js` | **保留** | `shared/utils` | 内部/自包含 | 方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/Toml.js` | **保留** | `shared/utils` | app, shared/i18n | 方法(21) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/WallpaperMath.js` | **保留** | `shared/utils` | modules/wallpaper | 方法(18) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/WallpaperPaletteScope.js` | **保留** | `shared/utils` | modules/wallpaper | 方法(1) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/WallpaperSource.js` | **保留** | `shared/utils` | app, modules/settings, modules/sidebars, modules/wallpaper, shared/utils | 方法(10) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |
| `shared/utils/ZenPalette.js` | **保留** | `shared/utils` | modules/settings, modules/wallpaper, shared/utils | 方法(16) | 无 | 复用原子控件/设计Token/纯数学，零副作用 |

### native/ （共 0 文件）

| 文件路径 | 处置状态 | 归属 (Owner) | 消费者 (Consumers) | I/O | 副作用 | 目标路径 / 说明 |
|---|---|---|---|---|---|---|

### bin/ （共 0 文件）

| 文件路径 | 处置状态 | 归属 (Owner) | 消费者 (Consumers) | I/O | 副作用 | 目标路径 / 说明 |
|---|---|---|---|---|---|---|

### packaging/ （共 3 文件）

| 文件路径 | 处置状态 | 归属 (Owner) | 消费者 (Consumers) | I/O | 副作用 | 目标路径 / 说明 |
|---|---|---|---|---|---|---|
| `packaging/arch/PKGBUILD.in` | **保留** | `packaging` | 内部/自包含 | - | 无 | 系统打包与 systemd 单元元数据 |
| `packaging/dependencies.json` | **保留** | `packaging` | app, modules/dock, modules/launcher, packaging | - | 无 | 系统打包与 systemd 单元元数据 |
| `packaging/systemd/user/nyxuri-shell.service` | **保留** | `packaging` | 内部/自包含 | - | 无 | 系统打包与 systemd 单元元数据 |

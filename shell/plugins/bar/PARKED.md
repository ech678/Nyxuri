# 暂缓件（B 卷运行态审计下架）

> 2026-11-14 实机审计后下架的部件。改代码前先读这里，别把死件重新接进选装集。
> 分期与验收见 [ROADMAP](../../ROADMAP.md) §B，症状登记见
> [known-issues](../../../llms-wiki/shell/known-issues.md)。
>
> 2026-11-14 B8.4/B8.5 复核：岛 OSD 已接线（`DynamicIsland` 监听音量/亮度/
> 键盘锁服务，`DiOsd` 是真实消费者），`islandStyle/islandOverlay/islandPosition/
> hoverAction/click*/media*Style/keyhole` 已从配置与设置页退役——它们不再是
> “待接线”，而是明确删除。`DiTimers.qml` 仍按下方服务缺失口径停车。
>
> 2026-11-14 B8.2 复核：旧条目里「缺基件、参考树也没有」的判定是错的——
> `BarWidgetSwitcher*`、`ClippedProgressBar`、`Clipped*CircularProgress`、
> `StyledProgressBar`、`ResourceCard`、`ResourceUsage` 在 `references/end4-pC`
> 与 `references/iNiR` 都有源，已整抄入 `shell/plugins/bar` 与 `shell/services`。
> 下表只保留真正未接线的部分。

## 已解冻（不再是暂缓件）

| 文件 | 处理 |
| --- | --- |
| `Resources.qml` / `ResourcesPopup.qml` / `Resource.qml` | 基件整抄后进选装集（`systemMonitor`） |
| `ClockWidget.qml` / `ClockWidgetPopup.qml` | `BarWidgetSwitcher` + `DateTime` 到位，进选装集（`clock`） |
| `BatteryIndicator.qml` / `BatteryPopup.qml` | `ClippedProgressBar` 到位，进选装集（`battery`） |
| `SystemIcons.qml` / `NotificationUnreadCount.qml` | 直连 Nyxuri 服务，进选装集（`systemIcons`） |
| `PowerButton.qml` / `LauncherButton.qml` | 对齐 end4 原件，进选装集 |
| `BarGroupStylePopup.qml` | 右键就地调色已接线，样式持久化在 `PersonalizationConfig.barWidgetStyles` |
| `Workspaces.qml` | iNiR 876 行原件剪裁为 Niri-only end4 视觉，选装集默认部件 |

## 服务缺失（面已下架）

| 文件 | 缺的服务 | 下架方式 |
| --- | --- | --- |
| `DiTimers.qml` | `TimerService`（pomodoro/countdown/stopwatch） | 从 `DynamicIsland.contentProviders` 移除 timer 面，设置页无对应项 |
| 录制面（原 `DynamicIsland` 内联 `recordingComponent`） | `RecordingService` / `AudioRecordingService` | 从 `contentProviders` 移除 recording 面；`island/IslandPage.qml` 删除录制目录设置与 `FilePickerWindow`；`Bar.qml` 删除 `island stopRecording` IPC |

Timer/Recording 的配置键与 i18n 词条一并清空；恢复时按 end4 原件整抄
（`DiTimers.qml` 仍在树上，接上真实服务即可复活）。

## 未接线的孤儿（不进选装集）

| 文件 | 状况 |
| --- | --- |
| `HyprlandXkbIndicator.qml` | 依赖 iNiR `KeyboardIndicators`；当前键盘锁指示由 `SystemIcons` 直连 `KeyboardLockService` 承担 |
| `NetworkSpeed.qml` / `NetworkSpeedPopup.qml` | 依赖 iNiR `Network` 单例名；接线前先映射 `NetworkService`，不建转发别名 |
| `WeatherBar.qml` / `WeatherPopup.qml` / `WeatherCard.qml` | 依赖 iNiR `Weather`；`WeatherService` 已有，待 B8.5 复核后接线 |
| `DocktoPanel.qml` / `LeftSidebarButton.qml` / `RightSidebarButton.qml` | 依赖树内没有的 `ShellLayoutController` / 侧栏宿主直连；接线前先走 `ActionGateway` |
| `UpdatesCount.qml` | 依赖包管理器更新源；暂不引入 |

## 判定口径

- 「下架」= 从 `barComponentIds` / `barComponentOptions` / provider 表 / 设置页
  摘除，配置里残留的 id 在装载时被规范化过滤；**文件不删**（删除需作者确认）。
- 下架件不得出现在设置页、搜索锚点、manifest 路由与 IPC 面里——UI 不承诺
  不存在的能力。

# 暂缓件（B 卷运行态审计下架）

> 2026-11-14 实机审计后下架的部件。共同原因：它们依赖的上游基件/服务不在
> Nyxuri 树内，本地参考树里也没有相应源文件，无法 Fork & Trim，只能先下架。
> 恢复条件写在各条里；改代码前先读这里，别把死件重新接进选装集。
> 分期与验收见 [ROADMAP](../../ROADMAP.md) §B，症状登记见
> [known-issues](../../../llms-wiki/shell/known-issues.md)。

## 不能装载（缺基件，Loader status=Error）

| 文件 | 缺的基件 | 下架方式 |
| --- | --- | --- |
| `Resources.qml` / `ResourcesPopup.qml` / `Resource.qml` | `BarWidgetSwitcherArea`、`ClippedOutline/FilledCircularProgress`、`ResourceUsage` 单例 | 已从 `barComponentIds` / `barComponentOptions` 移除（`systemMonitor` 不可选）；`getWidgetUrl` 映射保留，配置里残留的 id 由 `normalizedBarLayoutIds` 过滤 |
| `ClockWidget.qml` / `ClockWidgetPopup.qml` | `BarWidgetSwitcher` | 已从 `barComponentIds` 移除（`clock`） |
| `BatteryIndicator.qml` / `BatteryPopup.qml` | `ClippedProgressBar` | 从未进入选装集；文件保留但无消费者 |

`BarWidgetSwitcher*`、`ClippedProgressBar` 在 `references/iNiR` 里**不存在**
（`barM3/*` 只引用它们），所以不是“忘了拷”，而是上游快照本身就缺。恢复
前先补齐这三个基件与 `ResourceUsage` 桥（`SystemMonitorService` 派生
cpu/memory/disk 百分比），再一次性把 id 加回选装集。

## 服务缺失（面已下架）

| 文件 | 缺的服务 | 下架方式 |
| --- | --- | --- |
| `DiTimers.qml` | `TimerService`（pomodoro/countdown/stopwatch） | 从 `DynamicIsland.contentProviders` 移除 timer 面，设置页无对应项 |
| 录制面（原 `DynamicIsland` 内联 `recordingComponent`） | `RecordingService` / `AudioRecordingService` | 从 `contentProviders` 移除 recording 面；`island/IslandPage.qml` 删除录制目录设置与 `FilePickerWindow`；`Bar.qml` 删除 `island stopRecording` IPC |

Timer/Recording 的配置键与 i18n 词条一并清空；恢复时按 end4 原件整抄
（`DiTimers.qml` 仍在树上，接上真实服务即可复活）。

## 未接线的孤儿

| 文件 | 状况 |
| --- | --- |
| `BarGroupStylePopup.qml` | B0 整抄件，**全库零消费者**。D5 的“右键部件就地调色”未接线；接线或删除二选一 |
| `DocktoPanel.qml` / `NetworkSpeed.qml` / `NetworkSpeedPopup.qml` / `LeftSidebarButton.qml` / `RightSidebarButton.qml` / `UpdatesCount.qml` / `SystemIcons.qml` / `NotificationUnreadCount.qml` / `HyprlandXkbIndicator.qml` / `WeatherBar.qml` / `WeatherPopup.qml` / `WeatherCard.qml` | 依赖 iNiR 单例名（`CompositorService`、`Audio`、`Notifications`、`Network`、`BluetoothStatus`、`KeyboardIndicators`、`Weather`、`Icons`）或树内没有的 `ShellLayoutController` / `AppSearch` / `TaskbarApps`；当前不在选装集内，也未做别名桥接。接线前先做单例映射，别用 `eval` 兜底 |
| `MediaArtworkResolver.qml` / `MediaCrossSlideImage.qml` / `CavaProcess.qml` / `TrayService.qml` | 有真实消费者的辅助件（Media / SysTray / BarContent），不属于下架范围，列在此处只为与孤儿区分 |

## 判定口径

- 「下架」= 从 `barComponentIds` / `barComponentOptions` / provider 表 / 设置页
  摘除，配置里残留的 id 在装载时被规范化过滤；**文件不删**（删除需作者确认）。
- 下架件不得出现在设置页、搜索锚点、manifest 路由与 IPC 面里——UI 不承诺
  不存在的能力。

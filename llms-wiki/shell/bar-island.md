# Bar & Island 统一工作页（B 卷）

> 本页回答：Bar/Island 现在由哪些文件承载、样式与几何的真值在哪、怎么验证。
> 分期、验收标准与断裂提醒以 [shell/ROADMAP](../../shell/ROADMAP.md) §B 为准；
> 症状见 [known-issues](known-issues.md)，下架件与恢复条件见
> [PARKED](../../shell/plugins/bar/PARKED.md)。B0–B7 的计划叙事已归档，不再冒充事实。

## 结构

- `plugins/bar/` 是一个单元（`shell.bar`），五种几何插槽里的 `edge`；岛不再是独立单元，
  而是中段布局部件 `componentId: "island"`，设置随 bar 页的 `bar.island` 子页。
- `Bar.qml`：窗口壳（layer/exclusive/autohide/屏幕角/bar/island IPC）。
- `BarContent.qml`：唯一的分发点。三段 lane（left/middle/right）× 两套外观分支
  （material / plain）；部件通过 `getWidgetUrl()` 装载，隐藏分支的 Loader `active:false`。
- `BarGroup.qml`：分组胶囊（圆角 start/mid/end、`paintBackground`、`segmented`、
  `groupColor`、右键样式弹层、`contentColor` 注入）。
- `DynamicIsland.qml` + `Di*.qml`：岛本体与 Notif/Battery/OSD/Media/Session 面；
  `island/` 下是路由页面与横排时钟编辑器。
- 部件池：`Workspaces`（iNiR 剪裁）、`Media`、`SysTray*`、`UtilButtons*`、
  `Resources*`、`ClockWidget*`、`BatteryIndicator`、`SystemIcons`、`LauncherButton`、
  `PowerButton`、`ActiveWindow`（end4 重抄）、`Divisor`。
- 设置：`GeneralBarPage.qml`（位置/样式/workspaces/三段拖拽）与
  `island/IslandPage.qml`（岛开关、卫星、键盘指示、横排时钟）。

## 样式与几何真值

- 视觉基线是 end4-pC：胶囊几何、分组色、每部件 M3Palette 色调、material 黑名单、
  workspaces dots/数字/占用态、岛自画胶囊。
- material 判定只有一个来源：`PersonalizationConfig.barIsMaterial`（3||4）、
  `barIsMaterialHug`（4）、`barIsPanel`（5）。部件不得自行 `=== 3`。
- 中段定位是显式 `x: (parent.width - width) / 2`；宽度由活动分支决定。两套 lane
  同时声明，但部件 Loader 按分支门控——否则每屏两个岛，隐藏岛会抢
  `ActionGateway.islandHost`。
- 窗口层：3 档用 `layerGap`，4/5 档 exclusive zone 额外 +4；4 档挂左右圆角装饰，
  按 lane 是否为空显示。
- 岛 OSD 是岛内生产：监听 `VolumeService`/`BrightnessService`/`KeyboardIndicators`
  （iNiR 整抄的 panel/popup 服务），写入 `GlobalStates.osdKind`，仅主屏岛发布；
  `DiOsd` 只读该状态。键盘布局由 `KeyboardLayoutService` 从
  `niri msg -j keyboard-layouts` + 事件流投影。
- 岛 idle 卫星由 `islandSatellite`（clock/weather/none）控制，默认时钟；
  不是 end4 `leftWidget` 的硬编码。

## 验证

```bash
python3 -m unittest tests.shell.test_bar_runtime            # 运行态探针（无 Wayland 显式跳过）
shell/scripts/dev/probe-bar.sh --json                       # 同一探针的 JSON 输出
shell/scripts/dev/probe-bar.sh --json --session             # 在现有图形会话跑（无窗口）
python3 -m unittest tests.shell.test_bar_end4 tests.shell.test_island_end4
```

探针把 `BarContent` 装进隔离 shell，逐档 cornerStyle 1/3/4/5 重建，断言所有 active
`Loader.Ready`、无 pending/failed、几何有限且中段居中、岛可见，并扫描日志中的
TypeError/ReferenceError/compiled empty。静态字符串测试只作结构回归，不作为完成证据。

## 不抄与停车

- 不抄 blob C++ 形状/透明度调色系统；以同色矩形 + blur/实色近似。
- Timer/Recording 无服务实体，provider/设置/IPC/i18n 已下架，`DiTimers.qml` 留文件。
- lyrics 面板、岛悬浮模式、竖排 bar 岛角部按钮、battery 岛面在停车场；
  未复活前不回到搜索、设置或默认键位。
- 依赖 iNiR 单例名的 `HyprlandXkbIndicator`/`NetworkSpeed*`/`Weather*`/
  `DocktoPanel`/`SidebarButton` 未接线，清单以 PARKED.md 为准。

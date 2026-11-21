# B9 基线差异矩阵（冻结）

> 冻结日期：2026-11-21。原位置：`shell/ROADMAP.md` B 卷 §1（2026-11-14 审计快照）。
> 本页是 B9.0–B9.8 验收的对照依据，只进不改；不反映 D 卷（设计统一）之后的现状。
> 部分条目标注「已对齐」指 2026-11-14 当时的实现状态，后续演进以源码为准。
> D-1 定案修订了其中字号条款（end4 字号阶梯 → M3 type scale），见当前
> [shell/ROADMAP](../../shell/ROADMAP.md) 定案区与 [design-system](../shell/design-system.md)。

## 1.1 全局尺寸、字号、圆角

| 项 | end4 | Nyxuri 现状 | 结果 |
| --- | --- | --- | --- |
| 基础 bar 高度 | 用户自由调整 | 默认 36（`defaultBarThickness`，可改） | **不作为差异项**；部件与字号必须适配所选厚度 |
| Float 高度 | 所选厚度 + 5×2 | 所选厚度 + 5×2 | B9.0 已对齐（`barStyleBoost`） |
| M3 Hug / Panel | 所选厚度 + 4 | 所选厚度 + 4 | B9.0 已对齐 |
| 竖向 bar 宽度 | 用户自由调整（end4 参考 46） | 独立可调（`barVerticalThickness`，默认 36） | B9.4 已对齐；不冻结为 46 |
| `smallest` | 10 | 10 | B9.0 已对齐 |
| `smaller` | 12 | 12 | B9.0 已对齐 |
| `smallie` | 13 | 13 | B9.0 已对齐 |
| `small` | 15 | 15 | B9.0 已对齐 |
| `normal` | 16 | 16 | B9.0 已对齐 |
| `large` | 17 | 17 | 无差异 |
| `larger` | 19 | 19 | 无差异 |
| `unsharpenmore` | 6 | 6 | B9.0 已对齐 |
| `screenRounding` | 23 | 23 | B9.0 已对齐 |
| `windowRounding` | 18 | 18 | B9.0 已对齐 |

证据：B9.0 起 `shell/commons/Typography.qml` 全局 1.0，`Appearance.font.pixelSize`
直接钉住 end4 的 10/12/13/15/16/17/19；`Appearance.sizes.barHeight` 由
`PersonalizationConfig.barStyleHeightBoost` 注入样式加成，默认厚度 36 仍可调。
end4 基准在 `references/end4-pC/modules/common/Appearance.qml:253-263,436-438`。

## 1.2 Bar 窗口与 lane

| 项 | end4 | Nyxuri 现状 |
| --- | --- | --- |
| 左右 lane 内缩 | material 5 / Hug 0 / Float、Panel 4 / 其余 8 | 同 end4（B9.0 定义 `laneMargin`，此前引用未定义恒 0） |
| 窗口高度 | 含 Float/Hug/Panel 修正 | 同 end4（`sizes.barHeight` 含样式加成） |
| 角落出现动画 | `showCorners` + 65ms timer | **结案（B9.6）**：该属性在 end4 参考树里零消费者，是参考自身死代码；Nyxuri 直接显隐即 end4 运行态，不移植 |
| islands 样式 | cornerStyle 2，名称 “Islands” | 名称已改为 “Islands”（B9.0）；lane inset 已生效 |
| 中段岛宽 | `dynamicIslandEnabled` 特殊分支 | B9.6 已对齐：岛占中段时 centerPill 走 −4/+8 满高分支（probe `b96.hug` 断言） |

## 1.3 分组胶囊与右键改色

- 胶囊 padding、背景上下内缩、`fullRadius=height/2` 与 end4 相同。
- `midRadius` 因 `unsharpenmore` 10 而整体变圆；Float 高度差又让胶囊更扁。（B9.0 后 `unsharpenmore=6`，已消）
- 右键样式编辑器：B9.6 已补齐全链路——`ClockWidget`、`Resources`/`Resource`、
  `BatteryIndicator`、`Divisor`、`UtilButtons`、`Media`、`Workspaces` 恢复
  `contentColor/contentColorOverridden`，`BarGroup` 的 Binding 探测到属性即接管文字/图标
  颜色（probe `b96.override` 端到端断言）。
- `BarGroupStylePopup`：B9.6 换装 end4 `ConfigSlider`（整抄 `ConfigSlider`/`StyledSlider`/
  `OptionalMaterialSymbol`），并接全屏 backdrop 外点关闭（Niri 无 focus-grab 协议，
  同 StyledPopup B9.1 模式）。

## 1.4 部件差异

| 部件 | 差异 |
| --- | --- |
| Workspaces | **B9.6 已重做（end4 骨架整抄）**：material 宽 30 / 其余 26；default/gnome/dots/ticks 四样式（`WorkspacesAlt` 整抄）；active Colorizer 数字着色；右键 toggleOverview、右键长按样式编辑器。**槽位语义按作者定案改用 iNiR `dynamicCount` 口径（见 2.4）**：槽位 = 本输出实际存在的工作区（niri 保留空槽，尾巴真实且稳定），预算 `shown` 只作上限/翻页宽度——这是对 end4 固定网格的登记偏离，实机否决了虚构尾巴 |
| Media | **B9.6 已对齐**：contentColor 链路、无 artist `topMargin:-13`、next 右 margin −2、播放/暂停 hover 走 end4 混合语义（0.87/0.9）、右键长按样式编辑器；字号已随 B9.0 Typography 1.0 成为真 13/12 |
| SystemIcons | B9.2 已重做：七个固定 26px 槽 + hover 胶囊 + 17px 图标 + tooltip + 独立点击；`PeripheralBattery` 低电/危险双档；旧账：裸 Flow 宽度跳变、19px、整块 MouseArea、无外设电池 |
| SysTray | B9.1 已重做：iNiR `TrayService` 剪裁整抄 + `bar.tray` 持久化；下箭头随 unpinned 出现；tint/filter/id 三项真实可调；overflow 点击外部关闭。旧账：`unpinnedItems` 恒空、`togglePin()` 空实现、无存储、tint 读不存在属性 |
| ClockWidget | **B9.6 已对齐**：contentColor 接管 default 两味；AM/PM 不再强制补零；徽标字色 `colPrimary`；colDefault letterSpacing −0.9（Nyxuri 自加的字体覆写键保留为默认值之上的 override） |
| Resources | **B9.6 已对齐**：`contentColor/contentColorOverridden` 全链路接管 ink 与百分比文字 |
| BatteryIndicator | **B9.6 已对齐**：highlightColor 跟随右键色；hover 在 click-to-show 模式下关闭（同 end4） |
| UtilButtons | **B9.6 已对齐**：contentColor 接管 legacy 图标/计时文字；`UtilButton` 回归 end4 原件（hover 底 `transparentize(colLayer0, 0.8)`、图标 primary/onPrimary，不再按皮肤分支） |
| PowerButton | **B9.6 已对齐**：material 32（`barPowerButtonSize`） |
| ActiveWindow | **B9.6 已对齐**：去掉右侧 6px margin；垂直 fallback `desktop_windows` 删除（end4 空着） |
| Divisor | **B9.6 已对齐**：dot 文本 `"• "` 与宽度分支、rect 色 contentColor 化；`space` 间距读数与 UI 归 B9.7 |

### 部件清点（2026-11-15 截图审计：end4 `allWidgets` 23 件 → Nyxuri 处置）

| 处置 | 部件 |
| --- | --- |
| 已对齐（13，白名单成员） | workspaces、media、resources、systemIcons、clockWidget、utilButtons（白名单内 `quickSettings` 为同件双名）、sysTray、batteryIndicator、activeWindow、powerButton、divisor、launcherButton、dynamicIsland（媒体面见 1.5 / B9.9） |
| B9.9 接线 | weatherBar（作者 4 张截图中 3 张可见 "14°C/12°C"；fork 在树，引用不存在的 iNiR `Weather`/`Icons.getWeatherIcon`，且不在 `barComponentIds`）、visualizer（图 3 中段频谱条；文件在树，白名单缺） |
| B9.9 核实 | hyprlandXkbIndicator（名绑 Hyprland；先查 niri 有无键盘布局数据面，有则接 `NiriDriver` 并正名，无则登记不做） |
| 待拍板 | bluetooth、avatar 独立件（树无文件；SystemIcons 蓝牙槽与岛头像已覆盖展示，默认不做，要整抄补一句进 B9.9 即可） |
| 维持下架 | networkSpeed（数据面 `NetworkInterfaceHistoryService` 已备，接时再立项）、updatesCount（无包管理器更新源）、leftSidebarButton / docktoPanel（PARKED：接线走 ActionGateway；dock 不在对照范围） |
| 不做 | aiUsage（end4 AI 服务专属依赖） |

## 1.5 岛（Dynamic Island）

**默认显示**：idle 面左侧头像圆（material 32px 贴左；非 material 24px + 4px 左边距，
可用 `islandShowAvatar` 隐藏），右侧状态图标（mic/音量/WiFi/未读）与时钟。B9.3 起右侧
时钟是横向时钟 `ClockContent`（日期 + 风格化数字，`islandHideDate` 为真实开关），
宽度按内容增长，探针基线 185（隐藏头像 157）。`~/.face` 不存在时显示 `person`
兜底图标，不再留空色圆。

| 项 | end4 | Nyxuri 现状 |
| --- | --- | --- |
| 左右卫星 | `dynamicIsland.leftWidget/rightWidget` 在岛两侧渲染 | 已删除，改成 `islandSatellite` 只在 idle 面内部显示 clock/weather |
| 日期 | idle 不显示 | B9.3 接线：idle 横向时钟渲染日期，`islandHideDate` 是真实开关（Nyxuri 有意差异） |
| 岛胶囊 | material/centerOnly 时透明，可跟随 frame 色 | **B9.6 已对齐**：material 或 centerOnly（cornerStyle 0）时透明（probe `b96.hug` 断言两态）；`followFrameColor` 维持删除（无 UI 无消费者） |
| 媒体面 | 可配媒体按钮 + dots/wave | **B9.9 恢复（待开始，B-10 拍板推翻原有意差异登记）**：`showMediaControls` 三按钮（skip_previous/pause/skip_next，可见性吃 canGoPrevious/canGoNext）+ `visualizerStyle` dots/wave/none 回归；wave 态 cava 仅媒体面可见且播放时拉起（`WaveVisualizer.qml` 自 end4 新 cp，end4 默认 dots/controls-off） |
| Timer/Recording | 有 | 已下架（有意） |
| 通知面 | 图标左 4/12、文字左 14/2、fallback 左 0/4 | **B9.6 已对齐**（wrapper 按可见子项取 end4 锚点） |
| OSD | volume/brightness/gamma 三通道，132 宽 | **B9.6 已对齐宽度**：全通道 132（keyboard 收进）；gamma 通道为**登记有意差异**——Niri 无 gamma 服务（hyprsunset 等 Hyprland 生态件），不追 |
| 竖向岛 | 不完整 | B9.4：竖向布局过滤岛，通知宿主回退。**B9.6 定案挂起**：end4 自身竖向岛不完整、无基线可抄，重排待独立设计，不进对照执行分期 |

## 1.6 弹层与 tooltip

- `StyledPopup`：**B9.6 已对齐** end4 `colLayer1Base` / 圆角 `large+5`(=28) / 内边距 8 /
  边框 `colLayer0Border`。tray overflow、时钟、电池、资源弹层随之统一。
- `SysTrayMenu`：**B9.6 已对齐**——剥掉 zzz/angel/inir 死皮肤分支（引用 Nyxuri
  `Appearance` 上不存在的 token，undefined 恒假），默认路径即 end4 `colLayer0` +
  `windowRounding`(18)；`SysTrayMenuEntry` 同步清理。
- `M3ToolTip`：**B9.6 已对齐**——恢复 end4 `PopupToolTip` 外边距（=padding），不再压 0。
- `BarGroupStylePopup`：**B9.6 已对齐**——end4 `ConfigSlider` 三件套整抄替换 Nexus 滑块，
  backdrop 外点关闭。

## 1.7 设置真伪清单

| 设置 | 现状 |
| --- | --- |
| `Floating`（`barOverlay`） | **B9.7 已下架**（作者拍板；Clavis 遗产，end4 选项面无 overlay） |
| `Screen edge` left/right | B9.4 已实现：切换窗口锚点、内容层与 exclusiveZone |
| `Show Island` / 布局成员 | B9.3 已收口：布局成员是唯一真相；设置开关改走 `setIslandInLayout`，删掉岛后不会被重新播种 |
| `islandLayoutMigrated` | B9.3 已修：加载改读 `layoutMigrated`；纯函数 `resolveBarLayouts` 由探针验证「空中段 + 已迁移」不复活 |
| `islandHideDate` / 水平时钟 | B9.3 已接线：`ClockContent` 进入 idle 面，日期开关与水平时钟编辑页都有真实消费者 |
| 通知槽仲裁 | B9.3 已修：`shell.qml` 改看 `islandInLayout`，岛不在布局里时通知宿主恢复 |
| tray 配置 | B9.1 已接线：`bar.tray` 五键双向读写并落盘 |
| `barShowBackground` | **B9.7 已接线**：真属性落盘；UI 仅 Hug/Float 可用（end4 同款）；probe `b97` 断言背景色翻转 |
| `barDividerSpacing` | **B9.7 已接线**：4–400 step 2，`bar.divider`/`m3.divider` 两处桥归一；UI 仅 space 样式出现 |
| autoHide | **B9.7 已接线**：`enable` 落盘 + 设置页开关；pushWindows/hoverRegionWidth/Super 显出保持内部默认（有消费者不可见）；probe 断言 reservation 0↔41 往返 |
| screenList | **B9.7 已接线**：Screens 段（>1 屏出现，All 收拢规则）+ `normalizedScreenList`；未知屏幕名回退全屏由 probe 验证 |
| utilButtons | **B9.7 已接线**：七键真属性 + Utility buttons 段（`layoutUses` 门控）；`showScreenRecord` 处决（Recorder 僵尸：孤儿桩 + 不存在的 `recordScriptPath`）；部件加回 `barComponentIds` 白名单（此前不可达） |
| resources | **B9.7 已接线**：5 个 alwaysShow + Filled/Outline + Show percentage；轮询服务面保持内部默认 |
| numberMap | **B9.7 已接线**（作者拍板）：`numberStyle` 三预设（Normal/汉字/罗马）单一真相，桥派生数组（end4 存裸数组、UI 只出三预设，登记偏离） |
| `bar.tray` 设置 | B9.1 已补 Tray 段：pin/tint/passive/id 均可调 |
| workspaces 样式/槽位 | B9.6 已接线：`workspaceStyle` 四选 + `workspaceShown` 槽位预算（1–50）落 `workspaceStyle`/`workspaceShown` 键，Bar 设置页 Workspaces 段可调 |
| 竖向厚度 | B9.4 新增 `barVerticalThickness`，仅左右边缘时出现，独立于水平厚度 |
| 外边距 | B9.5 新增「屏幕边缘边距 / 两端边距」，0 = end4 贴边；exclusiveZone 与弹层同步 |

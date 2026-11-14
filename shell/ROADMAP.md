# Nyxuri Shell 路线图

> 本页只回答：现在在哪、下一步是什么、什么已定死。运行行为以源码与契约测试为准；
> 开发契约见 [AGENTS](AGENTS.md)；知识库索引见 [llms.txt](../llms-wiki/llms.txt)。
> 阶段状态仅在有可复现证据时更新，不以目录、字符串、Loader 存在或隐藏 UI 作为完成证明。
> 各阶段任务分解与逐项验收记录在追加式台账
> [shell-roadmap-ledger](../llms-wiki/archive/shell-roadmap-ledger.md)。
> 当前整体处于**实验性阶段**（BUG 多、外观未开发、暂不推荐日常使用）；
> 已知 BUG 与暂缓的基础设施缺口见 [known-issues](../llms-wiki/shell/known-issues.md)。
> 跨域骨架与架构重塑演进（S0/S1 插件生命周期，以及 P0~P4 架构散文化与优雅化专项）归根
> [ROADMAP](../ROADMAP.md) 管。本页承载 P4/T3 收尾验收与 B 卷（Bar & Island 统一）计划。

## 目标与边界

- Shell 冷启动路径小而可解释；可选功能按需加载，停用后释放实例及其 Timer、Process、请求、连接、监听和回调。
- 模块按功能域自治；UI 通过 Action Gateway 表达桌面意图，领域服务拥有对应 I/O；全局 singleton 仅用于确有跨域共享状态的能力。
- 设置 UI 的 Default（Caelestia 式）与 Dashboard 均是正式可选呈现，支持热切换；它们共享设置模型、路由、搜索、动作和持久化逻辑，不复制业务。
- 清理和重构不得降低视觉品质、动效、可读性、几何精度或对齐。
- 以原版 Niri 为基础兼容目标；外部能力缺失时局部降级，不让可选依赖阻断核心 Shell。
- Wiki 只保留能指导实现、审查、验证或排障的现行契约；历史资料归档，不冒充当前事实。

## 状态规则

任务状态只使用 `待开始`、`进行中`、`阻断`、`待验收`、`已完成`。合并前置、实现、行为验证和视觉验收分别记录；测试失败、环境跳过与未验证不得混为通过。每项任务明确旧实现的保留、迁移、归档或删除方式。

## 卷宗总览

| 卷 | 内容 | 状态 |
| --- | --- | --- |
| P4 | 主题契约、模板兼容与取色引擎分阶 | 待验收（契约测试全绿；实机行为与视觉证据待作者） |
| T3 | 设置界面替换：Caelestia 安卓风味 | M3/M4 待验收（机器证据齐；视觉过目待作者） |
| B | Bar & Island（布局自由 + end4 视觉基线） | B9.0/B9.1/B9.2/B9.3 待验收（机器证据齐；截图、实机托盘与视觉过目待作者）；B8 旧验收作废，仅保留结构回归证据 |
| P6 | 整体验收与未来移植 | 排队（前置主线 KM5） |

## 已交付基线台账

| 阶段 | 交付 | 状态 |
| --- | --- | --- |
| R1 | 状态与事实收口 | 已完成 |
| R2 | 启动闭包与可选模块 | 已完成 |
| R3 | 品牌、路径与构建边界 | 已完成 |
| R4 | 架构、生命周期与结构收敛 | 已完成 |
| R4-C | 结构收敛与全面去 C++ | 已完成 |
| R5 | 资源、文档与测试收口 | 已完成 |
| R6 | 能耗基线、事件循环与稳态治理 | 已完成 |
| R7 | 多套设置 UI 与 PR #120 前置审查 | 已完成 |
| R8 | 设置导航扁平化与 M3 信息架构 | 已完成 |
| R9 | 功能开关与真实生命周期 | 已完成 |
| R10 | Action Gateway 与模块自治 | 待验收 |
| R11 | 控制面与透明度 | 已完成 |
| R12 | 全局文档架构重塑 | 已完成 |
| KM4.5/4.6 | 随主线结构收敛：modules→units 拆迁正名、packaging/fallback/assets 处决、quicksettings→quickpanel 正名（明细见台账） | 已完成 |

「已完成」表示该阶段按当时验收标准交付并留有行为证据，明细见归档台账。
R10 行为与契约测试全绿，待作者实机验收后改为已完成。

## P4 主题契约、模板兼容与取色引擎分阶（待验收）

**目标：** 主题契约与渲染引擎自有、与 Noctalia v5 palette/template 规范兼容；
matugen 降格为纯取色位；深浅模式系统级写入收敛为 `nyxuri theme` 单一实现。

**实施（明细见台账 P4 实施记录）：**
- 契约层：一次生成双写 `colors.json`（50 token 热载，schema 不变）与
  `palette-modes.json`；16 角色 palette JSON 镜像至 Noctalia 自定义色板目录，
  双 Shell 默认各自独立取色，谁 active 谁写全部输出。
- 短期引擎：matugen 仅 `--json` 纯取色，Tera 渲染路径全量退役；纳入 doctor
  可选依赖检查。
- 渲染层：TemplateAdapter 落 `services/TemplateService.qml`，表达式子集
  （块/过滤器/`palettes.*` 显式拒绝）；kitty/btop/starship vendor 入库（MIT
  来源映射），yazi 取色模板删除。
- 深浅模式：Shell 侧系统写入清算，代调 `nyxuri theme`（CLI 缺失时内部照切
  并明示）；gsettings 只读观察回路保留。
- 色差实测：分歧矩阵已钉值（`on_*_container` 系 Noctalia tone 重锚定，
  ΔE00≈10）；对齐路径为镜像色板 + `color-scheme-set`。

**验收：** 契约测试全绿（golden master + MD3 向量 + 分歧矩阵 + 注册表行为测试，
宿主 550 测试、分类 111 测试、check.sh 全绿）；壁纸切换/深浅代调链路/模板
hooks 的实机行为证据与视觉验收待作者确认。镜像色板是否长期作为 Noctalia
对齐策略（`source = custom`）留验收拍板。

## T3 设置界面替换：Caelestia 安卓风味（收尾验收中）

> 对应主线跨域活跃路线 T3 站。旧 Default + Minimal 设置中心外壳已替换为 Caelestia Nexus
> 视觉范式（Material Design 3 Master-Detail 连通卡片与双行导航）；与 Dashboard（端景网格）
> 双轨并存，坚守“换皮不换骨、只换呈现不碰业务”底线。

- **策略（No picking）**：偏好原子原件从本地参考树 `shell/references/caelestia/modules/nexus/`
  全套拷入（100% 纯 QML/JS，斩断外部 C++/插件依赖，桥接 Nyxuri 真相
  `Appearance.m3colors`/`rounding`/`spacing`/`Fonts`/`I18n`），落 `shell/ui/` 平面原子库
  （`ConnectedRect`、`Preference*` 八行原子、`NexusSearchBar`、`NexusPageBase`；
  几何/字号唯一源 `ui/NexusStyle.qml`，tokens.hpp 值 1:1 移植、脱离全局 0.85 缩放、
  契约测试逐值钉死），再自顶向下积木式翻新。
- **不移植声明**：blob C++ 形状系统（含果冻物理回弹）与 transparency layer 调色系统
  不进 Nyxuri（纯 QML 红线），以同色矩形融合 + blur/实色近似——这是与原版仅剩的刻意差异。
- **轴收敛**：`settingsPanelStyles` 收敛为 `default`/`dashboard` 两态，历史 `minimal`
  自动折叠为 `default`；搜索框对齐原版**纯视觉占位**形态。

| 阶段 | 交付目标 | 状态 |
| --- | --- | --- |
| M0 | 配置轴 3 ➔ 2 收敛与向后兼容；路由元数据补充顶层 `description`；单测守住基线 | 已完成 |
| M1 | 偏好原子套件纯 QML 拷入与重构（`ConnectedRect`、`PreferenceToggle` 等 11 个原件落地并过原子单测） | 已完成 |
| M2 | 视窗外壳与 NavPane 双行导航骨架落地，接入药丸搜索（原版占位形态）与胶囊高亮，处决旧 `NavigationRail*`；fidelity 修订对齐 Caelestia 实测值并新增 About 页 | 已完成 |
| M3 | 核心页面首批积木化翻新（`AccountPage`、`ThemePage`、`WallpaperPage`、`DisplaysPage`） | 待验收（机器证据已随 S0-4 收窄版产出；视觉过目待作者） |
| M4 | 全页面覆盖、废弃代码清算与全量测试冒烟验收（批 A–F 已落地；清算档 dashboard 双轨合并已划掉——双轨终局保留，其余候选整档挂起；冒烟证据随 S0-4 收窄版产出） | 待验收 |

**待验收**：M3 核心四页与 M4 全页面覆盖的实机视觉过目。fidelity 三轮修订与
S0-4 资产收编明细见台账 T3 实施记录。

## B 卷：Bar & Island（布局自由 + end4 视觉基线）

> **状态：2026-11-14 第二次重置。** B8.1–B8.6 的“已完成/待验收”只证明了结构存在、
> Loader 不空、探针几何不 NaN，没有证明与 end4 的表现一致；这些阶段全部退回
> `待开始`，历史明细继续留在台账，不再作为本页的完成依据。
> 本页只写：**定案、全量表现差异、分期、验收方式**。
> 症状登记见 [known-issues](../llms-wiki/shell/known-issues.md)，
> 下架件见 [PARKED](../shell/plugins/bar/PARKED.md)。

### 0. 定案（2026-11-14，作者拍板）

| # | 决策 | 结论 |
| --- | --- | --- |
| B-1 | 布局自由度 | 三段（`left/middle/right`）自由拖拽，不写死部件组合；空 lane 不占位、不出胶囊 |
| B-2 | 视觉基线 | **end4-pC 的相对几何为唯一准绳**。bar 厚度与竖向宽度由用户自由调整，不冻结绝对值；Float = 所选厚度 + 5×2，M3 Hug/Panel = 所选厚度 + 4，padding/间距/圆角关系照 end4。bar/island 字体走 1.0 尺度；`unsharpenmore=6`、`screenRounding=23`、`windowRounding=18` |
| B-3 | 岛的唯一真相 | 以“岛是否在布局里”为唯一真相；`islandEnabled` 只保留旧配置迁移读取，不再作为第二开关。通知槽仲裁必须看布局成员，不看旧开关 |
| B-4 | Timer / Recording | 继续下架：无 `TimerService`/`RecordingService`，provider、组件、设置、IPC、i18n 一并摘除；`DiTimers.qml` 留文件待接线 |
| B-5 | 验收口径 | 只认运行态：`qs -p` 逐件 `Loader.Ready` + 布局求值数值 + 实机截图；静态字符串断言只作结构回归 |
| B-6 | 整抄纪律 | 有上游源的一律 `cp` 原件再剪裁；禁止手写残卷。SysTray、竖向 bar、SystemIcons、Workspaces 都按此执行 |
| B-7 | SysTray | Windows 式“可见区 + 下箭头小菜单 + 可隐藏图标”；end4/iNiR 已有 pinned/unpinned + overflow 网格可抄，Nyxuri 补真实持久化、外部点击关闭和设置页 |
| B-8 | SystemIcons | 抄 bar 上“快捷设置”部件（`UtilButtons.qml` / `UtilButton.qml`）的按钮语言：固定槽位、hover 胶囊、统一图标尺寸与 tooltip；不抄裸 Flow |
| B-9 | 外边距 | 新增“上/下边界”和“左右边距”两项设置；与内部 lane inset 分离，默认 0 = end4 行为 |

### 1. 全量表现差异（2026-11-14 审计）

#### 1.1 全局尺寸、字号、圆角

| 项 | end4 | Nyxuri 现状 | 结果 |
| --- | --- | --- | --- |
| 基础 bar 高度 | 用户自由调整 | 默认 36（`defaultBarThickness`，可改） | **不作为差异项**；部件与字号必须适配所选厚度 |
| Float 高度 | 所选厚度 + 5×2 | 所选厚度 + 5×2 | B9.0 已对齐（`barStyleBoost`） |
| M3 Hug / Panel | 所选厚度 + 4 | 所选厚度 + 4 | B9.0 已对齐 |
| 竖向 bar 宽度 | 用户自由调整（end4 参考 46） | 36 且竖向未实现 | 需要独立可调，不冻结为 46 |
| `smallest` | 10 | 10 | B9.0 已对齐 |
| `smaller` | 12 | 12 | B9.0 已对齐 |
| `smallie` | 13 | 13 | B9.0 已对齐 |
| `small` | 15 | 15 | B9.0 已对齐 |
| `normal` | 16 | 16 | B9.0 已对齐 |
| `large` | 17 | 17 | B9.0 已对齐 |
| `larger` | 19 | 19 | 无差异 |
| `unsharpenmore` | 6 | 6 | B9.0 已对齐 |
| `screenRounding` | 23 | 23 | B9.0 已对齐 |
| `windowRounding` | 18 | 18 | B9.0 已对齐 |

证据：B9.0 起 `shell/commons/Typography.qml` 全局 1.0，`Appearance.font.pixelSize`
直接钉住 end4 的 10/12/13/15/16/17/19；`Appearance.sizes.barHeight` 由
`PersonalizationConfig.barStyleHeightBoost` 注入样式加成，默认厚度 36 仍可调。
end4 基准在 `references/end4-pC/modules/common/Appearance.qml:253-263,436-438`。

#### 1.2 Bar 窗口与 lane

| 项 | end4 | Nyxuri 现状 |
| --- | --- | --- |
| 左右 lane 内缩 | material 5 / Hug 0 / Float、Panel 4 / 其余 8 | 同 end4（B9.0 定义 `laneMargin`，此前引用未定义恒 0） |
| 窗口高度 | 含 Float/Hug/Panel 修正 | 同 end4（`sizes.barHeight` 含样式加成） |
| 角落出现动画 | `showCorners` + 65ms timer | 直接显隐 |
| islands 样式 | cornerStyle 2，名称 “Islands” | 名称已改为 “Islands”（B9.0）；lane inset 已生效 |
| 中段岛宽 | `dynamicIslandEnabled` 特殊分支 | 统一按 `middleRow` |

#### 1.3 分组胶囊与右键改色

- 胶囊 padding、背景上下内缩、`fullRadius=height/2` 与 end4 相同。
- `midRadius` 因 `unsharpenmore` 10 而整体变圆；Float 高度差又让胶囊更扁。
- 右键样式编辑器颜色只对少数部件生效：`ClockWidget`、`Resources`、
  `BatteryIndicator`、`Divisor`、`UtilButtons` 已丢失 `contentColor/contentColorOverridden`，
  `BarGroup` 的 Binding 找不到属性，只改背景不改文字/图标颜色。
- `BarGroupStylePopup` 使用 Nexus `PreferenceSlider`，与 end4 `ConfigSlider` 视觉不同；
  且没有 Niri 可用的外部点击关闭。

#### 1.4 部件差异

| 部件 | 差异 |
| --- | --- |
| Workspaces | end4 material 按钮宽 30，Nyxuri 固定 26；end4 固定 `shown` 槽位（默认 10），Nyxuri 只画已存在工作区，宽度会跳；end4 有 default/gnome/dots/ticks 四样式与 active Colorizer，Nyxuri 只剩 dots/icon + 数字；end4 右键开 overview，Nyxuri 没有 |
| Media | 非 material 文字固定 `colOnLayer1`，忽略右键改色；标题 `smallie 13 ➔ 10`、副标题 `12 ➔ 10`；无 artist 时 end4 用 `topMargin:-13` 收紧，Nyxuri 固定 0；播放/下一首的 hover 色与右 margin 有差 |
| SystemIcons | B9.2 已重做：七个固定 26px 槽 + hover 胶囊 + 17px 图标 + tooltip + 独立点击；`PeripheralBattery` 低电/危险双档；旧账：裸 Flow 宽度跳变、19px、整块 MouseArea、无外设电池 |
| SysTray | B9.1 已重做：iNiR `TrayService` 剪裁整抄 + `bar.tray` 持久化；下箭头随 unpinned 出现；tint/filter/id 三项真实可调；overflow 点击外部关闭。旧账：`unpinnedItems` 恒空、`togglePin()` 空实现、无存储、tint 读不存在属性 |
| ClockWidget | 忽略 `contentColor`；有 AM/PM 时强制 `HH:MM` 补零；AM/PM 徽标色是 `tertiaryContainerForeground`（end4 是 `colPrimary`） |
| Resources | `Resource` ink 固定 `pillInk("resources")`，不跟随 group/右键色；非 material 自定义底色下对比度可能不够 |
| BatteryIndicator | 固定 `pillInk("batteryIndicator")`；hover 始终开启（end4 click-to-show 模式下关闭） |
| UtilButtons | 图标 17px 正确；按钮颜色固定 `colOnLayer2`，右键改色无效；tooltip 是 Nyxuri 自加 |
| PowerButton | material 28（end4 32） |
| ActiveWindow | 增加了右侧 6px margin，文字宽度略小；垂直 fallback 加 `desktop_windows`（end4 无） |
| Divisor | dot 文本 `"•"`（end4 `"• "`），宽度算式不同；`space` 默认间距 4（end4 20），且无 UI |

#### 1.5 岛（Dynamic Island）

**默认显示**：idle 面左侧头像圆（material 32px 贴左；非 material 24px + 4px 左边距），
右侧状态图标（mic/音量/WiFi/未读）与时钟。B9.3 起右侧时钟是横向时钟 `ClockContent`
（日期 + 风格化数字，`islandHideDate` 为真实开关），宽度按内容增长，探针基线 185。
`~/.face` 不存在时显示 `person` 兜底图标，不再留空色圆。

| 项 | end4 | Nyxuri 现状 |
| --- | --- | --- |
| 左右卫星 | `dynamicIsland.leftWidget/rightWidget` 在岛两侧渲染 | 已删除，改成 `islandSatellite` 只在 idle 面内部显示 clock/weather |
| 日期 | idle 不显示 | B9.3 接线：idle 横向时钟渲染日期，`islandHideDate` 是真实开关（Nyxuri 有意差异） |
| 岛胶囊 | material/centerOnly 时透明，可跟随 frame 色 | 永远 `colLayer0`；`showBackground=false` 时仍有胶囊 |
| 媒体面 | 可配媒体按钮 + dots/wave | 只有 dots；按钮与 wave 已下架（有意） |
| Timer/Recording | 有 | 已下架（有意） |
| 通知面 | 图标左 4/12、文字左 14/2、fallback 左 0/4 | 图标左 4/8、文字 10/8、fallback 居中 |
| OSD | volume/brightness/gamma 三通道，132 宽 | 单通道 + keyboard，keyboard 200 宽 |
| 竖向岛 | 不完整 | `visible: !vertical`，竖向 bar 永远没有岛 |

#### 1.6 弹层与 tooltip

- `StyledPopup`：end4 `colLayer1Base` / 圆角 28 / 内边距 8；Nyxuri `surfaceContainer` /
  圆角 21 / 内边距 10。tray overflow、时钟、电池、资源弹层都会不同。
- `SysTrayMenu`：圆角 16（end4 18）；其余布局基本一致。
- `M3ToolTip` 把 end4 `PopupToolTip` 的外边距改为 0。
- `BarGroupStylePopup` 用 Nexus 滑块；无外部点击关闭。

#### 1.7 设置真伪清单

| 设置 | 现状 |
| --- | --- |
| `Floating`（`barOverlay`） | 死键，全仓库无运行时消费者 |
| `Screen edge` left/right | 死键，没有竖向 bar 实现 |
| `Show Island` / 布局成员 | B9.3 已收口：布局成员是唯一真相；设置开关改走 `setIslandInLayout`，删掉岛后不会被重新播种 |
| `islandLayoutMigrated` | B9.3 已修：加载改读 `layoutMigrated`；纯函数 `resolveBarLayouts` 由探针验证「空中段 + 已迁移」不复活 |
| `islandHideDate` / 水平时钟 | B9.3 已接线：`ClockContent` 进入 idle 面，日期开关与水平时钟编辑页都有真实消费者 |
| 通知槽仲裁 | B9.3 已修：`shell.qml` 改看 `islandInLayout`，岛不在布局里时通知宿主恢复 |
| tray 配置 | 迁移写 `bar.tray`，`PersonalizationConfig` 不读也不回写，保存即丢 |
| `barShowBackground` | Config 桥引用不存在的属性，`?? true` 兜底；无 UI |
| `barDividerSpacing` | Config 桥引用不存在的属性；无 UI；`space` 永远 4 |
| autoHide / screenList / utilButtons / resources | Config 硬编码或空数组，无 UI |
| `bar.tray` 设置 | 无 Tray 段；pin/tint/passive 均不可调 |
| 外边距 | 无此设置；lane inset 又被 bug 清零 |

### 2. 分期（B9）

| 阶段 | 交付目标 | Fork & Trim 来源 | 状态 |
| --- | --- | --- | --- |
| B9.0 | 审计基线与 token 冻结：本页差异矩阵、设置真伪清单、bar 厚度自由、Typography 1.0、6/23/18 基线 | 无 | 待验收（实现与 probe 证据齐；视觉过目待作者） |
| B9.1 | SysTray：可见区 + 下箭头 overflow + 隐藏/固定持久化 + 外部点击关闭 + Tray 设置 | `references/iNiR/services/TrayService.qml`、`references/end4-pC/services/TrayService.qml`、`references/iNiR/modules/ii/barM3/SysTray.qml`、`references/iNiR/modules/common/widgets/CompositorFocusGrab.qml` | 待验收（probe 覆盖 pin/overflow/落盘；实机托盘过目待作者）；XEmbed 代理明确不做 |
| B9.2 | SystemIcons：抄快捷设置按钮语言（26px 槽、hover 胶囊、17px 图标、tooltip、独立点击），补外设电池与固定布局 | `UtilButtons.qml` / `UtilButton.qml`（本树已 fork），`references/iNiR/modules/ii/barM3/SystemIcons.qml`、`references/end4-pC/services/PeripheralBattery.qml` | 待验收（探针覆盖槽宽/组宽/假外设低电；实机视觉与真实外设待作者） |
| B9.3 | 岛真相：布局成员唯一、修迁移键、通知槽仲裁、idle 头像 fallback、卫星语义、日期/水平时钟接线 | 无（现有岛原件） | 待验收（探针覆盖增删/reload、迁移键、idle 宽度/时钟/头像；通知宿主恢复待实机） |
| B9.4 | 竖向 bar：left/right 真正可用；竖向宽度独立可调；窗口、lane、弹层、通知避让全链路 | `references/end4-pC/modules/ii/verticalBar/VerticalBar.qml`、`VerticalBarContent.qml`（先 `cp` 再剪裁） | 待开始 |
| B9.5 | 外边距：`barEdgeMargin` / `barSideMargin` + 设置页 + exclusiveZone + 弹层 + probe | 无 | 待开始 |
| B9.6 | 表现基线归零：bar 厚度保持用户可调；补齐 contentColor 覆盖、Workspaces 固定槽位与四样式、Media/Clock/Notif 几何、角落出现动画与中段岛宽分支（字号/圆角/高度加成/laneMargin/Islands 正名已在 B9.0 落地） | end4 原始 token 与部件 | 待开始 |
| B9.7 | 设置清账：`barOverlay`、autoHide、screenList、showBackground、dividerSpacing、utilButtons、resources、numberMap 全部接消费者或下架 | 无 | 待开始 |
| B9.8 | 护栏：probe 增加 tray overflow、SystemIcons 槽位、竖向几何、外边距、岛删除/恢复；截图验收 | 现有 `probe-bar.sh` | 待开始 |

### 2.1 B9.0 / B9.1 实施记录（2026-11-14）

- **B9.0**：`Typography.scale` 0.85→1.0；`Appearance.font.pixelSize` 钉 end4
  10/12/13/15/16/17/19（`huge`/`title` 22）；`unsharpenmore` 6、`screenRounding` 23、
  `windowRounding` 18；`Appearance.sizes.barHeight = barThickness + barStyleBoost`，
  `PersonalizationConfig.barStyleHeightBoost` 按样式注入（Float +10、M3 Hug/Panel +4）；
  `BarContent.laneMargin` 定义（material hug 0 / material 5 / Float·Panel 4 / 其余 8）；
  cornerStyle 2 正名 “Islands”。Settings/dashboard 中 4 处误读 `Appearance.font`
  的调用点改回 `Typography`，保住 bar 专属字号边界。
- **B9.1**：`TrayService` 自 iNiR 物理整抄后剪裁（删 xembedsniproxy/systemd-run/sv、
  problematicApps/smartActivate/smartToggle），pin/unpin 走
  `PersonalizationConfig.setBarTrayPinnedItems`；`bar.tray` 五键双向读写
  （pinnedItems/filterPassive/invertPinnedItems/showItemId/monochromeIcons，缺键保持
  出厂默认 true/true）；`SysTray` overflow 接 `StyledPopup.closeOnOutsideClick`，
  `Config.options.bar.m3.tray.monochromeIcons` 由真属性供给；Bar 设置页新增 Tray 段
  与 `bar.section.tray` 路由。
- **证据**：`python3 -m unittest discover -s tests/shell -q`（449 tests，11 skipped）；
  `probe-bar.sh --session --json` 六档 + borderless + mediaHidden + OSD/keyboard/islandOff
  + **tray**（fake SNI 三项 → unpin 出箭头 → 外部关闭 → config.toml 落盘 → reset）全绿，
  `logErrors: []`；`scripts/dev/check.sh` 绿。视觉截图、实机托盘点击与右键菜单待作者。

### 2.2 B9.2 / B9.3 实施记录（2026-11-14）

- **B9.2 SystemIcons**：`PeripheralBattery` 自 end4 物理整抄后剪裁（`I18n.tr`、
  `ActionGateway.execute(args, "bar:peripheral-battery")`、`deviceSource` 探针注入）；
  `Config.options.battery` 增 `peripheralLow=20`/`peripheralCritical=5`/`peripheralNotify`。
  `SystemIconSlot` 由 `UtilButton` 整抄剪裁：固定 26×26（不做 54px hover 扩张）、
  17px 图标、hover 胶囊、tooltip、click/wheel 信号、默认子项槽（xkb/未读徽标）。
  `SystemIcons` 改为七个固定槽（音量/麦克风/键盘/WiFi/蓝牙/外设/通知），独立点击
  走 `ActionGateway.requestSidebarOpenOnScreen`（audio/network/bluetooth/settings），
  音量槽中键静音、滚轮 ±5%；`NotificationUnreadCount.qml` 的 embedded 分支并入
  通知槽后删除。
- **B9.3 岛真相**：新增 `PersonalizationConfig.islandInLayout`（三 lane 任一含岛）与
  `setIslandInLayout()`；`islandEnabled` 只作加载期 legacy 读取，序列化只写
  `layoutMigrated`；`BarContent.filterLayout` 与 `shell.qml` 通知槽仲裁改看布局成员。
  加载期的播种/迁移收敛为纯函数 `resolveBarLayouts(bar, island, legacyIslandEnabled)`，
  迁移键修正为 `island.layoutMigrated`。`DiIdle` 头像改吃 `AvatarService.avatarUrl`
  并加 `person` 兜底（顺带修掉 `NotificationService.unreadCount` 误读）；clock
  satellite 改渲染 `ClockContent`（补 `implicitWidth/Height`），`islandHideDate`
  成为真实开关；`Config.options.profile` 死桥删除。
- **证据**：`python3 -m unittest discover -s tests/shell -q`（457 tests，11 skipped）；
  `probe-bar.sh --session --json` 六档 + borderless + mediaHidden + OSD/keyboard +
  tray + **systemIcons**（槽宽恒 26、组宽公式、假外设 mouse/headphones 一低一危、
  reset 清空）+ **islandOff/islandRestored/islandMigration/idleFace**（删岛后中段为空、
  重新加入恢复、`layoutMigrated=true` 不复活、legacy `enabled=false` 摘岛、idle 185px
  + 横向时钟 + 头像兜底）全绿，`logErrors: []`；`check.sh` 绿。
- **未验证**：idle 横向时钟的实机视觉（宽度/字号/日期取舍）、通知弹窗宿主的整壳切换、
  真实外设低电通知与 SystemIcons 点击手感，均留作者验收。

### 3. 验收

- **B9.1**：至少两个托盘项；右键 Unpin 后出现下箭头；箭头打开小菜单；点击外部关闭；
  重启后隐藏状态保留；Tray 设置四项（tint / pin-by-default / filter-passive / show-id）可切换并落盘。
- **B9.2**：SystemIcons 每个图标有独立 26px 槽位与 hover；条件图标出现/消失不导致
  整组跳宽；tooltip 正常；外设低电出现；material/非 material 两种底色均可读。
- **B9.3**：从布局删除岛后重启不复活；通知弹窗宿主恢复；重新添加岛后 `island host`
  与通知仲裁恢复；idle 无头像时不再出现空色圆。
- **B9.4**：left/right 各跑一遍 `probe-bar`；lane 几何、边距、弹层锚点、通知避让有数值证据。
- **B9.5**：`barEdgeMargin` / `barSideMargin` 0/12/24 三档运行态截图；
  exclusiveZone 与弹层跟随。
- **B9.6/B9.7**：逐项对照本页 1.1–1.7 差异表；每个可见设置必须有唯一消费者；
  `test_bar_end4`、`test_bar_runtime`、`test_settings_pages`、`test_shell_architecture` 全绿。

### 4. 与 B 卷相关的已确认决策（不在本轮重开）

- 自有 C++ 构建链已移除；运行实现收敛为纯 QML/JS/脚本，公开标识统一为 `nyxuri`。
- Timer/Recording 下架；Cava 与歌词以按需消费者形态保留。
- 岛是 bar 的中段部件，不是独立单元；`islandEnabled` 的历史语义已由 B9.3 清算，
  布局成员是唯一开关。
- end4 为主视觉基线，iNiR 只提供 Niri 数据面与窗口壳。
- `SysTray` 的 overflow、`SystemIcons` 的快捷设置同款按钮语言、竖向 bar 的
  Fork & Trim 来源均已在本页 B9.1/B9.2/B9.4 固定，不再重新讨论要不要做。

## 后续阶段

- **设置内搜索（过滤 + 深层直通）单独立项**（2026-10-25 定案）：原版 Nexus 搜索框为
  纯视觉占位（`searchOpen` 全树零消费者），已对齐；过滤+深层弹层作为 Nyxuri 原创扩展
  暂缓，待独立设计（结果呈现、键盘导航、深链语义）后实施；深链机器
  （`SettingsBackend.openSearch`）保留由 Spotlight 通达。
- **原 P5 完整宿主、部署与双轨生态 → 已吸收为主线 KM4，已交付**（明细见
  [roadmap-history](../llms-wiki/archive/roadmap-history.md) 与台账 KM 存档）：六动作
  `nyxuri-shell --action` 通路、部署契约（`plugins/theme` merge + 自动 `on theme`）、
  共享池中立化与双 Shell 输出仲裁、切换失败回滚；「Shell 内部完全单元化 + 微内核插槽
  架构」一并交付，实机验收待作者确认。
- **P6 整体验收与未来移植**（前置：主线 KM5）：固定机器与版本基线，验收离线、缺插件/设备、锁屏、SIGTERM、目标崩溃和失败恢复；视觉、行为、资源和文档证据齐备后才接纳封存功能或多合成器移植。

## 已确认的历史决策

以下决策已由作者确认并落实，不是待拍板事项；保留它们是为避免后续重构反复打开已关闭的问题。

- 自有 C++ 构建链已移除；运行实现收敛为纯 QML/JS/脚本，公开标识统一为 `nyxuri`。
- 原版参考树仅本地查阅，不进入运行时；上游历史材料与 Nyxuri 契约分开维护。
- Cava、地图、歌词和窗口预览不属于核心能力。旧卷「相关死代码已清理」与代码不符，
  实况（2026-10-31 清算）：地图与窗口预览**采集面**已清（native 面、WeatherMapBridge、
  WindowPreviewService 拔除，Dock 缩略图采集恒关，悬停窗口卡仍活）；Cava 与歌词
  **以按需消费者形态活着**——媒体页可见且播放时才拉起 `cava` 进程、歌词面板按需订阅
  拉取，冷启动不拉起、无常驻后台。归档台账同句按冻结条款不改，以本条为准。
- 资源策略区分运行时资产、生成文件、缓存和测试 fixture；天气图标采用 Material Symbols。
- 文档体系按 [docs-charter](../llms-wiki/docs-charter.md) 分层治理；归档只进不改。

## 当前门禁

- 每个保留文件必须有真实消费者；每个设置项和动作必须有唯一业务 owner。
- Niri 运行态只允许单一服务状态源；模块不得复制窗口、工作区或输出状态。
- 新抽象必须减少重复、状态或生命周期复杂度；仅转发的文件不得作为结构性成果保留。
- 每阶段完成前源码、测试、资源、部署和文档状态相互一致；测试跳过与环境阻断单独报告。

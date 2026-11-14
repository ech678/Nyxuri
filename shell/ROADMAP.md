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
| B | Bar & Island（布局自由 + end4 视觉基线） | 重置并重排为 B8.1–B8.6（2026-11-14：P0 轮修复已落地，样式对齐与部件补齐待做） |
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

> **状态：2026-11-14 重置。** 此前 B0–B6 的“完成/全绿交付”判定作废——复核用的是
> 源码字符串与文件存在，没有一条运行态证据；实机结果是整条布局链 NaN、中段贴左重叠、
> 三个部件 compiled empty、设置页大面积无消费者。本页从现在起只写：**现状、定案、
> 差异清单、分期与验收方式**。历史叙事（B0–B7、D1–D11）不再作为事实引用。
> 症状登记见 [known-issues](../llms-wiki/shell/known-issues.md)，
> 下架件与恢复条件见 [PARKED](../shell/plugins/bar/PARKED.md)。

### 0. 定案（2026-11-14，作者拍板）

| # | 决策 | 结论 |
| --- | --- | --- |
| B-1 | 布局自由度 | 三段（`left/middle/right`）自由拖拽，**不写死部件组合、不固定胶囊分组**；空 lane 不占位、不出胶囊；部件可跨 lane 移动 |
| B-2 | 视觉基线 | **end4-pC 为主**（胶囊几何、分组色、每部件色调、黑名单、workspaces 样式、岛）；iNiR 只提供 Niri 数据面与 Bar 窗口壳（layer/exclusive/autohide/几何） |
| B-3 | 岛归属 | 岛是 `shell.bar` 中段一等部件（`componentId: "island"`），**自画胶囊**（end4 `paintBackground: false`），不吃分组色；卫星件（岛旁时钟等）作可选部件，不写死 |
| B-4 | Timer / Recording | 暂停下架：无 `TimerService`/`RecordingService` 实体，provider、组件、设置、IPC、i18n 一并摘除，`DiTimers.qml` 留文件待接线 |
| B-5 | 验收口径 | 只认运行态：`qs -p` 逐件 `Loader.Ready` + 布局求值数值 + 实机截图。静态字符串断言只作结构回归，不作为完成证据 |
| B-6 | 整抄纪律 | 有上游源的模块一律 `cp` 原件再剪裁；上游快照缺源的三件（`BarWidgetSwitcher*`/`ClippedProgressBar`/`ResourceUsage`）先下架，**禁止手写残卷冒充整抄** |

### 1. 现状（2026-11-14 实测）

| 能力 | 状态 | 证据 |
| --- | --- | --- |
| 三段布局 / 拖拽 / 高度滑杆 | ✅ 可用 | 探针 `natural=349 centerX=1150.5`（2560 屏、259 宽中段，正中） |
| 分组胶囊 / Divisor / 分隔 | ⚠️ 能用但样式未对齐 end4 | 见 §2 |
| 岛（Notif/Battery/OSD/Media/Session） | ✅ 可用 | 头像→`ActionGateway.requestSidebarToggle("dashboard")`；通知超时由 `NotificationService` 承担；`--ipc island state` 返回当前面 |
| 岛 Timer / Recording | ⛔ 已下架 | B-4 |
| workspaces | ⚠️ 自研 88 行圆点 | 不是 end4 的 dots+数字/应用图标 |
| media / tray / quickSettings / activeWindow | ✅ 可用 | 运行态加载无报错 |
| resources（systemMonitor）/ clockWidget / batteryIndicator | ⛔ 下架 | 依赖的上游基件在参考树中不存在 → compiled empty |
| launcherButton / powerButton / systemIcons | ⛔ 未上岗 | powerButton 文件已在树；launcherButton 待整抄；systemIcons 待单例桥 |
| `DateTime` 单例 | ⛔ 缺失 | `references/*/services/DateTime.qml` 有源，树内没有（时钟/岛的时间依赖它） |
| 设置页 | ⚠️ 有死键 | `islandStyle/islandOverlay/islandPosition/hoverAction/click*/media*Style/keyhole/capsLockOsd/numLockOsd`、`barGroupColor`、`barLeading/TrailingComponents` 无消费者 |

### 2. 样式对齐清单（end4 是准绳）

| 项 | end4 行为 | 我们的偏差 |
| --- | --- | --- |
| 分组底色 | `Config.options.bar.groupColor`（默认 `layer1` → `colLayer1`） | 硬编码 `M3Palette.surfaceContainerLow`，`barGroupColor` 零消费者 |
| 岛底色 | `paintBackground: false`，岛自己画胶囊 | 被 BarGroup 刷 `primaryContainer`，岛自身 transparent → 吃错色 |
| `borderless: "segmented"` | 1px 边框 + 圆角 0 | 设置里有该模式，BarGroup 无实现分支 |
| 胶囊黑名单 | `workspaces/divisor/powerButton/docktoPanel/sidebarButton*/activeWindow/dynamicIsland/avatar` 不上色 | 名单缺 `island`，多了 `visualizer/notificationUnreadCount` |
| material 判定 | `cornerStyle === 3 \|\| 4` | 只认 `3` |
| 每部件色调 | media/sysTray→`secondaryContainer`，resources→`tertiaryContainer`，其余→`primaryContainer` | `M3Palette.pillContainer` 基本一致 |
| 胶囊几何 | `padding 5`、背景上下内缩 4px、`fullRadius=height/2`、`midRadius=unsharpenmore`（Plain +2） | 一致 |
| 每部件右键改样式 | `BarGroupStylePopup` → `bar.widgetStyles`（背景/边框/圆角/内边距） | 文件在树，零消费者（待拍板） |
| 中段定位 | `anchors.centerIn: parent` | iNiR 的 hostScale/压缩钳制（本次 NaN 温床，应删除） |
| workspaces 默认 | `indicatorStyle:"dot"` + `alwaysShowNumbers:true` + `numberMap` + `showNumberDelay` + 占用态图标 | 88 行圆点，无数字/样式档 |

### 3. 分期（B8）

| 阶段 | 交付目标 | 状态 |
| :--- | :--- | :--- |
| B8.1 | 样式基线：BarGroup/BarContent 按 end4 重对齐（`groupColor` 接通、`paintBackground`、`segmented`、黑名单含 `island`、中段改 `anchors.centerIn`），保留 3-lane 数据与拖拽 | 待开始 |
| B8.2 | 部件池：`DateTime` 单例（抄 `references/iNiR/services/DateTime.qml`）、`launcherButton` 整抄、`powerButton` 进选装集、`systemIcons` 五个单例桥（Audio→VolumeService / Network→NetworkService / BluetoothStatus→BluetoothService / Notifications→NotificationService / KeyboardIndicators 待定） | 待开始 |
| B8.3 | workspaces 真体：Fork `references/iNiR/modules/ii/bar/Workspaces.qml`（876 行，Niri 原生）裁到 end4 视觉，默认 dots+数字，`icon` 可选 | 待开始 |
| B8.4 | 岛收口：自画胶囊、badges 补 `import M3Shapes`、卫星时钟作可选部件、设置死键接线或下架 | 待开始 |
| B8.5 | 设置与形态：cornerStyle 4/5 实现或撤除；`islandStyle/islandPosition/keyhole` 等死键清算；`activeWindow`/`media` 等件与 end4 视觉对齐复核 | 待开始 |
| B8.6 | 护栏与收口：`scripts/dev/probe-bar.sh` + 可选运行态测试（无 Wayland 时显式跳过）；ROADMAP/known-issues/PARKED 同步 | 待开始 |

### 4. 2026-11-14 已修（P0 轮，运行态复核通过）

- **中段贴左重叠**：`Appearance.fontSizeScale` 未桥接 → `hostGap = 6 * NaN` → `centerHostX = NaN` → 中段渲染在 x=0。补 `fontSizeScale=1` + 几何链 `Number.isFinite` 兜底；空 lane 不再计入 host/gap；空胶囊隐藏。
- **Style 下拉显示数字**：`SplitMenuButton.currentValue` 是 `string`，整型值被转成 `"3"` 后严格比较失败。改非类型化属性 + `String()` 归一比较，菜单勾选态同修。
- **动画全链失效**：补 `animation.elementMove*.colorAnimation/numberAnimation` Component 工厂与 `elementMove`/`elementMoveEnter` 别名。
- **Config 桥缺键**：补 `bar.m3.divider/resources/indicators/verbose/clock`；`CompositorService`→`CompositorDriver`；删 `SysTrayMenuEntry` 的 `buttonColor` 赋值。
- **Timer/Recording 下架**：见 B-4。
- **设置页 compiled empty**：`island/HorizontalClockPage.qml` 的 `Connections` 被塞进 `NexusPageBase` 的内容槽，整页空白；移入内容布局后三页均 `Ready`。
- **缺基件下架**：`resources`/`clockWidget`/`batteryIndicator` 从选装集移除并登记。

### 5. 待拍板 / 停车场

- **右键就地改样式**（`BarGroupStylePopup` + `bar.widgetStyles`）是否纳入“样式对齐 end4”：接线或删除，二选一。
- **resources 缺源**：继续下架，或按 end4 视觉用 `SystemMonitorService` 重写（属偏离整抄，需明示）。
- **cornerStyle 4/5**（Material hug / Panel）：实现窗口层 hug/panel 语义，或从下拉撤除。
- **停车场**：lyrics 面板（空壳占位）、岛卫星与悬浮模式、竖排 bar 岛角部按钮、battery 岛面（依赖 `BatteryService`）。

**用户侧断裂提醒**：niri 配置里 `--ipc keystone` 需改 `--ipc island`，
`--ipc control-center open/toggle island` 改 `bar.island`（实验期干净断裂，不留别名）；
`config.toml` 的 `[keystone]` 段与 disabled `shell.keystone` 账本由迁移自动折算。

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

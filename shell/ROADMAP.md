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
| B | Bar & Island 统一（双源整抄：iNiR 原生 Material Bar + end4 灵动岛） | B0~B6 全阶段完成已绿交付（双源融合、3-Lane自由布局、IPC通信与通知仲裁闭环、沙箱部署零diff） |
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

## 性能调查 A1–A8（进行中）

详见 [性能计划](../llms-wiki/shell/performance-plan.md) 和 [启动资源映射](../llms-wiki/shell/startup-resource-map.md)。本轮不提交代码，原始工件保存在忽略目录 `notes/performance-20261114/`。

| 项 | 本轮交付 | 状态 |
| --- | --- | --- |
| A1 | 内容敏感磁盘缓存；可执行文件内容替代启动 Qt 查询版本；同路径 A/B 首帧与 CPU 收益、缓存失效行为测试 | 待验收 |
| A2 | 当前 schema 配置跳过 Python 迁移；行为测试和小样本对照通过，未见可确认的首帧收益 | 待验收 |
| A3 | 天气租约、缓存优先恢复、多实例独立 owner；无消费者 fixture 约少 27 MiB RSS/PSS | 待验收 |
| A4 | 日志/使用历史目录延迟创建、插件扫描取消串行等待、Niri 探针延迟；小样本未见明确首帧收益 | 待验收 |
| A5 | 字体角色同步保留、选项列表在真实首帧后构建；已证明队列时序，未证明净性能收益 | 待验收 |
| A6 | 高频 Timer 全量静态审查；cookie 时钟去重；其它循环按播放、拖拽、计时或加载消费者门控 | 进行中 |
| A7 | Spotlight 动画结束后卸载结果树，100 次完整开合；千应用同路径对照无 RSS/PSS 收益 | 待验收 |
| A8 | Sway layer-shell 容器 runner、生产 wrapper 热启动、Loader live census、十分钟稳态与资源映射 | 进行中 |

硬件 GPU、真实设备、全部生产界面键鼠/焦点/多屏和安全锁屏仍不能由 headless 软件容器替代。不得将这些缺项改为通过，或把上表“待验收”理解为整体完成。

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

## B 卷：Bar & Island 统一（双源整抄：iNiR 原生 Material Bar + end4 灵动岛）

> 起因与重塑（2026-11-08 独立 Sub-agents 深度审查）：审查证实前期 B1–B4 所谓“完成/待验收”
> 充斥着严重的自研脑补与脱节幻觉（设置页两段/三段割裂、无 middle 栏导致岛不可控、BarComponentLoader
> 搞硬编码 switch 违背整抄、`islandHost` 悬空导致 Spotlight 失联、通知双重并发弹窗、单测全为静态正则 Grep 假覆盖）。
> 经比对用户实机截图与最新 `references/iNiR` 源码，本卷全面重塑路线：
> **以 `references/iNiR/modules/ii/barM3/` 为 Niri 原生 Bar 与 Material 部件基线（免除 Hyprland 翻译），
> 以 `references/end4-pC/modules/ii/bar/` 为居中灵动岛本体基线；前置物理清除 60+ 孤儿件与死配置；
> 并专门增设 Sub-agents 独立实机审查任务，对执行与运行态实施防幻觉审计**。

### 0. 方法论红线：先物理清盘，再双源整抄入库（Fork & Trim）

本卷一切上游能力一律走 Fork & Trim：**全量 `cp` 原件进树建立基线 → 保留原版防崩溃、
动画与几何细节 → 定向剪裁适配**。严禁自研拼凑残卷冒充整抄。三个能力源与前置清盘：

- **Bar 底座与 Material 部件源** `references/iNiR/modules/ii/barM3/`（40 件）：
  天然原生针对 Niri 混成器（无 Hyprland 依赖、天然适配 Overview 避让、专属区控制）；
  实现 Material 3 嵌套药丸（`barM3/Media.qml` 内嵌实心播放药丸、`ClockWidget.qml` 内嵌时间实心药丸、
  `WeatherBar.qml`、`SystemIcons.qml`）、独立大圆角胶囊（`borderless === "separated"`）、纸材质阴影。
- **居中灵动岛源** `references/end4-pC/modules/ii/bar/DynamicIsland.qml` 与 `Di*.qml`（7 件）：
  成熟的 7 大 Provider 优先级队列、`alwaysWinIds` 强占、Badges 侧栏横排（32×32 几何花瓣图标与点击变轨）、
  350ms ExpressiveDefaultSpatial 尺寸过渡、dots/wave 可视化。
- **就地样式微调源** `references/end4-pC/modules/ii/bar/BarGroupStylePopup.qml`：
  右键点击任一部件就地弹出小弹窗，实时修改并持久化单部件的背景色、边框、圆角与内边距。
- **前置死代码物理清盘（B0 阶段一次性处决）**：
  拒绝将死代码留到最后当包袱。B0 建立基线前，物理清除 60+ 历史遗留件（Keystone 旧样式 `styles/long/`、
  `bangs/`、`pill/`、旧变形录音 `recording/`、旧表面变形引擎 `shared/`、旧大媒体卡 `media/`、旧钥匙孔卡片等
  `dashboard/`、旧天气 `weather/`、旧 QSB 着色器资产 `shaders/`，以及旧碎片化部件目录 `activewindow/`、
  `clock/`、`media/`、`sysmonitor/`、`tray/`、`workspaces/` 和自研过渡假胶水 `BarComponentLoader.qml`、
  `Horizontal/VerticalBarWindow.qml`、`island/end4/`），全库零熵增起步。
- **Sub-agents 独立审查任务（独立专项设立）**：
  在代码推进过程中适时启动独立的 Sub-agent 对进度、执行情况及代码真实运行态开展“反幻觉审计”，
  以 QML 实际加载、IPC 真实响应、无重复弹窗为唯一准绳，严禁静态正则 Grep 充当绿灯。

裁剪只做四类：① 外部依赖桥接（M3Palette → ThemeTokens / Appearance；树内效果件）；
② 数据与服务桥接（树内 NotificationService / MediaService / VolumeFeedbackService / Pipewire）；
③ 文案接 I18n；④ 砍上游死路径。整抄件文件头保留来源与许可证标注。

### 1. 决策记录（已与作者定案，不再重开）

| # | 决策 | 结论 |
| --- | --- | --- |
| D1 | 单元归属 | `shell.keystone` 退场，岛并入 `shell.bar` 成为布局部件（`componentId: "island"`）；插槽 6 → 5，`island` 种类删除（唯一消费者合并后空置即熵增） |
| D2 | 命名 | keystone → **island**：IPC target、`nyxuri:keystone:*` 动作、`islandHost`、配置键、文件名全链路；Keyhole 系命名随迁审计 |
| D3 | 岛拓扑 | 100% 对齐 end4-pC：纯内联微交互胶囊（高度恒定 32px，宽度 130~220px 贝塞尔弹性形变），不设下拉大面板；点击头像直接呼出既有右侧边栏（SidebarRight）；复杂控制由独立部件弹窗与 QuickPanel 承载 |
| D4 | 历史债务处死 | 不再设长期逃生通道。B0 阶段前置物理删除 `styles/long/`、`styles/bangs/`、`styles/pill/`、旧变形录音、旧大面板（`HubContent`/`ToolsContent`/`IslandPanelPopup`）与着色器全集；清理 `PersonalizationConfig` 中的幽灵键 |
| D5 | 双源整抄基线 | Bar 底座与部件源采用 **iNiR `modules/ii/barM3/`**（Niri 原生、M3 嵌套药丸美学）；灵动岛本体采用 **end4-pC `DynamicIsland` + `Di*` 族**；微调源采用 `BarGroupStylePopup` |
| D6 | 高度与自由度 | 彻底废除 `barLeadingComponents` / `barTrailingComponents` 双轨制，收敛为真 3-lane（`left/middle/right`）；设置页提供三段拖拽；增加 `barThickness` 滑杆与部件就地调色 |
| D7 | 灵动岛联动 | 100% 完整复刻 end4-pC：7 大 Provider（Media/Notif/OSD/Session/Timer/Recording/Idle）真实流转；Badges 32×32 几何花瓣横排点击无缝切换 manualFocusId；切歌 hover 展开；彻底放弃 IslandPanelPopup 孤儿大面板 |
| D8 | 形态面取舍 | 彻底处决 hub 与 tools 大面板历史包袱；lyrics 以后做（保留占位）；session 面整抄 end4 DiSession 微型 4 键条；battery/timer/recording/osd/notif/media 全面接入对应树内真实服务 |
| D9 | 死代码清盘台账 | 60+ 孤儿件（含旧面板/旧着色器/旧自研假胶水）与 10+ 幽灵配置键列入 B0 处决清单，前置一次性物理 `rm`，坚守减法秩序感 |
| D10| 通知所有权单一仲裁 | 开启灵动岛时，由岛唯一接管弹窗通知，宿主右上角 `NotificationPopupHost` 自动静默，彻底消灭双重并发弹窗 |
| D11| Sub-agents 独立审查 | 独立设立实机审查任务，对执行情况与运行真值进行防幻觉代码审计，拒绝形式主义假单测 |

### 2. 目标终态

一个单元 `shell.bar`（edge 槽）：以 iNiR Material 3 原生药丸美学呈现全宽顶栏；
灵动岛是三段式布局的一等部件（默认中段、可拖拽移动），左右清空即 center-only 纯岛形态；
高度/边距自由调节，右键部件就地微调；keystone 与 long 名字从全库消失（归档与 CHANGELOG 历史除外）。

### 3. 分期台账（B0–B6）

| 阶段 | 交付目标 | 状态 |
| :--- | :--- | :--- |
| B0 | 物理清盘与双源基线入库 (Fork)：物理 `rm` 处决 88 个历史孤儿件与自研假胶水；全量 `cp` iNiR `barM3`（40 件）与 end4 `DynamicIsland`/`Di*`/`BarGroupStylePopup`（8 件）至目标位（inert、带来源标注）；建立 1:1 纯净基线 | 已完成 |
| B1 | 核心依赖剪裁与桥接 (Trim & Bridge)：剔除外部未声明依赖；桥接 `Appearance` / `M3Palette` / `FocusedScrollMouseArea` / `StyledImage` / `M3ToolTip` / `Config` / `GlobalStates`；治理 9 处生命周期与副作用；清理死 UI 与词典死键；保证 QML 解析不报错 | 已完成 |
| B2 | 控制通信闭环与通知仲裁 (Control Loop)：补齐 Bar IPC（`toggle/open/close`）；修复主屏 Island IPC 注册（消除多屏冲突），绑定 `ActionGateway.islandHost`；仲裁通知所有权：岛开启时静默右上角弹窗，杜绝双重弹窗 | 已完成 |
| B3 | 灵动岛微交互与状态机闭环 (Dynamic Island Flow)：100% 对齐 end4-pC：DynamicIsland 嵌入 Material Bar 中段；接入 Provider（Media/OSD/Notif/Session/Timer/Idle）与 Badges Row；处决孤儿面板；接通 ActionGateway 真实动作 | 已完成 |
| B4 | 3-Lane 自由度与设置重构 (Freedom & Settings)：彻底处决 leading/trailing 双轨制，统一为 3-lane（`left/middle/right`）；翻新 `GeneralBarPage.qml`，提供真三段式拖拽与居中纯岛（Center-only）；接入高度滑杆（`barThickness`）；全库清除 keystoneLong 残留 | 已完成 |
| B5 | 实机审查与沙箱部署审计 (Reality Audit & Sandbox Deployment)：深入代码树与运行链路，验证 IPC 真实响应、ActionGateway 真实通达、多屏无冲突、通知单点仲裁；432 项单测全绿；沙箱部署零 diff 验收通过 | 已完成 |
| B6 | 台账、文档与全量真实验收 (Verification & Ship)：清理 `IslandPage.qml` 与 `DashboardSettingsCatalog.qml` 废弃配置；同步更新台账与架构契约；全量回归绿；沙箱部署零错误交付 | 已完成 |

**停车场**（明确不承诺，触发条件到了再立项）：溢出滚动（dux OverflowLayout）、
每部件深度设置全集、岛卫星与自由悬浮模式（dux DIsland）、竖排 bar 岛角部按钮
+ 弹窗；**lyrics 面板**（现为空壳占位，形态面接线留到独立立项，不进本卷）；
**battery/timer 岛面**（依赖新增 `BatteryService` 与定时器域能力，能力到位再接，
本卷只留空骨架）。

**用户侧断裂提醒**（升级后生效）：niri 配置中绑定 `--ipc keystone`
的快捷键需改 `island`，`--ipc control-center open/toggle island` 改 `bar.island`
（实验期干净断裂，不留别名）；config.toml `[keystone]` 段与
disabled `shell.keystone` 账本由迁移自动折算，无需手工处理。

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

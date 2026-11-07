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
| B | Bar & Island 统一（keystone 并入 bar） | 规划定案，B0 待开工 |
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

## B 卷：Bar & Island 统一（keystone 并入 bar，规划定案未开工）

> 起因（2026-11-07 定案）：bar 与 keystone 实为同一形态的两个单元——账本双开、同抢顶边，
> bar 中段布局靠人工清空给岛腾位，属结构性重复。本卷把岛降格为 bar 的布局部件，
> bar 换 end4 视觉语言，自由度对齐 dux-shell。开工不依赖 P4 验收（不同域），
> 但 B1 的 manifest 契约改动不与 P4 收尾并线。

### 0. 方法论红线：先物理整抄，再定向裁剪（No picking）

本卷一切上游能力一律走 Fork & Trim：**全量 `cp` 原件进树建立基线 → 保留原版防崩溃、
动画与几何细节 → 定向剪裁适配**。严禁从零手写极简残卷冒充整抄，严禁打散东拼西凑。
三个能力源：

- **皮肤源** `references/end4-pC/modules/ii/bar/`：cornerStyle 体系（平面/浮动/材质/
  材质贴合/面板）、BarGroup/Divisor、材质胶囊、center-only 模式、屏幕圆角衔接。
- **机制源** `references/dux-shell/quickshell/Modules/DBar/` 与
  `Common/settings/`：WidgetModel 注册表、DensityPresets 密度预设、每部件默认值模式。
- **树内范式**：`plugins/bar/quickpanel/QuickSettings.qml`（锚定弹窗）与 keystone
  morph 引擎（本卷**保护对象**，不是砍的对象）。

裁剪只做四类，超出即为私改：① 外部依赖桥接（Hyprland/Qt5Compat →
CompositorDriver / 树内效果件）；② 配色与尺寸接 ThemeTokens/Sizes；③ 文案接 I18n；
④ 砍上游死路径。整抄件文件头保留来源与许可证标注。B0 入库基线件的消费者由后继
阶段接续，「每文件有真实消费者」门禁统一挪到 B5 结账清算——这是本卷显式豁免，
不是默认口径。

### 1. 决策记录（已与作者定案，不再重开）

| # | 决策 | 结论 |
| --- | --- | --- |
| D1 | 单元归属 | `shell.keystone` 退场，岛并入 `shell.bar` 成为布局部件（`componentId: "island"`）；插槽 6 → 5，`island` 种类删除（唯一消费者合并后空置即熵增） |
| D2 | 命名 | keystone → **island**：IPC target、`nyxuri:keystone:*` 动作、`islandHost`、配置键、文件名全链路；Keyhole 系命名随迁审计 |
| D3 | 岛拓扑 | **inline 进 bar 窗口**，三档：小变形（胶囊↔媒体↔通知）inline；中变形（媒体展开/歌词/录音，≤~200px）走 bar 画布下探 + 输入遮罩仍 inline；大面板（dashboard/hub/tools）锚定弹窗 + 从胶囊 bounds 生长的入场动画。bangs 贴顶形态保留（bar 背景挖洞让位）；bar 悬浮/贴底/竖排时岛语义改为「从 bar 带长出」 |
| D4 | long 样式 | 换皮实机验收（B3）通过后处死；B1 起冻结（配置键不迁移、标记 deprecated、保持可用作逃生通道） |
| D5 | Fork 来源 | 即 §0 三源；数据部件（workspaces/clock/tray/media/sysmonitor/quickpanel）保留 Nyxuri niri 原生实现，只换外壳 |
| D6 | 高度与自由度 | `barThickness`/`islandThickness` 可调键（Sizes 降为默认值）；4 级密度预设 + 自定义；封闭 switch → widget 注册表 |

### 2. 目标终态

一个单元 `shell.bar`（edge 槽）：岛是布局表一等部件（默认中段、可拖拽移动），
左右清空即 center-only 纯岛形态，完整继承「只要岛不要 bar」场景；高度/密度自由
调节；加部件 = 注册表加一行；keystone 名字从全库消失（归档与 CHANGELOG 历史除外）。

### 3. 分期台账（B0–B5）

| 阶段 | 交付目标 | 状态 |
| --- | --- | --- |
| B0 | 契约定案 + 整抄基线：end4 皮肤件与 dux 机制件全量 `cp` 入 `plugins/bar/` 目标位（inert、带来源标注），裁剪清单成文；shell 运行零变化，`tests/shell/` 全绿，git 检查点可回滚 | 待开始 |
| B1 | 合并与正名（行为等价）：`plugins/keystone/` → `plugins/bar/island/`，`Keystone*` → `Island*`；manifest 合并、账本迁移（disabled keystone → `islandEnabled=false`）、配置键 `keystone*` → `island*`（long 系冻结除外）；IPC/动作/`keystoneHost`/niri-actions.json 正名；插槽 6→5（manifest.py 枚举、PluginRegistry、manifest-schema、AGENTS、architecture-matrix、popup:notification 仲裁键改绑 bar）。岛此阶段仍独立窗口居顶（过渡态）。验收：bangs 视觉逐像素等价、`off shell.bar` 连带岛消失、全库无 keystone 残留 | 待开始 |
| B2 | 拓扑手术：岛 inline 进 bar。bar 画布下探 + 输入遮罩机制；IslandSurface 宿主改写为 inline 部件，morph 引擎（弹簧/provider/形态面）原样保留；键盘焦点与预约窗路径改道；大面板整抄 `QuickSettings.qml` 范式转锚定弹窗 + 生长入场；布局表注册 island 部件。风险探针：画布下探若在 niri/Quickshell 实测有输入遮罩或层级缺陷，中变形降级为锚定弹窗，不阻塞主线。竖排 bar × 岛单独裁决（初案：竖排禁入布局表，转角部按钮 + 弹窗）。验收：作者实机验收 morph 手感等价、透明区点击穿透、多屏热插拔、锁屏不降级 | 待开始 |
| B3 | bar 换皮（end4 皮肤）：B0 基线件定向裁剪四类后上岗——cornerStyle 体系、BarGroup/Divisor/材质胶囊、屏幕圆角衔接；弹窗（托盘菜单/快捷面板）同语言重皮；竖排同步换装。验收：作者实机视觉验收、部件功能零回退、无裁切错位（红线 3）、60fps。**本阶段通过 = D4 处死闸门放行** | 待开始 |
| B4 | 高度与自由度（dux 机制）：B0 机制件上岗——厚度可调键 + 设置页滑杆；密度预设 4 级 + 自定义（含 transition() 语义：切预设不覆盖用户已自定的键）；switch → widget 注册表（含 island 条目）。验收：高度实时生效、预设切换保留自定义值、新部件零宿主改动接入有实测 | 待开始 |
| B5 | 清偿收尾：处死 long（文件/冻结键/设置段/i18n/测试全链路）；删被替代路径（旧 bar 外壳、KeystoneSurface 死窗口路径、deprecated 别名）；文档同步（architecture-matrix/plugin-model/manifest-schema/operation-map）+ CHANGELOG；消费者门禁统一清算。验收：audit-lifecycle clean、无 keystone/long 残留字符串、全量回归 + 沙箱部署 + 能耗 sanity（无多余 Timer/订阅） | 待开始 |

**停车场**（明确不承诺，触发条件到了再立项）：溢出滚动（dux OverflowLayout）、
每部件深度设置全集、岛卫星与自由悬浮模式（dux DIsland）、end4 Di* provider 扩展。

**用户侧断裂提醒**：B1 后 niri 配置中绑定 `--ipc keystone` 的快捷键需改 `island`
（实验期干净断裂，不留别名）。

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

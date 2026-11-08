# Nyxuri Shell 阶段台账（追加式归档）

> 本文件是 shell/ROADMAP.md 的明细账：2026-10-06 路线图压缩时整卷迁入，此后**只追加、不修改**。
> 每当路线图中一个阶段转为「已完成」，把该阶段的任务分解与验收记录追加到本文件末尾。
> 当前状态与活跃阶段以 [shell/ROADMAP.md](../../shell/ROADMAP.md) 为准；本页只回答「当时承诺了什么、逐项如何验收」。

---


本路线图只描述尚待执行的阶段、依赖与验收。源码和行为测试是运行事实；[Shell 开发约定](AGENTS.md)是当前设计契约；[Wiki 导航](wiki/index.md)负责指向可维护的架构、生命周期与开发资料。阶段状态仅在有可复现证据时更新，不以目录、字符串、Loader 存在或隐藏 UI 作为完成证明。

## 目标与边界

- Shell 冷启动路径小而可解释；可选功能按需加载，停用后释放实例及其 Timer、Process、请求、连接、监听和回调。
- 模块按功能域自治；UI 通过 Action Gateway 表达桌面意图，领域服务拥有对应 I/O；全局 singleton 仅用于确有跨域共享状态的能力。
- 设置 UI 的 Default、Minimal、Dashboard 均是正式可选呈现，支持热切换；它们共享设置模型、路由、搜索、动作和持久化逻辑，不复制业务。
- 清理和重构不得降低视觉品质、动效、可读性、几何精度或对齐。
- 以原版 Niri 为基础兼容目标；外部能力缺失时局部降级，不让可选依赖阻断核心 Shell。
- Wiki 只保留能指导实现、审查、验证或排障的现行契约；历史资料可归档，但不能冒充当前事实。

## 状态规则

任务状态只使用 `待开始`、`进行中`、`阻断`、`待验收`、`已完成`。合并前置、实现、行为验证和视觉验收分别记录；测试失败、环境跳过与未验证不得混为通过。每项任务明确旧实现的保留、迁移、归档或删除方式。

## 已完成阶段：原任务分解与验收记录

以下保留改写前 R1–R6 的逐项任务、前置关系和原验收描述，供追溯阶段承诺与实现来源。它们是历史交付记录，不表示本次重新运行了所有旧验收；发现现状变化时以源码、测试和对应证据为准。

### R1 状态与事实收口（P0）

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 已完成 | 统一路线图状态，删除互相矛盾的历史完成语句 | 无 | 正文只保留当前任务；历史内容进入本页简表；完成项有证据链接 |
| 已完成 | 建立当前测试与环境证据索引 | R1-01 | 每项证据包含命令、环境、日期、结果和跳过/阻断原因 |

### R2 启动闭包与可选模块（P0/P1）

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 已完成 | 盘点 `AppShell.qml` 真实消费者，区分核心、按需和封存宿主 | R1 | 冷启动不实例化非核心后台；LauncherHost 按需装配；DesktopCardHost/RegionSelector/DisplayOverlays/Sidebars 按需挂载；ShellStartupService 阶段观测全链路（INIT, FIRST_FRAME, READY, IPC_READY） |
| 已完成 | 拆分高成本宿主与可选 native 插件（按作者指令彻底移除 Cava、地图、歌词、窗口预览） | R2-01 | 彻底物理移除 Cava、地图、歌词、窗口预览 native 插件、fallback 及 UI；相关消费者（AudioSpectrum, WindowPreviewService, WeatherMapBridge）转化为零开销安全桩，QML 零相关导入 |
| 已完成 | 建立启动取消、崩溃、SIGTERM 和正常退出验收 | R2-01 | wait_shell_ready 进程崩溃即刻失败，SIGTERM 2.5s 优雅停止，热切换崩溃自动安全回滚至 Noctalia |

### R3 品牌、路径与构建边界（P1）

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 已完成 | 决定 `Clavis` 标识、旧路径、旧变量、IPC 和 QML module 的兼容期限 | R1 | 公开接口与运行时收敛为 nyxuri，Paths.qml 默认 ~/.config/nyxuri；薄兼容层 nyxuri_paths.py / nyxuri-paths.sh 承接旧变量；作者拍板 CPP 内部暂不动并直接对接 R4-C 去 C++ 化 |
| 已完成 | 收敛 CMake、安装目录、脚本、fallback、日志和翻译命名 | R3-01 | 彻底物理删除 2.6 万行臃肿 XML (.ts) 翻译文件；全面切换为纯净 TOML 字典 (zh_CN.toml, en_US.toml) 并通过 compile_i18n.py 驱动 Qt 运行时构建；Paths.qml 与构建树一致解析 |
| 已完成 | 确定生成文件、qsb、vendor、fixture 和构建缓存的版本控制策略 | R1 | qsb 二进制保留免工具链离线运行；SearchCatalog.js 脚本生成并入库由单测契约约束；vendor/kdl 严格忽略并清理 __pycache__；fixtures 仅留存于测试树 |

### R4 架构、生命周期与结构收敛（P1/P2）

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 已完成 | 建立文件级 owner、允许 import、输入/输出和副作用矩阵 | R2 | 编制 [架构边界矩阵](wiki/architecture-matrix.md)，明确四层分工、所有者与 import 白名单；升级 audit-lifecycle.py 增加 ARCH001 静态边界检查与 shared/ 零副作用约束 |
| 已完成 | 修正跨域 singleton、backend 归属和 shared 越界 | R4-01 | 剥离 Launcher 冗余导入；Dashboard 跨域导入收敛于白名单；SplitMenuButton 移入 shared/controls 消除 SystemCards 越界；NotificationContent 提升至 notifications 域并消除 Keystone 重复副本；shared 层经契约断言绝对纯净 |
| 已完成 | 把生命周期静态审计与行为证据分开 | R4-01 | lifecycle-inventory.json 升级为 schema v2，明确分离 static_inventory（0 违规）与 runtime_evidence；tests/test_shell.py 固化全量分层契约测试 |

### R4-C 结构收敛与全面去 C++（P0/P1）

参考实现：`shell/references/iNiR`。重点参考其按功能域组织模块、将长期系统能力集中到少量服务、按需装配低频服务的方式；Niri 相关服务可参考
`shell/references/iNiR/services/NiriService.qml`，但不复制代码、命名或未经验证的依赖。

目标不是按目录名机械删改，而是让每个文件都有清楚归属，每项能力只有一个实现和一个状态源。`shared/`、`bin/`、`packaging/`
#### 架构与美学审计基准（灵魂拷问：这是最简洁优雅的状态了吗？）

在 R4-C 初期整理后，以艺术品和极致秩序感标准排查，源码仍存六重严重破坏几何精度的熵增与杂质：

1. **`app/services/` 依旧臃肿（48 个文件）与局部状态外溢**：
   - 壁纸域碎片（`WallpaperService`, `WallpaperSceneService`, `WallpaperPaletteSession`, `AwwwWallpaperService` 4 个文件）散落在全局；
   - 桌面卡片拖拽与展示（`DesktopPresentationService`, `SystemCardDragSession`, `SystemCardDragState.js`）等领域私有状态外溢到 app；
   - 侧边栏抽屉番茄钟（`TimerService`, `InfoDrawerState`）私有状态未归域。
2. **死功能空壳与僵尸目录残留（做减法未彻底）**：
   - Keystone 歌词整套目录（`modules/keystone/lyrics/` 5 个文件）全库零消费，纯死代码；
   - Dock 假预览（`modules/dock/preview/DockCaptureImage.qml` 8 行空白 Item）；
   - 已放弃的 Cava（`AudioSpectrum.qml`）与窗口预览（`WindowPreviewService.qml`）伪单例空桩依然在多处被调用；
   - `cava-colors.ini` 模板残留。
3. **服务命名三权割据与同名污染**：
   - 裸名词混乱：`Volume.qml`（Pipewire 复杂音频）、`Brightness.qml`（背光控制）、`Time.qml`（系统时钟）；
   - **同名污染**：`modules/bar/quicksettings/Brightness.qml`（UI 按钮）与全局服务 `Brightness.qml` 同名冲突；
   - 伪插件名不副实：`WeatherPlugin.qml` 既非原生插件亦非扩展，实为 QML 单例服务；
   - Manager 与 Service 混用：`NotificationManager`、`MediaManager` 破坏一致性。
4. **JS 工具脚本孤例怪胎与开发脚本风格混杂**：
   - 全库 40 个 JS 文件中 39 个遵循 `PascalCase.js`，唯独孤立一个 `calendar_layout.js`（而 QML 导入却写 `as CalendarLayout`）；
   - `scripts/` 目录下短横线（`audit-lifecycle.py`）与下划线（`compile_i18n.py`, `lock_snapshot.sh`）五五开混杂；双语脚本如 `clavis_paths.py` 与 `clavis-paths.sh` 连分隔符都对不齐。
5. **功能域重名与嵌套冗余（Stuttering）**：
   - `modules/quicksettings/`（弹窗）与 `modules/sidebars/quicksettings/`（侧边栏）同名混淆；
   - `modules/sidebars/quicksettings/QuickSettingsSidebar.qml` 产生语义三重叠床架屋。
6. **`shell/bin/` 目录形式大于实质（单文件孤岛）**：
   - `bin/` 目录下仅有唯一的 `nyxuri-shell` 脚本，与 `scripts/` 功能割裂，作者已拍板直接砍掉 `bin/`，将 `nyxuri-shell` 提升至 `shell/` 根目录。

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 已完成 | 建立全树结构清单和迁移映射 | R4 | 完成全树 631 文件全量盘点并输出 [结构清单与迁移映射](wiki/tree-inventory.md)；标定 616 保留、12 移动、2 删除、1 合并；每项记录 owner、consumers、I/O 与副作用；tests/test_shell.py 契约全绿 |
| 已完成 | 按功能域重组运行代码 | R4-C-01 | 12 项专属服务（FileSearchService、SpotlightSearchService、SpotlightToolService、AudioRecordingService、RecordingService、MediaPalette、TrayService、QuickToggleConfig、NetworkInterfaceHistoryService、TodoService、AutostartService、DisplayConfigService）成功迁回所属功能域；物理删除 ToolsBackend.qml 与 settings/SplitMenuButton.qml 冗余代理；清理 settings/backend 与 native/tools 空目录；静态审计 0 违规，tests/test_shell.py 与全量单测全绿 |
| 已完成 | 统一全库命名法典与清理死代码假桩 | R4-C-02 | 确立全库艺术级命名法典（QML 类型/单例统一 PascalCase `*Service.qml`/`*Config.qml`，JS 工具统一 PascalCase.js 镜像别名，CLI 脚本统一 kebab-case，目录统一全小写）；物理删除 Keystone 歌词僵尸代码（5 文件）、Dock 假预览空壳（DockCaptureImage.qml）与废弃 Cava 模板（cava-colors.ini）；拔除 AudioSpectrum 与 WindowPreviewService 空桩并解除调用点假绑定；消除 Brightness 与 Bar 按钮同名冲突及 WeatherPlugin 伪命名；暂不动 native C++；单测与生命周期审计全绿 |
| 已完成 | 收敛 `app/` 全局边界 | R4-C-02a | 彻底解决 app/services 局部状态外溢；壁纸域（WallpaperService、WallpaperSceneService、WallpaperPaletteSession、AwwwWallpaperService 4 文件）归入 modules/wallpaper；桌面卡片拖拽与展示（DesktopPresentationService、SystemCardDragSession、SystemCardDragState.js 3 文件）归入 modules/desktopcards；侧边栏抽屉番茄钟（TimerService、InfoDrawerState 2 文件）归入 modules/sidebars/dashboard/infotools；app/ 规模严格收敛至 42 文件（app/services/ 降至 38 个纯粹全局服务）；白名单与清单闭环，单测契约全绿 |
| 已完成 | 建立 Niri 单一运行时入口 | R4-C-02 | 建立 `app/services/NiriService.qml` 成为唯一运行时 IPC 入口；统一管理 EventStream Socket、Action Socket 与 Process 异步查询；内置指数退避抖动自动重连与防陈旧 generation 校验；提供 workspacesModel/outputsModel/windowsModel 统一状态源及丰富查询/动作接口；全面移除全库所有 QML 业务模块中的 `import Clavis.Niri` 与直接 IPC 连接（11 个消费者完全安全重定向接入 NiriService）；生命周期审计与测试全绿 |
| 已完成 | 迁移纯逻辑与系统边界 | R4-C-03 | 纯计算、数据整形、路径、天气、图标和媒体辅助逻辑全部迁移至纯 QML/JS；文件、设备、亮度、网络、音频、显示和通知按真实边界归属；彻底砍掉 `bin/` 目录，将 `nyxuri-shell` 提升至 `shell/` 根目录与 `shell.qml` 并列；CLI/Niri 脚本全面接入自动自愈机制；单测与生命周期审计全绿 |
| 已完成 | 彻底解耦全部 Native 插件与统一生态体验 | R4-C-04 | 业务层除 I18nManager 双轨兼容桥外实现 0 `import Clavis.*`；7 项插件（Gamma/Runtime/Weather/Files/Media/Keyboard/DesktopCards）全面解耦为纯 QML/JS，I18n 提供纯 QML fallback 桩保证离线免编译运行；DisplayColor 深度整合 Niri `toggle-eyecare.sh` 与 `effects.kdl` 单一真值源；笔记本背光（brightnessctl 降级）与系统色彩模式（theme-sync 广播）在 Noctalia 与 Nyxuri Shell 达成 100% 体验统一；全库 517 项单测与生命周期审计全绿 |
| 已完成 | 删除 Nyxuri 自有 C++ 构建链 | R4-C-05 | 物理删除 113 项自有 C++ 源码、fallback 桩目录、native 测试与 CMake 构建系统（CMakeLists.txt）；全面清理 check.sh、lint-qml.sh、PKGBUILD.in 与 dependencies.json，构建环境免除 C++ 编译器与 CMake/CTest 依赖；I18nService 纯 QML 化且 100% 保持原有 API；单测与生命周期审计全绿 |
| 已完成 | 完成结构与行为收口 | R4-C-06 | 架构彻底收敛为 app/ -> modules/ -> shared/ 3 级纯 QML 体系；每个功能域从单一目录追踪到界面、状态与动作；Niri 确立单一运行时状态源（NiriService）；shared 层零副作用；生命周期审计 0 违规，全量契约测试与沙箱部署全绿 |

### R5 资源、文档与测试收口（P2）

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 已完成 | 盘点图标、翻译、shader、主题和第三方资源消费者 | R2/R3 | 彻底盘点全库资产并消除死资产（物理删除 SvgIcon.qml 与无消费 Font Awesome 图标）；修复 Zen 着色器断裂缺陷（预编译 zen-palette.frag.qsb，消除 qrc: 悬空路径，路径收敛为 Paths.fileUrl）；清理 zh_CN.toml 孤立歌词段落；Simple Icons 许可证自包含；Meteocons 保持构建时拉取机制；全量着色器存在性与有效性闭环 |
| 已完成 | 统一 README、wiki、注释和上游参考资料职责 | R1/R3 | 物理删除 4 篇违背物理隔离的冲突母体文档；P3 近 600KB 恢复比对档案移至 wiki/archive/ 解除认知过载；翻新 wiki/development.md 为 100% 纯 QML 调试指南；编制 wiki/references.md 固化母体 commit 15403b9 提取指令；index.md 与 llms.txt 确立 architecture-matrix 为核心真值；PKGBUILD.in 与 AwwwWallpaperService 命名空间收敛为 nyxuri |
| 已完成 | 按逻辑、运行时资源、native、图形环境和静态规则分类测试 | R4 | 建立 run-tests.py 分类测试运行器，将测试体系解耦为 [STATIC]、[LOGIC]、[RESOURCE]、[NATIVE]、[GRAPHICS] 五大独立分类；修复 Presentation 测试因 Clavis/Runtime 遗留检测导致的硬跳过阻断；集成至 check.sh；独立输出五分类成绩单，杜绝单一总数掩盖缺陷 |

### R6 能耗基线、事件循环与稳态治理（P0）

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 已完成 | 天气资产做减法：淘汰 meteocons 臃肿依赖，原生化图标映射 | R5 | 彻底移除 48.5MB (3,806 文件) 的 meteocons 外部资源包与构建依赖；MeteoIcon 切换为纯字体图标（Fonts.materialSymbolsOutlined）与 24 状态字典映射；零网络依赖、零磁盘冗余、零 Lottie/SVG 异步加载开销 |
| 已完成 | MPRIS DBus 频繁失效重连与位置轮询治理 | R5 | MediaService 建立 positionSubscribers 引用计数与按需轮询机制（仅在 Keystone 媒体前台展开且活跃播放时订阅）；移除外部伪触发 player.positionChanged()；挂接 onObjectRemovedPost 瞬时注销断开播放器，彻底消除“Remote peer disconnected”无意义会话日志风暴 |
| 已完成 | 根除 `interval: 0` 事件循环空转与高频定时器降频 | R5 | 消除全库 7 处 Timer `interval: 0` 隐式空转，统一重构为帧级安全的 `Qt.callLater` 批处理；TimerService 秒表定时器由 10ms (100Hz) 平滑降频至 50ms (20Hz)；ClockContent 时钟定时器绑定 visible 属性；静态审计新增 LIFE007 门禁，全库零违规 |
## 已确认的历史决策


以下决策已由作者确认并落实，不是待拍板事项；保留它们是为避免后续重构反复打开已关闭的问题。
- 自有 C++ 构建链已移除；运行实现收敛为 QML/JS/脚本，公开标识统一为 `nyxuri`。
- 原版参考树仅用于本地查阅，不进入运行时；上游历史材料与 Nyxuri 契约分开维护。
- Cava、地图、歌词和窗口预览不属于当前核心能力；相关死代码按已完成阶段清理。
- 资源策略区分运行时资产、生成文件、缓存和测试 fixture；qsb 保留为离线运行资产，搜索目录生成物由测试校验。
- 天气图标采用 Material Symbols；自有 Meteocons 资源与构建拉取已移除。

## 当前阶段：设置体系与架构收口

R1–R7 是已交付基线。下一步从 R8 开始；P4 及之后保留在后续阶段，不因插入新工作而丢失。

### R7 多套设置 UI 与 PR #120 前置审查（已完成）

**目标：** 将三套设置呈现收敛为同一业务系统的可切换外壳。PR #120 作为候选实现来源完成前置架构治理与审查验收。

**已完成治理与验收：**
- 完成 PR #120 全量 12 提交逐项代码审查；将 Apache-2.0 Material 3 形状引擎完整纳入并收敛为符合法典的 PascalCase.js 工具；保留 Noto Sans 默认字体并将 MiSans 作为优质 UI 回退首项。
- 歌词服务彻底领域收敛至 `shell/modules/settings/dashboard/lyrics/`，消除全局 `app/` 污染与常驻轮询后台定时器（仅在歌词面板展开且处于播放态时按需激活）；`app/` 规模严格守住 43 文件架构契约。
- `SettingsHost.qml` 实现无缝动态热切换与路由保留（Default / Minimal / Dashboard），热切换时完整卸载旧 UI 窗口及子窗口生命周期，杜绝常驻内存泄漏。
- 全量契约测试（519 测试）、五大分类测试（105 测试）、生命周期审计（550 文件 0 违规）、i18n 完整度审计（0 缺失）与沙箱隔离部署全面通过。

### R8 设置导航纯一级分类扁平化与 M3 信息架构（已完成）

**目标：** 消除 General 与 Advanced 杂项多级嵌套容器，将设置导航与页面选项彻底扁平化为纯一级分类（Flat Top-Level Categories）；保持 Nyxuri 原生纯 QML 架构与严谨规整的 Material 3（M3）设计语言（对齐规整、M3 色阶体系、容器圆角与几何精度）；Default 与 Minimal 统一外壳；保留搜索直达与历史路由别名兼容。不 1:1 复刻外部复杂控件族或移动端视觉元素，坚守低熵与秩序感。

**实施：**
- **消除嵌套容器与返回堆栈**：彻底废弃多级包裹层（`GeneralPage.qml`、`AdvancedPage.qml`）与索引跳转瓦片（`GeneralOverviewPage.qml`），消除子页面内部“返回”（Back）跳转与多级路由状态。
- **纯一级分类直达呈现**：将原有嵌套子页面（主题外观、壁纸、模糊与效果、状态栏、程序坞、显示器、Keystone、快捷键、Spotlight、网络、蓝牙与设备、自启动、默认应用、语言与区域、关于等）直接提升为左侧导航的一级直达列表，点击直接在右侧主视图渲染对应功能域页面，选项在页面内直接展开呈现。
- **坚守 M3 设计语言与几何秩序感**：
  - 严格保持 Material Design 3（M3）视觉体系：复用现有的 M3 色彩 Token（`m3colors.m3surfaceContainerLow`、`colSecondaryContainer`、`colOutlineVariant` 等）、M3 字体排版与圆角阶梯；
  - 侧边栏（`NavigationRail`）采用规范的 M3 SecondaryContainer 胶囊高亮、Filled/Outlined 图标切换与微动效；
  - 保持 Nyxuri 艺术秩序感（几何精度 + 做减法）：拒绝引入与桌面环境冲突的过度装饰（不引入 Android 式 FAB 悬浮操作按钮、复杂异形遮罩或抽屉拖拽手柄）；
  - 控件全面采用 Nyxuri 既有的 M3 纯 QML 控件（`MaterialSymbol`、`StyledSwitch`、`MaterialSlider`、`SettingsRow`、`SettingsSection` 等），不自造或搬入未经验证的平行外来组件。
- **统一外壳自适应**：Default 与 Minimal 维持单组件统一外壳呈现，通过 `isMinimal` 模式驱动窗口缩放（`styleScale`）、紧凑内边距与侧边栏精简，杜绝多套外壳维护成本。
- **深链与别名兼容闭环**：`settings-routes.json` 重构为扁平一级路由，为原 `general.*` 等旧 route ID 保留别名（`aliases`）重定向映射，保证 Spotlight / Action Gateway / CLI（`nyxuri-shell settings <route>`）直达调用无缝兼容。
- **派生重建搜索索引**：同步派生更新 `SearchCatalog.js`，通过搜索契约与漂移门禁测试。

**验收：** 侧边栏为纯一级分类列表且分类按功能域可预测；General 和 Advanced 多级容器与返回按钮彻底消除；视觉风格严谨符合 Material Design 3 规范与几何秩序感；Default 与 Minimal 为同一组件且自适应紧凑切换生效；旧 route ID 别名映射有效，Spotlight 搜索与 CLI 直达不中断；`SearchCatalog.js` 派生检查与契约测试全绿。

### R9 功能开关与真实生命周期（已完成）

**目标：** 功能开关控制实例存在，而非仅控制可见性；按用户理解的能力域设开关，不为每个视觉子组件造开关。明确 `enabled`（用户允许）、`active`（存在消费者）、`mounted`（实例已创建）严格生命周期语义。

**实施与完成：**
- **AppShell 根装配真卸载**：
  - `DisplayOverlays.qml` 包装进条件 Loader（仅在 `DisplayConfigService.identify || confirming` 时挂载）；
  - `Bar.qml` 包装进条件 Loader（`PersonalizationConfig.barEnabled` 关闭时真实卸载物理 layer-shell PanelWindow）；
  - `DockHost.qml` 包装进条件 Loader（`DockService.enabled` 停用时销毁全部 dock 窗口与监听）；
  - `NotificationPopupHost.qml` 仅在 `!PersonalizationConfig.keystoneEnabled` 时挂载 fallback 宿主。
- **Layer-shell 背景与表面零僵尸实例**：
  - `OverviewWallpaper.qml` 将 Variants model 绑定为 `PersonalizationConfig.overviewEnabled ? Quickshell.screens : []`，关闭后即刻销毁后台 Background 表面；
  - `DesktopWallpaper.qml` 将 Variants model 绑定为 `AwwwWallpaperService.quickshellContentVisible ? Quickshell.screens : []`，启用外部 awww 后端时物理销毁 Quickshell 壁纸窗口，杜绝双重渲染开销；
  - `HotCorners.qml` 严格过滤 `PersonalizationConfig.hotCornerIds`，仅针对未设为 `"disabled"` 的物理热角实例化 Overlay PanelWindow；
  - `RegionSelector.qml` 将 Variants model 绑定为 `RegionSelectionService.active ? Quickshell.screens : []`，闲置时零 Loader 与零窗口常驻。
- **领域服务与设置后台防泄漏收敛**：
  - `DockService.qml`：`rebuild()` 增加停用判定，禁用时清空数据模型并停止 `launchTimeout` 定时器；`Connections` 目标与 `root.enabled` 绑定，禁用时完全断开 Niri、ApplicationService 及 SpotlightAppUsage 信号响应；
  - `WallpaperSceneService.qml`：增加 `pruneScenes()` 动态感知屏幕插拔并销毁离线 screen 的 scene 实例；增加 `Component.onDestruction` 完整清理所有场景；
  - `DisplayConfigService.qml`：增加 `cancelPreview()` 接口；在 `Component.onDestruction` 中严谨停止 `identifyTimer` 与 `pollTimer`，终止 dangling 外部操作；
  - `AutostartService.qml`：显式跟踪动态创建的 `deleteProcess` 句柄，销毁时强制终止并析构，杜绝孤儿进程泄漏；
  - `SettingsBackend.qml`：增加 `Component.onDestruction`，销毁时调用 `cancelSearch()` 停止 `searchDeadline` 并重置搜索状态。

**验收：** 静态生命周期审计全量覆盖 549 个文件零违规（`audit-lifecycle.py --scope full --check` clean）；五大分类测试套件全部 105 用例独立通过（STATIC 20, LOGIC 48, RESOURCE 9, NATIVE 26, GRAPHICS 2）；契约断言全面覆盖 R9 挂载语义与清理守卫。

### R10 Action Gateway 与模块自治（待验收）

**目标：** 桌面意图有统一边界，功能域拥有自身状态与副作用。

**实施与完成：**
- **动作契约收口**：`ActionGateway.execute(args, owner)` 头注释固化为全库唯一结果语义——布尔返回值表示「已受理派发」，不追踪命令完成态，参数必须是纯数组、owner 非空（LIFE001/LIFE004 门禁保持）；删除零消费者的 `actionDispatched` 死信号（R11 控制面需要错误流时随真实消费者重建）；secure-power 8 秒未锁自动丢弃的取消路径保留并由契约测试覆盖。
- **AppShell 瘦身至纯装配**：壁纸目录动作分发与 `pendingCycleAction` 兜底细节迁入 `WallpaperService.runCatalogAction(method)`（纯搬运，IPC 返回码与 PENDING 语义逐条不变）；sidebar 搜索动作复用 `ActionGateway.requestSidebarToggle` 消除第三份校验拷贝；`executeSearchAction` 收敛为单行委托映射；修复 IpcHandler 区三层错位缩进。AppShell 只保留根装配、跨模块连接与公开 IPC，不承载领域业务。
- **UI 直接 I/O 归零（LIFE008 新门禁）**：`audit-lifecycle.py` 新增 LIFE008——`modules/` 视图与 `app/` 顶层文件禁止持有 `FileView`/`Process`（`*Service/*Config/*Backend/*State/*Catalog` 后缀与显式 allowlist 豁免）；Dock 预览弹层的强杀进程 `Process` 迁为 `ActionGateway.execute(["kill","-KILL",…], "dock:force-quit")`；主题页 scheme-previews `FileView` 迁入 `MatugenTemplateService`；allowlist 仅保留域自有 I/O（`lock/Lock.qml` 会话标记、`lock/PreLockCapture.qml` 抓屏、`keystone/media/MediaPalette.qml` 取色）。
- **死代码与单例减法**：物理删除零消费者失败桩 `WeatherMapBridge.qml`，audit 豁免表清空并反转既有测试断言（必须不存在）。
- **可选依赖显式降级**：新建 keystone 域 `ColorPickerService`（一次性 `probe-tool.sh` PATH 探活 → 缺失时 notify-send 明示 "hyprpicker is missing"，存在时走 Gateway 派发），消除 hyprpicker 静默失败；外部命令降级矩阵：硬依赖 `systemctl`/`niri`（目标环境必在），可选 `wl-copy`（ClipboardService/Spotlight 已有缺失提示）、`hyprpicker`（本轮补齐）、`notify-send`（缺失时通知渠道整体不可用，属环境级降级）。
- **generated 路径去 clavis 化**：`assets/matugen/config.toml`、`generate-matugen-previews.sh`、`ThemeService.colorsPath` 全部改写 `<generated>/nyxuri/`，读取侧保留旧 `clavis/` 目录一次性回退（含显式 reload，杜绝 path 重绑不加载），改名不丢已生成调色板（GRAPHICS 行为测试以旧路径 fixture 实证回退成立）。
- **双轨主题统一（T7）**：Shell 新增 `theme` IPC target（`set dark|light`/`toggle`/`status` → `ThemeService.setThemeMode` 唯一业务入口）；`nyxuri theme` CLI 传播链对齐 bash 版语义——`noctalia msg status` 探活 → Nyxuri Shell IPC → 两者皆无仅同步系统，全程捕获子进程 stderr，杜绝第三方 `error:` 裸漏，单行汇总注明传播去向（`shell: noctalia|nyxuri|none running`）；`theme.py` 补齐 Kvantum ini 切换（仅主题已安装时）与 niri glow layout 明暗 kdl 原子切换（preset active 为 glow 且字节有差异才写，reload 有 `niri` 探活守卫）；`UiPreferences` 轮询新增 `systemThemeModeObserved` 信号，`ThemeService` 闭环回写 `PersonalizationConfig.themeMode` 并重跑 matugen（同值 no-op 防回环，60s 轮询保留为兜底）。

- **切换器多实例治理（R10 现场修复）**：`shell_switcher` 修复双 Shell 并存缺陷链——`probe_running_shells()` 全量清单化双端实例（旧 probe 单返回且 nyxuri 优先，对侧残留被无视）；"already active" 早退收紧为「target 在场且对侧零实例」，残留先清场并在成功消息中列出被清对象；`stop_shell_process` 返回真实死亡状态并在 SIGKILL 后补等观察，`stop_all_shell_instances` 按类全量清扫（原 lingering 分支在 target=noctalia 时方向写反，恰是残留 noctalia 阻断后续切换的根源）；`wait_shell_ready` 的 noctalia 探针由不存在的 `noctalia msg ping`（永不通过，靠"活过 1 秒即放行"兜底假成功）换为真实存在的 `noctalia msg theme-mode-get`（returncode 0 即 IPC 应答）；回滚与 spawn 失败路径先全场清扫再复活旧 shell，保证恢复后单 Shell。行为测试：残留清理、方向修正、readiness 双分支、SIGKILL 升级链共 6 项。

**验收：** UI 不直接启动桌面命令或写配置（LIFE004 + LIFE008 双门禁，547 文件 0 违规）；动作有参数形状与失败清理契约测试（`test_r10_action_gateway_and_module_autonomy` + secure-power drop 路径断言）；可选服务缺失时模块仍装载并明示降级（ColorPickerService 探活模式）；架构 import/副作用契约通过（五分类 108 用例全绿，`test_shell.py` 45 用例全绿）；双轨主题跟随性矩阵——GTK3/4 ini、Libadwaita portal、Chromium prefer-dark、Kitty SIGUSR1+matugen 模板、Qt/Kvantum、niri glow、Shell M3 调色板、zen 着色器全部跟随且 `nyxuri theme` 三场景（noctalia 在 / 仅 nyxuri shell / 都不在）输出一致无裸 error；Noctalia 专属 wallpaper picker 不在迁移范围，双轨切换与部署链路零触碰。

### R11 Nyxuri Shell 控制面与透明度（已完成）

**目标：** 提供按需加载、用户可理解且可行动的 Shell 管理页面，不做开发者对象检查器。

**实施与完成：**
- **控制面页面（一级路由 `shell`，导航末位）**：新建 `modules/settings/ShellPage.qml`（纯视图，零 `FileView`/`Process`/`Timer`），三个搜索锚点 section（模块与依赖 / 资源采样 / 诊断与路径）。模块行直接绑定 owner 单例——启动阶段（`ShellStartupService`）、Niri 集成、Bar/Dock/Keystone/概览壁纸（复用既有 setter 的真卸载开关）、网络/蓝牙可用性、剪贴板（cliphist/wl-copy/wl-paste 逐项）、取色器（hyprpicker 探活）、系统监视器（key-cli 状态 + 重试）；每条错误带行动按钮（重连/重试/开关/提示），notify-send 按既有决策如实标注为环境级不可探测。路由与别名进入 `settings-routes.json`（`control-plane`/`diagnostics`），Dashboard 风格补 `"shell": "settings"` 别名防路由落空，`SearchCatalog.js` 派生再生成。
- **采样引擎（`ShellControlService.qml`，settings 域唯一 I/O 归属）**：采样对象为 Shell 自身进程——`Timer(5s 固定低频)` + 两个服务自有 `FileView` 重读 `/proc/self/status`（VmRSS）与 `/proc/self/stat`（CPU jiffies），不派生子进程、不依赖 `QML_XHR_ALLOW_FILE_READ` 环境变量（QML 默认禁止本地文件 XHR，采样不得依赖启动方式）。双重门控 `samplingActive = pageMounted && UiPreferences.controlPlaneResourceSampling`：开关默认 **false** 并持久化（`UiPreferences.controlPlaneResourceSampling` 四处对称：属性/setter/save/load）；门开立即首采、第二次采样起给 CPU% 基线差值；门关停 Timer、清全部数值，迟到的 /proc 回调在写状态前复查门控，无法复活已清数字。纯解析数学在 `ShellSamplerMath.js`（`.pragma library`，无 Qt 无 I/O）。
- **诊断脱敏与导出**：`ShellDiagnostics.js` 纯函数按 **allowlist** 构造负载（schema 键固定：shell/compositor/modules/dependencies/errors/sampling/paths），每个字符串经 `maskHome`（`$HOME`→`~` + 残余 `/home/<user>` 正则兜底）、空白折叠、512 字符截断；零环境变量、零配置内容。导出经 `mkdir -p`（argv 数组）+ `FileView` 原子写 `cacheHome/diagnostics/nyxuri-shell-<时间戳>.json`，失败路径分「目录创建失败」与「写入失败」双提示。IPC `shell diagnostics()` 一行薄委托返回同一脱敏 JSON（`nyxuri-shell ipc call shell diagnostics` 即可无 UI 抓诊断）。
- **NiriService 公开化**：补 `readonly property bool reconnecting` 与幂等 `reconnect()`（重置退避、按需重连，健康时 no-op），控制面展示「正在重新连接」并提供重连按钮。
- **i18n 与既有债务**：zh_CN.toml 补 34 键（本阶段 24 键 + 修复 HEAD 上已存在的 10 个先存缺失——ColorPickerService 2 键、Dashboard 卡片 8 键，`audit-i18n` 在本轮之前即为 exit 1），并为 Niri 语境的 `Disconnected` 增加 `[ShellPage]` 上下文覆盖（全局键是「网络未连接」网络语义）；`audit-i18n: clean`。

**验收：** `tests/test_shell.py` 53 用例全绿（新增 `test_r11_shell_control_plane_and_transparency` 静态契约：路由注册、页面零 I/O、双门控表达式、UiPreferences 默认 false 四处对称、IPC 薄委托、JS 纯净与掩码规则、搜索目录含 3 个 section）；五分类 111 用例（STATIC 24, LOGIC 48, RESOURCE 9, NATIVE 26, GRAPHICS 4）——GRAPHICS 新增 2 项真实行为测试：`test_r11_sampling_gate_lifecycle`（headless Weston 真实 QML：挂载未开关键是零采样 → 开关后 RSS>0 且第二次采样 CPU%>0 → 卸载即停且数值全清 → 关开关保持空闲）与 `test_r11_diagnostics_sanitized_and_exported`（毒化负载断言 `/home/nyxuser` 不泄漏、控制符折叠、512 截断、路径变 `~`；端到端负载 schema 键恰等于 allowlist 且无 `$HOME`/`NIRI_SOCKET`；导出文件真实落盘并复验脱敏）；生命周期审计 552 文件 0 违规，inventory 再生成（236 项）；搜索目录契约（16 个一级 id）通过。页面关闭零监控开销与状态-生命周期吻合由 Loader 卸载语义 + 门控行为测试共同背书；视觉与交互冒烟（M3 对齐、几何精度）已经作者实机确认，随本段落定标记「已完成」。

### R12 全局文档架构重塑与单一真值体系

**目标：** 终结文档熵增，重塑覆盖项目全局（根目录契约、`llms-wiki/`、`shell/wiki/`、路线图及各域指南）的文档架构。建立优雅、精简、具备自愈与可检验能力的单一真值体系，消除冗余、陈旧与多重权威冲突，为后续 Agent 协作留出清晰边界与高度发挥空间。

**核心哲学与自治空间（秩序感与充分发挥）：**
- **真值拓扑分层 (Tiers of Truth)**：
  - **L0 运行与测试事实**：源码、模板与自动化契约测试；
  - **L1 架构契约与行动路由**：`AGENTS.md` 与 `llms-wiki/`，作为 Agent 和开发者的最高意图准则，直达改动范围，拒绝全库盲目遍历；
  - **L2 领域演进与路线图**：项目全局及各模块 `ROADMAP.md`，记录阶段事实、前置依赖与验收证据，只保留未完成任务与已确认交付，淘汰悬空承诺；
  - **L3 历史档案与外部参考**：上游母体、比对记录、历史审计结论严格隔离归档，绝不允许冒充当前事实。
- **Agent 自治与演化空间**：
  - **全权重组与演进**：Agent 拥有对项目全局文档体系充分的自由裁量权与设计空间。可以爱怎么搞就怎么搞——自由决策全局文档拓扑整合、跨域 Wiki 与路线图的重构、拆分、提炼或深度归档；
  - **结构重组与做减法**：支持统一全局文档标准，消除各自为政的死角；将过往沉重脆弱的手工统计（如全树盘点、清单枚举）转为轻量、可自动派生或单测断言的活契约（Living Contracts）；
  - **克制精炼的文风标准**：坚守几何精度与去 AI 味的表达艺术，用最少最凝练的文字直击本质，给未来维护者留下经得起反复审视的高品质秩序感。

**实施要点：**
- **全局真值对齐与去歧义**：排查并消灭全库所有多头权威；使各级 `README`、`ROADMAP`、`wiki/`、`llms-wiki/` 形成单向闭环的引用拓扑，严禁同一事实在两处独立维护且口径漂移。
- **Wiki 与演进文档脱虚向实**：重整 `shell/wiki/` 与全局知识库，历史审计结论移入归档或删除；将 R7–R11 的真实工程交付与生命周期事实同步闭环至对应架构文档中。
- **轻量化自愈与校验探索**：鼓励 Agent 按需探索或集成轻量级校验（如相对链接有效性、术语一致性、契约一致性测试），让文档演进与 CI/单测同频。

**验收标准：**
- 全库文档拓扑规整，任何架构事实与设计决策均有且仅有唯一真值源；
- 内部链接与引用 100% 有效，无悬空断链与虚假现状描述；
- 现行文档中的每一处契约与参数皆能与代码、测试或真实决策相互印证；
- 自动化单测与静态语法验证保持全绿通过。

## 后续阶段

### P4：壁纸、调色与模板兼容

**前置：** R7–R12 完成；壁纸、主题与调色状态源及领域归属明确；生命周期已验证。

- 核对 Noctalia 模板、变量、过滤器和 `palette.toml` 字段，不自行发明兼容语法。
- 复用已验证的壁纸、M3 调色与模板算法；以源码证据决定 native/外部工具的必要性和失败降级。
- GTK、Fcitx、Kitty、Starship 与用户模板无需重写；用户覆盖不会被覆盖；写入失败可回滚且不破坏当前主题/壁纸状态。

### P5：完整宿主、部署与双轨生态

**前置：** P4 完成，六动作及核心 Shell 行为已验收。

- 验收 launcher、session、settings、clipboard、lock、wallpaper-random 六动作及兼容入口。
- 按原子复制、Dunder、manifest、快照、回滚和卸载契约接入可选部署流程。
- Noctalia 模式与自研模式按需运行；切换失败不损失配置、不留下受管残留。

### P6：整体验收与未来移植

**前置：** P5 完成。

- 固定机器、版本、分辨率、缩放和字体，记录冷/暖启动及稳态资源基线。
- 验收核心离线、缺插件/设备、锁屏、会话结束、SIGTERM、目标崩溃和失败恢复。
- 完成视觉、行为、资源和文档证据后，才接纳封存功能或多合成器移植。

## P4 实施记录（追加式，2026-10-06）

**状态：实现完成、契约测试全绿；行为与视觉验收待作者实机确认（待验收）。**

### M0 前置 spike（已完成）

- matugen 4.2.0 实测：`--json hex` 一次输出全 mode，`.colors` 与退役的内部 Tera
  模板 50 键同构（含 `source_color`）；`--source-color-index` 可用 → 采用
  「纯取色 + 脚本组装」方案，Tera 渲染路径全量退役。
- Noctalia 5.2.1 `noctalia theme <img> --scheme X --both -o` 离线可用，作为黄金参照；
  golden fixtures（确定性 ffmpeg 图像 + 参照输出）入库
  `shell/tests/fixtures/theme/`（再生命令见其 README）。
- matugen↔Noctalia scheme 映射：m3-tonal-spot/fruit-salad/rainbow/monochrome ↔
  scheme-* 全等；`m3-content ↔ scheme-content` 含已知 3 键分歧（见 M5）；
  vibrant/faithful/soft/muted/dysfunctional 为 Noctalia 自有算法，无对等。

### M1 契约层（已完成）

- `generate-matugen-colors.sh` 重写：单次 matugen 提取 → 双写
  `colors.json`（50 键热载契约不变）与 `palette-modes.json`（dark+light+source_color）；
  `--generated-home` 改为显式必传（ThemeService 传 `Paths.generatedHome`），
  消除旧 placeholder 依赖。`generate-matugen-previews.sh` 同步改 `--json`。
- 16 角色 palette JSON（Noctalia 自定义色板 schema，dark/light + terminal 段）
  由 `shared/utils/ThemePalette.js` 单点派生，TemplateService 原子写入
  `~/.config/noctalia/palettes/nyxuri.json`（受管生成物，用户自建色板不触碰）。

### M2 引擎收口（已完成）

- matugen 注册表资产（`assets/matugen/`）删除；新内置注册表
  `assets/templates/config.toml`（kitty/btop/starship vendor 自 Noctalia 5.2.1 MIT
  并品牌化为 nyxuri；gtk3/gtk4/niri_glow/palette_toml 指向共享池
  `~/.config/noctalia/templates/`——P4 不迁移池位置，留 P5 随部署接入处理）。
- yazi 模板全链删除；cava 设置项死条目一并清除。
- doctor 新增 `_check_matugen`：缺失报 WARN + 内置回退色说明，不阻断。
- kitty 落地机制改为 Noctalia 式 include 行管理（`themes/nyxuri.conf`），
  弃 `current-theme.conf` 整文件覆盖；starship apply 双向剥离 nyxuri/noctalia
  托管块，保证双 Shell 交替写时文件不积累第二块。

### M3 渲染层（已完成）

- `shared/utils/ThemeColor.js`：material-color-utilities 0.3.0（Apache-2.0）
  整合 vendor，往返精确；`ThemePalette.js`（terminal 22 token + 16 角色派生）、
  `TemplateExpr.js`（表达式子集渲染，块/过滤器/`palettes.*` 显式拒绝）。
- `MatugenTemplateService` 更名 `TemplateService`：注册表管理 + palette-modes
  热载 + 镜像写入 + 串行渲染队列（读→渲→原子写→hook，参数数组 +
  `TEMPLATE_DIR` 环境注入，失败按模板登记不阻塞队列）。
- terminal 派生规则（逆向并 golden 验证）：黑=`surface_variant`、红=`error`、
  绿=`primary`、黄=`secondary`、蓝=`tertiary`、magenta=`surface_tint`、
  cyan=`secondary_fixed_dim`、白=`on_surface`、bright 黑=`outline`；
  light 模式 magenta/cyan = dark 值在 tone 48.4 的 HCT 变体（参照引擎求解器
  微差，契约容差 ΔE00 ≤ 1.5，实测最差 1.44）。

### M4 深浅单一写手（已完成）

- 删除 `set-system-color-scheme.sh` 与 `configs/noctalia/theme-sync.sh`
  （manifest chmod、doctor 脚本清单、部署注释同步）；`configs/noctalia/README.md`
  现行事实节改写、历史 Problem Log 加注。
- `UiPreferences.writeSystemColorScheme` 改为代调 `nyxuri theme <mode>`
  （binHome 探测，缺失 → 内部照切 + i18n 明示）；观察回路保持只读。
- `ThemeService.setThemeMode` 加同值短路：CLI 经 IPC 回写时无回环。

### M5 色差实测（已完成，矩阵钉值）

- 分歧矩阵（solid fixture，matugen vs Noctalia golden）：dark tonal-spot 全等；
  light tonal-spot 与双 mode content 在 `on_{primary,secondary,tertiary,error}_container`
  分歧（Noctalia 将 container 前景色重锚定至 tone≈30，ΔE00 ≈ 10，可见）。
- 钉在 `tests/test_shell.py::TestP4ThemeEngineContract.test_extraction_diff_matrix`；
  对齐路径为镜像色板 + `noctalia msg color-scheme-set custom nyxuri`（文档化，
  未自动接线——是否长期切换 Noctalia 至 custom 属策略决策，留验收时拍板）。

### M6 验证（契约层全绿；行为证据待实机）

- 契约测试：`TestP4ThemeEngineContract`（qmltestrunner golden master 6 项 +
  MD3 向量 + 分歧矩阵）；`shell/tests/test_matugen_registry.sh` 重写为
  --json 管线行为测试（真实 matugen，缺依赖 exit 77）；宿主 550 测试全绿；
  `check.sh`（shellcheck/qml-lint/qml-format/lifecycle-audit）与分类测试
  111 项全绿。
- 行为证据（待实机）：壁纸切换→色板再生+模板渲染+镜像更新；深浅切换→CLI
  代调链路（GTK/Kvantum/kitty/glow 跟随）；kitty include、btop 信号、starship
  托管块；用户模板注册渲染与失败呈现。

### P4 遗留与边界

- 双 Shell 输出仲裁（ kitty 双 include、gtk.css 交替写）按「谁 active 谁写」
  运行；切换残留清理归 P5 部署域。
- 共享池位置迁移（`configs/theme/templates/` 中立化）需部署引擎配合，P5 处理。
- 后置收口（不阻断 P5）：MCU 全量 vendor 替换取色位、matugen 资产与命名清算。

## 已交付基线

以下只标记路线图改写前的历史基线，不替代后续行为验收：

| 阶段 | 历史交付 | 说明 |
| --- | --- | --- |
| R1–R3 | 状态/证据收口、启动闭包、品牌路径与构建边界 | 当前仍受新阶段回归门禁约束 |
| R4-C | 纯 QML 结构、Niri 单一状态入口、移除自有 C++ 构建链 | 结构变化不代表所有运行时生命周期已动态验证 |
| R5 | 资源清理、开发文档和分类测试 | 后续 Wiki 重置须保留仍有效的测试契约 |
| R6 | 天气资源精简、MPRIS 订阅轮询、定时器稳态治理 | 新增常驻行为仍需单独审计 |
| P3 | 功能恢复及结构整理历史 | 明细仅作归档追溯，不作为当前完成证据 |

## 当前门禁

- 不合并 PR #120，直至 R7 审查、修正与验收完成；其目标是接纳多 UI 能力，不是照单全收实现细节。
- 任何新依赖、直接副作用、跨域 singleton、常驻资源或未解释的视觉回退都需有明确 owner、理由和验证。
- 每个保留文件必须有真实消费者；每个设置项和动作必须有唯一业务 owner。
- Niri 运行态只允许单一服务状态源；模块不得复制窗口、工作区或输出状态。
- 新抽象必须减少重复、状态或生命周期复杂度；仅转发的文件不得作为结构性成果保留。
- 每阶段完成前源码、测试、资源、部署和文档状态相互一致；测试跳过与环境阻断单独报告。

## KM4 实施记录（追加式，2026-10-17）

**状态：M1–M6 实现完成、全量契约测试绿；行为、视觉与六动作实机验收待作者确认。**
阶段台账在根 ROADMAP；本节按台账约定留可复现证据。

### M1 引擎侧（已完成，此前提交 afc781b）

- registry 命名空间根（`units/` → 裸 ID，`shell/units/` → `shell.` 前缀）；12 个
  Shell 单元 `runtime = true` 蓝图；`unit-changed` 事件端口 + `desktop/bridge.py`
  投递（`qs ipc call unit reload`，无订阅者 no-op）；契约同步 unit-model §6 /
  manifest-schema。

### M2 微内核宿主（已完成）

- `app/services/StateProjection.qml`：FileView 只读挂 `Paths.stateHome/state.json`
  （与 ledger 同一文件）；`isEnabled()` 无记录 = 默认启用；账本解析失败 = `degraded`
  全启用降级；`watchChanges: false`——重投影只发生在启动与 `unit` IPC 事件。
- `app/UnitCatalog.qml`：12 单元 × 六插槽目录（id/label/slot/source），堆叠序保持
  旧 AppShell 声明序；`app/SlotHost.qml`：`Repeater + Loader` 目录驱动装配，
  `active = slotActive(unit)`。
- `AppShell.qml` 377 → 238 行：零按名实例化；宿主保留通用 IPC
  （unit/shell/theme/shortcut-map/wallpaper——wallpaper 是能力面，视觉单元 off
  不影响 set/random 语义）+ 宿主级意图源（HotCorners）+ lock 冻结 Binding +
  IdleService 降级接线。搜索目录执行器留在宿主（模块能力桥接），网关自有意图
  归 `ActionGateway.executeIntent()`（unit-model §6 命名兑现）。
- 单元自有 IPC 迁入单元根：lock→`Lock.qml`、power-menu→`SessionHost.qml`、
  spotlight→`LauncherHost.qml`、control-center+settings→`SettingsHost.qml`
  （keystone 原已自有）。宿主引用倒置：Lock/SettingsHost/Keystone/Sidebars
  自注册 ActionGateway（onCompleted 注册 / onDestruction 注销），
  `lockEngaged` 成网关只读安全事实。
- 槽仲裁（宿主唯一冲突裁决点）：lock 持有期禁卸载（`off` 延迟至解锁）；
  keystone 在场独占 `popup:notification` 槽（拆掉 `!keystoneEnabled` 私有互斥）。
- 降级：`shell.lock` off → idle 锁请求报真实失败（横幅可见）；无锁挂起直接执行
  （不再 park 等 `secured()` 8 秒超时）；`shell.wallpaper` off → 合成器背景透出。
- `DesktopCardHost` 原宿主侧数据门（desktopCardIds）移入单元（`model: []` 门），
  槽装载保持纯存在性。

### M3 单一开关真相（已完成）

- `app/services/UnitControlService.qml`：Process 参数数组派发
  `nyxuri on/off shell.<domain>`（binHome 探测、15s 有界 watchdog、失败显横幅）；
  lock 持有期 `canToggle` 拒绝。UI 零乐观翻转。
- `ShellPage` 模块区改 12 单元全景开关（Repeater over UnitCatalog）+ 应用中/失败/
  账本降级横幅；`SettingsControlCatalog` keystone/bar/dock 开关改走 UnitControl；
  子页（GeneralBarPage/KeystonePage/DockPage）私有开关移除（单一投影面）。
- 私有开关状态干净断裂退役（拍板：不迁移旧值）：PersonalizationConfig 删
  `barEnabled`/`keystoneEnabled`（属性/toJson/loadFromObject），残留旧键由既有的
  repair-on-load 重写自然清除；DockModel/DockService 删 `enabled` 选项，
  `DockService.enabled` 变账本投影读（后台订阅随之精确 gate）。
- 死刑清单登记 + 执法（unit-model §7）：Shell 私有开关字段、AppShell 硬编码组件
  与宿主代管单元 IPC、noctalia 命名空间共享池。

### M4 闭包与证据（静态/契约层完成）

- `shell/tests/test_unit_catalog.py`（+11 契约）：目录↔目录（ids ≡ `shell/units/`）、
  label↔manifest、插槽六分类、source 存在性、宿主闭包（AppShell 零单元组件、
  SlotHost 唯一装配点、lock 安全规则原文）、事件回路（bridge 原文 ↔ `target: "unit"`
  ↔ StateProjection 只读）、开关动词回路（UnitControl 无 state.json 写入）。
- 旧架构契约测试重写为 KM4 语义：`test_r2_startup_closure_and_lazy_hosts`（槽驱动
  闭包）、`test_r9_feature_toggles`（存在性 = 投影）、`test_r10_action_gateway`
  （executeIntent + 单元自有 IPC）、`test_p3_notification_fallback`（槽仲裁）、
  `test_p3_settings_wiring`（自注册）、`test_unit_model.test_shell_coordination`
  （§6 三条 + 迁移断言）。
- `run-tests.py` 陈旧 import 修复（`tests.test_shell` → `tests.shell.test_shell`，
  KM3.5 测试镜像树遗留——分类套件此前在 main 上整体不可运行）。
- 宿主 118 分类测试 + 引擎 966 测试 + check.sh（qml-lint advisory 与存量同类）
  + i18n audit 全绿。

### M5 P5 平移项（已完成）

- 共享池中立化：`units/noctalia/templates/`（5 文件）→ 新 `units/theme/` 单元
  （`target = "~/.config/nyxuri/templates"` + `merge = true` 共享生活区：用户已改
  模板永不覆盖，off 只撤蓝图具名文件）；`noctalia-config.toml` 5 处 input_path 与
  shell `assets/templates/config.toml` 4 处 input_path 同源改指新池；部署流程
  （install/update/test）自动 `on theme`（`deploy.enable_theme_unit`，镜像
  wallpapers 模式）；蓝图 12 → 13 目录。
- 双 Shell 输出仲裁：kitty include 去重 + noctalia BEGIN_KITTY_THEME 块剥离既有
  （`kitty-apply.sh`）；gtk.css/niri colors 同池同输出，切换后活动 Shell 启动即
  全量重渲（ThemeService.reloadColors 启动路径），无跨 Shell 受管残留。
- 顺带清算（shell/KNOWN-ISSUES）：quickshell 入根 `catalog.toml`（deps 菜单 +
  gen-deps optdepends 同源）；修复 KM3.5 搬家遗留的 PKGBUILD 生成标记 stale
  （`nyxuri/packaging/` → `packaging/`）导致 `gen-deps --update` 静默 no-op 的
  预存 bug；`nyxuri-shell` 卸载残留复核——清理代码已在，沙箱实证
  `uninstall --all` 双软链清零，条目过时勾销。TUI 缺口按拍板保留不动。

### M6 契约与文档（已完成）

- unit-model §6 兑现自身承诺：插槽分类学迁 `shell/AGENTS.md`（微内核宿主/六插槽/
  数据驱动装载/单一开关真相/单元自有 IPC/降级语义），§6 只留内核三条 + 内核侧
  承载；§7 死刑清单补 KM4 执法三行。
- overview.md 蓝图数、architecture-matrix 池路径、units/noctalia README、
  install.sh 蓝图卫 Statement、两级 ROADMAP 同步。
- 已知边界（如实）：mango.conf 模板仅 noctalia 侧注册渲染，nyxuri TemplateService
  未加 mango 条目——双合成器过渡形态既有债务（delayed-decisions 在册），不随
  池迁移扩大战场。

### 运行时调试记录（2026-10-17，实机首切失败定位）

首次实机 `nyxuri shell switch` 探针超时回滚。离屏（offscreen）实跑替代 qmllint
（其对 Quickshell 合成 qmldir 全盲，322 条 advisory 淹没了真错）逐层定位；随后
接入 LogService（会话日志环 + `qs ipc call shell log` + 设置页会话日志节 +
state/logs/shell.log）后，日志点失踪暴露出第三个根因（缓存陈旧化）。共四个
独立缺陷、全部已修并有干净启动与全链路证据：

1. **qs-import 装载缺陷**：Loader 装载的组件首次解析 qs.* import 图不可靠，
   败者不确定地报「module not installed / X is not a type」整单元暴毙（与
   磁盘缓存无关，复现稳定）。修复：SlotHost 静态预热 import 12 个单元模块
   ——只注册不实例化，零实例化契约不变。
2. **QML 磁盘缓存陈旧化**：quickshell qmlcache 在源码改动后仍供应旧编译
   产物——新旧代码混跑（「改了没生效」的另一半真相；曾使诊断日志点整体
   失踪）。修复：nyxuri-shell wrapper 每次启动清空 qmlcache。实测注意：
   `QML_DISABLE_DISK_CACHE=1` 不可替代——无缓存写入时每次 Loader 装载都会
   重新触发缺陷 1（冷编译 + 缓存写入的组合反而干净）。
3. **IpcHandler 模块归属**：0.3.2 的 IpcHandler 挂在 Quickshell.Io；三个新增
   handler 的单元根（Session/Settings/Launcher）缺 `import Quickshell.Io`，
   目标静默消失（mod+i 无响应的直接原因）。已补。
4. **DockModel decodeConfig 严格校验回归**：退役 `enabled` key 导致现存
   dock.json 全员被拒读（「无法读取 Dock 设置」横幅）。修复：退役/未知
   key 丢弃而非拒读，损坏值维持原拒绝语义。

修复后同机实测：零类型错误、READY→IPC_READY 46ms；IPC 面全通——`unit reload`
回 OK、`control-center toggle` OPENING/CLOSING、`spotlight toggle` OPENING、
`shell isReady` true；`nyxuri on/off shell.bar` 经 bridge 端到端驱动运行中实例
无错误。两项约束已登记 shell/AGENTS.md（quickshell 升级后重估）。

### 待实机验收清单（作者签字项）

1. 冷启动闭包：`off` 若干单元后启动 quickshell，未启用域零窗口/零后台；
2. 开关回路：Shell 设置页翻转 12 单元开关 ↔ `state.json` 落账 ↔ 界面投影
   （含失败横幅、lock 持有期禁关）；
3. lock 安全：锁屏中 `off shell.lock` 被拒、`unit reload` 不撕锁、解锁后摘除；
4. 六动作：`nyxuri-shell --action launcher|session|settings|clipboard|lock|wallpaper-random`
   全通过，对应单元 off 时得到真实失败而非假成功；
5. 池迁移：实机 `nyxuri on theme` 后 `~/.config/nyxuri/templates/` 五文件落位，
   双 Shell 主题渲染正常，旧 `~/.config/noctalia/templates/` 随 noctalia 重部署
   自然消失；
6. Noctalia + Wallpaper Picker 双轨互不干扰、各自纯白（P5 平移验收项）。

## T3 实施记录（追加式，2026-10-24）

### M0 配置轴 3 ➔ 2 收敛与路由元数据（已完成）

**实现**：
- `PersonalizationConfig.settingsPanelStyles` 收敛为 `default` + `dashboard` 两值；
  历史配置中的 `"minimal"` 经既有 `normalizedOption(..., "default")` 在 load 与
  setValue 两条通路上自动折叠为 `default`，无特判分支，不主动写回文件。
- 消费面收缩：`ControlCenterWindow` 剥离 `isMinimal`/`styleScale` 及 7 处三元
  分支（尺寸全落 default 档）；`SettingsPanelStyleCard` 删硬编码 minimal 选项；
  `DashboardStyleCard` 删 `decoration.minimal`；`DashboardSettingsCatalog` 关键词
  去 minimal；`zh_CN.toml` 清 3 个死键（Minimal / Compact rail / Compact overlay）。
- 路由元数据：`settings-routes.json` 全部 20 条路由补顶层 `description`（英文
  源串，M2 NavPane 双行导航副标消费；数据随 catalog 透传，`render()` 不改）。
  compiler `required` 增补 `description` 必填——缺描述在生成时即失败。
- 基线测试：新增 `tests/shell/test_settings_shell.py`（轴恰两值、折叠通路保持、
  `"minimal"` 零存活消费者、路由描述非空）；
  `shell/tests/test_search_catalog.py` fixtures 同步并新增缺描述拒绝用例。

**验证**：`tests/shell` 130 绿（11 跳过 = 基线）；`shell.tests.test_search_catalog`
+ `test_i18n_catalog` 10 绿；`check.sh` changed scope 全绿（104 advisory 为既有
基线）；lifecycle-audit clean。`SearchCatalog.js` 已重新生成（+40 行，纯数据）。

**验收（2026-10-25）**：作者实机复核通过，M0 转已完成。

### M1 偏好原子套件纯 QML 拷入与重构（已完成，2026-10-24）

**实现**（11 原件全落 `shell/units/settings/controls/`，100% 纯 QML/JS，
零 Caelestia/Quickshell-native 依赖）：
- `ConnectedRect`：first/last 大圆角、中间 extraSmall 平接的连通基座，
  驱动全部行卡分组形态（`m3surfaceContainer`）。
- `PreferenceToggle`：ConnectedRect 行 + 双行文本 + `StyledSwitch` 药丸；
  整行 MouseArea 互补命中区（开关保有自己的 hit area，点文本同样切换），
  全行 StateLayer 按压反馈。
- `PreferenceSlider`：图标 + 主标 + 当前值 + 全宽纤细滑块。滑块按
  Caelestia StyledSlider 原件重构为无样式 `QtQuick.Templates` Slider
  （视觉全在 contentItem：渐隐剩余轨、端点圆点、按压生长细柄、拖拽
  Binding 覆写 pos 实现指跟手）；外包滚轮条带以 `wheelStep` 微调，
  滚轮不再滚动页面。
- `PreferenceInput`：双行标签 + 内嵌圆角输入框（焦点呼吸边框 1→2px
  primary、错误态翻转 error 色）+ 清除按钮 + validate（RegExp/函数）/
  errorText/`Component.onDestruction` 未提交编辑 flush——关页不丢输入。
- `PreferenceSelect`：`SplitMenuButton` 药丸桥接（model/currentValue/
  selected），合成器 input region 由页面注入（默认 null，原子不读
  app 服务）。
- `PreferenceStepper`：`MaterialStepper` 桥接（- 数值 +，按住重复），
  moved(int) 语义与底层 valueModified 一致。
- `PreferenceAction`：图标 + 双行文本 + 默认 chevron_right 尾箭头；
  副标 `animateChange` 滚动换值；禁用态 0.5 透明度动画。
- `PreferenceInfo`：纯只读属性行（图标 + 属性名 + 右对齐值），
  契约测试钉死无 MouseArea/StateLayer/clicked。
- `PreferenceHeader`：卡片组上方小节标（labelMedium 辅助色，
  `first` 免顶距并按父列 spacing 补偿）。
- `NexusSearchBar`：全圆角胶囊搜索框（search/clear 图标、聚焦呼吸
  边框、清除按钮随文本淡入）；root 即 TextField，消费方直绑
  text/accepted。
- `NexusPageBase`：详情页脚手架——大标题（titleLarge）+ isSubPage
  返回箭头（`backRequested` 信号，导航状态留在宿主，M2 接线）+
  maxContentWidth 封顶的滚动列（`StyledFlickable`，default property
  contentChild 注入 contentItem）。
- 桥接真相：全部走 `Appearance.m3colors/rounding/spacing`、
  `Typography`、`Metrics`、`Fonts`、`I18n`；零硬编码色值/字体。
  行节奏：panelPadding(20) 横距、spacing.medium(16) 纵距、
  spacing.small(8) 内距（对位 Caelestia 20/16/12 节奏，Nyxuri 值域）。
- KM4.6 预热规则落实：新合成池 `qs.units.settings.controls` 进
  SlotHost 预热名单（无顶层消费者的 qs.* 池首次解析不得落在
  Loader 内）。
- i18n：新增 `"Go back" = "返回"`；清除/搜索复用既有键。

**验证**：新增 `tests/shell/test_preference_atoms.py` 17 测试（池形状
恰 11 文件、无上游/副作用导入、零硬编码色、连通圆角契约、各原子 API
面钉死、搜索胶囊/页面脚手架契约、SlotHost 预热与 i18n 键）；
`tests/shell` 全量 147 绿（11 跳过 = 基线）；`test_i18n_catalog` +
`test_search_catalog` 10 绿；`check.sh` changed scope 全绿
（qml-lint 161 advisory 全为既有 missing-property 类——动态 QtObject
token 的已知限制，全库 --all 同类 3902 条为基线；unqualified 与
id-shadows（MouseArea.drag 遮蔽）已修零）；lifecycle-audit clean；
qmlformat 全量格式化通过。

**验收（2026-10-25）**：作者实机复核通过（比例、动画手感、StateLayer
反馈；页面消费者随 M3 接入），M1 转已完成。

### M2 视窗外壳与 NavPane 双行导航骨架（已完成，2026-10-24）

**实现**（chrome-only 重塑，业务面零改动）：
- `ControlCenterWindow` 重写外壳：退役 titlebar 框与 `navExpanded` 展开
  轨道；无边框 `rounding.extraLarge(28)` 视窗 + 既有 `CompositorBlurRegion`；
  顶部仅留极简拖拽带（DragHandler → `startSystemMove`）与右上角内嵌
  关闭按钮；外部 API 面（`openPage`/`openPageSection`/`prepareSearchTarget`/
  `advanceSearchTarget`/`currentRouteId`/`popoutClosed`/child-window 清理）
  与 `title: "nyxuri-settings"`（`focusWindow` 按名匹配）原样钉死。
- `NexusNavPane.qml`（units/settings 根，不开新 qs.* 池、预热零变更）：
  顶部 `NexusSearchBar` → 分组连通列表（Flickable）→ 底部两条
  `PreferenceAction` 配置快捷动作（编辑/复制路径，复制走既有 1400ms
  toast 键）。分组为 QML 侧呈现表（个性化/桌面/网络与设备/搜索与输入/
  系统，5 组 × 16 条顶层路由），表外 id 落尾部无标组兜底，改名不孤儿。
- `NexusNavRow.qml`：双行导航行——圆形强调色徽章（激活 primary /
  常态 secondaryContainer）+ DemiBold 主标 + 副标描述；激活整行
  secondaryContainer 胶囊、按压圆角收缩形变（对位参考树 NavLocations
  的 RadiusBehavior）；激活行自动滚入视野（`ensureRowVisible`）。
- 药丸搜索双通路：输入实时过滤导航行（title/description/sourceTitle/
  aliases 归一匹配）；同时弹层列出匹配的**深层**条目（`path.length > 1`
  且 `available()`，上限 8），点选/回车兜底走既有
  `SettingsBackend.openSearch` 深链（唯一业务 owner 保持在窗口）；
  Enter 优先首个可见路由，Esc 清空。
- `ConnectedRect` 增 `uniformRadius`（默认 -1 不生效；≥0 四角统一），
  承载激活/按压形变；四角加 radius Behavior，分组重排时组形平滑过渡。
- 路由描述翻译通路补全：`generate-search-catalog.py` 的 `description(id)`
  增设 settings 条目（路由）cases，`SpotlightCatalog.description(id)` 桥
  接；20 条路由描述 + 分组标签 + 快捷动作文案共 24 键补入 zh_CN。
- 处决 4 文件：`NavigationRailButton.qml`、`NavigationRailTabArray.qml`、
  `NavigationRailExpandButton.qml`、`FloatingActionButton.qml`（均唯一
  消费者旧 chrome，死刑断言进测试；`references/` 参考树不计）。

**验证**：新增 `tests/shell/test_settings_navpane.py` 17 测试（死刑断言、
窗口 API 面钉死、title 稳定性、chrome 事实、NavPane 组合原子、分组
全覆盖、零硬编码色、i18n 键）；`test_preference_atoms` 同步
uniformRadius 契约（断言空白不敏感化，钉语义不钉 qmlformat 换行）；
`tests/shell` 164 绿（11 跳过 = 基线）；`shell/tests` 81 绿（含
search-catalog 契约与 i18n 完整性）；check.sh changed scope 全绿
（104 advisory 全为既有 missing-property 基线）；lifecycle-audit clean；
qmlformat 全量格式化通过。

**验收（2026-10-25）**：作者实机复核通过（连通组形态、激活胶囊形变、拖拽、
路由标题 switchAnim；后续 fidelity 修订见下），M2 转已完成。

### M2-fidelity 修订：逐项对齐 Caelestia 实测值 + About 页（已完成，2026-10-25）

> 起因：作者对照实机截图指出与原版差距大（搜索框大小/窗口圆角/胶囊
> 形变/搜索结果真实性四项）。逐行比对参考树与 C++ 侧 tokens.hpp 后
> 全量修订；值全部以原版 token 实测为准。

**实现**：
- **token 扩充**：`Appearance.rounding` 增 `medium: 16`（窗口圆角 =
  Caelestia `rounding.large`）与 `extraLargeIncreased: 32`（激活胶囊），
  填自家梯子空位、零改名零冲突；按压收缩用既有 `small`(12)。
- **搜索框对齐原版**：无边框（原版 StyledRect border.width=0，NavPane
  只绑不可见的 border.color）、背景 surfaceContainerLowest、高度=内容
  +32 节奏、图标 `clear`（原为 `close`，杜撰）、未聚焦按压 StateLayer、
  图标边距 20/12；**杜撰的 1px 边框与聚焦呼吸边框处决**。
- **搜索框回归原版占位**：查明原版 `searchOpen` 全树零消费者、无任何
  结果 UI——M2 的过滤+建议弹层属 Nyxuri 原创，按拍板处决（routeMatches/
  suggestions/弹层/Enter-Esc 全灭），设置内搜索转后续独立立项（深链
  机器保留给 Spotlight）。占位钉死进测试（相关函数名死刑断言）。
- **NavRow 对值修正**：激活 `extraLargeIncreased(32)`、按压 `small(12)`、
  组边 28/中间 4 不变；**行距 4px**（原为 0 紧贴）+ 组间 +12px；未激活
  底色 `colSurfaceContainerHigh`（原 m3surfaceContainer 错值）；标题
  bodyMedium **恒定 Normal 恒定色**（原 bodyLarge+激活 DemiBold+变色，
  双杜撰）；描述 labelSmall；行内距 16、图标距 12；徽章 fillHeight
  ±1 出血、图标 grade 25（MaterialSymbol 增 GRAD 变量轴支持）。
- **分类纯几何**：原版 NavLocations **无分组标题**（杜撰的 PreferenceHeader
  导航标签移除）；单列扁平 + groupStart 驱动组间间隙与连通首尾；死键
  "Network & devices"/"Search & input" 清除。
- **窗口对齐**：圆角 28→`medium(16)`、去 1px 描边（原版无边框）；尺寸
  = 屏高×0.7、宽=高×16:9、min 800×500（原固定 980×665）；关闭钮对齐
  windowBtn（12px 圆角衬底 surfaceContainerLow、hover 变 m3error、按压
  scale 0.8、无 StateLayer）。
- **切页动画对齐 Pages.qml**：容器级淡出 200ms → 方向感知垂直 28px 滑入
  300ms（导航序向决定进出轴向）；`SettingsPageHost` 增
  `animationsEnabled` 开关（窗口侧关内部层动画，宿主仍管异步加载与
  搜索重试）；路由标题对齐 `title.large` 22px Medium。
- **渐隐列表**：`VerticalFadeFlickable` 纯 QML 移植（Mask+Gradient 渐隐
  遮罩 + 内容不足时渐隐收起）入 `shared/controls`；导航列表去滚动条。
- **About 页（新增需求）**：路由 `about`（icon `info`，导航底部独立分组）
  + `AboutPage.qml`——hero 连通卡（夜弧记号 + Nyxuri Shell + Quickshell
  版本）+ System 段（Hostname/Device/Distro/Kernel/Firmware）+ Software
  段（Quickshell/Qt/合成器）；数据全取 `SystemIdentityService`，版本探针
  （`quickshell --version` 定参）按需归服务层单次缓存（LIFE002/008 审计
  纠偏：视图零进程）；首个纯 M1 原子页面，M3 打样。引擎无版本通道，
  hero 版本行用 Shell 运行时（Quickshell）版本，如实映射。
- i18n：+8 键（About/Software/Hostname/Device/Distro/Firmware/Compositor/
  路由描述），-2 死键；路由描述经 catalog `description(id)` 翻译桥（生成
  器 settings 条目补 cases）。

**验证**：`tests/shell` 170 绿（11 跳过 = 基线；navpane 契约重写：搜索
占位钉死、原版比例/圆角/形变值钉死、About 路由与命令形状钉死）；
`shell/tests` 81 绿（catalog 路由集合补 about、死键清零）；check.sh
changed scope 全绿（249 advisory = missing-property 基线类 + 2 既有
singleton 提示；SettingsPageHost `id: layer` 遮蔽顺手正名
`pageLayer`）；qmlformat 全量通过。

**验收（2026-10-25）**：作者实机复核通过（搜索框比例、胶囊 32/12 形变、
渐隐列表、方向感知切页、About 页；后续像素级修订见第二轮）。

**事故修复（2026-10-25，mod+i 失灵）**：`FloatingWindow.minimumWidth/
Height` 并非 Quickshell 属性（正名 `minimumSize`），误赋值使 settings
单元 compiled empty、IPC 目标消失——已改 `minimumSize: Qt.size(800, 500)`
+ 尺寸下限并入 implicit 计算；同场修 `TapHandler.hovered` 运行时
undefined（hover 态改 `HoverHandler`）。两条陷阱钉进测试与
shell/AGENTS Quickshell 运行时约束 ④；`lint-qml.sh` import 集补 Quickshell
插件路径（注：qs.* VFS 混合导入下 qmllint 仍不做成员校验，Quickshell
API 面改动以实机为准）。IPC 实测 `--action settings` 返回 OPENING。

### M2-fidelity 第二轮：像素级对齐 + 双色分区 chrome（已完成，2026-10-25）

> 起因：作者实机复核提出三项（导航行过宽且右侧页面无法显示／全部
> 字体控件尺寸／关闭钮不对），要求逐细节对准原版。

**诊断（实测证据）**：
- `niri msg` 实测窗口 **800×1016**：`minimumSize` 赋值在 Quickshell
  0.3.2 把宽度钉死在下限（高度未受影响）——窗口半宽导致详情区仅
  ~430px，老页面挤爆；"导航过宽 + 右侧无法显示"同根因。
- 全局 0.85 缩放 vs 原版原生值的系统性差距（搜索框 48 vs 53px、图标
  20.4 vs 24、行高 56 vs 66、字号全线 -15%）。
- 关闭钮位置/尺寸/按压三处不符；且查明原版窗口为**双色分区**
  （BlobGroup 单色实证：左区面板 + 12px 框带 + 关闭钮同用
  surfaceContainerLow，中部 m3surface 承载页面）。

**实现**：
- **`NexusStyle.qml`**（units/settings 单例）：tokens.hpp + 字号权重 +
  Nexus 比例常量 1:1 移植，设置界面（chrome + 11 原子 + About）整体
  **脱离 0.85 缩放**；全部 `small+xSmall=12` 式组合算术消灭；原子池
  新契约禁 `Typography.*`/`Metrics.*`（颜色/动画仍归 Appearance）。
- **窗口 chrome 重构**：双色分区纯 QML 复刻——左区矩形（导航宽+32、
  左角 16）+ 关闭钮与框带同色融合；详情区按 Pages.qml 锚位（框带 12 +
  内距 16 = 窗边 28、距左区 28）；**size minimums 全面禁止赋值**
  （Quickshell 0.3.2 陷阱，下限由 Math.max 承担，测试钉死）。
- **关闭钮**：贴角零边距、36×32、r12、24px 图标、仅图标缩压 0.8、
  hover error 红、无 StateLayer、Accessible 保留。
- **NavPane 宽度 bug**：三边锚接漏设 width 退化成内容隐式宽——补
  `width: navPaneWidth`（实机坐实修复）。
- **搜索框/行/原子/About 全值归位**：53px 节奏、24/20 图标、14/11 字
  号、行内距 16-12、按压 12/激活 32 圆角、hero 28px 记号 48px。
- 拖拽：左区面板 + 详情标题带双 DragHandler。

**验证**：`tests/shell` 175 绿（11 跳过 = 基线；新增 NexusStyle 逐值
对照 tokens.hpp 的 parity 测试 + 双区 chrome/关闭钮/禁 minimums 契约）；
`shell/tests` 81 绿；check.sh changed scope 全绿；qmlformat 22 文件通过；
实机 IPC OPENING/CLOSING 双向、窗口宽度恢复（niri 按应用记忆用户拖动
尺寸 1664×1047 为用户偏好保留）。

**验收（2026-10-25）**：作者实机复核通过（分区、搜索框 53px、行高 66、
窗口宽度恢复）。

### M2-fidelity 第三轮：作者三项裁决 + About 页静默死亡修复（已完成，2026-10-25）

**作者裁决的刻意偏离原版**（钉死防未来对照回改）：
- 导航宽度：原版 `min(600, 窗宽/3)`（33%）观感偏宽——改 **`min(480, 窗宽/4)`**
  （稳定 25%），`NexusStyle.maxNavWidth` 600→480，测试钉死公式。
- 配置快捷动作：原版本无 footer，我们的扩展在导航底部观感突兀——从
  `NexusNavPane` 处决（信号/属性全清），**迁入 About 页「配置」段**（两条
  `PreferenceAction` 直调 `ApplicationService`/剪贴板，ShellPage 先例；
  复制反馈 = 行内副标 "Path copied" + 页面内 Timer）。
- 关闭按钮：原版有 windowBtn，作者裁决**完全不要**——贴角芯片处决，
  chrome 只剩左区面板；关窗走 mod+i toggle / 合成器；`"Close"` 键其余
  5 处消费者不受影响。

**About 页静默死亡修复（运行时日志实锤）**：
- `NexusPageBase` 的 default property 是单 `Item`（contentChild）——页面根
  直接挂 `Timer` 触发 "Cannot assign Timer to QQuickItem*" 类型错误 →
  整页实例化失败 → 宿主保留旧页、标题仍随路由更新（作者现象：动画重放、
  内容停在上页、标题已是"关于"）。修复：Timer 移入内容列（ColumnLayout
  data 接受非可视子项）；陷阱注释钉在代码位。
- 同场修 `Qt.version`（Quickshell QML 全局无此属性，undefined 静默击穿
  QString 绑定）→ 正名 **`Qt.qmlVersion`**，日志归零。

**验证**：`tests/shell` 177 绿（11 跳过 = 基线；导航宽 /4+480、关闭钮死刑、
NavPane 无 footer、About 配置段四组新契约）；`shell/tests` 81 绿；check.sh
changed scope 全绿；qmlformat 通过；实机 `--ipc settings open about`
日志零警告（Timer/Qt.version 两类错误前后对照）。

**追修（同日）**：About 页"双关于"——窗口路由标题垫片与 NexusPageBase
自带标题叠加。定则**标题归页面**：`NexusPageBase` 暴露
`rendersPageTitle`，窗口垫片对自绘标题页自动退位（隐藏 + 高度塌缩，
旧页面继续用垫片）；此即 M3 全页面化后的通用机制。另：Quickshell 的
QML 全局无任何 Qt 版本属性（`Qt.version`/`qtVersion`/`qmlVersion` 三者
皆 undefined，首次"干净"系旧实例未重载假象）——Software 段删 Qt 行
（Quickshell + 合成器），注释钉因。实机两轮开合日志零警告。

### M3 核心页面首批积木化翻新（待验收，2026-10-25）

> 范围拍板（作者裁决）：Gamma 全量 + DisplayConfiguration 行级归原子
> （画布/事务流/高级区/缩放对话框保留，深度重设计留 M4）；M0–M2 同日
> 作者实机过目转已完成。

**实现**（四页一页一 commit，About 页模式推广）：
- **通用模式**：`NexusPageBase` 脚手架（自绘大标题 → 窗口垫片退位）+
  `PreferenceHeader` 小节标 + 连通组原子行（接缝 `extraSmall/2`=2px，
  无组容器）；`searchLeaf`/`parentModal`/`presentationActive`/
  `navigateRequested`/`closeChildWindows` 窗口契约面逐页保命；
  `SettingsSearchAnchor` 声明字节级不变（catalog 零重生成）；非视觉
  子项（Timer/弹窗/Binding/Connections）一律挂内容列（About 事故定则）；
  几何只用 `NexusStyle`，颜色只用 m3 系。
- **AccountPage**（618→837 行重构）：hero 保留 `AccountProfileHeader`；
  语言/蓝牙/快捷键/个性化四组归原子（select×2 注入 PopupInputRegion、
  toggle、action）；设备行（图标+双行+连接钮+溢出菜单）与壁纸 6 格
  快选为原子无形状的 sanctioned 自定义行；MaterialCard 双列布局退役
  （Nexus 单列）。
- **ThemePage**（1007→约 900 行）：透明度/模糊/锁屏/光标（主题选择器
  包 ConnectedRect、尺寸滑杆、双隐藏）/图标主题/四字体归原子（滑杆
  值显示含 Off/毫秒语义）；页内私有 Section/ToggleSettingRow/
  SliderSettingRow/SearchSelectSettingRow 四件套处决；预览卡对、
  面板样式卡、matugen 色板按钮组、Super 键键帽、模板列表（SettingsRow
  平行清单入单卡）保留；requestTemplateDeletion 对外 API 不动。
- **WallpaperPage**（1010→约 950 行）：预览 hero×2、循环/填充/转场
  按钮组、Bézier 编辑器+坐标对话框、文件浏览器/取色器×2 保留；
  Per-monitor/Overview 开关、输出选择×2、视差四开关、缩放/行程、
  图像效果四滑杆归原子；chartSide 下限 360→240 适配 800 封顶列宽。
- **Displays**：壳声明 `rendersPageTitle: true` 令窗口垫片退位，子页
  各自渲染大标题（SpotlightCatalog title 桥）；GammaControlPage 全量
  原子化（`SidebarFlickable`/gapFor/pullExpansion 机制随页退役；时间
  输入正则校验、经纬度范围函数校验、只读状态行归 `PreferenceInfo`；
  first/last 随可见性动态绑定保连通几何）；DisplayConfigurationPage
  行级归原子（DisplayChoice×5→PreferenceSelect、Enabled 行→Toggle、
  逻辑坐标→Input(smallField)、高级展开→Action；画布+事务栏+高级/
  热角区块+缩放对话框保留，对话框 token 换 NexusStyle；滚轮让位 Binding
  `flickable.interactive`）。
- i18n：新增 Color scheme 键；死键三批清除（Choose language/Choose
  color mode/Choose icon theme/Select * font×4/Hide the cursor after
  inactivity…/Select output/Desktop|Overview wallpaper output/Enable
  vertical parallax first/The current transition does not use */过渡
  tooltip 等 16 键）。
- 旧组件生态核查：SidebarFlickable（sidebars 仍在用）、
  GeneralSliderSetting（Dock/Keystone 仍在用）、DisplayChoice（高级/
  热角区块仍在用）、SettingsSection（未翻新页面仍在用）全部保留，
  零消费者文件为零——M4 全页面化时再清算。

**验证**：新增 `tests/shell/test_settings_pages.py` 28 测试（四页+壳：
脚手架/标题、窗口契约面、锚 id 钉死、原子在场、业务 owner 钉死、
sanctioned 自定义件在场、页内私有行组件与旧词汇死刑、壳路由保命）；
`tests/shell` 206 绿（11 跳过 = 基线）；`shell.tests` 10 绿；
check.sh changed scope 全绿（27 advisory = 既有 missing-property 基线）；
qmlformat 全量通过；lifecycle-audit clean。

**待验收**：实机视觉/交互（四页连通组形态、select 药丸菜单越界输入
区域、滑杆拖拽/滚轮、Gamma 动态分组几何、DisplayConfig 事务流与新行
的交互、深链搜索锚滚动定位）；深链回归（Spotlight→displays.gamma
深两级路径）。M4（全页面覆盖与废弃代码清算）待开始。

**修订（2026-10-25，作者 M3 验收反馈）**：Account 壁纸快选格子仍按旧
~450px MaterialCard 调参（152px 上限），进 800px Nexus 列后被
GridLayout 拉伸、比例失真且两侧空洞。改自适应满宽条：列数 ≥640px 取
6 否则 3（6 项恒整除铺满，无尾格无死区），格宽=(行宽-缝)/列数、5:4
恒定，`wallpaperPreviewMaximumWidth` 处决；当前壁纸叠 2px primary 内缩
描边选中态；空态占位 `columnSpan` 跨全列。列数公式与 152 上限死刑钉
进 test_settings_pages（207 绿）。

### S0-4 资产收编与实机验收·收窄版（已收口，2026-11-01）

> 拍板：dashboard 双轨**终局保留**（退出功能阉割档候选）；「页面内容收编进各
> 插件」依赖 S0-3 去中心化落位，挪入 S0-3；本站先行收口清算 + 收编核查 + M3/M4
> 机器验收证据。执行序调整为 S0-4（收窄版）→ S0-3，站号不动。`shell/archive/`
> 作者裁决保留，补 README 封存登记（引用关系：test_shell_architecture 落位契约
> 钉住两份服务文件存在性，动 archive 必须先动测试）。

**清算**：`ui/MaterialCard.qml`（M3 后零消费者，LEGACY_VOCABULARY 死刑词表
保留防复活）、`ui/SidebarStagger.qml`（抽屉删除后零消费者）处决；
`plugins/settings/AppBrowserPopup.qml`（autostart 页伴生弹窗，唯一消费者在
archive）迁 `archive/settings/autostart/` 与家族同放。零消费者扫描（词边界，
含 manifest source 与脚本引用）覆盖 ui/ 平面池、settings 根、dashwindow、
commons、services——其余全部有真实消费者。扫描升格常驻契约
`tests/shell/test_asset_placement.py`：消费者语料 = 运行时树（qml/js/py/sh/toml），
测试源不算消费者；处决名单防回流断言。

**测试对齐（S0-1/S0-2 遗留 22 处预存在红全数改写绿）**：
- 锚点词表：`"id":"…"` JSON 字面 → `anchorId: "…"` 运行时注册（test_settings_pages
  全量跟词；Displays/DefaultApps 封存页测试类处决，archive fallback 退役）。
- 四件套尸体：settings-routes.json / SearchCatalog.js 读取点全部改读
  `manifest.toml`（test_settings_navpane 路由+分组、test_settings_shell 描述、
  test_shell_architecture p3/r11）；生成器 generate-search-catalog.py 升格死刑
  断言（必须保持退役）。
- i18n：r3 的 qsTranslate 词表断言（Account/Bar/Dock/Theme）随 S0-2 词表进
  manifest 失实——新契约为「manifest 全部 settings 词条（16 路由 + 53 锚点的
  title/description）必须在 zh_CN.toml 经 context-or-default 可解析」，翻译桥
  真相是 SpotlightCatalog `I18n.tr(title, context)`。

**实机验收证据（隔离实例：独立路径防 IPC 串台，账本预置 11 单元 disabled 只开
settings）**：`shell status` → `IPC_READY`、零 compiled empty；16 路由
`settings open` 全 OK；双轨 default↔dashboard 经 config watcher 翻转后以合成器
toplevel 标题作证（`nyxuri-settings` ↔ `nyxuri-settings-dashboard`，窗口粒度
切换如 SettingsHost 设计）；spotlight 单元临时启用 + `unit reload` 后
`spotlight search` → `SEARCH` 相位（深链点击属 UI 面，归作者视觉验收）。
启动告警（QQmlVMEMetaObject invalid context / Tray barVisualBounds /
FilePickerWindow buildBreadcrumbItems）与 HEAD 干净副本对照实例逐条一致——
0.3.2 冷编译预热闭包预存在产物，非本站回归。

**验证**：`tests/shell` 282 绿（11 跳过=基线，净变化 +2 契约、−2 封存页类）；
`run-tests.py --all` 五分类 106 绿（5 跳过=基线）。

**待办归位**：M3/M4 视觉过目归作者（过目后 shell/ROADMAP M3/M4 转已完成）；
dashwindow 手写目录接不接 PluginRegistry 随 S0-3 设计定夺。

## KM4.5 拆迁与正名（追加式，2026-10-17；2026-11-07 自 shell/ROADMAP.md 迁入归档，正文逐字保留）

### KM4.5 拆迁与正名（2026-10-17，随主线 KM4.5）

> 起因：`modules/`（16 域，混居 4 个非单元支撑目录）与 `units/`（12 个纯 manifest
> 存根）两棵树表达同一概念且数目对不上，"bar 在哪"要查三处——文件树不表达架构，
> KM3.5 的成果在 Shell 侧未兑现。本阶段模仿 KM3.5：先处决、再正名、一次契约同步。
> 单元 ID（`shell.<domain>`）不变，ledger/state/IPC 零影响；实机验收与 KM4 合并。

**处决清单（全部落地）**：
`hotcorners/` → `app/services/HotCorners.qml`（唯一消费者 AppShell，宿主能力面）；
`filepicker/` → `app/services/FilePickerWindow.qml`（keystone + settings 共用对话框
能力）；`quicksettings/` → 并入 `sidebars/quicksettings/`（唯一消费者）；`systemcards/`
拆分——纯展示 27 文件 → `shared/cards/`，直读 app 单例的 6 文件
（SystemCardContent、SystemWeatherCard、SystemBatteryTank、SystemClockCard、
SidebarCookieClock、NetworkInterfaceHistoryService）→ `app/services/`，其中两时钟卡
按 LIFE002 服务层规则补齐 `Component.onDestruction` teardown；SlotHost 重复注释块、
全树 `__pycache__` 清除。

**正名**：`modules/<12 域>` 物理并入 `units/<域>/`，manifest.toml 与代码同目录——
目录即单元，兑现内核「Adding a unit = adding a directory」承诺；顶层目录 10 → 8，
`shell/modules/` 消失；`qs.modules.*` → `qs.units.*` 全量正名（实树 96 行 import +
SlotHost 预热 12 行 + UnitCatalog source ×12 + 工具链与测试）。

**契约同步**：shell/AGENTS 三层边界重写（app/units/shared + 支撑代码归宿规则）；
architecture-matrix 重写（12 单元矩阵）；plugin-model §6 承载修订；shell/development
分层词表；audit-lifecycle / generate-search-catalog / run-tests / check.sh /
test_unit_catalog 路径改判；契约测试改测新真相（test_shell 61 绿、
test_bugfix_regressions 109 绿，含 app/ 56 文件收敛断言与 units/ 死刑断言：
`shell/modules/` 必须不存在、4 个已处决支撑目录不得复辟）。

**验证**：全量引擎 970 测试绿（14 跳过 = 基线）+ Shell 分类 118 测试绿 +
audit-lifecycle clean（560 文件）+ 单例纯度扫描零 offender。实机行为/视觉验收与
KM4 合并进行。
- **KM4.6 Shell 结构微整**（2026-10-17，结构层不碰行为；先行提交 KM4.5 后开工）：
  处决——`packaging/`（死独立发行管线：release.py 已不存在，gen-deps 只写仓库根
  packaging/，dependencies.json 引用旧 modules 树）整目录处决；`fallback/` 解散
  （lottieqt 桩零消费者删除；M3Shapes 具名模块桩以真身份迁
  `shared/controls/shapes/M3Shapes/`，wrapper `FALLBACK_QML_PATH` →
  `SHAPES_QML_PATH` 指向 shapes 目录——桩紧邻其未来要吸收的 vendored 数学）；
  `assets/` Junk Drawer 解散——shaders 按域归 `units/{keystone,launcher,wallpaper}/
  shaders/`（frag+qsb 同迁，消费改 unit 相对 `Qt.resolvedUrl`），i18n 词典 →
  `app/i18n/`，icons → `app/icons/`，内置模板注册表 → `app/templates/`
  （matugen-registry.sh builtin 根同步），第三方许可证 12 件折入 `LICENSE`
  第三方附录（逐字保留）；Paths 死属性清算（builtinMatugenDir/audioScriptsDir/
  weatherIconsDir/weatherScriptsDir/scriptsDir 旁挂）。
  分池——`app/cards/` 新建：SystemCardContent/SystemWeatherCard/SystemBatteryTank/
  SystemClockCard/SidebarCookieClock 5 个直读单例的 UI 渲染件出 `services/`
  （services 50 → 45 只剩服务+配置+能力面；NetworkInterfaceHistoryService 留列）。
  scripts 收拢 9 → 5（dev/lib/media/system/theme）：build→dev、lyrics+cava→media、
  capture 解散（LockSnapshot.qml + lock-snapshot.sh 一体归 `units/lock/`——
  QML 混居 scripts 的错位纠正）。
  正名——`settings/dashboard` → `settings/dashwindow`（语义钉死：它是
  settingsPanelStyle==="dashboard" 的卡片窗变体，非页面）；`bar/quicksettings` →
  `bar/quickpanel`；`sidebars/{dashboard,quicksettings}` 保留（对齐
  `WidgetState.dashboardSidebarView` 的运行时 view id）。
  验证：全量引擎 970 + Shell 分类 118 + audit-lifecycle clean（562 文件）+
  单例纯度零 offender + check.sh + 沙箱部署绿。终态顶层：app/units/shared/scripts/
  tests 五目录 + 8 根文件。
  实机验收修正（同日）：settings 窗口 on/off 实测暴露 `shell.desktopcards`
  永久 compiled empty 刷屏——`qs.app.cards` 新池无顶层 import、首次解析落在
  Loader 内（0.3.2 约束①），SlotHost 预热名单补行；顺带坐实自愈上限（原 "/2"
  为写死字符串，无限重试刷到 pass 11/2）——per-unit `failedHeals` 计数、超限
  给决断性日志、unit-changed 清零重新武装。登记 KNOWN-ISSUES 已修复段；
  AGENTS 约束①增补推广条款：新 qs.* 池必须进预热名单。
  同日复核：上述修正未根治 compiled empty——真因是重构残留的失效相对 import
  （DesktopCardCanvas import `../systemcards/…`、SystemCardContent import
  `../shared/cards/…` 少一级 `../`，SystemCards 模块解散后真身在 `shared/cards/`），
  文件不存在属硬错误；两处正名后恢复，settings ShellPage 误引 `UnitControl`
  一并正名 `UnitControlService`（预热与自愈上限修正独立成立，保留）。
  开关无反应同场根治——`probe_running_shells` 误排 `getppid()`，shell 派生的
  nyxuri 探测不到自己的 qs 父进程，bridge 静默丢 unit-changed；修为只排除
  自身，真实进程拓扑回归测试坐实（tests/test_bugfix_regressions）。

## B 卷实施记录（追加式，2026-11-07）

### B0 整抄基线入库（待验收，2026-11-07）

**入库**：三能力源之二物理 `cp` 入 `shell/plugins/bar/vendor/`（保源相对
子路径，inert、无消费者、不进装载闭包）——end4 皮肤件 8 件（Bar/
BarContent/BarGroup/BarGroupStylePopup/Divisor/StyledPopupHeaderRow/
StyledPopupValueRow + common 的 RoundCorner，B3 消费）、dux 机制件 6 件
（WidgetModel.js + SurfaceWidgetFactory/Host/Context + BarWidgetDefaults/
DensityPresets，B4 消费）；各带 README（来源、inert 状态、消费者计划、
B5 清算条款）。第三源（树内 QuickSettings.qml 范式 + keystone morph 引擎）
为保护对象无需拷贝。裁剪清单成文：[bar-island](../shell/bar-island.md)
（四类裁剪逐件过堂 + 不抄清单 8 项裁决 + 晋升/豁免机制），llms.txt 已索引。

**verbatim 偏离登记**：仅 end4 Bar.qml/BarContent.qml 剥离行尾空白共 9 行
（git whitespace 门禁），其余 12 件与源逐字节一致（cmp 核验）。

**豁免登记（B0 起 B5 止）**：① files.sh `nyxuri_qml_files` 跳过 `*/vendor/*`
（qmlformat/qmllint 不吃基线原格式）；② test_qml_structure 单例 import 扫描
排除 `vendor` 路径段（上游自带 import 形态，如 dux `qs.Common` 读 `I18n.tr`）；
③ test_i18n_catalog 语料排除 `vendor`（基线字面量 `I18n.tr` 非我方词典义务、
基线文本不算真实消费者）；④ test_shell_architecture 三处树级扫描排除
`vendor`（plugins 目录小写卫牛——基线保源相对布局含 `Modules/` 驼峰、
废弃 import 禁令——基线上游词表 `qs.Common`/`qs.Services`/`qs.modules.*`、
`Quickshell.execDetached` 禁令——dux factory 内 exec 属④类裁剪目标）；
⑤ audit-lifecycle 本就按 `vendor` 路径段排除，零改动；⑥ 消费者门禁扫描池
（ui/ 平面池、plugins/settings 根）本不含 plugins/bar/，零改动——B5 结账
统一清算。许可证附录 provenance 两节挂起（作者自领，verbatim 文本已在
shell/LICENSE 附录：end-4 GPL-3 / DankMaterialShell MIT）。

**验证**：tests/shell 全量绿（405 测试、11 跳过=基线，含
test_qml_structure/test_plugin_decoupling/test_plugin_manifests/
test_asset_placement/test_i18n_catalog/test_shell_architecture 门禁面）+
test_ai_specs 绿 + check.sh 绿（changed scope：whitespace/qml-format/
shell-lint/qml-lint/lifecycle-audit 五步）+ `HOME=$(mktemp -d) python3 -m
nyxuri test` 沙箱部署绿。运行零变化论证：零 manifest/entryPoint/SlotHost
预热/引用改动，vendor/ 文件惰性，PluginRegistry/装载闭包不触及。

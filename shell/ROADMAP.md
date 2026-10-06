# Nyxuri Shell 路线图

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

### R10 Action Gateway 与模块自治

**目标：** 桌面意图有统一边界，功能域拥有自身状态与副作用。

**实施：** 审查全部外部进程、文件写入、剪贴板、Niri IPC、URL 打开及配置写入；UI 直接副作用迁到 Action Gateway 或领域服务。缩小 `AppShell.qml`，保留根装配、跨模块连接和公开 IPC，不承载领域业务。每项动作定义 owner、参数形状、成功/失败/取消结果和反馈；减少只转发的抽象与无必要全局单例。

**验收：** UI 不直接启动桌面命令或写配置；动作有参数形状测试与失败清理测试；可选服务缺失时模块仍能装载并明确降级；架构 import/副作用契约通过。

### R11 Nyxuri Shell 控制面与透明度

**目标：** 提供按需加载、用户可理解且可行动的 Shell 管理页面，不做开发者对象检查器。

**实施：** 展示模块启用/加载状态、可选依赖可用性、降级/最近错误、配置与诊断路径及安全关闭/恢复操作。允许展示资源占用数字，但必须提供独立设置开关；关闭时完全不采样、不留 Timer/Process，开启后才按需低频采样，并显示来源与更新时间。诊断导出过滤凭据、配置内容及敏感环境信息。

**验收：** 页面关闭后无监控开销；采样开关真实启停采样；展示状态与实际生命周期吻合；错误信息可采取行动；诊断内容经脱敏测试。

### R12 Wiki 重置与新标准

**目标：** 清理重复、过时和不可维护的资料，建立精简、可验证的 Wiki 结构。

**实施：**
- 先完成 R7–R11 的源码与行为事实，再重整 Wiki，避免先写出未实现契约。
- 保留单一导航/真值分工、架构边界、生命周期 schema、当前开发调试流程、上游参考说明；每份文档有唯一职责、owner、证据来源和更新触发条件。
- 合并 `audit.md` 与 `cleanup-audit.md` 的现行内容；历史审计结论移入归档或删除。将 `tree-inventory.md` 转为可生成/可校验清单，无法持续更新的手工统计移除。
- 上游资料明确标记为非项目契约；恢复矩阵与比对档案保留为非主路径历史附件；删除被源码、测试或新契约替代的重复说明。

**验收：** Wiki 主导航精简且无重复权威；每个现行架构结论可追到源码/测试/决策；链接有效；新契约可由测试或脚本校验；无法复现的数字与结论不再作为现状描述。

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

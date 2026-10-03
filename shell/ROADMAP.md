# Nyxuri Shell 路线图

本文件只维护当前计划、阶段依赖、状态和验收门槛。源码与行为测试是运行事实；
[开发约定](AGENTS.md)是设计不变量；[审计报告](wiki/audit.md)记录已核对事实；
[净化审计](wiki/cleanup-audit.md)记录问题清单与建议动作；[开发与调试](wiki/development.md)记录工具流程。

## 状态规则

任务状态只使用以下五种：`待开始`、`进行中`、`阻断`、`待验收`、`已完成`。
历史交付只保留简表，不能改变当前任务状态。测试通过、跳过、环境阻断和产品失败必须分开记录；
目录存在、字符串匹配、Loader 存在或隐藏 UI 都不能单独构成完成证据。

## 目标与不变量

- Nyxuri Shell 是独立产品；核心启动路径保持小、快、可解释，视觉质量不因清理而下降。
- 运行代码按职责组织：`app/` 负责装配和真正的全局边界，`modules/` 负责功能域，`shared/` 只承载实际复用的纯组件与纯函数；跨层依赖和副作用必须有明确 owner。
- `shared/` 保持纯净，但不以目录名决定去留；每个文件必须有真实复用者或明确的基础层理由。
- UI 通过 Action Gateway 表达桌面意图；外部命令使用参数数组，执行、失败、取消和超时可追踪。
- 模块停用必须真正停止 Timer、Process、请求、连接、监听器、窗口和旧代回调；`visible: false` 不算停用。
- 原版 Niri 是基础兼容目标；扩展能力逐项核实，不能把整个 native bridge 作为不可拆分依赖。
- Cava、地图、歌词、录音、预览等可选能力不能阻断核心 Shell；缺失时必须局部降级。
- 参考 `shell/references/iNiR` 的取向，Nyxuri 自有业务逻辑以 QML/JavaScript/外部脚本为主；
  “去 C++”指移除项目自有 native 实现，不否认 Quickshell、Wayland、Niri 或系统服务本身的原生实现。
- 参考资料、第三方代码、生成物和构建缓存不得进入运行时加载闭包。

## 当前阶段：净化审计与启动闭包重建

当前阶段暂停新功能扩张，先解决路线图、边界、命名、启动和证据问题。基线与逐项位置见
[净化审计](wiki/cleanup-audit.md)。

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
| 待开始 | 删除 Nyxuri 自有 C++ 构建链 | R4-C-05 | 删除自有 C++、fallback、native 测试、CMake native target、原生安装元数据和遗留生成入口；默认构建不要求 C++ 编译器、Qt native target 或 native CTest |
| 待开始 | 完成结构与行为收口 | R4-C-06 | 每个功能域可从单一目录追踪到界面、状态、数据和动作；Niri 只有一个状态源；核心 QML/JS、生命周期、原版 Niri 和退出清理测试全绿 |

### R5 资源、文档与测试收口（P2）

| 状态 | 任务 | 前置 | 验收 |
| --- | --- | --- | --- |
| 待开始 | 盘点图标、翻译、shader、主题和第三方资源消费者 | R2/R3 | 核心、可选、封存、第三方和死数据分类完成，许可证可追溯 |
| 待开始 | 统一 README、wiki、注释和上游参考资料职责 | R1/R3 | 不再把上游安装或旧品牌误当 Nyxuri 契约 |
| 待开始 | 按逻辑、运行时资源、native、图形环境和静态规则分类测试 | R4 | 报告按类别记录，不用单一总数代表完成 |

## 后续阶段

### P4：壁纸、调色与模板兼容

前置：R1-R5 完成，核心启动和生命周期门禁通过。

- 核对 Noctalia 模板、变量、过滤器和 palette.toml 字段，不自行发明兼容语法。
- 复用已验证的壁纸、M3 调色和模板算法；明确 native 必要性与失败降级。
- 验收 GTK、Fcitx、Kitty、Starship 和用户模板无需重写，用户覆盖不会被覆盖。

### P5：完整宿主、部署与双轨生态

前置：P4 完成，六动作和核心 Shell 行为已验收。

- 验收 launcher、session、settings、clipboard、lock、wallpaper-random 六动作及兼容入口。
- 通过原子复制、Dunder、manifest、快照、回滚和卸载契约接入可选部署流程。
- Noctalia 模式与自研模式按需运行，切换失败不损失配置、不留下受管残留。

### P6：整体验收与未来移植

前置：P5 完成。

- 固定机器、版本、分辨率、缩放和字体，分别记录冷/暖启动和稳态资源基线。
- 验收核心离线、缺插件/设备、锁屏、会话结束、SIGTERM、目标崩溃和失败恢复。
- 完成视觉、行为、资源和文档四类证据后，才接纳封存功能或多合成器移植。

## 历史交付简表

这些条目保留历史可追溯性，不自动表示当前源码已通过对应验收；详细证据以链接文档为准。

| 阶段 | 历史交付 | 当前解释 |
| --- | --- | --- |
| P0 | 启动、依赖、资源接口和 Niri 能力初步盘点 | 历史调查；事实按 R1 重新核对 |
| P1 | 隔离启动、基础界面、Shell 切换和开发闭环 | 历史里程碑；不能替代 R2 当前证据 |
| P2 | 四层骨架、Action Gateway、按需加载和 native 解耦基础 | 历史架构交付；R4 重新验证边界和生命周期 |
| R4-C | 活跃交付中；已交付 R4-C-01 域服务回迁、R4-C-02 命名法典与假桩清理、R4-C-02a app 边界收敛与 Niri 单一入口、R4-C-03 提升 nyxuri-shell 根入口与路径自愈、R4-C-04 彻底解耦全部 Native 插件与统一生态体验 | 业务层除 I18nManager 外 0 Clavis 依赖；解耦 7 大 C++ 插件为纯 QML/JS；砍掉 bin/ 目录；背光与色彩系统级联动；单测契约覆盖 |
| P3-R00/R01 | 参考树固定、恢复点和功能矩阵 | 资料保留；见 [恢复矩阵](wiki/recovery-matrix.md) |
| P3-R02..R08 | Bar、通知、设置、锁屏、启动器和剪贴板恢复 | 历史恢复记录；证据由 R1/R2 重新归档 |
| P3-R09 | 按需启动、动作收敛、生命周期和视觉门禁 | 仍有未完成门禁，不标为整体完成 |
| P3-R10 | 生命周期静态审计与资源治理 | 静态规则保留；行为证据由 R4 重新分组 |
| P3-R11/R12 | 云业务、字体、图标、轮询和死资源清理 | 历史清理记录；资源由 R5 重新盘点 |
| P3-R13 | 脚手架、死 C++、命名和共享层整理 | 历史清理记录；品牌与构建由 R3 收口 |

## 待作者拍板
1. **[已拍板]** `Clavis` 内部标识处理：作者明确指示 CPP 部分不动（后续直接对接 R4-C 全面去 C++ 化）；QML、路径、脚本全部收敛至 `nyxuri` 命名空间，仅保留极薄兼容层。
2. `references/` 与 `wiki/upstream-*` 是否长期保留，或压缩为最小来源/许可证档案。
3. **[已拍板]** Keystone、天气、地图、歌词等能力的核心/可选边界：作者明确拍板放弃 Cava、地图、歌词、窗口预览；已在 R2 彻底物理移除相关 native 插件、fallback 与死 QML UI，相关消费者转化为零开销安全桩。
4. **[已拍板]** 生成文件、qsb、vendor Python 包和测试 fixture 的版本控制策略：qsb 作为免编译运行资产保留；SearchCatalog.js 脚本生成入库由单测校验；vendor 清理缓存；fixtures 隔离在测试树。
5. **[已拍板]** 翻译与对外兼容：废除 2.6 万行 XML，采用纯 TOML 双语字典；对外变量优先 NYXURI_*，兼容读取 CLAVIS_*。
6. **[已拍板]** 目录极简与 `bin/` 处置：作者明确拍板砍掉 `shell/bin/` 目录，将 `nyxuri-shell` 提升至 `shell/` 根目录，与 `shell.qml` 并列构成一动一静、一外一内的极简双入口；全库命名统一遵循艺术级命名法典；暂不改动 C++ 部分。

## 当前门禁

- 任何新依赖、直接副作用、跨层 singleton、常驻资源或未解释的视觉回退都会阻断合并。
- 每个任务必须写明旧实现的处理方式：保留、迁移、封存或删除。
- 每个保留文件必须有真实消费者和明确 owner；全局服务必须证明跨模块必要性。
- Niri 运行时必须通过单一服务入口；模块不得复制窗口、工作区或输出状态。
- `shared/`、`bin/`、`packaging/` 按实际用途逐项清理，不因目录名称整体删除，也不保留死文件和重复包装。
- 新增抽象必须减少重复、状态或生命周期复杂度；只做转发的文件不得作为结构性成果保留。
- 每个阶段完成前，源码、测试、环境、资源和文档状态必须相互一致；无法复现的历史数字只能作为历史备注。

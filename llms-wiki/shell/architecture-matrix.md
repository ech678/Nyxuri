# Nyxuri Shell 五层纯净架构与边界矩阵

本文件是 Nyxuri Shell 的架构契约与分层依赖真值表。在 R4-C-05/06 全面去 C++ 收口后，原生 `native/` 层与 CMake 构建链已彻底注销与物理移除；KM4.5 拆迁正名后曾确立三层模型（`app/`、`units/`、`shared/`），S0-1 五件套迁移（Omarchy 骨架对位）定形为 `app/`（纯装配）、`commons/`、`ui/`、`services/`、`plugins/` 五层纯净模型——插件代码与 `manifest.toml` 同目录（目录即插件，内核 registry 以目录名派生 `shell.<domain>` id），规范其职责、文件所有者、允许的导入规则（Import Whitelist）、输入输出契约与副作用边界。

---

## 1. 五层分工总则

```
┌─────────────────────────────────────────────────────────────┐
│                            app/                             │
│  纯装配与宿主数据层：AppShell/SlotHost/UnitCatalog/Paths/     │
│  WidgetState/ActionGateway/icons/templates                   │
└──────────────┬───────────────────────────────┬──────────────┘
               │ 依赖注入 / 动作派发            │
┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
│     plugins/<domain_a>/     │ │     plugins/<domain_b>/     │
│  manifest.toml + 功能域视图  │ │  manifest.toml + 功能域视图  │
│       与专属 Backend        │ │       与专属 Backend        │
└──────────────┬──────────────┘ └──────────────┬──────────────┘
               │                               │
               └───────────────┬───────────────┘
                               │ 仅依赖纯组件 / 代币 / 服务单例
┌──────────────────────────────▼──────────────────────────────┐
│        commons/ 与 ui/（纯展示）    +    services/（服务层）   │
│  commons/：设计代币、纯算法 JS、i18n、纯展示系统卡片 (cards/)  │
│  ui/：平面原子控件库 + shapes/                                │
│  services/：域服务、配置存储、宿主能力面与跨单元渲染边          │
│  【commons/ui：零外部服务、零进程、零文件IO、零网络】           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 分层契约与 Import 白名单

| 层级 | 路径 | 核心职责 | 允许 Import | 严禁行为 / 副作用 |
|---|---|---|---|---|
| **app** | `shell/app/` | 纯装配与宿主数据层（`AppShell`/`SlotHost`/`UnitCatalog`/`Paths`/`WidgetState`/`ActionGateway`/`icons`/`templates`） | Qt 原语、`Quickshell`、`qs.commons.*`、`qs.ui`、`qs.services`、按需装配的 `qs.plugins.*` 插件 Host | 禁止在展示组件中写死命令或业务逻辑；禁止绕过 `ActionGateway` 随意执行外部进程；非 `NiriService` 严禁直接建立 Niri IPC 连接 |
| **services** | `shell/services/` | 服务层：域服务与配置存储（`ThemeService`、`NotificationService`、`PersonalizationConfig`、`UiPreferences` 等）、宿主能力面（`HotCorners`、`IdleInhibitorSurface`、`FilePickerWindow`）、跨单元服务态渲染边（`SystemCardContent` 等五个系统卡片） | Qt 原语、`Quickshell`、`qs.commons.*`、`qs.ui`、`qs.services`（同层）、`qs.app`（窄接口） | 副作用必须有 owner 登记与显式销毁；展示组件不得下沉为服务；不得反向 import `qs.plugins.*`（跨域协调走 app 窄接口） |
| **plugins** | `shell/plugins/<domain>/`（`manifest.toml` + 代码同目录） | 十二个可开关插件：`bar`, `desktopcards`, `dock`, `keystone`, `launcher`, `lock`, `notifications`, `regionselector`, `session`, `settings`, `sidebars`, `wallpaper` | Qt 原语、`Quickshell`、`qs.commons.*`、`qs.ui`、`qs.services`、同域相对路径 `./*` 或 `qs.plugins.<domain>.*` | **严禁横向私自跨域导入**（如 `plugins/launcher` 直接导入 `qs.plugins.settings`）；跨域桌面意图必须路由至 `ActionGateway`；插件开关真相在 ledger，Shell 只投影（unit-model §6） |
| **commons / ui** | `shell/commons/`、`shell/ui/` | 纯净原子复用层：`ui/`（原子按钮/卡片/滑动条/指示器等平面控件 + `shapes/` 具名模块桩）、`commons/`（设计代币与字体 token、数学/时间/格式化/TOML 解析纯算法 JS、纯 QML/JS 国际化单例与内存字典 `i18n/`、纯展示系统卡片 `cards/`） | Qt 原语、`qs.commons`、`qs.ui`、`qs.commons.i18n`、`qs.commons.cards` | **绝对零副作用**：严禁 `import qs.app`、`import qs.services`、`import qs.plugins.*`、`Quickshell.Io`、`Process`、`FileView`、`Socket`、`Quickshell.env`、`XMLHttpRequest`、文件写操作或 DBus 发送 |
| *(已退役)* | `shell/modules/`、`shell/native/`、`shell/shared/`、`shell/units/` | `modules/` 已于 KM4.5 整体正名为 `units/`（后随 S0-1 改 `plugins/`）；`native/` 已于 R4-C-05 彻底物理删除；`shared/` 与 `units/` 已于 S0-1 五件套迁移消解为 `commons/`、`ui/` 与 `plugins/` | - | 全库严禁任何 `import qs.modules.*`、`import Clavis.*`、`qs.shared.*` 与 `qs.units.*` 导入 |

**支撑代码归宿（KM4.5 裁决，S0-1 路径对位）**：插件之外的复用代码不设额外的层——宿主能力面归 `services/`（`HotCorners.qml`、`FilePickerWindow.qml`、`IdleInhibitorSurface.qml` 同类）；单消费者组件并入唯一消费单元（`sidebars/quicksettings/`）；跨单元纯展示卡片归 `commons/cards/`（布局几何 JS、cookieclock 指针组、日历/存储/网络/可视化卡等）；凡直读 app 单例的 UI 渲染件归 `services/`（KM4.6：`SystemCardContent`、`SystemWeatherCard`、`SystemBatteryTank`、`SystemClockCard`、`SidebarCookieClock`——S0-1 随 app/cards 消解迁入，`NetworkInterfaceHistoryService` 在列）；插件自有 shader 归 `plugins/<domain>/shaders/`（frag 源 + qsb 产物同迁，`compile-shaders.sh` 全量重编 11 个 qsb，归 `scripts/dev/`）；`assets/`、`fallback/`、`packaging/` 已于 KM4.6 处决（M3Shapes 具名模块桩迁 `ui/shapes/M3Shapes/`，lottieqt 死桩删除，第三方许可证折入 `LICENSE` 第三方附录，独立发行管线退役）。

---

## 3. 单元（Units）详细矩阵与所有者

| 单元 | 目录 | 职责与内聚内容 | 外部依赖输入 | 对外意图输出 |
|---|---|---|---|---|
| **bar** | `plugins/bar/` | 桌面状态栏、托盘（内聚 `TrayService`）、工作区指示、时钟、状态条快捷设置 | `Quickshell.screens`、`Workspaces`、`ThemeService` | 触发面板展开、窗口切换 |
| **dock** | `plugins/dock/` | 应用停靠栏、常驻应用、活动窗口指示 | `DockService`、`ApplicationService` | 启动应用、激活/最小化窗口 |
| **keystone** | `plugins/keystone/` | 动态岛/多形态中枢、专属录制与辅助（内聚 `AudioRecordingService`、`RecordingService`、`MediaPalette`） | `MediaService`、`NotificationService`、`WidgetState`、`TimerService` | 媒体控制、快速操作、录制派发 |
| **launcher** | `plugins/launcher/` | Spotlight 聚焦启动器、专属检索与工具（内聚 `FileSearchService`、`SpotlightSearchService`、`SpotlightToolService`） | `ApplicationService`、`SearchCatalog`、`WallpaperService` | `ActionGateway.execute(args, "launcher")` |
| **settings** | `plugins/settings/` | 控制中心设置窗口与配置管理（内聚 `AutostartService`、`DisplayConfigService`、`ShellControlService`——控制面采样与脱敏诊断唯一 I/O 归属） | `PersonalizationConfig`、`NiriConfigService`、`WallpaperService`、`UiPreferences` | 更新用户配置、重启服务、按门控采样 Shell 自身占用 |
| **sidebars** | `plugins/sidebars/` | 侧边栏（Dashboard、QuickSettings 托板与开关配置、内聚 `TodoService`、`TimerService`、`InfoDrawerState`） | `WidgetState`、`SystemStatusService`、`DesktopPresentationService` | 切换视图、系统快捷开关 |
| **notifications** | `plugins/notifications/` | 通知弹窗宿主（PopupHost）、通知卡片视图 | `NotificationService` | 点击通知动作、关闭通知 |
| **lock** | `plugins/lock/` | 锁屏界面、PAM/认证交互 | `WlSessionLock`、`WallpaperService` | 解锁会话、密码校验 |
| **wallpaper** | `plugins/wallpaper/` | 壁纸背景渲染、视差场景与调色盘提取（内聚 `WallpaperService`、`WallpaperSceneService`、`WallpaperPaletteSession`） | `PersonalizationConfig`、`NiriConfigService`、`ThemeService` | 请求壁纸重绘、分析通知 |
| **desktopcards** | `plugins/desktopcards/` | 桌面卡片宿主、画布网格吸附、布局与手势拖放呈现（内聚 `DesktopPresentationService`、`SystemCardDragSession`、`SystemCardDragState`） | `SystemCardService`、`WallpaperSceneService` | 卡片持久化排布 |
| **session** | `plugins/session/` | 会话面板（注销/重启/关机意图，经 `ActionGateway` 会话通道） | `ActionGateway` | 注销/重启/关机会话动作派发 |
| **regionselector** | `plugins/regionselector/` | 截图/取色屏幕区域选择器 | `RegionSelectionService` | 选区坐标上抛并结束交互 |

---

## 4. 生命周期与副作用契约

1. **显式销毁（Explicit Teardown）**：
   - 任何持有 `Process`、`Timer(repeat: true)`、`Socket` 或网络请求的组件，必须提供 `Component.onDestruction` 钩子并在组件卸载时立即取消任务与停止监听。
2. **防陈旧回调（Anti-Stale Callback）**：
   - 涉及异步操作（如外部进程输出解析、网络获取）的 Backend，必须维护递增的 `generation` 计数器；异步回调触发时核对当前 generation，陈旧代次的回调必须丢弃。
3. **参数数组执行（Argv Execution）**：
   - 所有外部进程派发必须通过 `ActionGateway.execute(args, owner)`，使用严格的参数数组（`["cmd", "arg1", ...]`），禁止拼接 Shell 字符串，禁止未经 Gateway 直接调用 `execDetached`。
   - `execute` 的布尔返回值语义是「已受理派发」，不代表命令完成；需要向用户呈现结果的调用点自行反馈（notify-send 等）。
4. **共享层无菌（Shared Layer Hygiene）**：
   - `commons/` 与 `ui/` 仅接收外部传入的数据、几何尺寸与颜色 Tokens；任何共享控件不得自行发起文件读写或读取宿主环境变量。
5. **UI 层无直接 I/O（LIFE008，R10）**：
   - `plugins/` 视图与 `app/` 顶层装配禁止持有 `FileView`/`Process`；文件 I/O 与子进程归 `*Service/*Config/*Backend/*State/*Catalog` 域文件或显式 allowlist（lock 会话标记、PreLockCapture、MediaPalette）。
   - 用户触发的桌面副作用（如 Dock 强杀进程）由视图发起意图、Gateway/域服务派发并登记 owner（`"dock:force-quit"` 模式）。
6. **主题模式单一真值（R10 / P4 收口）**：
   - Shell 主题模式唯一业务入口为 `ThemeService.setThemeMode/toggleThemeMode`（同值短路防回环）；对外经 `theme` IPC target（`set dark|light`/`toggle`/`status`）暴露。
   - 深浅切换的系统级写入（gsettings、GTK INI、Kvantum、kitty 信号、glow 布局、Noctalia IPC）唯一归 `nyxuri/desktop/theme.py`（`nyxuri theme` CLI）：Shell 切内部模式后代调 `nyxuri theme`，CLI 缺失时内部照切并经 `UiPreferences.systemThemeLastError` 明示；Shell 自带的 `set-system-color-scheme.sh` 与部署侧 `theme-sync.sh` 已清算。
   - 系统色彩方案变化经 `UiPreferences.systemThemeModeObserved` 信号闭环回写 `PersonalizationConfig.themeMode` 并再生色板（同值 no-op 防回环，且传 `syncExternal=false` 杜绝反向写回引发的 flock 竞争）；`UiPreferences.themePoller` 引入冷启动对齐门控（`startupAligned`），首次轮询以 `PersonalizationConfig` 为准，防止宿主陈旧 gsettings 冲刷覆盖 `config.json`；60s 轮询仅为无 IPC 环境的兜底通道。
   - `nyxuri/desktop/theme.py` 中的 `_mode_from_system` 与 `_propagate` 严格依 `active_shell()` 决定查询与广播优先级；`gsettings` 仅在显式出现 `prefer-light` 时判定为 `"light"`，GNOME 默认值 `'default'` 回退到 `DEFAULT_MODE`（dark），杜绝误判为 light。
   - 生成产物位于 `<generated>/nyxuri/`：`colors.json`（50 token 内部热载契约）、`palette-modes.json`（dark+light 双 mode，镜像与渲染的输入）、`scheme-previews.json`（scheme 画廊缓存）。
   - **取色与渲染分层（P4）**：matugen 仅作取色位（`--json` 纯 stdout，一次输出全 mode）；模板渲染由 `services/TemplateService.qml` 经 `commons/TemplateExpr.js`（Noctalia 兼容表达式子集，块/过滤器/`palettes.*` 显式拒绝）完成，matugen 不再渲染任何应用模板。
   - **模板归属**：内置注册表 `shell/app/templates/config.toml`（kitty/btop/starship vendor 自 Noctalia 5.2.1 MIT + 共享池 `~/.config/nyxuri/templates/` 的 gtk/glow/palette.toml + Fcitx5 NyxMellow 皮肤三模板 `fcitx5_theme/panel/highlight`——随 `fcitx5-rime` 单元激活）；用户注册表机制不变。kitty include 管理脚本 `kitty-apply.sh` 双向剥离 `noctalia.conf` 与 `current-theme.conf` 并置于 `__custom__.conf` 之前，彻底解决双 Shell include 顺序覆盖导致的配色失效。每次生成双写 16 角色 palette JSON 到 `~/.config/noctalia/palettes/nyxuri.json`（受管生成物，原子写）供 Noctalia `source = custom` 对齐选用；双 Shell 默认各自独立取色，谁 active 谁写全部输出。
   - **派生契约**：terminal 22 token 与 16 角色映射单点实现在 `commons/ThemePalette.js`（HCT 数学 vendor 自 material-color-utilities，Apache-2.0）；golden master 契约测试见 `shell/tests/qml/tst_ThemeContract.qml`，分歧矩阵（Noctalia 对 `on_*_container` 的 tone 重锚定）钉在 `tests/shell/test_shell.py::TestP4ThemeEngineContract`。
7. **切换器清场契约（R10 现场修复）**：
   - 切换决策基于 `probe_running_shells()` 全量实例清单，而非首个匹配；"already active" 仅在 target 在场且对侧零实例时成立，否则先清残留并报告被清对象。
   - spawn 前后双清场：`stop_all_shell_instances` 按类全量清扫（SIGTERM → 有界等待 → SIGKILL → 补等观察），`stop_shell_process` 返回真实死亡状态。
   - readiness 探针必须指向真实存在的 IPC 子命令（noctalia 用 `theme-mode-get`）；"进程存活超时"不作为就绪证据，杜绝双 Shell 假成功。
   - 回滚前全场清扫，恢复后必须单 Shell；清场失败向上返回失败而非假装成功。
   - **双轨状态继承契约（State Handoff）**：关停旧 Shell 前由 `capture_active_theme_state` 捕获内存运行态的 `mode`（dark/light）与壁纸路径；目标 Shell 就绪（或回滚恢复旧 Shell）后由 `handoff_theme_state` 注入（Nyxuri Shell 走 `theme.set` / `wallpaper.set` IPC；Noctalia 走 `theme-mode-set` / `wallpaper-set`）并触发全系统同步（`theme.sync`），杜绝切换后深浅模式与壁纸丢失。

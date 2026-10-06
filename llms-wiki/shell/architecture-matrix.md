# Nyxuri Shell 三层纯净架构与边界矩阵

本文件是 Nyxuri Shell 的架构契约与分层依赖真值表。在 R4-C-05/06 全面去 C++ 收口后，原生 `native/` 层与 CMake 构建链已彻底注销与物理移除；架构确立为 `app/`、`modules/` 与 `shared/` 三层纯净模型，规范其职责、文件所有者、允许的导入规则（Import Whitelist）、输入输出契约与副作用边界。

---

## 1. 三层分工总则

```
┌─────────────────────────────────────────────────────────────┐
│                            app/                             │
│  顶层装配、系统协调、Niri 单一运行时 IPC (NiriService)、动作网关  │
└──────────────┬───────────────────────────────┬──────────────┘
               │ 依赖注入 / 动作派发            │
┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
│     modules/<domain_a>/     │ │     modules/<domain_b>/     │
│   功能域视图与专属 Backend   │ │   功能域视图与专属 Backend   │
└──────────────┬──────────────┘ └──────────────┬──────────────┘
               │                               │
               └───────────────┬───────────────┘
                               │ 仅依赖纯组件 / 代币
┌──────────────────────────────▼──────────────────────────────┐
│                           shared/                           │
│        原子控件 (controls/)、设计代币 (theme/)、纯算法 (utils/)   │
│             【零外部服务、零进程、零文件IO、零网络】              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 分层契约与 Import 白名单

| 层级 | 路径 | 核心职责 | 允许 Import | 严禁行为 / 副作用 |
|---|---|---|---|---|
| **app** | `shell/app/` | 顶层装配（`AppShell`）、环境/路径感知（`Paths`）、Niri 单一运行时 IPC（`NiriService`）、会话/启动管理（`services/`）、全局动作网关（`ActionGateway`） | Qt 原语、`Quickshell`、`qs.shared.*`、`qs.app.*`、按需装配的 `qs.modules.*` 顶层 Host | 禁止在展示组件中写死命令或业务逻辑；禁止绕过 `ActionGateway` 随意执行外部进程；非 `NiriService` 严禁直接建立 Niri IPC 连接 |
| **modules** | `shell/modules/<domain>/` | 独立桌面功能域（`bar/`, `dock/`, `keystone/`, `launcher/`, `settings/`, `sidebars/`, `notifications/`, `osd/`, `lock/`, `wallpaper/`, `systemcards/`, `desktopcards/`, `hotcorners/`, `regionselector/`） | Qt 原语、`Quickshell`、`qs.shared.*`、`qs.app.services`、同域相对路径 `./*` 或 `qs.modules.<domain>.*` | **严禁横向私自跨域导入**（如 `modules/launcher` 直接导入 `qs.modules.settings`）；跨域桌面意图必须路由至 `ActionGateway` |
| **shared** | `shell/shared/` | 纯净原子复用层：`controls/`（原子按钮/卡片/滑动条/指示器）、`theme/`（调色板与字体代币）、`utils/`（数学/时间/格式化/TOML 解析纯算法）、`i18n/`（纯 QML/JS 国际化单例与内存字典） | Qt 原语、`qs.shared.theme`、`qs.shared.controls`、`qs.shared.utils`、`qs.shared.i18n` | **绝对零副作用**：严禁 `import qs.app.*`、`import qs.modules.*`、`Quickshell.Io`、`Process`、`FileView`、`Socket`、`Quickshell.env`、`XMLHttpRequest`、文件写操作或 DBus 发送 |
| *(已退役)* | `shell/native/` | **已于 R4-C-05 彻底物理删除**。原 C++ 插件与 fallback 桩由 pure QML/JS/Script 替代 | - | 全库严禁任何 `import Clavis.*` 原生插件导入 |

---

## 3. 功能域（Modules）详细矩阵与所有者

| 功能域 | 目录 | 职责与内聚内容 | 外部依赖输入 | 对外意图输出 |
|---|---|---|---|---|
| **bar** | `modules/bar/` | 桌面状态栏、托盘（内聚 `TrayService`）、工作区指示、时钟 | `Quickshell.screens`、`Workspaces`、`ThemeService` | 触发面板展开、窗口切换 |
| **dock** | `modules/dock/` | 应用停靠栏、常驻应用、活动窗口指示 | `DockService`、`ApplicationService` | 启动应用、激活/最小化窗口 |
| **keystone** | `modules/keystone/` | 动态岛/多形态中枢、专属录制与辅助（内聚 `AudioRecordingService`、`RecordingService`、`MediaPalette`） | `MediaService`、`NotificationService`、`WidgetState`、`TimerService` | 媒体控制、快速操作、录制派发 |
| **launcher** | `modules/launcher/` | Spotlight 聚焦启动器、专属检索与工具（内聚 `FileSearchService`、`SpotlightSearchService`、`SpotlightToolService`） | `ApplicationService`、`SearchCatalog`、`WallpaperService` | `ActionGateway.execute(args, "launcher")` |
| **settings** | `modules/settings/` | 控制中心设置窗口与配置管理（内聚 `AutostartService`、`DisplayConfigService`、`ShellControlService`——控制面采样与脱敏诊断唯一 I/O 归属） | `PersonalizationConfig`、`NiriConfigService`、`WallpaperService`、`UiPreferences` | 更新用户配置、重启服务、按门控采样 Shell 自身占用 |
| **quicksettings** | `modules/quicksettings/` | 快捷设置托板与开关配置（内聚 `QuickToggleConfig`） | `NetworkService`、`BluetoothService` | 快速开关网络/蓝牙/显示状态 |
| **sidebars** | `modules/sidebars/` | 侧边栏（Dashboard、QuickSettings、内聚 `TodoService`、`TimerService`、`InfoDrawerState`） | `WidgetState`、`SystemStatusService`、`DesktopPresentationService` | 切换视图、系统快捷开关 |
| **notifications** | `modules/notifications/` | 通知弹窗宿主（PopupHost）、通知卡片视图 | `NotificationService` | 点击通知动作、关闭通知 |
| **lock** | `modules/lock/` | 锁屏界面、PAM/认证交互 | `WlSessionLock`、`WallpaperService` | 解锁会话、密码校验 |
| **wallpaper** | `modules/wallpaper/` | 壁纸背景渲染、视差场景与调色盘提取（内聚 `WallpaperService`、`WallpaperSceneService`、`WallpaperPaletteSession`） | `PersonalizationConfig`、`NiriConfigService`、`ThemeService` | 请求壁纸重绘、分析通知 |
| **systemcards** | `modules/systemcards/` | 系统监控卡片（CPU, RAM, 存储, 网络与流量历史 `NetworkInterfaceHistoryService`） | `SystemMonitorService`、`Appearance` | 卡片拖放、切换监控视图 |
| **desktopcards** | `modules/desktopcards/` | 桌面卡片宿主、画布网格吸附、布局与手势拖放呈现（内聚 `DesktopPresentationService`、`SystemCardDragSession`、`SystemCardDragState`） | `SystemCardService`、`WallpaperSceneService` | 卡片持久化排布 |
| **hotcorners** | `modules/hotcorners/` | 屏幕热区感知与触发 | `Quickshell.screens`、`NiriConfigService` | 触发 Overview 或自定义动作 |
| **regionselector** | `modules/regionselector/` | 截图/取色屏幕区域选择器 | `RegionSelectionService` | 选区坐标上抛并结束交互 |
| **osd** | `modules/osd/` | 音量/亮度屏幕即时显示浮层 | `BrightnessService`、`VolumeService` | 浮层展示与定时淡出 |

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
   - `shared/` 仅接收外部传入的数据、几何尺寸与颜色 Tokens；任何共享控件不得自行发起文件读写或读取宿主环境变量。
5. **UI 层无直接 I/O（LIFE008，R10）**：
   - `modules/` 视图与 `app/` 顶层装配禁止持有 `FileView`/`Process`；文件 I/O 与子进程归 `*Service/*Config/*Backend/*State/*Catalog` 域文件或显式 allowlist（lock 会话标记、PreLockCapture、MediaPalette）。
   - 用户触发的桌面副作用（如 Dock 强杀进程）由视图发起意图、Gateway/域服务派发并登记 owner（`"dock:force-quit"` 模式）。
6. **主题模式单一真值（R10 / P4 收口）**：
   - Shell 主题模式唯一业务入口为 `ThemeService.setThemeMode/toggleThemeMode`（同值短路防回环）；对外经 `theme` IPC target（`set dark|light`/`toggle`/`status`）暴露。
   - 深浅切换的系统级写入（gsettings、GTK INI、Kvantum、kitty 信号、glow 布局、Noctalia IPC）唯一归 `nyxuri/theme.py` CLI：Shell 切内部模式后代调 `nyxuri theme`，CLI 缺失时内部照切并经 `UiPreferences.systemThemeLastError` 明示；Shell 自带的 `set-system-color-scheme.sh` 与部署侧 `theme-sync.sh` 已清算。
   - 系统色彩方案变化经 `UiPreferences.systemThemeModeObserved` 信号闭环回写 `PersonalizationConfig.themeMode` 并再生色板（同值 no-op 防回环）；60s 轮询仅为无 IPC 环境的兜底通道。
   - 生成产物位于 `<generated>/nyxuri/`：`colors.json`（50 token 内部热载契约，读取侧保留旧 `clavis/` 一次性回退）、`palette-modes.json`（dark+light 双 mode，镜像与渲染的输入）、`scheme-previews.json`（scheme 画廊缓存）。
   - **取色与渲染分层（P4）**：matugen 仅作取色位（`--json` 纯 stdout，一次输出全 mode）；模板渲染由 `app/services/TemplateService.qml` 经 `shared/utils/TemplateExpr.js`（Noctalia 兼容表达式子集，块/过滤器/`palettes.*` 显式拒绝）完成，matugen 不再渲染任何应用模板。
   - **模板归属**：内置注册表 `shell/assets/templates/config.toml`（kitty/btop/starship vendor 自 Noctalia 5.2.1 MIT + 共享池 `~/.config/noctalia/templates/` 的 gtk/glow/palette.toml）；用户注册表机制不变。每次生成双写 16 角色 palette JSON 到 `~/.config/noctalia/palettes/nyxuri.json`（受管生成物，原子写）供 Noctalia `source = custom` 对齐选用；双 Shell 默认各自独立取色，谁 active 谁写全部输出。
   - **派生契约**：terminal 22 token 与 16 角色映射单点实现在 `shared/utils/ThemePalette.js`（HCT 数学 vendor 自 material-color-utilities，Apache-2.0）；golden master 契约测试见 `shell/tests/qml/tst_ThemeContract.qml`，分歧矩阵（Noctalia 对 `on_*_container` 的 tone 重锚定）钉在 `tests/test_shell.py::TestP4ThemeEngineContract`。
7. **切换器清场契约（R10 现场修复）**：
   - 切换决策基于 `probe_running_shells()` 全量实例清单，而非首个匹配；"already active" 仅在 target 在场且对侧零实例时成立，否则先清残留并报告被清对象。
   - spawn 前后双清场：`stop_all_shell_instances` 按类全量清扫（SIGTERM → 有界等待 → SIGKILL → 补等观察），`stop_shell_process` 返回真实死亡状态。
   - readiness 探针必须指向真实存在的 IPC 子命令（noctalia 用 `theme-mode-get`）；"进程存活超时"不作为就绪证据，杜绝双 Shell 假成功。
   - 回滚前全场清扫，恢复后必须单 Shell；清场失败向上返回失败而非假装成功。

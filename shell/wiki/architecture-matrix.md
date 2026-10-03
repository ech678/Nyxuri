# Nyxuri Shell 四层架构与边界矩阵

本文件是 Nyxuri Shell 的架构契约与分层依赖真值表。它规定 `app/`、`modules/`、`shared/` 与 `native/` 四层的职责、文件所有者、允许的导入规则（Import Whitelist）、输入输出契约与副作用边界。

---

## 1. 四层分工总则

```
┌─────────────────────────────────────────────────────────────┐
│                            app/                             │
│       顶层装配、系统协调、IPC 桥、ActionGateway 动作网关       │
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
                               ▲
                               │ 抽象隔离
┌──────────────────────────────┴──────────────────────────────┐
│                           native/                           │
│        原生桥 (C++ 插件与降级桩，对接后续 R4-C 纯化主线)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 分层契约与 Import 白名单

| 层级 | 路径 | 核心职责 | 允许 Import | 严禁行为 / 副作用 |
|---|---|---|---|---|
| **app** | `shell/app/` | 顶层装配（`AppShell`）、环境/路径感知（`Paths`）、全局 IPC 处理、会话/启动管理（`services/`）、全局动作网关（`ActionGateway`） | Qt 原语、`Quickshell`、`qs.shared.*`、`qs.app.*`、按需装配的 `qs.modules.*` 顶层 Host | 禁止在展示组件中写死命令或业务逻辑；禁止绕过 `ActionGateway` 随意执行外部进程 |
| **modules** | `shell/modules/<domain>/` | 独立桌面功能域（`bar/`, `dock/`, `keystone/`, `launcher/`, `settings/`, `sidebars/`, `notifications/`, `osd/`, `lock/`, `wallpaper/`, `systemcards/`, `desktopcards/`, `hotcorners/`, `regionselector/`） | Qt 原语、`Quickshell`、`qs.shared.*`、`qs.app.services`、同域相对路径 `./*` 或 `qs.modules.<domain>.*` | **严禁横向私自跨域导入**（如 `modules/launcher` 直接导入 `qs.modules.settings`）；跨域桌面意图必须路由至 `ActionGateway` |
| **shared** | `shell/shared/` | 纯净原子复用层：`controls/`（原子按钮/卡片/滑动条/指示器）、`theme/`（调色板与字体代币）、`utils/`（数学/时间/格式化纯算法） | Qt 原语、`qs.shared.theme`、`qs.shared.controls`、`qs.shared.utils` | **绝对零副作用**：严禁 `import qs.app.*`、`import qs.modules.*`、`Quickshell.Io`、`Process`、`FileView`、`Socket`、`Quickshell.env`、`XMLHttpRequest`、文件写操作或 DBus 发送 |
| **native** | `shell/native/` | 原生 C++ 插件与对应降级桩（对接后续 R4-C 全面去 C++ 主线） | 仅供 QML 层窄接口调用 | 严禁与 QML 核心逻辑反向强耦合；缺失时必须具备安全空桩降级能力 |

---

## 3. 功能域（Modules）详细矩阵与所有者

| 功能域 | 目录 | 职责与内聚内容 | 外部依赖输入 | 对外意图输出 |
|---|---|---|---|---|
| **bar** | `modules/bar/` | 桌面状态栏、托盘（内聚 `TrayService`）、工作区指示、时钟 | `Quickshell.screens`、`Workspaces`、`ThemeService` | 触发面板展开、窗口切换 |
| **dock** | `modules/dock/` | 应用停靠栏、常驻应用、活动窗口指示 | `DockService`、`ApplicationService` | 启动应用、激活/最小化窗口 |
| **keystone** | `modules/keystone/` | 动态岛/多形态中枢、专属录制与辅助（内聚 `AudioRecordingService`、`RecordingService`、`MediaPalette`） | `MediaService`、`NotificationService`、`WidgetState`、`TimerService` | 媒体控制、快速操作、录制派发 |
| **launcher** | `modules/launcher/` | Spotlight 聚焦启动器、专属检索与工具（内聚 `FileSearchService`、`SpotlightSearchService`、`SpotlightToolService`） | `ApplicationService`、`SearchCatalog`、`WallpaperService` | `ActionGateway.execute(args, "launcher")` |
| **settings** | `modules/settings/` | 控制中心设置窗口与配置管理（内聚 `AutostartService`、`DisplayConfigService`） | `PersonalizationConfig`、`NiriConfigService`、`WallpaperService` | 更新用户配置、重启服务 |
| **quicksettings** | `modules/quicksettings/` | 快捷设置托板与开关配置（内聚 `QuickToggleConfig`） | `NetworkService`、`BluetoothService` | 快速开关网络/蓝牙/显示状态 |
| **sidebars** | `modules/sidebars/` | 侧边栏（Dashboard、QuickSettings、内聚 `TodoService`、`TimerService`、`InfoDrawerState`） | `WidgetState`、`SystemStatusService`、`DesktopPresentationService` | 切换视图、系统快捷开关 |
| **notifications** | `modules/notifications/` | 通知弹窗宿主（PopupHost）、通知卡片视图 | `NotificationService` | 点击通知动作、关闭通知 |
| **lock** | `modules/lock/` | 锁屏界面、PAM/认证交互 | `WlSessionLock`、`WallpaperService` | 解锁会话、密码校验 |
| **wallpaper** | `modules/wallpaper/` | 壁纸背景渲染、视差场景、调色盘提取与 awww 后端（内聚 `WallpaperService`、`WallpaperSceneService`、`WallpaperPaletteSession`、`AwwwWallpaperService`） | `PersonalizationConfig`、`NiriConfigService`、`ThemeService` | 请求壁纸重绘、分析通知 |
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
4. **共享层无菌（Shared Layer Hygiene）**：
   - `shared/` 仅接收外部传入的数据、几何尺寸与颜色 Tokens；任何共享控件不得自行发起文件读写或读取宿主环境变量。

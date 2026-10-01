# Nyxuri Shell — 母体基准与审计

## 基准与适用范围

- 上游：[StatIndet/quickshell](https://github.com/StatIndet/quickshell)，默认分支 `main`。
- 固定 commit：`91cdecbe08831acdcff44d350e09232efe7164ed`；提交时间 `2026-09-30T22:21:35+08:00`；获取日期 `2026-10-01`。
- 导入方式：完整 clone 到临时目录，再用该 commit 的 `git archive` 平铺到 `shell/`。901 个 Git 跟踪文件原样保留，包括隐藏文件、测试、GPL-3.0 主许可证及第三方归属；不包含 `.git`、构建产物和上游未跟踪文件。
- 母体导入时唯一修正：`.gitignore` 的 `build/` 改为 `/build/`。上游已跟踪的 `scripts/build/compile-launcher-shaders.sh` 在新宿主中否则会被忽略；收窄规则后 901 个文件均可正常纳入 Git。导入前已逐文件验证内容和可执行权限，修正后源码仍与基准一致。
- 导入树约 11.86 MB，507 个 QML 文件；Google Sans Flex 字体本体 3,997,148 字节。本轮不删字体、不改上游源码、不运行上游安装器、不接入部署。
- 需求依据：[issue #111](https://github.com/ech678/Nyxuri/issues/111)。后续工作见 [实施蓝图](shell-blueprint.md)。

同步上游必须显式选择 commit、先比较净差异，再在现有母体上合并；不自动跟随 main，不用一次全量覆盖抹掉 Nyxuri 修改。此记录是上游基准，不是 Nyxuri 发布版本。未来编译应显式传入基准 commit，避免 CMake 在无嵌套 `.git` 时误把宿主 HEAD 当成 Clavis commit。

`shell/AGENTS.md`保留上游开发约定，仅适用于该源码树。源码软链进用户配置的上游开发方式与宿主物理隔离契约冲突，Nyxuri 必须采用原子复制。上游单独 clone 的测试假设、Git 文件选择器和根目录 GitHub workflows 不会因平铺自动适配宿主；不能假定原有检查入口已正确覆盖导入树。

## 结论与证据等级

本页的“确认”来自固定 commit 源码；“实测”仅限下面的隔离探测。静态扫描列出候选接口，不能证明文件启动可达、进程实际常驻或网络实际发出。没有真实 Wayland 视觉、冷启动性能、RSS 或退出残留测量，不能宣称秒启、零报错或泄漏成立。

### 启动闭包

[shell.qml](../shell/shell.qml) 的 `ShellRoot` 直接创建 [AppShell.qml](../shell/AppShell.qml)。AppShell 静态导入 `Clavis.Niri` 和多个功能目录，直接实例化 DisplayOverlays、WallpaperBackground、DesktopCardHost、Bar、DockHost、Keystone、RegionSelector、SidebarHostWindow、HotCorners、Lock、PowerMenu、LauncherWindow。这里是**对象装配事实**，并不意味着每个对象的所有内部窗口和后台都已活跃。

AppShell 的完成钩子初始化 I18n、DisplayColor、LyricsTrackService、SystemIdentityService；歌词初始化明确接通 MPRIS 曲目和 native Lyrics，不能仅隐藏歌词画面来封存它。`DisplayColor.evaluate()` 又把 Gamma 能力拉入启动路径。[DisplayColor.qml](../shell/Services/DisplayColor.qml) 还引用天气位置。

控制中心是反例：[ControlCenterService.qml](../shell/Services/ControlCenterService.qml) 打开时激活 LazyLoader；[ControlCenterWindow.qml](../shell/Modules/ControlCenter/ControlCenterWindow.qml) 第 150 行附近的 `onVisibleChanged` 发出 `popoutClosed`，AppShell 转给 `windowClosed()`，最终将 Loader 设为 inactive。不能只读 `close()` 中的 `visible=false` 就判定虚假关闭。是否存在关闭后引用或进程残留仍需运行验证。

[LauncherWindow.qml](../shell/Modules/Launcher/LauncherWindow.qml) 本体由 AppShell 直接创建，导入 `Clavis.Keyboard`；多个 provider 已按 showing、mode 和 closing 状态启停。后续应把整个临时面板放进可销毁的宿主，同时保留 provider 的按需规则。[PowerMenu.qml](../shell/Modules/PowerMenu/PowerMenu.qml) 每屏 Loader 的 active 恒为 true，窗口再按服务状态控制 visible，适合改成真正按需实例化。

### 依赖与降级缺口

**原版 Niri 约束**：Nyxuri 使用官方原版 Niri。`Clavis.Niri` 是上游自定义桥，其标准 IPC 能力与依赖魔改合成器的高级扩展须分别审计；不将整个插件视为原版能力，也不认定所有桥内功能都必须删除。动画目标、最小化、浮动移动/视差需分别调查，不能按名称认定全部依赖魔改；只有已证实不兼容的扩展才隔离。基础工作区/窗口/输出接口以标准协议实测为准。导入时缺插件的启动失败仍是当前事实，不能据此推断必须安装魔改 Niri。

依赖真值为 [packaging/dependencies.json](../shell/packaging/dependencies.json) 和构建声明，而不是 issue 中的概括。当前上游完整安装面很大，不能直接搬入 Nyxuri CORE_DEPS。

| 能力 | 当前证据 | 重构要求 |
| --- | --- | --- |
| Niri 原生桥 | AppShell、工作区、活动窗口、亮度等静态导入 `Clavis.Niri` | 从入口移除硬导入；按能力加载原有桥，缺失时隐藏相应数据部件，保留核心栏与启动器 |
| Cava / 音频分析 | `core/CMakeLists.txt` 必需 PipeWire、`libcava` 或 `cava` pkg-config；`AudioSpectrum.qml` 静态导入 `Clavis.Cava` | 关闭构建目标并隔离 QML 导入；安装 cava 命令本身不能满足开发库依赖 |
| 天气 / 地图 | Weather、WeatherMap 原生目标无条件加入；完整依赖含 QtLocation、MapLibre、QtKeychain | 本期封存，禁止触达 provider；不启动请求、缓存维护或定位 |
| 歌词 | AppShell 主动 initialize，`LyricsTrackService.qml` 静态导入 `Clavis.Lyrics` | 从启动装配撤出，并取消曲目监听与 native 网络对象 |
| M3Shapes | 多个 UI 静态 import，包括 Lock AuthCard | 外部运行时 QML 模块；核心消费路径需用原有几何资产提供降级，不能写空白 AuthCard 冒充锁屏 |
| Runtime / I18n / Keyboard / Files / Media / Gamma / WindowPreview / DesktopCards | 各自为独立原生 QML URI；详见后附导入位置 | 分别隔离加载和构建；按真实消费者启用，不能把整个 core 当作最小依赖 |
| key-cli | `Paths.stableKey` 默认 `key`；user unit 运行 `key shell`；键盘状态、sysmon、剪贴板等消费 JSON/JSONL | 作为可选外部能力，不做核心冷启动依赖；本期不重写 sysmon parser，也不复制 key-cli |
| Quickshell / Qt | 上游文档基准 QS 0.3.1、Qt 6.8+，需要相应 Wayland/PAM/PipeWire 等编译能力 | 精简配置必须实测后才能宣布最小依赖集合；不能由完整安装清单反推 |

QML 的静态 import 解析先于 `active:false` 的对象控制。把带缺失模块 import 的组件留在入口内联 Loader 中，不能作为已证明的降级方案；应拆成独立 source URL，异步加载真实组件并处理 Loader.Error，验证缺失插件时核心仍亮屏。

### 生命周期与副作用归属

| 域 | 已确认行为 / 风险 | 目标所有者与处理 |
| --- | --- | --- |
| 时间 | `Services/Time.qml:32` 的 Timer 每 30 秒运行，SystemClock 按分钟更新 | bar 的时钟服务；没有消费者时销毁，不做全局常驻工具 |
| 键盘状态 | `KeyboardLockService.qml:78` 完成时启动 `key keyboard watch`，断开后最多重连 3 次 | lock / OSD 的显式租约；无消费者不启动，退出不重连 |
| 频谱 | `AudioSpectrum.qml` 已有 acquire/release，CavaProvider.active 取决于消费者数 | 封存；保留所有权思路，消除静态导入硬依赖 |
| 系统监控 | `SystemMonitorService.qml:662` 起有 watchdog、重连和 2 秒强制终止，消费 key sysmon | 封存；不归入首期基础栏，未来迁移保留真实协议和有界终止 |
| 通知 | `NotificationManager.qml:97` 建存储目录；通知到期 Timer 会 destroy；历史和 FileActionService 有耦合 | notifications 常驻接收服务，弹窗/历史面板短生命周期，历史有界保存；不能随面板收起丢掉 D-Bus 接收 |
| 锁屏 | `Lock.qml` 的 WlSessionLock/PamContext，截图前置、监控消费者与 WindowPreviewService 绑定 | lock 模块；保留安全状态机，截图和装饰可降级，不能因停用/切换销毁正在保护会话的锁 |
| 空闲策略 | `IdleService.qml` 文件写入、显示电源/休眠进程，析构时恢复显示与亮度 | lock 的会话策略服务；禁用后释放监视与恢复临时改变，副作用经动作执行边界 |
| 音量 / 亮度 / 托盘 | Quickshell 能力及 Brightness 原生/外部命令、Tray 文件接口 | 各域服务由 bar / panel 明确获取；设备缺失局部 unavailable，不阻断栏 |
| 壁纸 / Dock / 桌面卡片 / 侧栏 | AppShell 全量装配；各自含外部命令、预览与设置引用 | 本期封存，不能仅隐藏父 Item；保留源码与资源，但核心不引用其根组件 |
| 天气网络 | `core/src/openmeteo_client.cpp` 包含 ipwho.is、Open-Meteo、Nominatim 请求与超时 abort | 封存 weather 的网络与缓存对象；源码含 URL 不等于冷启动已发请求 |
| 歌词网络 | `core/plugin/lyrics/src/lyrics.cpp` 包含 LRCLIB/网易请求、取消与 deleteLater | 封存 lyrics；取消在途请求和轨道监听，不把已有取消机制重写为猜测桩 |
| 文件 / 主题 / 偏好 | `Common/Appearance.qml:298` FileView；多个 Services 写配置，脚本涉及 gsettings / matugen / Niri 文件 | app 持有存储与动作执行边界；shared 只接收色板、尺寸、字体和模型 |

扫描 Widgets/Components 未发现本次模式中的 Process 或 execDetached，但仍广泛引用全局 Services/Common。不存在这两种文本并不能证明展示层纯净。Common 已有文件读取，Paths 持有宿主环境，故不可整体搬进 shared。

“释放模块”指 QObject 树、窗口、定时器、连接、请求、子进程与引用清理。Qt、字体和分配器缓存不保证 RSS 立即回到原值；必须验证多轮稳态不持续增长，不能承诺销毁后每个字节立刻归还系统。

### 资产、许可证与视觉

[Fonts.qml](../shell/Common/Fonts.qml) 不只是设置默认 family：它加载内嵌 Google Sans Flex，并让 expressive 和 systemClock 使用该字体；删除字体必须同时改消费者与回退规则。ui 已有系统字体可用性判断，mono/numeric 有 monospace fallback。

MaterialSymbol 用系统 Material Symbols 字体，文件不是内嵌资产；直接退回普通字体会显示图标名称。必须声明系统图标字体能力，或为首期图标提供 SVG fallback。优先复用原有 ThemeIcon/SvgIcon，不凭空重做图标系统。删除字体不意味着删除对应历史许可记录。

保留 Keystone/Launcher/Wallpaper 的 GLSL 与 QSB、几何和动画源码；重型功能封存不等于删掉其视觉资产。`assets/icons/weather/meteocons/` 在 Git 树仅有占位，发布源码准备才下载校验资源；完整 Git 母体与完整发布包不是同一概念，本轮不下载额外资源。

主许可证见 `shell/LICENSE`，混合来源见 `shell/licenses/README.md` 及各 notice；keyboard、rclone、搜索图标有独立说明。后续删除/替换按资产引用和原始许可逐项处理，不能把所有文件重新标记成 Nyxuri 自有。

### 原版 Niri 调查线索（未完成兼容验收）

`core/plugin/niri/CMakeLists.txt` 将标准桥、动画目标与浮动视差编入同一 URI。`niri_animation_targets.cpp:88` 发送 SetWindowAnimationTargets；`niri_plugin.cpp` 有 MinimizeWindow/RestoreWindow 和能力探测；`niri_floating_parallax.cpp` 通过 MoveFloatingWindow 组合效果。这些是请求/实现存在的事实，尚未逐项对照固定原版协议或实机验收，不能直接称全都专有，也不能报告全部标准兼容。拆分任务见 ROADMAP P0-04。

### 宿主接入

- `nyxuri/cli.py:_cmd_shell` 的 set 仅写账本；status 的 Ready 仅表示路径存在且可执行，不是运行健康。没有热切换或 readiness 握手。
- `configs/niri/scripts/session-shell.sh` 对 custom 成功执行 `exec` 后，不再捕获异常退出；现有回退仅覆盖缺失可执行文件。入口只停止特定 Noctalia scope，不是任意 Shell 的完整清理协议。
- `shell-action.sh` 已提供 8 个稳定动作，但根据持久账本分发，不是当前实际存活实例。custom 启动失败时可能仍路由到失败端。
- 上游 unit 使用 `key shell`，与宿主路由不能同时充当会话所有者；平铺后 root workflows 也不会自动在 Nyxuri 根目录生效。
- `shell/` 不在当前 `configs/` 自动发现域；本轮不会被部署。未来应通过明确可选流程，以 `atomic_replace_item` 原子复制，接入快照/回滚/卸载，不做软链或伪装为默认 config。
- 主题流水线仍与 Noctalia 相连。首期保留 Noctalia 生成的已存在色板作为只读输入，并提供静态 fallback；不因停用 Noctalia 临时引入第二个主题守护进程。

## 验证记录

- Nyxuri 导入前基线：475 tests，OK，6 skipped。
- 本机 QS：0.3.1。隔离 HOME/XDG、禁用真实 session bus、offscreen、10 秒上限运行原版入口，退出 255，首次 QML 失败为 `AppShell.qml:4 module "Clavis.Niri" is not installed`；另有 IPC socket 建立失败，可能受执行沙箱限制，未把它判成源码缺陷。日志 `/tmp/nyxuri-shell-startup.log`。
- CMake configure 到 `/tmp/nyxuri-shell-native-check`，在 `core/CMakeLists.txt:63` 被缺失的 `cava` pkg-config 阻断；已先尝试 libcava。未编译 native、未运行 CTest、未安装依赖。单独 pkg-config 查询 Qt6Keychain 名称失败不等于 CMake Qt6Keychain 缺失，实际 configure 已通过该发现阶段。
- 上游 `scripts/dev/check.sh` 停在 qml-format：原有 QML 与本机格式工具输出不一致，日志 `/tmp/clavis-check.a1bYq4/qml-format.log`。没有重排母体，没有运行后续 lint/CTest，不能把格式检查失败称为运行错误或零警告通过。
- 导入后宿主单测仍为 475 tests，OK，6 skipped；compileall、宿主 bash 语法、install.sh ShellCheck 与临时 HOME 沙箱部署均通过。导入 Python 全树内存编译通过，文档本地链接已检查。上游全量运行测试因原生依赖阻断未完成。
- offscreen 不提供真实 Wayland 安全锁、输出热插拔或视觉验收；本轮不启动真实桌面，也不把探测失败改写成架构已完成。

## 全树资源接口索引

以下扫描覆盖 QML/JS/C++/头文件中的 Process/QProcess、execDetached、Timer/QTimer/SystemClock、FileView/QFile/QDir、网络类型、原生 import 与析构钩子，共 210 个文件。行号固定于本页基准 commit。声明、include 和实现均可能命中；这是审查入口，不是实例数量或泄漏统计。脚本和 D-Bus/Wayland/socket 等其他接口仍需在对应模块实施时追踪；本轮没有对每个后台的动态存活给出证明。

| 文件 | 接口及行号 |
| --- | --- |
| [AppShell.qml](../shell/AppShell.qml) | 脱离进程：73, 166, 172, 178；原生导入：4 |
| [Common/Appearance.qml](../shell/Common/Appearance.qml) | 文件接口：298 |
| [Modules/Bar/ActiveWindow/ActiveWindow.qml](../shell/Modules/Bar/ActiveWindow/ActiveWindow.qml) | 原生导入：3 |
| [Modules/Bar/SysMonitor/SysMonitor.qml](../shell/Modules/Bar/SysMonitor/SysMonitor.qml) | 销毁钩子：76 |
| [Modules/Bar/Workspaces/Workspaces.qml](../shell/Modules/Bar/Workspaces/Workspaces.qml) | 原生导入：4 |
| [Modules/ControlCenter/AccountPage.qml](../shell/Modules/ControlCenter/AccountPage.qml) | 销毁钩子：24 |
| [Modules/ControlCenter/AddNetworkPage.qml](../shell/Modules/ControlCenter/AddNetworkPage.qml) | 销毁钩子：45 |
| [Modules/ControlCenter/AdvancedPage.qml](../shell/Modules/ControlCenter/AdvancedPage.qml) | 计时器：108 |
| [Modules/ControlCenter/BezierCurveEditor.qml](../shell/Modules/ControlCenter/BezierCurveEditor.qml) | 脱离进程：266 |
| [Modules/ControlCenter/BezierCurveLayerEditor.qml](../shell/Modules/ControlCenter/BezierCurveLayerEditor.qml) | 脱离进程：193 |
| [Modules/ControlCenter/BluetoothPairingPage.qml](../shell/Modules/ControlCenter/BluetoothPairingPage.qml) | 销毁钩子：44 |
| [Modules/ControlCenter/CloudRemoteManagerWindow.qml](../shell/Modules/ControlCenter/CloudRemoteManagerWindow.qml) | 计时器：79 |
| [Modules/ControlCenter/ComputerBackupWindow.qml](../shell/Modules/ControlCenter/ComputerBackupWindow.qml) | 计时器：284 |
| [Modules/ControlCenter/ControlCenterWindow.qml](../shell/Modules/ControlCenter/ControlCenterWindow.qml) | 计时器：166 |
| [Modules/ControlCenter/DisplaysPage.qml](../shell/Modules/ControlCenter/DisplaysPage.qml) | 销毁钩子：50 |
| [Modules/ControlCenter/GeneralSidebarPage.qml](../shell/Modules/ControlCenter/GeneralSidebarPage.qml) | 销毁钩子：107 |
| [Modules/ControlCenter/LanguageAndRegionPage.qml](../shell/Modules/ControlCenter/LanguageAndRegionPage.qml) | 原生导入：3 |
| [Modules/ControlCenter/MapTilerApiSettingsCard.qml](../shell/Modules/ControlCenter/MapTilerApiSettingsCard.qml) | 原生导入：2 |
| [Modules/ControlCenter/NetworkPage.qml](../shell/Modules/ControlCenter/NetworkPage.qml) | 计时器：179；销毁钩子：147 |
| [Modules/ControlCenter/OpenWeatherApiSettingsCard.qml](../shell/Modules/ControlCenter/OpenWeatherApiSettingsCard.qml) | 原生导入：2 |
| [Modules/ControlCenter/ShortcutsPage.qml](../shell/Modules/ControlCenter/ShortcutsPage.qml) | 原生导入：8；销毁钩子：358 |
| [Modules/ControlCenter/SplitMenuButton.qml](../shell/Modules/ControlCenter/SplitMenuButton.qml) | 销毁钩子：116 |
| [Modules/ControlCenter/WallpaperColorPicker.qml](../shell/Modules/ControlCenter/WallpaperColorPicker.qml) | 销毁钩子：30 |
| [Modules/DesktopCards/DesktopCardHost.qml](../shell/Modules/DesktopCards/DesktopCardHost.qml) | 原生导入：4；销毁钩子：260 |
| [Modules/Dock/DockFileArtwork.qml](../shell/Modules/Dock/DockFileArtwork.qml) | 原生导入：2 |
| [Modules/Dock/DockFileDrag.qml](../shell/Modules/Dock/DockFileDrag.qml) | 销毁钩子：63 |
| [Modules/Dock/DockFileIcon.qml](../shell/Modules/Dock/DockFileIcon.qml) | 原生导入：2 |
| [Modules/Dock/DockFilePopup.qml](../shell/Modules/Dock/DockFilePopup.qml) | 原生导入：4 |
| [Modules/Dock/DockFolderFan.qml](../shell/Modules/Dock/DockFolderFan.qml) | 原生导入：3 |
| [Modules/Dock/DockFolderModel.qml](../shell/Modules/Dock/DockFolderModel.qml) | 原生导入：3 |
| [Modules/Dock/DockPreviewPopup.qml](../shell/Modules/Dock/DockPreviewPopup.qml) | 原生导入：6；销毁钩子：62 |
| [Modules/Dock/DockSurface.qml](../shell/Modules/Dock/DockSurface.qml) | 计时器：624, 632, 642, 650, 659；原生导入：5, 6 |
| [Modules/Dock/DockWindowCard.qml](../shell/Modules/Dock/DockWindowCard.qml) | 原生导入：4 |
| [Modules/FilePicker/FilePickerWindow.qml](../shell/Modules/FilePicker/FilePickerWindow.qml) | 计时器：870 |
| [Modules/HotCorners/HotCorners.qml](../shell/Modules/HotCorners/HotCorners.qml) | 原生导入：4 |
| [Modules/Keystone/ClockContent/ClockContent.qml](../shell/Modules/Keystone/ClockContent/ClockContent.qml) | 计时器：103 |
| [Modules/Keystone/CloudUploadContent/CloudUploadContent.qml](../shell/Modules/Keystone/CloudUploadContent/CloudUploadContent.qml) | 计时器：182 |
| [Modules/Keystone/DashboardContent/DashboardClock.qml](../shell/Modules/Keystone/DashboardContent/DashboardClock.qml) | 计时器：31 |
| [Modules/Keystone/DashboardContent/DashboardWeatherCard.qml](../shell/Modules/Keystone/DashboardContent/DashboardWeatherCard.qml) | 计时器：100 |
| [Modules/Keystone/DashboardContent/UserCard.qml](../shell/Modules/Keystone/DashboardContent/UserCard.qml) | 原生导入：3 |
| [Modules/Keystone/LyricsContent/LyricsContent.qml](../shell/Modules/Keystone/LyricsContent/LyricsContent.qml) | 原生导入：2 |
| [Modules/Keystone/LyricsContent/LyricsSpectrum.qml](../shell/Modules/Keystone/LyricsContent/LyricsSpectrum.qml) | 销毁钩子：26 |
| [Modules/Keystone/MediaContent/CaelestiaCover.qml](../shell/Modules/Keystone/MediaContent/CaelestiaCover.qml) | 原生导入：9；销毁钩子：49 |
| [Modules/Keystone/Styles/Long/LongStatusItem.qml](../shell/Modules/Keystone/Styles/Long/LongStatusItem.qml) | 销毁钩子：213 |
| [Modules/Keystone/Styles/Long/LongWorkspaces.qml](../shell/Modules/Keystone/Styles/Long/LongWorkspaces.qml) | 原生导入：4 |
| [Modules/Keystone/Styles/Recording/AudioRecordingVisual.qml](../shell/Modules/Keystone/Styles/Recording/AudioRecordingVisual.qml) | 原生导入：3 |
| [Modules/Keystone/Styles/Shared/KeystoneHoverController.qml](../shell/Modules/Keystone/Styles/Shared/KeystoneHoverController.qml) | 计时器：54, 62 |
| [Modules/Keystone/Styles/Shared/KeystoneSurface.qml](../shell/Modules/Keystone/Styles/Shared/KeystoneSurface.qml) | 计时器：1387, 1476；原生导入：9；销毁钩子：925 |
| [Modules/Keystone/Tools/ToolsBackend.qml](../shell/Modules/Keystone/Tools/ToolsBackend.qml) | 进程对象：35 |
| [Modules/Keystone/WeatherContent/WeatherContent.qml](../shell/Modules/Keystone/WeatherContent/WeatherContent.qml) | 计时器：195 |
| [Modules/Keystone/WeatherContent/WeatherMapCard.qml](../shell/Modules/Keystone/WeatherContent/WeatherMapCard.qml) | 原生导入：3；销毁钩子：101 |
| [Modules/Keystone/WeatherContent/WeatherSunriseSunset.qml](../shell/Modules/Keystone/WeatherContent/WeatherSunriseSunset.qml) | 计时器：62 |
| [Modules/Launcher/LauncherWindow.qml](../shell/Modules/Launcher/LauncherWindow.qml) | 计时器：321；原生导入：7 |
| [Modules/Launcher/SpotlightAppDrag.qml](../shell/Modules/Launcher/SpotlightAppDrag.qml) | 销毁钩子：96 |
| [Modules/Launcher/SpotlightClipboardDetails.qml](../shell/Modules/Launcher/SpotlightClipboardDetails.qml) | 计时器：63, 242；销毁钩子：59 |
| [Modules/Launcher/SpotlightFileProvider.qml](../shell/Modules/Launcher/SpotlightFileProvider.qml) | 销毁钩子：62 |
| [Modules/Launcher/SpotlightResultsPanel.qml](../shell/Modules/Launcher/SpotlightResultsPanel.qml) | 计时器：509；销毁钩子：779 |
| [Modules/Lock/Cards/AuthCard.qml](../shell/Modules/Lock/Cards/AuthCard.qml) | 原生导入：5 |
| [Modules/Lock/Cards/WeatherCard.qml](../shell/Modules/Lock/Cards/WeatherCard.qml) | 计时器：383 |
| [Modules/Lock/DefaultLockContent.qml](../shell/Modules/Lock/DefaultLockContent.qml) | 计时器：75 |
| [Modules/Lock/DefaultLockStatus.qml](../shell/Modules/Lock/DefaultLockStatus.qml) | 销毁钩子：32 |
| [Modules/Lock/Lock.qml](../shell/Modules/Lock/Lock.qml) | 销毁钩子：56 |
| [Modules/Lock/LockContent.qml](../shell/Modules/Lock/LockContent.qml) | 计时器：578 |
| [Modules/Lock/PreLockCapture.qml](../shell/Modules/Lock/PreLockCapture.qml) | 进程对象：197；计时器：107；销毁钩子：227 |
| [Modules/Map/MapLibreView.qml](../shell/Modules/Map/MapLibreView.qml) | 网络接口：37, 40；销毁钩子：124 |
| [Modules/Sidebars/Dashboard/DailyAirQualityTrendPane.qml](../shell/Modules/Sidebars/Dashboard/DailyAirQualityTrendPane.qml) | 计时器：173 |
| [Modules/Sidebars/Dashboard/DailyForecastTrendCard.qml](../shell/Modules/Sidebars/Dashboard/DailyForecastTrendCard.qml) | 计时器：175 |
| [Modules/Sidebars/Dashboard/DailyWindTrendPane.qml](../shell/Modules/Sidebars/Dashboard/DailyWindTrendPane.qml) | 计时器：162 |
| [Modules/Sidebars/Dashboard/DrawerView.qml](../shell/Modules/Sidebars/Dashboard/DrawerView.qml) | 原生导入：2；销毁钩子：321 |
| [Modules/Sidebars/Dashboard/HourlyAirQualityTrendPane.qml](../shell/Modules/Sidebars/Dashboard/HourlyAirQualityTrendPane.qml) | 计时器：172 |
| [Modules/Sidebars/Dashboard/HourlyWindTrendPane.qml](../shell/Modules/Sidebars/Dashboard/HourlyWindTrendPane.qml) | 计时器：165 |
| [Modules/Sidebars/Dashboard/InfoView.qml](../shell/Modules/Sidebars/Dashboard/InfoView.qml) | 销毁钩子：30 |
| [Modules/Sidebars/Dashboard/WeatherAqiCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherAqiCard.qml) | 原生导入：3 |
| [Modules/Sidebars/Dashboard/WeatherAstroCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherAstroCard.qml) | 原生导入：3 |
| [Modules/Sidebars/Dashboard/WeatherBlob.qml](../shell/Modules/Sidebars/Dashboard/WeatherBlob.qml) | 原生导入：3 |
| [Modules/Sidebars/Dashboard/WeatherHumidityCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherHumidityCard.qml) | 原生导入：4 |
| [Modules/Sidebars/Dashboard/WeatherInsightCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherInsightCard.qml) | 原生导入：2 |
| [Modules/Sidebars/Dashboard/WeatherMetricTrendPane.qml](../shell/Modules/Sidebars/Dashboard/WeatherMetricTrendPane.qml) | 计时器：314 |
| [Modules/Sidebars/Dashboard/WeatherPrecipitationCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherPrecipitationCard.qml) | 原生导入：3 |
| [Modules/Sidebars/Dashboard/WeatherPressureCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherPressureCard.qml) | 原生导入：3 |
| [Modules/Sidebars/Dashboard/WeatherView.qml](../shell/Modules/Sidebars/Dashboard/WeatherView.qml) | 计时器：380 |
| [Modules/Sidebars/Dashboard/WeatherVisibilityCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherVisibilityCard.qml) | 原生导入：3 |
| [Modules/Sidebars/Dashboard/WeatherWindCard.qml](../shell/Modules/Sidebars/Dashboard/WeatherWindCard.qml) | 原生导入：3 |
| [Modules/Sidebars/Dashboard/infoTools/InfoToolDrawer.qml](../shell/Modules/Sidebars/Dashboard/infoTools/InfoToolDrawer.qml) | 计时器：135 |
| [Modules/Sidebars/Dashboard/notifications/NotificationItem.qml](../shell/Modules/Sidebars/Dashboard/notifications/NotificationItem.qml) | 计时器：301 |
| [Modules/Sidebars/Dashboard/notifications/NotificationList.qml](../shell/Modules/Sidebars/Dashboard/notifications/NotificationList.qml) | 原生导入：4 |
| [Modules/Sidebars/QuickSettings/BluetoothContent.qml](../shell/Modules/Sidebars/QuickSettings/BluetoothContent.qml) | 计时器：137, 145；销毁钩子：109 |
| [Modules/Sidebars/QuickSettings/IdleContent.qml](../shell/Modules/Sidebars/QuickSettings/IdleContent.qml) | 计时器：41 |
| [Modules/Sidebars/QuickSettings/NetworkContent.qml](../shell/Modules/Sidebars/QuickSettings/NetworkContent.qml) | 计时器：170, 178；销毁钩子：145 |
| [Modules/SystemCards/CookieClock/BubbleDate.qml](../shell/Modules/SystemCards/CookieClock/BubbleDate.qml) | 原生导入：2 |
| [Modules/SystemCards/CookieClock/CookieFace.qml](../shell/Modules/SystemCards/CookieClock/CookieFace.qml) | 原生导入：2 |
| [Modules/SystemCards/ExpressiveMetricTile.qml](../shell/Modules/SystemCards/ExpressiveMetricTile.qml) | 原生导入：4 |
| [Modules/SystemCards/SidebarCookieClock.qml](../shell/Modules/SystemCards/SidebarCookieClock.qml) | 计时器：32 |
| [Modules/SystemCards/SystemCalendarCard.qml](../shell/Modules/SystemCards/SystemCalendarCard.qml) | 计时器：30 |
| [Modules/SystemCards/SystemCardContent.qml](../shell/Modules/SystemCards/SystemCardContent.qml) | 原生导入：3 |
| [Modules/SystemCards/SystemClockCard.qml](../shell/Modules/SystemCards/SystemClockCard.qml) | 计时器：46 |
| [Modules/SystemCards/SystemLiquidMetricCard.qml](../shell/Modules/SystemCards/SystemLiquidMetricCard.qml) | 原生导入：5 |
| [Modules/SystemCards/SystemWeatherCard.qml](../shell/Modules/SystemCards/SystemWeatherCard.qml) | 原生导入：3 |
| [Modules/Wallpaper/WallpaperTransitionSurface.qml](../shell/Modules/Wallpaper/WallpaperTransitionSurface.qml) | 计时器：497 |
| [Modules/Wallpaper/ZenPaletteRenderer.qml](../shell/Modules/Wallpaper/ZenPaletteRenderer.qml) | 原生导入：17 |
| [Services/ApplicationService.qml](../shell/Services/ApplicationService.qml) | 脱离进程：66；原生导入：5 |
| [Services/AudioRecordingService.qml](../shell/Services/AudioRecordingService.qml) | 进程对象：185, 209, 235, 250；脱离进程：60；计时器：264, 273 |
| [Services/AudioSpectrum.qml](../shell/Services/AudioSpectrum.qml) | 原生导入：5 |
| [Services/AutostartService.qml](../shell/Services/AutostartService.qml) | 进程对象：472, 560；文件接口：498, 542 |
| [Services/AvatarService.qml](../shell/Services/AvatarService.qml) | 进程对象：33；脱离进程：41, 45 |
| [Services/AwwwWallpaperService.qml](../shell/Services/AwwwWallpaperService.qml) | 进程对象：325, 339, 349, 386, 440, 468；计时器：430 |
| [Services/BluetoothService.qml](../shell/Services/BluetoothService.qml) | 计时器：576, 587；销毁钩子：445 |
| [Services/BlurService.qml](../shell/Services/BlurService.qml) | 进程对象：76 |
| [Services/Brightness.qml](../shell/Services/Brightness.qml) | 进程对象：158, 175, 296, 304；计时器：311；原生导入：6, 7 |
| [Services/ClipboardService.qml](../shell/Services/ClipboardService.qml) | 进程对象：483, 500, 520, 540 |
| [Services/CloudUploadService.qml](../shell/Services/CloudUploadService.qml) | 进程对象：294；原生导入：2 |
| [Services/ControlCenterService.qml](../shell/Services/ControlCenterService.qml) | 脱离进程：44；计时器：100 |
| [Services/DefaultApplicationsService.qml](../shell/Services/DefaultApplicationsService.qml) | 进程对象：805；文件接口：755, 778 |
| [Services/DisplayColor.qml](../shell/Services/DisplayColor.qml) | 进程对象：148；计时器：126, 139, 144；文件接口：159；网络接口：80, 83；原生导入：6 |
| [Services/DisplayConfigService.qml](../shell/Services/DisplayConfigService.qml) | 进程对象：186；计时器：175, 180；原生导入：6 |
| [Services/DockService.qml](../shell/Services/DockService.qml) | 进程对象：468；计时器：510；文件接口：480；原生导入：6, 7 |
| [Services/FileActionService.qml](../shell/Services/FileActionService.qml) | 进程对象：24 |
| [Services/FileSearchService.qml](../shell/Services/FileSearchService.qml) | 进程对象：219, 234, 249；计时器：214 |
| [Services/I18nService.qml](../shell/Services/I18nService.qml) | 原生导入：5 |
| [Services/IdleService.qml](../shell/Services/IdleService.qml) | 进程对象：363, 403, 421；脱离进程：444；文件接口：374；销毁钩子：441 |
| [Services/InfoDrawerState.qml](../shell/Services/InfoDrawerState.qml) | 进程对象：142；计时器：185；文件接口：154 |
| [Services/KeyboardLockService.qml](../shell/Services/KeyboardLockService.qml) | 进程对象：80；计时器：99 |
| [Services/LyricsTrackService.qml](../shell/Services/LyricsTrackService.qml) | 原生导入：5 |
| [Services/MatugenTemplateService.qml](../shell/Services/MatugenTemplateService.qml) | 进程对象：109, 143；计时器：96, 103；文件接口：90 |
| [Services/MediaManager.qml](../shell/Services/MediaManager.qml) | 计时器：39 |
| [Services/MediaPalette.qml](../shell/Services/MediaPalette.qml) | 原生导入：5 |
| [Services/NetworkManagerExtras.qml](../shell/Services/NetworkManagerExtras.qml) | 进程对象：116, 188, 226, 253, 286 |
| [Services/NetworkService.qml](../shell/Services/NetworkService.qml) | 计时器：1104, 1118, 1131, 1142；销毁钩子：953 |
| [Services/NiriConfigService.qml](../shell/Services/NiriConfigService.qml) | 进程对象：151；文件接口：221；原生导入：8 |
| [Services/NotificationManager.qml](../shell/Services/NotificationManager.qml) | 进程对象：172；计时器：74；文件接口：246 |
| [Services/PackageService.qml](../shell/Services/PackageService.qml) | 进程对象：34, 53；计时器：72 |
| [Services/PersonalizationConfig.qml](../shell/Services/PersonalizationConfig.qml) | 进程对象：2182；计时器：2193；文件接口：2167, 2201 |
| [Services/QuickToggleConfig.qml](../shell/Services/QuickToggleConfig.qml) | 进程对象：124；文件接口：134 |
| [Services/RcloneService.qml](../shell/Services/RcloneService.qml) | 进程对象：703, 760, 793, 848, 889；计时器：922, 932, 942 |
| [Services/RecordingService.qml](../shell/Services/RecordingService.qml) | 进程对象：220, 239, 259, 274；计时器：288, 297 |
| [Services/RegionSelectionService.qml](../shell/Services/RegionSelectionService.qml) | 计时器：65 |
| [Services/SpotlightAppUsage.qml](../shell/Services/SpotlightAppUsage.qml) | 进程对象：61；文件接口：74 |
| [Services/SpotlightCatalog.qml](../shell/Services/SpotlightCatalog.qml) | 脱离进程：93 |
| [Services/SpotlightSearchService.qml](../shell/Services/SpotlightSearchService.qml) | 进程对象：127；计时器：141, 151 |
| [Services/SpotlightToolService.qml](../shell/Services/SpotlightToolService.qml) | 进程对象：209, 224；计时器：195, 200 |
| [Services/SystemCardService.qml](../shell/Services/SystemCardService.qml) | 销毁钩子：278 |
| [Services/SystemIdentityService.qml](../shell/Services/SystemIdentityService.qml) | 进程对象：153；计时器：130, 134；文件接口：141 |
| [Services/SystemMonitorService.qml](../shell/Services/SystemMonitorService.qml) | 进程对象：734；计时器：662, 669, 703, 723, 742 |
| [Services/ThemeService.qml](../shell/Services/ThemeService.qml) | 进程对象：321, 331, 346；原生导入：6 |
| [Services/Time.qml](../shell/Services/Time.qml) | 计时器：26, 32 |
| [Services/TimerService.qml](../shell/Services/TimerService.qml) | 脱离进程：87；计时器：219, 226 |
| [Services/TodoService.qml](../shell/Services/TodoService.qml) | 进程对象：80；文件接口：92 |
| [Services/TrayService.qml](../shell/Services/TrayService.qml) | 进程对象：108；文件接口：118 |
| [Services/UiPreferences.qml](../shell/Services/UiPreferences.qml) | 进程对象：575, 706, 720；计时器：698, 741, 751；文件接口：588；原生导入：7 |
| [Services/WallpaperSceneService.qml](../shell/Services/WallpaperSceneService.qml) | 原生导入：5 |
| [Services/WallpaperService.qml](../shell/Services/WallpaperService.qml) | 进程对象：686；计时器：659, 668 |
| [Services/WeatherPlugin.qml](../shell/Services/WeatherPlugin.qml) | 原生导入：3 |
| [Services/WindowPreviewService.qml](../shell/Services/WindowPreviewService.qml) | 计时器：97；原生导入：4, 5；销毁钩子：79 |
| [Widgets/common/BrailleSpinner.qml](../shell/Widgets/common/BrailleSpinner.qml) | 计时器：23 |
| [Widgets/common/CompositorBlurRegion.qml](../shell/Widgets/common/CompositorBlurRegion.qml) | 计时器：196；销毁钩子：189 |
| [Widgets/common/MaterialStepper.qml](../shell/Widgets/common/MaterialStepper.qml) | 计时器：95 |
| [Widgets/common/SearchSelectMenuField.qml](../shell/Widgets/common/SearchSelectMenuField.qml) | 计时器：423 |
| [Widgets/common/SettingsSearchAnchor.qml](../shell/Widgets/common/SettingsSearchAnchor.qml) | 计时器：99；销毁钩子：55 |
| [Widgets/common/StyledScrollBar.qml](../shell/Widgets/common/StyledScrollBar.qml) | 计时器：29 |
| [Widgets/weather/WeatherBackground.qml](../shell/Widgets/weather/WeatherBackground.qml) | 计时器：1026, 1124 |
| [core/plugin/cava/src/audio_level_provider.cpp](../shell/core/plugin/cava/src/audio_level_provider.cpp) | 计时器：9, 12 |
| [core/plugin/cava/src/audio_level_provider.h](../shell/core/plugin/cava/src/audio_level_provider.h) | 计时器：7, 65, 66 |
| [core/plugin/cava/src/cava_provider.cpp](../shell/core/plugin/cava/src/cava_provider.cpp) | 计时器：13 |
| [core/plugin/cava/src/cava_provider.h](../shell/core/plugin/cava/src/cava_provider.h) | 计时器：4, 49 |
| [core/plugin/desktopcards/src/wallpaper_analyzer.cpp](../shell/core/plugin/desktopcards/src/wallpaper_analyzer.cpp) | 计时器：6, 383 |
| [core/plugin/files/src/desktop_files.cpp](../shell/core/plugin/files/src/desktop_files.cpp) | 进程对象：8, 165, 177, 178, 181, 182；文件接口：5, 39, 40 |
| [core/plugin/files/src/desktop_files.h](../shell/core/plugin/files/src/desktop_files.h) | 文件接口：2, 38 |
| [core/plugin/files/src/file_metadata.cpp](../shell/core/plugin/files/src/file_metadata.cpp) | 文件接口：4, 13, 17 |
| [core/plugin/gamma/src/gamma_backend.cpp](../shell/core/plugin/gamma/src/gamma_backend.cpp) | 计时器：9, 69, 75, 125, 138, 183 |
| [core/plugin/keyboard/src/shortcut_recorder.cpp](../shell/core/plugin/keyboard/src/shortcut_recorder.cpp) | 文件接口：4, 5, 72, 73, 74 |
| [core/plugin/lyrics/src/lyrics.cpp](../shell/core/plugin/lyrics/src/lyrics.cpp) | 计时器：232；文件接口：4, 6, 14, 656, 667, 682, 1261, 1276, 1284, 1297, 1298, 1310, 1311, 1342, 1348, 1350, 1351, 1359, 1373, 1374, 1388；网络接口：12, 239, 623, 829, 835, 836, 848, 850, 851, 857, 871, 872 |
| [core/plugin/lyrics/src/lyrics.h](../shell/core/plugin/lyrics/src/lyrics.h) | 计时器：9, 106；网络接口：5, 6, 41, 103, 104, 105, 176 |
| [core/plugin/niri/src/niri_animation_targets.cpp](../shell/core/plugin/niri/src/niri_animation_targets.cpp) | 计时器：11, 12 |
| [core/plugin/niri/src/niri_animation_targets.h](../shell/core/plugin/niri/src/niri_animation_targets.h) | 计时器：4, 29, 30 |
| [core/plugin/niri/src/niri_floating_parallax.cpp](../shell/core/plugin/niri/src/niri_floating_parallax.cpp) | 计时器：8, 128 |
| [core/plugin/niri/src/niri_plugin.cpp](../shell/core/plugin/niri/src/niri_plugin.cpp) | 计时器：7, 17, 597 |
| [core/plugin/runtime/src/clavis_file_system.cpp](../shell/core/plugin/runtime/src/clavis_file_system.cpp) | 文件接口：3, 27, 30 |
| [core/plugin/runtime/src/config_file_watch.cpp](../shell/core/plugin/runtime/src/config_file_watch.cpp) | 文件接口：2, 12, 13, 30 |
| [core/plugin/runtime/src/config_file_watch.h](../shell/core/plugin/runtime/src/config_file_watch.h) | 文件接口：2, 23 |
| [core/plugin/windowpreview/src/window_capture_probe.cpp](../shell/core/plugin/windowpreview/src/window_capture_probe.cpp) | 计时器：7, 30, 31, 69, 71, 132 |
| [core/plugin/windowpreview/src/window_preview_manager.cpp](../shell/core/plugin/windowpreview/src/window_preview_manager.cpp) | 计时器：8, 11, 100, 226 |
| [core/plugin/windowpreview/src/window_preview_manager.h](../shell/core/plugin/windowpreview/src/window_preview_manager.h) | 计时器：6, 44, 45 |
| [core/src/niri_icon_lookup.cpp](../shell/core/src/niri_icon_lookup.cpp) | 文件接口：3, 5, 110, 124, 152, 219, 232 |
| [core/src/niri_ipc_client.cpp](../shell/core/src/niri_ipc_client.cpp) | 计时器：8, 201, 217 |
| [core/src/openmeteo_client.cpp](../shell/core/src/openmeteo_client.cpp) | 计时器：14, 176；网络接口：7, 8, 172, 173, 180, 182, 183 |
| [core/src/openmeteo_client.h](../shell/core/src/openmeteo_client.h) | 计时器：7, 42；网络接口：4, 40 |
| [core/src/runtime/backlight_reading.cpp](../shell/core/src/runtime/backlight_reading.cpp) | 文件接口：2, 7 |
| [core/src/runtime/clavis_paths.cpp](../shell/core/src/runtime/clavis_paths.cpp) | 文件接口：3, 17, 43, 55, 60, 64, 84, 86, 98 |
| [core/src/weather_backend.cpp](../shell/core/src/weather_backend.cpp) | 计时器：66, 67, 69 |
| [core/src/weather_backend.h](../shell/core/src/weather_backend.h) | 计时器：8, 38, 39 |
| [core/src/weather_cache.cpp](../shell/core/src/weather_cache.cpp) | 文件接口：3, 4, 12, 14, 20, 34, 35 |
| [core/src/weather_map_provider.cpp](../shell/core/src/weather_map_provider.cpp) | 计时器：25；网络接口：7, 8, 48, 139, 140, 143, 144, 150, 153, 186, 187, 190, 191, 197, 200, 225, 226, 229, 230, 236, 239 |
| [core/src/weather_map_provider.h](../shell/core/src/weather_map_provider.h) | 计时器：5, 73；网络接口：3, 8, 72, 74, 75, 76 |
| [core/src/weather_normals_cache.cpp](../shell/core/src/weather_normals_cache.cpp) | 文件接口：3, 4, 8, 13, 24, 26, 88, 89 |
| [core/tests/clavis_paths_test.cpp](../shell/core/tests/clavis_paths_test.cpp) | 文件接口：3, 4, 31, 32, 33, 34, 35, 36, 39, 40, 41, 42, 44, 47, 48, 49, 50, 51, 53, 54, 55, 56 |
| [core/tests/desktop_files_test.cpp](../shell/core/tests/desktop_files_test.cpp) | 进程对象：8, 61, 67；文件接口：4, 5, 34, 35, 37, 73, 82, 99, 126, 144, 166 |
| [core/tests/device_state_test.cpp](../shell/core/tests/device_state_test.cpp) | 文件接口：2, 14, 35 |
| [core/tests/icon_theme_controller_test.cpp](../shell/core/tests/icon_theme_controller_test.cpp) | 文件接口：3, 4, 24, 26 |
| [core/tests/lyrics_test.cpp](../shell/core/tests/lyrics_test.cpp) | 计时器：15, 137；文件接口：3, 5, 185, 186, 187, 188, 284, 285；网络接口：9, 11, 12, 44, 46, 47, 51, 53, 57, 62, 63, 77, 104, 108, 117, 124, 127, 149, 425, 439, 589 |
| [core/tests/niri_icon_lookup_test.cpp](../shell/core/tests/niri_icon_lookup_test.cpp) | 文件接口：3, 4, 39, 40, 41, 47 |
| [core/tests/niri_ipc_async_test.cpp](../shell/core/tests/niri_ipc_async_test.cpp) | 计时器：5, 24 |
| [core/tests/niri_minimize_test.cpp](../shell/core/tests/niri_minimize_test.cpp) | 计时器：10, 53, 90 |
| [core/tests/process_quit_test.cpp](../shell/core/tests/process_quit_test.cpp) | 进程对象：2, 11, 20, 25, 41 |
| [core/tests/weather_climate_normals_test.cpp](../shell/core/tests/weather_climate_normals_test.cpp) | 文件接口：5, 71 |
| [core/tests/weather_location_test.cpp](../shell/core/tests/weather_location_test.cpp) | 文件接口：5, 47 |
| [scripts/capture/LockSnapshot.qml](../shell/scripts/capture/LockSnapshot.qml) | 计时器：14 |
| [tests/qml/tst_gamma_backend.qml](../shell/tests/qml/tst_gamma_backend.qml) | 原生导入：3 |
| [tools/window-preview/Fixture.qml](../shell/tools/window-preview/Fixture.qml) | 计时器：14 |
| [tools/window-preview/Preview.qml](../shell/tools/window-preview/Preview.qml) | 原生导入：4 |
| [tools/window-preview/main.cpp](../shell/tools/window-preview/main.cpp) | 计时器：12, 62, 106, 111, 116, 153, 168, 174；文件接口：4, 77 |

### 脚本调用与写入复查入口

以下为 scripts 下命令、子进程与文件操作候选行号。build/dev/ci/release/install 属于开发或发布路径，不应自动进入 Shell 运行闭包；capture/system/theme/lib 中的接口需沿调用者继续确认。命中命令字符串或帮助文案不代表执行，shell 重定向与原生间接调用不能仅靠此扫描穷尽。

| 脚本 | 候选行号 |
| --- | --- |
| [scripts/build/compile-launcher-shaders.sh](../shell/scripts/build/compile-launcher-shaders.sh) | 43 |
| [scripts/capture/screenshot_to_clipboard.sh](../shell/scripts/capture/screenshot_to_clipboard.sh) | 5 |
| [scripts/check-package.py](../shell/scripts/check-package.py) | 6, 13, 43 |
| [scripts/ci/arch.sh](../shell/scripts/ci/arch.sh) | 23, 36 |
| [scripts/ci/publish.sh](../shell/scripts/ci/publish.sh) | 9 |
| [scripts/dev/check.sh](../shell/scripts/dev/check.sh) | 69, 97, 106, 107, 108, 113 |
| [scripts/dev/format-qml.sh](../shell/scripts/dev/format-qml.sh) | 62 |
| [scripts/dev/generate-search-catalog.py](../shell/scripts/dev/generate-search-catalog.py) | 15, 30, 32, 33, 101, 103, 131, 147, 148 |
| [scripts/dev/lint-qml.sh](../shell/scripts/dev/lint-qml.sh) | 33, 34, 78, 97, 107, 113, 127 |
| [scripts/install/arch.py](../shell/scripts/install/arch.py) | 15, 16, 38, 42, 46, 47, 48, 190, 263, 271, 436, 445, 478, 481, 483, 489, 513, 555, 562, 567, 572, 577, 580, 588, 616, 650, 686 |
| [scripts/install/launcher.sh.in](../shell/scripts/install/launcher.sh.in) | 38, 58 |
| [scripts/lib/matugen-registry.sh](../shell/scripts/lib/matugen-registry.sh) | 10, 11 |
| [scripts/release.py](../shell/scripts/release.py) | 16, 17, 74, 82, 90, 98, 105, 106, 128, 129, 181, 186, 201, 202, 204, 213, 214, 228, 231, 233, 242, 256, 279, 280, 283, 284, 285, 290, 337, 395, 422, 437 |
| [scripts/system/display_preview.py](../shell/scripts/system/display_preview.py) | 315, 332, 345, 363 |
| [scripts/system/manage-niri-effects.sh](../shell/scripts/system/manage-niri-effects.sh) | 4 |
| [scripts/system/manage-niri-fragment.sh](../shell/scripts/system/manage-niri-fragment.sh) | 4 |
| [scripts/system/niri_config.py](../shell/scripts/system/niri_config.py) | 2, 15, 39, 80, 96, 99, 118, 184, 187, 202, 203, 205, 236, 239, 254, 260, 307, 309, 311, 312, 320, 527, 539, 544, 547, 553, 587, 620, 621, 689, 707, 722, 730, 737, 738, 758, 763, 768 |
| [scripts/system/niri_outputs.py](../shell/scripts/system/niri_outputs.py) | 1, 3 |
| [scripts/system/overview.sh](../shell/scripts/system/overview.sh) | 12, 25 |
| [scripts/theme/generate_matugen_colors.sh](../shell/scripts/theme/generate_matugen_colors.sh) | 6, 72, 73, 83, 84, 99, 104, 106 |
| [scripts/theme/list_cursor_icon_themes.sh](../shell/scripts/theme/list_cursor_icon_themes.sh) | 13 |
| [scripts/theme/manage_matugen_templates.sh](../shell/scripts/theme/manage_matugen_templates.sh) | 6, 28, 29, 31, 109, 114, 126 |
| [scripts/theme/set_system_color_scheme.sh](../shell/scripts/theme/set_system_color_scheme.sh) | 17, 18, 22, 29, 37 |
| [scripts/theme/write_niri_cursor_config.sh](../shell/scripts/theme/write_niri_cursor_config.sh) | 4 |

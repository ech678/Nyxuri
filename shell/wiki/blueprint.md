# Nyxuri Shell — 启动与架构设计

## 文档状态

当前已完成 P0 调查并冻结启动计划，正式进入 P1 阶段（第一个可用里程碑）。本页维护确定约束、技术事实与
已冻结设计；任务顺序/状态唯一维护在 [Shell ROADMAP](../ROADMAP.md)，
约束见 [AGENTS](../AGENTS.md)，事实见 [审计](audit.md)，操作见
[开发与调试](development.md)。产品名 Nyxuri Shell，程序/配置标识 nyxuri-shell。

“精神 → 详细计划 → 开发”是开发推进顺序，不意味着必须新增一个轻量程序启动复杂程序。
原版 Niri、完整母体就地修整、视觉保真与干净生命周期已确定；启动管理实现尚须论证。

## 已确定的设计边界

运行代码最终分为 app（装配/环境/协调）、modules（自治功能域）、shared（纯控件/
动画/计算）、native（必要原生桥）。资源、测试、工具和许可不强行塞进四层。
现有 AppShell/Modules/Services/Common/core 是待修整母体，不是已完成的目标架构。

- 依赖显式注入；跨域协调通过窄接口，不能随手调用全局业务 singleton。
- 展示组件不执行命令、写文件或发请求；Action Gateway 收敛桌面意图，明确 backend
  执行副作用并登记 owner。后台订阅也要明确归属。
- shared 不读环境或存储，不持有业务连接、后台任务；Common 不能整体直接搬入 shared。
- 可选 native 隔离 import 和构建依赖。Loader inactive 不保证静态 import 不解析；
  降级需真实组件验证，不伪造接口桩。
- 面板关闭动画后销毁，停用域停止 Timer/重连、断连接、取消请求、结束专属进程并释放引用。
  基础常驻服务按真实消费者保留；关闭历史面板不能停止通知接收。
- 锁屏安全状态不受普通停用/切换破坏；只清理受管实例，不杀其他 Shell 或用户应用。

C++ 不是项目强制选择。QML/JavaScript 承担界面与普通逻辑；先修整现有 C++ 的有效模型/
协议，不为“零 C++”全面重写。新增 native 必须证明系统能力缺口或实际性能必要性。

原版 Niri 是支持基线。Clavis.Niri 是上游自定义桥，不等于全部依赖魔改；每个请求、事件
和字段单独核实。动画目标/最小化和浮动移动/视差分别调查，不按功能名字判定兼容性。
已证实需要扩展的高级能力封存，基础工作区/窗口/输出标准能力保留。

## 启动与第一个开发闭环

先证明隔离环境中的基础界面、输入、ready 与干净退出，再证明真实会话的接管、切换和
恢复。两个检查点属于同一 P1；隔离运行成功不能替代完整闭环验收。

现状是 shell.qml 直接实例化 AppShell；入口静态导入 Clavis.Niri，完成钩子又初始化
歌词等服务。核心闭包、native 构建和母体隐式上下文必须一起追踪，不能只改主入口。
首个运行里程碑包括保留视觉的基础栏、本地应用入口、就绪/退出、即时切换与调试流程。

P0 需为每个启动对象记录：是否核心必需、解析依赖、初始化副作用、资源 owner、退出
方式及缺失行为。输出具体改动顺序，优先隔离封存功能，不先改造整个仓库。

启动要能区分环境检查、进程创建、QML 解析、首帧、动作就绪与失败。进程存活或路径
可执行都不等于 ready。就绪探测来源、超时、日志与退出契约在 P0 冻结；基础就绪不应
等待尚未实现的通知等后续域初始化。

### 切换目标与当前事实

当前 set 只写 active_shell/custom_shell_bin 偏好，status 只检查可执行文件；启动脚本
exec custom 后不能处理其崩溃。目标是提前在 P1 兑现 set 的可靠即时切换。

- 保留 noctalia/custom 兼容值和可选路径；Nyxuri Shell 名称不强制触发账本迁移。
- 区分偏好与实际实例，动作路由按真实运行端分发，不能在回退后继续调用失败端。
- 先做不占用共享资源的目标预检，再按已验证的交接流程停止旧实例与启动目标，
  目标就绪后才提交选择；失败清理目标并恢复旧 Shell。
- 重复请求幂等、并发串行；不无限重启。恢复也失败时明确记录两次失败。
- 默认 Noctalia；对现存不受管实例先确认归属/接管，禁止按名字直接杀进程。
- 锁屏或无法确认安全状态时拒绝切换；安全锁崩溃不能用普通回退宣称解决。

P0-06 必须明确各步允许的资源占用与动作路由：预检不等于 ready，目标不能以双栏或
通知服务争抢换取提前就绪。旧实例停止后的空档、目标失败、恢复失败及管理进程中断
都要有可观察状态与有界处理；具体实现、探测来源和时限仍须调查后冻结。

### 已冻结的设计决策 (P0-08 冻结)

| 决策 | 冻结结论与依据 |
| --- | --- |
| 会话所有者 | 沿用现有 `session-shell.sh` 与 Python 管理引擎结合；不增设额外独立常驻 supervisor |
| readiness/退出 | 目标进程启动后以 IPC 握手或 Socket 监听为就绪依据（限时 3.0s）；退出使用优雅信号 + 2.5s 超时清理 |
| custom 兼容 | 保留 `--action` 插槽；不支持健康接口的旧 binary 仅在成功映射窗口时视作就绪 |
| 无图形会话/不受管实例 | `nyxuri shell set` 在无 Wayland 时仅持久化账本；发现不受管实例先尝试优雅通知或提示用户，禁止盲目 pkill |
| 开发命令 | 统一使用 `qs --path ./shell --no-duplicate -v` 隔离调试；不强行增加复杂包装命令 |
| 模块/动作接口 | P1 首个闭环仅对接标准工作区、聚焦窗口、应用启动器及锁屏，重型模块全部隔离封存 |
| 超时与性能目标 | 退出超时 2.5s，就绪探测超时 3.0s；有界重试，失败立即回滚旧 Shell |

## 后续架构与宿主连接

四层按完整功能域增量迁移，可运行检查点通过验收；实验中间状态允许失败但保留恢复点。
保留有效消费者计数和取消机制；跨热重载
引用、异步代际和专属子进程要有明确释放责任。应用启动与 Shell 专属任务分开归属。

去臃肿化与迁移一起推进：缩小启动闭包、停止无消费者后台、拆分默认构建依赖，并核实
删除死代码、重复实现与废弃资产。每个域迁移后清理旧路径，避免双实现长期共存。
app 协调，域 backend 执行；Action Gateway 不包揽业务。先用两个真实域检验接口，
不为未来所有移植提前设计框架。封存与删除依据见开发契约，状态只维护在路线图。

首期完整基础面包括工作区/活动窗口/时钟/电池/托盘、启动器、会话、通知、音量/亮度、
设置和安全锁屏；核心最低面不等于永久删除这些功能。Cava、天气地图、歌词等重型
附加功能不进入奠基闭包。静态色板可用于奠基，后续必须兑现原生壁纸/M3 同构 palette.toml。

TemplateAdapter 根据 Wiki 的 [主题适配](../../configs/noctalia/README.md)、注册配置和
真实模板确定渲染器/变量契约；GTK CSS、Fcitx SVG、Kitty、Starship 与用户模板无需重写
的承诺保留，不能未经调查自创有限 Jinja 子集并声称完全兼容。

正式宿主对接兑现六动作 launcher/session/settings/clipboard/lock/wallpaper-random；
另有 wallpaper-picker/radial-launcher 兼容接口。尚未实现动作明确不可用，不暗中拉另一套
Shell 执行。Noctalia 伴生 GUI 在 Noctalia 模式按需使用，自研模式不依赖它们。

源码预览允许 qs 显式 --path；正式配置必须原子复制，禁止源码软链进 ~/.config。
运行配置标识使用 nyxuri-shell，用户设置/状态/缓存按宿主 XDG 边界单独管理；具体部署
清单和路径方案在 P5 明确，不能提前修改真实文件。更新/快照/回滚/卸载遵循宿主保留契约，
不删除用户其他 QS 配置。Python 管理引擎保持纯标准库。

## 验证设计

- 行为测试用 TempEnv、可控进程/IPC 与参数数组断言，覆盖成功、崩溃、超时、并发、
  清理、恢复失败和状态不一致；不靠 regex 匹配 QML 布局伪造架构测试。
- 真实原版 Niri 检查首帧、输入、视觉、通知互斥、锁屏、多屏与退出；离屏只能辅助解析。
- 反复开关、停用和切换，观察专属资源与后半程稳态；不把字体/分配器缓存自动判成泄漏。
- 启动记录首帧和 ready 的 p50/p95，机器/版本/缩放/字体固定；暖缓存与冷缓存分开。
  测量基线建立后冻结秒级目标，不写未经论证的硬门槛。
- 宿主必要检查、受影响 native/协议测试和文档事实同步；上游 monorepo 路径、格式基线与
  源码内生成问题先明确，阻断如实记录，不安装工具或全库重排来掩盖它。

## P1 交付事实与工程成果

1. **构建与加载解耦**：
   - CMake 将 Cava、Weather、Lyrics 设为默认 `OFF`，保留 7 个核心 native 模块并保持 21 个 CTest 100% 通过；
   - 采用动态 Loader 隔离 `Clavis.Cava`、`Clavis.Weather`、`Clavis.Lyrics` 与 AUR `M3Shapes`，彻底消除运行时静态解析阻断；
   - `AppShell.qml` 精简顶层常驻装配，保留 `Bar`、`Lock`、`PowerMenu`、`LauncherWindow`，封存模块安全撤出。
2. **基础界面与字体回退**：
   - 修复 `SysMonitor.qml` 在未获取 CPU 温度时的 `undefined` 类型警告；
   - `Fonts.qml` 增强多候选回退链（优先使用系统已有的 `LXGW WenKai Mono`、`霞鹜文楷等宽`、`Noto Sans CJK SC`），排版优雅稳定；
   - 产出 `shell/bin/nyxuri-shell` 统一步伐入口，原生支持六动作派发（`--action`）、就绪探测（`--check-ready`）与优雅终止（`--stop`）。
3. **即时热切换状态机**：
   - 实现纯 Python 标准库 `nyxuri/shell_switcher.py`：预检目标 -> 锁屏防御 -> 停止旧端 (2.5s) -> 启动新端 -> 就绪探测 (3.0s) -> 成功提交账本 / 失败清理并回滚恢复旧 Shell；
   - `cli.py` 增强 `nyxuri shell status`（区分偏好与运行实例）与 `nyxuri shell set`（无图形会话安全存账，Wayland 会话平滑切换）；
   - `session-shell.sh` 与 `shell-action.sh` 增加对 `nyxuri-shell` 的自动回退发现；
   - 宿主单元测试增加状态机与回滚测试，478 个全量单测全部保持秒级通过。

## P2 交付事实与工程成果

1. **四层架构骨架落地**：
   - 创建 `shell/app/`（装配、环境与协调）、`shell/modules/`（自治功能域）、`shell/shared/`（纯共享层）三层目录，形成规范的单向依赖流；
   - 提取纯净共享层：`shared/theme/Appearance.qml`（纯设计系统 Token）、`shared/controls/StateLayer.qml`（状态交互层）、`shared/controls/MaterialSymbol.qml`（安全边界图标渲染）与 `shared/compositor/CompositorBlurRegion.qml`（无 Services 耦合的高斯模糊），严守零 IO、零进程副作用底线。
2. **意图收敛与命令安全**：
   - 实现全局单例 `shell/app/ActionGateway.qml`，所有系统电源动作（`poweroff`、`reboot`、`suspend`、`hibernate`、`logout`、`lock`）及应用启动全部收敛并使用纯参数数组调用外部命令（`Quickshell.execDetached`）；
   - 继承安全锁屏挂起防御（挂起/休眠前确保 `sessionLocker.secure`）。
3. **功能域 1（Session）自治生命周期与去冗余**：
   - 构建 `shell/modules/session/SessionHost.qml` 与 `SessionPanel.qml`，彻底废弃旧母体常驻 `Loader { active: true }` 占用；
   - 实现面板打开时按需挂载、按键与鼠标交互、关闭动画结束后触发 `dismissFinished` 彻底销毁窗口并释放 Layer-shell 表面（`active: false`）；
   - 彻底删除旧 `shell/Modules/PowerMenu/` 目录与 `shell/Services/PowerMenuService.qml`，并同步更新状态栏 `PowerButton.qml` 与 `QuickSettingsSurface.qml` 对接 ActionGateway。
4. **功能域 2（Launcher）接口复用与验证**：
   - `LauncherWindow.qml` 接入 `ActionGateway` 意图收敛与 `shared/controls`、`shared/theme`，验证共享层通用性与动作路由一致性。
5. **契约测试与原生构建验证**：
   - 宿主单元测试扩展 P2 四层结构与命令参数契约断言，480 个单测秒级全绿通过；
   - 原生构建 23 个 CTest 100% 通过（22 个通过，1 个跳过）。

## 目录架构重构与清算规划

### 1. 终局物理目录树规范

重构最终彻底废弃上游平铺混杂的 `Modules/`、`Services/`、`Common/`、`Widgets/`、`Components/` 目录，收敛至严格的四层规范目录：

```text
shell/
├── bin/
│   └── nyxuri-shell              # 统一命令行入口与动作派发
├── shell.qml                     # Quickshell 顶层入口 (ShellRoot)
├── app/                          # 第一层：装配、协调与动作网关
│   ├── AppShell.qml              # 顶层对象装配与环境协调
│   ├── ActionGateway.qml         # 动作收敛中枢（参数数组化命令调用、锁屏防御）
│   └── RuntimeContext.qml        # 全局只读上下文（显示器、会话状态注入）
├── modules/                      # 第二层：自治功能域（按需加载、关闭即销毁、内聚私有逻辑）
│   ├── session/                  # 会话面板（P2 已完成）：SessionHost, SessionPanel
│   ├── settings/                 # 系统设置（原 ControlCenter，P3-01）：SettingsHost, pages/
│   ├── bar/                      # 状态栏（原 Modules/Bar，P3-02）：BarHost, workspaces, clock, tray
│   ├── notifications/            # 通知系统（P3-03）：常驻 D-Bus 监听与瞬态弹窗/抽屉
│   ├── lock/                     # 真实锁屏（原 Modules/Lock，P3-04）：LockHost, PAM 上下文
│   ├── launcher/                 # 应用启动器（P3-05）：LauncherHost, providers/
│   ├── clipboard/                # 剪贴板历史（P3-05）：ClipboardHost, 数据源
│   └── wallpaper/                # 原生壁纸与调色（P4）：渲染器与 palette.toml 导出
├── shared/                       # 第三层：纯共享层（严格零 IO、零外部进程、零环境读取）
│   ├── theme/                    # 设计系统 Token：Appearance.qml, Fonts.qml, Colors.qml
│   ├── controls/                 # 基础原子控件：StateLayer.qml, MaterialSymbol.qml, Button, Slider...
│   ├── compositor/               # 合成器特效桥：CompositorBlurRegion.qml
│   └── utils/                    # 纯计算与数学函数（几何对齐、颜色转换、贝塞尔）
├── native/ (或 core/)            # 第四层：原生 C++ 桥与扩展
│   ├── runtime/                  # ClavisRuntime: 硬件/输出/路径探测
│   ├── niri/                     # ClavisNiri: 原版 Niri IPC Socket 流与标准事件
│   ├── tests/                    # CTest 契约测试集
│   └── optional/                 # 封存可选模块 (cava, weather, weathermap, lyrics, windowpreview)
├── assets/                       # 静态资源（本地 SVG 图标、QSB 着色器；内嵌字体彻底淘汰）
├── i18n/                         # 国际化多语言翻译
└── wiki/                         # 架构契约与开发文档
```

### 2. 旧母体清算与迁移映射表

| 原母体目录 / 文件 | 处置动作 | 目标路径 | 依赖与副作用处理 | 清理时机 |
|---|---|---|---|---|
| `Modules/PowerMenu/` | **物理删除** | `modules/session/` | 淘汰 `PowerMenuService`，改用 `ActionGateway` 纯数组调用 | **P2 已完成** |
| `Services/PowerMenuService.qml` | **物理删除** | `app/ActionGateway.qml` | 消除全局业务单例 | **P2 已完成** |
| `Modules/ControlCenter/` | **重构迁移** | `modules/settings/` | 剥离 `Clavis.WeatherMap` 依赖；改为按需 Loader 与动态页面加载 | **P3-01 已完成** |
| `Services/ControlCenterService.qml` | **私有内聚** | `modules/settings/SettingsBackend.qml` | 消除全局单例，降级为 settings module 内部私有协调对象 | **P3-01 已完成** |
| `Modules/Bar/` | **重构迁移** | `modules/bar/` | 接入 `shared/controls` 与 `shared/theme`；外设断开平滑降级 | P3-02 |
| `Services/NotificationManager.qml` | **重构内聚** | `modules/notifications/NotificationService.qml` | 保留常驻 D-Bus 监听，消除与 UI 面板的硬耦合，限制历史上限 | P3-03 |
| `Modules/Sidebars/notifications/` | **重构迁移** | `modules/notifications/NotificationDrawer.qml` | 瞬态面板，关闭即销毁 | P3-03 |
| `Modules/Lock/` | **重构迁移** | `modules/lock/` | 解耦 PAM 认证状态机与装饰层；锁屏中状态机安全防御 | P3-04 |
| `Modules/Launcher/` | **重构迁移** | `modules/launcher/` | 对接 `ActionGateway` 与 `shared/`；解耦按需 provider | P3-05 |
| `Common/Appearance.qml` | **拆分迁移** | `shared/theme/Appearance.qml` | 剥离文件读写与 XDG 依赖，变为纯设计系统 Token | P2 已提取纯净层，P5 彻底清理旧文件 |
| `Common/Fonts.qml` | **重构迁移** | `shared/theme/Fonts.qml` | 建立系统文楷与 Sans 回退链，删除 4MB Google Sans 实体 | P5 |
| `Widgets/common/*` | **提取迁移** | `shared/controls/*` | StateLayer、MaterialSymbol 等纯交互控件逐项收敛入 shared | P2 已开始，P3-P5 逐步清空 |
| `Widgets/audio/`、`weather/` | **封存删除** | — | 随重型功能封存，不进入核心四层 | P3 期间清理 |
| `Modules/DesktopCards/`、`Dock/` | **封存删除** | — | 非核心桌面层，P1 已解除装配，彻底物理清理 | P5 |
| `Services/AwwwWallpaperService.qml` | **物理删除** | `modules/wallpaper/` (P4 自研) | 淘汰 awww 进程轮询，P4 统一用自研与 palette.toml 替换 | P4 |
| `Services/cava/`、`lyrics/`、`weather/` | **封存隔离** | `native/optional/` | 静态 import 阻断已消除，P5 移出主构建树 | P5 |
| 跨域 Services (40+ 个) | **彻底清算** | 归入所属 module 或淘汰 | 彻底根除“全局单例地狱”，只允许 app 持有全局协调 | P3-P5 逐域清空 |

### 3. 重构执行守则

1. **逐域推进，拒绝大爆炸重构**：严禁一次性全库移动文件导致几百个 QML import 断裂。必须遵循“选定功能域 ➔ 提取 shared 原子 ➔ 实现 modules 自治域 ➔ 接入 app ➔ 物理删除旧目录 ➔ 契约单测断言旧文件消失”的严谨闭环。
2. **零容忍代码冗余**：新域交付的同时，旧实现必须彻底从磁盘删除，严禁新旧两套代码长期并存。
3. **单向依赖铁律**：`shared/` 绝对禁止 import `modules/`、`Services/` 或 `app/`；`modules/` 只能依赖 `shared/`，跨域必须经过 `app/ActionGateway` 或显式属性注入。




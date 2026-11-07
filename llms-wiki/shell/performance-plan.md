# Nyxuri Shell 性能与资源治理完整计划

> 状态：进行中；整体未完成。
>
> 本计划只描述一次性完整实施，不拆 MVP，不以临时降级或删除功能换取数字。
> 目标是保留 Nyxuri Shell 的用户可见能力、视觉质量、交互反馈和可诊断性，同时
> 降低冷启动时间、稳态内存、事件循环负载、渲染成本、外部进程开销和长时间运行
> 后的资源漂移。

> 当前执行记录（2026-11-07）：容器 benchmark runner、资源探针和启动生命周期改造
> 已落地；固定 Quickshell 0.3.2/Weston/D-Bus 容器已真实运行并生成报告。当前报告
> 的 `startup_valid`、`sample_valid`、`controlled_shutdown` 均为 100%，但因容器内
> 若干可选外部命令缺失，`process_start_failures=9`，兼容性矩阵和失败日志归因仍未
> 完成，因此本计划整体仍未完成。
>
> 后续执行记录：兼容性探针已改为自带隔离 Weston，长稳态/回收参数、old/new channel
> 和 live telemetry 已合并；最新短 smoke 曾因合并时参数/生命周期冲突失败，修复已
> 提交但尚未生成新的完整 raw/report。旧 channel、10 分钟稳态、100-cycle 回收和
> QML live census 仍不得标记为已验证。
>
> 2026-11-07 完整 new-channel 容器报告已生成：10 冷启动、5 warm、600.179 秒稳态
>（596 样本）、100/100 回收、0.1/1/2/5 秒窗口和兼容性矩阵成功。old 0.2.1 已按
> 五种 rootless/privileged 变体重试，均在 Qt 6.12 头文件兼容性错误处失败，已按
> 环境/工具链原因记录跳过。Loader/unit live census 已接入，其他 QML 资源类别仍以
> partial/null 明示。
>
> 旧 channel 后续已补齐：独立 pinned Qt 6.8.3/Nixpkgs toolchain 下 Quickshell 0.2.1
> 容器构建 991/991 成功，runtime 与 Loader/IPC/qmlcache compatibility probe 均成功。
>
> 最新资源 smoke（当前代码）真实返回 loaders=12、timers=11、processes=3、fileviews=1、
> connections=1、windows=1、delegates=11；Canvas/layer 仍为 null。进程 lifecycle 已
> 提供 PID/starttime/command/观测时长下界/launch 与 restart 估计；owner、精确 kernel
> exit、逐进程 CPU/output 归因仍不可得。两项限制均保留为 partial，不作为完成证据。
>
> 进程采样已增加 lower-bound lifecycle 聚合（PID/starttime/command/首次与末次观测、
> launch/restart 估计和失败启动分类），owner 与真实 kernel exit 仍明确标为不可得。

> 最新 owner smoke 已在当前代码中确认：StateProjection/FilePickerWindow/NiriDriver/
> SystemMonitorService/NetworkService 的 owner 分类和资源计数可从容器 IPC 读取；
> Canvas/layer 与未注册服务仍明确 partial。

## 0. 硬约束

- 禁止在宿主机真实启动 Nyxuri Shell、Quickshell、Weston、Niri 或任何会创建桌面
  窗口、Wayland surface、IPC 会话的运行测试。
- 所有真实启动、IPC、窗口、渲染、帧时间、进程树、内存、I/O、长稳态和交互测试
  必须在一次性隔离容器内完成；容器内使用独立的 `HOME`、所有 XDG 目录、Wayland
  socket、D-Bus session、配置、状态、缓存和临时目录。
- 宿主机只允许执行静态读取、代码检查、文档检查、容器构建/运行命令编排和结果
  读取；不得调用 `shell/nyxuri-shell`、`qs`、`quickshell`、`weston`、`qmlscene`
  或其他真实桌面入口。
- 容器内的运行环境必须固定 Quickshell、Qt、Wayland compositor、renderer、
  Nixpkgs revision、Python 和测试脚本版本；报告必须写出这些版本和 Git SHA。
- `.omo/` 中已有报告属于历史资料，不作为当前实现的结论、失败依据或性能基线。
  只有本计划实施后在当前代码、当前容器锁定环境中重新生成的报告才具有验收效力。
- 不删除用户体验功能；天气、壁纸、通知、Dock、Spotlight、Settings、Dashboard、
  Keystone、锁屏、媒体、歌词、Cava、网络、蓝牙、剪贴板、主题、搜索和多屏能力
  必须保留。只有在没有消费者且有源码、调用点、行为测试和容器运行证据时，才可
  清理死代码或无效资产。
- 不以 `visible: false` 冒充卸载；停用必须销毁对象、停止 Timer/Process/Socket、
  断开 Connections、取消请求、释放模型和纹理。
- 不全局关闭动画、blur、shader、Canvas 或主题效果；只能依据真实场景 profiling
  对具体对象做生命周期化、可见性化或分辨率化调整。
- 不引入 pip 依赖，不把一次性 benchmark 工具变成运行时依赖，不把宿主机路径、
  用户配置、凭据或个人信息写入报告和源码。

## 1. 交付物清单

- [ ] `llms-wiki/shell/performance-plan.md`（本计划，作为实施入口）。
- [x] 容器构建定义与锁定的 Quickshell/Qt/Nixpkgs 版本记录。
- [x] 容器内可重复执行的 benchmark runner，支持基线、冷启动、热启动、交互、
  长稳态、资源回收、渲染和失败场景。
- [x] 机器可读的 JSON 原始报告、汇总报告、对比报告和人读 Markdown 报告。
- [x] 运行时资源探针：singleton、Loader、Timer、Process、FileView、Canvas、
  layer、窗口、模型和纹理相关的可观察计数。
- [ ] 启动闭包、常驻对象、按需对象和消费者关系清单。
- [ ] 逐项优化补丁、对应行为测试、容器真实使用证据和可回滚提交边界。
- [ ] 性能预算表、回归门禁、残余风险、环境限制和未覆盖项。
- [ ] 与实现同步的 `shell/ROADMAP.md`、`llms-wiki/shell/development.md` 或
  其他受影响契约文档；只在行为已经被代码和容器证据证明后更新状态。

## 2. 容器运行环境与 Quickshell 更新

### 2.1 环境形态

- [x] 采用可复现的 Nix/Podman 容器；代码以只读方式挂载到 `/workspace`，结果写入
  单独的 `/results` 挂载点，禁止容器反向修改仓库源码。
- [x] 容器内创建独立目录：`/tmp/nyxuri-home`、`/tmp/nyxuri-config`、
  `/tmp/nyxuri-data`、`/tmp/nyxuri-state`、`/tmp/nyxuri-cache`、
  `/tmp/nyxuri-runtime`。
- [x] 运行 Weston headless 或等价隔离 Wayland compositor；只使用容器内部
  `WAYLAND_DISPLAY`，不能绑定宿主 Wayland socket、X11 socket 或真实 D-Bus。
- [ ] 先建立软件渲染可重复基准，再建立容器内 GPU/渲染后端基准；两套报告不能混用。
- [ ] 容器内设置固定 locale、timezone、CPU affinity 策略、屏幕尺寸、刷新率、
  屏幕数量和随机种子；随机 wallpaper、搜索排序和通知顺序必须可复现。
- [ ] 禁止测试脚本扫描宿主 `/proc`、宿主用户目录或宿主进程；进程、cgroup、fd、
  I/O 和内存采样必须限定在容器测试进程树。

### 2.2 更新 Quickshell

- [x] 在容器中查询可用的最新稳定 Quickshell 版本和对应 Nixpkgs 包信息；不要在
  宿主机安装或升级任何包。
- [x] 选择一个明确版本作为本轮基准，记录：Quickshell 版本、revision、Qt 主次
  版本、QtQuick backend、Wayland backend、Nixpkgs revision 和镜像 digest。
- [x] 对当前契约要求的 Quickshell 0.3.2 行为做兼容性矩阵：`qmldir`、动态
  `Loader`、`file://` source、`qs.*` 预热 import、QML disk cache、`IpcHandler`、
  `FloatingWindow.minimumSize`、`HoverHandler` 和 `TapHandler`。
- [x] 在容器中分别测试旧锁定版本和更新版本：冷编译、重复启动、Loader 单元装载、
  单元 off/on、IPC 注册、SIGTERM、崩溃恢复和 qmlcache 命中/失效。
- [ ] 只有当更新版本通过全部行为矩阵并且性能不引入功能回归时，才把容器默认版本
  更新为新版本；失败时保留旧版本作为对照，不修改用户环境。
- [x] 把 Quickshell 版本选择写入容器锁定文件和 benchmark 报告，禁止使用浮动的
  `latest` 作为可交付基准。
- [ ] 重新验证 `shell/nyxuri-shell` 的 qmlcache 清理策略。若新版本可靠失效缓存，
  改为按源码/版本指纹清理；若仍需冷编译，保留清理并把成本单独记录。

## 3. 基准工具修正与测量契约

### 3.1 报告正确性

- [x] 修复 benchmark 的成功语义：采样后受控 SIGTERM 是正常结束，不得被记为失败。
- [x] 将 `marker`、`startup_valid`、`sample_valid`、`controlled_shutdown`、
  `fatal_log_count`、`compiled_empty`、`process_start_failures` 和 `success` 分开。
- [x] `success` 只在启动标记有效、采样有效、无 compiled empty、无 required 或
  无法归因的进程启动失败、无 fatal 错误时成立，与退出码是否为 0 解耦。已确认的
  optional dependency 失败单独计数，不阻断成功；未知命令和缺失命令详情按失败处理。
- [x] 所有缺失、无效、空集合和零分母指标均输出 `null`/`N/A`，报告生成不能抛异常，
  也不能把缺失值伪装成零。
- [x] 报告写出当前 Git SHA、工作树 dirty 状态、容器镜像 digest、Quickshell/Qt/
  Weston/Nixpkgs 版本、测试参数、渲染后端和环境变量摘要。
- [x] 报告中区分源码静态 profile、冷启动、热启动、稳态、峰值、交互、回收和长稳态；
  不把不同场景合并成一个无法解释的分数。

### 3.2 基线与重复次数

- [x] 同一个容器镜像内运行空 `ShellRoot` 基线、最小 Nyxuri 配置、默认全功能配置。
- [x] 冷启动每个场景至少 10 次，先丢弃一次预热结果，再报告 p50/p95/p99、min/max、
  标准差和失败次数。
- [x] 热启动明确缓存状态：qmlcache 命中、qmlcache 清空、XDG 缓存保留和完整 sandbox
  重建必须分别测试，不能把它们统称为 warm。
- [x] 每个长稳态场景至少运行 10 分钟；高频打开/关闭场景至少循环 100 次；通知、
  搜索、网络设备等数据量场景至少覆盖 1、10、100、1000 条记录。
- [x] 每次报告保存原始采样，而不是只保存最终平均值；异常运行保留日志和退出原因。

### 3.3 采样项目

- [x] 启动：进程创建、首个日志、FIRST_FRAME、READY、IPC_READY、首个可交互动作。
- [x] CPU：进程树 user/system CPU、CPU 时间、CPU 利用率、上下文切换、page fault。
- [x] 内存：RSS、PSS、Private、匿名/file/shmem、VmPeak、VmHWM、swap、cgroup current
  和 peak。
- [ ] 进程：Shell 子进程数量、线程数、fd 数、Process 启动次数、失败次数、平均
  生命周期和重启次数。
- [x] I/O：read/write bytes、read/write syscall 数、日志字节数、配置和缓存读写。
- [ ] QML live census：Loader 状态、已实例化单元、singleton 触发列表、活跃 Timer、
  活跃 Process、FileView、Connections、Repeater/ListView/GridView delegate、Canvas、
  layer 和窗口计数。Loader/unit/delegate 已有真实运行值；Timer、Process、FileView、
  Connections、Canvas、layer、window 仍未集中 instrument。
- [x] 容器 runner 在进程树性能采样结束后读取 `shell metrics`，把 startup metrics 与
  `qml_resources` 分开写入每次运行记录。计数缺失时输出 `null` 和 `unavailable`；只有
  IPC payload 提供完整的非负整数计数时才标为 `available`。源码计数仍归 `static_qml`，
  不作为 live census 替代。
- [x] 回收：关闭动作后 100 ms、1 s、2 s、5 s 的计数和 RSS/PSS；重复循环后的基线
  漂移；异常退出后的残留进程和 socket。
- [ ] 渲染：容器内 renderer 的帧时间、掉帧、纹理/离屏目标可用指标；软件渲染与 GPU
  后端分开报告。

## 4. 功能保持矩阵

- [ ] 启动与 IPC：`shell status`、`stage`、`isReady`、`metrics`、`diagnostics`、
  `log`、unit reload、theme、wallpaper、shortcut-map。
- [ ] 六大插槽：`edge`、`island`、`overlay`、`drawer`、`surface:desktop`、
  `popup:notification` 的启用、停用、仲裁和恢复。
- [ ] 面板：bar、dock、Spotlight、Settings、Quick Settings、Dashboard、Keystone、
  notifications、session、lock、region selector、wallpaper。
- [ ] 数据域：Niri workspace/window/output、音量、亮度、网络、蓝牙、电池、媒体、
  天气、系统指标、剪贴板、应用目录、主题和国际化。
- [ ] 可选重型消费者：天气动画、壁纸编辑器、图片预览、Cava、lyrics、录音、网络
  扫描、蓝牙发现、文件选择器和大列表搜索。
- [ ] 异常：缺少 Niri、缺少可选命令、损坏配置、损坏 JSONL、Process 启动失败、
  Loader compiled empty、IPC 目标消失、锁屏期间 unit off、SIGTERM 和崩溃恢复。
- [ ] 用户体验：动画时长和方向、键盘导航、鼠标/滚轮、焦点、hover/press 状态、
  多屏定位、主题切换、语言切换、错误横幅和可诊断日志不得因优化消失。

## 5. 启动闭包与初始化清单

- [ ] 生成完整 import/类型/Loader 闭包图，标注 `shell.qml` 顶层预热 import 的必要性。
- [ ] 保留 Quickshell 0.3.x 动态 Loader 所需的最小预热集合；每次减少 import 前在
  容器内完成冷编译 20 次和单元加载矩阵，不以静态 grep 代替运行验证。
- [x] 将启动工作明确分为 CORE、INTERACTIVE、BACKGROUND、ON-DEMAND 四类，并为每个
  初始化动作记录 owner、触发条件、最大耗时、失败行为和取消方式。
- [ ] 保证 CORE 只包含 ShellRoot、AppShell、StateProjection、PluginRegistry 的
  必要部分、CompositorDriver 基础面、ActionGateway、最小 IPC 和主题 token。
- [ ] 将字体完整刷新、系统身份、完整 i18n、应用目录、默认应用、模板刷新、网络
  扩展探测等移入首帧后可取消队列，不阻塞 FIRST_FRAME/IPC_READY。
- [x] 建立单一启动调度器，批量执行 background job，限制每个事件循环批次的工作量，
  记录每项耗时和失败原因；禁止多个 singleton 在 `Component.onCompleted` 无序抢占启动。
- [ ] 为每个后台任务提供 cancellation、timeout、retry 上限和幂等 teardown；失败只影响
  对应能力，不阻塞核心 Shell。
- [ ] 检查 AppShell、ShellStartupService、PluginRegistry、StateProjection、ThemeService、
  FontService、I18nService、SystemIdentityService 的初始化顺序和重复触发。
- [ ] 评估 `SlotHost` Repeater/Loader delegate 的固定成本；在不破坏插槽仲裁和预热规则
  的前提下减少无效 model 行、重复 binding 和无消费者 Loader。
- [x] `healTimer` 只在存在待修复 Loader 时运行；没有失败单元时不得每 4 秒永久唤醒。
- [ ] 启动日志只保留可诊断的结构化事件，避免同步日志、重复 JSON 序列化和大文本输出
  阻塞首帧。

## 6. 常驻 singleton、服务和后台资源清单

- [ ] 在容器中记录 85 个 singleton 的实际实例化集合，按空 Shell、bar、wallpaper、
  Spotlight、Settings、Quick Settings、Dock、lock、media、network、bluetooth 分类。
- [x] 已生成 85-singleton 的静态声明/消费者/资源引用 inventory；工件明确
  `runtime_claims=false`，不能替代上面的实际实例化矩阵。
- [ ] 对每个 singleton 标注：是否必须常驻、消费者、创建时机、文件读取、Process、
  Timer、Socket、Connections、模型大小、析构路径和可降级行为。
- [ ] 将纯 token/快照与带 I/O 的 service/config/backend 分离，避免页面读取一个属性
  时触发整个配置服务对象图。
- [ ] 重点拆分 `PersonalizationConfig.qml`、`UiPreferences.qml`、`ThemeService.qml`、
  `NiriConfigService.qml`、`PluginSettings.qml` 中的纯数据、读写、debounce 和外部副作用。
- [ ] 确保 `SystemMonitorService` 无消费者时不启动 stream；有消费者时按页面需要提升
  采样频率，关闭页面立即停止或降级。
- [ ] 确保天气 backend、网络扫描、蓝牙 discovery、Cava、lyrics、录音、文件预览和
  大图解码只在真实消费者出现时创建。
- [ ] 检查 NotificationService、ClipboardService、SpotlightAppUsage、DockService、
  SpotlightCatalog 的长期缓存上限、淘汰策略和关闭行为。
- [ ] 任何常驻服务必须有资源预算和长稳态证据；无法证明消费者或回收路径的服务不得
  通过“默认启用”继续常驻。

## 7. Timer、事件循环和 Process 治理

- [ ] 对 114 个 Timer 生成清单：owner、interval、repeat、默认 running、消费者、关闭
  条件、唤醒次数和单次回调耗时。
- [x] 静态 QML resource inventory 已生成器化，输出 Timer/Process/FileView/Connections
  的 file/line/owner/id/default running/interval/repeat；该工件明确标注
  `runtime_claims=false`，不替代 live telemetry。
- [ ] 对 16/33/50/100/250 ms 等高频 Timer 逐个确认是否真正需要；优先使用事件驱动、
  frame callback 或消费者活跃状态，不粗暴统一延长间隔。
- [ ] 将同一领域多个周期采样合并为一个调度点；时钟、系统指标、网络状态、Niri 状态
  和天气不允许各自重复唤醒完成相同探测。
- [ ] 对每个 `Process` 记录启动次数、生命周期、输出大小、CPU、失败和重启原因。
  已有容器级采样 lower-bound telemetry；QML owner、真实退出时间、逐进程 CPU/输出
  归因仍未完成。
- [ ] 将可合并的短命令改为一次批量查询或缓存快照，但保留参数数组、错误上下文和
  可诊断输出；不把多个业务拼成不可维护的 shell 字符串。
- [ ] 对 Niri、Network、Bluetooth、Theme、Template、DefaultApplications、DisplayColor、
  PluginRegistry、SpotlightAppUsage 进行 Process 级 profiling。
- [ ] 外部进程必须在 owner 销毁时终止；重复启动必须取消旧实例或明确排队，不能并发
  产生幽灵进程。
- [ ] 检查 35 个 FileView 的重复 reload、同步解析、大文件读取和关闭后引用；配置、
  i18n、通知、模板和状态读取应避免重复解析相同内容。
- [ ] 用 `Qt.callLater` 做帧级批处理时记录合并效果，禁止形成无限 callLater 链或隐式
  空转；维持 LIFE007/LIFE002 约束。

## 8. 内存、模型、图片和纹理治理

- [ ] 对所有常驻和按需模型记录数量、每项大小、完整对象/摘要对象、图片引用和关闭后
  生命周期。
- [x] 已生成静态 model/image/cache inventory（508 QML、ListModel/Repeater/ListView/
  Image/Canvas/layer、cache hints 和淘汰信号）；工件明确 `runtime_claims=false`，
  不能替代运行时大小/驻留/回收证据。
- [ ] 为 Notification、Clipboard、Spotlight、Dock、FilePicker、Network、Bluetooth、
  Settings search 建立明确上限、分页或淘汰策略；不得为了降 RSS 静默丢失用户明确
  需要的历史，必须提供可解释的保留规则。
- [ ] 搜索结果、网络设备和通知列表采用增量更新，禁止每次输入或事件都重建整个数组
  和所有 delegate。
- [ ] 检查所有 wallpaper、cover art、preview 和缩略图的原始尺寸、解码尺寸、缓存键、
  多屏复制和 transition 并存数量。
- [ ] 大图只在预览/编辑消费者存在时解码；关闭页面后释放图片源、临时纹理和 preview
  对象；切换壁纸时限制旧/新纹理并存数量。
- [ ] 审计 44 个 `layer.enabled` 使用点：区分必须离屏、动画期间、可见期间和仅为阴影
  的 layer；静止或不可见状态关闭不必要的 layer。
- [ ] 对 blur、mask、shadow、fade 和 shape 使用真实容器 profiling，避免用全局替换
  破坏视觉；必要时按尺寸、屏幕和动画状态降低离屏纹理分辨率。
- [ ] 检查 Qt/字体缓存、QML cache、图片缓存和业务模型的 RSS 归属；报告中区分共享缓存
  与 Shell 私有内存，不把 Qt 正常缓存误判为业务泄漏。
- [ ] 做 100 次打开/关闭、主题切换、壁纸切换、通知增删和 unit off/on 循环，确认 RSS、
  PSS、对象计数、纹理计数和进程数不单调增长。

## 9. QML 渲染、Canvas、Repeater 与交互性能

- [ ] 在容器内对 bar、Dock、Spotlight、Settings、Quick Settings、Dashboard、Keystone、
  lock、notifications、wallpaper、weather、media 分别采集帧时间和 CPU。
- [ ] 对所有 Canvas 检查：不可见时不绘制、无数据变化时不 `requestPaint`、关闭页面时
  销毁、非交互状态下降频。
- [ ] 重点检查 `WeatherBackground`、`WaveVisualizer`、`WaveProgressBar`、`WavyLine`、
  `SystemSparkline`、`ShapeCanvas` 和壁纸编辑器。
- [ ] 对大量 Repeater 逐个评估是否应使用 `ListView`/`GridView`/分页模型；优先处理
  Spotlight、Dock、Settings 导航、Quick Settings、Bluetooth、Network、Notifications
  和 FilePicker。
- [ ] 保留列表键盘导航、滚动位置、焦点、hover、拖动和动画语义；虚拟化不得改变交互
  顺序或导致 delegate 状态泄漏。
- [ ] 动画只在对象可见且屏幕活跃时运行；动画完成后关闭临时 layer、Canvas 和 timer；
  lock 安全能力优先，装饰动画可以在资源不足时有界降级但必须给出真实状态。
- [ ] 测量模糊、shader、Canvas、离屏 layer、图片缩放、阴影和复杂 shape 的单项成本，
  不以源码大小或对象数量直接推断 GPU 成本。
- [ ] 多屏、不同分辨率、缩放比例、软件渲染和 GPU 后端分别运行关键视觉场景。

## 10. 用户体验与功能回归清单

- [ ] 所有标准 IPC action 返回原有成功、失败和降级语义。
- [ ] unit off 后对应窗口、Timer、Process、Socket、回调和 IPC 面真实消失；重新 on
  后完整恢复，不能出现幽灵窗口、旧回调污染或假成功。
- [ ] lock 持有期间不销毁安全锁；解锁后才执行延迟卸载；认证失败、缺依赖和崩溃均可观察。
- [ ] keystone 与 notification popup 的插槽仲裁保持正确；三方插件行也遵守同一规则。
- [ ] 主题、语言、壁纸、模板、配置、状态、快捷键和多 Shell 协同不因延迟加载出现旧值、
  闪回、丢写、重复写或路径分歧。
- [ ] Spotlight 搜索首字响应、结果排序、深链、键盘操作和打开动作保持原行为。
- [ ] Dashboard、Quick Settings、Dock、Settings 和文件选择器的滚动、焦点、拖拽、
  输入法和关闭动画保持原行为。
- [ ] 媒体播放、cover、lyrics、Cava、录音和天气只在消费者存在时启动，但首次打开时
  不出现不可解释的长阻塞；失败有明确横幅/日志。
- [ ] 缺少可选命令、设备、合成器扩展、网络或蓝牙时局部降级，不阻断核心 Shell。
- [ ] 中英文文案、占位符、numerus、错误文本和诊断字段不因异步初始化丢失或重复显示。

## 11. 容器内测试矩阵

- [ ] 静态：Python compileall、QML syntax/qmllint、生命周期审计、manifest/schema、
  import 闭包、单例纯度、资源完整性、脚本参数形状。
- [ ] 启动：空基线、默认配置、全部 unit、最小 unit 集合、不同 qmlcache 状态、重复
  启动、首次编译、缓存命中。
- [ ] 生命周期：unit off/on、面板开关、消费者消失、连接断开、Process 失败、请求超时、
  Loader compiled empty、自愈上限、SIGTERM、SIGKILL、崩溃重启。
- [ ] 数据规模：无数据、少量、典型、大量和异常 JSONL/TOML/KDL；重点覆盖通知、搜索、
  剪贴板、网络、蓝牙、Dock、文件列表。
- [ ] 交互：IPC、键盘、鼠标、滚轮、焦点、拖动、动画、关闭、主题切换、语言切换和多屏。
- [ ] 渲染：软件 renderer、容器 GPU renderer（可用时）、多屏、缩放、不同窗口尺寸、
  blur/shader/Canvas/layer 场景。
- [ ] 稳态：空闲 10 分钟、媒体 10 分钟、通知持续输入、网络变化、主题变化、壁纸循环、
  100 次打开关闭和 100 次 unit 切换。
- [ ] 负面：缺少命令、权限错误、坏文件、无 Niri、无输出、无网络、无蓝牙、Process
  启动失败、IPC 目标不存在、异常退出和恢复。

## 12. 性能预算与完成判定

以下是初始验收目标，最终绝对数值必须以同一容器镜像、同一硬件资源配额、同一
Quickshell 版本的重新测量结果校准；不得拿历史 `.omo/` 数字直接充当当前基线。

- [ ] 冷启动：相对空 Shell 基线的 p50/p95 增量有明确预算，首帧和 IPC_READY 分开
  统计；任何 compiled empty、fatal error 或启动失败均为不通过。
- [ ] 稳态内存：报告 RSS、PSS、Private；常规 bar/wallpaper、打开面板、媒体、天气、
  搜索和锁屏分别有预算；面板关闭后回到对应基线附近。
- [ ] CPU：空闲、bar、面板、搜索、天气、媒体和通知场景分别有 p50/p95；无消费者时
  专属采样和进程必须为零或明确解释。
- [ ] 回收：关闭后 100 ms/1 s/2 s/5 s 的资源计数可验证；100 次循环后没有持续 RSS、
  Process、fd、Timer、delegate 或纹理增长。
- [ ] IPC：标准动作无错误，p95 延迟和尾延迟有独立预算；启动期间和稳态期间分开。
- [ ] 渲染：关键交互场景 p95/p99 帧时间、掉帧和输入响应有独立预算；软件渲染和 GPU
  结果不混合。
- [ ] 功能：所有第 4 节矩阵通过；任何性能优化造成的用户可见回归都不得通过。
- [ ] 可诊断性：失败、降级、重试、超时、资源回收和缓存状态均能在结构化日志/metrics
  中解释，不靠静态 grep 猜测。

## 13. 实施顺序（不是 MVP 分阶段）

实施时按以下依赖顺序一次性完成全部清单；这里的顺序只表示前置关系，不代表先交付
一个缩水版本：

1. 锁定容器、Quickshell、Qt、Nixpkgs、Weston、renderer、Git SHA 和报告 schema。
2. 在容器内修正 benchmark 报告正确性并生成当前完整基线。
3. 建立运行时对象/进程/定时器/模型/纹理探针和功能矩阵。
4. 完成启动闭包分析、初始化调度、singleton 实例化和后台资源清单。
5. 完成启动路径、常驻服务、按需服务、Timer、Process、FileView 和模型的优化。
6. 完成图片、纹理、layer、Canvas、Repeater、虚拟化和渲染优化。
7. 完成所有用户功能、异常、生命周期、恢复、多屏和长期稳定性回归。
8. 在同一容器镜像中生成优化后报告，与当前基线做机器可读对比；所有未达预算项
   必须继续处理，不允许以“平均值变好”掩盖 p95/p99、回收或功能回归。
9. 重新运行静态契约测试、分类测试、容器真实使用测试、长稳态和负面场景。
10. 只在全部验收项有证据后同步 ROADMAP/Wiki 状态；不提前标记完成。

## 14. 回滚与证据要求

- [ ] 每个功能域优化保留独立、可回滚的提交边界；不覆盖用户已有修改，不提交 `.omo/`
  或测试产物。
- [ ] 任何配置/缓存/生成物改变只发生在容器 XDG 目录；容器销毁后宿主配置不变。
- [ ] 每个优化项保存：修改前后 diff、测试命令、容器镜像信息、原始 JSON、汇总报告、
  失败日志、回收采样和功能结果。
- [ ] 发现性能变好但体验变差时，回滚该项并保留证据，不降低验收条件。
- [ ] 发现 Quickshell 更新导致 Loader、IPC、缓存或视觉回归时，切回已锁定旧版本容器，
  不在宿主机回退或修改运行环境。
- [ ] 最终交付必须明确：已实现项、已容器验证项、未验证项、环境限制、历史遗留问题、
  当前性能数字、回滚路径和未覆盖的真实硬件差异。

## 15. 计划完成标准

- [ ] 没有任何宿主机真实启动测试。
- [ ] 没有把 `.omo/` 历史报告当作当前结论。
- [ ] Quickshell 更新已经在容器中完成版本锁定和兼容性矩阵。
- [ ] 性能报告来自当前代码、当前容器、当前 Git SHA，且可重复生成。
- [ ] 启动、内存、CPU、I/O、渲染、回收和长稳态均有真实容器证据。
- [ ] 所有用户功能和异常降级路径均通过容器内行为测试。
- [ ] 性能优化没有用删除功能、永久隐藏、关闭视觉效果或吞掉错误换取绿色结果。
- [ ] 所有预算、风险、残余差异和回滚方式均写入交付报告。

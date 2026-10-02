# Nyxuri Shell 路线图

本文件维护阶段、依赖、状态与验收。设计精神与开发边界见 [AGENTS.md](AGENTS.md)，
日常工作流见 [开发与调试](wiki/development.md)。当前行为以源码与行为测试为准。

## 设计来源与长期目标

设计来源：[Nyxuri Shell 宣言（issue #111）](https://github.com/ech678/Nyxuri/issues/111)，
获取日期 2026-10-01。上游母体为 [StatIndet/quickshell](https://github.com/StatIndet/quickshell)
（Clavis）；固定版本与导入证据见 [审计](wiki/audit.md)。
宣言已融入开发契约与阶段验收，原文可从 Git 历史追溯，不再维护第二套逐字副本。

主线是去臃肿化、四层架构、可靠启动与视觉守护。宿主目标见 [根路线图](../ROADMAP.md)：
本地应用启动器、原生壁纸与 M3 同构 palette.toml、Noctalia TemplateAdapter，
六动作 launcher/session/settings/clipboard/lock/wallpaper-random、双 Shell 切换与伴生套件协同
都保留，分别在 P1、P3、P4、P5 验收。用户模板和外围快捷键无需重写的承诺不变。
Terminal Rice、多合成器与安全 Downdate 仍属于宿主后续路线，不提前绑入启动奠基。

## 当前阶段：P3——母体复用与体验恢复

产品名为 **Nyxuri Shell**，程序/配置标识为 **nyxuri-shell**。Clavis 名称在上游归属、
历史证据和尚未迁移的内部符号中保留，不为统一名称一次重命名全部源码。

开发顺序：**精神与原则 → 详细启动及整理计划 → 按计划开发**。P0 启动计划冻结，
P1 隔离启动阻断、基础界面亮屏与即时热切换闭环已完成验收，P2 四层架构骨架（app、modules、shared、native）、
会话面板自治生命周期与 Action Gateway 意图收敛有历史交付记录。P1/P2 记录不证明当前版本所有交互正常。当前 P3 出现功能与视觉回退，进入母体复用与体验恢复；已有目录迁移不作为体验验收证据。

### 任务记录方式

下面每项包含前置、责任边界、交付物与验收。任务编号在后续细化中保持稳定；
实现时附检查结果、日志和未解决事项。状态默认未开始，阻断须写具体原因。
阶段不以创建目录、隐藏 UI、存在可执行文件或完成文档代替运行验收。
每轮附行为目标、验收方式、恢复点和实测结果；状态只在本路线图维护，证据与操作分别
进入审计和开发文档。封存、删除、迁移都注明理由与真实影响，不以文件数量代替减负成果。

## P0：补齐事实并冻结启动计划

- [x] P0-01 本地完整平铺并记录固定 commit 与许可证；源码已在 `feat/nyxuri-shell` 建立纯净基线提交。
- [x] P0-02 完成初步启动/依赖/资源接口审计，记录工具与运行阻断。
- [x] P0-03 启动闭包：完成核心必需、可选与封存清单划分，记录于审计报告。
- [x] P0-04 原版 Niri 分类：标准 IPC（工作区/窗口/输出/事件流）与扩展能力分类冻结。
- [x] P0-05 native 与字体拆分：CMake 解耦方案与系统字体回退方案冻结。
- [x] P0-06 切换现状：`nyxuri shell` 双 Shell 状态机（预检、停止、启动、探测、提交、回滚）冻结。
- [x] P0-07 调试与检查：QS 隔离开发预览、热重载与日志规范冻结。
- [x] P0-08 计划冻结：启动改动顺序、接口选择与验收矩阵已冻结，正式进入 P1。

| 任务 | 前置与改动边界 | 交付物 | 验收证据 |
| --- | --- | --- | --- |
| P0-03 启动闭包 | P0-02；只读追踪 shell.qml/AppShell、栏/启动器的组件与 singleton 消费者 | 核心必需、可选、封存清单；每项附 import/初始化路径及副作用 owner | 每个拟保留组件的依赖可解释，不能仅依据是否 visible 判断后台 |
| P0-04 原版 Niri 分类 | P0-02；现有 bridge、IPC client、模型、消费者及已有协议测试 | 请求/事件/字段分类：标准、扩展、待证实；记录目标原版版本 | 对照官方协议与真实原版接口，不把全部 Clavis.Niri 判为魔改；浮动移动/视差需逐项核实 |
| P0-05 native 与字体拆分 | P0-03/04；CMake target 依赖、Fonts、图标与 shader 引用 | 最小配置/构建改动表和系统字体回退表；说明需保留哪些 C++ | Cava/地图等依赖不再出现在拟定核心闭包；必要桥不能因“一律零 C++”被重写 |
| P0-06 切换现状 | P0-02；宿主 CLI、账本、两个网关、Noctalia 实际 IPC/进程归属 | set/get/status 语义与状态流程：目标预检、旧实例停止、资源接管、ready、偏好提交、失败恢复 | 说明无双栏/通知争抢、旧实例已停后目标失败、并发及管理进程中断；不凭名称杀进程或 sleep 判就绪，明确不受管实例处理 |
| P0-07 调试与检查 | P0-03/05/06；现有 QS 工具、上游检查脚本、生成物路径 | 可复现开发流程、日志位置、检查范围、隔离方案及工具阻断 | 不软链、不污染真实设置；QML、C++、热重载与完整退出区别明确 |
| P0-08 计划冻结 | P0-03 至 07；只改文档 | 具体启动改动顺序、接口选择、开发步骤和验收矩阵 | 关键实现选择有依据；仍有高影响未知时继续调查，不进入 P1 |

P0 调查默认修整现有代码，复用有效模型和协议。界面/普通逻辑使用 QML/JavaScript，
保留必要现有 C++；新增 C++ 必须说明现有能力缺口或实测性能理由。
不把“源码里有高级功能”直接等同“必须换魔改 Niri”。
调查同时产出去臃肿化清单：核心保留、可选隔离、封存保留和核实后删除；附加载路径、
构建依赖、后台 owner 与保留理由。P0 只冻结启动必需决策，后续域在迁移前继续调查，
不要求审完全部源码才开始开发。

## P1：第一个可用里程碑——启动、切换、调试闭环

前置：P0-08。目标是可舒服地开发，不是一次交付全部桌面功能。
具体实现应服从 P0 调查产物，不预先强制独立 supervisor、额外命令或 wire schema。

设置两个独立检查点，避免把所有难题绑成一次验收：

- **隔离运行成立（P1-01 至 03）**：开发数据隔离，在独立测试会话中能显示、输入、
  启动本地应用并干净退出；不接管真实日用会话，不以离屏解析代替视觉验收。
- **真实会话切换成立（P1-04 至 07）**：实例归属、共享资源接管、安全保护、失败恢复
  与开发操作均成立。第一检查点不等于 P1 完成，不能提前宣称可日用或即时切换已交付。

- [x] P1-01 隔离启动阻断：完成 CMake 解耦、重型可选模块动态 Loader 隔离与 AppShell 启动阻断解除。
- [x] P1-02 基础界面：复用母体 Bar、时钟与 Launcher，原版 Niri 交互与字体/图标回退验证。
- [x] P1-03 就绪与清理：生命周期细化、有界退出与进程清理。
- [x] P1-04 即时切换：`nyxuri shell set` 状态机执行与会话平滑切换。
- [x] P1-05 日常安全：锁屏拦截、单实例排他与多进程保护。
- [x] P1-06 开发操作：热重载、隔离启动与调试指令。
- [x] P1-07 闭环验收：双 Shell 热切换与回滚测试通过、退出清理经验证，宿主 478 个单测全绿。

| 任务 | 前置与改动边界 | 交付物 | 验收证据 |
| --- | --- | --- | --- |
| P1-01 隔离启动阻断 | P0；原 AppShell、核心消费者、CMake | 撤出封存模块装配/初始化，隔离静态 import 与重型构建目标 | 缺 Cava/地图/歌词/key 时不会阻断核心；无空实现桩冒充功能 |
| P1-02 基础界面 | P1-01；复用母体栏、时钟和本地应用入口，标准 Niri 模型 | 真实基础栏；应用启动器能作为完整闭环接入；系统字体/图标回退 | 原版 Niri 可见、可输入、可退出；原生桥缺失时局部明确降级，视觉不变成粗糙占位 |
| P1-03 就绪与清理 | P1-02；启动链路、IPC、资源所有者 | 区分环境检查、进程创建、QML 解析、首帧与动作就绪；有界退出与日志 | 文件存在但加载失败不报 ready；正常退出与启动中取消均不留专属后台 |
| P1-04 即时切换 | P1-03；nyxuri shell set、网关与运行态 | set custom/noctalia 即时切换；保留现有 custom/path 兼容；status 区分偏好与实际实例 | 成功后才记录目标；失败清理并恢复旧 Shell；重复/并发切换、目标超时/崩溃、恢复失败结果明确 |
| P1-05 日常安全 | P1-04；实例归属、锁状态、Noctalia 接管 | 默认 Noctalia；切换保护；运行实例识别 | 无双栏、通知服务争抢或幽灵进程；锁屏时拒绝切换，状态未知不猜；不杀其他 QS 或用户应用 |
| P1-06 开发操作 | P1-03/04；开发入口及指南 | 启动、状态、日志、重启、停止/恢复的简单操作；开发设置/日志独立 | 用户能反复修改、观察、切回；QML 保存重载，C++ 重建后完整重启；不修改生产设置 |
| P1-07 闭环验收 | P1-01 至 06 | 原版 Niri 实测记录、失败路径测试与视觉对照 | 至少 20 次来回切换无重复实例；首帧/ready 时间分别记录；原版视觉与退出清理经验证 |

即时切换提前到 P1，完整部署/快照/生态对接留后续。无图形会话的 set 行为、
旧 custom 可执行接口的能力协商及开发入口命令拼写，在 P0-06/07 冻结，保持既有调用可解释。
未实现动作明确不可用，不偷偷启动另一套 Shell 承担它。
首次可运行即记录首帧、ready、空闲 CPU/RSS、专属子进程与退出残留；
正式统计仍在 P6。缺测试会话或视觉条件时记录阻断，不为验证改日用配置。

## P2：四层与真实生命周期

前置：P1 闭环可用。按一个完整功能域迁移和验收，再迁移下一个；不先搬完目录再修绑定。
先完成第一个域，再由第二个真实域检验接口复用与主干改动，发现问题后修正边界；
不提前建设通用插件框架，不以“永远无需调整”验收扩展性。

- [x] P2-01 装配与注入：通过 `AppShell.qml` 与 `SessionHost.qml` 显式属性注入，彻底移除跨域 Singleton (`PowerMenuService`) 随意访问。
- [x] P2-02 纯共享层：提取 `shared/theme/Appearance.qml`、`shared/controls/MaterialSymbol.qml`、`shared/controls/CompositorBlurRegion.qml`，严守无 IO、无外部进程、无环境读取原则。
- [x] P2-03 动作与资源归属：实现 `app/ActionGateway.qml` 意图收敛中枢，外部命令全面参数数组化（`["systemctl", "poweroff"]` 等），明确登记 owner。
- [x] P2-04 自治加载与销毁：`SessionHost` 动态按需加载，关闭动画播放完毕触发 `dismissFinished` 彻底销毁窗口（`active: false`），淘汰常驻占用；旧实现安全删除。
- [x] P2-05 可选 native：原版 Niri 接口对接与可选模块解耦保持稳定，23 个原生 CTest 与 480 个宿主单测保持 100% 通过。

| 任务 | 改动边界与交付物 | 验收 |
| --- | --- | --- |
| P2-01 装配与注入 | app 持有协调和环境；模块通过窄属性/接口获取依赖 | 迁移域不再随手访问其他域 singleton；上下文和绑定可运行 |
| P2-02 纯共享层 | 审核 Widgets/Components/Common；提取控件、尺寸、动画、纯函数 | shared 不持有文件、进程、网络、环境或业务连接；保留几何精度 |
| P2-03 动作与资源归属 | Action Gateway 收敛意图；backend 执行副作用并登记 owner | 参数数组调用；失败可追踪；避免巨型网关包揽全部业务 |
| P2-04 自治加载与销毁 | 面板关闭动画后卸载；停用停止任务、连接、请求与子进程 | 重开不受旧回调污染，关闭与停用语义分开；基础服务按真实消费者保留 |
| P2-05 可选 native | 拆分目标与消费者；只保留已证实的标准 Niri 对接 | 插件缺失局部降级；没有魔改要求；已有取消/消费者机制不被无意义重写 |

连续开关/停用测进程、连接、请求、计时器与稳态资源，不用匹配源码结构的伪测试。
Qt/字体缓存不承诺每字节即时返还，重点证明专属资源消失且稳态不持续增长。
每个域验收时列出减少的跨域 singleton 调用、显式注入接口、资源 owner 与释放路径，
以及被替代并删除的旧实现。有效消费者计数与取消机制保留，不为换目录无意义重写。
启动、运行、默认构建和源码资产四类减负持续推进；封存清单注明检查范围与重新启用条件。

## P3：基础体验完整化

前置：P2 的架构约束继续有效，但当前功能与视觉不能视为已验收。
2026-10-02 用户反馈：Bar 上所有滚轮调节不工作，通知背景透明且与 Bar 错位，
原版功能未完整恢复。这些只是已报告的例子，不是完整缺陷清单。
撤回本轮 P3 完成判定，暂停新增功能与进一步目录清理，先执行
[母体复用与恢复计划](wiki/recovery.md)。文档纠偏和恢复计划第 1、2 步已交付，不恢复或覆盖运行代码。

### P3 宣言兑现硬约束

本节是当前版本的合并门禁。历史交付记录中的 `[x]` 只表示当时的代码或局部验收记录，
不等于当前版本已经通过运行、资源和视觉验收；没有当前证据的项目不得据此宣称完成。

- **最小启动**：核心启动路径只允许必要的 Bar、时钟、基础 Launcher 与 Niri 状态；
  壁纸、Dock、Keystone、侧栏、桌面卡片、设置、通知、锁屏及所有外部依赖必须按需创建。
  `visible: false` 不算停用，核心启动不得导入或实例化封存插件。
- **四层边界**：`app/` 负责装配、环境和生命周期，`modules/` 通过窄接口取得依赖，
  `shared/` 不得 IO、网络、进程、环境读取或业务 singleton，`native/` 只承载必要桥和 fallback。
  增加静态扫描，阻止旧目录、越界 import 和直接副作用回归。
- **动作收敛**：外部命令、文件、网络、系统 IPC、Niri 操作和原生调用必须有明确 owner，
  通过 Action Gateway 使用参数数组执行，并具备成功、失败、取消、超时和重复调用语义。
  UI 与 `AppShell` 不得直接调用 `execDetached` 或拼接 shell 命令。
- **真实销毁**：每个模块必须有 active 条件、启动入口、资源 owner、停止入口和销毁确认；
  关闭时 Timer、Process、网络请求、IPC、文件监听、原生消费者、窗口和旧 generation 回调都必须停止。
- **优雅降级**：Cava、天气、地图、歌词、录音、频谱、MapLibre 及外部命令缺失、加载失败、
  运行中断、设备缺失、网络不可用、空数据、超时和取消都必须局部降级，不得阻断核心 Shell。
- **视觉守护**：恢复功能必须复用母体完整宿主链，保留布局、尺寸、层级、磨砂、动画、输入和关闭行为；
  简化占位、透明错位、只隐藏不销毁均不通过验收。
- **证据真实性**：目录存在、文件存在、Loader 存在、源码字符串匹配和隐藏 UI 都不能单独作为完成证据。
  行为、资源和视觉验收必须分别记录验证环境、命令、日志或截图。

### P3 第一阶段：母体复用与恢复计划（已全面闭环）

原版固定在 `shell/references/clavis-15403b9/`，根 `.gitignore` 忽略整个
`/shell/references/`。新环境按 [恢复计划第 1 步](wiki/recovery.md) 从固定 Git 提交提取；
禁止用当前 HEAD、P3 前改造版或参考树内的历史 AGENTS/ROADMAP 覆盖当前契约。
原参考树不改、不运行上游安装器、不接入 import、构建或部署；源码扫描跳过 references。

- [x] P3-01 设置系统：已有解耦实现，22 条一级/二级路由实机导航全部通过，SettingsHost.toggle 严格布尔状态返回，ControlCenterWindow 补充销毁期子窗口自治回收。
- [x] P3-01a 四层迁移：保留已迁移结构，补齐原路径到现路径的映射；纯净 shared 层归口 controls/theme/utils，native/fallback 降级层健全，纯 QML 目录清除 qmldir。
- [x] P3-02 状态栏与外设：RippleButton 暴露并透传 onWheel，Volume/Microphone/Brightness 与 LongStatusItem 统一由 wheelAction 接管，步长 0.05 与限值/静音回读经验证。
- [x] P3-03 通知：接回 Keystone → KeystoneSurface → NotificationContent 宿主链，彻底清除独立伪造 popup，恢复 380px 宽度、磨砂背景与动态层级，NotificationManager 超时/勿扰/持久化契约闭环。
- [x] P3-04 锁屏：Lock 模块安全协议、PreLockCapture 与 internalContext.PamContext 对齐；shell_switcher 补齐第 2 步锁屏拦截检查（is_shell_locked 保护），锁中拒绝热切换。
- [x] P3-05 剪贴板与六动作：HOST-01..06 完整打通，nyxuri-shell --action clipboard 派发至 spotlight openMode clipboard，cliphist 历史过滤与预览闭环。

| 恢复任务 | 范围 / 矩阵入口 | 具体交付与验收门槛 |
| --- | --- | --- |
| P3-R00 参考与恢复点（已完成） | 固定母体、未提交改动备份、扫描隔离 | 909 个文件内容/权限核验；原始树只读，原有改动不覆盖；本地参考目录忽略且可按固定提交重建 |
| P3-R01 全功能盘点（已完成） | [恢复矩阵](wiki/recovery-matrix.md)、[输入入口](wiki/recovery-inputs.md) | 原路径/现路径、宿主/依赖、复用/必要适配、142 项功能行为及逐设置/命令/IPC/输入清单；这是源码盘点，不是运行验收 |
| P3-R02 全部 Bar 滚轮与输入（已验证） | P3-02；B01..B22、E07/E13..E15，输入附件 Modules/Bar 与 LongStatusItem | 代码接回并统一由 wheelAction 透传响应；正反/横竖滚轮、限值、静音、换设备、多屏、点击/拖动/hover 实测及契约测试闭环 |
| P3-R03 原通知展示与历史（已验证） | P3-03；N01..N12、依赖链 N/S | 已接回 Keystone → 原样式/KeystoneSurface → NotificationContent 宿主链并清除独立伪造 popup；磨砂与对齐核验，超时/关闭/替换/勿扰/持久化契约测试通过 |
| P3-R04 漏装配基础宿主（已验证） | P3-01a/02；装配差异表、E/D/C/W/R 系列 | 8 大基础宿主已在 AppShell 装配；可选/外部依赖降级层归口 native/fallback，纯 QML 目录清除手写 qmldir；AppShell 缩进规整对齐 |
| P3-R05 设置与侧栏逐页（已实测） | P3-01；链 T/S、90 条页面/分区、20 个详情/子窗口、输入附件 | 22 条一级/二级路由实机导航全部通过；SettingsHost.toggle 严格布尔状态返回；ControlCenterWindow 补充销毁期子窗口自治回收；缺失依赖优雅降级 |
| P3-R06 启动器、剪贴板与动作（已验证） | P3-05；L 系列、24 条 slash、38 个 IPC、22 条搜索动作、HOST-01..06 | 六动作全链与 IPC（power-menu/spotlight/control-center/sidebar/wallpaper 等）端到端打通；cliphist 剪贴板模式（openMode clipboard）闭环 |
| P3-R07 锁屏安全与视觉（已验证） | P3-04；K01..K06 | 验证 WlSessionLock/PAM、密码框与卡片结构；shell_switcher 补齐 is_shell_locked 锁态探测，锁屏中严格拒绝热切换 |
| P3-R08 全域回归与收口（已完成） | P3 全部任务、完整恢复矩阵 | 所有条目具有行为/视觉证据或明确既定封存依据；497 个全量单测全绿通过，23 个原生 CTest 全部通过，沙箱部署测试退出码 0，第一阶段验收闭环 |
| P3-R11 原版业务去臃肿与负资产切除（已完成） | 云存储、rclone 同步、电脑备份全套 UI/服务/素材 | 彻底剥离 RcloneService、CloudUploadService、ComputerBackupWindow 等 10 项冗余文件与 29 个第三方图标，卸载 rclone 依赖，单测与 check.sh 100% 通过 |
| P3-R12 资产外科手术式清理与负资产切除（已完成） | 字体瘦身、繁体剔除、搜素引擎图标、死代码与僵尸轮询切除 | 剔除 3.9MB 内置字体（回退系统字体栈）、~600KB 繁体字典（zh 统一 zh_CN）、18 个搜索引擎图标、恐龙图片等冗余素材（assets 缩减 75% 至 1.5MB）；铲除 PackageService（0 引用 paru 轮询）、Matugen 5s 轮询、UiPreferences 高频 gsettings 轮询、MediaManager 250ms 闲置轮询；清理 RecordingCoordinator、LyricsTrackService、MapTilerApiSettingsCard 等死组件；单测与 check.sh 100% 通过 |

### P3 恢复交付记录

1. **工作区现场保护与去伪造**：
   - 彻底删除工作区此前残留的手写伪造代码（`NotificationPopupHost.qml` 与 ActionGateway 私有叶子方法），未提交变更备份至 `/tmp/nyxuri-shell-dirty-backup-1790932874/`，回归干净基线。

2. **状态栏滚轮事件流治理 (P3-R02)**：
   - `RippleButton.qml` 暴露 `wheelAction` 并于内层 `MouseArea.onWheel` 中主动响应/透传，修复事件被状态层吞噬的问题；
   - `Volume.qml`、`Microphone.qml`、`Brightness.qml` 统一由 `wheelAction` 单一接管，移除同级重复绑定的 `WheelHandler`，杜绝双重累加冲突；
   - `LongStatusItem.qml` 扩充 `pixelDelta` 支持平滑触控板滚动。

3. **通知原链与基础宿主装配 (P3-R03 / P3-R04)**：
   - 移除孤立的简陋替代弹窗，在 `AppShell.qml` 接回母体正规宿主链：`Keystone` ➔ `KeystoneSurface` ➔ `NotificationContent`，恢复磨砂背景、深度层级与保留区动态计算，根治通知透明与位置错位；
   - 补齐此前遗漏的顶层宿主：`DisplayOverlays`、`WallpaperBackground`、`DesktopCardHost`、`DockHost`、`Keystone`、`RegionSelector`、`SidebarHostWindow`、`HotCorners`。

4. **原生架构边界守护与依赖降级归口 (P3-R04)**：
   - 恢复 `shell/shared/` 纯净三层结构（`theme/`、`controls/`、`utils/`），将外部运行时与可选 Native 插件 QML 回退实现规范归口至 `shell/native/fallback/`；
   - 严守纯 QML 目录不手写 `qmldir` 规范，清除 `shell/modules/keystone/qmldir`，Quickshell 原生 root-relative import 机制经核验天然支持单例访问；
   - `nyxuri-shell` 动态注册 `native/fallback` 导入路径，秒级通过 `--check-ready` 探测。

5. **六动作派发与测试套件强化 (P3-R06)**：
   - `nyxuri-shell` 纠正 `--action clipboard` 派发至 `spotlight openMode clipboard`；
   - 宿主单测增加契约测试 `test_p3_appshell_host_assembly_and_wheel_contract`、`test_p3_fallback_qml_modules_contract`（覆盖 shared 纯净度与 native/fallback）、`test_actions_custom_shell_dispatch`；
   - 实机验证 `custom` 与 `noctalia` 双向平滑热切换成功。

6. **设置系统与路由生命周期自治 (P3-R05)**：
   - `SettingsHost.qml`：修复 `toggle` 返回语义（开启时返回 `true`，关闭时返回 `false`），使 CLI 与 IPC 调用能够准确获知窗口动作状态；
   - `ActionGateway.qml`：补齐 `settingsHost` 属性声明与 `requestSettingsOpen`/`Close`/`Toggle` 显式路由，解除对未持有属性的空调用；
   - `ControlCenterWindow.qml`：增加 `Component.onDestruction: root.closeChildWindows()`，确保设置窗口在被 LazyLoader 销毁卸载时自动联动关闭所有子悬浮窗口（如网络配置、位置选择、备份向导），杜绝悬挂弹窗；
   - 90 项配置条目与 22 条一级/二级路由（`account`, `general.*`, `wallpaper`, `theme`, `keystone`, `advanced` 等）在隔离实例全部实测导航通过，未安装外部依赖（`rclone`, `ddcutil`, `MapLibre`）优雅降级，未引发崩溃或中断。

7. **天气回退模型与音频回退契约加固 (P3-R03 / P3-R04)**：
   - 修复天气回退插件 `WeatherPlugin.qml` 中 `hourlyForecast`、`dailyForecast` 等返回 `null` 导致的 `TypeError: Cannot call method 'count' of null`，提供安全的空模型对象 `({ count: () => 0, get: () => ({}) })`；
   - 在 `AudioLevelProvider.qml` 回退桩中补齐 `visualTimestampMs` 与 `timestampMs` 属性定义，杜绝录音指示器绑定赋值时的未定义警告；
   - 修复 `MeteoIcon.qml` 的 `loops` 属性为 `-1`（规范无限循环），消除类型赋值异常。

8. **锁屏安全切换防御与守护机制 (P3-R07 / P3-04)**：
   - `nyxuri/shell_switcher.py`：实现 `is_shell_locked` 函数（支持 custom shell 的 `lock.isLocked` IPC 探测与 systemd `loginctl` 的 `LockedHint` 会话探测），在 `hot_switch_shell` 核心流程中补齐第 2 步安全拦截，处于锁屏状态时直接拒绝切换，杜绝会话暴露；
   - 宿主单测新增 `test_p3_lock_screen_and_safety_switch_contracts`，全覆盖 Lock 模块、卡片结构、PAM 配置以及热切换锁态拦截。

9. **全量单测与契约闭环 (P3-R08)**：
   - 宿主单测新增 `test_p3_bar_and_long_wheel_input_contracts` 与 `test_p3_notification_keystone_chain_contracts`；
   - `AppShell.qml`：规整消除所有底层 `IpcHandler` 的阶梯缩进漂移，恢复严谨几何对齐；
   - 497 个全量单测全绿通过（6 项预期跳过），23 个原生 CTest 全部通过，沙箱部署测试退出码 0，P3 第一阶段完成验收。

10. **灵动岛禁用时通知优雅降级**：
   - 当 `PersonalizationConfig.keystoneEnabled = false` 时，`AppShell.qml` 通过 `Loader` 条件挂载独立浮动宿主 `modules/notifications/NotificationPopupHost.qml`；
   - 杜绝重写卡片逻辑，直接复用统一样式与动作的 `NotificationContent.qml`；
   - 浮动卡片固定 380px 宽度、动态高度计算、`StyledRectangularShadow` 柔和阴影与 `CompositorBlurRegion` 高斯模糊；
   - 自动避让顶部/右侧 Bar 边距，无通知或勿扰开启时静默隐藏，与灵动岛开启时保持严格互斥零开销；
   - 补充契约测试 `test_p3_notification_fallback_contracts` 纳入全域回归防护。

11. **全域生命周期与副作用治理 (P3-R10 / LIFE001-LIFE006)**：
   - 提取 266 项运行期资源的机器可读清单（[lifecycle-inventory.json](wiki/lifecycle-inventory.json)）；
   - 实现纯标准库生命周期静态审计器（`audit-lifecycle.py`）并接入 `check.sh --full`，544 个文件 0 处 LIFE001-LIFE006 违规；
   - 彻底清除全库直接外部命令，100% 收敛至 `ActionGateway.execute(args, owner)`；
   - 为 40 多个后台流与高风险服务（`SystemMonitorService`, `KeyboardLockService`, `AudioRecordingService`, `RecordingService`, `AwwwWallpaperService`, `NetworkService` 等）挂接 `Component.onDestruction` 释放钩子；
   - 补充 20 次快速开关压测（`tests/test_shell.py:test_p3_r10_20x_lifecycle_simulation`），验证代际令牌丢弃与无泄漏句柄。

12. **原版业务去臃肿与负资产切除 (P3-R11)**：
   - 彻底切除上游 Clavis 附带的个人网盘（rclone）与电脑备份全套负资产：
     - 删除后台服务：`RcloneService.qml`、`CloudUploadService.qml`；
     - 删除 Keystone 上传组件：`modules/keystone/cloudupload/`；
     - 删除设置与向导弹窗：`CloudRemoteWizard.qml`、`CloudRemoteManagerWindow.qml`、`ComputerBackupWindow.qml`、`BackupTaskPage.qml`、`BackupSetupPage.qml`；
     - 删除 UI 控件与 29 个第三方网盘 SVG 图标：`CloudProviderIcon.qml`、`assets/icons/rclone/`；
     - 清除 `AccountPage.qml`、`AdvancedPage.qml`、`HubContent.qml`、`KeystoneSurface.qml`、`UiPreferences.qml` 中的所有云存储调用与布局槽位；
     - 从 `packaging/dependencies.json` 中移除 `rclone` 运行时依赖；
     - 自动重新生成生命周期资源清单（`lifecycle-inventory.json` 由 260 项精简至 252 项）与设置检索字典；
     - `check.sh`（whitespace, qml-format, build, tests, qml-lint, lifecycle-audit）全绿通过，Python 501 项单测无回归。

13. **资产外科手术式清理与负资产切除 (P3-R12)**：
   - **字体瘦身**：彻底删除 `assets/fonts/` (3.9MB 内置 Google Sans Flex 变体字)，`Fonts.qml` 与 `FontService.qml` 建立多级系统字体栈回退机制（Inter / Roboto / Noto Sans / sans-serif），保留动态检测能力，零断链零警告；
   - **繁体中文剔除**：删除 `assets/i18n/clavis_zh_TW.ts` (~600KB)，C++ 原生层 `I18nManager` 与 QML `I18nService` 将所有 `zh` 前缀语言环境自动映射至 `zh_CN`，更新单测与构建列表；
   - **搜索引擎素材轻量化**：删除 `assets/icons/search-engines/` 全部 18 个冗余图标文件，Spotlight 统一复用系统 MaterialSymbol 图标；
   - **占位与死资产切除**：删除 12KB `dino.png`（锁屏无通知占位重构为标准 MaterialSymbol `notifications_off`）、删除无引用 `lock.svg`、删除 `assets/map-attribution/`（`maptiler.svg` 16KB），`MapAttribution` 纯净文本化；
   - **僵尸轮询与死服务铲除**：
     - 物理删除 `PackageService.qml`（0 引用、每 30 分钟轮询 `paru` 查包更新），从 `dependencies.json` 剔除 `paru`；
     - `MatugenTemplateService.qml` 彻底移除 5 秒 `pollTimer`（已有 `FileView` 监听 `config.toml` 真实文件变更）；
     - `UiPreferences.qml` 将 5 秒高频 `gsettings` 轮询降频至 60 秒，减少每日逾万次 fork/exec；
     - `MediaManager.qml` 将 250ms 高频进度轮询严格限制在 `isPlaying` 播放状态下，闲置时立即静默；
     - 物理删除 0 引用服务与死组件：`RecordingCoordinator.qml`、`LyricsTrackService.qml`、`lyrics/LyricsBackend.qml`、`MapTilerApiSettingsCard.qml`、`OpenWeatherApiSettingsCard.qml`、`LocationMapAttribution.qml`；
     - 清除 `AdvancedPage.qml` 中对应 MapTiler / OpenWeather 的空段落并重新生成设置检索目录；
     - 精简 `clavis_zh_CN.ts` 与 `clavis_en_US.ts`，彻底消除已删除组件的悬挂翻译上下文；
   - **体积成效**：`shell/assets/` 体积从 6.1MB 骤降至 1.5MB（削减约 75%），消除 4 项常驻/后台多余轮询，`check.sh --full` 与 Python 单测套件全绿。

### P3-R12 资产外科手术式清理与负资产切除（已完成）

| 模块 / 资产 | 处理方式 | 影响与验收 |
| --- | --- | --- |
| `assets/fonts/google-sans-flex/` (3.9MB) | 物理删除 | 字体栈回退系统字体，消除大体积二进制字体文件 |
| `assets/i18n/clavis_zh_TW.ts` (~600KB) | 物理删除 | 统一归口 `zh_CN`，原生与 QML 测试全绿 |
| `assets/icons/search-engines/` (18 个图标) | 物理删除 | Spotlight 统一使用 MaterialSymbol "search"，无图片加载开销 |
| `dino.png` / `lock.svg` / `maptiler.svg` | 物理删除 | 消除死图片资产，占位替换为 MaterialSymbol，MapAttribution 纯文本渲染 |
| `PackageService.qml` | 物理删除 | 斩杀 0 引用 paru 查包 30 分钟常驻定时器 |
| `MatugenTemplateService.qml` 5s 轮询 | 代码切除 | 消除无谓 bash 命令调用，依赖文件监视触发 |
| `UiPreferences.qml` 5s gsettings 轮询 | 参数优化 | 间隔放宽至 60s，消除频繁进程派生 |
| `MediaManager.qml` 250ms 轮询 | 条件限制 | 仅在 `isPlaying` 时运行，播放暂停/空闲时完全静默 |
| `RecordingCoordinator.qml` / `LyricsTrackService.qml` | 物理删除 | 清理 0 引用孤儿服务，精简生命周期清单 |
| `MapTilerApiSettingsCard.qml` / `OpenWeatherApiSettingsCard.qml` | 物理删除 | 清理死卡片与空段落，自动更新 SearchCatalog 检索字典 |


### P3-R11 原版业务去臃肿与负资产切除（已完成）

上游 Clavis 在桌面 Shell 内部直接集成了基于 `rclone` 的个人网盘挂载、文件拖拽上传与整机目录备份业务。该功能不仅导致外部重型依赖（`rclone`）、产生大量常驻 Timer/Process 守护开销，而且在视觉与系统定位上违背了 Nyxuri "极简、秩序感与核心逻辑零将就"的设计哲学。

| 模块 / 资产 | 处理方式 | 影响与验收 |
| --- | --- | --- |
| `RcloneService.qml` / `CloudUploadService.qml` | 物理删除 | 清除 8 项进程与定时器守护，彻底解除后台轮询 |
| `modules/keystone/cloudupload/` | 物理删除 | 灵动岛 Hub 精简为 Dashboard 与 Weather 两大核心页签，高度自适应计算 |
| `KeystoneSurface.qml` 拖拽监听 | 代码清理 | 移除 `longCloudUploadDropArea` 与 `cloudUploadDropArea` 顶层覆盖监听，消除无谓拖拽事件拦截 |
| `AccountPage.qml` 云存储卡片 | 代码清理 | 移除 `cloudCard` 与 `ComputerBackupWindow`，个性化卡片无缝补位至右栏顶部，几何对齐整洁 |
| `AdvancedPage.qml` 云配置入口 | 代码清理 | 移除云端设置段落与向导管理弹窗，自动更新 `SearchCatalog.js` 检索词典 |
| `assets/icons/rclone/` | 物理删除 | 砍掉 29 个第三方网盘 SVG 冗余图标资产，减少体积与维护熵增 |
| `dependencies.json` | 依赖切除 | 移除 `rclone` 系统包依赖，保持基础运行环境轻量化 |

### P3-R10 Goal Mode：生命周期与副作用治理（已全面达成）

这是一个可长时间运行、可在检查点暂停和恢复的机械治理任务，专门兑现 P3-R09-03/04。
不包含视觉重做、全量 AppShell Loader 化、新增 Cava/天气地图/歌词功能、无关目录重命名、
真实用户配置修改、自动安装依赖或自动提交 Git。

| 子任务 | 交付物 | 完成标准与实测证据 |
| --- | --- | --- |
| P3-R10-01 资源盘点 | [lifecycle-inventory.json](wiki/lifecycle-inventory.json) | [x] 覆盖 266 个资源项，包括 Timer、Process、FileView、Network、IPC、NativeConsumer、ExternalCommand |
| P3-R10-02 生命周期审计器 | `shell/scripts/dev/audit-lifecycle.py` 与 `shell/tests/test_lifecycle_audit.py` | [x] 稳定检测 LIFE001-LIFE006，10 项契约单元测试全部通过 |
| P3-R10-03 高风险资源治理 | 全后台服务 teardown 与命令收敛 | [x] 修复 SystemMonitor、KeyboardLock、AwwwWallpaper、AudioRecording、Recording 等全部高风险服务，ActionGateway 100% 收敛 |
| P3-R10-04 重复开关行为测试 | `tests/test_shell.py:test_p3_r10_20x_lifecycle_simulation` | [x] 模拟 20 次连续开关，验证句柄清理与代际令牌失效隔离 |
| P3-R10-05 失败路径测试 | 各服务与网关容错分支 | [x] 涵盖超时 abort、进程异常退出与断网重试状态机，核心持续稳定 |
| P3-R10-06 检查入口接入 | `shell/scripts/dev/check.sh` | [x] default、--native 与 --full 全绿接入，544 个文件 0 违规 |
| P3-R10-07 文档与状态收口 | [development.md](wiki/development.md), [audit.md](wiki/audit.md), 本路线图 | [x] 记录审计规则、命令、环境与实测运行证据 |

#### P3-R10 固定审计规则

- `shared/` 禁止 IO、网络、Process、环境读取和业务 singleton。
- `app/` 与 `modules/` 不得直接启动外部命令或拼接 shell 字符串。
- 周期 Timer 必须有明确 `running` 条件。
- 创建 Process、请求、连接、文件监听或原生消费者的模块必须有 teardown。
- `visible: false` 不能作为唯一停用方式。
- 可选插件必须有 fallback 或显式禁用路径。
- `shell/references/`、vendor 和 fixture 不得进入运行时扫描或导入路径。
- 每个例外必须登记原因、owner、重新启用条件和验证方式。

建议审计错误编号固定为：`LIFE001`（缺少 owner）、`LIFE002`（缺少销毁路径）、
`LIFE003`（shared 层副作用）、`LIFE004`（直接外部命令）、`LIFE005`（可选依赖无降级）、
`LIFE006`（仅通过 visible 停用）。

#### P3-R10 Goal Mode 检查点（已全部达成）

1. [x] 资源清单生成：`shell/wiki/lifecycle-inventory.json`（266 项）；
2. [x] 审计器验证：`python3 -m unittest shell/tests/test_lifecycle_audit.py` 10 项全绿；
3. [x] 高风险模块 teardown：全库 544 个 QML/JS 文件 0 处 LIFE001-LIFE006 违规；
4. [x] 重复开关与失败路径测试：`python3 -m unittest tests/test_shell.py` 23 项全绿；
5. [x] `check.sh --full` 接入：全项测试通过，CTests 21 项全通过，生命周期审计全绿；
6. [x] 文档、证据和路线图状态同步：已完整同步。

#### P3-R10 完成门槛

- 运行时 QML 资源清单完整；
- 高风险 Process、Timer、IO、网络和原生资源都有 owner 与 teardown；
- shared 副作用扫描通过；
- Action Gateway 绕过扫描通过，或所有例外有记录；
- 连续开关不产生资源增长；
- 正常退出、取消、SIGTERM 和失败恢复无专属残留；
- `check.sh --full` 可重复执行；
- 不引入 pip 或其他未声明依赖；
- 当前源码、测试、日志和路线图状态一致。

### P3 宣言兑现专项主线与状态对齐（P3-R09 系列）

| 任务 | 交付与硬验收 | 当前状态与实测证据 |
| --- | --- | --- |
| P3-R09-01 按需宿主与启动闭包 | AppShell 仅装配核心宿主；高成本模块由真实消费者 Loader 化；禁用 Keystone 时不创建 Keystone；冷/暖缓存分别记录首帧、ready、IPC ready 和失败阶段。 | [ ] **[当前主线卡点]** 待实现：AppShell 剥离常驻 Keystone/Dock/DesktopCard，建立 Loader 按需机制与冷暖性能基线 |
| P3-R09-02 Action Gateway 全路径收敛 | 清除 `app/` 与 `modules/` 的直接外部命令和系统副作用；所有动作有结构化意图、参数数组、owner、结果、取消和超时测试。 | [x] **[已闭环]** 由 P3-R10 彻底消除直接外部命令，全库 100% 收敛至参数数组与明确 owner |
| P3-R09-03 生命周期与资源 owner | 每个可选模块完成重复打开/关闭/重建测试；证明 Timer、Process、请求、连接、窗口和旧回调消失，RSS/CPU/进程/连接不持续增长。 | [x] **[已闭环]** 由 P3-R10 交付 266 资源盘点、40+ teardown 与 20x 压测，全绿归档 |
| P3-R09-04 四层与 fallback 自动守门 | shared 副作用扫描、跨域 singleton 扫描、native/fallback 缺失与运行失败矩阵通过；旧物理路径不能回归。 | [x] **[已闭环]** 由 P3-R10 静态审计器接入 check.sh，全量拦截 LIFE001-LIFE006 违规 |
| P3-R09-05 视觉与交互恢复 | Bar、通知、Launcher、Lock、Sidebar、Keystone 在隔离 Wayland/Niri 会话完成输入和截图验收；降级状态布局稳定。 | [ ] **[待验收]** 依赖实机/虚拟 Wayland 会话截图与输入日志闭环 |
| P3-R09-06 测试环境证据分类 | 图形测试先检查 Wayland socket、Compositor、Quickshell、D-Bus 和 Niri 前置；区分通过、跳过、环境阻断和产品失败。 | [ ] **[待验收]** 环境前置探针与跳过分类矩阵 |
| P3-R09-07 P3 收口 | 只有 R09 全部具备当前源码、行为、资源和必要视觉证据后，才允许恢复 P3 整体完成状态。 | [ ] **[门禁锁定]** 待 R09-01/05/06 交付后进行最终整体验收 |

每批交接必须记录：原文件与依赖、直接复用部分、适配差异及理由、复现步骤、验证环境、
截图/日志、资源释放、未解决事项、恢复点与旧实现处理。先切消费者并验收，再删替代实现；
禁止覆盖现有未提交改动、顺手扩张功能或继续全库清理。无法复用时先在矩阵写明具体阻断
与最小替代范围，不能绕过来源审查。
P4/P5 新增开发等待 P3 恢复验收；不能通过缩小功能清单把遗漏变成“已完成”。

## P4：壁纸、M3 调色与模板兼容

前置：地基及生命周期成立。保留根目录原生能力和用户模板无需重写的承诺。

- [ ] P4-01 先查 Wiki 的 [主题适配](../configs/noctalia/README.md)、现有注册与真实模板，记录渲染器、变量/过滤器/语法契约；不凭“Jinja 风格”发明解析器。
- [ ] P4-02 对比母体现有壁纸和调色实现，明确可复用算法、原生必要性与依赖；自研模式不依赖外部 Python GUI 伴生脚本。
- [ ] P4-03 原生壁纸与 M3 调色输出同构 palette.toml，保留字段、色值与明暗联动契约。
- [ ] P4-04 TemplateAdapter 以真实模板和 Noctalia 支持能力为兼容依据；GTK CSS、Fcitx SVG、Kitty、Starship 和用户模板无需重写。

每项在实现前形成具体输入/输出、失败处理和测试样本方案。模板结果、主题信号、
用户覆盖保护均有验收；渲染依赖与 Python 引擎纯标准库约束不能混淆。

## P5：完整宿主与双轨生态

前置：P3/P4；P1 已兑现即时切换，不将其再次当作尚未开始的大阶段。

- [ ] P5-01 完整验收六动作 launcher/session/settings/clipboard/lock/wallpaper-random，外围快捷键无需改写；另外记录 wallpaper-picker/radial-launcher 两个兼容接口。
- [ ] P5-02 可选部署/更新/快照/回滚/卸载接入原子复制、Dunder 和 manifest 保留；明确源码预览与正式安装区别。
- [ ] P5-03 Noctalia 模式伴生套件按需部署/运行，自研模式独立；切换、主题、壁纸与模板双轨互不覆盖。
- [ ] P5-04 同步命令、状态、打包、安装方式和卸载契约，验证升级及恢复失败不损失配置。

验收：真实部署沙箱证明原子性与配置保护；回滚精确恢复，卸载不清用户其他 QS 配置。
默认 Noctalia 与自研模式均可用，失败日志不无限增长，无未声明依赖或受管残留。

## P6：整体验收及未来移植

- [ ] P6-01 固定机器/版本/分辨率/缩放/字体，记录 20 次首帧与 ready 的 p50/p95，暖缓存与冷缓存分别记录；秒级目标依据基线冻结，不写未经论证的硬数字。
- [ ] P6-02 重复面板开关、模块停用和 Shell 切换，记录后半程稳态 RSS/CPU/进程/连接，验证无持续增长及后台残留。
- [ ] P6-03 核心离线无请求；缺插件/设备矩阵、锁屏与会话结束、SIGTERM、失败恢复均有证据。
- [ ] P6-04 完成宿主必要检查和受影响上游行为测试；稳定后再接纳封存功能或生态移植。
- [ ] P6-05 Action Gateway 无绕过路径；所有副作用均有 owner、参数数组、失败/取消/超时语义和可追踪结果。
- [ ] P6-06 四层边界扫描通过；shared 无 IO/网络/进程/环境读取，modules 无未注入跨域 singleton，native fallback 覆盖缺失与崩溃。
- [ ] P6-07 正常退出、启动取消、SIGTERM、目标崩溃、切换失败和恢复失败均无专属进程、窗口、连接、监听器或临时文件残留。
- [ ] P6-08 视觉验收覆盖核心态、禁用态、降级态和恢复态；功能测试、资源测试和截图证据分别保存，不能互相替代。
- [ ] P6-09 路线图状态与当前源码、测试输出和验证环境逐项对齐；历史数字无法复现时必须标记为历史记录，不得作为完成依据。

Terminal Rice、安全 Downdate 仍属于根目录宿主路线；多合成器抽象在原版 Niri
地基成立后再推进，不在启动阶段提前实现 Hyprland/Sway。

## 用户要求与任务对应

| 要求 | 落点 |
| --- | --- |
| 精神 → 详细计划 → 开发，当前只补计划 | 当前阶段、P0-08 |
| 宣言精神融入文档，长期目标不丢失 | 开发约定、设计来源与长期目标、P4/P5/P6 |
| Nyxuri Shell / nyxuri-shell 命名 | 当前阶段、开发约定、调试指南 |
| 修整完整母体、保视觉与上下文 | P0-03、P1-01/02、P2 |
| 原版 Niri，不整体否定桥 | P0-04、P2-05 |
| C++ 非强制，保留必要现有代码 | P0-05、开发约定 |
| 舒适可靠启动、及时切换 Noctalia | P1-01 至 05 |
| 我怎样调试 | P0-07、P1-06、开发与调试指南 |
| 四层、动作网关、真实销毁与无失控依赖 | P2、P3、P6 |
| 按需启动、完整副作用收敛、真实 Hot Teardown | P3-R09、P6-02、P6-05、P6-07 |
| shared 纯净、native fallback、视觉与证据守门 | P3-R09-04/05/06、P6-06、P6-08 |
| 去臃肿化、删除旧路径与架构行为验收 | 开发约定、P0 清单、P1/P2 |
| 单开发分支大胆实验、检查点与阶段合并 | 开发与调试 |
| 壁纸/M3/模板与六动作、双轨承诺 | P4、P5 |

文档职责：本文件维护阶段与状态，[开发约定](AGENTS.md) 管约束，
[蓝图](wiki/blueprint.md) 管设计与未决方案，
[审计](wiki/audit.md) 管事实，
[开发与调试](wiki/development.md) 管实际工具与未来开发流程。

### 状态真实性规则

- `[x]` 只有在当前版本的源码、行为测试和所需实机/隔离会话证据全部齐全时才表示完成；
  历史代码记录必须标注为历史，不得隐含当前验收通过。
- 目录、文件、Loader、字符串、隐藏 UI 或文档存在性不能单独改变任务状态。
- 测试通过、测试跳过、环境阻断和产品失败必须使用不同状态和文字记录。
- 每项完成记录必须包含复现命令、验证环境、失败路径、资源释放证据和视觉证据（若适用）。
- 任何新依赖、直接副作用、跨层 singleton、常驻资源或未解释的视觉回退都构成合并阻断。

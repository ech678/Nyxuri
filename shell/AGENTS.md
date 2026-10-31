# Nyxuri Shell 开发约定

## 目标与真值

本文件适用于 `shell/`，继承仓库根目录 [AGENTS.md](../AGENTS.md) 的约束。
Nyxuri Shell 以完整 Clavis 母体为起点，就地净化、重构；当前先完成干净启动与规整架构，
为未来功能移植建立可持续的底座。产品名 **Nyxuri Shell**，程序/配置标识 **nyxuri-shell**。
开发顺序是精神与原则 → 详细启动及整理计划 → 开发；按已确认的阶段计划实施与验收。
这不是必须采用两级程序启动架构的要求，候选实现不能提前变成契约。

- 设计依据：[issue #111](https://github.com/ech678/Nyxuri/issues/111)。宣言精神已融入本文件
  与 [ROADMAP.md](ROADMAP.md)，原文通过 Git 历史追溯，不要求维护逐字副本。
- 当前实现以源码和行为测试为准；本文件是开发契约，ROADMAP 是阶段与验收计划。
- 母体版本与重现指令见 [上游参考](../llms-wiki/shell/references.md)（历史时点审计已冻结于
  [archive](../llms-wiki/archive/)）；日常调试循环与分类测试见
  [开发与调试](../llms-wiki/shell/development.md)。详细阶段以本目录 ROADMAP 为准。
- `llms-wiki/upstream/clavis-docs/` 中的 Clavis 文档属于上游参考，不能覆盖 Nyxuri 契约；上游安装命令、软链
  开发入口、key-cli 工作流不自动成为本项目要求。

## 设计精神

极简是秩序：几何精度、对齐规整，以及砍掉不必要的东西。核心质量不能以“能跑”为由
将就；依赖、后台和配置都应清楚可控。选择 Clavis 是为了保住现代视觉语言与流体交互，
净化骨架不能牺牲它的质感。未来生态移植沿四层和动作边界接入，不靠猜接口与虚构胶水。

扩展性由真实功能接入证明。先做通一个完整域，再用第二个域检验复用与边界；
不提前建设通用插件框架，也不以“永远无需调整架构”作为完成标准。

## 当前红线

1. **完整母体上动刀**：在现有代码树内改造，保留 QML 上下文、级联和绑定；禁止另开
   孤立实现、从零切片搬运、猜测接口或添加未经验证的 shim。实验可以暂时不可运行，
   但必须保留恢复点；可运行检查点与阶段合并必须通过验收。
2. **先启动与架构**：Cava、复杂天气地图、歌词等重型附加功能封存。封存意味着不进入
   核心加载闭包、不实例化后台、不参与默认构建；`visible: false` 不算封存。
3. **视觉守护**：保留原版几何精度、流体动画与质感；删依赖、删字体不能换来裁切、错位、
   图标缺失或简陋占位。保留资产来源和许可证。
4. **原版 Niri 基线**：支持官方原版 Niri，不要求用户安装魔改合成器。
   `Clavis.Niri` 是上游自定义 QML/C++ 桥，不是原版 Niri 自带模块；桥内标准 IPC
   与高级扩展必须逐项区分。工作区、窗口、输出等基础能力对接标准接口；动画目标、
   最小化、浮动移动/视差分别核实，只有已证实依赖扩展的能力才按兼容性封存。
   不把整个桥简单删除，也不把它全部当作必需依赖；按真实能力隔离、验证、降级。
5. **语言按必要性选择**：C++ 不是强制要求。界面与普通逻辑用 QML/JavaScript；
   先保留并修整现有有效 native 模型/协议，新增 C++ 须说明能力缺口或实测性能理由。
6. **干净可控**：不为审计或普通验证安装依赖、改用户配置、启动持久服务；不执行上游
   安装器。key-cli、冷门 native 插件与在线服务不绑架核心冷启动。

## 去臃肿化

同时清理启动、运行、构建依赖与源码资产四种负担：缩小加载闭包，停止无消费者后台，
拆出可选构建目标，核实后删除死代码、重复实现、废弃脚本与死数据。内嵌字体改用系统回退，
同步检查时钟、图标、布局和许可证；有效视觉资产不因压缩体积被误删。

封存只解决当前隔离，不能代替最终清理。记录保留理由、入口、依赖、检查范围和重新启用
条件；无消费者且无保留理由的代码核实后删除。重新启用须验证接口、依赖、生命周期与视觉。

## 三层边界与单元目录（KM4.5 拆迁正名后）

目标运行代码严格分为 `app/`、`units/`、`shared/` 三层（原 `native/` 层已于 R4-C 彻底解耦并物理删除，全库转为纯 QML/JS/Script 架构；原 `modules/` 层已于 KM4.5 整体正名为 `units/`，代码与 `manifest.toml` 同目录——目录即单元，内核 registry 以目录名派生 `shell.<domain>` id）。遗留母体结构 `Modules/`、`Components/`、`Widgets/`、`Common/`、`Services/` 与 `core/` 已全面清算归并。KM4.6 起 `assets/` Junk Drawer 解散——单元自有 shader 归 `units/<domain>/shaders/`，宿主数据（i18n 词典、icons、内置模板注册表）归 `app/`，第三方许可证与溯源记录折入 `LICENSE` 第三方附录；`fallback/`、`packaging/` 同阶段处决。所有单元与深层目录严格遵循全小写规范，根目录已消除上游独立发行残余（`install.sh`、`scripts/ci/`）。测试、资源、工具和许可证保留各自合理位置。

- **app**：顶层装配（`AppShell`/`SlotHost`/`UnitCatalog`）、环境与能力感知、IPC、全局快捷键意图、生命周期与存储协调；业务执行归明确 backend，不把 app 变成包揽所有业务的控制中心。`app/services/` 同时承载宿主能力面（`HotCorners`、`FilePickerWindow`、`IdleInhibitorSurface`）与直读 app 单例的跨单元渲染边（`SystemCardContent`、`SystemClockCard`、`SidebarCookieClock` 等）。
- **units**：功能域自治，一单元一目录（`manifest.toml` + 视图、模型和专属 backend 内聚），通过显式属性注入依赖。禁止跨域随手调用全局 Service；跨单元协调由 app 的窄接口完成。新增单元 = 加目录 + manifest + 代码，零宿主代码改动。
- **shared**：复用的原子控件（`controls/`）、纯展示系统卡片（`cards/`）、几何、动画和纯计算（`utils/`）。不得读取配置/环境、写文件、发请求、起进程或持有业务连接；接收注入的色板、字体、尺寸与数据。凡需直读 app 单例的卡片不进 `shared/`，留 `app/services/`。
- **支撑代码归宿**（KM4.5 裁决，不设第四棵树）：宿主能力面归 `app/services/`；单消费者组件并入唯一消费单元（如 `sidebars/quicksettings/`）；跨单元纯展示组件归 `shared/cards|controls/`。

UI 只呈现和响应输入；桌面意图经 Action Gateway 执行。命令、文件修改、网络请求
由明确 backend/执行器承担并登记 owner，不在展示组件深处执行。外部命令使用参数数组，
不 eval、不拼 shell 字符串；后台订阅也必须有归属，不能绕过生命周期管理。
每个域迁移时同步检查旧路径，验收后移除被替代实现，避免新旧两套长期共存。

## 微内核宿主与几何插槽（KM4 契约，迁自 plugin-model §6）

Shell 是极致精简的**微内核宿主**：宿主只保留装配（`SlotHost`）、动作网关
（`ActionGateway`，含 `executeIntent` 跨域意图路由）、会话协议（`NiriService`）、
主题代币（`ThemeTokens`/ThemeService）与账本投影（`StateProjection`）。内核侧
三条（同一账本、单一事件通道、点分 ID）冻结在 plugin-model §6，此处承载实现契约。

- **六大几何插槽**：所有 Shell 单元（`shell/units/<domain>/`，`runtime = true`，
  manifest 与代码同目录——目录即单元，KM4.5 后 modules/ 已正名并入）
  向唯一的 6 种几何插槽声明挂载——`edge`（bar/dock）、`island`（keystone）、
  `overlay`（launcher/lock/session/settings/regionselector）、`drawer`（sidebars）、
  `surface:desktop`（desktopcards/wallpaper）、`popup:notification`（notifications）。
  插槽归属数据在 `app/UnitCatalog.qml`，与 `shell/units/` 由
  `shell/tests/test_unit_catalog.py` 强制同步。
- **数据驱动装载**：`AppShell.qml` 不按名实例化任何单元组件；`SlotHost` 以
  `Repeater + Loader` 依目录装配，`active` 只读 `StateProjection`。单元 `disabled`
  即 `Loader.active = false`：实例销毁，Process/Timer/Socket/回调全部注销；冷启动
  未启用域零读文件、零实例化。槽仲裁归宿主：lock 持有期间禁卸载（延迟至解锁）；
  keystone 在场时独占 `popup:notification` 槽。
- **单一开关真相**：Shell 永不直写账本。开关只经 `UnitControlService` 派发
  `nyxuri on/off shell.<domain>`，UI 不乐观翻转——`unit-changed` 事件
  （`qs ipc call unit reload`，宿主 `IpcHandler target: "unit"` 接收）到达后由
  `StateProjection` 重投影。账本无记录 = 默认启用；账本损坏 = 全启用降级 + 诊断
  横幅。外观轴（位置/样式/覆盖等）仍归 PersonalizationConfig，与开关轴正交。
- **单元自有 IPC**：单元的 IPC surface 属单元（lock/spotlight/power-menu/
  control-center/settings/keystone），随单元装载生死；宿主只保留通用面
  （unit/shell/theme/shortcut-map/wallpaper）。单元 off 时其 IPC 目标消失，
  六动作经 `nyxuri-shell --action` 得到真实失败而非假成功；任意单元 IPC 面
  （`niri-actions.json` 目录 207 条）经 `nyxuri-shell --ipc <target> <method>
  [args…]` PATH 稳定网关分发，合成器 binds 不再引用 quickshell 配置名。
- **Quickshell 0.3.2 运行时约束**（KM4 实测，quickshell 升级后重估）：
  ① Loader 动态装载的组件首次解析 qs.* import 图不可靠——单元以「module not
  installed / X is not a type」不确定地整单元暴毙（与 QML 磁盘缓存无关）。
  对策：SlotHost 静态预热 import 全部 12 个单元模块（只注册不实例化），装载仍
  纯 Loader 驱动；禁用单元零实例化、零窗口、零驻留内存不变，代价是预热注册的
  仅解析成本。**推广（KM4.6 实机验收教训）**：任何新建的 qs.* 合成池（如
  `qs.app.cards`）只要被单元组件消费，就必须进 SlotHost 预热名单——全库没有
  顶层文件 import 它时，首次解析必然发生在 Loader 内，单元确定性 compiled
  empty；宿主自愈重试两次后放弃并在日志明示，unit-changed 重新武装。
  ② QML 磁盘缓存会供应陈旧编译产物——源码改动后新旧代码混跑（表现为「改了没
  生效」「部分单元是新逻辑部分是旧逻辑」）。对策：nyxuri-shell wrapper 每次
  启动清空 qmlcache（永远冷编译，预热 import 已证冷编译干净）。注意不可用
  `QML_DISABLE_DISK_CACHE=1` 替代——没有缓存写入时每次 Loader 装载都会重新
  踩中 ① 的 import 缺陷。
  ③ `IpcHandler` 类型挂在 `Quickshell.Io` 模块下——单元根新增 handler 时必须
  `import Quickshell.Io`（仅 import Quickshell 不够，报「IpcHandler is not a
  type」且目标静默消失）。
  ④ 窗口与处理器属性面与 Qt/QML 习惯不同（2026-10-25 mod+i 事故定案）：
  `FloatingWindow` 无 `minimumWidth`/`minimumHeight`（正名 `minimumSize`，
  误赋值 = 单元 compiled empty，宿主自愈两次后放弃）；`TapHandler` 无
  `hovered`（运行时 undefined 静默击穿绑定，hover 态一律用 `HoverHandler`）。
  qmllint 对含 qs.* VFS 导入的文件不做此类成员校验——Quickshell API面
  改动必须实机验证，不能只信 lint。
- **降级语义**：能力全开、副作用明示——`off shell.lock` 后 idle 锁请求报失败
  横幅、无锁挂起直接执行；`off shell.wallpaper` 卸载壁纸视觉，合成器背景透出；
  域服务（通知接收、壁纸状态、主题管线输入）是 app 层能力，不随视觉单元卸载。

## 生命周期与退出

- 模块未使用时不启动专属后台。面板收起立即停止专属任务，关闭动画结束后卸载对象；
  重开取消旧卸载，旧异步回调不得污染新实例。
- 停用功能域要销毁窗口、停止 Timer/重连、断开连接、取消请求、终止专属子进程、
  释放消费者租约与外部引用。shutdown 幂等且有界；不能只隐藏 UI。
- 通知接收、栏实际使用的设备订阅等基础服务与临时面板分离，只有实际消费者需要时保留。
  不以关闭历史面板为由停止通知接收。
- Shell 退出/切换只清理自己管理的实例与进程，不 `pkill qs`，不杀用户启动的应用。
  不出现双状态栏或幽灵进程；缺目标或启动失败要有真实运行态和有界回退。
- 锁屏中禁止销毁安全锁、停用 lock 或普通热切换；认证和 Wayland 安全语义不能降级为
  普通窗口。装饰缺失不阻断认证，安全能力缺失必须明确失败。
- 对资源回收测量多轮稳态与残留，不能把 Qt/字体缓存的 RSS 当作必然泄漏，也不能承诺
  QObject 销毁后每个字节立即返还系统。

## 宿主连接与持久数据

仓库源码与用户配置物理隔离；部署只能经 `nyxuri.deploy.atomic.atomic_replace_item`
原子复制，禁止将源码软链进 ~/.config。保留 `__custom__` 与 manifest preserve 协议，
状态、缓存、设置遵循宿主 XDG 路径，禁止硬编码家目录或无声明写入。

保留根目录 ROADMAP 的启动器、壁纸/M3 调色、Noctalia TemplateAdapter、六大标准
动作、双 Shell 切换与伴生套件协同目标；启动奠基优先不等于删除长期目标。
当前仅写偏好的 `nyxuri shell set` 不能被描述成已完成热切换。新增命令与语义调整应
同步命令契约，不能覆盖既有承诺。Python 管理引擎保持标准库零 pip 依赖。

## QML、构建与文案

- 保留 Quickshell root-relative import 语义，不给纯 QML 目录手写 qmldir。
  native 的 qmldir、qmltypes 和 plugin 由 CMake/Qt 生成，不手改生成物或用户安装目录。
- 静态 import 不因 Loader inactive 自动变成可选。缺插件路径必须用真实独立组件
  验证隔离；默认构建不 require 封存依赖。
- `shared/` 由 `theme/`（设计 Token 与注入数据）、`controls/`（原子控件与区域几何）和 `utils/`（纯计算）构成，不读取环境、发现系统字体/图标或监听文件。主题 IO、字体加载与发现、图标解析归 `app/services/`，路径归 `app/Paths.qml`；`Resources` 与 `Fonts` 仅承载 app 注入的展示数据。设置搜索锚点归 settings，面板协调状态归 app；共享控件的 Connections 只能观察注入对象和自身几何。
- 删除内嵌字体时同步处理 family、时钟、图标与排版回退，禁止启动时联网下载。
- UI 文案沿用 qsTr/qsTranslate、占位符与 Qt numerus；修改时同步相关翻译。
  语言切换不改变地区、单位或用户数据。宿主文案遵循 writing-voice 与 i18n 契约。

## 验证与完成定义

先看 git status，运行宿主基线测试。只改请求范围，不主动 commit、不重排无关文件。
文档修改只做相关一致性、链接和空白检查；运行代码修改按影响选择必要验证。
日常循环、单开发分支实验与阶段合并规则见
[开发与调试](../llms-wiki/shell/development.md)。分支不改变真实配置与服务的隔离要求。

- QML：只格式化改动文件，检查真实 import/类型和受影响消费者，按需做原版 Niri
  视觉/交互冒烟。普通布局不自动新增 QtTest。
- native：配置/构建受影响目标，运行已有纯逻辑与协议测试；必要时扩至 CTest。
- Python/Shell：语法与相关现有行为测试；宿主新测试使用 tests/utils.py:TempEnv，
  外部命令断言参数数组形状，禁止写真实 ~/.config。
- 生命周期：用可观测窗口、进程、连接、请求和多轮开关验证；禁止用 grep/regex 匹配
  Loader、property、目录或对象层级来假装行为测试。静态审计可以搜索源码，但不替代测试。
- scripts/dev/check.sh 按 Shell 内相对路径选择变更；QML lint 检查核心 native 模块就绪，可选插件缺失须注明；不得把未覆盖或工具阻断
  报成成功。工具缺失只诊断一次，不顺手安装、重排全库或引入大工具链。

完成时说明真实改动、验证结果和阻断；架构/接口/命令变更同步对应 Wiki 与 ROADMAP。
路线图只有验收成立才勾选，不以能创建目录、隐藏组件或存在可执行文件作为完成依据。
清理与架构验收列明减少的加载、依赖及后台负担、消除的跨域调用和删除的旧路径，
并附行为证据；目录规整不能代替架构验收。

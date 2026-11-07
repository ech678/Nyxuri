# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段台账、当前阶段与门禁见
> [shell/ROADMAP.md](shell/ROADMAP.md)。上一卷「插件市场化改造」KM0–KM5 已全数
> 落地收口，整卷台账冻结于 [archive/roadmap-history](llms-wiki/archive/roadmap-history.md)；
> 设计哲学与五条简洁标准见 [vision](llms-wiki/vision.md)。
> 本卷为「架构重塑卷」：先修已知问题、做减法收概念，再换 Shell 骨架，
> 最后开第三方插件的大门。

## 主线收口（上一卷地基）

「桌面插件市场」产品形态成立：内核（registry · resolver · transaction · ledger）+
万物皆插件的 manifest 全声明目录 + 多前端界面，以账本为唯一开关真相、原子部署连接
只读蓝图与用户生活区；安装器退役为一次性引导。术语与内核契约的唯一权威在
[plugin-model](llms-wiki/plugin-model.md)，此处不复述。本卷在此地基上重塑；
R0-1 落地时同步改写该页术语（单元 → 插件）。

## 活跃路线（执行序即优先级）

| 站 | 交付 | 状态 |
| --- | --- | --- |
| G0 | 修复 GitHub 已知问题：可独立修的立即修，架构根因随 R0 兑现后关闭回填 | 可独立修落地（#144 #146）；根因修随 R0-3 落地（#143 #145 #147 #149）；#142 随 R0-5 转上游跟踪 |
| R0 | 引擎收敛：概念定名 Plugin/插件 + 杀词并轨 + 单一激活管线 + 声明贯通 + 减法外迁 + 文档对齐 | 已收口（R0-1 ~ R0-6；R0-5 取消自带收口，launcher 暂留） |
| S0 | Shell 骨架整抄 Omarchy：五件套 + 运行时插件注册表 + 设置去中心化 + 合成器驱动面（S0-0 ~ S0-5 全数收口；manifest 协议 TOML 本站定稿） | 已收口 |
| S1 | 第三方插件生命周期：协议 1:1 + 生命周期动词 + Shell 心脏整抄 + 所有权账本回植 | 进行中（S1-0 ~ S1-4 已收口） |
| T4 | Shell 可控性与透明化（开工时立细则） | 待开始 |
| T5 | 多合成器解耦（门禁触发） | 待开始 |
| T2 | TUI Textual 重做（暂缓，分支备用） | 待开始 |

### G0 · 修复 GitHub 已知问题

> 原则：不在旧概念上做新架构；但症状能独立修的先修，用户不等重塑。
> 每个修复在 issue 下回填路线引用与验收证据（GitHub CLI）。

- **可独立修（不依赖 R0，前向兼容）**：
  - #144 壁纸路径写死 `~/Pictures/Wallpapers`：manifest 目标与 `install-pack` 钩子
    接 `core.get_pics_dir()`（XDG）；R0-4 的 `xdg:` 词汇是它的推广形态。
  - #146 `adw-gtk-theme` 未声明：`units/theme/manifest.toml` 的 packages 补一行。
- **根因修（已随 R0-3 落地关闭）**：#143（事务渲染 phase 注入）、#145（壁纸包收编
  声明式钩子）、#147（hook-only 形态矩阵显式化）、#149（安装器组件勾选改派发事务）。
- **随外迁处置**：#142 划词翻译 PDF——已随 R0-5 转上游 [orbit-translate#1](https://github.com/WALKERKILLER/orbit-translate/issues/1) 跟踪，本仓库 issue 保持原样。

### R0 · 引擎收敛（架构重塑地基）

- **R0-1 概念定名：Plugin / 插件**。「单元」退役，三词术语收敛为
  **插件 · manifest · 账本**。`units/` → `plugins/`（引擎蓝图目录，机械改；
  shell 侧随 S0）；账本键 `units.*` 提供一次性迁移（老安装升级路径）；
  [plugin-model](llms-wiki/plugin-model.md) 随本站改写；术语权威表述见
  [vision](llms-wiki/vision.md) §1。
- **R0-2 杀词并轨**（已收口）：预设 + 零件合并为插件的**形态字段**——manifest
  `[presets]`/`[parts]` 并轨 `[forms]` 单节、账本 `preset` 字段改名 `form` + 顶层
  `forms` 槽位字典（一次性迁移）、`deploy/preset.py` → `forms.py`、`use` 动词上位
  （`preset` 命令与 `on --preset` 降级 deprecated 别名，一版周期）；`presets/<app>.active`
  双写退役（只读采纳一版周期，用户形态目录 `nyx_dir/presets` → `forms` 一次性迁移）；
  「源」概念删除（plugin-model §2 三词定案）；市场/工坊词退役（含 wiki 比喻改写
  「桌面插件引擎」）；`catalog.toml` 并轨——18 条「装但不部署」声明升格 manifest-only
  插件（`deploy = false` 显式声明压过内容扫描，deps 菜单单源聚合 manifest）；
  保险库降级为 off 的内部机制、用户文案只剩「快照 / 收存」；`__custom__` 退出用户
  文档教学（模板作者文档保留冻结协议）；一条 apply 路径吃两轴
  （`_reconcile_active_parts` 旁路退役为 `replay_active_forms` 同路径重放）；
  **步 5 供给面处决（已执法）**：常用推荐软件安装整体退役——18 个仅包声明插件目录、
  `deploy = false` / `detect` 键（声明即解析报错）、`deps apps`（`opt`/`optional`）命令、
  安装器菜单项与部署后「常用软件」入口、`CategoryCheckboxList` 手风琴、`app_*`/`apps_cat_*`
  文案全数清除；插件装包统一走 `nyxuri on <plugin>` 单路径，`deps` 收敛为核心依赖勾选单，
  greeter 形态仅声明单元（装包 + hooks + 落账）保留。
- **R0-3 单一激活管线**（已收口）：启用一个插件的步骤清单只留 transaction 一条——渲染
  phase 入事务（Issue #143）、插件形态矩阵（runtime / merge / atomic / hook-only）manifest 化（Issue #147）、
  安装器组件勾选改派发事务（Issue #149）、壁纸包收编 wallpapers 声明式钩子（Issue #145）。
  兼容清扫同站执法（R0-2 一版周期期满）：`preset` 命令别名与 `on --preset` 旗标处决、
  `.active` marker 只读采纳 shim 处决、read_ledger 遗留迁移代码（units→plugins、
  preset→form、presets/parts→forms）处决。
  验收 = #143 / #145 / #147 / #149 契约绿。
- **R0-4 声明贯通与边界校验**（已收口）：manifest 路径词汇 XDG 化（推广为完整 8 类用户目录映射，模板图片目录中立化合一）；
  theme 副作用的包依赖声明与医生巡检（#146 根因，sysdoctor 补齐 adw-gtk-theme 在位性诊断）；叶名 / containment 校验进引擎
  （#48 的 `../../` 越界教训，core/registry/manifest/transaction 严格阻断逃逸）；保留策略按操作参数化——回滚默认精确恢复，
  支持显式 `--keep-custom` 保留并报告（#56）、更新尊重 Drifted 基线（#139 定案行为在此收编为契约）。
- **R0-5 减法外迁**（已收口）：orbit-translate 彻底外迁上游
  [WALKERKILLER/orbit-translate](https://github.com/WALKERKILLER/orbit-translate)
  ——程序、测试（≈3K 行）、CI、issue 全部上游自持（#142 → 上游 #1）。Nyxuri
  **取消自带**：`plugins/noctalia/tools/` 翻译器 payload 删除，用户经上游
  `install.sh` 自装，S1 落地后 `nyxuri add` 接管（接入清单见 S1 节）；测试
  `tests/tools/translate/` 删除（上游 CI 为测试权威）。`orbit` 星环启动器**暂留**。
  `nyxuri/market/` 与 `tests/market/` 残留删除；本地脏区清理（qmlls.ini 悬空链、
  packaging 构建残留、插件 hooks `__pycache__`）；本地 `pr-*` 分支清理，远端
  `archive/*` 分支随 T2 重启决策定去留。
- **R0-6 文档对齐**（已收口）：`plugin-model` / `forms`（原 preset-mechanism）/ `manifest-schema`
  已随 R0-2 改写同步；剩余失实记录已按实况清算——旧卷「Cava/歌词/窗口预览死代码已清理」
  与代码不符（实况：地图已清，Cava 与歌词活着），`shell/ROADMAP` 历史决策句与
  `shell/AGENTS` 红线 2 已改写为实况描述（归档台账同句按冻结条款不改，以活文档为准），
  `WeatherContent` 悬空 `weatherMapLoader` 残留随清算清除。

### S0 · Shell 骨架整抄（Omarchy 协议，小写命名）

- **整抄裁决**：作者定案——Omarchy 4 的插件系统、注册程序与骨架整包采纳；
  目录名保持小写开头风格（`Commons/Ui/plugins` → `commons/ui/plugins`）；
  不抄它的 `shell.json` 开关状态——单一开关真相继续留在引擎账本。
- **manifest 载体定案（作者拍板）**：**TOML，彻底换代零兼容**。Omarchy 协议字段
  语义 1:1、载体不跟——`schemaVersion` / `kinds` / `entryPoints` / settings schema
  并轨进 `manifest.toml` 单文件，引擎 registry 与 shell PluginRegistry 同读一份。
  并轨是整批重写不是追加兼容：两套词表撞概念的杀词并轨、冗余字段直接删，
  仓库内全部 manifest 一次改写到新形态（`schemaVersion` 起步即新形态）；引擎与
  注册表只认新形态，旧形态（含缺 `schemaVersion`）声明即解析报错——不设兼容期、
  不做只读采纳、无迁移 shim。S0 即协议定稿（[manifest-schema](llms-wiki/manifest-schema.md)
  随站同步），S1 只管对第三方开放与生命周期动词，不再动字段。
- **`shell.json` 非开关部分不跟**：Omarchy 把 widget 设置值与 bar 布局也塞在
  `shell.json`——设置值走设置去中心化的 schema + 现有状态投影存储，布局状态落点
  随 S0-3 定稿登记；不引入第二份开关 / 状态真相。
- **装配层留任**：五件套指 Omarchy 骨架对位的五层（`shell.qml` + `commons/` +
  `ui/` + `services/` + `plugins/`），`app/` 不被吞并——瘦身为纯装配与宿主数据层
  （AppShell / SlotHost / Paths / WidgetState / ActionGateway / icons / templates）。
- **迁移对照表**（逐行核对，是机器验收的核对基准）：

| 旧 | 新 |
| --- | --- |
| `shell.qml` | 不动（常驻宿主入口） |
| `shared/utils` + `shared/theme` | `commons/` |
| `shared/i18n` + `app/i18n` | `commons/i18n`（两份合一：词典 + I18n 单例） |
| `shared/cards` + `app/cards` | `commons/cards`（两份合一） |
| `shared/controls` + T3 M1 积木 | `ui/`（平面控件库） |
| `app/services` | `services/`（+ PluginRegistry / PluginXxxApi） |
| `shell/units/` | `plugins/`（每域 `manifest.toml` + entryPoints） |
| `app/` 其余（AppShell / SlotHost / Paths / WidgetState / ActionGateway / icons / templates） | 不动（纯装配与宿主数据层） |
| `scripts/` | 基本不动；例外：`generate-search-catalog.py` 与 catalog 门禁随四件套退役 |

- **import 根随迁机械扫**：`qs.units.*` → `qs.plugins.*`、`qs.shared.*` →
  `qs.commons.*` / `qs.ui.*`、`qs.app.services.*` → `qs.services.*`；收口标准是
  全库 grep 旧根零命中。
- **分站（执行序即优先级，一站一收口）**：
  - **S0-0 装载 spike（门禁先行）**（已收口）：在 Quickshell 0.3.2 的 qs-import Loader
    缺陷（SlotHost 预热名单就是它的补丁）上验证注册表装载形态。结论：**file:// URL
    装载形态定案**（Omarchy `entryPointUrl` 形态，release 0.3.2 与 master 9b0f339
    双版本各 20/20）；「升级 Quickshell」不修（master 逐格同行为，0/20）、启动期
    `createComponent` 预热无效（0/20）——根因是 qmldir 合成闭包不含动态装载面。
    证据、矩阵与复跑命令见 [loader-form](llms-wiki/shell/loader-form.md)；S0-2 开工放行。
  - **S0-1 五件套机械迁移**（已收口）：对照表全量执行 + import 机械扫（旧根零命中
    升格常驻护栏）+ 引擎侧扫描路径随迁 + 受影响定向测试改写绿；旧路径物理消失、
    相对 import 目标存在性全库零断链。实机验证四域复活（`shell status` →
    `IPC_READY`、compiled empty 零）；全量 984 仅余 #149 预存在红（另案）。
    顺带清算：SearchCatalog 生成器模板旧路径止血（防重生成写回断链）、批量替换
    误伤断言恢复、install.sh 失效探测项换现存插件。
  - **S0-2 运行时注册表取代四件套**（已收口）：手写 `UnitCatalog.qml` 镜像、
    `settings-routes.json`、`SearchCatalog.js` 生成器、`NexusNavPane.groupTable`
    全部由 PluginRegistry 运行时读 `manifest.toml` 取代——「新增插件 = 加目录 +
    manifest + 代码，零宿主改动」从口号变成事实；manifest 词表整批重写（杀词并轨 +
    删冗余）随此落地，旧形态一处不留；shell/AGENTS.md 对应契约段随站修订。
    收口明细：16 路由 + 53 锚点 + 21 可搜索动作全部迁入 manifest（settings 路由带
    `group`/`order`，导航几何分组连续性由测试钉死）；`SettingsSearchAnchor` 收窄为
    `anchorId` 运行时注册（声明数据只住 manifest，页内 JSON 字面与 GammaControlPage
    三条 `displays.gamma` 死锚点顺手处决）；`niri-actions.json` 剥离 `search` 块只剩
    binds 真值，manifest 动作与 binds 表达式按 id 焊接（契约测试断言 argv 形状）；
    对抗性门禁落地（testing.md 承诺）：临时插件塞入 → 发现 → 移除全程零宿主文件
    改动。证据：`run-tests.py` 五分类 105+ 绿（含新增 settings-schema 契约与临时插件
    往返）、`tests/deploy/test_manifest` 59 绿、隔离实机冒烟（独立路径防 IPC 串台）
    sidebar visible 真实翻转 + `control-center open` OK + 加载零 compiled empty。
  - **S0-3 设置去中心化**（已收口）：设置页由插件自带（panel entry / schema 两种形态），
    中央设置窗降级为聚合 panel 插件；「页面内容收编进各插件」自 S0-4 收窄版挪入
    本站执行完毕。T3 双轨呈现（default / dashboard）**已拍板（2026-11-01）：双轨
    保留**——dashboard 是正式呈现而非过渡形态。收口明细：①契约升格——
    `SettingsSearchAnchor` + `SettingsSearch` 状态机 + `PluginSettings` 值存储
    升 `services/`（宿主-页面契约面，任何插件经 `qs.services` 使用），
    `SettingsBackend` 瘦身为聚合窗私有生命周期；②7 组域页面外迁（wallpaper 6 件 /
    bar 2 件 / dock / keystone 3 件 / sidebars / launcher）+ 对应 `[[settings]]`
    路由锚点块随迁各域 manifest，聚合窗按注册表 `sourceUrl` 跨插件 file:// 装载
    （`Qt.resolvedUrl` 相对解析退役）；`WallpaperColorPicker` 随 wallpaper 落位后
    `DashboardSidebar` 等三处 `../../settings` import 处决（两处死 import）；
    `BarLayoutDragCoordinator` 被 bar/keystone 双消费正名 `ui/LayoutDragCoordinator`；
    ③值域 schema 词表定稿（S0-3b，协议冻结义务）：`[[settings]]` 第三形态 `controls`
    五型封闭词表（switch/select/slider/spin/text，语义对位 Omarchy
    boolean/enum/integer/string），引擎 `manifest.py` 与壳 `PluginManifest.js` 同一套
    检查、未知键即报错；`SchemaSettingsPage` 通用渲染页（ui/ Preference 原子）+
    值落 `PluginSettings` 存储（键 `<pluginId>.<key>`）——第三方插件几行声明即有
    设置页，存量页面零转换；④悬案登记：dashwindow 手写目录本站不接注册表
    （受控债务，触发条件见 delayed-decisions）；bar 布局落点定稿
    （PersonalizationConfig 外观轴 = 终态）。证据：`tests/shell` 282 绿（11 跳过
    =基线）、`run-tests.py --all` 五分类 106 绿（5 跳过=基线）、
    `tests/deploy/test_manifest` 60 绿（含 controls 词表正反用例）、对抗门禁扩展
    （临时插件 schema 路由发现 + 聚合器吃注册表 URL + 域插件零聚合器 import
    三条焊点）、隔离实机 16 路由 `settings open` 全 OK + dashboard 轨经新
    registerWindow 路径 wallpaper OK + 副本树注入 schema 路由（wallpaper-probe
    五控件）打开 OK 且渲染零告警 + 三次冒烟均零 compiled empty。
  - **S0-4 资产收编与实机验收（收窄版，2026-11-01 拍板先行，已收口）**：原任务里
    「页面内容收编进各插件」依赖 S0-3 的去中心化落位，挪入 S0-3；本站先行收口剩余
    三件。①清算：`ui/MaterialCard`、`ui/SidebarStagger` 零消费者处决，
    `AppBrowserPopup` 归档与 autostart 封存家族同放，`shell/archive/` 补封存登记
    README（作者裁决保留）；零消费者扫描升格常驻契约
    （`tests/shell/test_asset_placement`，含处决名单防回流）。②收编核查：11 件
    Preference/Nexus 原子件钉死 ui/（`test_preference_atoms` 既有契约复核）。③测试
    对齐与验收证据：S0-1/S0-2 遗留的 22 处预存在红全数改写绿——锚点词表跟
    `anchorId` 运行时注册、路由/分组/描述/i18n 契约改读 `manifest.toml`（新增
    manifest 词条词典可解析契约：16 路由 + 53 锚点 title/description 全部经
    context-or-default 解析）、Displays/DefaultApps 封存页测试类处决（archive
    fallback 一并退役）、SearchCatalog 生成器死刑断言钉住。证据：`tests/shell`
    282 绿（11 跳过=基线）、`run-tests.py --all` 五分类 106 绿（5 跳过=基线）、
    隔离实机（独立路径防 IPC 串台）`IPC_READY` + 16 路由 `settings open` 全 OK +
    双轨 default↔dashboard 以合成器 toplevel 真实翻转作证
    （`nyxuri-settings` / `nyxuri-settings-dashboard`）+ spotlight `SEARCH`
    相位 + 零 compiled empty；启动告警与 HEAD 对照实例逐条一致（0.3.2 冷编译
    预热产物，非本站回归）。M3/M4 视觉过目仍归作者。执行序调整：S0-4（收窄版）
    先行、S0-3 随后，站号不动。
  - **S0-5 合成器面清理（已收口）**：shell 现状本就是 niri（原 `NiriService`
    直连 `NIRI_SOCKET`，本库 grep 证实零 `Quickshell.Hyprland` import）——清的是
    **整抄对象（Omarchy）代码里的** Hyprland 语义（lock corners、dock
    workspace-layout 等），按 [omarchy-parity](llms-wiki/shell/omarchy-parity.md) §C
    逐组核对落判定。收口形态：**`CompositorDriver` 面（单例投影）+ `NiriDriver`
    首驱动**——niri 方言（`NIRI_SOCKET`、`niri msg` argv、`niri --version` 探针）
    锁死单文件，13 处消费者（app 1 / services 4 / plugins 7 / archive 1）全部改绑
    `CompositorDriver`，`isNiri` 语义正名 `available`。**散点收编**：ActionGateway
    logout 的硬编码 argv → `quitSession()`（execDetached，脱离宿主存活）；
    IdleService 的 `niri msg power-*` 进程 → `setMonitorsPower(off, callback)`
    （受管回调 / 无回调即 detached teardown 形态）；BlurService 私有版本探针 →
    `compositorVersion/Ready/Error`（版本**解释**留在 blur 域）。**处决**零消费者
    死面：工作区导航动词全家（合成器 binds 直接执行，shell 不经手）、键盘布局状态
    链、foreign-toplevel 映射、MRU、displayScales、socket 版 quit/power（1321 →
    约 830 行）。**引擎侧随站收编**：`nyxuri/compositors.py` 注册表吃掉
    `SUPPORTED_WMS` 元组 + `detect_preferred_wm()`、`menus.py` WM radio 特判、
    `sysdoctor.py` 三处 `("mango","niri")` 字面量、`theme.py` reload argv；
    `MAIN_WM` 单源化。**key-cli 实勘修正**：命令真相已单源于 `Paths.stableKey`，
    9 个消费文件是域流管理（塞进驱动即上帝对象），驱动不重复登记（判定入 §C）。
    证据：`tests/shell` 282 绿（11 跳过=基线）；`run-tests.py --all` 五分类 110 绿
    （5 跳过=基线）；`check.sh` 全过（format/lint/lifecycle-audit，驱动获 argv
    白名单豁免）；全量 Python 991 测试全绿（#149 的 `unknown plugin:
    wallpapers` 非交互崩溃一并修掉：目标列表只纳入注册表已知插件，未知 id
    降级为 WARN 而非 `plugin_on` 抛 KeyError 半途炸在已部署之后；新增
    `test_installer_skips_absent_optional_plugins_instead_of_crashing` 回滚
    即红坐实）；定向 `test_mango_adaptation` / `test_forms` / `test_theme_sync`
    / `test_ai_specs` 全绿；隔离实机（独立 XDG 路径 + 按 pid IPC）`IPC_READY`
    + `settings open wallpaper` OK + `compositor.present/connected=true`
    （驱动实时会话坐实）+ 零 compiled empty + 零 ERROR。
- **引擎侧波及（随站执行，不是顺手改）**：`nyxuri/kernel/registry.py` 的
  `shell/units/` 扫描路径与 `shell.<domain>` id 派生随 S0-1 改写；
  `test_unit_catalog` / `test_search_catalog` / catalog 门禁的新契约随 S0-2 定稿。
- **验收纪律**：防幻觉按全局门禁 4 执行；本站额外断言 = 对照表逐行核对、旧路径
  物理消失、import 全库 grep 零命中、受影响定向测试绿。

### S1 · 第三方插件生命周期

> 逐资产「照抄 / 改造 / 推迟 / 拒绝」过堂台账见 [omarchy-parity](llms-wiki/shell/omarchy-parity.md)
> （含 S1-0 裁决变更登记）。**战略定调：留我们的皮，换 Omarchy 的心**——
> - **皮（誓死守护）**：Clavis/Caelestia 现代视觉原子、流体动画、Niri 合成器驱动、引擎账本单一开关真相；
> - **心（代码物理整抄）**：Omarchy 经过实战检验的 806 行 `PluginRegistry.qml`（进程守护、inotify 实时监听、流解析）
>   物理整抄；`Plugin*Api.qml` 门面与宿主注入工厂按消费者落度（S1-0 改裁，触发条件 =
>   首个三方 ui 插件真实样例）；
> - **缝合切口**：三方落位 `~/.local/share/nyxuri/plugins/<id>/`（物理隔离）、清单接入现成 `Toml.parse`、
>   开关读取对接账本。
> **执行铁律：代码物理整抄（Fork & Trim），严禁从零自研！**
> S0 已完成骨架对位与存量搬迁，S1 是 Omarchy 源码整抄的主战场。Shell 侧直接复制
> `shell/references/omarchy/shell/services/PluginRegistry.qml` 原件至生产目录建立基线，
> 保留其进程守护与安全检查逻辑，再定向剪裁；Python 引擎侧严格按 Omarchy 契约 1:1 实现
> 命令流与快照咬合。动词契约唯一权威：[plugin-model](llms-wiki/plugin-model.md) §5；
> manifest 第三方词表与落位：[manifest-schema](llms-wiki/manifest-schema.md) 第三方章。

- **S1-0 裁决定案（2026-11-01，作者拍板）**：
  ① `update` 撞名 → **参数分派**：无参 = 引擎自更新（现状不动），`update <插件id>` =
     第三方插件更新；
  ② 7 门面 → **按消费者落度**：S0 定稿 kinds 词表无 bar-widget/menu/panel，5 门面 +
     BarWidgetRegistry 无 kind 消费者——PluginRegistry 心脏整抄照旧，门面与宿主注入
     工厂推迟（触发 = 首个三方 ui 插件真实样例），menu/bar-widget 专属件永久推迟登记
     delayed-decisions；
  ③ 来源真相 → **账本顶层 `sources` 键**（`{id: {url, commit, added}}`，与 `forms`
     键同模式，不碰五字段冻结）；
  ④ `add` 默认态 → **off**，`on` 启用，`--enable` 顺带；
  ⑤ orbit-launcher → **留一方**（noctalia manifest 声明），`radial-launcher` 动作从
     一方注册表推导路径，写死 `~/.config/noctalia/tools/` 全部退役。

- **分站（执行序即优先级，一站一收口）**：

| 站 | 交付 | 状态 |
| --- | --- | --- |
| S1-0 裁决过堂 | 五裁决落 wiki：plugin-model §5 八动词终态、manifest-schema 第三方章（落位 / reverse-DNS / 禁软链 / sources / 拒钩子）、omarchy-parity 改裁登记、overview 动词面与划词翻译失实句修正 | 已收口 |
| S1-1 落位与注册 | `Environment.data_dir`（XDG_DATA_HOME）+ registry 第三根 + 软链拒绝统一进扫描层 + TempEnv 补 `XDG_DATA_HOME` + `_MANIFEST_CACHE` 失效处理 | 已收口 |
| S1-2 生命周期动词 | `add`（clone → staging → 校验=加载同一套 → id 冲突 → 落位 → 记 sources）/ `remove`（停用 → 按所有权账本撤回 → 非管辖时间戳备份）/ `update <id>`（diff 预览 → 拒绝非 ff → 校验失败自动回退咬合快照重基线）；所有权账本回植（PR #148 素材剪裁）；git 传输原语（clone/fetch/ff 判定/diff/reset）落 `sources.py`（`timed_run` 直驱，不进 pkg/net 引擎自更新领地）；三方 v1 拒钩子 + `audit-lifecycle.py` 审计扩展；CLI / translations / operation-map 三闸门同批 | 已收口（audit 扩展改裁随 S1-3：该脚本审计 shell 树，三方 shell 面尚不存在；引擎侧静觉得等价物 = 加载时钩子门 + 词表封闭，已测。部署管线开缝 `registry.plugin_dir`——`_item_src` / `_app_src` / `_plugin_root` / `_is_deployable_app` 四点，第三方 config 类从此可过唯一事务管线） |
| S1-3 Shell 心脏整抄 | 806 行原件物理拷入 `shell/services/` 建基线（守护三件套 / 流解析 / 安全检查原样保留）；剪裁：二根扫描、开关读 StateProjection、删 shell.json 写入、走既有 `PluginManifest.js` TOML 通路；自研 192 行的 S0-2 投影（units / toggles / settingsRoutes / anchors / actions）并轨不丢失；首日 spike = 三方 ui kind 在 SlotHost 槽模型的落座规则；对抗门禁 = 手工塞临时三方插件 → 发现 → 移除全程零宿主文件改动 | 已收口（基线 `c91fc6a` cmp 字节一致 → 剪裁 429 行，整抄护栏 `TestThirdPartyHeart` 器官/疤痕双向钉死；S0-2 五视图并轨 + `unitId` 完整账本键贯通，槽仲裁改 kind 判定；能力标记随门面推迟、IpcRegistry 核对为既有通道覆盖，均入 omarchy-parity 补遗。首日 spike：S0-0 `external` case 20/20 已覆盖树外装载，S1-3 探针补四池取证入 loader-form §5。实机（沙箱 XDG + 三方探针）：冷启动零实例化 → `on` 挂载 → `off` 真实析构 → 热改 manifest 重扫重挂 → `shell.evil` 响亮拒绝 → 移除零残留，全程零宿主改动、零 ERROR。对抗门禁撞出两个预存在缺陷顺手清算：投影读退役账本键 `units`（S0-1 起开关轴空转，正名 `plugins`）+ 冷启动装配竞态（`primed` 闸门，禁用单元不闪挂）。门禁：tests/shell 282 绿（11 跳过=基线）、test_plugin_manifests 25 绿、五分类 110 绿、check.sh 过、lifecycle-audit 14 绿） |
| S1-4 首个用例贯通 | 上游 orbit-translate 补 manifest.toml（PR #5 已合入，纯裸名 id）；sources.py 支持安全裸名；网关（shell-action.sh / niri-scratch-toggle.sh / nyxuri-shell）接入 find_action_tool 动态发现，彻底消除 orbit-translate 硬编码，优先从 Nyxuri 插件数据域唤醒；sysdoctor 动态巡检脚本与 GtkLayerShell；端到端全链路 test_orbit_translate_pipeline 绿，实测在线 add WALKERKILLER/orbit-translate 成功 | 已收口 |
| S1-5 收口 | ROADMAP 回填、wiki 清算、全局门禁 4 过堂 | 待开始 |

- **扩展面边界**：钩子是引擎已有的语言无关扩展面（manifest 声明 + 任意可执行），
  不是新发明；用户已有配置的「导入」走保留策略（carry / vault），与第三方插件
  导入是两条线，语义永不混合。
- **安全立场**：插件是用户信任的代码——明说不沙箱、不做安全剧场；第三方包
  v1 拒绝钩子；能力声明 + `audit-lifecycle.py` 静态审计扩展。
- **非目标（v1 明确不做）**：插件间依赖声明（包依赖走 manifest packages、运行冲突
  走槽仲裁）；schemaVersion 迁移框架（只拒绝未知版本）。
- **Python 侧不引框架（裁决）**：pluggy / stevedore 管的是 Python-import 式扩展，
  与「声明 + 文件 + 钩子」形状不符；引擎即插件管理器本体，一套协议两个运行时。
  entry points（stdlib）为预留通道，第二个真实用例出现才建；pkg 后端窄驱动
  （pacman / apt，os-release 选择）随 #148 回植建立——不进 S1 主线，挂回植清单尾。

## 分支策略（PR #148 · Ubuntu 支持）

- PR #148（138 文件，+10519/−2532）整包暂存：自 main 建立 `legacy/ubuntu-support`，
  `gh pr edit 148 --base legacy/ubuntu-support` 后 merge（保署名）；该分支永不再
  rebase，仅作参考实现。分支操作待作者点头执行。
- **回植清单**（R0-3 / S1 落地后按图索骥）：包后端窄驱动（pacman/apt、os-release
  探测）、文件所有权账本。生命周期统一部分不回植——R0 以自身设计重实现。

## 冻结与挂起

- **T2 TUI Textual 重做**：选型 Textual、一次全搬定案不变；分支
  `archive/t2-textual-market` 备用，择机重启（M0 spike 先行：kitty 终端交接、
  中文对齐、退出干净）。
- **Shell 功能阉割档：整档挂起（作者裁决）**。dashboard 双轨合并（约 −5,900）已于
  2026-11-01 作者裁决**划掉——双轨终局保留**，退出候选。其余候选清单留档备查：
  cookie 时钟链（约 −870）、lock 双风格链（约 −1,000）、
  通知双渲染实现合一、regionselector（随 key-cli）、PersonalizationConfig 死函数
  （约 −340）、mango 第二合成器去留、BezierCurveLayerEditor（1,153 行）、
  WeatherBackground（1,226 行）；零风险小件（约 −490 行）若 S0 迁移触及则顺带
  处置，不立项。
- **T4 Shell 可控性与透明化**：待开工，开工时立细则；吸收 T0 让渡的 Shell 启动
  失败通知反馈。
- **T5 多合成器解耦**：门禁触发型；S0 的 niri 适配层兑现其前置——`SUPPORTED_WMS`
  硬编码、组件菜单特判、doctor 三处合成器字面量收编（债务登记见
  [delayed-decisions](llms-wiki/delayed-decisions.md)）。

## 已收口（本卷前置）

- **T0 终端体验**：复制粘贴终审落地（`Ctrl+Shift+C/V` 唯一路径，回归护栏在测试）；
  终端桥系统侧已修（`xdg-terminal-exec` 入位）。Shell 侧失败通知转 T4。
- **T1 上架 AUR**：`nyxuri-git` 上架（PKGBUILD 重构、依赖策略翻转、实机冒烟全过）；
  key-cli 暂缓，登记见 [shell/KNOWN-ISSUES](shell/KNOWN-ISSUES.md)。
- **T3 设置界面替换**：Caelestia 原子套件 M0–M2 完成；M3 待验收；M4 批 A–F 已落地
  （状态对账见 [shell/ROADMAP.md](shell/ROADMAP.md)）。剩余验收与资产收编随 S0 兑现。

## Shell 侧

阶段台账、P4 验收与门禁唯一见 [shell/ROADMAP.md](shell/ROADMAP.md)，此处不复述。
未收口项（壁纸域取色内生、matugen 退役）随 S0/S1 推进。长期目标保留不减：
启动器、壁纸/M3 调色、Noctalia TemplateAdapter、六大标准动作、双 Shell 切换与
伴生套件协同（契约见 [shell/AGENTS.md](shell/AGENTS.md)）。

## 全局门禁（每阶段验收都过）

1. 五原则验收给可复现证据（真诚透明 / 绝对主权 / 骨架包容 / 轻盈生长 /
   通用自然，见 [vision](llms-wiki/vision.md)）。
2. 单一开关真相与插件边界不变量的唯一权威在
   [plugin-model](llms-wiki/plugin-model.md) 与 [AGENTS.md](AGENTS.md)，此处只链接不复述。
3. 架构 / 命令 / manifest 变更同步对应 wiki 页与台账（路由见 AGENTS.md）。
4. 完成声明防幻觉：状态改「已完成」前必须有独立复核命令的原始输出作证，AI 转述
   不算证据；迁移类验收只认机器可查断言（旧路径物理消失、全库 grep 零命中、
   定向测试绿）。查不出证据就不算完成，发现假象状态立即回退。

## 储备（不承诺）

- 第三方目录站、信任分级与签名——git URL 即源成立后再议。
- 安全 Downdate 体系：现场快照优先还原 + Git 逆向检出的安全版本回退。
- i18n 三处（引擎 translations.toml / shell i18n / humans-wiki 双语页）受众不同，
  低优登记不动；humans-wiki 与 operation-map 的受众重叠同理。

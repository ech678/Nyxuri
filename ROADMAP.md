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
| S0 | Shell 骨架整抄 Omarchy：五件套 + 运行时插件注册表 + 设置去中心化（S0-0 装载 spike 门禁先行；manifest 协议 TOML 本站定稿） | 待开始 |
| S1 | 第三方插件生命周期：协议 1:1 + 四动词 + 所有权账本回植 | 待开始 |
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
  - **S0-0 装载 spike（门禁先行）**：在 Quickshell 0.3.2 的 qs-import Loader 缺陷
    （SlotHost 预热名单就是它的补丁）上验证注册表装载形态——升级 Quickshell 或
    替代装载机制二选一，产出结论与证据；未过不得开工 S0-2（S0-1 不受限）。
  - **S0-1 五件套机械迁移**：对照表全量执行 + import 机械扫 + 受影响定向测试
    改写绿；旧路径物理消失。
  - **S0-2 运行时注册表取代四件套**：手写 `UnitCatalog.qml` 镜像、`settings-routes.json`、
    `SearchCatalog.js` 生成器、`NexusNavPane.groupTable` 全部由 PluginRegistry 运行时读
    `manifest.toml` 取代——「新增插件 = 加目录 + manifest + 代码，零宿主改动」从口号
    变成事实；manifest 词表整批重写（杀词并轨 + 删冗余）随此落地，旧形态一处不留；
    shell/AGENTS.md 对应契约段随站修订。
  - **S0-3 设置去中心化**：设置页由插件自带（manifest settings schema / panel entry），
    宿主用 ui/ 原子控件渲染；中央设置窗降级为聚合 panel 插件。T3 双轨呈现
    （default / dashboard）去留**开工前**拍板，不留到迁移中途当阻塞。
  - **S0-4 资产收编与实机验收**：T3 M4 批 A–F 的积木原子控件与页面内容收编进 ui/
    与各插件；M3 / M4 实机验收证据在此产出。
  - **S0-5 合成器面清理（唯一实质大改，措辞正名）**：shell 现状本就是 niri
    （`NiriService` 直连 `NIRI_SOCKET`）——要清的是整抄代码里的 Hyprland 语义
    （`Quickshell.Hyprland` import、lock corners、dock workspace-layout，散布多处）。
    做法是抽 **CompositorDriver** 面 + niri 首驱动（socket / `niri msg` / key-cli
    收敛进一个驱动），不硬译 niri 字面量——兑现 T5 前置一次做对。
- **引擎侧波及（随站执行，不是顺手改）**：`nyxuri/kernel/registry.py` 的
  `shell/units/` 扫描路径与 `shell.<domain>` id 派生随 S0-1 改写；
  `test_unit_catalog` / `test_search_catalog` / catalog 门禁的新契约随 S0-2 定稿。
- **验收纪律**：防幻觉按全局门禁 4 执行；本站额外断言 = 对照表逐行核对、旧路径
  物理消失、import 全库 grep 零命中、受影响定向测试绿。

### S1 · 第三方插件生命周期

- **协议语义 1:1 Omarchy（载体 TOML，S0 定稿）**：`schemaVersion`、reverse-DNS `id`（官方保留裸名与
  `nyxuri.` 前缀）、`kinds`、`entryPoints`、settings schema、禁软链；安装绝不执行
  包内代码、无 install hook、无 sudo；`validate` 与加载时同一套检查。
- **动词终态八条**：`on / off / use / add / remove / update / doctor / list`。
  `add <git-url>`（本地目录路径顺带支持）；`remove` = 停用 → 按所有权账本撤回 →
  非管辖区时间戳备份；`update` = diff 预览、拒绝非 fast-forward、校验失败自动回退
  （咬合引擎快照）。
- **落位与消费**：第三方统一落 `~/.local/share/nyxuri/plugins/<id>/`
  （H4 数据目录 + H8 复制不软链）；kinds 路由消费——引擎消费 config 类、
  shell 注册表消费 ui 类。一个位置一份 manifest，两个注册表各取所需。
- **首个真实用例 · orbit-translate 接入（R0-5 取消自带的彻底改）**：上游补插件
  manifest（kinds / entryPoints，几行）；`add` 接管安装——落 share 目录后
  config_path 随入口推导，配置不再混 noctalia 生活区；`shell-action` 的
  `translate` / `radial-launcher` 动作与 sysdoctor 残留的 orbit 检查改按注册表
  消费，写死 `~/.config/noctalia/tools/` 路径退役。
- **扩展面边界**：钩子是引擎已有的语言无关扩展面（manifest 声明 + 任意可执行），
  不是新发明；用户已有配置的「导入」走保留策略（carry / vault），与第三方插件
  导入是两条线，语义永不混合。
- **所有权账本回植**：PR #148 素材（文件归属记录）支撑 remove 的精确撤回。
- **安全立场**：插件是用户信任的代码——明说不沙箱、不做安全剧场；第三方包
  v1 拒绝钩子；能力声明 + `audit-lifecycle.py` 静态审计扩展。
- **非目标（v1 明确不做）**：插件间依赖声明（包依赖走 manifest packages、运行冲突
  走槽仲裁）；schemaVersion 迁移框架（只拒绝未知版本）。
- **Python 侧不引框架（裁决）**：pluggy / stevedore 管的是 Python-import 式扩展，
  与「声明 + 文件 + 钩子」形状不符；引擎即插件管理器本体，一套协议两个运行时。
  entry points（stdlib）为预留通道，第二个真实用例出现才建；pkg 后端窄驱动
  （pacman / apt，os-release 选择）随 #148 回植建立。

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
- **Shell 功能阉割档：整档挂起（作者裁决）**。候选清单留档备查：dashboard 双轨
  合并（约 −5,900）、cookie 时钟链（约 −870）、lock 双风格链（约 −1,000）、
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

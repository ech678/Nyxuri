# Nyxuri 架构重塑卷台账历史（G0 · R0 · S0 · S1 归档冻结）

> 本文件是上一卷「架构重塑卷」（2026-10 ~ 2026-11）全部交付台账的永久归档冻结副本。
> 包含 G0（GitHub 已知问题修复）、R0（引擎收敛与单一激活管线）、S0（Shell 骨架整抄 Omarchy）、S1（第三方插件生命周期）的完整机器可查证据与设计裁决。
> 活跃演进路线已交接至根目录 [ROADMAP.md](../../ROADMAP.md) 的新卷「散文化与架构优雅化卷（P0 ~ P5）」。

---

## 一、 架构重塑卷收口全景

| 站 | 交付 | 状态 | 核心收口断言 / 证据 |
| --- | --- | --- | --- |
| G0 | 修复 GitHub 已知问题：独立修即时修，根因修随 R0 兑现 | 已收口 | #144 壁纸 XDG 路径化；#146 adw-gtk-theme 包声明；#143 渲染 phase 入事务；#145 壁纸收编声明式钩子；#147 形态矩阵显式化；#149 安装器派发事务；#142 转上游跟踪 |
| R0 | 引擎收敛：定名 Plugin + 杀词并轨 + 单一激活管线 + 声明贯通 + 减法外迁 | 已收口 | R0-1~R0-6 全数收口：单元→插件；forms 并轨；供给面处决（常用推荐软件整体退役）；orbit-translate 外迁上游；本地脏区清理 |
| S0 | Shell 骨架整抄 Omarchy：小写五件套 + 运行时注册表 + 设置去中心化 + 合成器驱动面 | 已收口 | S0-0~S0-5 全数收口：file:// URL 装载定案；五件套机械迁移；运行时注册表取代四件套；设置去中心化（panel/schema）；CompositorDriver 面隔离 Niri 方言 |
| S1 | 第三方插件生命周期：协议 1:1 + 生命周期动词 + Shell 心脏整抄 + 所有权账本回植 | 已收口 | S1-0~S1-5 全数收口：五大裁决过堂；add/remove/update 动词落地；Omarchy 806 行 PluginRegistry.qml 物理整抄；首个用例 orbit-translate 贯通 |

---

## 二、 逐站详细实施与验收记录

### G0 · 修复 GitHub 已知问题
- **可独立修（不依赖 R0，前向兼容）**：
  - #144 壁纸路径写死 `~/Pictures/Wallpapers`：manifest 目标与 `install-pack` 钩子接 `core.get_pics_dir()`（XDG）；R0-4 的 `xdg:` 词汇是它的推广形态。
  - #146 `adw-gtk-theme` 未声明：`units/theme/manifest.toml` 的 packages 补一行。
- **根因修（已随 R0-3 落地关闭）**：#143（事务渲染 phase 注入）、#145（壁纸包收编声明式钩子）、#147（hook-only 形态矩阵显式化）、#149（安装器组件勾选改派发事务）。
- **随外迁处置**：#142 划词翻译 PDF——已随 R0-5 转上游 [orbit-translate#1](https://github.com/WALKERKILLER/orbit-translate/issues/1) 跟踪，本仓库 issue 保持原样。

### R0 · 引擎收敛（架构重塑地基）
- **R0-1 概念定名：Plugin / 插件**。「单元」退役，三词术语收敛为 **插件 · manifest · 账本**。`units/` → `plugins/`（引擎蓝图目录，机械改；shell 侧随 S0）；账本键 `units.*` 提供一次性迁移（老安装升级路径）；[plugin-model](../plugin-model.md) 随本站改写；术语权威表述见 [vision](../vision.md) §1。
- **R0-2 杀词并轨**（已收口）：预设 + 零件合并为插件的**形态字段**——manifest `[presets]`/`[parts]` 并轨 `[forms]` 单节、账本 `preset` 字段改名 `form` + 顶层 `forms` 槽位字典（一次性迁移）、`deploy/preset.py` → `forms.py`、`use` 动词上位（`preset` 命令与 `on --preset` 降级 deprecated 别名，一版周期）；`presets/<app>.active` 双写退役（只读采纳一版周期，用户形态目录 `nyx_dir/presets` → `forms` 一次性迁移）；「源」概念删除（plugin-model §2 三词定案）；市场/工坊词退役（含 wiki 比喻改写「桌面插件引擎」）；`catalog.toml` 并轨——18 条「装但不部署」声明升格 manifest-only 插件（`deploy = false` 显式声明压过内容扫描，deps 菜单单源聚合 manifest）；保险库降级为 off 的内部机制、用户文案只剩「快照 / 收存」；`__custom__` 退出用户文档教学（模板作者文档保留冻结协议）；一条 apply 路径吃两轴（`_reconcile_active_parts` 旁路退役为 `replay_active_forms` 同路径重放）；
  **步 5 供给面处决（已执法）**：常用推荐软件安装整体退役——18 个仅包声明插件目录、`deploy = false` / `detect` 键（声明即解析报错）、`deps apps`（`opt`/`optional`）命令、安装器菜单项与部署后「常用软件」入口、`CategoryCheckboxList` 手风琴、`app_*`/`apps_cat_*` 文案全数清除；插件装包统一走 `nyxuri on <plugin>` 单路径，`deps` 收敛为核心依赖勾选单，greeter 形态仅声明单元（装包 + hooks + 落账）保留。
- **R0-3 单一激活管线**（已收口）：启用一个插件的步骤清单只留 transaction 一条——渲染 phase 入事务（Issue #143）、插件形态矩阵（runtime / merge / atomic / hook-only）manifest 化（Issue #147）、安装器组件勾选改派发事务（Issue #149）、壁纸包收编 wallpapers 声明式钩子（Issue #145）。兼容清扫同站执法（R0-2 一版周期期满）：`preset` 命令别名与 `on --preset` 旗标处决、`.active` marker 只读采纳 shim 处决、read_ledger 遗留迁移代码（units→plugins、preset→form、presets/parts→forms）处决。验收 = #143 / #145 / #147 / #149 契约绿。
- **R0-4 声明贯通与边界校验**（已收口）：manifest 路径词汇 XDG 化（推广为完整 8 类用户目录映射，模板图片目录中立化合一）；theme 副作用的包依赖声明与医生巡检（#146 根因，sysdoctor 补齐 adw-gtk-theme 在位性诊断）；叶名 / containment 校验进引擎（#48 的 `../../` 越界教训，core/registry/manifest/transaction 严格阻断逃逸）；保留策略按操作参数化——回滚默认精确恢复，支持显式 `--keep-custom` 保留并报告（#56）、更新尊重 Drifted 基线（#139 定案行为在此收编为契约）。
- **R0-5 减法外迁**（已收口）：orbit-translate 彻底外迁上游 [WALKERKILLER/orbit-translate](https://github.com/WALKERKILLER/orbit-translate)——程序、测试（≈3K 行）、CI、issue 全部上游自持（#142 → 上游 #1）。Nyxuri **取消自带**：`plugins/noctalia/tools/` 翻译器 payload 删除，用户经上游 `install.sh` 自装，S1 落地后 `nyxuri add` 接管；测试 `tests/tools/translate/` 删除。`orbit` 星环启动器**暂留**。`nyxuri/market/` 与 `tests/market/` 残留删除；本地脏区清理；本地 `pr-*` 分支清理。
- **R0-6 文档对齐**（已收口）：`plugin-model` / `forms` / `manifest-schema` 已随 R0-2 改写同步；剩余失实记录已按实况清算——旧卷「Cava/歌词/窗口预览死代码已清理」与代码不符（实况：地图已清，Cava 与歌词活着），`shell/ROADMAP` 历史决策句与 `shell/AGENTS` 红线 2 已改写为实况描述，`WeatherContent` 悬空 `weatherMapLoader` 残留随清算清除。

### S0 · Shell 骨架整抄（Omarchy 协议，小写命名）
- **整抄裁决**：作者定案——Omarchy 4 的插件系统、注册程序与骨架整包采纳；目录名保持小写开头风格（`Commons/Ui/plugins` → `commons/ui/plugins`）；不抄它的 `shell.json` 开关状态——单一开关真相继续留在引擎账本。
- **manifest 载体定案**：**TOML，彻底换代零兼容**。Omarchy 协议字段语义 1:1、载体不跟——`schemaVersion` / `kinds` / `entryPoints` / settings schema 并轨进 `manifest.toml` 单文件，引擎 registry 与 shell PluginRegistry 同读一份。
- **迁移对照表**：
  | 旧 | 新 |
  | --- | --- |
  | `shell.qml` | 不动（常驻宿主入口） |
  | `shared/utils` + `shared/theme` | `commons/` |
  | `shared/i18n` + `app/i18n` | `commons/i18n`（两份合一：词典 + I18n 单例） |
  | `shared/cards` + `app/cards` | `commons/cards`（两份合一） |
  | `shared/controls` + T3 M1 积木 | `ui/`（平面控件库） |
  | `app/services` | `services/`（+ PluginRegistry / PluginXxxApi） |
  | `shell/units/` | `plugins/`（每域 `manifest.toml` + entryPoints） |
  | `app/` 其余 | 不动（纯装配与宿主数据层） |
  | `scripts/` | 基本不动；例外：`generate-search-catalog.py` 与 catalog 门禁随四件套退役 |
- **分站实施证据**：
  - **S0-0 装载 spike（门禁先行）**（已收口）：验证注册表装载形态。结论：**file:// URL 装载形态定案**（release 0.3.2 与 master 9b0f339 双版本各 20/20）；证据见 [loader-form](../shell/loader-form.md)。
  - **S0-1 五件套机械迁移**（已收口）：对照表全量执行 + import 机械扫（旧根零命中）+ 引擎侧扫描路径随迁 + 受影响定向测试改写绿；实机验证四域复活（`shell status` → `IPC_READY`、compiled empty 零）。
  - **S0-2 运行时注册表取代四件套**（已收口）：手写 `UnitCatalog.qml`、`settings-routes.json`、`SearchCatalog.js` 生成器、`NexusNavPane.groupTable` 全部由 PluginRegistry 运行时读 `manifest.toml` 取代；16 路由 + 53 锚点 + 21 可搜索动作全部迁入 manifest。证据：`run-tests.py` 五分类 105+ 绿、`test_manifest` 59 绿、隔离实机冒烟 OK。
  - **S0-3 设置去中心化**（已收口）：设置页由插件自带（panel entry / schema 两种形态），中央设置窗降级为聚合 panel 插件。7 组域页面外迁 + `[[settings]]` 路由随迁各域 manifest。值域 schema 词表定稿（controls 五型封闭词表）。
  - **S0-4 资产收编与实机验收（收窄版）**（已收口）：`ui/MaterialCard`、`ui/SidebarStagger` 处决；`tests/shell` 282 绿、隔离实机 16 路由全 OK + 双轨翻转实机坐实。
  - **S0-5 合成器面清理**（已收口）：`CompositorDriver` 单例面 + `NiriDriver` 首驱动；13 处消费者改绑 `CompositorDriver`；清理零消费者死面（1321 → 约 830 行）；引擎侧 `nyxuri/compositors.py` 注册表吃掉 `SUPPORTED_WMS`。全量 991 测试全绿。

### S1 · 第三方插件生命周期
- **S1-0 裁决定案**：
  ① `update` 撞名 → **参数分派**：无参 = 引擎自更新，`update <插件id>` = 第三方插件更新；
  ② 7 门面 → **按消费者落度**；
  ③ 来源真相 → **账本顶层 `sources` 键**（`{id: {url, commit, added}}`）；
  ④ `add` 默认态 → **off**，`on` 启用，`--enable` 顺带；
  ⑤ orbit-launcher → **留一方**（noctalia manifest 声明）。
- **S1-1 落位与注册**（已收口）：`Environment.data_dir`（XDG_DATA_HOME）+ registry 第三根 + 软链拒绝统一进扫描层 + TempEnv 补 `XDG_DATA_HOME` + `_MANIFEST_CACHE` 失效处理。
- **S1-2 生命周期动词**（已收口）：`add`（clone → staging → 校验 → id 冲突 → 落位 → 记 sources）/ `remove`（停用 → 按所有权账本撤回 → 时间戳备份）/ `update <id>`（diff 预览 → 拒绝非 ff → 回退快照）；git 传输原语落 `sources.py`；部署管线开缝 `registry.plugin_dir`。
- **S1-3 Shell 心脏整抄**（已收口）：Omarchy 806 行原件物理拷入 `shell/services/`（守护三件套 / 流解析 / 安全检查保留），剪裁 429 行，基线 commit `c91fc6a` cmp 字节一致；实机（沙箱 XDG + 三方探针）：冷启动零实例化 → `on` 挂载 → `off` 析构 → 热改 manifest 重扫重挂 → `shell.evil` 响亮拒绝 → 移除零残留。
- **S1-4 首个用例贯通**（已收口）：上游 orbit-translate 补 manifest.toml（PR #5 合入）；网关动态发现彻底消除硬编码；端到端 test_orbit_translate_pipeline 绿，实测在线 add 成功。
- **S1-5 收口**（已收口）：运行时对齐 + Wiki 清算 + 全局门禁 4 过堂全绿。

# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段台账、当前阶段与门禁见
> [shell/ROADMAP.md](shell/ROADMAP.md)。
> 第一卷「插件市场化改造」KM0–KM5 已全数收口，台账冻结于 [archive/roadmap-history](llms-wiki/archive/roadmap-history.md)；
> 第二卷「架构重塑与三方插件」G0–S1 已全数收口，台账冻结于 [archive/reconstruction-history](llms-wiki/archive/reconstruction-history.md)；
> 设计哲学与五条简洁标准见 [vision](llms-wiki/vision.md)；
> 本卷为**第三卷「散文化与架构优雅化卷（P0 ~ P5）」**：以 `/home/ray/docs/lain-connect.md` 为唯一美学与秩序依归，
> 空间大一统、真·Omarchy 解耦、独立插件管理、统一 TOML 配置、引擎去企味，最后以 Sub-agents 全景深度审查作为最终检查任务收口。

## 主线收口（前两卷地基）

- **第一卷「插件市场化改造」（KM0–KM5）**：内核（registry · resolver · transaction · ledger）+ 万物皆插件 manifest + 账本单一真相成立，整卷台账冻结于 [archive/roadmap-history](llms-wiki/archive/roadmap-history.md)。
- **第二卷「架构重塑与三方插件」（G0–S1）**：定名 Plugin/插件、forms 杀词并轨、单一激活管线、Omarchy 五件套骨架整抄（TOML 协议定稿、设置去中心化、CompositorDriver 面）、S1 第三方生命周期（806 行 PluginRegistry 心脏整抄、sources 来源账、首个用例 orbit-translate 贯通），整卷台账冻结于 [archive/reconstruction-history](llms-wiki/archive/reconstruction-history.md)。

## 活跃路线（执行序即优先级）

| 站 | 交付 | 状态 |
| --- | --- | --- |
| P0 | 空间纯度大一统：根目录纯化 + PKGBUILD 修复 + 单测重心合一 + 消解 `shell/app/`（纯正 5 层） | 已完成 |
| P1 | 插件专属控制面与动态导航：独立 `PluginsPage` 插件管理 + 切除设置中心幽灵 Tab 根因 + Spotlight 联动 | 已完成 |
| P2 | 真 Omarchy 解耦与容错：切除 70 处跨插件静态引用 + 焚毁伪合规白名单 + 拔插容错（任意删插件宿主不崩） | 待开始 |
| P3 | 统一配置 TOML 化：升级 `Toml.js` 导出 `stringify` + 废除 7 个碎片 JSON，归拢为带注释的单一 `config.toml` | 待开始 |
| P4 | 引擎散文化与去企味重塑：处决 `ledger.py`/`transaction.py` 银行黑话 + 解构 913 行 `core.py`，消除 `kernel/core` 分裂人格 | 待开始 |
| P5 | **Sub-agents 全景深度审查与巡检验收（作为本卷最终检查任务，就像启动并发审查一样）** | 待开始 |
| T4 | Shell 可控性与透明化（开工时立细则） | 待开始 |
| T5 | 多合成器解耦（门禁触发） | 待开始 |
| T2 | TUI Textual 重做（暂缓，分支备用） | 待开始 |

### P0 ~ P5 · 散文化与架构优雅化专项（代码与空间大一统）

> **设计哲学依归**：`/home/ray/docs/lain-connect.md`（原始根面 Pristine Root、单一重心 Single Center of Gravity、散文化韵律 Prose-like Cadence、扁平几何 Flat Geometry、TOML-first、绝对解耦与极简秩序感）。
> 本专项直面当前系统的深层隐患：切除伪解耦与 70 处跨插件静态引用、消除设置中心幽灵 Tab、升级 `Toml.js` 统一 `config.toml`，并彻底处决 `ledger.py`/`transaction.py` 银行过度工程黑话，最后由 4-Agent 并发审计出具无保留合格结论闭环。

- **P0 空间纯度大一统 (Pristine Root & Workspace Purity) · 已收口**：
  - **清理根面瑕疵**：修复 `packaging/PKGBUILD:89` 中早该进历史的 `cp -a units catalog.toml` 遗留死指令；正式设计笔记收入 `notes/`；
  - **测试单重心**：将 `shell/tests/` 11 个文件（含 fixtures 与 sh 脚本）全量并入根 `tests/shell/`，全库只有唯一单测入口 `python3 -m unittest discover -s tests`（补齐 3 处未定义 i18n 词条）；
  - **消解 `shell/app/`**：将 `AppShell.qml` 并入 `shell.qml`（恢复 Omarchy 纯正宿主骨架），单例移入 `services/`，静态资产移入 `commons/assets/`，物理删除 `shell/app/`，严格呈现 Omarchy 纯正 5 层结构（`shell.qml`, `commons/`, `ui/`, `services/`, `plugins/`，全库切除 115 处 `import qs.app`）。
- **P1 插件专属控制面与动态导航 (Plugins Control Plane & Dynamic Nav) · 已完成**：
  - **切除幽灵 Tab 根因**：在 `ControlCenterWindow.qml:28-40` 注入 `StateProjection.isEnabledUnit(entry.pluginId)` 动态过滤；停用插件时，其设置 Tab 即刻从导航栏消失；
  - **独立“插件 (Plugins)”页面**：新增 `PluginsPage.qml`（`group = "system"`, `order = 125`，保持几何连续性），构建完整生命周期：
    - 内置插件：支持开/关切换、重置为默认配置（停用即移出视觉空间，明示不可物理删除）；
    - 第三方插件：支持 Git URL 安装（带 `--enable`）、在线检查更新、彻底卸载与打开源码目录；
  - **纯化 Shell 页面**：移除 `ShellPage.qml` 中的开关列表，正名为“系统运行状态与诊断”，专注 CPU/RSS 采样、日志、Niri 会话连接与诊断导出。
- **P2 真 Omarchy 解耦与容错 (True Decoupling & Fault Isolation)**：
  - **切除跨插件静态引用**：清除 `AppShell.qml`、`ThemeService.qml`、`SpotlightCatalog.qml` 对 `wallpaper` 和 `launcher` 的静态依赖；壁纸取色通过数据 Token 解耦；
  - **专属逻辑归位**：将 `DockService.qml` 移入 `plugins/dock/`，wallpaper 色彩算法移回 `plugins/wallpaper/`；
  - **焚毁伪白名单**：物理删除 `audit-lifecycle.py:74-82` 中的 `ALLOWED_MODULE_CROSS_IMPORTS` 白名单，将“零跨插件静态导入”设立为不可越过的 CI 铁律；
  - **热拔插容错验收**：单测断言任意物理删除/改名 `shell/plugins/` 下任一插件，Shell 宿主依然能够优雅自愈启动，主界面绝不发生 QML 编译报错。
- **P3 统一配置 TOML 化 (Unified Config Purity)**：
  - **赋予 QML 原生写 TOML 能力**：升级 `shell/commons/Toml.js`，导出内置 `smol-toml` 的 `stringify()` 方法；
  - **配置大一统**：在 `~/.config/nyxuri/` 废除 7 个碎片化 JSON，统一由单个 `config.toml` 管理主题、Dock、Bar、Idle 与显示配置；
  - **旧配置吸收**：首次启动自动吸收遗留 JSON 配置生成规整的 `config.toml` 并自动清理废弃 JSON。
- **P4 引擎散文化与去企味重塑 (Prose Architecture & De-Enterprization)**：
  - **处决过度工程命名**：
    - `nyxuri/kernel/ledger.py` → `nyxuri/state/store.py`；
    - `nyxuri/kernel/transaction.py` → `nyxuri/deploy/engine.py`；
    - 彻底从代码、注释与双语文案中清除“账本”、“事务”、“对账”等银行黑话；
  - **消灭双重人格**：
    - 彻底解散 `nyxuri/kernel/` 目录，引擎核心收敛为 `deploy/`、`state/`、`system/` 三大干净领域；
    - 解构 913 行的 `nyxuri/core.py`，清除根部平铺的 8 个散落脚本；
  - **散文化审美审查**：代码行文遵循散文韵律与左对齐扁平几何（Guard Clauses Over Pyramids）。
- **P5 Sub-agents 全景深度审查与巡检验收 (Final Deep Verification Task)**：
  - **整卷最终检查任务**：由 4 个并发 Sub-agent 进行深度穿透交叉审计（非单一 AI 转述），全员出具无保留合格结论并附原始输出作证：
    - **Agent 1（空间纯度与根面）**：检查根目录与包目录有无散落实现脚本、死代码或未被隔离的巨型杂物；
    - **Agent 2（解耦与真实可拔插）**：全库扫描 `import "../plugins/"`，严禁跨插件静态导入；测试随机物理删除/移动某个插件目录，宿主是否优雅容错绝不发生编译崩溃；
    - **Agent 3（状态机与视图联动）**：在后台切换插件启闭，检查 UI 视图、设置导航 Tab、全局搜索索引是否即时同步消失与出现，杜绝幽灵残留；
    - **Agent 4（命名去企味与散文化审美）**：审查代码圈复杂度、金字塔嵌套（强制 Guard Clauses），彻底清除非法企业黑话（如 ledger/transaction），配置坚守平坦纯洁的 TOML。
  - 查出任何一处硬编码、伪解耦或黑话违背，该阶段立即阻断，全部合格后方可收口第三卷。

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
- **T4 Shell 可控性与透明化**：架构重塑卷收敛后的首个用户体验与观测性专项。立项三件套：
  - **T4-1 启动可见性（吸收 T0 让渡）**：`Terminal=true` 与桌面应用通过 `xdg-terminal-exec` / `gio open` 启动失败时，Shell 侧由发后即忘（`execDetached`）升级为状态捕获与用户通知反馈（`notify-send` / Shell 告警），终态消除「点击无声无息失败」；
  - **T4-2 运行时透明度与生命周期诊断**：`nyxuri doctor` 与 `shell status` 输出插件挂载几何插槽状态、IPC 连通性与事件延迟指标；
  - **T4-3 异常隔离与弹性守护**：UI 插件或脚本发生运行时语法/渲染崩溃时局部熔断隔离并上报错误横幅，确保主 Shell 宿主与其它常驻插槽不瓦解。
- **T5 多合成器解耦**：门禁触发型；S0 的 niri 适配层兑现其前置——`SUPPORTED_WMS`
  硬编码、组件菜单特判、doctor 三处合成器字面量收编（债务登记见
  [delayed-decisions](llms-wiki/delayed-decisions.md)）。

## 已收口（本卷前置）

- **T0 终端体验**：复制粘贴终审落地（`Ctrl+Shift+C/V` 唯一路径，回归护栏在测试）；
  终端桥系统侧已修（`xdg-terminal-exec` 入位）。Shell 侧失败通知转 T4。
- **T1 上架 AUR**：`nyxuri-git` 上架（PKGBUILD 重构、依赖策略翻转、实机冒烟全过）；
  key-cli 暂缓，登记见 [shell-known-issues](llms-wiki/shell/known-issues.md)。
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

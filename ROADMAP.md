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
| P2 | 真 Omarchy 解耦与容错：切除 70 处跨插件静态引用 + 焚毁伪合规白名单 + 拔插容错（任意删插件宿主不崩） | 已完成 |
| P3 | 统一配置 TOML 化：升级 `Toml.js` 导出 `stringify` + 废除 7 个碎片 JSON，归拢为带注释的单一 `config.toml` | 已完成 |
| P4 | 引擎散文化与去企味重塑：处决 `ledger.py`/`transaction.py` 银行黑话 + 解构 913 行 `core.py`，消除 `kernel/core` 分裂人格 | 已完成 |
| P5 | **Sub-agents 全景深度审查与巡检验收（作为本卷最终检查任务，就像启动并发审查一样）** | 已完成 |
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
- **P2 真 Omarchy 解耦与容错 (True Decoupling & Fault Isolation) · 已完成**：
  - **切除 34 处跨插件/跨层静态引用（70+ 符号依赖全部解耦）**：`shell.qml`、`ThemeService.qml`、`SpotlightCatalog.qml`、`LauncherWindow.qml` 等切断对 `plugins/wallpaper`、`plugins/dock`、`plugins/settings` 的静态导入；
  - **领域专属与共享组件归位**：
    - `DockService.qml` 移入 `plugins/dock/`，拖拽状态与 `Launcher` 彻底通过 `ActionGateway.externalDragActive` 解耦，`DockService` 仅在运行时作为 `ActionGateway.dockHost` 注册；
    - Wallpaper 领域色彩算法移回 `plugins/wallpaper/`，色彩 Token 提取与静态判定抽取为无副作用的 `shell/commons/WallpaperSource.js`，动态宿主调用走 `ActionGateway.wallpaperHost`；
    - 共享工具提取至 `commons/`（`SpotlightCommands.js`, `SpotlightAppOrder.js`, `SpotlightSearch.js`, `cards/SystemCardDragState.js`）；跨域 UI 与呈现组件归位至 `services/`（`MediaPalette.qml`, `SystemCardDragSession.qml`, `NotificationContent.qml`）；
  - **焚毁伪合规白名单**：物理删除 `shell/scripts/dev/audit-lifecycle.py` 中 `ALLOWED_MODULE_CROSS_IMPORTS` 白名单（ARCH001 跨域导入零容忍），静态检查全库 542 个文件零违规；
  - **热拔插容错与契约测试**：新增 `tests/shell/test_plugin_decoupling.py`，断言全部 12 个插件 domain 零跨插件静态导入、宿主及共享层零插件引用，并实测热拔插遍历 12 个插件 domain 任意物理移出时其余全模块与静态检查依然 100% 干净；定向单测（96 项）全绿。
- **P3 统一配置 TOML 化 (Unified Config Purity) · 已完成**：
  - **赋予 QML 原生读写 TOML 全量能力**：升级 `shell/commons/Toml.js`，基于官方规范重导出 `smol-toml@1.9.1`（TOML v1.1.0 标准），完整导出 `parse()` 与 `stringify()`，零运行时外部依赖；
  - **单一物理重心与配置大一统**：实现 `shell/services/ConfigService.qml`，以单个原子 `FileView` 管理 `~/.config/nyxuri/config.toml`；废除 7 个碎片化 JSON（`config.json`, `dock.json`, `tray.json`, `quick-toggles.json`, `display-color.json`, `idle-policy.json`, `ui-preferences.json`）；
  - **领域服务全面解耦与收口**：`PersonalizationConfig`, `DockService`, `TrayService`, `QuickToggleConfig`, `DisplayColor`, `IdleService`, `UiPreferences` 彻底剥离独立 FileView 与散乱写回，通过 `ConfigService` 统一分发与防抖落盘；
  - **无感迁移与零残留**：通过 `shell/scripts/system/migrate_config.py` 在首次加载时自动吸收遗留 JSON 配置归拢入 `config.toml` 并安全解链清理旧文件；双语 i18n 词条同步净化死键；
  - **桌面 Python 生态无缝对接**：`nyxuri/system/theme.py` 与 `nyxuri/system/shell.py` 优先使用 Python 3.11+ 标准库 `tomllib` 读取 `config.toml`（保留 `config.json` 降级兜底）。
- **P4 引擎散文化与去企味重塑 (Prose Architecture & De-Enterprization) · 已完成**：
  - **处决过度工程命名与银行黑话**：
    - `nyxuri/kernel/ledger.py` → `nyxuri/state/store.py`；
    - `nyxuri/kernel/transaction.py` → `nyxuri/deploy/engine.py`；
    - `nyxuri/kernel/registry.py` + `resolver.py` → `nyxuri/deploy/catalog.py`；
    - 彻底从代码、注释、别名导入与双语文案中清除“账本”、“事务”、“对账”、“ledger”、“transaction”等企业黑话；
  - **消灭双重人格与分工正交重塑**：
    - 彻底解散 `nyxuri/kernel/`、`pkg/`、`desktop/`、`installer/` 与伪代理 `nyxuri/core.py`；
    - 引擎核心收敛为 4 个职责正交的清晰领域：`deploy/`（部署与蓝图）、`state/`（状态与快照）、`system/`（环境、包供给、桌面集成）、`ui/`（终端 UI 与整装交互）；根目录净空仅保留主入口与文案资源；
  - **散文化审美审查与机器状态纯化**：代码行文遵循散文韵律与左对齐扁平几何（Guard Clauses Over Pyramids），彻底清理 `state.json` 历史死键（`modules`/`shell_package`/`units` 等）与冗余元数据，收敛纯粹机器状态。
- **P5 Sub-agents 全景深度审查与巡检验收 (Final Deep Verification Task) · 已完成**：
  - **整卷最终检查任务**：由 5 个并发 Sub-agent 进行深度穿透交叉审计（非单一 AI 转述），全员出具无保留合格结论并附原始输出作证：
    - **Agent 1（空间纯度与根面）**：工作区净空零临时垃圾，修齐 `run-tests.py` 与 `check.sh` 开发门禁，`ResourceIntegrityTests` 抽离合流至根单测；清理死文档索引与打包陈旧注释；
    - **Agent 2（解耦与真实可拔插）**：全库扫描零跨插件静态导入；`ActionGateway` 动态注册完全对称；热拔插 12 域遍历沙箱测试 100% 容错无崩溃；`audit-lifecycle.py` 伪合规白名单彻底焚毁；
    - **Agent 3（状态机与视图联动）**：验证停用插件设置 Tab 秒级动态剥除与越界保护；Spotlight 动作拦截与壁纸联动正常；TOML 单重心读写防抖落盘稳定；`state.json` 净化历史死键；
    - **Agent 4（命名去企味与散文化审美）**：核心引擎 0 银行黑话残留、0 假别名垫片；修齐 `fish` 速查手册与更新测试用例中残留字样；代码圈复杂度与 Guard Clauses 几何规整；原生 Python 3.11+ `tomllib` 纯正对接；
    - **Agent 5（全局契约与路线图一致性）**：同步更新 `ROADMAP.md`、`shell/ROADMAP.md` 与 `llms-wiki/` 活跃页面，彻底清除解散包路径；`test_ai_specs.py` 增设防复辟硬门禁；双语 i18n 349 键 100% 契约合规。
  - **第三卷「散文化与架构优雅化卷（P0 ~ P5）」全卷正式圆满闭环收口**。

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
  key-cli 彻底废弃移除，登记见 [shell-known-issues](llms-wiki/shell/known-issues.md)。
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

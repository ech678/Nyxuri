# 上游参考资料与历史重现指南

> 本页说明本地参考树的来源、重现命令与检索方式；运行契约以源码与测试为准。

本工程在演进过程中参考了以下上游参考树。`shell/references/` 是可选本地检出位置（由根目录 `.gitignore` 排除），新环境中未必存在；缺少时须按固定上游提交获取，不凭本地搜索结果判断上游是否包含某个控件。

Bar 资源控件的补齐版本为 `pctrade/end4-pC` 提交 `b881970bfc25ff92b0f72b751c810a178c5fc677`（GPL-3.0-or-later）：`BarWidgetSwitcherArea`、`ClippedOutlineCircularProgress`、`ClippedFilledCircularProgress`、`ResourceCard`、`StyledProgressBar` 均先复制完整原件，再适配导入路径。颜色和动画仍使用本项目 Token；常用采样与显示默认值采用该版 Config 的 resources 字段。

其余参考：

## 1. 母体参考：Clavis (`clavis-15403b9`)
- **上游来源**：[StatIndet/quickshell](https://github.com/StatIndet/quickshell)
- **基准提交**：`15403b9`（对应主干 commit `91cdecb`）
- **重现与提取命令**（若在新环境需要考证原始 909 个文件）：
  ```bash
  # 从对应历史节点导出
  git archive --format=tar 15403b9 shell | tar -x -C /tmp/clavis-ref
  ```
- **检索方式**：参考树被 Git 忽略，检索原版须显式使用
  `rg --no-ignore shell/references/clavis-15403b9/shell`，
  不得因普通 `rg` 未命中而判断原功能不存在。
- **参考内容**：历史 UI 布局、参数 Token、动效曲线参考。Nyxuri Shell 在此基础上移除了 113 项自有 C++ 插件与 CMakeLists.txt，改用纯 QML/JS。

## 2. 纯逻辑架构参考：iNiR
- **设计启发**：按功能域组织模块、Niri IPC 集中式单一状态源服务（`app/services/NiriService.qml`）、去 C++ 化纯 QML 取向。
- **现行状态**：部分纯逻辑工具与资源消费者采用 Fork & Trim，文件头保留来源；`plugins/bar/ResourceUsageMonitor.qml` 基于 `snowarch/iNiR` 的 `28365436c2a00d083d29503aacfc0b5b321d67c6`（GPL-3.0），适配现有 SystemMonitorService 租约，不另起采样后端。

## 3. 设置界面与安卓视觉范式参考：Caelestia Shell (`caelestia`)
- **上游来源**：[caelestia-dots/shell](https://github.com/caelestia-dots/shell)
- **基准提交**：`2e1c51f`
- **检索方式**：参考树保持在本地 `shell/references/caelestia/`，由 `.gitignore` 排除。检索使用 `rg --no-ignore shell/references/caelestia`。
- **参考内容**：T3 Nexus 安卓风味（Material Design 3 Master-Detail）视窗与分组卡片范式——双行信息流分类导航（NavPane）、连通偏好设置原件（`ConnectedRect` 几何派生 `InfoRow` / `ToggleRow` / `SliderRow`）、大标题头部与 Hero Banner 设计参考。Nyxuri 在此基础上坚持纯 QML/JS、无外部二进制插件绑定并兼容现有 `SettingsBackend` 统一状态。

## 4. 插件系统与宿主骨架参考：Omarchy (`omarchy`)
- **上游来源**：[basecamp/omarchy](https://github.com/basecamp/omarchy)
- **基准提交**：`0740d1b`（完整克隆后检出钉住；GitHub 拒绝按 SHA 浅取，`--depth 1` 后 `git fetch origin 0740d1b` 不可用）
- **重现命令**（保留 `shell/` 全量 + 三份协议文档；`manual/` 只留 32 号插件指南，发行版用户手册与翻译目录不进参考树；本地树未就位时按此补拉再裁剪）：
  ```bash
  git clone https://github.com/basecamp/omarchy shell/references/omarchy
  cd shell/references/omarchy && git checkout 0740d1b
  find . -mindepth 1 -maxdepth 1 ! -name shell ! -name docs ! -name agents ! -name manual -exec rm -rf {} +
  find manual -mindepth 1 -maxdepth 1 ! -name 32-shell-plugins.md -exec rm -rf {} +
  rm -rf .git
  ```
- **检索方式**：参考树由 `.gitignore` 排除，检索使用 `rg --no-ignore shell/references/omarchy`（协议文档在 `shell/` 之外，勿把检索范围写死为 `omarchy/shell`）。
- **参考内容**：S0 骨架整抄的原始蓝本（根 [ROADMAP](../../ROADMAP.md) S0/S1）——`shell.qml` 常驻宿主 + `Commons/` `Ui/` `services/` `plugins/` 结构、`PluginRegistry` 运行时插件注册表、manifest 协议（`schemaVersion` / reverse-DNS `id` / `kinds` / `entryPoints`）的装载与校验实现、Quickshell 0.3.2 上插件动态加载的实跑解法。协议与骨架照抄、目录名小写化；其 `shell.json` 开关状态不抄（单一真相留在引擎账本）。**协议文档是 S1 的真值来源**：`docs/omarchy-shell.md`（manifest / IPC / shell.json 契约）、`manual/32-shell-plugins.md`（安装·克隆·分享生命周期）、`agents/skills/shell-dev.md`（插件作者契约）。逐资产「照抄 / 改造 / 拒绝」过堂台账见 [omarchy-parity](omarchy-parity.md)。

## 5. 纯 QML 视觉参考：end-4 (`end4-pC`)
- 本地已有 `shell/references/end4-pC/`（纯 QML 参考树，`.gitignore` 排除），历史上未单独立卷登记；来源与基准提交待考，检索用 `rg --no-ignore shell/references/end4-pC`。

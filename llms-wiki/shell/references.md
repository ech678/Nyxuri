# 上游参考资料与历史重现指南

> 本页说明本地参考树的来源、重现命令与检索方式；运行契约以源码与测试为准。

本工程在演进过程中参考了以下上游参考树。参考树保持在本地 `shell/references/`（由根目录 `.gitignore` 排除，不污染 Git 主分支）：

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
- **核心价值**：历史 UI 布局、参数 Token、动效曲线参考。Nyxuri Shell 已在此基础上彻底清除 113 项自有 C++ 插件与 CMakeLists.txt，实现 100% 纯 QML/JS 架构。

## 2. 纯逻辑架构参考：iNiR
- **设计启发**：按功能域组织模块、Niri IPC 集中式单一状态源服务（`app/services/NiriService.qml`）、去 C++ 化纯 QML 取向。
- **现行状态**：Nyxuri 已完全实现自主设计与独立单测，无任何外部代码直接拷贝。

## 3. 设置界面与安卓视觉范式参考：Caelestia Shell (`caelestia`)
- **上游来源**：[caelestia-dots/shell](https://github.com/caelestia-dots/shell)
- **基准提交**：`2e1c51f`
- **检索方式**：参考树保持在本地 `shell/references/caelestia/`，由 `.gitignore` 排除。检索使用 `rg --no-ignore shell/references/caelestia`。
- **核心价值**：T3 Nexus 安卓风味（Material Design 3 Master-Detail）视窗与分组卡片范式——双行信息流分类导航（NavPane）、连通偏好设置原件（`ConnectedRect` 几何派生 `InfoRow` / `ToggleRow` / `SliderRow`）、大标题头部与 Hero Banner 设计参考。Nyxuri 在此基础上坚持纯 QML/JS、无外部二进制插件绑定并兼容现有 `SettingsBackend` 统一状态。

## 4. 插件系统与宿主骨架参考：Omarchy (`omarchy`)
- **上游来源**：[basecamp/omarchy](https://github.com/basecamp/omarchy)
- **重现命令**（浅克隆即可，本地树未就位时按此补拉）：
  ```bash
  git clone --depth 1 --single-branch https://github.com/basecamp/omarchy shell/references/omarchy
  ```
- **检索方式**：参考树由 `.gitignore` 排除，检索使用 `rg --no-ignore shell/references/omarchy/shell`。
- **核心价值**：S0 骨架整抄的原始蓝本（根 [ROADMAP](../../ROADMAP.md) S0/S1）——`shell.qml` 常驻宿主 + `Commons/` `Ui/` `services/` `plugins/` 结构、`PluginRegistry` 运行时插件注册表、manifest 协议（`schemaVersion` / reverse-DNS `id` / `kinds` / `entryPoints`）的装载与校验实现、Quickshell 0.3.2 上插件动态加载的实跑解法。协议与骨架照抄、目录名小写化；其 `shell.json` 开关状态不抄（单一真相留在引擎账本）。

## 5. 纯 QML 视觉参考：end-4 (`end4-pC`)
- 本地已有 `shell/references/end4-pC/`（纯 QML 参考树，`.gitignore` 排除），历史上未单独立卷登记；来源与基准提交待考，检索用 `rg --no-ignore shell/references/end4-pC`。

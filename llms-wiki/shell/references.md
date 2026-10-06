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

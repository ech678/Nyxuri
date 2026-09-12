---
type: Playbook
title: Fisher 插件管理器模块
description: fisher 安装、插件版本固定、卸载清理范围。
resource: nyxniri/modules/fisher.py
tags: [fisher, fish, plugin, version-lock]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.5
  tier: short
  verdict: verified
  use_count: 1
---

# Fisher 插件管理器模块

## 设计要点

- fisher 本身是 fish 的插件管理器，NyxNiri 在安装时自动安装它
- 插件列表固定到已审查版本（不随 upstream 变动）
- 卸载时只清理 NyxNiri 通过 fisher 安装的插件，不动用户手动安装的插件

## 关键函数

- `fisher_installed()` — 检查 fisher binary 是否存在
- `fisher_install()` — 安装 fisher + 部署插件列表
- `fisher_uninstall()` — 移除 NyxNiri 管理的插件（保留 fisher 本体供用户继续使用）

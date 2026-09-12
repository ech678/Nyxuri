---
type: Playbook
title: 勾选式卸载
description: uninstall_nyxniri 执行顺序铁律、模块优先原则、legacy alias。
resource: nyxniri/state/uninstall.py
tags: [uninstall, checkbox, lifecycle]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.7
  tier: long
  verdict: verified
  use_count: 1
---

# 勾选式卸载

## 执行顺序铁律（§8.6）

1. **模块卸载先于 nyx_dir 删除**：fcitx 需要读取 `.prev` 状态文件，greeter 需要读取系统配置备份
2. **用户领土删除**：清理 nyxniri 创建的文件（configs/<app>/、wallpapers/）
3. **nyx_dir + state 最后**：快照目录、active 文件、CLI 软链

## uninstall_nyxniri(mode)

mode 参数：
- `""`（默认）/ `"1"` / `"safe"` / `"standard"` — 交互 checkbox 模式
- `"2"` / `"--restore"` / `"restore"` — 折叠到 rollback（保留快照）
- `"--all"` / `"purge"` — 同上但删除所有快照

非 TTY 时 fallback 到 standard scope（全量卸载）。

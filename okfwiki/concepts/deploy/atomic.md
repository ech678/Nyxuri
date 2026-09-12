---
type: Playbook
title: 原子替换部署
description: atomic_replace_item 合约——swap+preserve、Dunder __custom__ walk、glob 匹配规则。
resource: nyxniri/deploy/atomic.py
tags: [atomic, deploy, swap, preserve, dunder]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.95
  tier: long
  verdict: verified
  use_count: 1
---

# 原子替换部署

## atomic_replace_item(src, dest, preserve, chmod)

核心合约：
1. **快照 preserve**：manifest 声明的文件（如 niri/monitor.kdl）在 swap 前 copy 到 temp
2. **Swap**：`copytree(src, dest, ignore=_deploy_ignore_factory(src))`——删 repo-only 条目
3. **Restore preserve**：快照文件从 temp 还原
4. **chmod**：manifest 声明的 glob（如 `scripts/*.sh`）设置执行位
5. **清理 temp**：atexit 钩子兜底

## Dunder __custom__ Walk

`_deploy_ignore_factory` 自动跳过含 `__custom__` 的文件/目录（不管 glob 是否命中），保证用户自定义内容永不丢失。

## _matches_pattern(rel_str, is_dir, patterns)

支持两种模式：
- 无 `/`：按文件名匹配（`*.kdl`、`config.*`）
- 有 `/`：按相对路径匹配（`scripts/*.sh`、`presets/**`）
- dir pattern：`presets/` 结尾的 pattern 也匹配其子项

## _deploy_ignore_factory(root_src)

copytree ignore 回调：
- 永远跳过 `__pycache__`、`.module.toml`
- 顶层跳过 `presets/` 目录（预设由 preset 模块单独管理）
- 应用 include/exclude glob 过滤

---
type: Playbook
title: 快照生命周期
description: backup_configs 创建、rollback_configs 回滚、MAX_SNAPSHOTS=30 prune 上限。
resource: nyxniri/state/backup.py
tags: [backup, snapshot, rollback, prune]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.8
  tier: long
  verdict: verified
  use_count: 1
---

# 快照生命周期

## 快照目录

`~/.config/NyxNiri/backups/<snapshot_name>/`

命名规范（正则）：`snapshot_YYYYMMDD_HHMMSS[_extra]` 或 `pre_rollback_YYYYMMDD_HHMMSS[_extra]` 或 `dotfiles_backup_*`

## backup_configs(note, interactive, protected_snapshot)

1. 生成带时间戳的快照名
2. `copy_path(config_dir, snapshot_path)`（symlink-aware）
3. 写入 `note` 到 `<snapshot>/NOTE.txt`
4. 若超过 MAX_SNAPSHOTS（30），调用 `_prune_old_snapshots()` 清理最旧的非受保护快照

## rollback_configs(snapshot_path)

1. 验证 snapshot 路径在 backups/ 目录下且命名规范匹配
2. 备份当前 config_dir（创建新快照）
3. `remove_path(config_dir)` + `copy_path(snapshot_path, config_dir)`
4. 触发 post-install 服务重载

## list_backups() / get_all_backups()

扫描 backups/ 目录，返回排序后的快照列表（最新在前）。

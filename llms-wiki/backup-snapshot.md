# Backup Snapshot — 快照生命周期、回滚与防灾合约

> Nyxuri 的状态引擎负责为用户的 dotfiles 提供轻量、免依赖的原子快照与回滚。
> 源码：`nyxuri/state/backup.py`，快照根目录：`~/.config/nyxuri/backups/`。

## 快照存储拓扑

所有状态信息严格收拢在 Nyxuri 独立状态目录内，禁止向 `~/.config/` 根目录倾倒元数据：

```
~/.config/nyxuri/backups/
├── snapshot_20260912_140000/
│   ├── niri/
│   ├── kitty/
│   └── noctalia/
└── pre_rollback_20260912_143000/
```

## 核心机制

### 1. 自动容量修剪 (Prune)
- **硬限制**：`MAX_SNAPSHOTS = 30`。
- 每次创建新快照后，按时间戳升序排序，自动删除最旧的历史快照，防止磁盘无限膨胀。
- **保护机制**：支持传入 `protected_snapshot`，当前正在操作的目标快照绝不被意外 prune。

### 2. 回滚前自保 (Pre-rollback Safety)
执行 `rollback_configs()` 从历史快照还原配置之前，引擎会**强制为当前实机配置生成一份 `pre_rollback_` 快照**。即使用户回滚错了版本，也能再次反向恢复，杜绝数据丢失。

### 3. 精确恢复模式 (Preserve Custom Contract)
调用 `atomic_replace_item` 执行回滚还原时，传入 `preserve_custom=False`：
- 回滚的目标是精准还原该历史时刻的纯净状态。
- 若继承当前实机后期产生的 `__custom__` 文件，将导致回滚产生脏数据污染。因此回滚模式下不进行 Dunder 继承，确保还原一致性。

## CLI 接口

```bash
nyxuri snapshot create [note]   # 创建新快照
nyxuri snapshot list            # 列出所有可用快照（带序号与时间）
nyxuri snapshot rollback [id]   # 回滚到指定快照（回滚前自动生成安全快照）
```

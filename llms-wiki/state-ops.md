# State Ops — 快照生命周期与勾选式卸载

> 状态域两件事：snapshot（30 个滚动快照，防灾回滚点）与 uninstall（勾选式清理）。
> 源码：`nyxuri/state/backup.py`、`nyxuri/state/uninstall.py`；CLI 动词见
> [operation-map](operation-map.md)。

---

# 快照（snapshot / rollback）

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
- 回滚要还原快照当时的状态，不混入之后新增的自定义文件。
- 若继承当前实机后期产生的 `__custom__` 文件，将导致回滚产生脏数据污染。因此回滚模式下不进行 Dunder 继承，确保还原一致性。
- 回滚同样不走所有权 carry（#139）：裸调用默认 `carry=False`，受管文件精确还原快照内容，不保留实机侧偏离快照的改动（回滚前已有 `pre_rollback_` 快照兜底）。

## CLI 接口

```bash
nyxuri snapshot [note]          # 创建新快照（alias: backup）
nyxuri snapshot delete [index]  # 删除指定序号的快照
nyxuri list                     # 列出所有可用快照（带序号与时间）
nyxuri rollback [index]         # 回滚到指定快照（回滚前自动生成安全快照，alias: restore）
```


---

# 卸载（uninstall）

## 勾选清单

默认勾选 = 原 standard 范围（归档配置 + 删 CLI + 已装模块）。其余默认不勾。

```
用户配置          Nyxuri 自身        可选模块（已装的才显示）
[✓] configs       [✓] cli             [✓] fcitx  (~/.local/share/fcitx5/themes/nyxmellow/)
[ ] nyx_dir       [ ] state           [✓] gtk    (~/.config/gtk-3.0,4.0/gtk.css)
[ ] archives      [ ] cache           [✓] greeter [sudo]  (/etc/greetd, /etc/polkit-1, /var/lib/)
[ ] wallpapers                        [✓] fisher (~/.config/fish/functions/fisher.fish, conf.d/)
```

模块项只显示已装的（`fcitx5_installed` / `gtktheme_registered` / `greeter_installed` / fisher.fish 存在），旁边显示实际路径。

## CLI 适配

- `nyxuri uninstall`（无参）→ 交互勾选清单（默认 standard 范围）
- `nyxuri purge` / `uninstall --all` → 跳过勾选、全选 + 确认（等价完全卸载但补全历史遗留）
- 非交互式（管道，非 TTY）→ 默认全选 + 归档配置
- 检测到 system 模式 → 清单末尾提示"源码包归 pacman 管，完全卸载请再跑 `sudo pacman -R nyxuri-git`"

## 5 处历史 [gap]（已修复）

| 历史遗留问题 | 落在哪个勾选项 | 修复策略 |
|---|---|---|
| `~/.config/nyxuri_archive_*` 不清 | `[ ] archives` 独立项 | purge/全选时勾上，glob 清（只清预存的，保护当次新建的归档） |
| `/var/lib/noctalia-greeter/` 残留 | `[✓] Noctalia Greeter` 插件项 | `greeter` 插件 `hooks/deactivate` 执行 `sudo rm -rf /var/lib/...` |
| fisher + fish 插件谁都不清 | `[✓] fisher` 插件项 | `fish` 插件 `hooks/remove-fisher`：fish 在→`fisher remove --all`；不在→直接 rm conf.d/ 降级清理 |
| standard 漏调 greeter 清理 | `[✓] Greeter` 默认勾 | standard 范围默认包含 greeter 插件项 |
| 旧 quickphrase.conf 修改的清退 | `[✓] fcitx5-rime` 插件项 | `fcitx5-rime` 插件 `hooks/deactivate` 恢复热键并清理皮肤 |

卸载时带钩子插件（`HOOK_PLUGINS = ("fcitx5-rime", "fish", "greeter", "noctalia")`）统一经 `transaction.plugin_off(uid, cascade=True)` 调度执行其专属清理钩子。

## 卸载执行顺序

```
1. 插件钩子清理 FIRST   HOOK_PLUGINS (fcitx5-rime/greeter/fish/noctalia) 执行 plugin_off
                        （fcitx 读 state_dir 的 .prev 备份；greeter 的 sudo 在这步）
2. configs              归档后删（交互）/ 直接删（purge）
3. nyx_dir              ~/.config/nyxuri/（快照 + 预设；连带清理历史小写 ~/.config/nyxniri）
4. archives             只删预存的 Nyxuri_archive_*（保护 step 2 刚建的归档）
5. wallpapers           <XDG 图片目录>/Wallpapers/（如 ~/图片/Wallpapers，经 get_pics_dir 解析；读 .nyxuri-managed.json / .nyxniri-managed.json 仅清理受管壁纸，绝不误伤用户私人壁纸）
6. cli                  ~/.local/bin/nyxuri
7. state                ~/.local/state/nyxuri/（AFTER 插件钩子；连带清理历史小写目录）
8. cache                ~/.cache/nyxuri/（连带清理历史小写目录 ~/.cache/nyxniri）
```

**核心时序**：插件恢复先于 `~/.config/nyxuri/` 删除——fcitx 的 classicui/quickphrase 恢复要读 state_dir/nyx_dir 里的备份，备份目录必须活到插件恢复完成之后。删 Nyxuri dir 永远排在所有插件钩子之后。

> greeter（sudo / 系统领地）在 step 1（插件钩子阶段），技术上早于用户领地删除（step 2-8）。这优先满足钩子先于 nyx_dir 删除的原则；sudo 若失败时用户领地尚未删，反而更安全（未破坏用户环境，可重试）。

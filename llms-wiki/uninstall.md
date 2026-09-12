# Uninstall — 勾选式、5 处 [gap]、执行顺序铁律

> 卸载是**一个勾选清单**（替换旧的"三选一"），用户逐项选要清什么。源码：
> `nyxniri/state/uninstall.py`（`uninstall_nyxniri`）。

## 勾选清单

默认勾选 = 原 standard 范围（归档配置 + 删 CLI + 已装模块）。其余默认不勾。

```
用户配置          NyxNiri 自身        可选模块（已装的才显示）
[✓] configs       [✓] cli             [✓] fcitx  (~/.local/share/fcitx5/themes/nyxmellow/)
[ ] nyx_dir       [ ] state           [✓] gtk    (~/.config/gtk-3.0,4.0/gtk.css)
[ ] archives      [ ] cache           [✓] greeter [sudo]  (/etc/greetd, /etc/polkit-1, /var/lib/)
[ ] wallpapers                        [✓] fisher (~/.config/fish/functions/fisher.fish, conf.d/)
```

模块项只显示已装的（`fcitx5_installed` / `gtktheme_registered` / `greeter_installed` /
fisher.fish 存在），旁边显示实际路径（§8.4"每项旁边显示实际路径"）。

## CLI 适配

- `nyxniri uninstall`（无参）→ 交互勾选清单（默认 standard 范围）
- `nyxniri purge` / `uninstall --all` → 跳过勾选、全选 + 确认（等价旧 purge 但补全 5 处遗漏）
- 非交互式（管道，非 TTY）→ 默认全选 + 归档配置
- 检测到 system 模式 → 清单末尾提示"源码包归 pacman 管，完全卸载请再跑 `sudo pacman -R nyxniri-git`"

## 5 处历史 [gap]（全修）

| gap | 落在哪个勾选项 | 修法 |
|---|---|---|
| `~/.config/NyxNiri_archive_*` 不清 | `[ ] archives` 独立项 | purge/全选时勾上，glob 清（只清预存的，保护当次新建的归档） |
| `/var/lib/noctalia-greeter/` 残留 | `[✓] Noctalia Greeter` 模块项 | `greeter_uninstall` 加 `sudo rm -rf /var/lib/...`（`GREETER_STATE_DIR` 常量） |
| fisher + fish 插件谁都不清 | `[✓] fisher` 模块项 | 新增 `fisher_uninstall`（modules/fisher.py）：fish 在→`fisher remove --all`；不在→直接 rm conf.d/（降级，§8.6） |
| standard 漏调 greeter_uninstall | `[✓] Greeter` 默认勾 | standard 范围默认含 greeter 模块项 |
| 旧 quickphrase.conf 修改的清退 | `[✓] fcitx` 模块项 | 恢复旧版备份中仍由项目占用的热键；新版皮肤安装不再修改热键 |

`fisher_uninstall` 在 `nyxniri/modules/fisher.py`——fisher 现是一等模块（与 fcitx/greeter/gtk
同款 install|status|uninstall），由 deploy 流水线自动安装（同 gtk 被自动渲染）。卸载元组四项
全来自 modules/，归类一致。

## 执行顺序铁律（§8.6）

```
1. 模块卸载器 FIRST   fcitx/gtk/greeter/fisher 各自 *_uninstall
                       （fcitx 读 state_dir 的 .prev 备份；greeter 的 sudo 在这步）
2. configs            归档后删（交互）/ 直接删（purge）
3. nyx_dir            ~/.config/NyxNiri/（快照 + 预设 + active）
4. archives           只删预存的 NyxNiri_archive_*（保护 step 2 刚建的归档）
5. wallpapers         ~/Pictures/Wallpapers/
6. cli                ~/.local/bin/nyxniri
7. state              ~/.local/state/NyxNiri/（AFTER 模块卸载——.prev 活在这）
8. cache              ~/.cache/NyxNiri/
```

**铁律**：模块恢复先于 `~/.config/NyxNiri/` 删除——fcitx 的 classicui/quickphrase 恢复要读
state_dir/nyx_dir 里的备份，备份目录必须活到模块恢复完成之后。删 NyxNiri dir 永远排在所有
`*_uninstall` 之后。

> greeter（sudo / 系统领地）在 step 1（模块阶段），技术上早于用户领地删除（step 2-8）。
> 这优先满足铁律（模块先于 nyx_dir 删除）；sudo 若失败时用户领地尚未删，反而更安全（啥都没删，
> 可重试）。

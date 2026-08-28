# Preset Mechanism — active 状态、src 四分支、写时序、原子写、同步语义

> 预设机制的核心：活动选择存 state 文件（不占配置槽），deploy 时读它决定 src 是哪个目录。
> 写时序铁律 + 原子写堵死所有"半途崩溃留下错乱态"的故障路径。源码：`nyxniri/deploy/preset.py`。

## active 状态文件

`~/.config/NyxNiri/presets/<app>.active`——一行，内容是预设名或 `default`。不占配置槽
（这是扔掉 include 间接层、扔掉 `__preset__` 保留名的关键简化：一个概念减两份复杂度）。

- `read_active_preset(app)` → 文件不存在时返回 `"default"`，空白、读失败或非法内容会抛出 `InvalidActivePresetError` 并冻结部署
- `write_active_preset(app, name)` → **原子写**（temp + `os.replace`）。半写空文件会被
  拒绝并冻结部署——原子写堵死这条故障路径

## src 四分支（`resolve_preset_src(app, active, dest)`）

deploy 时根据 active 选源目录，四条分支 + 一条冻结：

1. **dest 不存在 + active≠default**（用户 `rm -rf ~/.config/<app>` 想重置但 active 还在）→
   `src=app_root`（默认配置）、`reset_active="default"`、若原 active 在仓库+用户都找不到则
   **额外警告**（上游改名/删除信息不能被静默吞）。这是唯一 **write-before-deploy** 例外
   （dest 已空，reset 后下次自愈）。
2. **active == "default"** → `src=app_root`（仓库默认配置）。
3. **官方预设**（`configs/<app>/presets/<active>/` 存在）→ `src=` 该目录。
4. **用户预设**（`~/.config/NyxNiri/presets/<app>/<active>/` 存在）→ `src=` 该目录。
   官方优先：同名时先查仓库再查用户。
5. **找不到** → `src=None`（冻结 dest + 警告），**绝不回 default**（会静默擦用户配置）。
   `~/.config/<app>` 保持当前内容、未重新部署，提示用户 `nyxniri preset <app> list` 选新的。

官方/用户优先级在 `elif` 链里：先 official、再 user、都没命中才冻结。

## 写时序铁律

**先 `atomic_replace_item` 成功，再写 `<app>.active`**。反过来（先写 active 再 deploy）一旦
中途崩了，active 指向新预设但 dest 还是旧的，下次读到 active 以为切好了就不重写，用户卡在
"显示新预设、实际旧配置"的错乱态。

- **apply 流程**（`apply_preset`）：`atomic_replace` → `_phase_render_templates(only_app=app)`
  → `write_active_preset`。deploy-then-write。write 失败（磁盘满/权限）会报错返回
  False——deploy 已落地、active 未记录，下次 update 按 default 重新部署。
- **dest-missing reset** 是 sanctioned write-before-deploy：dest 已空，reset 后下次自愈。
- **update 流程**（`_phase_atomic_deployment`）：active 本就正确，只在 dest-missing 时重置
  写 active；其余分支不重写 active。

## apply 的窄路径

`apply_preset` 只跑该 app 的 `atomic_replace` + 模板渲染，**不走**全流水线——不触发
`_phase_hardware_patches`（NVIDIA 解注释）和 `_phase_post_install_services`（fisher update /
theme-sync / gtk 重渲染）。切个 kitty 预设不该顺带跑 fisher，无关副作用违反"无熵"。

## update 同步语义（关键）

`update` 本身就是同步机制，不需要新命令。预设住在仓库里，仓库更新了预设源就更新了。

- **情况 1（新增预设）**：开发者加 `configs/kitty/presets/dark/` → 用户 update git pull 到 →
  下次 `preset kitty list` 扫 `configs/kitty/presets/*/` 直接看到。**零同步代码**，list 是 live 扫描。
- **情况 2（改预设内容）**：transparent 改了几行 → update pull 到新内容 →
  `offer_overwrite_upgrade` 触发 re-deploy → 读 active=transparent → src=新内容 → 部署。
  用户活动预设自动吃到最新版，`__custom__` 照常保留。
- **情况 3（删/重命名预设）**：active 还指旧名但仓库没了 → 不 deploy + 醒目警告（不回 default，
  不擦用户状态），把决定权留给用户。

符合"破坏性操作必须显式确认"的精神。doctor 还有 `_check_preset_drift`——平时不 update
也能撞见"你的 kitty 透明预设已不在上游"。

## CLI

```
nyxniri preset <app> list                # 列所有预设，* 标当前活动（list 即 status）
nyxniri preset <app> apply <name>        # 切预设（apply default = 回默认 = reset）
nyxniri preset <app> save <name>         # 当前配置存成用户预设（过滤 __custom__）
nyxniri preset <app> edit <name>         # 在 $EDITOR 里直接改用户预设目录（改完重新 apply 生效）
nyxniri preset <app> delete <name>       # 删用户预设（官方不能删）
```

`save` 拒 `default`（保留字）、拒官方同名（官方优先）。`delete` 同样拒这两类。`edit` 也拒这两类
（官方预设只读）——想改官方预设的口味，先 `apply` 它再 `save` 成用户预设。也可跳过命令，直接
编辑 `~/.config/NyxNiri/presets/<app>/<name>/` 里的文件，`apply` 即部署。

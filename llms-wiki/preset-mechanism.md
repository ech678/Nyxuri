# Preset Mechanism — active 状态、src 四分支、写时序、原子写、同步语义

> 预设机制的核心：活动选择存 state 文件（不占配置槽），deploy 时读它决定 src 是哪个目录。
> 写时序铁律 + 原子写堵死所有"半途崩溃留下错乱态"的故障路径。源码：`nyxuri/deploy/preset.py`（底层引擎）+ `nyxuri/desktop/presets.py`（工作流动词）。

## active 状态文件

`~/.config/nyxuri/presets/<app>.active`——一行，内容是预设名或 `default`。不占配置槽
（这是扔掉 include 间接层、扔掉 `__preset__` 保留名的关键简化：一个概念减两份复杂度）。
同时同步记录至 `~/.local/state/nyxuri/state.json` 账本（`presets` 字典）。
`read_active_preset` 以**文件为权威**：读取不修改账本；文件（或其所在目录）
缺失时兜底读账本，账本同样没有才回落 `"default"`。

- `read_active_preset(app)` → 文件缺失走账本兜底，仍无则返回 `"default"`；空白、读失败或非法内容会抛出 `InvalidActivePresetError` 并冻结部署
- `write_active_preset(app, name)` → **原子写**（temp + `os.replace`）并同步更新 `state.json`。半写空文件会被
  拒绝并冻结部署——原子写堵死这条故障路径

## src 四分支（`resolve_preset_src(app, active, dest)`）

deploy 时根据 active 选源目录，四条分支 + 一条冻结：

1. **dest 不存在 + active≠default**（用户 `rm -rf ~/.config/<app>` 想重置但 active 还在）→
   `src=app_root`（默认配置）、`reset_active="default"`、若原 active 在仓库+用户都找不到则
   **额外警告**（上游改名/删除信息不能被静默吞）。这是唯一 **write-before-deploy** 例外
   （dest 已空，reset 后下次自愈）。
2. **active == "default"** → `src=app_root`（仓库默认配置）。
3. **官方预设**（`units/<app>/__presets__/<active>/` 或 `presets/<active>/` 存在）→ `src=` 该目录。
4. **用户预设**（`~/.config/nyxuri/presets/<app>/<active>/` 存在）→ `src=` 该目录。
   官方优先：同名时先查仓库再查用户。
5. **找不到** → `src=None`（冻结 dest + 警告），**绝不回 default**（会静默擦用户配置）。
   `~/.config/<app>` 保持当前内容、未重新部署，提示用户 `nyxuri preset <app> list` 选新的。

官方/用户优先级在 `elif` 链里：先 official、再 user、都没命中才冻结。

## 写入与事务边界

`apply_preset` 只接受已启用的目录单元；`target` 单文件、`merge` 和 `runtime` 单元不提供
整包预设。选择无效或冲突界面取消时不修改文件、active 或账本。

切换通过 `unit_on(..., preset=name, refresh=True, run_hooks=False)`：校验预设与依赖状态，
披露冲突，必要时先建恢复快照，再原子复制、提交选择、渲染本次实际写入的模板、记录基线。
保留的个人内容不参与渲染，不以当前内容重建基线；外来文件保留。文件提交后出错保留 pending，
返回失败，不能把多处写入视作跨文件系统的原子提交。

切换不运行安装钩子，只执行该 manifest 的 `preset_reload`。删除用户预设时拒绝删除当前
活动选择；先明确切换到其他预设，再删除原目录，避免界面显示与实机文件错位。

`resolve_preset_src` 保留底层部署工具的 dest-missing 行为；单元事务显式解析活动预设，
首次 `on --preset` 即使目标不存在也使用指定预设，不自动改为 default。

## update 同步语义（关键）

`update` 本身就是同步机制，不需要新命令。预设住在仓库里，仓库更新了预设源就更新了。

- **情况 1（新增预设）**：开发者加 `units/kitty/__presets__/dark/` → 用户 update git pull 到 →
  下次 `preset kitty list` 扫 `units/kitty/__presets__/*/` 直接看到。**零同步代码**，list 是 live 扫描。
- **情况 2（改预设内容）**：transparent 改了几行 → update pull 到新内容 →
  `offer_overwrite_upgrade` 触发 re-deploy → 读 active=transparent → src=新内容 → 部署。
  用户活动预设自动吃到最新版，`__custom__` 照常保留。
- **情况 3（删/重命名预设）**：active 还指旧名但仓库没了 → 不 deploy + 醒目警告（不回 default，
  不擦用户状态），把决定权留给用户。

符合"破坏性操作必须显式确认"的精神。doctor 还有 `_check_preset_drift`——平时不 update
也能撞见"你的 kitty 透明预设已不在上游"。

## 预设继承与通用零件插槽体系（Parts Slots）

配置体系支持应用级整包预设与解耦的声明式零件插槽（Parts）：

- **通用零件插槽 (`preset <app> part <slot> <name>`)**：
  - 核心逻辑由 `nyxuri.deploy.preset` 提供（`list_parts`、`apply_part`、`get_active_part`）。
  - 元数据在单元根目录 `units/<unit>/manifest.toml` 的 `[parts.<slot>]` 声明（如 Niri 声明了 `[parts.effects]` 与 `[parts.glow]`）。
  - 零件源模板存放于 `units/<app>/__presets__/<source_dir>/`，目标为具体的配置零件（如 `target = "effects_normal.kdl"` 或 `target = "glow.kdl"`）。
  - 声明在 `[parts.<slot>]` 的 `target` 在解析 manifest 时会自动追加至受保护清单（`preserve`），避免全量替换时被覆盖。
  - **防覆写自愈（commit `db289bd`）**：在部署与重载流水线中，`_reconcile_active_parts` 机制会自动读取 `state.json` 账本中已激活的非默认变体并对齐应用，确保配置重新应用时零件插槽目标不被默认模板回退。
- **稀疏预设 (Sparse Presets)**：应用级整包预设目录仅存放与底版有差异的文件，未重写的文件自动从底版继承。
  - **白名单保障**：由 `manifest.toml` 中的 `allow` 与 `include` 控制继承白名单与匹配范围。
- **动态光晕模板解耦**：Niri 的 `glow-material-you` 由 Noctalia 原生渲染输出为独立的 `~/.config/niri/colors.kdl`，不再覆写核心布局 `layout.kdl`；`config.kdl` 中在 `layout.kdl` 之后通过 `include optional=true "colors.kdl"` 引入。

## CLI

```
nyxuri preset <app> list                # 列所有预设，* 标当前活动（list 即 status）
nyxuri preset <app> apply <name>        # 切预设（apply default = 回默认 = reset）
nyxuri preset <app> save <name>         # 当前配置存成用户预设（过滤 __custom__）
nyxuri preset <app> edit <name>         # 在 $EDITOR 里直接改用户预设目录（改完重新 apply 生效）
nyxuri preset <app> delete <name>       # 删用户预设（官方不能删）
nyxuri preset <app> parts               # 查询应用声明的所有零件插槽及其可用变体
nyxuri preset <app> part <slot> <name>  # 切换通用零件插槽（如 nyxuri preset niri part effects xray-blur）
```

`save` 拒 `default`（保留字）、拒官方同名（官方优先）。`delete` 同样拒这两类。`edit` 也拒这两类
（官方预设只读）——想改官方预设的口味，先 `apply` 它再 `save` 成用户预设。也可跳过命令，直接
编辑 `~/.config/nyxuri/presets/<app>/<name>/` 里的文件，`apply` 即部署。冲突可用 `apply <name> --force` / `part <slot> <name> --force` 备份后覆盖。

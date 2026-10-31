# Form Mechanism — 形态轴、use 动词、账本真相、写时序、原子写、同步语义

> 形态机制的核心：活动选择存账本（整型轴在插件记录的 `form` 字段，槽位轴在顶层
> `forms` 字典），deploy 时读它决定 src 是哪个目录。写时序铁律 + 原子写堵死所有
> 「半途崩溃留下错乱态」的故障路径。源码：`nyxuri/deploy/forms.py`（底层引擎）+
> `nyxuri/desktop/forms.py`（工作流动词）。唯一动词：`nyxuri use`。

## 两根形态轴（R0-2 杀词并轨）

预设 + 零件已并轨为插件的**形态字段**，由 `use` 动词承载（形态轴不设名词）：

1. **整型形态轴（whole axis）**：应用级整包变体。目录约定隐式声明——
   `plugins/<plugin>/__forms__/<名>/`，`default` 即插件根目录。
2. **槽位形态轴（slot axes）**：单文件热插拔。manifest `[forms.<slot>]` 声明
   （`target` / `source_dir` / `default`），源模板住 `__forms__/<source_dir>/`。

## 活动形态状态（账本单真相）

- **整型轴** → 插件账本记录的 `form` 字段（五字段冻结形状之一）。
  从未切换的插件读出 `"default"`。
- **槽位轴** → 账本顶层 `forms` 键：`{<plugin>: {<slot>: <变体>}}`。

**历史兼容（一版周期，R0-3 清扫）**：退役的 `~/.config/nyxuri/forms/<app>.active`
marker 文件只读不写——读到合法值即采纳进账本并删除文件；非法内容告警后忽略
（账本是唯一真相，垃圾 marker 不再冻结部署）。用户形态存储目录已从
`nyx_dir/presets/` 一次性迁移至 `nyx_dir/forms/`（同一文件系统，目录原子改名）。

- `read_active_form(app)` → 账本记录为准；账本缺失时采纳遗留 marker，仍无则 `"default"`
- `write_active_form(app, name)` → 落账本记录（保留既有记录的 state/files/vault；
  从未切换的插件合成 `disabled` 记录——无归档物，`vault` 为 null），并顺手删除遗留 marker

## 整型轴 src 四分支（`resolve_form_src(app, active, dest)`）

deploy 时根据活动形态选源目录，四条分支 + 一条冻结：

1. **dest 不存在 + active≠default**（用户 `rm -rf ~/.config/<app>` 想重置但 active 还在）→
   `src=app_root`（默认配置）、`reset_form="default"`、若原形态在仓库+用户都找不到则
   **额外警告**（上游改名/删除信息不能被静默吞）。这是唯一 **write-before-deploy** 例外
   （dest 已空，reset 后下次自愈）。
2. **active == "default"** → `src=app_root`（仓库默认配置）。
3. **官方形态**（`plugins/<app>/__forms__/<active>/` 存在）→ `src=` 该目录。
4. **用户形态**（`~/.config/nyxuri/forms/<app>/<active>/` 存在）→ `src=` 该目录。
   官方优先：同名时先查仓库再查用户。
5. **找不到** → `src=None`（冻结 dest + 警告），**绝不回 default**（会静默擦用户配置）。
   `~/.config/<app>` 保持当前内容、未重新部署，提示用户 `nyxuri use <app> list` 选新的。

## 写时序铁律

**先原子部署成功，再落账本形态**。反过来（先写形态再 deploy）一旦中途崩了，
形态指向新变体但 dest 还是旧的，下次读到形态以为切好了就不重写，用户卡在
「显示新形态、实际旧配置」的错乱态。

- **use 流程**（`use_form`）：atomic swap → 模板渲染 → chmod → 槽位重放 →
  落账本 → reload。deploy-then-write。落账失败会报错返回 False——部署已落地、
  形态未记录，下次 update 按 default 重新部署。
- **dest-missing reset** 是 sanctioned write-before-deploy：dest 已空，reset 后下次自愈。
- **update 流程**（`_phase_atomic_deployment`）：形态本就正确，只在 dest-missing 时重置
  落账；其余分支不重写。

## 一条 apply 路径

`use_form(app, axis, value)` 是唯一形态切换路径（R0-2）：`axis=None` 走整型轴，
`axis=<slot>` 走槽位轴——preset + part 两条旧路径与 `_reconcile_active_parts`
旁路已退役。整型轴切换后，账本记录的槽位选择经同一实现重放
（`replay_active_forms`），部署流水线与 `use` 共用，槽位目标不会被默认模板回退。

## use 的窄路径

`use_form` 整型轴只跑该插件的 atomic swap + 模板渲染，**不走**全流水线——不触发
`_phase_post_install_services`（fisher update / theme-sync / gtk 重渲染）。切个 kitty
形态不该顺带跑 fisher，无关副作用违反「无熵」。

## update 同步语义（关键）

`update` 本身就是同步机制，不需要新命令。官方形态住在仓库里，仓库更新了形态源就更新了。

- **情况 1（新增形态）**：开发者加 `plugins/kitty/__forms__/dark/` → 用户 update git pull 到 →
  下次 `use kitty list` 扫 `plugins/kitty/__forms__/*/` 直接看到。**零同步代码**，list 是 live 扫描。
- **情况 2（改形态内容）**：transparent 改了几行 → update pull 到新内容 →
  `offer_overwrite_upgrade` 触发 re-deploy → 读 active=transparent → src=新内容 → 部署。
  用户活动形态自动吃到最新版，`__custom__` 照常保留。
- **情况 3（删/重命名形态）**：active 还指旧名但仓库没了 → 不 deploy + 醒目警告（不回 default，
  不擦用户状态），把决定权留给用户。

符合「破坏性操作必须显式确认」的精神。doctor 还有 `_check_form_drift`——平时不 update
也能撞见「你的 kitty transparent 形态已不在上游」。

## 形态继承与槽位轴（manifest `[forms]` 单节）

配置体系支持整型形态与解耦的槽位轴，全部住在 manifest 的 `[forms]` 单节：

```toml
[forms]              # 整型轴旋钮（可选）
inherit = true
allow = ["glow"]
include = ["scripts/**", "*.kdl"]
exclude = ["*.bak"]
reload = ["niri", "msg", "action", "reload-config"]

[forms.effects]      # 槽位轴声明
target = "effects_normal.kdl"
source_dir = "effects"
default = "default"
```

- **槽位轴**：`target` 在解析 manifest 时自动追加至受保护清单（`preserve`），
  避免全量替换时被覆盖；`_apply_slot` 单文件原子置换 + 落账 `forms` 字典 + reload。
- **防覆写自愈**：部署与重载流水线经 `replay_active_forms` 自动对齐账本中已激活的
  非默认变体（原 `_reconcile_active_parts` 旁路退役后的同路径重放）。
- **稀疏形态 (Sparse Forms)**：整型形态目录仅存放与底版有差异的文件，未重写的文件
  自动从底版继承。白名单/黑名单由 `[forms]` 的 `allow` / `standalone` / `include` /
  `exclude` 控制（黑名单绝对否决 > 白名单匹配 > inherit 总开关）。
- **动态光晕模板解耦**：Niri 的 `glow-material-you` 由 Noctalia 原生渲染输出为独立的
  `~/.config/niri/colors.kdl`，不再覆写核心布局 `layout.kdl`；`config.kdl` 中在
  `layout.kdl` 之后通过 `include optional=true "colors.kdl"` 引入。

## CLI（`use` 动词；`preset` 为 deprecated 别名，一版周期后删除）

```
nyxuri use <插件> list                # 列所有形态，* 标当前活动（list 即 status）
nyxuri use <插件> <形态>              # 切形态（default = 回默认 = reset）
nyxuri use <插件> save <名>           # 当前配置存成用户形态（过滤 __custom__）
nyxuri use <插件> edit <名>           # 在 $EDITOR 里直接改用户形态目录（改完重新 use 生效）
nyxuri use <插件> delete <名>         # 删用户形态（官方不能删）
nyxuri use <插件> slots               # 查询插件声明的所有槽位轴及可用变体
nyxuri use <插件> slot <轴> <变体>    # 切换槽位轴（如 nyxuri use niri slot effects xray-blur）
```

`save` 拒 `default`（保留字）、拒官方同名（官方优先）。`delete` 同样拒这两类。`edit` 也拒
（官方形态只读）——想改官方形态的口味，先切它再 `save` 成用户形态。也可跳过命令，直接
编辑 `~/.config/nyxuri/forms/<插件>/<名>/` 里的文件，切换即部署。

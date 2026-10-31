# Plugin Model — 插件模型、内核架构与极简契约

> 本页是 Nyxuri 插件模型、内核架构、状态机与 Manifest Schema v2 的唯一权威契约；
> 运行时行为与单测以 `tests/test_plugin_model.py` 为准。

---

## 1. 物理空间三对偶与不变量

系统由三个物理隔离的空间与一条单向中轴连接，互不侵犯：

```
┌────────────────────────────────┐
│   空间 A：源码蓝图 (Blueprint)  │  只读，版本受控，平铺所有插件目录
│   路径：plugins/<plugin>/          │  （永不向此处写入运行时状态）
└───────────────┬────────────────┘
                │
                │  中轴：nyxuri.deploy.atomic
                │  （哈希比对、原子替换、模板渲染、Dunder/Preserve 继承）
                ▼
┌────────────────────────────────┐       停用归档 (Vault In)       ┌─────────────────────────────────┐
│   空间 B：实机生活区 (Living)   │ ──────────────────────────────► │   空间 C：状态与保险域 (State)   │
│   路径：~/.config/<target>/    │ ◄────────────────────────────── │   路径：~/.local/state/nyxuri/  │
│   （用户的日常桌面生活环境）    │       启用恢复 (Vault Out)      │   - state.json (单一真相账本)    │
└────────────────────────────────┘                                 │   - vault/<plugin>/ (自定义备份)  │
                                                                   │   - backups/ (30 个滚动快照)    │
                                                                   └─────────────────────────────────┘
```

### 空间不变量
1. **源码绝对只读**：`plugins/` 永远是只读蓝图。严禁在源码树建软链接，严禁向源码树写状态（插件钩子注入 `PYTHONDONTWRITEBYTECODE=1`，钩子引引擎代码也不得落 `__pycache__`）。
2. **实机白纸洁癖**：未启用的插件在实机 `~/.config/<target>` 必须 100% 抹净，不留任何受管文件或幽灵残留。
3. **心血零丢失**：插件停用时，用户的自定义文件（`__custom__` 与 `preserve`）原样存入空间 C 的 `vault/<plugin>/`；实机还原纯白，心血在保险库有据可查。

---

## 2. 四大法定术语 (The 4 Canonical Primitives)

全库统一且仅承认以下四个词：

| 术语 | 英文 | 本质定义 | 物理承载 | 行为边界 |
|---|---|---|---|---|
| **插件** | `Plugin` | 桌面上**一切可独立开关**的原子能力实体。 | `plugins/<plugin>/` 目录 | 拥有独立的生命周期与状态，可声明依赖、文件与预设。 |
| **内核** | `Kernel` | Nyxuri 常驻骨架，负责编排与记账（纯 Python 标库）。 | `nyxuri/kernel/{registry, resolver, transaction, ledger}` | **内核不是插件**，不可插件化、不可开关，是承载一切的物理底座。 |
| **源** | `Source` | 插件的供给方与索引来源。 | 本地抽象 `local:builtin`（对应 `plugins/`） | 本阶段仅维持单一本地内置源，推迟网络多源。 |
| **manifest** | `Manifest` | 插件的自描述规格书。全库统称 `manifest.toml`。 | `plugins/<plugin>/manifest.toml` | 纯声明式静态元数据，**全字段可选，无文件 = 全默认**。 |

### 严正排除项
* **系统软件包（pacman / AUR / Flatpak 包）**：不是插件！它们只是插件声明书里写的 `dependencies`。
* **仅包声明插件（packages-only，R0-2 catalog 并轨）**：是插件！`nautilus`、`qq` 这类
  「装但不部署」的声明住各自 `plugins/<name>/manifest.toml`（只有 packages / label /
  category / detect，无部署物、无生活区）；`on` = 装包 + 落账，`off` = 纯落账——
  与 runtime 插件同形，但拥有真实的包世界投影（deps apps 菜单与安装器）。
  原 KM3.5 的根 `catalog.toml` 已随 R0-2 并轨处决（见 §7 死刑清单）。

### 内核分层契约（依赖方向冻结）

四个内核模块呈星形单向分层，物理承载 `nyxuri/kernel/`（KM3.5 正名）：**transaction 是唯一允许多依赖的编排层，其余三件互不认识**。

```
transaction（编排：唯一可触碰副作用的模块）
 ├─► registry   唯一扫描插件蓝图与 manifest 的模块（蓝图域唯一入口；
 │              蓝图根：`plugins/` → 裸 ID，`shell/units/` → `shell.` 前缀，KM4）
 ├─► resolver   纯函数：依赖图进，拓扑序出（零 I/O、零状态，表驱动可测）
 └─► ledger     唯一读写 state.json 的模块（状态域唯一入口）
```

* 禁止绕过 ledger 直写账本，禁止绕过 registry 直读蓝图；
* `resolver` 不 import 任何内核兄弟模块，只做纯计算；
* deploy.atomic、Vault、事件通知、插件生命周期钩子（`post_install` / `post_remove`，
  执行插件目录内 `hooks/<名字>` 脚本，注入 `PYTHONDONTWRITEBYTECODE=1`）只允许 transaction 触碰；
* doctor 三态对账（`audit_plugins`：`Synced` / `Drifted` / `Ghost`）是只读能力，
  同样收敛在 transaction（受管文件与哈希知识只此一家），内核保持四模块不变。

---

## 3. 正交模型与状态机 (Orthogonal State Machine)

插件与预设各管各的，两轴严格垂直正交：
* **开关状态（横轴，存在性）**：用不用该软件？（`enabled` ↔ `disabled`）
* **外观形态（纵轴，呈现参数）**：软件长什么样？（`preset` / `parts`）

```
                [ Disabled ] (停用态：实机无文件，自定义配置存 Vault)
                     │
           on / enable       off / disable
         (预检清单与安装)   (归档抹净还原白纸)
                     ▼
                [ Enabled ]  (启用态：实机存在配置，服务活跃)
                     │
                     └── 内部形态切换：preset / parts（不改变 Enabled 状态）
```

### 迁移事务规则
1. **启用动作 (`on` / `enable`)**：
   - 依赖解析器遍历依赖链：若下游依赖未启用，一同列入启用预检清单；
   - 检查外部包：若缺少 pacman/AUR 包，调用 `nyxuri.pkg` 提示安装；
   - 从 `vault/<plugin>/` 捞回自定义文件与最新蓝图合并（捞回即消费：归档移入实机后
     Vault 清空，用户已删除的自定义不会被下次启用复活）；
   - 原子置换进 `~/.config/<target>` 并完成模板渲染；
   - 状态经 ledger 落账 `state.json`，随后发出一次 `plugin-changed` 事件（见 §6，尽力而为，无订阅者即 no-op）；
2. **停用动作 (`off` / `disable`)**：
   - 反向依赖检查：若有其他已启用插件依赖它且未带 `--cascade`，强行阻断并报警；
   - 将 `~/.config/<target>` 中的 `__custom__` 与 `preserve` 文件原子移入 `vault/<plugin>/`；
   - 彻底删除受管文件，空目录删除，实机恢复纯白；非受管的外来文件不吞——
     幸存并在报告中列明（doctor 记 `Ghost`），绝不背地里吃掉用户文件；
   - 状态经 ledger 落账 `state.json`；
   - 真诚报告交底：明确告知配置已归档，二进制包保留在系统（不背着用户 sudo 卸包）；
   - 发出同一 `plugin-changed` 事件，Shell 据此摘除挂件。

### 账本记录形状（KM0 冻结）

`state.json` 中每条插件记录只含五个字段。KM2 的事务与 doctor 对账全部建立在其上，实现不得私加：

| 字段 | 类型 | 含义 |
|---|---|---|
| `state` | `enabled` / `disabled` | 开关轴唯一状态 |
| `preset` | `string` | 形态轴当前选择（预设或零件） |
| `files` | `map<相对路径, sha256>` | 受管文件哈希快照，`Drifted` 判定依据 |
| `vault` | `路径?` | 停用时自定义文件的 Vault 归档位置，`disabled` 时必填 |
| `updated` | `ISO 时间戳` | 最近一次事务落账时间 |

插件记录统一挂在 `state.json` 顶层的 `plugins` 键下，以插件 ID 为键（R0-1 前的老账本
键名为 `plugins`，首次读取时一次性迁移改写）；`updated` 为带时区的
ISO 8601 时间戳。插件记录的读写只经 `nyxuri.ledger`，任何内核模块不得绕过。

`files` 快照口径（KM2 落地，KM3 扩展，#139 收敛）：只记**引擎铺设的模板产物**——
`__custom__` 与 manifest `preserve` 文件属用户心血，不入快照、不参与 `Drifted` 判定；
`preserve_values` 目标文件计入；symlink 记 `link:<目标>`；`post_install` 钩子在快照**之前**
运行，钩子落进插件自身生活区的产物自动入快照、`off` 走正常抹白（钩子落生活区外的产物由
`post_remove` 自清，见 [manifest-schema](manifest-schema.md) 钩子契约）。

**carry 不变式（#139）**：部署时按基线判定搬入的用户文件（改动文件与自放文件）**永不入账**
——若入账，下次部署会把它当作"引擎铺设过且未被动过"的文件用新模板覆盖，账本自吞用户数据。
推论：所有权只经 `on`（收编）增长，`update` 永不把新路径登记为受管。`update`/install 在
部署 + 钩子重放之后经 `resnapshot_plugins` 重登记受启用插件（搬入文件剔除），使账本始终
等于"引擎上次铺设的内容"；`on` 的快照同样剔除搬入文件。doctor 对账按账本条目逐文件
比对（缺文件、内容漂移各自成立），搬入的用户文件不构成 Drifted 噪音。
领地按账本划：基线里有、用户没动过、这次 payload 不再含的路径（钩子产物）随 swap
退场、由钩子重放重铺、resnapshot 重新入账——KM3「产物受管、off 抹白」在 carry 下
依然成立，且不进搬运报告。`__pycache__`/`*.pyc` 两侧 walk 剪除，永不搬入或报告。

停用时无受管快照（`files` 空：从未经事务开关，或停用后再现内容）的插件按**蓝图具名**
撤回——引擎 payload 文件回收，其余内容原地幸存并报 `foreign-left`（#139：v3 时代
未登记的实机目录不得被 `off` 整域吞掉）；单文件插件（`target=`）无 Vault 进出，
其唯一实机文件若不在受管快照内同样幸存并上报。

**merge 插件（KM3.5，共享生活区）**：manifest 声明 `merge = true` + `~/` 前缀
或 `xdg:<KIND>/…` 的 `target`（如壁纸落 `xdg:PICTURES/Wallpapers`，解析为
XDG 图片目录下的 `Wallpapers`，与 Noctalia、壁纸选择器、doctor 同源）
即声明「生活区是共享空间」——
`on` 走 no-clobber 增量合流（已存在的文件永不覆盖、永不删除），快照只记部署实际
落下的文件；`off` 只撤回快照文件，pack、用户自有壁纸等外来内容原地幸存并在报告
列明（`foreign-left`），目录本身只在清空后消失；doctor 对停用 merge 插件的
Ghost 判据 = 蓝图具名文件残留，共享目录因外来内容存在不构成 Ghost。merge 插件
同样无 Vault 进出、不支持 presets/parts。

---

## 4. Manifest Schema v2 极简规范

坚持**约定优于配置（Zero-Config by Default）**：
* 插件名称 = 目录名；
* 部署目标 = `~/.config/<目录名>`（除非显式指定 `target`）；
* 系统包名 = `[<目录名>]`（除非显式指定 `packages`）；
* **无 `manifest.toml` = 100% 采用全默认**（如 `kitty/` 目录不需要任何 TOML 文件）。

### 差异化字段范式（只写例外）

```toml
# 目标路径例外（如单文件目标）
target = "starship.toml"

# 系统包名例外（如带连字符或特殊命名）
packages = ["mission-center"]
packages_aur = ["brave-bin"]
packages_flatpak = ["com.qq.QQ"]

# 依赖的其他 Nyxuri 插件
dependencies = []

# 跨部署保留文件与可执行脚本权限
preserve = ["monitor.kdl"]
chmod = ["scripts/*.sh"]

# 预设与重载命令
[presets]
default = "default"
reload = ["niri", "msg", "action", "reload-config"]

# 通用零件插槽
[parts.effects]
target = "effects_normal.kdl"
source_dir = "effects"
default = "default"

# 特权声明（涉及 /etc 修改）
[privilege]
requires_root = false
system_paths = []
```

### 声明边界

manifest 只声明上述字段，不追求覆盖一切。插件的外部副作用走**插件本地钩子**：
`post_install` / `post_remove` 指向 `plugins/<plugin>/hooks/<名字>` 可执行脚本，
由 transaction 执行（KM3 契约，`<module>:<function>` 旧形态已随 `nyxuri/modules/`
退役；详见 [manifest-schema](manifest-schema.md) 钩子契约）。systemd 服务启停等
跨系统声明字段仍暂不进 manifest：属插件内部行为，出现真实需求再议（登记于
[delayed-decisions](delayed-decisions.md)）。完整字段参考（含 `label` / `category` / `detect` / `optional` / `preserve_values` 等展示与包元数据字段）见 [manifest-schema](manifest-schema.md)。

---

## 5. 四大核心命令

命令行只保留 4 个通用动词（`list`、`on`、`off`、`doctor`），`on` / `off` 另有语义等价长动词（`enable` / `disable`）。不设更短的缩写别名——动词已经够短，别名只是要供养的表面：

```bash
# 1. 查看全景清单或单个详情
nyxuri list [plugin]

# 2. 开启插件（支持指定预设）
nyxuri on <plugin> [--preset <p>]     # 等价: enable

# 3. 关闭插件（默认拒绝级联，显式 --cascade 才级联关闭下游依赖）
nyxuri off <plugin> [--cascade]       # 等价: disable

# 4. 对账检查（实机文件 vs 账本三态审计）
nyxuri doctor [plugin]
```

单源阶段**不设独立 `refresh` 动词**：账本即真相，无缓存可刷。

---

## 6. Shell 内部插件化与协同契约 (Shell Pluginization & Coordination)

> **层次边界（KM4 已兑现）**：内核只关心本节三件事——同一账本、单一事件通道、
> 点分 ID。插槽分类学与微内核宿主实现细节已迁归 [Shell 契约](../shell/AGENTS.md)。
>
> **设计初衷**：当前 Shell 超过 50% 组件为借用的临时过渡品，未来将由作者大幅重构与推倒重写。微内核 + 几何插槽保证了借用组件与外壳的**绝对绝缘**——拔除、重写或替换任意组件，微内核与其他模块零改动。

Nyxuri Shell 绝非特权单体，其内部亦彻底插件化（宿主侧契约见 Shell AGENTS）。
内核只冻结以下三条：

1. **同一账本**：Shell 设置面板拨动开关仅派发 `nyxuri on/off shell.<domain>` 调用
   内核事务；Shell 永远只是 `state.json` 在屏幕上的**只读投影**，不持有私有开关
   状态（Shell 私有开关字段已随 KM4 处决，见 §7）。
2. **单一事件通道**：事务落账后只发一次 `plugin-changed` 事件。这是抽象端口，不是
   内核命令——当前唯一投递实现是 `quickshell ipc unit reload`，由外层注入
   （`nyxuri/desktop/bridge.py`，CLI 入口 `bridge.wire()` 统一接线），内核不
   import、不 subprocess quickshell；无订阅者时为 no-op（测试与无 Shell 环境
   零负担）。
3. **点分 ID 约定**：Shell 域插件以 `shell.<domain>` 命名（如 `nyxuri off
   shell.dock`），统一挂入 `state.json` 与 4 大动词管辖。内核只认点分 ID 本身，
   不特判任何前缀。

**内核侧承载（KM4 落地，KM4.5 正名）**：Shell 插件物理住在 `shell/units/<domain>/`
（文件树表达架构；KM4.5 后 `modules/` 已整体正名并入——manifest 与代码同目录，
目录即插件，registry 仍只读 `iterdir` 的目录名，插件内文件布局对内核不可见），
registry 以**命名空间根**解析——`plugins/` 产裸 ID，`shell/units/` 产 `shell.` 前缀 ID，
前缀属于根不属于逐 ID 特判；manifest `name` 一律补齐为全点分 ID（账本键、Vault 路径、
报告所见即 registry ID）。Shell 插件以 `runtime = true` 声明**运行态插件**：无载荷、
无生活区、无 Vault 进出，`on`/`off` = 账本落记 + 一次事件，运行中的 Shell 据事件
装载/卸载该域；`off` 永不触碰实机同名目录（无目标即无抹白），doctor 恒 `Synced`。
deploy/deps 的包世界（`discover_manifest_apps`）只扫 `plugins/`，Shell 插件对包体系不可见。

---

## 7. 深层防御与代码级死刑清单

1. **包管理非对称**：`disable` 只撤回配置与桌面集成，绝不私自调用 sudo 卸载系统包，以避免打断和破坏系统依赖；结果在执行报告中如实写明。
2. **单文件特例一律铲除**：全库 100% 目录平铺化。`configs/starship.toml` 升格为 `configs/starship/`（现 `units/starship/`），消灭 sidecar 机制。
3. **Vault 纯文件平铺**：`~/.local/state/nyxuri/vault/<plugin>/` 保持目录镜像平铺，不建数据库，不打包压缩，用户肉眼直观可见。
4. **死刑清单与两步执法**：所有过渡物登记在下方清单（名字 + 死刑阶段），契约测试分两步执法：
   - **登记步（KM0 已生效）**：`tests/test_ai_specs.py` 断言清单条目齐全；
   - **执法步**：对应阶段收口时，断言升级为物理删除。升级动作写进该阶段验收步骤（见 ROADMAP），届时登记步对该条目退役。

| 死刑对象 | 死刑阶段 |
|---|---|
| `.optional-apps.toml`（axis-B sidecar） | KM1（已执法） |
| `configs/starship.toml` + `starship.toml.module.toml`（单文件特例） | KM1（已执法，升格为 `units/starship/` + `target`） |
| `*.module.toml` sidecar 机制（已统一收敛为目录内 `manifest.toml`） | KM1（已执法） |
| `nyxuri/modules/` 专用业务模块（能力并入 `units/` 单元 + 钩子脚本） | KM3（已执法） |
| 旧 CLI 命令兼容别名 ×12 与 `RETIREMENTS` 倒计时表（`deploy/backup/restore/remove/purge/recommended/wp/report` + 幽灵指针 `greeter/fcitx/gtk/fisher`） | KM3.5（已执法，旧名 = 普通 unknown command） |
| `nyxuri/template_registry.py`（生产零引用）及其测试 | KM3.5（已执法） |
| 17 个零文件假单元（`configs/` 下仅 manifest 的包目录）→ 根 `catalog.toml` | KM3.5（已执法，包目录清单不是单元） |
| `assets/` + `nyxuri/deploy/assets.py`（壁纸旁路）→ `units/wallpapers/` 单元 + `hooks/install-pack` | KM3.5（已执法，`wallpapers` 动词处决 → `on wallpapers`） |
| 蓝图正名 `configs/` → `units/`、引擎物理分层（`kernel/` `desktop/` `installer/` `pkg/` 收编、`sysdoctor` 正名、`packaging/` 迁仓库根、测试镜像树） | KM3.5（已执法，文件树即架构） |
| Shell 私有开关状态（settings.json `bar.enabled`/`keystone.enabled`、dock.json `enabled`）→ 账本投影（`StateProjection`）+ `UnitControl` 派发内核动词 | KM4（已执法，单一开关真相） |
| AppShell 硬编码单元组件 ×9 与宿主代管的单元 IPC（power-menu/lock/spotlight/control-center/settings）→ `SlotHost` 槽驱动 + 单元自有 IPC | KM4（已执法，微内核插槽架构） |
| `~/.config/noctalia/templates/` 共享池（寄宿 noctalia 命名空间）→ `units/theme/` 单元 + `~/.config/nyxuri/templates/` | KM4（已执法，池位置中立化，merge 共享生活区） |
| `install.sh` 安装器职责（退役为一次性引导）→ `nyxuri/launcher.sh` 常驻启动器 + 无透传引导；同批清算：`nyxuri/migrations/` 整模块、nyxniri 别名与 `NYXNIRI_*` 兼容层 | KM5（已执法；`nyxuri/cli.py` 交互菜单经作者裁决保留为常驻产品面，登记撤销） |
| 蓝图正名 `units/` → `plugins/`（账本键 `units` → `plugins` 一次性迁移 + 引擎标识符与文案 unit → plugin） | R0-1（已执法） |
| 根 `catalog.toml`（包目录清单）+ `pkg/catalog.py` → 18 个 manifest-only 插件目录（`plugins/<name>/manifest.toml` 仅包声明，deps 菜单聚合 manifest） | R0-2（已执法） |
| 预设/零件概念 → 插件形态字段（manifest `[presets]`/`[parts]` 并轨 `[forms]`、账本 `preset` 字段改名 `form` + 顶层 `forms` 槽位字典、`deploy/preset.py` → `forms.py`、`presets/<app>.active` 双写退役） | R0-2（已执法） |
---

## 8. 路径与环境术语表（原 concept-glossary，KM3.5 并入）

路径在 `nyxuri/core.py` 的 `Environment` 定义（`configs_src` → `units_src` → `plugins_src`，两级正名）：

| 术语 | 定义 | 实际路径 |
|---|---|---|
| `repo_dir` | 源码所在地（cache / clone / system 三选一，谁被跑谁赢） | `~/.cache/nyxuri` / clone 路径 / `/usr/share/nyxuri` |
| `config_dir` | 部署目标，恒定 | `~/.config` |
| `nyx_dir` | Nyxuri 自己的家：backups / presets / active / hooks | `~/.config/nyxuri` |
| `state_dir` | 运行时状态账本（`state.json`）与瞬态（lock + log） | `~/.local/state/nyxuri`（XDG_STATE_HOME） |
| `plugins_src` | 仓库插件蓝图源（原 `configs_src`） | `repo_dir/plugins` |
| `presets_dir` | 用户预设 + active 状态 | `nyx_dir/presets` |
| `hooks_dir` | 用户自定义部署后置钩子脚本 | `nyx_dir/hooks` |

边界规则：Nyxuri 元数据**只许在 `~/.config/nyxuri/`**，不许往 `~/.config/<plugin>/`
里塞 Nyxuri 自己的东西（`__custom__` 是约定保留名，属插件配置的一部分；`manifest.toml`
是仓库元数据，部署时被跳过）。`~/.config/nyxuri/` 放用户数据（backups、presets）；
`~/.local/state/nyxuri/` 放运行时账本与瞬态（lock、log）。不混用。

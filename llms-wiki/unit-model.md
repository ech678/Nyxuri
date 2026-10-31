# Unit Model — 单元模型、内核架构与极简契约

> 本页是 Nyxuri 单元模型、内核架构、状态机与 Manifest Schema v2 的唯一权威契约；
> 运行时行为与单测以 `tests/test_unit_model.py` 为准。

---

## 1. 物理空间三对偶与不变量

系统由三个物理隔离的空间与一条单向中轴连接，互不侵犯：

```
┌────────────────────────────────┐
│   空间 A：源码蓝图 (Blueprint)  │  只读，版本受控，平铺所有单元目录
│   路径：units/<unit>/           │  （永不向此处写入运行时状态）
└───────────────┬────────────────┘
                │
                │  中轴：nyxuri.deploy.atomic
                │  （哈希比对、原子替换、模板渲染、Dunder/Preserve 继承）
                ▼
┌────────────────────────────────┐       停用归档 (Vault In)       ┌─────────────────────────────────┐
│   空间 B：实机生活区 (Living)   │ ──────────────────────────────► │   空间 C：状态与保险域 (State)   │
│   路径：~/.config/<target>/    │ ◄────────────────────────────── │   路径：~/.local/state/nyxuri/  │
│   （用户的日常桌面生活环境）    │       启用恢复 (Vault Out)      │   - state.json (单一真相账本)    │
└────────────────────────────────┘                                 │   - vault/<unit>/ (自定义备份)  │
                                                                   │   - backups/ (30 个滚动快照)    │
                                                                   └─────────────────────────────────┘
```

### 空间不变量
1. **源码绝对只读**：`units/` 永远是只读蓝图。严禁在源码树建软链接，严禁向源码树写状态（单元钩子注入 `PYTHONDONTWRITEBYTECODE=1`，钩子引引擎代码也不得落 `__pycache__`）。
2. **撤回边界**：停用单元只撤回账本确认归属的文件；外来或来源不明的文件原地保留并报告，不能为了清空目录而删除。
3. **心血零丢失**：停用前将有创建来源记录的 `__custom__`、`preserve` 和相对上次部署基线已修改的受管文件归档到 `vault/<unit>/`；全部复制成功后才撤回原件。保留名本身不构成归属证据，未知内容原地保留。目录、单文件和 merge 单元遵循同一规则。

---

## 2. 四大法定术语 (The 4 Canonical Primitives)

全库统一且仅承认以下四个词：

| 术语 | 英文 | 本质定义 | 物理承载 | 行为边界 |
|---|---|---|---|---|
| **单元** | `Unit` | 桌面上**一切可独立开关**的原子能力实体。 | `units/<unit>/` 目录 | 拥有独立的生命周期与状态，可声明依赖、文件与预设。 |
| **内核** | `Kernel` | Nyxuri 常驻骨架，负责编排与记账（纯 Python 标库）。 | `nyxuri/kernel/{registry, resolver, transaction, ledger}` | **内核不是单元**，不可插件化、不可开关，是承载一切的物理底座。 |
| **源** | `Source` | 单元的供给方与索引来源。 | 本地抽象 `local:builtin`（对应 `units/`） | 本阶段仅维持单一本地内置源，推迟网络多源。 |
| **manifest** | `Manifest` | 单元的自描述规格书。全库统称 `manifest.toml`。 | `units/<unit>/manifest.toml` | 纯声明式静态元数据，**全字段可选，无文件 = 全默认**。 |

### 严正排除项
* **系统软件包（Arch/AUR、Ubuntu APT、Flatpak 包）**：不是单元！它们由单元声明书的包字段声明，`dependencies` 只引用其他 Nyxuri 单元。
* **预设与零件（Preset / Parts）**：不是单元！它们是单元内部的配置变体（Variants）。
* **包目录清单（根 `catalog.toml`）**：不是单元！「装但不部署」的软件（brave-origin、
  missioncenter 这类无配置可 ship 的声明）住根 `catalog.toml`，供 `deps apps` 菜单与
  gen-deps optdepends 同源消费；目录条目没有账本生命周期，永不进 `units/`（KM3.5 正名）。

### 内核分层契约（依赖方向冻结）

四个内核模块呈星形单向分层，物理承载 `nyxuri/kernel/`（KM3.5 正名）：**transaction 是唯一允许多依赖的编排层，其余三件互不认识**。

```
transaction（编排：唯一可触碰副作用的模块）
 ├─► registry   唯一扫描单元蓝图与 manifest 的模块（蓝图域唯一入口；
 │              蓝图根：`units/` → 裸 ID，`shell/units/` → `shell.` 前缀，KM4）
 ├─► resolver   纯函数：依赖图进，拓扑序出（零 I/O、零状态，表驱动可测）
 └─► ledger     唯一读写 state.json 的模块（状态域唯一入口）
```

* 禁止绕过 ledger 直写账本，禁止绕过 registry 直读蓝图；
* `resolver` 不 import 任何内核兄弟模块，只做纯计算；
* deploy.atomic、Vault、事件通知、单元生命周期钩子（`post_install` / `post_remove`，
  执行单元目录内 `hooks/<名字>` 脚本，注入 `PYTHONDONTWRITEBYTECODE=1`）只允许 transaction 触碰；
* doctor 对账（`audit_units`：`Synced` / `Drifted` / `Ghost` / `Pending` / `Orphan`）是只读能力，
  同样收敛在 transaction（受管文件与哈希知识只此一家），内核保持四模块不变。

---

## 3. 正交模型与状态机 (Orthogonal State Machine)

单元与预设各管各的，两轴严格垂直正交：
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
   - 按 [平台依赖覆盖](manifest-schema.md#平台依赖覆盖) 检查外部包与手动资源：不支持的平台先阻断，可安装的缺失包由 `nyxuri.pkg` 供给，安装后再次检查；
   - 显式预设、依赖平台与历史目标在任何文件部署之前校验；无效预设不写 active、Vault 或依赖配置；
   - 从 `vault/<unit>/` 逐文件恢复归档，不替换父目录；成功恢复的叶节点才从 Vault 移除。
     同名内容冲突先创建可恢复快照，保留生效区版本及尚未恢复的归档，并披露冲突；
   - 原子置换进 `~/.config/<target>` 后，复用整装流程的单元级路径渲染，将
     `/home/user` 等占位符替换为本次 HOME；carry 保留的个人文件跳过渲染。随后执行 `post_install`，
     最终基线只记录实际写入的内容；外部产物由其独立归属清单管理，不重复认领；
   - 状态经 ledger 落账 `state.json`，随后发出一次 `unit-changed` 事件（见 §6，尽力而为，无订阅者即 no-op）；
2. **停用动作 (`off` / `disable`)**：
   - 反向依赖检查：若有其他已启用单元依赖它且未带 `--cascade`，强行阻断并报警；
   - 先停止消费者模板输出并撤回受管外部产物，再将有归属证据的 Custom、preserve 和普通修改逐文件归档；
     文件与上次部署哈希不同即视为修改，不能用仓库当前模板代替历史基线；
   - 彻底删除受管文件，空目录删除，实机恢复纯白；非受管的外来文件不吞——
     幸存并在报告中列明（doctor 记 `Ghost`），绝不背地里吃掉用户文件；
   - 状态经 ledger 落账 `state.json`；
   - 真诚报告交底：明确告知配置已归档，二进制包保留在系统（不背着用户 sudo 卸包）；
   - 发出同一 `unit-changed` 事件，Shell 据此摘除挂件。

### 账本记录与部署元数据版本

`state.json.units` 保持原五字段形状，供已有读取端继续消费。历史目标、迁移和未完成阶段由
独立的版本化 `deployments` 顶层映射承载，不向单元记录添加隐式字段：

| 字段 | 类型 | 含义 |
|---|---|---|
| `state` | `enabled` / `disabled` | 开关轴唯一状态 |
| `preset` | `string` | 形态轴当前选择（预设或零件） |
| `files` | `map<相对路径, sha256>` | 受管文件哈希快照，`Drifted` 判定依据 |
| `vault` | `路径?` | 停用时自定义文件的 Vault 归档位置，`disabled` 时必填 |
| `updated` | `ISO 时间戳` | 最近一次事务落账时间 |

单元记录统一挂在 `state.json` 顶层的 `units` 键下，以单元 ID 为键；`updated` 为带时区的
ISO 8601 时间戳。单元记录的读写只经 `nyxuri.kernel.ledger`，任何内核模块不得绕过。

`deployment_version = 1` 对应 `deployments[unit]` 的以下字段：

| 字段 | 含义 |
| --- | --- |
| `version` | 单元部署元数据版本，当前为 `1` |
| `target` / `shape` | 实际绝对落地点与 `directory` / `file` / `merge` / `runtime` 形状 |
| `preserve` | 当时的按名保留规则，源码改变后停用仍按历史规则归档 |
| `protected_paths` | 部署或钩子实际新建的保留叶节点来源集合；不含内容哈希，旧记录默认为空 |
| `pending` | `null` 表示完成；部署、钩子、零件和重载失败保留具体阶段供重试 |
| `archived_baselines` | 停用前的部署哈希，恢复普通修改时继续使用旧基线 |
| `pending_part` | 零件切换中断时保存 `slot` / `variant`，完成后清空 |
| `migration` | 布局迁移中保存新区 `target` / `shape`、候选文件身份 `files` 与 `backup`；完成后清空 |

旧五字段记录不会在读取时重新计算哈希或自动认领当前文件；首次成功修改时补充部署元数据。
旧记录对应的源码已经消失且没有历史目标时，doctor 报 `Orphan`，停用拒绝猜测路径。
已有历史目标的 orphan 可安全撤回。`legacy_targets` 明确授权的旧目录到 merge 布局、以及
动态 Pictures 目标变化，可先快照再逐文件迁移；其他目标变化先拒绝刷新，显式停用旧目标后
同形状重新启用会先备份。未声明的形状变化拒绝执行，不把新目标当作旧目标删除位置。
旧五字段记录的已声明迁移使用唯一旧默认目标，off 在首次迁移前也从该旧目标撤回。
`pending=migration` 保留旧目标，普通 off 拒绝，用户可重试 on 或通过快照 rollback。

`files` 记录上一次实际铺设的内容：普通文件使用 SHA-256，软链使用 `link:<目标>`。
Custom 与普通 preserve 文件不入基线，只把实际新建路径登记到 `protected_paths`；
已有个人文件不能因名称符合规则而被接管。零件目标虽由 preserve 保护，实际零件部署仍记录
其写入哈希。零件选择 `parts` 与这次写入的文件基线在同一次账本提交中更新。

**carry 不变式**：个人修改不能变成新的部署基线。已登记文件发生修改时，继续保留旧哈希，
doctor 报 `Drifted`，后续停用仍能归档；从未登记的外来文件继续不入账。成功刷新实际铺设的新
模板文件可新增归属。运行时生产者的独立外部产物按原值与最后写入身份撤回，不再重复加入普通文件基线。
主配置的受管运行时变换（例如 Starship palette 段）仍保留普通归属：只有当前哈希精确匹配
部署基线才允许变换，并同步该单一文件基线；源码刷新后重建可逆原值，撤回变换时同步恢复
原基线。个人漂移不重基、不覆盖。初始运行时插槽只可凭本轮确实新铺设的证据登记，
Vault 恢复与部署前已有内容不构成新建证明；相关规则见 [状态操作](state-ops.md)。

**统一刷新**：`unit_refresh()` 只处理已启用单元，沿用 `unit_on(..., refresh=True)` 的预检、
备份、文件提交、账本提交和运行时动作。未启用依赖会阻断并披露，不能因 update 自动启用。
普通 `on` 会补齐明确依赖。`install config` 可跳包探测和单元钩子，但留下 `config-only`
未完成阶段；后续普通 `on` 必须补包预检和钩子，不能误报已完整启用。

**主题消费者刷新**：单元开关均更新模板输出门控；只有主题生产者及其消费者变更才重建
Noctalia 模板表。Greeter 等无关单元不得触发应用主题迁移。注册暂存模板前检查输入可读，
缺失时保留原配置并报告 `consumer-sync` 待重试，先刷新模板所属单元再重试。
已有 Noctalia `builtin_ids` 在更新时保留；仍启用的 Kitty/Qt 原生模板不重复注册同目标的
Nyxuri 暂存模板。只有明确停用对应消费者或 theme 才撤回这两个原生模板，其他内置选择不改。
原生模板仍由 Noctalia 自身写入与撤回，不追认成 Nyxuri 已登记的外部产物；新部署继续使用
带归属核对的暂存提交。不能靠清空内置列表进行迁移，其撤回钩子会删除主题文件及应用引用。

**失败与重试**：持锁验证账本后才允许文件动作；损坏、不可读或加锁失败均停止，只有不存在
的账本才表示首次使用。文件部署、安装/卸载钩子、零件或重载失败返回 `ok=False`；已经落地的
部分保留 `pending`，doctor 报 `Pending`，再次执行对应动作或 `on` 可重试。成功才发事件。
强制采用模板先生成可通过 rollback 恢复的完整快照，失败不覆盖；强制只覆盖模板具名冲突，
其他外来文件仍保留。相关归档及恢复规则见 [文件保留](file-preservation.md)。

**merge 单元**：共享目录逐文件部署，更新未修改受管文件、补入新模板，移除源码已删除且仍
匹配旧基线的文件。修改过的受管文件保留旧基线；普通外来内容不覆盖、不删除。停用前同样
归档修改，只撤回登记路径；目录仅在清空后删除。merge 不支持 presets/parts。
`when_units` 只筛选具名载荷，不构成启用依赖；相关单元开关刷新已启用的条件单元，
不自动启用它，也不隐式重启运行时进程。条件失效时修改文件入 Vault，旧哈希进入
`archived_baselines`，条件恢复后继续使用。`retired_files` 则仅删除身份精确匹配的旧产物，
修改与未知版本原地保留并退出普通归属。

---

## 4. Manifest Schema v2 极简规范

坚持**约定优于配置（Zero-Config by Default）**：
* 单元名称 = 目录名；
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

# 依赖的其他 Nyxuri 单元
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

manifest 只声明上述字段，不追求覆盖一切。单元的外部副作用走**单元本地钩子**：
`post_install` / `post_remove` 指向 `units/<unit>/hooks/<名字>` 可执行脚本，
由 transaction 执行（KM3 契约，`<module>:<function>` 旧形态已随 `nyxuri/modules/`
退役；详见 [manifest-schema](manifest-schema.md) 钩子契约）。systemd 服务启停等
跨系统声明字段仍暂不进 manifest：属单元内部行为，出现真实需求再议（登记于
[delayed-decisions](delayed-decisions.md)）。完整字段参考（含 `label` / `category` / `detect` / `optional` / `preserve_values` 等展示与包元数据字段）见 [manifest-schema](manifest-schema.md)。

---

## 5. 四大核心命令

命令行只保留 4 个通用动词（`list`、`on`、`off`、`doctor`），`on` / `off` 另有语义等价长动词（`enable` / `disable`）。不设更短的缩写别名——动词已经够短，别名只是要供养的表面：

```bash
# 1. 查看全景清单或单个详情
nyxuri list [unit]

# 2. 开启单元（支持指定预设）
nyxuri on <unit> [--preset <p>]     # 等价: enable

# 3. 关闭单元（默认拒绝级联，显式 --cascade 才级联关闭下游依赖）
nyxuri off <unit> [--cascade]       # 等价: disable

# 4. 对账检查（实机文件、待重试阶段与源单元缺失）
nyxuri doctor [unit]
```

单源阶段**不设独立 `refresh` 动词**：账本即真相，无缓存可刷。

---

## 6. Shell 内部单元化与协同契约 (Shell Unitization & Coordination)

> **层次边界（KM4 已兑现）**：内核只关心本节三件事——同一账本、单一事件通道、
> 点分 ID。插槽分类学与微内核宿主实现细节已迁归 [Shell 契约](../shell/AGENTS.md)。
>
> **设计初衷**：当前 Shell 超过 50% 组件为借用的临时过渡品，未来将由作者大幅重构与推倒重写。微内核 + 几何插槽保证了借用组件与外壳的**绝对绝缘**——拔除、重写或替换任意组件，微内核与其他模块零改动。

Nyxuri Shell 绝非特权单体，其内部亦彻底单元化（宿主侧契约见 Shell AGENTS）。
内核只冻结以下三条：

1. **同一账本**：Shell 设置面板拨动开关仅派发 `nyxuri on/off shell.<domain>` 调用
   内核事务；Shell 永远只是 `state.json` 在屏幕上的**只读投影**，不持有私有开关
   状态（Shell 私有开关字段已随 KM4 处决，见 §7）。
2. **单一事件通道**：事务落账后只发一次 `unit-changed` 事件。这是抽象端口，不是
   内核命令——当前唯一投递实现是 `quickshell ipc unit reload`，由外层注入
   （`nyxuri/desktop/bridge.py`，CLI 入口 `bridge.wire()` 统一接线），内核不
   import、不 subprocess quickshell；无订阅者时为 no-op（测试与无 Shell 环境
   零负担）。
3. **点分 ID 约定**：Shell 域单元以 `shell.<domain>` 命名（如 `nyxuri off
   shell.dock`），统一挂入 `state.json` 与 4 大动词管辖。内核只认点分 ID 本身，
   不特判任何前缀。

**内核侧承载（KM4 落地，KM4.5 正名）**：Shell 单元物理住在 `shell/units/<domain>/`
（文件树表达架构；KM4.5 后 `modules/` 已整体正名并入——manifest 与代码同目录，
目录即单元，registry 仍只读 `iterdir` 的目录名，单元内文件布局对内核不可见），
registry 以**命名空间根**解析——`units/` 产裸 ID，`shell/units/` 产 `shell.` 前缀 ID，
前缀属于根不属于逐 ID 特判；manifest `name` 一律补齐为全点分 ID（账本键、Vault 路径、
报告所见即 registry ID）。Shell 单元以 `runtime = true` 声明**运行态单元**：无载荷、
无生活区、无 Vault 进出，`on`/`off` = 账本落记 + 一次事件，运行中的 Shell 据事件
装载/卸载该域；`off` 永不触碰实机同名目录（无目标即无抹白），完成时 doctor 为 `Synced`，
未完成阶段为 `Pending`；显式预设参数被拒绝且不写状态。
deploy/deps 的包世界（`discover_manifest_apps`）只扫 `units/`，Shell 单元对包体系不可见。

---

## 7. 深层防御与代码级死刑清单

1. **包管理非对称**：`disable` 只撤回配置与桌面集成，绝不私自调用 sudo 卸载系统包，以避免打断和破坏系统依赖；结果在执行报告中如实写明。
2. **单文件特例一律铲除**：全库 100% 目录平铺化。`configs/starship.toml` 升格为 `configs/starship/`（现 `units/starship/`），消灭 sidecar 机制。
3. **Vault 纯文件平铺**：`~/.local/state/nyxuri/vault/<unit>/` 保持目录镜像平铺，不建数据库，不打包压缩，用户肉眼直观可见。
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
---

## 8. 路径与环境术语表（原 concept-glossary，KM3.5 并入）

路径在 `nyxuri/core.py` 的 `Environment` 定义（`configs_src` 已随蓝图正名改为 `units_src`）：

| 术语 | 定义 | 实际路径 |
|---|---|---|
| `repo_dir` | 源码所在地（cache / clone / system 三选一，谁被跑谁赢） | `~/.cache/nyxuri` / clone 路径 / `/usr/share/nyxuri` |
| `config_dir` | 部署目标，恒定 | `~/.config` |
| `nyx_dir` | Nyxuri 自己的家：backups / presets / active / hooks | `~/.config/nyxuri` |
| `state_dir` | 运行时状态账本（`state.json`）与瞬态（lock + log） | `~/.local/state/nyxuri`（XDG_STATE_HOME） |
| `units_src` | 仓库单元蓝图源（原 `configs_src`） | `repo_dir/units` |
| `presets_dir` | 用户预设 + active 状态 | `nyx_dir/presets` |
| `hooks_dir` | 用户自定义部署后置钩子脚本 | `nyx_dir/hooks` |

边界规则：Nyxuri 元数据**只许在 `~/.config/nyxuri/`**，不许往 `~/.config/<unit>/`
里塞 Nyxuri 自己的东西（`__custom__` 是约定保留名，属单元配置的一部分；`manifest.toml`
是仓库元数据，部署时被跳过）。`~/.config/nyxuri/` 放用户数据（backups、presets）；
`~/.local/state/nyxuri/` 放运行时账本与瞬态（lock、log）。不混用。

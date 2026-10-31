# Manifest Schema — `manifest.toml`

> 一个单元一个 manifest，**全字段可选、无文件 = 全默认**。约定自描述：目录名驱动所有默认值。
> 源码：`nyxuri/deploy/manifest.py`（`load_manifest`、`discover_manifest_apps`）。
> KM1 ② 已执法：`.module.toml` sidecar 与 `.optional-apps.toml` 两条旧机制物理删除，
> 一切收敛为目录内单一 `manifest.toml`（契约见 [unit-model](unit-model.md)）。

## 顶层字段（平铺，只写例外）

`units/<unit>/manifest.toml`——只有需要覆盖默认时才写：

| 字段 | 默认 | 作用 |
|---|---|---|
| `packages` | `[<目录名>]` | pacman 包名。**显式 `packages = []` 保持为空**（Flatpak/AUR-only 单元防名字泄进 pacman） |
| `packages_aur` | `[]` | AUR 包名 |
| `packages_flatpak` | `[]` | Flathub app id——走 `flatpak install`，永不进 pacman/AUR/PKGBUILD |
| `target` | `""` | 无 merge 时为单文件例外，落点 `~/.config/<target>`；`merge = true` 时为共享目录（如 Fcitx 的 `fcitx5`）。`~/` 或绝对路径可指定 HOME 内的目标；`@pictures/Wallpapers` 使用 `get_pics_dir()` 解析图片目录。target 单元不支持 presets/parts |
| `merge` | `false` | 共享目录逐文件合流：未变受管文件跟随新模板，修改和外来文件保留；force 先备份再覆盖具名冲突。`off` 归档个人修改后只撤回登记路径，其他内容保留；不支持 presets/parts |
| `legacy_targets` | `{}` | 明确的旧目标到旧形状映射，形如 `{ "fcitx5-rime" = "directory" }`；只为已有账本提供目录到 merge 的保全迁移，未知旧目录不自动认领 |
| `when_units` | `{}` | merge 文件到单元 ID 列表；所有引用单元均已启用且受当前平台支持才部署该文件。开关相关单元只同步已经启用的条件单元 |
| `retired_files` | `[]` | merge 中明确退役的旧文件；只有当前内容匹配历史基线才备份后删除，未知或修改版本原地保留并报告 |
| `runtime` | `false` | 运行态单元声明（KM4，shell 命名空间专用，见 [unit-model](unit-model.md) §6）：无载荷、无生活区、无 Vault 进出、无 presets/parts——`on`/`off` 纯账本落记 + 一次 `unit-changed` 事件，运行中的宿主（Shell）据事件装载/卸载该域。doctor 恒 `Synced`（实机无可对账之物）。物理承载 `shell/units/<domain>/manifest.toml` |
| `preserve` | `[]` | 跨部署保留的路径（按名声明，如 `monitor.kdl`；与 Dunder 不同机制）。条目可以是**目录**：整目录归运行时管理（如 fish 的 `functions/`），部署前整树注入、off 入 Vault、目录下所有文件不入账不参与 Drifted。**禁令：preserve 目录不得混铺模板 payload**——声明即承诺"模板不在此目录铺设任何文件"，混居会把 payload 永久冻结在旧版 |
| `preserve_values` | `{}` | 跨部署保留指定文本配置里的个别键，形如 `{ "noctalia-config.toml" = ["enable_ddcutil"] }`。旧文件里存在的键按原样带入新文件，缺失的键不携带，沿用新模板的值 |
| `chmod` | `[]` | 部署后设 +x 的 glob（相对单元目录，如 `scripts/*.sh`） |
| `label` | `<目录名>` | PKGBUILD optdepends 展示名（菜单显示名走 i18n `app_*` 键） |
| `category` | `""` | 菜单分组键，显示名走 i18n `apps_cat_<key>` |
| `detect` | `<目录名>` | 检测是否安装的命令名（纯名字，无 `binary:` 前缀 DSL） |
| `optional` | `false` | 可选单元：进应用菜单与 PKGBUILD `optdepends`，不占硬依赖 |
| `post_install` | `""` | on 侧生命周期钩子：`units/<unit>/hooks/<名字>` 可执行脚本名（如 `"setup-rime"`），事务在蓝图部署后、账本快照前执行 |
| `post_remove` | `""` | off 侧生命周期钩子：同形态，实机抹白之后执行，负责清理生活区**外**的产物（KM3） |
| `[privilege]` | 无表 | 特权副作用声明：`requires_root = true` + `system_paths = [...]`（如 greeter 的 `/etc/greetd`）。只声明事实供展示与审计，不改变执行方式 |
| `dependencies` | `[]` | 依赖的其他 Nyxuri 单元（内核 resolver 的输入） |

### 平台依赖覆盖

运行时依赖由 `nyxuri/pkg/requirements.py:resolve_requirements` 统一解析。
顶层 `packages` / `packages_aur` / `packages_flatpak` 保持原有 Arch 声明；
`ModuleManifest` 和 `CatalogEntry` 保存原始字段，不随宿主平台改写。
因此 `packaging/gen-deps.py` 在 Ubuntu 上运行仍得到 Arch 的包名。

Ubuntu 单元在同一个 manifest 中声明覆盖，包目录清单使用相同字段：

```toml
# units/noctalia/manifest.toml 的平台覆盖示例
[platforms.ubuntu]
packages = ["noctalia", "python3-gi", "gir1.2-gtklayershell-0.1", "wl-clipboard", "python3-cairo", "python3-gi-cairo"]
reason = "Noctalia requires its configured APT source."

# catalog.toml 中的独立条目示例
[vscode.platforms.ubuntu]
packages = ["code"]
```

| 字段 | 作用 |
| --- | --- |
| `packages` | 当前平台的原生包名；Ubuntu 只送往 APT。需要显式无依赖时写 `[]` |
| `packages_flatpak` | 覆盖 Flatpak app ID；缺省时沿用顶层的跨发行版 ID |
| `manual` | 必须已由用户提供的命令或资源 ID；只探测，不送往 APT，不触发编译 |
| `supported` | `false` 明确不支持该平台，不部署、不调用安装器 |
| `reason` | 来源或不支持原因，供详情与安装失败说明使用 |

Ubuntu 覆盖替换整个原生依赖集合，不与顶层 Arch/AUR 包名合并。缺少覆盖且存在
原生/AUR 依赖时，解析为不支持；只有 Flatpak 或完全无包依赖的单元可以跨平台沿用。
空平台表或只有 `reason` 的表不能表示依赖齐全；必须写明包/资源字段或 `supported=false`。
手动资源缺失时单元启用失败；会话工具链的手动项与配置整装边界见
[Ubuntu 兼容指南](ubuntu-compatibility.md)。

CLI、工坊、单元事务、应用菜单和安装器均使用解析后的集合。`on` 在副作用前检查
平台支持和依赖，安装后重新检查；`off` 报告当前平台保留的软件包。没有 Ubuntu
供应声明不影响单纯取用配置的 `install config`。

### 共享目录与桌面专用规则

Fcitx 的配置目标是 `~/.config/fcitx5`。旧 `~/.config/fcitx5-rime` 的已登记文件、
个人修改、preserve/Custom 与 Vault 按 [文件保留](file-preservation.md) 的迁移流程处理。
新版配置不再单独铺设一个 Fcitx 不读取的目录；共享目录中的其他配置保持原状。

Portal 只提供 `niri-portals.conf` 与 `mango-portals.conf`，依据全部已启用且受支持的
窗口管理器计算，不读取当前 `XDG_CURRENT_DESKTOP` 选择唯一桌面。Ubuntu 不支持的
Mango 不生成规则。Niri/Mango 开关会同步已启用的 Portal 单元，不自动启用 Portal，
也不主动重启用户会话的 Portal 后端。文件更新是否被当前进程重新读取需会话验收。
通用 `portals.conf` 不再作为默认载荷，避免覆盖 GNOME 的缺省路由；未知或修改版本保留。

壁纸目标使用 `@pictures/Wallpapers`，支持 HOME 内本地化图片目录。账本保存实际绝对路径；
图片目录设置变化后先快照再迁移登记文件，其他个人壁纸仍留在原目录。

### 单元生命周期钩子（KM3 契约）

钩子是**单元自己的行为**，不是内核业务代码——落点固定为单元目录内
`units/<unit>/hooks/<名字>`（任意解释器，`#!/usr/bin/env python3` 或 `sh` 均可，
必须带可执行位）。`<module>:<function>` 旧形态随 `nyxuri/modules/` 退役（KM3 死刑）。

- **执行归属**：只有 transaction 执行钩子（内核唯一副作用层），注入
  `NYXURI_UNIT` / `NYXURI_UNIT_SRC` / `NYXURI_UNIT_DEST` 环境变量，不解释钩子内部；
- **快照口径**：`post_install` 在账本快照**之前**运行——钩子落进单元自身生活区的
  文件自动进入 `files` 快照，`off` 走正常抹白（如 fisher 装进 `~/.config/fish` 的
  插件文件无需自记账）；
- **生活区外**（`~/.local/share`、`/etc` 等）的产物 `post_remove` 自清；用户域主题与
  Fcitx 产物经 `desktop.owned_outputs` 登记生产者、消费者、绝对目标、首次原值及
  最后写入身份。元数据保存于状态域 `external-outputs.json`（仅当前用户可读），
  不能用普通 CSS 内容、固定文件名或只列文件名的旧标记认领文件。撤回时只有当前
  内容仍与最后写入一致才恢复原值；后续个人修改留在原地，恢复证据保留。
  首次遇到陌生同名不同内容的目标也默认保留并报告冲突；不能先覆盖再用原值备份
  解释为已获授权。相同字节可以登记，但保留原权限和原值。显式 force 必须先完成
  事务快照；守护进程通过绑定目标当前身份的一次性许可提交，目标变化、停用或
  回滚都会使许可失效。新铺设的蓝图运行时插槽只能凭事务的本次新建路径证明登记。
- **子进程锁边界**：transaction 持有 ledger 锁同步等待生命周期 hook；cleanup hook
  调用 `withdraw_outputs(..., ordinary_only=True)`，只撤回不需要改账本的普通产物，
  不能在子进程重新申请父事务持有的 ledger 锁。主文件可逆变换由父事务预先撤回并
  同步基线；子进程遇到变换立即报告失败，不能漏改基线或等待父锁。
- `hooks/` 是仓库元数据，永不部署进 `~/.config`，也不计入 `is_deployable`；
- 钩子失败降级 WARN，Step detail 标 `hook-failed: <名字>`，不阻断事务。

### 跨单元模板消费者

Noctalia 的共享模板输入由 `dependencies = ["theme"]` 保证供给；Kitty、Niri、Mango、
Fcitx 是可选消费者，不因生产者启用而被自动启用。GTK、Qt 与公共色板归 `theme`。
事务在生命周期钩子之前刷新具名模板表，停用时先落消费者门控并请求 Noctalia 重载，
随后撤回文件；运行时重载失败须报告未完成，不能继续宣称停用成功。
Noctalia 配置表只有当前内容与账本基线一致时才能自动更新；未知或个人改过的
配置保持原字节，外置消费者门控仍先提交，事务报告可重试的 consumer-sync 未完成。
其他单元的开关不能借机重写个人 Noctalia 模板字段。

Noctalia 与 Nyxuri Shell 的内置模板先写状态域暂存文件，最终提交时再次持锁核对
消费者开关与最后写入身份，阻止排队中的旧渲染重新创建停用单元文件。Noctalia 的
默认 Kitty、Qt 模板改为显式的受管模板，其余用户模板保留显式配置的契约。
Nyxuri Shell 的内置 btop、Starship 配置接线也登记原值；Shell 切换只检查 Niri
网关，不直接覆盖脚本，网关升级由 Niri 单元的 refresh 执行。

快照通过同一帮助模块保存外部产物的目标内容、原值与归属；恢复拒绝跨 HOME 目标，
不能只恢复文件却丢弃生产者与最后写入身份。运行时真实渲染和桌面会话仍需分别验收。

Starship 等主配置接线使用独立的可逆变换：只有当前主文件哈希精确匹配该单元
普通 files 基线时才能执行，保存本次源部署原值与变换后的最后身份，并同步该文件
基线为实际受管结果。主文件不会从普通 files 中排除；refresh 正常升级模板后，只在
新文件匹配新基线时重建变换原值。off 撤回未被个人修改的变换后，同步把基线恢复到
源部署原值，再执行归档与撤回，避免把恢复的模板误认作个人修改。

### 固定 Fish 插件与个人插件

Fish 的固定插件集合由单元 hook 中的不可变提交声明供给，在临时 HOME 与
`fisher_path` 内安装，再对实际生成的 functions、completions、conf.d 文件整组预检。
个人 `fish_plugins` 和 universal 变量不作为固定集合的输入；清单由 preserve 保护，
即使强制更新模板也不重置额外个人插件。

固定产物使用同一原值/最后写入身份协议。陌生同名文件或后续个人修改默认保留，
hook 返回未完成；事务显式 force 且已成功创建完整快照后，才覆盖这组具名冲突。
额外个人插件不进入清理集合；固定集合删除的旧产物只按已登记归属退役。
事务在 hook 前后读取 `managed_paths()` 并排除这些路径的普通文件快照，避免把
恢复的个人原值或外部归属产物重新认领成模板基线。旧 `fisher.json` 的文件名清单
不再授权自动覆盖或删除，保留原件供明确迁移。

### 通用零件插槽（`[parts.<slot>]` 表，可选）

支持全系统通用零件化插槽体系，每个 `[parts.<slot>]` 定义一个可单独切换的配置零件（如视觉效果、发光边框）：

| 字段 | 默认 | 作用 |
|---|---|---|
| `target` | （必填） | 目标配置文件相对路径（如 `"effects_normal.kdl"`）。**引擎解析时会自动将其追加到 `preserve` 保护清单中**，无需重复手动声明。 |
| `source_dir` | `<slot>` | 零件源文件目录名（位于 `units/<unit>/__presets__/<source_dir>/`） |
| `default` | `""` | 默认选用的零件名称 |

零件文件存放于 `units/<unit>/__presets__/<source_dir>/` 目录（例如 `effects/default.kdl`）。

### 预设与继承控制（`[presets]` 表，可选）

针对预设较多、希望支持轻量差异化预设（如 Niri `glow` 仅修改 `layout.kdl`）或热重载信号的单元，可通过 `[presets]` 表精确配置：

| 字段 | 默认 | 作用 |
|---|---|---|
| `reload` | `[]` | 预设切换后执行的热重载命令参数列表（如 `["pkill", "-SIGUSR1", "-x", "kitty"]`） |
| `allow` | `[]` | **预设白名单**：仅列出的预设开启底版继承（未列出的保持 100% 独立） |
| `standalone` | `[]` | **预设黑名单**：强制列出的预设独立部署，绝不继承底版 |
| `inherit` | `false` | 全局继承开关（当 `allow` 与 `standalone` 均为空时的兜底策略） |
| `include` | `[]` | **文件白名单**：仅从底版继承匹配这些 glob 的文件/目录（如 `["scripts/**", "*.kdl"]`） |
| `exclude` | `[]` | **文件黑名单**：从底版继承时排除匹配这些 glob 的文件/目录 |

### 实际 ship 的 manifest

```toml
# units/niri/manifest.toml — monitor.kdl 被 include 引用；effects.kdl 为运行时护眼模式符号链接
preserve = ["monitor.kdl", "effects.kdl", "effects_normal.kdl", "glow.kdl", "colors.kdl", "noctalia.kdl", "eyecare_temp"]
chmod = ["scripts/*.sh", "scripts/*.py"]

[parts.effects]
target = "effects_normal.kdl"
source_dir = "effects"
default = "default"

[parts.glow]
target = "glow.kdl"
source_dir = "glow"
default = "default"

# units/kitty/manifest.toml — 切换预设后发送 SIGUSR1 热重载
preserve = ["current-theme.conf", "themes/noctalia.conf"]

[presets]
reload = ["pkill", "-SIGUSR1", "-x", "kitty"]

# units/noctalia/manifest.toml
packages = ["noctalia", "python-gobject", "gtk-layer-shell", "wl-clipboard"]
preserve_values = { "noctalia-config.toml" = ["enable_ddcutil"] }
chmod = ["wallpaper-hook.sh", "mpvpaper-sync.sh", "tools/*.sh", "tools/*.py"]

# units/xdg-desktop-portal/manifest.toml — 按启用桌面提供专用规则
label = "XDG Portals"
merge = true
legacy_targets = { "xdg-desktop-portal" = "directory" }
when_units = { "niri-portals.conf" = ["niri"], "mango-portals.conf" = ["mango"] }
retired_files = ["portals.conf"]

# units/starship/manifest.toml — 单文件单元（target 例外）
target = "starship.toml"
```

fastfetch 的 Arch 包名与二进制名仍由目录名默认推导；其 manifest 只补 Ubuntu 覆盖。

## 可选供给（`optional = true` 与根 `catalog.toml`，两源同汇）

可选不再住 sidecar 登记簿——真单元在自己的 `manifest.toml` 里声明 `optional = true`；
「装但不部署」的软件（无配置可 ship）住**根 `catalog.toml`**（KM3.5 正名：包目录清单
不是单元，17 个零文件假目录已处决）。两源同汇进 `deps apps` 菜单（T1 依赖按需化后
gen-deps `optdepends` 有意与 catalog 脱钩，见 PKGBUILD 头注释）。
**zed / mango / greeter / fcitx5-rime 双轴共存**：既有配置目录又声明可选，
两个事实同时为真。例外字段照旧只写差异：

```toml
# catalog.toml（仓库根）— 装但不部署，永不进 units/
[brave-origin]
label = "Brave Origin"          # optdepends 展示名；菜单显示名走 i18n app_* 键
category = "browser"
packages_aur = ["brave-origin-bin"]

[qq]
label = "QQ"
category = "social"
packages_flatpak = ["com.qq.QQ"]   # 显式空 packages 防名字泄进 pacman

[missioncenter]
label = "Mission Center"
category = "system"
detect = "mission-center"          # 目录名 missioncenter，包名连字符
packages = ["mission-center"]

# units/fcitx5-rime/manifest.toml — Fcitx 实际配置目录逐文件合流
target = "fcitx5"
merge = true
legacy_targets = { "fcitx5-rime" = "directory" }
optional = true
packages = ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"]
packages_aur = ["rime-ice-git"]
label = "Fcitx5 Rime"
category = "system"
preserve = ["conf/classicui.conf", "profile"]   # 用户层随行：部署不倒灌，off 入 Vault
post_install = "activate"       # → hooks/activate：皮肤落 ~/.local/share + rime patch
post_remove = "deactivate"      # → hooks/deactivate：撤皮肤 + 按 owned 标记回滚 rime patch

# units/greeter/manifest.toml — /etc + root + systemd 副作用全声明
optional = true
packages = ["greetd"]
packages_aur = ["noctalia-greeter"]
label = "Noctalia Greeter"
category = "system"
post_install = "activate"
post_remove = "deactivate"

[privilege]
requires_root = true
system_paths = ["/etc/greetd/config.toml", "/etc/polkit-1/rules.d/50-noctalia-greeter.rules", "/var/lib/noctalia-greeter"]
```

单元 id = 目录名；菜单显示名必须配 i18n `app_<name>`（zh/en 成对，`-` 换 `_`）。
菜单排序为**全字母序**（类别与组内条目均是），无策展顺序需要维护。

## 发现规则

- `units/` 顶层**只认目录**——每个子目录即一个单元；散落文件不是单元（死刑断言守卫顶层无文件）；
- 「只有 manifest、无配置」的包目录不是单元——住根 `catalog.toml`（KM3.5 死刑断言守卫）；
- `manifest.toml`、`__pycache__`、`hooks/` 是仓库元数据，永不落进 `~/.config`。

## 边界（含声明式边界，原 declarative 页并入）

不放进 manifest 的（会让它膨胀成小语言）：doctor 检查项、i18n 键、post-install 钩子
以外的命令式副作用。这些是 `DOCTOR_CHECKS` 列表 / `translations.toml` 的事。

声明式与命令式的分界：仓库 `units/` = 期望状态，`~/.config` = 当前状态，
`atomic_replace_item` = 对账器，Dunder = 增量保留，snapshot/rollback = 状态存取，
active 预设名 = state 文件里的显式期望——这半边是声明式。依赖安装、主题同步、
输入法重载是命令式副作用，由对应入口负责；安装可选软件只装包，不自动激活单元。
明确拒绝的规则清单（避免熵增）详见 [delayed-decisions](delayed-decisions.md) 与 [archive/agent-rules-provenance](archive/agent-rules-provenance.md)。

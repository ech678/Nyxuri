# Manifest Schema — `manifest.toml`

> 一个插件一个 manifest，**全字段可选、无文件 = 全默认**。约定自描述：目录名驱动所有默认值。
> 源码：`nyxuri/deploy/manifest.py`（`load_manifest`、`discover_manifest_apps`）。
> KM1 ② 已执法：`.module.toml` sidecar 与 `.optional-apps.toml` 两条旧机制物理删除，
> 一切收敛为目录内单一 `manifest.toml`（契约见 [plugin-model](plugin-model.md)）。

## 顶层字段（平铺，只写例外）

`plugins/<plugin>/manifest.toml`——只有需要覆盖默认时才写：

| 字段 | 默认 | 作用 |
|---|---|---|
| `packages` | `[<目录名>]` | pacman 包名。**显式 `packages = []` 保持为空**（Flatpak/AUR-only 插件防名字泄进 pacman） |
| `packages_aur` | `[]` | AUR 包名 |
| `packages_flatpak` | `[]` | Flathub app id——走 `flatpak install`，永不进 pacman/AUR/PKGBUILD |
| `target` | `""` | 单文件插件例外：插件目录只 ship 一个文件 `plugins/<plugin>/<target>`，落点 `~/.config/<target>`（如 starship）。`~/` 前缀则声明 `~/.config` 外的**共享生活区**。`xdg:<KIND>/<rest>` 走 XDG 用户目录解析（支持 8 大标准用户目录：`DESKTOP`、`DOWNLOAD`、`TEMPLATES`、`PUBLICSHARE`、`DOCUMENTS`、`MUSIC`、`PICTURES`、`VIDEOS`；未知 KIND 直接拒绝，严禁 `..` 越界——如壁纸 `xdg:PICTURES/Wallpapers`，R0-4 推广为完整映射）。target 插件不支持形态轴 |
| `merge` | `false` | 共享生活区声明：`on` 走 no-clobber 增量合流（已存在文件永不覆盖），快照只记部署落下的文件；`off` 只撤回快照文件，外来内容幸存并报告；doctor 对停用 merge 插件只把蓝图具名残留记 Ghost（见 [plugin-model](plugin-model.md) §3） |
| `runtime` | `false` | 运行态插件声明（KM4，shell 命名空间专用，见 [plugin-model](plugin-model.md) §6）：无载荷、无生活区、无 Vault 进出、无形态轴——`on`/`off` 纯账本落记 + 一次 `plugin-changed` 事件，运行中的宿主（Shell）据事件装载/卸载该域。doctor 恒 `Synced`（实机无可对账之物）。物理承载 `shell/units/<domain>/manifest.toml` |
| `morphology` | `""` | 插件形态矩阵（R0-3 显式契约，四选一：`"atomic"` / `"merge"` / `"runtime"` / `"hook-only"`）。缺省留空时由引擎根据 payload、`merge`、`runtime` 自动推导（零配置）。显式声明时校验合法性；`"hook-only"` 插件（如 greeter）无生活区目录，事务仅执行装包、特权钩子与落账，跳过 Vault 与形态轴 |
| `preserve` | `[]` | 跨部署保留的路径（按名声明，如 `monitor.kdl`；与 Dunder 不同机制）。条目可以是**目录**：整目录归运行时管理（如 fish 的 `functions/`），部署前整树注入、off 入 Vault、目录下所有文件不入账不参与 Drifted。**禁令：preserve 目录不得混铺模板 payload**——声明即承诺"模板不在此目录铺设任何文件"，混居会把 payload 永久冻结在旧版 |
| `preserve_values` | `{}` | 跨部署保留指定文本配置里的个别键，形如 `{ "noctalia-config.toml" = ["enable_ddcutil"] }`。旧文件里存在的键按原样带入新文件，缺失的键不携带，沿用新模板的值 |
| `chmod` | `[]` | 部署后设 +x 的 glob（相对插件目录，如 `scripts/*.sh`） |
| `label` | `<目录名>` | PKGBUILD optdepends 展示名 + 插件详情视图显示名 |
| `category` | `""` | 插件详情视图分组键 |
| `optional` | `false` | 可选插件：进 PKGBUILD `optdepends`，不占硬依赖（应用菜单已随 R0-2 步 5 处决） |
| `post_install` | `""` | on 侧生命周期钩子：`plugins/<plugin>/hooks/<名字>` 可执行脚本名（如 `"setup-rime"`），事务在蓝图部署后、账本快照前执行 |
| `post_remove` | `""` | off 侧生命周期钩子：同形态，实机抹白之后执行，负责清理生活区**外**的产物（KM3） |
| `[privilege]` | 无表 | 特权副作用声明：`requires_root = true` + `system_paths = [...]`（如 greeter 的 `/etc/greetd`）。只声明事实供展示与审计，不改变执行方式 |
| `dependencies` | `[]` | 依赖的其他 Nyxuri 插件（内核 resolver 的输入） |

### 插件生命周期钩子（KM3 契约）

钩子是**插件自己的行为**，不是内核业务代码——落点固定为插件目录内
`plugins/<plugin>/hooks/<名字>`（任意解释器，`#!/usr/bin/env python3` 或 `sh` 均可，
必须带可执行位）。`<module>:<function>` 旧形态随 `nyxuri/modules/` 退役（KM3 死刑）。

- **执行归属**：只有 transaction 执行钩子（内核唯一副作用层），注入
  `NYXURI_UNIT` / `NYXURI_UNIT_SRC` / `NYXURI_UNIT_DEST` 环境变量，不解释钩子内部；
- **快照口径**：`post_install` 在账本快照**之前**运行——钩子落进插件自身生活区的
  文件自动进入 `files` 快照，`off` 走正常抹白（如 fisher 装进 `~/.config/fish` 的
  插件文件无需自记账）；
- **生活区外**（`~/.local/share`、`/etc` 等）的产物 `post_remove` 自清；
- `hooks/` 是仓库元数据，永不部署进 `~/.config`，也不计入 `is_deployable`；
- 钩子失败降级 WARN，Step detail 标 `hook-failed: <名字>`，不阻断事务。

### 形态轴（`[forms]` 单节，可选——R0-2 并轨）

预设 + 零件已并轨为插件的**形态字段**（`use` 动词承载，见 [forms](forms.md)）。
`[forms]` 单节同住两轴——顶层旋钮管整型轴，子表声明槽位轴：

| 字段 | 默认 | 作用 |
|---|---|---|
| `[forms.<slot>]` 子表 | — | **槽位轴声明**：单文件热插拔（如视觉效果、发光边框），子字段见下 |
| `reload` | `[]` | 形态切换后执行的热重载命令参数列表（如 `["pkill", "-SIGUSR1", "-x", "kitty"]`），两轴共用 |
| `allow` | `[]` | **整型轴白名单**：仅列出的形态开启底版继承（未列出的保持 100% 独立） |
| `standalone` | `[]` | **整型轴黑名单**：强制列出的形态独立部署，绝不继承底版 |
| `inherit` | `false` | 全局继承开关（当 `allow` 与 `standalone` 均为空时的兜底策略） |
| `include` | `[]` | **文件白名单**：仅从底版继承匹配这些 glob 的文件/目录（如 `["scripts/**", "*.kdl"]`） |
| `exclude` | `[]` | **文件黑名单**：从底版继承时排除匹配这些 glob 的文件/目录 |

`[forms.<slot>]` 子字段：

| 字段 | 默认 | 作用 |
|---|---|---|
| `target` | （必填） | 目标配置文件相对路径（如 `"effects_normal.kdl"`）。**引擎解析时会自动将其追加到 `preserve` 保护清单中**，无需重复手动声明。 |
| `source_dir` | `<slot>` | 槽位源文件目录名（位于 `plugins/<plugin>/__forms__/<source_dir>/`） |
| `default` | `""` | 默认选用的变体名称 |

槽位变体文件存放于 `plugins/<plugin>/__forms__/<source_dir>/` 目录（例如 `effects/default.kdl`）；
整型形态目录为 `plugins/<plugin>/__forms__/<名>/`。
### 实际 ship 的 manifest

```toml
# plugins/niri/manifest.toml — monitor.kdl 被 include 引用；effects.kdl 为运行时护眼模式符号链接
preserve = ["monitor.kdl", "effects.kdl", "effects_normal.kdl", "glow.kdl", "colors.kdl", "noctalia.kdl", "eyecare_temp"]
chmod = ["scripts/*.sh", "scripts/*.py"]

[forms.effects]
target = "effects_normal.kdl"
source_dir = "effects"
default = "default"

[forms.glow]
target = "glow.kdl"
source_dir = "glow"
default = "default"

# plugins/kitty/manifest.toml — 切换形态后发送 SIGUSR1 热重载
preserve = ["current-theme.conf", "themes/noctalia.conf"]

[forms]
reload = ["pkill", "-SIGUSR1", "-x", "kitty"]

# plugins/noctalia/manifest.toml
packages = ["noctalia", "python-gobject", "gtk-layer-shell", "wl-clipboard"]
preserve_values = { "noctalia-config.toml" = ["enable_ddcutil"] }
chmod = ["wallpaper-hook.sh", "mpvpaper-sync.sh", "tools/*.sh", "tools/*.py"]

# plugins/xdg-desktop-portal/manifest.toml — 只改菜单名
label = "XDG Portals"

# plugins/starship/manifest.toml — 单文件插件（target 例外）
target = "starship.toml"
```

fastfetch **不写 manifest**（目录名 = 包名 = 二进制名 = 无例外），全默认即对。

## 可选插件（optional 轴，全部来自插件 manifest）

可选不再住 sidecar 登记簿，也不再有根 `catalog.toml`（R0-2 已并轨处决）；
packages-only 供给面（`deploy = false` × 18 个推荐软件插件 + `deps apps` 菜单）
已随 R0-2 步 5 处决——供给声明只有一种形状：`plugins/<name>/manifest.toml`，
插件装包统一走 `nyxuri on <plugin>` 事务路径。
- 真插件声明 `optional = true`（optdepends 轴：进 PKGBUILD `optdepends`，
  不占硬依赖；greeter 这类仅声明单元 = 装包 + hooks + 落账，无生活区）；
- 退役键 `deploy`（仅包声明否决）与 `detect`（菜单检测）出现即解析报错。
**zed / mango / greeter / fcitx5-rime 双轴共存**：既有配置目录又声明可选，
两个事实同时为真。例外字段照旧只写差异：

```toml
# plugins/fcitx5-rime/manifest.toml — KM3 起皮肤入插件，配置整文件化
optional = true
packages = ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"]
packages_aur = ["rime-ice-git"]
label = "Fcitx5 Rime"
category = "system"
preserve = ["conf/classicui.conf", "profile"]   # 用户层随行：部署不倒灌，off 入 Vault
post_install = "activate"       # → hooks/activate：皮肤落 ~/.local/share + rime patch
post_remove = "deactivate"      # → hooks/deactivate：撤皮肤 + 按 owned 标记回滚 rime patch

# plugins/greeter/manifest.toml — /etc + root + systemd 副作用全声明（仅声明单元）
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

插件 id = 目录名；`label` 直接进 gen-deps `optdepends` 标签（PKGBUILD 轴），
插件详情视图（`nyxuri list <plugin>`）展示 `label` 与 `category`。

## 发现规则

- `plugins/` 顶层**只认目录**——每个子目录即一个插件；散落文件不是插件（死刑断言守卫顶层无文件）；
- 「只有 manifest + hooks/」的目录也是插件（greeter 形态仅声明单元，R0-2 步 5 起
  `deploy = false` 否决键已退役——目录内容即契约，多出的实文件即成为可部署插件）；
- `manifest.toml`、`__pycache__`、`hooks/` 是仓库元数据，永不落进 `~/.config`。

## 边界（含声明式边界，原 declarative 页并入）

不放进 manifest 的（会让它膨胀成小语言）：doctor 检查项、i18n 键、post-install 钩子
以外的命令式副作用。这些是 `DOCTOR_CHECKS` 列表 / `translations.toml` 的事。

声明式与命令式的分界：仓库 `plugins/` = 期望状态，`~/.config` = 当前状态，
`atomic_replace_item` = 对账器，Dunder = 增量保留，snapshot/rollback = 状态存取，
账本里的活动形态 = 显式期望——这半边是声明式。依赖安装、主题同步、
输入法重载是命令式副作用，由对应入口负责；安装可选软件只装包，不自动激活插件。
明确拒绝的规则清单（避免熵增）详见 [delayed-decisions](delayed-decisions.md) 与 [archive/agent-rules-provenance](archive/agent-rules-provenance.md)。

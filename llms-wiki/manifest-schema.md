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
| `target` | `""` | 单文件插件例外：插件目录只 ship 一个文件 `plugins/<plugin>/<target>`，落点 `~/.config/<target>`（如 starship）。`~/` 前缀则声明 `~/.config` 外的**共享生活区**。`xdg:<KIND>/<rest>` 走 XDG 用户目录解析（当前仅 `xdg:PICTURES/<rest>`，经 `xdg-user-dir PICTURES`，中文系统即 `~/图片`；未知 KIND 直接拒绝——如壁纸 `xdg:PICTURES/Wallpapers`，R0-4 推广为完整映射）。target 插件不支持 presets/parts |
| `merge` | `false` | 共享生活区声明：`on` 走 no-clobber 增量合流（已存在文件永不覆盖），快照只记部署落下的文件；`off` 只撤回快照文件，外来内容幸存并报告；doctor 对停用 merge 插件只把蓝图具名残留记 Ghost（见 [plugin-model](plugin-model.md) §3） |
| `runtime` | `false` | 运行态插件声明（KM4，shell 命名空间专用，见 [plugin-model](plugin-model.md) §6）：无载荷、无生活区、无 Vault 进出、无 presets/parts——`on`/`off` 纯账本落记 + 一次 `plugin-changed` 事件，运行中的宿主（Shell）据事件装载/卸载该域。doctor 恒 `Synced`（实机无可对账之物）。物理承载 `shell/units/<domain>/manifest.toml` |
| `preserve` | `[]` | 跨部署保留的路径（按名声明，如 `monitor.kdl`；与 Dunder 不同机制）。条目可以是**目录**：整目录归运行时管理（如 fish 的 `functions/`），部署前整树注入、off 入 Vault、目录下所有文件不入账不参与 Drifted。**禁令：preserve 目录不得混铺模板 payload**——声明即承诺"模板不在此目录铺设任何文件"，混居会把 payload 永久冻结在旧版 |
| `preserve_values` | `{}` | 跨部署保留指定文本配置里的个别键，形如 `{ "noctalia-config.toml" = ["enable_ddcutil"] }`。旧文件里存在的键按原样带入新文件，缺失的键不携带，沿用新模板的值 |
| `chmod` | `[]` | 部署后设 +x 的 glob（相对插件目录，如 `scripts/*.sh`） |
| `label` | `<目录名>` | PKGBUILD optdepends 展示名（菜单显示名走 i18n `app_*` 键） |
| `category` | `""` | 菜单分组键，显示名走 i18n `apps_cat_<key>` |
| `detect` | `<目录名>` | 检测是否安装的命令名（纯名字，无 `binary:` 前缀 DSL） |
| `optional` | `false` | 可选插件：进应用菜单与 PKGBUILD `optdepends`，不占硬依赖 |
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

### 通用零件插槽（`[parts.<slot>]` 表，可选）

支持全系统通用零件化插槽体系，每个 `[parts.<slot>]` 定义一个可单独切换的配置零件（如视觉效果、发光边框）：

| 字段 | 默认 | 作用 |
|---|---|---|
| `target` | （必填） | 目标配置文件相对路径（如 `"effects_normal.kdl"`）。**引擎解析时会自动将其追加到 `preserve` 保护清单中**，无需重复手动声明。 |
| `source_dir` | `<slot>` | 零件源文件目录名（位于 `plugins/<plugin>/__presets__/<source_dir>/`） |
| `default` | `""` | 默认选用的零件名称 |

零件文件存放于 `plugins/<plugin>/__presets__/<source_dir>/` 目录（例如 `effects/default.kdl`）。

### 预设与继承控制（`[presets]` 表，可选）

针对预设较多、希望支持轻量差异化预设（如 Niri `glow` 仅修改 `layout.kdl`）或热重载信号的插件，可通过 `[presets]` 表精确配置：

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
# plugins/niri/manifest.toml — monitor.kdl 被 include 引用；effects.kdl 为运行时护眼模式符号链接
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

# plugins/kitty/manifest.toml — 切换预设后发送 SIGUSR1 热重载
preserve = ["current-theme.conf", "themes/noctalia.conf"]

[presets]
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

## 可选供给（`optional = true` 与根 `catalog.toml`，两源同汇）

可选不再住 sidecar 登记簿——真插件在自己的 `manifest.toml` 里声明 `optional = true`；
「装但不部署」的软件（无配置可 ship）住**根 `catalog.toml`**（KM3.5 正名：包目录清单
不是插件，17 个零文件假目录已处决）。两源同汇进 `deps apps` 菜单（T1 依赖按需化后
gen-deps `optdepends` 有意与 catalog 脱钩，见 PKGBUILD 头注释）。
**zed / mango / greeter / fcitx5-rime 双轴共存**：既有配置目录又声明可选，
两个事实同时为真。例外字段照旧只写差异：

```toml
# catalog.toml（仓库根）— 装但不部署，永不进 plugins/
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

# plugins/fcitx5-rime/manifest.toml — KM3 起皮肤入插件，配置整文件化
optional = true
packages = ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"]
packages_aur = ["rime-ice-git"]
label = "Fcitx5 Rime"
category = "system"
preserve = ["conf/classicui.conf", "profile"]   # 用户层随行：部署不倒灌，off 入 Vault
post_install = "activate"       # → hooks/activate：皮肤落 ~/.local/share + rime patch
post_remove = "deactivate"      # → hooks/deactivate：撤皮肤 + 按 owned 标记回滚 rime patch

# plugins/greeter/manifest.toml — /etc + root + systemd 副作用全声明
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

插件 id = 目录名；菜单显示名必须配 i18n `app_<name>`（zh/en 成对，`-` 换 `_`）。
菜单排序为**全字母序**（类别与组内条目均是），无策展顺序需要维护。

## 发现规则

- `plugins/` 顶层**只认目录**——每个子目录即一个插件；散落文件不是插件（死刑断言守卫顶层无文件）；
- 「只有 manifest、无配置」的包目录不是插件——住根 `catalog.toml`（KM3.5 死刑断言守卫）；
- `manifest.toml`、`__pycache__`、`hooks/` 是仓库元数据，永不落进 `~/.config`。

## 边界（含声明式边界，原 declarative 页并入）

不放进 manifest 的（会让它膨胀成小语言）：doctor 检查项、i18n 键、post-install 钩子
以外的命令式副作用。这些是 `DOCTOR_CHECKS` 列表 / `translations.toml` 的事。

声明式与命令式的分界：仓库 `plugins/` = 期望状态，`~/.config` = 当前状态，
`atomic_replace_item` = 对账器，Dunder = 增量保留，snapshot/rollback = 状态存取，
active 预设名 = state 文件里的显式期望——这半边是声明式。依赖安装、主题同步、
输入法重载是命令式副作用，由对应入口负责；安装可选软件只装包，不自动激活插件。
明确拒绝的规则清单（避免熵增）详见 [delayed-decisions](delayed-decisions.md) 与 [archive/agent-rules-provenance](archive/agent-rules-provenance.md)。

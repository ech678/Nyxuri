# Manifest Schema — `manifest.toml`

> 一个插件一个 manifest。**无文件 = 全默认；有文件必须新形态**（S0-2 协议定稿）：
> `schemaVersion` 起步、词表封闭——退役键或未声明键出现即解析报错，不设兼容期、
> 不做只读采纳、无迁移 shim。引擎（`nyxuri/deploy/manifest.py`）与壳 PluginRegistry
> 读同一份文件、执行同一套检查（契约见 [plugin-model](plugin-model.md)）。
> 语义 1:1 Omarchy 插件协议（schemaVersion / id / kinds / entryPoints / settings
> schema / 禁软链），载体与词面不跟——载体 TOML，词表见下。

## 身份字段（manifest 存在即必填）

| 字段 | 默认 | 作用 |
|---|---|---|
| `schemaVersion` | 无 | 必须为 `1`。缺或异 → 解析报错（旧形态的判别式） |
| `id` | 无 | 插件 id，必须等于 **所在根的前缀 + 目录名**（`plugins/` 根无前缀：`kitty`；`shell/plugins/` 根前缀 `shell.`：`shell.bar`；第三方根无前缀、目录名 = id 全名：简洁裸名如 `orbit-translate` 或 reverse-DNS）。漂移即报错。官方保留 `shell.` 前缀。状态键 = 此 id |
| `kinds` | 无 | 非空数组，枚举封闭：`config`（引擎部署的配置插件）+ 六几何插槽 `edge` / `island` / `overlay` / `drawer` / `surface:desktop` / `popup:notification`（壳装载，见 [plugin-model](plugin-model.md) §6）+ `service`（保留位，暂无消费者）。**消费路由**：引擎消费 config 类，壳注册表消费插槽类 |
| `label` | `<id>` | 展示名（PKGBUILD optdepends 标签 + 插件详情视图 + 壳设置/开关页） |
| `order` | `0` | ui 堆叠序（bottom → top），替代手写镜像里的数组序 |

**形态由 kinds 表达**：kinds 不含 `config` ⇒ 运行态（runtime——无载荷部署、
无生活区、无 Vault、无形态轴，`on`/`off` 纯记录状态 + 一次 `plugin-changed` 事件）。
含 `config` 才谈部署形态，见 `morphology`。`runtime = true` / `merge = true`
布尔键已杀词并轨，出现即报错。

## 部署字段（config 类，只写例外）

| 字段 | 默认 | 作用 |
|---|---|---|
| `target` | `""` | 单文件插件例外：插件目录只 ship 一个文件 `plugins/<plugin>/<target>`，落点 `~/.config/<target>`（如 starship）。`~/` 前缀则声明 `~/.config` 外的**共享生活区**。`xdg:<KIND>/<rest>` 走 XDG 用户目录解析（支持 8 大标准用户目录：`DESKTOP`、`DOWNLOAD`、`TEMPLATES`、`PUBLICSHARE`、`DOCUMENTS`、`MUSIC`、`PICTURES`、`VIDEOS`；未知 KIND 直接拒绝，严禁 `..` 越界——如壁纸 `xdg:PICTURES/Wallpapers`，R0-4 推广为完整映射）。target 插件不支持形态轴 |
| `morphology` | 推导 | 插件形态矩阵（R0-3 显式契约，config 类三选一：`"atomic"` / `"merge"` / `"hook-only"`；runtime 形态由 kinds 表达，不进此字段）。缺省推导：无可部署内容且无 target → `hook-only`，否则 `atomic`。`"merge"` = 共享生活区：`on` 走 no-clobber 增量合流（已存在文件永不覆盖），快照只记部署落下的文件；`off` 只撤回快照文件，外来内容幸存并报告（见 [plugin-model](plugin-model.md) §3）。`"hook-only"` 插件（如 greeter）无生活区目录，引擎仅执行装包、特权钩子与记录状态，跳过 Vault 与形态轴 |
| `packages` | `[<目录名>]`（ui 类为 `[]`） | pacman 包名。**显式 `packages = []` 保持为空**（Flatpak/AUR-only 插件防名字泄进 pacman） |
| `packages_aur` | `[]` | AUR 包名 |
| `packages_flatpak` | `[]` | Flathub app id——走 `flatpak install`，永不进 pacman/AUR/PKGBUILD |
| `preserve` | `[]` | 跨部署保留的路径（按名声明，如 `monitor.kdl`；与 Dunder 不同机制）。条目可以是**目录**：整目录归运行时管理（如 fish 的 `functions/`），部署前整树注入、off 入 Vault、目录下所有文件不入账不参与 Drifted。**禁令：preserve 目录不得混铺模板 payload**——声明即承诺"模板不在此目录铺设任何文件"，混居会把 payload 永久冻结在旧版 |
| `preserve_values` | `{}` | 跨部署保留指定文本配置里的个别键，形如 `{ "noctalia-config.toml" = ["enable_ddcutil"] }`。旧文件里存在的键按原样带入新文件，缺失的键不携带，沿用新模板的值 |
| `chmod` | `[]` | 部署后设 +x 的 glob（相对插件目录，如 `scripts/*.sh`） |
| `category` | `""` | 插件详情视图分组键 |
| `optional` | `false` | 可选插件：进 PKGBUILD `optdepends`，不占硬依赖（应用菜单已随 R0-2 步 5 处决） |
| `post_install` | `""` | on 侧生命周期钩子：`plugins/<plugin>/hooks/<名字>` 可执行脚本名（如 `"setup-rime"`），执行流在蓝图部署后、状态记录前执行 |
| `post_remove` | `""` | off 侧生命周期钩子：同形态，实机抹白之后执行，负责清理生活区**外**的产物（KM3） |
| `[privilege]` | 无表 | 特权副作用声明：`requires_root = true` + `system_paths = [...]`（如 greeter 的 `/etc/greetd`）。只声明事实供展示与审计，不改变执行方式 |
| `dependencies` | `[]` | 依赖的其他 Nyxuri 插件（内核 resolver 的输入） |

## 壳侧声明（ui 类）

| 字段 | 默认 | 作用 |
|---|---|---|
| `[entryPoints]` | 无 | 一个 ui kind 一条：`<kind> = "<插件内相对路径>.qml"`，键必须**恰好覆盖** kinds 里的 ui 类。禁绝对路径、`..` 越界与软链（containment 校验），文件必须真实存在。壳注册表以 file:// URL 装载（[loader-form](shell/loader-form.md) 定案） |
| `[[settings]]` | `[]` | settings schema：设置路由（panel 页 / schema 控件）与搜索锚点同一张表（原 `settings-routes.json` + 页内 JSON 字面已收编于此；S0-3a 起路由随 owning 插件声明，聚合窗只聚合） |
| `[[actions]]` | `[]` | 可搜索固定动作（搜索索引的 include 全集；见下） |

`[[settings]]` 条目（键表封闭：`id` / `title` / `context` / `icon` / `source` /
`controls` / `description` / `group` / `order` / `route` / `aliases`），
三形态恰好取一（`source` / `controls` / `route`）：

- **panel 路由条目**（有 `source`）：`source` 为插件内相对 QML 页面文件（存在性校验）；
  `description`、`group`（导航几何分组键）必填，`order`（导航序，默认 0）可选。
  路由路径由 `id` 派生（`id.split('.')`，`path` 字段已删——恒等冗余）；
  嵌套路由（`keystone.horizontal-clock`）只许一层，父路由必须同 manifest 存在。
- **schema 路由条目**（有 `controls`，S0-3b）：无页面文件——宿主用 ui/ 原子
  （Preference 五件套）按控件描述通用渲染，值存宿主 `PluginSettings` 存储
  （键 `<pluginId>.<key>`）。`description` / `group` / `order` 语义同 panel 路由。
  控件词表见下（封闭，未声明键即报错）。
- **锚点条目**（有 `route`）：搜索锚点，`route` 指向同 manifest 的路由条目；
  运行时揭示（滚动定位 + 高亮）由页面的 `SettingsSearchAnchor` 按 id 注册，
  声明数据只住 manifest。

`controls` 控件描述词表（Omarchy schema 形态的语义对位：`switch`↔boolean、
`select`↔enum、`slider`/`spin`↔integer 的两种呈现、`text`↔string；multiselect /
path 不进 v1 词表）：

| 字段 | 必填 | 作用 |
|---|---|---|
| `key` | ✓ | 叶名（禁 `.` / `:`——存储命名空间是 `<pluginId>.<key>`），路由内唯一 |
| `type` | ✓ | `switch` / `select` / `slider` / `spin` / `text` 五型封闭 |
| `title` | ✓ | 展示名（i18n 键，context 取路由 `context`） |
| `description` | | 副标描述（i18n 键） |
| `icon` | | Material Symbols 图标名 |
| `default` | | 缺省值——switch 为布尔、select 必须是选项值、slider/spin 落在 `[min, max]`、text 为字符串 |
| `options` | select 必填 | 选项数组：`{ value, label, icon? }`，value 唯一 |
| `min` / `max` | slider/spin 必填 | 数值范围，`min < max` |
| `step` | | 步进——slider 缺省 0（连续），spin 缺省 1 |

`[[actions]]` 条目（键表封闭：`id` / `target` / `method` / `args` /
`confirmation` / `availability` / `search`）：

- `id` 稳定（`nyxuri:<target>:<method>[:<arg>]`），`target` / `method` 指向
  单元 IPC 面；`args` 为固定参数（缺省 `[]`）；
- `confirmation` ∈ `none` / `power-menu`——`power-menu` 目标必须开既有确认 UI；
- `availability` ∈ `always` / `awww` / `nyxuri-wallpaper` / `wallpaper-idle` /
  `keystone` / `keyboard-lock` / `dock-previews`（能见度枚举，词表封闭）；
- `[actions.search]`：`title` / `description` / `context` / `icon` 必填，
  `aliases` 可选。`[[actions]]` 即搜索 include 全集：与
  `scripts/system/niri-actions.json` 的 binds 真值按 id 一一焊接（argv 形状
  由契约测试断言，表达式不运行），未声明 = 不进搜索索引。

### 插件生命周期钩子（KM3 契约）

钩子是**插件自己的行为**，不是内核业务代码——落点固定为插件目录内
`plugins/<plugin>/hooks/<名字>`（任意解释器，`#!/usr/bin/env python3` 或 `sh` 均可，
必须带可执行位）。`<module>:<function>` 旧形态随 `nyxuri/modules/` 退役（KM3 死刑）。

- **执行归属**：只有 engine 执行钩子（引擎唯一副作用层），注入
  `NYXURI_UNIT` / `NYXURI_UNIT_SRC` / `NYXURI_UNIT_DEST` 环境变量，不解释钩子内部；
- **快照口径**：`post_install` 在状态快照**之前**运行——钩子落进插件自身生活区的
  文件自动进入 `files` 快照，`off` 走正常抹白（如 fisher 装进 `~/.config/fish` 的
  插件文件无需自记录）；
- **生活区外**（`~/.local/share`、`/etc` 等）的产物 `post_remove` 自清；
- `hooks/` 是仓库元数据，永不部署进 `~/.config`，也不计入 `is_deployable`；
- 钩子失败降级 WARN，Step detail 标 `hook-failed: <名字>`，不阻断部署；
- **第三方 v1 拒绝钩子**（S1 安全立场：安装一步绝不执行包内代码）——第三方
  manifest 声明 `post_install` / `post_remove` 在 add / validate 即拒绝。

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
schemaVersion = 1
id = "niri"
kinds = ["config"]
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

# plugins/starship/manifest.toml — 单文件插件（target 例外）
schemaVersion = 1
id = "starship"
kinds = ["config"]
target = "starship.toml"

# shell/plugins/bar/manifest.toml — 壳 ui 插件：kinds 即形态，无部署面
schemaVersion = 1
id = "shell.bar"
kinds = ["edge"]
label = "Status Bar"
order = 30

[entryPoints]
edge = "Bar.qml"
```

fastfetch **不写 manifest**（目录名 = 包名 = 二进制名 = 无例外），全默认即对。

## 可选插件（optional 轴，全部来自插件 manifest）

可选不再住 sidecar 登记簿，也不再有根 `catalog.toml`（R0-2 已并轨处决）；
packages-only 供给面（`deploy = false` × 18 个推荐软件插件 + `deps apps` 菜单）
已随 R0-2 步 5 处决——供给声明只有一种形状：`plugins/<name>/manifest.toml`，
插件装包统一走 `nyxuri on <plugin>` 部署路径。
- 真插件声明 `optional = true`（optdepends 轴：进 PKGBUILD `optdepends`，
  不占硬依赖；greeter 这类仅声明单元 = 装包 + hooks + 落账，无生活区）；
- 退役键 `deploy` / `detect`（供给面）、`runtime` / `merge`（杀词并轨）
  出现即解析报错。
**zed / mango / greeter / fcitx5-rime 双轴共存**：既有配置目录又声明可选，
两个事实同时为真。例外字段照旧只写差异：

```toml
# plugins/fcitx5-rime/manifest.toml — KM3 起皮肤入插件，配置整文件化
schemaVersion = 1
id = "fcitx5-rime"
kinds = ["config"]
optional = true
packages = ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"]
packages_aur = ["rime-ice-git"]
label = "Fcitx5 Rime"
category = "system"
preserve = ["conf/classicui.conf", "profile"]   # 用户层随行：部署不倒灌，off 入 Vault
post_install = "activate"       # → hooks/activate：皮肤落 ~/.local/share + rime patch
post_remove = "deactivate"      # → hooks/deactivate：撤皮肤 + 按 owned 标记回滚 rime patch

# plugins/greeter/manifest.toml — /etc + root + systemd 副作用全声明（仅声明单元）
schemaVersion = 1
id = "greeter"
kinds = ["config"]
morphology = "hook-only"
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

`label` 直接进 gen-deps `optdepends` 标签（PKGBUILD 轴），插件详情视图
（`nyxuri list <plugin>`）展示 `label` 与 `category`。

## 发现规则

- `plugins/` 顶层**只认目录**——每个子目录即一个插件；散落文件不是插件（死刑断言守卫顶层无文件）；
- 「只有 manifest + hooks/」的目录也是插件（greeter 形态仅声明单元，R0-2 步 5 起
  `deploy = false` 否决键已退役——目录内容即契约，多出的实文件即成为可部署插件）；
- `manifest.toml`、`__pycache__`、`hooks/` 是仓库元数据，永不落进 `~/.config`；
- id 由蓝图根前缀派生（不从目录名字面猜命名空间）：`plugins/<id>/` 出裸 id，
  `shell/plugins/<domain>/` 出 `shell.<domain>`；
- 第三方根 `~/.local/share/nyxuri/plugins/`（S1）：只认一级目录，目录名 = manifest
  id 全名（支持纯裸名如 `orbit-translate` 或 reverse-DNS，无前缀派生）；软链拒绝统一在扫描层，与 manifest 校验同一套
  检查。落位与生命周期语义见下节。

## 第三方插件（S1 生命周期）

第三方插件不住仓库蓝图，物理落位数据域（H4）：`~/.local/share/nyxuri/plugins/<id>/`
（复制不软链，H8；`<id>` = manifest id 全名，官方保留 `shell.` 前缀）。一个位置一份 manifest，两个注册表各取所需——引擎消费 config 类、
壳注册表消费插槽类（消费路由见身份字段 `kinds` 行）。

- **安装**：`nyxuri add <git-url>`（本地目录顺带）——clone 到 staging、校验（与加载
  同一套检查）、id 冲突检查、移入落位目录、来源记账。绝不执行包内代码、无 install
  hook、无 sudo。默认 off，`--enable` 顺带启用（动词契约见 [plugin-model](plugin-model.md) §5）。
- **来源真相**：状态顶层 `sources` 键 `{id: {url, commit, added}}`——与 `forms` 键同
  模式，不碰插件记录五字段冻结；目录里不藏 sidecar。
- **移除**：`nyxuri remove <id>` = 停用 → 按文件归属记录精确撤回 → 非管辖区（用户自有、
  来源不明）内容时间戳备份。绝不整目录抹白。
- **更新**：`nyxuri update <id>` = diff 预览、拒绝非 fast-forward、校验失败自动回退
  （咬合引擎快照重基线）。无参 `update` 仍是引擎自更新（参数分派裁决）。
- **文件归属记录**：PR #148 素材回植（文件归属与保护路径记录）支撑 remove 的精确撤回；
  启用中插件的文件归属本就住在状态 `files` 字段（快照口径），remove 复用同一记录。

## 边界（含声明式边界，原 declarative 页并入）

不放进 manifest 的（会让它膨胀成小语言）：doctor 检查项、i18n 键、post-install 钩子
以外的命令式副作用。这些是 `DOCTOR_CHECKS` 列表 / `translations.toml` 的事。
`[[settings]]` 与 `[[actions]]` 的展示文案（title/description）是 i18n 键，
译文住 `commons/i18n/` 词典，manifest 只持键。

声明式与命令式的分界：仓库 `plugins/` = 期望状态，`~/.config` = 当前状态，
`atomic_replace_item` = 一致性比对器，Dunder = 增量保留，snapshot/rollback = 状态存取，
状态里的活动形态 = 显式期望——这半边是声明式。依赖安装、主题同步、
输入法重载是命令式副作用，由对应入口负责；安装可选软件只装包，不自动激活插件。
明确拒绝的规则清单（避免熵增）详见 [delayed-decisions](delayed-decisions.md) 与 [archive/agent-rules-provenance](archive/agent-rules-provenance.md)。

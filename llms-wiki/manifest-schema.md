# Manifest Schema — `.module.toml` + `.optional-apps.toml`

> 两个 manifest 文件，**全字段可选、无文件 = 全默认**。约定自描述：目录名驱动所有默认值。
> 源码：`nyxniri/deploy/manifest.py`（`load_manifest`、`load_optional_apps`）。

## `.module.toml`（有配置的 app）

`configs/<app>/.module.toml`——只有需要覆盖默认时才写。字段全在 `[packages]` 表下：

| 字段 | 默认 | 作用 |
|---|---|---|
| `repo` | `[<目录名>]` | pacman 包名 |
| `aur` | `[]` | AUR 包名 |
| `preserve` | `[]` | 跨部署保留的文件（按名声明，如 `monitor.kdl`；与 Dunder 不同机制） |
| `chmod` | `[]` | 部署后设 +x 的 glob（相对 app 目录，如 `scripts/*.sh`） |
| `label` | `<目录名>` | 菜单显示名 |
| `detect` | `<目录名>` | 检测是否安装的命令名（纯名字，无 `binary:` 前缀 DSL） |

文件型 app（`starship.toml`）用 **sidecar**：`configs/starship.toml.module.toml`（文件名 + `.module.toml`）。

### 实际 ship 的 manifest

```toml
# configs/niri/.module.toml — monitor.kdl 被 config.kdl include 引用，不能改名走 dunder
[packages]
preserve = ["monitor.kdl"]
chmod = ["scripts/*.sh"]

# configs/fish/.module.toml — clean-cache.py 不是 .sh，需声明 chmod
[packages]
chmod = ["clean-cache.py"]

# configs/noctalia/.module.toml — 三个主题脚本
[packages]
chmod = ["theme-sync.sh", "wallpaper-hook.sh", "mpvpaper-sync.sh"]

# configs/xdg-desktop-portal/.module.toml — 只改菜单名
[packages]
label = "XDG Portals"

# configs/starship.toml.module.toml — 文件型 app 的 sidecar
[packages]
repo = ["starship"]
detect = "starship"
label = "Starship"
```

kitty / fastfetch / zed **不写 manifest**（目录名 = 包名 = 二进制名 = 无例外），全默认即对。

## `.optional-apps.toml`（可选软件，无配置）

`configs/.optional-apps.toml`——configs/ 根一个文件，列所有可选软件。每块一个 `[[app]]`：

| 字段 | 默认 | 作用 |
|---|---|---|
| `name` | （必填） | app 标识 |
| `repo` | `[<name>]` | pacman 包名（Flatpak-only app 必须显式 `repo = []`，防名字泄进 pacman） |
| `aur` | `[]` | AUR 包名 |
| `flatpak` | `[]` | Flathub app id——走 `flatpak install`，永不进 pacman/AUR/PKGBUILD |
| `label` | `<name>` | PKGBUILD optdepends 展示名（菜单显示名走 i18n `app_*` 键） |
| `category` | `""` | 菜单分组键，显示名走 i18n `apps_cat_<key>`；分类顺序 = 块首次出现顺序 |
| `detect` | `<name>` | 检测安装的命令名（Flatpak app 额外用 app id 探测 `flatpak list`） |

块顺序即菜单顺序。菜单显示名必须配 i18n `app_<name>`（zh/en 成对，`-` 换 `_`）。

### 实际 ship 的（节选）

```toml
[[app]]
name = "brave-origin"
label = "Brave Origin"
category = "browser"
repo = []                       # AUR-only → repo 显式置空
aur = ["brave-origin-bin"]
detect = "brave-origin"

[[app]]
name = "qq"                     # 闭源，走 Flathub
label = "QQ"
category = "social"
repo = []
flatpak = ["com.qq.QQ"]

[[app]]
name = "missioncenter"            # 目录名 missioncenter，包名 mission-center（连字符）
label = "Mission Center"
category = "system"
repo = ["mission-center"]
detect = "mission-center"

[[app]]
name = "fcitx5-rime"
label = "Fcitx5 Rime"
category = "system"
repo = ["fcitx5", "fcitx5-gtk", "fcitx5-qt", "fcitx5-configtool", "fcitx5-rime"]
aur = ["rime-ice-git"]
```

这些 app **无配置目录**（住 configs/ 只为 apps 菜单 + PKGBUILD optdepends 知道它们存在，
解决"git 不跟踪空目录"）。例外是 **zed**：既有配置目录又登记可选（§2 双轴共存），
可选轴字段（category 等）以 toml 为准、包不进硬依赖。详见 [two-axis-config](two-axis-config.md)。

## 两个 manifest 的分工

| | `.module.toml` | `.optional-apps.toml` |
|---|---|---|
| 谁有 | 有配置的 app（每 app 一个 / sidecar） | 整个 configs/ 一个 |
| 管 | 这个 app 的配置例外（preserve/chmod/label/…） | 哪些 app 是可选软件（包名） |
| axis | A（有配置）的细节 | B（可选）的登记 |

两轴详见 [two-axis-config](two-axis-config.md)。

## 边界

不放进 manifest 的（会让它膨胀成小语言）：doctor 检查项、post-install hook、i18n 键。
这些是 `DOCTOR_CHECKS` 列表 / 代码内联 / `TRANSLATIONS` dict 的事，manifest 只管"这个 app
配置上有啥例外"。

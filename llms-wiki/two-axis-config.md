# Two-Axis Config — 可选 / 有配置 解耦

> 一个 app 有两个**独立**属性："有没有配置" 和 "是不是可选软件"。两轴正交，不绑一起。
> 源码：`nyxniri/deploy/manifest.py`。

## 为什么解耦

旧架构是二元模型：有配置 = 必装，无配置 = 可选。问题：给一个可选软件加配置会"毕业"成必装
（不想）。用户可能兴致大发给 nautilus 挂个配置，但 nautilus 该**一直保持可选**（不是所有人
用 GNOME 文件管理器）。

解耦后两轴独立：
- **有配置（axis A）**：`configs/<app>/` 目录存在 → `nyxniri install` 部署它
- **可选（axis B）**：列在 `configs/.optional-apps.toml` → 进 deps 菜单、AUR `optdepends`

一个 app 可以是：可选+无配置（nautilus 现状）、必装+有配置（niri/kitty）、**可选+有配置**
（zed 现状——既有配置又登进可选菜单）、或都不沾（不存在）。

## 两个 discover 函数（独立查询）

| 函数 | 读什么 | 干啥 | 返回 |
|---|---|---|---|
| `discover_deployable_apps()` | **扫目录**（不看 toml） | `nyxniri install` 部署 | 有 `configs/<app>/` 的 app |
| `discover_optional_apps()` | **读 toml**（不看目录） | deps 菜单 + optdepends | `.optional-apps.toml` 里的 app |

`discover_manifest_apps()` 合并两源（目录扫描 + toml 读取），返回 `(name, ModuleManifest)`
列表。一个 app 在两边都出现 → 合并后一条、`is_deployable=True` AND `is_optional=True`
（可选+有配置）；其**可选轴字段**（repo/aur/flatpak/label/category/detect）以 toml 为准，
配置轴字段（preserve/chmod）留在 `.module.toml`。

## gen-deps 的判别（axis B 优先）

```python
for _name, m in discover_manifest_apps():
    if m.is_optional:           # axis B → optdepends（即使也有配置目录）
        optdepends += packages
    elif m.is_deployable:      # axis A only → depends（必装）
        depends += packages
```

is_optional 先判——可选+配置的 app 进 optdepends（保持可选），不进 depends。

## "加配置不毕业"的场景（用户要的）

nautilus 现在在 `.optional-apps.toml`、无配置目录 → 可选、无配置。
将来兴致大发加配置：

```bash
mkdir configs/nautilus/ && 放配置文件
```

立刻：`discover_deployable_apps()` 扫到它（有目录了）→ `nyxniri install` 部署它的配置。
但 `.optional-apps.toml` 仍列着它 → 仍在 deps 菜单、仍是 optdepends。**两条轴互不干扰**，
加配置不会误伤可选性。想去掉可选性是另一个主动动作（从 toml 删条目），不会被"加配置"误触发。

## 关键：toml 不是"目录优先自动作废"

注意——这里**没有**"目录出现就自动让 toml 条目失效"的规则。两轴真独立。toml 决定可选性，
目录决定有无配置，各管各的。毕业（从可选变必装）= 主动从 toml 删条目，不是被动触发。

## .module.toml vs .optional-apps.toml 分工

- `.module.toml`（每个有配置的 app 一个，或文件型 app 的 sidecar）→ 描述**这个 app 的配置
  例外**（preserve、chmod、label、detect、packages）。详见 [manifest-schema](manifest-schema.md)。
- `.optional-apps.toml`（configs/ 根一个）→ 描述**哪些 app 是可选软件**（包名，无配置）。
  解决"git 不跟踪空目录"——可选软件无配置目录，需要 toml 作为登记载体。

无配置的可选软件（nautilus/missioncenter/fcitx5-rime 及常用软件目录里的大部分）住
configs/ 只为让 apps 菜单和 PKGBUILD optdepends 知道"有这么个可选软件、包名叫啥"——
单一扫描路径，不加第二处。

## 替代了什么

旧 `deps.py` 的 `_OPT_APP_PKG_MAP` 硬编码 dict（"nautilus"→["nautilus"]…）被这套数据化
取代——加可选软件 = 编辑 `configs/.optional-apps.toml` 加几行，不碰代码。

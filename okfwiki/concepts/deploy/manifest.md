---
type: Playbook
title: Manifest 解析与两轴发现
description: .module.toml 字段语义、discover_deployable_apps vs discover_optional_apps、缓存策略。
resource: nyxniri/deploy/manifest.py
tags: [manifest, toml, discovery, two-axis]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.85
  tier: long
  verdict: verified
  use_count: 1
---

# Manifest 解析与两轴发现

## ModuleManifest 数据类

```python
@dataclass
class ModuleManifest:
    preserve: List[str]     # 跨 deploy 保留的文件 glob
    chmod: List[str]        # 需 chmod +x 的文件 glob
    include: List[str]      # 覆盖到 ~/.config 的文件 glob（默认包含整个 app 目录）
    presets: List[str]      # 允许切换的预设名
    label: Optional[str]    # 菜单显示名（None = 用目录名）
    repo: List[str]         # 需要安装的 repo 包
    aur: List[str]          # 需要安装的 AUR 包
    detect: List[str]       # 用于探测是否已安装的二进制名
    flatpak: List[str]      # Flatpak 应用 ID
```

## 两轴设计

| 轴 | 来源 | 含义 |
|---|---|---|
| **有配置** | `configs/<app>/.module.toml` | 有 manifest 的 app，会部署配置文件 |
| **可选安装** | `configs/.optional-apps.toml` | 只装包，不部署配置 |

两者独立：一个 app 可以同时在两轴上（如 fcitx5-rime：有 config dir 但无 manifest，仅在 optional-apps）。

## discover_deployable_apps()

扫描 `configs/` 下所有含 `.module.toml` 的目录，返回 app 名列表。结果缓存到模块级 `_MANIFEST_CACHE`。

## discover_optional_apps()

解析 `.optional-apps.toml`，返回 `[[app]]` 块列表（name、label、category、repo、aur、flatpak、detect）。

---
type: Playbook
title: AUR 打包
description: gen-deps.py 聚合脚本、PKGBUILD rolling 包结构。
resource: nyxniri/packaging/gen-deps.py + PKGBUILD
tags: [aur, pkgbuild, packaging, gen-deps]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.5
  tier: short
  verdict: verified
  use_count: 1
---

# AUR 打包

## gen-deps.py

扫所有 `configs/<app>/.module.toml` + `.optional-apps.toml`，聚合：
- `repo` 字段 → makedepends/deps 块
- `aur` 字段 → aur_deps 块
- `flatpak` 字段 → 不进入 PKGBUILD（AUR 包不管理 flatpak）

输出重写 `packaging/PKGBUILD` 的 `depends=` 和 `makedepends=` 块。

## PKGBUILD

`nyxniri-git` rolling 包：
- `pkgver()` 取 git commit count
- `package()` 仅复制 nyxniri/ + configs/ + assets/ + install.sh
- 依赖由 gen-deps.py 自动生成，不手写

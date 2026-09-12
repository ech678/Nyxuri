---
type: Playbook
title: 包管理器后端
description: command() 构造、run() 包装、pacman/paru/yay/shelly 多后端切换。
resource: nyxniri/pkg/__init__.py
tags: [pkg, pacman, aur, shelly, flatpak]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.7
  tier: long
  verdict: verified
  use_count: 1
---

# 包管理器后端

## command(action, packages, source, manager)

构造后端无关的命令列表：

| 后端 | install | remove | upgrade |
|---|---|---|---|
| pacman | `sudo pacman -S --needed --noconfirm <pkgs>` | `sudo pacman -Rns <pkgs>` | `sudo pacman -Syu` |
| paru/yay | `paru -S --needed --noconfirm <pkgs>` | `paru -Rns <pkgs>` | `paru -Syu` |
| shelly | `shelly install standard --no-confirm <pkgs>` | `shelly remove <pkgs>` | `shelly upgrade all` |

AUR 源 + pacman 后端 → 抛 ValueError（pacman 不能装 AUR）。

## run(argv, capture=False, timeout=INSTALL_TIMEOUT)

subprocess.run 包装：
- timeout=1800s（安装）/ 30s（查询）
- 超时 → CompletedProcess(returncode=124, stderr="Timed out...")
- OSError → returncode=127
- 正常失败 → 返回原退出码（不抛）

## install() / install_flatpaks()

高层接口：去重包列表、调用 command()+run()，返回 bool。

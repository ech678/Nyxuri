---
type: Playbook
title: 常量与项目标识
description: nyxniri/constants.py 中所有静态定义——项目名、WM、依赖列表、网络镜像、ANSI 色阶。
resource: nyxniri/constants.py
tags: [constants, identity, deps, colors]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.8
  tier: long
  verdict: verified
  use_count: 1
---

# 常量与项目标识

## 项目身份

| 常量 | 值 | 说明 |
|---|---|---|
| `PROJECT_NAME` | `"NyxNiri"` | 项目名称，出现在所有 TUI 文案和状态文件路径中 |
| `CLI_CMD` | `"nyxniri"` | Fish 补全和 PATH 软链的基准名 |
| `MAIN_WM` | `"niri"` | 主窗口管理器，决定会话入口和诊断检查 |
| `THEME_ENGINE` | `"noctalia"` | 顶栏/状态引擎 |
| `GREETER_PKG` | `"noctalia-greeter"` | greetd 登录界面包名 |
| `FCITX_THEME` | `"nyxmellow"` | Fcitx5 皮肤名 |

## 依赖列表

**CORE_DEPS**（25 项，Arch 官方仓库）：niri、noctalia、wlsunset、fish、starship、kitty、fastfetch、eza、mpvpaper、ffmpeg、jq、tmux、inotify-tools、fzf、python-gobject、gtk-layer-shell、ttf-jetbrains-mono、ttf-jetbrains-mono-nerd、noto-fonts-cjk

**AUR_DEPS**：mpvpaper（部分发行版不在官方仓库）

## 网络镜像

- `GIT_MIRROR_REGISTRY`：Official + gh-proxy.org（通过 `NYXNIRI_REPO` 环境变量可覆盖为自定义源）
- `WALLPAPER_MIRRORS`：Official GitHub + gh-proxy.org
- `RAW_MIRROR_TEMPLATES`：raw.githubusercontent.com + jsDelivr CDN + gh-proxy.org

## ANSI 色阶

`Colors` 类封装项目原生色阶（RED/GREEN/YELLOW/BLUE/PURPLE/CYAN/WHITE/DARK_GRAY + BOLD 变体），TUI 统一使用，不引入第三方色库。

---
type: Playbook
title: Fcitx5 NyxMellow 皮肤模块
description: fcitx_install/uninstall、模板注册、主题字段恢复、旧 QuickPhrase 备份清退。
resource: nyxniri/modules/fcitx.py
tags: [fcitx, skin, nyxmellow, input-method]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.65
  tier: long
  verdict: verified
  use_count: 1
---

# Fcitx5 NyxMellow 皮肤模块

## 路径结构

```
~/.local/share/fcitx5/themes/nyxmellow/templates/  ← 皮肤模板（assets/fcitx5/nyxmellow/templates/ 部署）
~/.config/fcitx5/conf/classicui.conf                ← 主题字段写入目标
~/.config/NyxNiri/state/fcitx-nyxmellow-theme.prev  ← 上次部署快照
~/.config/NyxNiri/state/fcitx-nyxmellow.enabled     ← 用户同意标记
```

## 关键函数

- `fcitx5_installed()` — `shutil.which("fcitx5")`
- `fcitx_enabled()` — 检测 enabled marker 文件
- `fcitx_templates_registered()` — 检查 templates 目录是否存在
- `fcitx_install()` — 部署皮肤 + 写 classicui.conf + 写 enabled marker
- `fcitx_uninstall()` — 恢复 .prev 快照 + 清退 templates
- `fcitx_reload()` / `fcitx_trigger_render()` — 通知 fcitx5 重读配置

## 变更隔离

卸载时只改 NyxNiri 写入的内容（classicui.conf 的主题字段、templates 目录），不碰用户其他 fcitx5 配置。

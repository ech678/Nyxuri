---
type: Playbook
title: GTK Material You 主题模块
description: GTK4 @media 双块、settings.ini 兼容、主题渲染触发。
resource: nyxniri/modules/gtktheme.py
tags: [gtk, theme, material-you, rendering]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.55
  tier: short
  verdict: verified
  use_count: 1
---

# GTK Material You 主题模块

## 渲染机制

GTK4 使用双 `@media` 块（dark/light）在 `~/.config/gtk-4.0/gtk.css` 中定义主题；
同时维护 `~/.config/gtk-3.0/settings.ini` 以保持 GTK3 应用兼容。

## 关键函数

- `gtktheme_registered()` — 检查 GTK CSS 文件是否存在
- `gtktheme_rendered()` — 检查主题颜色变量是否正确写入
- `gtktheme_install()` — 写入 GTK CSS + settings.ini
- `gtktheme_uninstall()` — 清退 NyxNiri 写入的内容（保留用户原有 GTK 配置）
- `gtktheme_trigger_render()` — 触发 noctalia 重读 GTK 主题信号

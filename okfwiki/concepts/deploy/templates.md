---
type: Playbook
title: 模板渲染
description: /home/user 占位符替换、screenshot-path 动态生成、per-app 窄路径。
resource: nyxniri/deploy/templates.py
tags: [template, render, placeholder, home]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.6
  tier: short
  verdict: verified
  use_count: 1
---

# 模板渲染

## _phase_render_templates(only_app=None)

仅修改已部署的配置文件中的路径占位符：

| 文件 | 替换内容 |
|---|---|
| `niri/config.kdl` | `/home/user` → `$HOME`；`screenshot-path` 动态计算相对路径 |
| `noctalia/noctalia-config.toml` | `/home/user` → `$HOME`；`directory` / `video_directory` → 壁纸路径 |
| `fish/fish_variables` | `/home/user` → `$HOME` |

`only_app` 非 None 时只处理对应 app（预设切换的窄路径，避免跨 app 副作用）。

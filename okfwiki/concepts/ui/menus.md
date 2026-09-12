---
type: Playbook
title: 菜单导航编排
description: main_menu_loop、run_master_component_menu、各子菜单协调。
resource: nyxniri/menus.py
tags: [menu, navigation, tui, interaction]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.7
  tier: long
  verdict: verified
  use_count: 1
---

# 菜单导航编排

## 主菜单树

```
main_menu_loop()
├── install / update
├── preset (preset_switcher_loop)
├── snapshot (snapshot_menu_loop)
├── rollback (list_backups + select)
├── deps (deps_menu_loop)
├── apps (run_optional_apps_menu_loop)
├── greeter (greeter_menu_loop)
├── fcitx (fcitx_menu_loop)
├── gtk (gtk_menu_loop)
├── fisher (fisher_menu_loop)
├── wallpapers (wallpaper picker)
├── clean (clean.main)
├── doctor (run_doctor)
└── uninstall (uninstall_nyxniri)
```

## run_master_component_menu(is_update, mode)

安装向导的核心组件选择面板：
- 展示所有可部署 app（有 manifest 的）供勾选
- 询问壁纸下载、fcitx、greeter 等附加项
- 调用 `_phase_preflight_check()` 前置确认
- 返回选择结果 dict → workflows.install_configs_workflow() 编排执行

## 非 TTY 降级

所有交互函数在非 TTY（管道/CI）时自动静默通过（相当于默认选中）。

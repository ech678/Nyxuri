---
type: Playbook
title: CLI 命令分发
description: COMMANDS dict 结构、_module_handler 工厂、exit code 传播。
resource: nyxniri/cli.py
tags: [cli, command, dispatch, exit-code]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.8
  tier: long
  verdict: verified
  use_count: 1
---

# CLI 命令分发

## COMMANDS dict

```python
COMMANDS = {
    "install":   (_cmd_install,   "Install or update configs"),
    "update":    (_cmd_update,    "Pull latest and redeploy"),
    "preset":    (_cmd_preset,    "Preset switcher"),
    "snapshot":  (_cmd_snapshot,  "Create config snapshot"),
    "rollback":  (_cmd_rollback,  "Roll back to a snapshot"),
    "list":      (_cmd_list,      "List available configs/presets"),
    "uninstall": (_cmd_uninstall, "Checkbox-style uninstall"),
    "doctor":    (_cmd_doctor,    "System health diagnostics"),
    "deps":      (_cmd_deps,      "Dependency check/install"),
    "apps":      (_cmd_apps,      "Optional apps menu"),
    "wallpapers":(_cmd_wallpapers,"Wallpaper management"),
    "clean":     (_cmd_clean,     "Cache cleanup"),
    "test":      (_cmd_test,      "Sandbox deploy test"),
    "bug":       (_cmd_bug,       "Generate bug report"),
    "help":      (_cmd_help,      "Show usage"),
    # module commands routed through _module_handler:
    "greeter":   (_module_handler("greeter", ...),  "..."),
    "fcitx":     (_module_handler("fcitx", ...),    "..."),
    "gtk":       (_module_handler("gtktheme", ...), "..."),
}
```

## _module_handler(module_name, triad_name)

工厂函数，动态 `importlib.import_module(f"nyxniri.modules.{module_name}")`，返回 triad（install/status/uninstall）中的指定动作。
测试时 mock 直接命中源模块（不走 re-export 缓存）。

## main()

解析 `sys.argv[1:]`，dispatch 到对应 handler，handler 返回 int exit code → `sys.exit(code)` 自动传播。

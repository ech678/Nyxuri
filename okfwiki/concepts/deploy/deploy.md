---
type: Playbook
title: 部署编排器
description: deploy_selected_configs 全流程——逐 app atomic_replace、post-install 服务触发、完成界面。
resource: nyxniri/deploy/deploy.py
tags: [deploy, orchestration, post-install, completion]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.9
  tier: long
  verdict: verified
  use_count: 1
---

# 部署编排器

## discover_config_items()

返回有 manifest 的可部署 app 列表（缓存，同一次进程内只扫一次）。

## deploy_selected_configs(items, ...)

逐 app 循环：
1. 调用 `resolve_preset_src()` 确定源目录
2. 调用 `atomic_replace_item()` 完成 swap+preserve
3. 若目标有 `.module.toml` 的 `chmod` 声明，设置执行位
4. 失败 app 加入 `failed_items` 列表继续（不中断整体流程）

## _phase_post_install_services()

触发以下后安装步骤：
- `noctalia msg reload`（若有守护进程响应）
- GTK theme render trigger（若 gtktheme 模块已安装）

## run_user_hooks()

运行 `~/.config/NyxNiri/hooks/post-deploy.sh`（若存在），timeout 30s，失败只 WARN 不阻断。

## render_completion_screen()

打印部署结果摘要：成功 app 数、失败 app 列表、壁纸状态行（8 分支枚举）、模块安装状态。

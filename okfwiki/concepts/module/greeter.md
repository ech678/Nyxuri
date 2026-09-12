---
type: Playbook
title: Noctalia Greeter 模块
description: greetd 登录界面安装、/etc/greetd 写入、polkit 规则、安全性约束。
resource: nyxniri/modules/greeter.py
tags: [greeter, greetd, login, system-level]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.75
  tier: long
  verdict: verified
  use_count: 1
---

# Noctalia Greeter 模块

## 系统路径

| 路径 | 用途 |
|---|---|
| `/etc/greetd/config.toml` | greetd 主配置（写入 session 命令） |
| `/etc/polkit-1/rules.d/50-noctalia-greeter.rules` | polkit 免密规则 |
| `/var/lib/noctalia-greeter/` | greeter 运行时状态 |
| `/etc/greetd/nyxniri-display-manager` | NyxNiri 安装标记 |

## 安全约束

`_trusted_executable(candidate)` 拒绝：
- 路径不在 `/usr/bin` 或 `/usr/local/bin`
- 文件不可执行或非正则文件
- 所有者非 root 或父目录 world-writable
- 路径含不安全字符（控制字符、`$`、`'`、`;`、`&` 等）

## 冲突检测

安装前检查是否已有其他 DM（sddm/lightdm/gdm/ly）接管 greetd，冲突时拒绝安装并提示。

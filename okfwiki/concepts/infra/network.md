---
type: Playbook
title: 网络操作
description: 多镜像 git pull/clone、超时降级、curl 容错、cancelable 交互。
resource: nyxniri/network.py
tags: [network, git, mirror, timeout]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.7
  tier: long
  verdict: verified
  use_count: 1
---

# 网络操作

## Git 网络参数

`_GIT_NET` flags（全局作用于所有 git 命令）：
```
-c http.lowSpeedLimit=1000
-c http.lowSpeedTime=15
-c http.connectTimeout=10
-c http.timeout=20
```
低于 1000 B/s 持续 15s 自动中断，避免弱网卡死。

## safe_git_pull()

多镜像重试：遍历 `GIT_MIRROR_REGISTRY`，每个镜像独立尝试，失败切下一个。
TTY 环境下支持 Esc/Ctrl+C 取消当前尝试（不取消整个列表）。

## safe_git_checkout_ref(ref)

类似逻辑，用于 `install.sh update --to <ref>` 场景。

## git_clone_timeout(url, dest, cancellable)

带超时的 clone，返回 bool；失败不抛异常，调用方自行处理。

## 容错原则

所有网络调用超时 → 降级继续，不阻断部署流程。用户感知为 WARN 日志 + 跳过步骤。

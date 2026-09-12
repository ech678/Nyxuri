---
type: Playbook
title: 核心基础设施
description: Environment 解析、文件锁、path 原语、超时包装、临时路径清理——所有模块的底层基石。
resource: nyxniri/core.py
tags: [core, environment, locking, paths, timeout]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.95
  tier: long
  verdict: verified
  use_count: 1
---

# 核心基础设施

## Environment 数据类

```python
class Environment:
    home: Path          # os.environ["HOME"]
    config_dir: Path    # ~/.config
    state_dir: Path     # ~/.local/state/NyxNiri
    cache_dir: Path     # ~/.cache/NyxNiri
    pictures_dir: Path  # ~/Pictures
    run_mode: str       # "system" | "repo" | "standalone"
    repo_dir: Path      # 仓库根（standalone 时为 cache 目录）
    config_dir_src: Path  # 仓库内 configs/
    assets_dir_src: Path  # 仓库内 assets/
```

**run_mode 检测逻辑**（§5.2）：
1. `.system-install` marker 存在 → `"system"`（AUR/包管理器安装）
2. root_dir == cache_dir → `"standalone"`（curl 装到 cache）
3. root_dir 含 configs/ + assets/ → `"repo"`（git clone 本地）
4. 否则 → fallback `"standalone"`

## path 原语

- `copy_path(src, dest)` — symlink-aware 复制（顶层软链保持为软链，目录用 copytree）
- `remove_path(path)` — 先判 is_symlink()，再判 is_dir()，最后 unlink；不跟随软链
- `register_temp_path(path)` / `cleanup_temp_paths()` — atexit 钩子自动清理 mktemp 产物

## 超时包装

`timed_run(argv, timeout, **kwargs) -> CompletedProcess | None`：
- 正常完成 → 返回 CompletedProcess（退出码原样）
- 超时 → 返回 None（**不抛 TimeoutExpired**）
- 调用方拿到 None 按各自语义降级，不阻断主流程

## 文件锁

`acquire_lock()` / `release_lock()` 用 fcntl F_OFD_SETLK，非阻塞；并发运行 install/update/rollback 时互斥。

## 日志

`init_logger()` 写 `~/.cache/NyxNiri/engine.log`；`log_msg(level, msg)` 追加写入。

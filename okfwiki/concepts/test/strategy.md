---
type: Playbook
title: 测试策略
description: TempEnv 隔离原则、mock 层级约束、契约测试要求。
resource: tests/utils.py + tests/test_*.py
tags: [testing, isolation, mock, contract-test]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.7
  tier: long
  verdict: verified
  use_count: 1
---

# 测试策略

## TempEnv 隔离

```python
with TempEnv() as env:
    # env.home 指向 mktemp 目录
    # os.environ["HOME"] 被 patch 为 env.home
    # core._ENV 被重置
    # 所有 nyxniri 调用自动指向临时环境
```

**铁律**：测试禁止碰实 `~/.config`、`~/.local`、`~/.cache`。

## Mock 层级约束

Mock 必须紧贴被测代码的**直接依赖**，不打太高：

- 测 `safe_git_pull()` → mock `_run_git_transfer()`（经过 `_with_git_progress` 的参数变形）
- 测 `deploy_selected_configs()` → mock `atomic_replace_item`（源模块直接 import）
- 测 `_module_handler()` → mock `importlib.import_module`（动态 import 路径）

Mock 打太高（如 mock `subprocess.run` 全局）会绕过命令构造逻辑，失去测试意义。

## 契约测试

外部命令构造函数（`pkg.command()`、`_run_git_transfer()` 等）必须有"参数列表形状"断言：
- 检查 argv 长度
- 检查关键 flag 是否存在
- 不依赖实际执行结果（mock subprocess）

## 验证命令

```bash
python3 -m compileall nyxniri          # 语法基线
python3 -m unittest discover -s tests -q  # 契约测试
HOME=$(mktemp -d) ./install.sh test    # 沙箱部署测试
```

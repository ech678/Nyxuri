---
type: Playbook
title: 模块生命周期合约
description: module_action() context manager——写入失败返回 False、中断继续上抛。
resource: nyxniri/modules/lifecycle.py
tags: [lifecycle, module, error-handling]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.6
  tier: short
  verdict: verified
  use_count: 1
---

# 模块生命周期合约

## module_action() context manager

```python
@contextmanager
def module_action(module_name, action):
    try:
        yield
    except Exception as e:
        log_msg("ERROR", f"{module_name} {action} failed: {e}")
        raise  # 中断上抛，让外层知道某模块失败
```

所有模块的 install/uninstall 都包在此 context manager 内：
- 写入失败 → 返回 False + 日志
- 不静默吞异常（与 deploy 阶段超时降级不同）
- 外层（menus.py 各子菜单）捕获后决定是继续还是中断流程

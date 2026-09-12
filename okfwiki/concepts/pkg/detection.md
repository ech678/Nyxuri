---
type: Playbook
title: 依赖探测
description: DependencyProbe 独立缓存、每轮重扫、flatpak 探测。
resource: nyxniri/pkg/detection.py
tags: [detection, probe, dependency, cache]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.55
  tier: short
  verdict: verified
  use_count: 1
---

# 依赖探测

## DependencyProbe

每次实例化时独立缓存，不跨轮次共享（避免 stale 状态）：

```python
class DependencyProbe:
    def installed(self, cmd: str) -> bool:
        # shutil.which(cmd) + 版本验证（部分包需要 --version 确认）
    
    @property
    def flatpaks(self) -> Set[str]:
        # flatpak list --system --columns=application
```

## 探测范围

- CORE_DEPS 中每项 → `which()` + 版本检查
- AUR_DEPS 中每项 → 同上（但 AUR 不存在时不算 missing）
- flatpak apps → `flatpak list` 输出解析

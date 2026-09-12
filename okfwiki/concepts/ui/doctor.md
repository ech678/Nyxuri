---
type: Playbook
title: 系统诊断
description: _check_* 体系、DOCTOR_CHECKS append 扩展、bug report 导出。
resource: nyxniri/doctor.py
tags: [doctor, diagnostic, health-check]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.65
  tier: long
  verdict: verified
  use_count: 1
---

# 系统诊断

## DOCTOR_CHECKS 结构

```python
DOCTOR_SECTIONS = [
    ("Compositor",    [_check_compositor, _check_wayland_session]),
    ("Core Apps",     [_check_noctalia, _check_core_deps]),
    ("Scripts",       [_check_scripts, _check_eyecare, _check_scratchpad, _check_orbit]),
    ("Shell",         [_check_shell, _check_fisher]),
    ("Audio/Bright",  [_check_audio, _check_brightness]),
    ("Portal",        [_check_portal_active, _check_portal_gtk, _check_portal_config]),
    ("Disk",          [_check_disk_space]),
    ("Modules",       [_check_fcitx_skin]),
]
DOCTOR_CHECKS = [chk for _, checks in DOCTOR_SECTIONS for chk in checks]
```

加新检查项：写 `_check_xxx(env) -> None`，append 到对应 section 列表，**不动 `run_doctor()`**。

## _check_* 函数契约

- 接受 `env: Environment` 参数
- 调用 `print(msg("doctor_ok", ...))` / `print(msg("doctor_warn", ...))` / `print(msg("doctor_err", ...))`
- 不调用 `sys.exit()` 或抛异常（全部 check 完成后汇总）

## generate_bug_report(env)

并行收集系统信息（platform、进程、磁盘、包状态），汇总为文本块供用户粘贴到 issue。

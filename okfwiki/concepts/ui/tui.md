---
type: Playbook
title: TUI 组件引擎
description: TerminalGuard 光标保障、Menu/CheckboxList/PresetSwitcher 组件、ANSI 输出协议。
resource: nyxniri/tui.py
tags: [tui, terminal, ansi, guard]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.85
  tier: long
  verdict: verified
  use_count: 1
---

# TUI 组件引擎

## TerminalGuard（绝对保障）

```python
class TerminalGuard:
    @classmethod
    def init(cls):           # 保存原始 termios 属性，注册 atexit + signal handler
    @classmethod
    def restore(cls):        # 恢复属性 + 关闭 mouse tracking + 显示光标
    @classmethod
    def _sig_handler(cls, signum, frame):  # SIGINT/SIGTERM 时立即恢复
```

**铁律**：`TerminalGuard.init()` 必须在程序入口处调用（`__main__.py` 已做）。

## 核心组件

| 组件 | 用途 |
|---|---|
| `Menu` | 单列选择菜单（箭头导航 + 回车确认） |
| `CheckboxList` | 多选列表（Space 勾选 + 回车确认） |
| `CategoryCheckboxList` | 带分组的 CheckboxList（apps 菜单用） |
| `PresetSwitcher` | 树状折叠预设工作台（Accordion Tree） |
| `prompt_confirm(q, default)` | Y/n 确认框（非 TTY 时静默返回 default） |

## 输出协议

- 只用 ANSI 转义码（`colors.Colors.*`），不引入 rich/ink 等第三方库
- 状态行用 `[✓]` `[!]` `[✗]` 符号（纯 ASCII，不依赖 emoji）
- 过程状态就地更新（`CLEAR_LINE` + `\r`），不刷屏

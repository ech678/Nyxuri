---
type: Playbook
title: 预设切换机制
description: active 文件读写、src 四分支解析、切换时序铁律、安全校验。
resource: nyxniri/deploy/preset.py
tags: [preset, active, switch, safety]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.9
  tier: long
  verdict: verified
  use_count: 1
---

# 预设切换机制

## 三层叠加

```
默认 config/  ←  官方预设 presets/<name>/  ←  __custom__ 文件
```

`~/.config/NyxNiri/presets/<app>.active` 记录当前激活状态（内容为预设名或 `"default"`）。

## resolve_preset_src(app, active, dest) → PresetSrcResult

四分支逻辑：
1. `active == "default"` → 直接部署 `configs/<app>/`
2. `active` 在 manifest `presets.allow` 列表中 → 部署 `configs/<app>/presets/<active>/`
3. `active` 是用户自定义 preset（`edit_preset` 创建的） → 部署 `~/.config/NyxNiri/presets/<app>/<active>/`
4. `active` 无效 → 返回 `InvalidActivePresetError`，触发冻结保护

## 时序铁律

**apply first, write active after**：先完成目标目录的原子替换，再写 `.active` 文件。
唯一例外：dest 缺失时允许先写 active（半写状态下次 run 自愈）。

## 安全校验

`_is_safe_component(value)` 拒绝：
- 空字符串、`.`、`..`
- 绝对路径、含路径分隔符
- 超过 255 字节或非 Unicode 控制字符
- 路径穿越（resolve 后不在 root 下）

`InvalidActivePresetError` 触发后：目标目录冻结，打印警告，跳过该 app。

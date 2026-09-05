# Orbit Launcher — 星环启动器设计规格

> Material 3 Expressive 星环启动器：高频 Scratchpad / 快捷工具箱。极致手感、物理秩序、
> 肌肉记忆、键盘友好、支持文件夹子环。入口：`configs/niri/scripts/orbit-launcher.py`；实现：`configs/niri/scripts/orbit/`（`window.py` 主体、`physics.py`、`config.py`、`renderer.py`）。

## 快捷键

| 功能 | 快捷键 |
|---|---|
| 打开主星环 | `Mod + A`（`Super + A`）或 `Mod + MouseForward` |
| 执行当前项 | `Enter` / 鼠标左键 / 松开 `Super` |
| 进入文件夹子环 | `Enter` / 左键 / 松开 `Super` |
| 返回父级 | `Backspace` / `Esc` / 右键 |
| 关闭星环 | `Esc` |
| 数字直达 | `1 - 9` |
| 第二层直达 | `Super + 1 - 9` |
| Vim 轮转 | `h / j / k / l` |
| 方向键轮转 | `← ↓ ↑ →` |
| 首字母助记 | `a - z` |
| 滚轮轮转 | 鼠标滚轮 |

## 双模手势

- **浏览模式**：`Mod + A` 打开后移动鼠标 / Tab / 滚轮浏览，点击或 `Enter` 执行。适合探索、查找、确认。
- **盲甩模式**：按住 `Super` 或鼠标左键向目标方向甩出，松开即执行。适合肌肉记忆用户，零思考启动。

## 状态机

```
IDLE
  ↓ Mod + A / MouseForward
RING_OPEN
  ↓
EXPLORE
  ↓
FLICK_AIM
  ↓
EXECUTE
  ↓
LAUNCH / DRILL_DOWN
  ↓
IDLE 或 SUB_RING
```

子环回退：

```
SUB_RING
  ↓ Backspace / Esc / 右键
BACK_TO_PARENT
  ↓
RING_OPEN
```

## 极坐标与防抖

```
r = sqrt(dx² + dy²)
θ = atan2(dy, dx)
sector = round(θ / Δ)
Δ = 2π / N
```

- **死区**：`r < 48px`（`DEADZONE_RADIUS = 48.0`）不触发选择。
- **角度滞后**：进入新扇区需偏离 `> 6°`（`HYSTERESIS_DEG = 6.0`，非对称施加于当前 hover 项）。防边缘跳变、防指针抖动误触。

## 物理弹簧参数

统一二阶阻尼弹簧：`x'' = -ω²(x - target) - 2ζωx'`

| 场景 | 阻尼 ζ | 频率 ω |
|---|---:|---:|
| 星环绽放 | 0.70 | 14 rad/s |
| 扇区吸附 | 1.00 | 18 rad/s |
| 盲甩结束 | 0.78 | 22 rad/s |
| 子环进入 | 0.80 | 15 rad/s |
| 子环退出 | 0.90 | 16 rad/s |
| 胶囊形变 | 0.65 | 12 rad/s |

手感目标：打开有呼吸感、吸附有落锁感、盲甩有确定感、子环有引力感。

## 盲甩释放

按住 `Super` 或鼠标左键移动到目标方向后松开，触发当前 hover 的胶囊。释放判定不依赖
速度、按住时长或拖拽距离——只看松手瞬间 hover 在哪。`on_button_release` /
`on_key_release`（`window.py:573,617`）直接调 `trigger_app`。

> 设计意图：盲甩靠极坐标死区 + 角度滞后保证 hover 稳定落在目标扇区，松手即确定——
> 不做松手后的角度预测补偿，避免预测偏差制造"甩到隔壁"的失控感。

## 文件夹子环

- **下钻**：选中文件夹后 `Enter` / 左键 / 松开 `Super`。动效——父环缩小后退、子环从中心弹出、新的引力核心形成。
- **回退**：`Backspace` / `Esc` / 右键。动效——子环沿切线退出、缩回父环、父环保留空间位置。

## 一句话总设计

> `Mod + A`（或 `Mod + MouseForward`）打开星环；轻用 hover 浏览，重用 hold-flick-release 盲甩；极坐标死区 + 角度滞后防误触；所有动画统一走二阶弹簧；文件夹用"父环后退、子环弹出"的引力隐喻。

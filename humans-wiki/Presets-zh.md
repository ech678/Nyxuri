有些应用自带多套风味——预设叠在默认配置和你的 `__custom__` 之间，切换不会碰你的自定义改动。

内置官方预设：
- **`kitty`**：
  - `default`：标准 90% 不透明度
  - `transparent`：75% 半透明高透风味
- **`niri`**：
  - `default`：极致极简无边框（默认）
  - `glow`：启用 2px 轮廓与 28px 柔和弥散光晕（解决多窗口平铺下的焦点识别问题）
  - `glow-material-you`：聚焦光晕跟随 Noctalia 当前壁纸提取的 Material You 配色（实时动态重绘）

预设体系同时支持独立零件插槽（Parts slot，如 `niri` 的 `glow` 与 `effects`），既可一键应用整套预设，也能自由组合叠加视觉部件。

---

## 预设管理指令

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri preset <app> list` | 列出预设（`*` 标当前活动） |
| `nyxuri preset <app> apply <name>` | 切换预设（`apply default` 回默认） |
| `nyxuri preset <app> save <name>` | 把当前配置存为私有预设 |
| `nyxuri preset <app> edit <name>` | 在 `$EDITOR` 里改私有预设 |
| `nyxuri preset <app> delete <name>` | 删除私有预设（官方预设只读） |

官方预设随 `nyxuri update` 更新；私有预设存在 `~/.config/nyxuri/presets/`。

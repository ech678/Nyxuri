插件可以提供多套形态。形态叠在默认配置和私有改动之间，切换时会保留你的修改。用 `nyxuri use` 管理形态。

内置官方形态：
- **`kitty`**：
  - `default`：标准 90% 不透明度
  - `transparent`：75% 半透明高透风味
- **`niri`**：
  - `default`：极简无边框（默认）

---

## 槽位轴 (Niri)

除切换整套形态外，插件还可声明**槽位轴**，单独切换某个视觉组件：

- **`glow`**（窗口焦点轮廓与弥散光晕）：
  - `default`：无轮廓、无光晕极简风
  - `glow`：启用 2px 轮廓与 28px 柔和弥散光晕，增强平铺窗口下的焦点识别
  - `glow-material-you`：聚焦光晕实时跟随 Noctalia 当前壁纸提取的 Material You 配色（动态重绘）
- **`effects`**（合成器着色器与模糊）：
  - `default`：标准窗口渲染
  - `xray-blur`：窗口透光与背景毛玻璃模糊

切换槽位轴：`nyxuri use niri slot <轴> <变体>`。

---

## 形态指令

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri use <插件> list` | 列出全部形态（`*` 标当前活动） |
| `nyxuri use <插件> <形态>` | 切换形态（`use <插件> default` 回默认） |
| `nyxuri use <插件> slots` | 查看可用槽位轴与可选变体 |
| `nyxuri use <插件> slot <轴> <变体>` | 切换单个槽位轴（如 glow、effects） |
| `nyxuri use <插件> save <名>` | 把当前配置存为私有形态 |
| `nyxuri use <插件> edit <名>` | 在 `$EDITOR` 里改私有形态 |
| `nyxuri use <插件> delete <名>` | 删除私有形态（官方形态只读） |

官方形态随 `nyxuri update` 更新；私有形态存在 `~/.config/nyxuri/forms/`。

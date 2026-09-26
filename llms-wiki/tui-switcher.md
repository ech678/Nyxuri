# TUI Preset Switcher — 双栏工作台拓扑、左右分栏焦点、原位无熵操作

> CLI（`nyxuri preset <app> apply <name>`）之外，交互菜单提供自包含的 Preset Studio 工作台。
> 采用 **双栏（Dual-Pane）工作台拓扑**：左栏应用列表与状态，右栏预设方案与独立零件双分区，下方支持可折叠详情卡片。源码：`nyxuri/tui.py`（`PresetSwitcher`）。

## 布局与视线设计

```text
  NYXURI  ·  预设与零件管理

  [应用列表]               │ [配置详情 · niri]
    fastfetch    default   │  ── 预设方案 ──
    fish         default   │  ❯ default                   ●
    kitty        transp.   │
  ❯ niri         default   │  ── 独立零件 ──
    noctalia     default   │    ▸ 零件 · 特效 (effects)    default
                           │    ▸ 零件 · 发光 (glow)       default

  ────────────────────────────────────────────────────────────

  [Tab] 详情   [Enter] 应用/展开   [←/→] 切栏   [s] 保存   [e] 编辑   [d] 删除   [q] 返回
```

### 展开详情视图（按 `Tab` / `i` 或鼠标点击）：
```text
  ────────────────────────────────────────────────────────────

  源: configs/kitty/__presets__/transparent

  ▾ 包含文件 (2):
      · current-theme.conf
      · kitty.conf

  ▾ 保留文件 (1):
      · monitor.kdl

  [Tab] 详情   [Enter] 应用/展开   [←/→] 切栏   [s] 保存   [e] 编辑   [d] 删除   [q] 返回
```

### 双栏交互法则 (Dual-Pane Rules)
- **左右分栏焦点**：
  - **左栏**：宽度约为 `cols // 3`（22~32 字符），高亮聚焦应用并显示当前活动预设名称与可用数量。
  - **中轴分割线**：采用 `│` 垂直分割。
  - **右栏**：清晰区分 `── 预设方案 ──` 与 `── 独立零件 ──` 两个层级，支持展开零件变体。
- **平滑切栏 (`←` / `→`)**：左右方向键在应用列表与详情面板之间切换控制焦点；在右栏内部，`←` 可从零件变体折叠回插槽。
- **状态指示**：活动预设与已激活零件右侧均以绿色圆点 `●` 明确标识。
- **动态 Inspector 卡片**：按 `[Tab]` 在底部唤起所选预设或零件的文件组成与保留清单。

## 原位拓扑操作 (In-Place Interaction Flow)

所有操作均在 Studio 面板内完成，**零跳出控制台、零滚屏刷屏、不弹“按任意键继续”**：

- **`↑` / `↓`**（+ `k`/`j` / 滚轮 / `PageUp`/`PageDown`/`Home`/`End`）：在平铺树状列表中上下穿梭。
- **`[Enter]` / `[Space]`**：
  - 在 **App 行**：展开 / 折叠该 App，展开时光标自动滑入活动预设行。
  - 在 **预设行**：窄路径原子部署，底部直接原位显示绿字通知 `[✓] 已应用 kitty 预设: transparent`，`●` 标记瞬时刷新到位。
  - 在 **零件插槽行 (`part_slot`)**：展开 / 折叠该零件插槽，展开后列出可用零件变体选项。
  - 在 **零件选项行 (`part_variant`)**：原地热插拔零件目标文件，底部显示 `[✓] 已应用 niri 零件 [effects]: xray-blur`，`●` 标记瞬时刷新到位。
- **`[Tab]` / `[i]`**：展开 / 折叠分割线下方的包含文件与保留文件列表。
- **`→` / `l`**：展开当前聚焦的 App 或零件插槽，并将光标移动至子项。
- **`←` / `h`**：在零件选项行时跳回所属插槽；在零件插槽行时折叠该插槽或跳回所属 App；在预设行时返回所属 App 并折叠；在 App 行时折叠该 App。
- **`[s]` 保存 (Save)**：底部原位唤起轻量单行输入 `▸ 新预设名称: `，确认后自动创建用户预设并展开高亮。
- **`[e]` 编辑 (Edit)**：对选中的用户预设调起 `$EDITOR`，保存退出后原位返回当前面板。官方预设受保护提示不可直接修改。
- **`[d]` 删除 (Delete)**：对选中的用户预设弹出确认 `▸ 确认删除用户预设 'my-nord'？[y/N]: `，确认后即刻移除。官方预设受保护禁止删除。
- **`[q]` / `[Esc]`**：返回上一级菜单。

## 通用零件插槽支持 (Modular Parts Studio)

当应用在 `.module.toml` 中声明了 `[parts.<slot>]`（如 Niri 特效零件）：
1. **多组分流**：展开应用后分为 `── 预设方案 ──` 与 `── 独立零件 ──`，分割线不接收焦点，方向键会跳过它。
2. **多级折叠**：零件插槽（如 `▸ 零件 · 特效 (effects)`）像应用分支一样支持折叠/展开，展开后直观呈现变体清单。
3. **动态 Inspector**：光标移动到插槽或选项行时，底部卡片动态呈现目标文件（如 `~/.config/niri/effects_normal.kdl`）、说明、全部选项与激活状态。

## apply 后的窄 deploy 路径

切预设只跑该 app 的 `atomic_replace_item` + 模板渲染（`/home/user` 替换），**不走**
`deploy_selected_configs` 全流水线——不触发
`_phase_post_install_services`（fisher update / theme-sync / gtk 重渲染）。切个 kitty 预设
不该顺带跑 fisher，无关副作用违反"无熵"。详见 [preset-mechanism](preset-mechanism.md)。

## 光标保障

`sys.stdout.write(Colors.CURSOR_HIDE)` 进入循环，`finally: CURSOR_SHOW`——光标恢复由 trap
钩子绝对保障（崩溃也恢复），符合 TUI 宪章"光标恢复由 trap 钩子绝对保障"。

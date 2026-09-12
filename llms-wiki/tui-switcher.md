# TUI Preset Switcher — 树状折叠拓扑工作台、单一光标、原位无熵操作

> CLI（`nyxniri preset <app> apply <name>`）之外，交互菜单提供自包含的 Preset Studio 工作台。
> **单栏树状折叠拓扑（Accordion Tree）**，默认折叠，下方支持分行可折叠详情卡片。源码：`nyxniri/tui.py`（`PresetSwitcher`）。

## 布局与视线设计

```text
  NYX NIRI  v3.0.3  ·  预设管理

    ▸ fastfetch                 default
    ▸ fish                      default
  ▾ kitty
      default                   ●
    ❯ transparent
      nord
    ▸ niri                      default (2)
    ▸ noctalia                  default

  ────────────────────────────────────────────────────────────

  源: configs/kitty/presets/transparent

  ▸ 包含文件 (2)
  ▸ 保留文件 (0)

  [Enter] 展开/应用   [Tab] 详情   [s] 保存当前   [e] 编辑   [d] 删除   [q] 返回
```

### 展开详情视图（按 `Tab` / `i` 或鼠标点击）：
```text
  ────────────────────────────────────────────────────────────

  源: configs/kitty/presets/transparent

  ▾ 包含文件 (2):
      · current-theme.conf
      · kitty.conf

  ▾ 保留文件 (1):
      · monitor.kdl

  [Enter] 展开/应用   [Tab] 详情   [s] 保存当前   [e] 编辑   [d] 删除   [q] 返回
```

### 单一光标法则 (Single Cursor Rule)
- **全屏唯一光标**：`❯`（青色粗体）在整个屏幕中永远只有 1 个，在 App 行与展开的预设行之间平滑流转。
- **默认折叠**：所有应用默认折叠（`▸`），右侧灰色轻量展示当前活动预设名称与预设数量。
- **下方独立多行折叠**：包含文件与保留文件各占独立一行，支持按 `[Tab]`（或 `[i]` / 鼠标点击）展开与收起。
- **极致降噪状态指示**：去除冗余的 `[官方]` 标签，活动预设右侧以精致的绿色圆点 `●` 标识。
- **零错位盒状线**：废除 `┼`、`┴`、`│` 盒状字符，使用 56 字符定宽底部分隔线，完全免疫终端字符公差错位。

## 原位拓扑操作 (In-Place Interaction Flow)

所有操作均在 Studio 面板内完成，**零跳出控制台、零滚屏刷屏、不弹“按任意键继续”**：

- **`↑` / `↓`**（+ `k`/`j` / 滚轮 / `PageUp`/`PageDown`/`Home`/`End`）：在平铺树状列表中上下穿梭。
- **`[Enter]` / `[Space]`**：
  - 在 **App 行**：展开 / 折叠该 App，展开时光标自动滑入活动预设行。
  - 在 **预设行**：窄路径原子部署，底部直接原位显示绿字通知 `[✓] 已应用 kitty 预设: transparent`，`●` 标记瞬时刷新到位。
- **`[Tab]` / `[i]`**：展开 / 折叠分割线下方的包含文件与保留文件列表。
- **`→` / `l`**：展开当前聚焦的 App 并聚焦其预设。
- **`←` / `h`**：在预设行时返回所属 App 并折叠；在 App 行时折叠该 App。
- **`[s]` 保存 (Save)**：底部原位唤起轻量单行输入 `▸ 新预设名称: `，确认后自动创建用户预设并展开高亮。
- **`[e]` 编辑 (Edit)**：对选中的用户预设调起 `$EDITOR`，保存退出后原位返回当前面板。官方预设受保护提示不可直接修改。
- **`[d]` 删除 (Delete)**：对选中的用户预设弹出确认 `▸ 确认删除用户预设 'my-nord'？[y/N]: `，确认后即刻移除。官方预设受保护禁止删除。
- **`[q]` / `[Esc]`**：返回上一级菜单。

## apply 后的窄 deploy 路径

切预设只跑该 app 的 `atomic_replace_item` + 模板渲染（`/home/user` 替换），**不走**
`deploy_selected_configs` 全流水线——不触发
`_phase_post_install_services`（fisher update / theme-sync / gtk 重渲染）。切个 kitty 预设
不该顺带跑 fisher，无关副作用违反"无熵"。详见 [preset-mechanism](preset-mechanism.md)。

## 光标保障

`sys.stdout.write(Colors.CURSOR_HIDE)` 进入循环，`finally: CURSOR_SHOW`——光标恢复由 trap
钩子绝对保障（崩溃也恢复），符合 TUI 宪章"光标恢复由 trap 钩子绝对保障"。

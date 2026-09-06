# Noctalia 主题适配 (Theme Adaptation)

> 本目录是 NyxNiri 主题系统的物理归属，包含调度脚本、配置模板、
> hook 脚本和 GTK Material You 模板。本文档记录架构设计、遇到过的
> 所有问题及其解决方案，供未来维护参考。

---

## 1. 架构总览 (Architecture Overview)

应用要知道"现在是深还是浅"，有三条信息源，互不替代：

| 信号路径 | 机制 | 谁在用 | 时机 |
|---|---|---|---|
| Portal `color-scheme` | gsettings → xdg-desktop-portal → `AdwStyleManager` | Nautilus 等 GTK4/libadwaita | 实时（portal 信号） |
| `settings.ini` `prefer-dark-theme` | `theme-sync.sh` 写入 → `GtkSettings` 读取 | Brave 等 Chromium | 启动时读一次 |
| `gtk-theme-name` 切换 | gsettings `gtk-theme` → `adw-gtk3(-dark)` | GTK3 老应用 | 启动时 + gsettings 信号 |

此外还有 **gtk.css（M3 配色）**：由 Noctalia 渲染到 `~/.config/gtk-{3,4}.0/gtk.css`，
GTK3 热重载，GTK4 靠 `@media (prefers-color-scheme)` 实时切换。

---

## 2. 组件清单 (Components)

```
configs/noctalia/
├── README.md              ← 本文档
├── theme-sync.sh          ← 调度中枢（深浅切换时运行）
├── noctalia-config.toml   ← hook + user template 注册
├── wallpaper-hook.sh      ← 壁纸切换 hook（视频缩略图）
├── mpvpaper-sync.sh       ← mpvpaper 视频壁纸同步
└── templates/
    ├── gtk-3.0.css        ← GTK3 M3 模板（无条件 @define-color）
    └── gtk-4.0.css        ← GTK4 M3 模板（双 @media 块）
```

### theme-sync.sh — 调度中枢

`theme-sync.sh` 在深浅切换时运行，按 step 1-9 执行：

| Step | 职责 | 说明 |
|---|---|---|
| 1 | 可覆盖变量 | `NYXNIRI_GTK_THEME_DARK` 等环境变量 |
| 2 | 并发锁 | `flock` 防止快速 toggle 竞争 |
| 3 | `atomic_update_ini` | 原子写 INI，含 regex 特殊字符转义 |
| 4 | `set_system_theme` | gsettings / dconf 双路径降级 |
| 5 | 模式解析 | `toggle` / `dark` / `light` / hook 环境变量 |
| 6 | gsettings 广播 | `color-scheme` + `gtk-theme` 立即广播 |
| 7 | settings.ini 同步 | 写入 `gtk-{3,4}.0/settings.ini` |
| 8 | 热重载 | Kitty `SIGUSR1` + Kvantum |
| 9 | 交互反馈 | 终端运行时打印结果 |

### noctalia-config.toml — 注册中心

- **hook 注册**：`theme_mode_changed` → `theme-sync.sh`
- **hook 注册**：`wallpaper_changed` → `wallpaper-hook.sh`
- **user template 注册**：`nyxniri_gtk3` / `nyxniri_gtk4`
- `/home/user` 占位符由 `nyxniri.deploy` 在部署时替换为实际 `$HOME`

### templates/gtk-3.0.css — GTK3 M3 模板

无条件 `@define-color`。GTK3 不用 `@media`，靠 `gtk-theme-name` 在
`adw-gtk3` / `adw-gtk3-dark` 之间切换。换壁纸时 Noctalia 重新渲染，
GTK3 应用热重载 CSS。

### templates/gtk-4.0.css — GTK4 M3 模板

**双 `@media (prefers-color-scheme: dark/light)` 块**（核心设计，见 §4）。
同一个文件同时输出 dark 和 light 两套 M3 配色，由 GTK4 运行时根据
portal `color-scheme` 选择。

### wallpaper-hook.sh — 视频壁纸缩略图

`wallpaper_changed` hook。视频壁纸无法直接取色，用 `ffmpeg` 提取首帧
作为缩略图喂给 Noctalia 的 Material You 算法。

### mpvpaper-sync.sh — mpvpaper 同步

视频壁纸分配与主题联动，依赖 `jq` / `ffmpeg` / `inotifywait`。

### niri config.kdl 中的主题相关配置

`configs/niri/config.kdl` 的 `spawn-at-startup` 中有一项与主题相关：

- **`spawn-at-startup "bash" "-c" "sleep 8; ..."`**
  冷启动后 Noctalia 需要时间算壁纸调色板。8 秒后强制重新渲染 gtk.css，
  确保 Nautilus 等 GTK4 应用尽快加载到 M3 配色（而非 libadwaita 默认外观）。

---

## 3. 信号流图 (Signal Flow)

```
nyxniri theme toggle / dark / light
        │
        ▼
theme-sync.sh
        │
        ├─ step 6: gsettings color-scheme + gtk-theme  ← 立即广播
        │     │
        │     ├─ Brave (Chromium 114+): 读 portal color-scheme
        │     │    → 冷启动后需按钮唤醒（见 Problem 11），唤醒后实时跟随 ✅
        │     ├─ Firefox: 读 portal color-scheme → 秒跟 ✅
        │     ├─ Kitty: 不读 gsettings，靠 step 8 SIGUSR1 → 秒跟 ✅
        │     └─ Nautilus (GTK4/libadwaita): 读 portal → AdwStyleManager
        │          → @media CSS 重求值 → 即时切换 ✅
        │
        ├─ step 7: settings.ini 写入 (prefer-dark-theme + gtk-theme-name)
        │     └─ Brave (Chromium): 启动时读一次（冷启动兜底）
        │
        ├─ step 8: pkill SIGUSR1 kitty + Kvantum
        │
        └─ Noctalia 自动 (~6s)
              │
              └─ gtk.css 重渲染 (M3 配色)
                    ├─ GTK3: 热重载 CSS
                    └─ GTK4: @media 已在内存中，深浅即时切；
                             M3 配色值更新需重启
```

**关键**：
- gsettings/portal 信号是**立即**的，深浅模式（明暗）秒跟。
- gtk.css（M3 自定义颜色）由 Noctalia **~6s** 自动渲染。
- Nautilus 靠 `@media` CSS 即时切换深浅，M3 配色值更新需重启。

---

## 4. GTK4 @media 双块设计 (Dual-Block Design)

### 遇到的问题

`gtk-4.0.css` 原本用无条件 `@define-color` 写死颜色：

```css
@define-color window_bg_color  #131318;  /* dark 值，永远生效 */
```

libadwaita 的 `AdwStyleManager` 读 portal `color-scheme` 切深浅，但它自身
的 `libadwaita.css` 用 `@media (prefers-color-scheme)` 包裹颜色定义（159 个
`@media` 块）。我们的无条件 `@define-color` 覆盖了 libadwaita 的 `@media` 块：

- portal 说"现在是 light"
- `AdwStyleManager` 切了它自己的运行时状态
- 但 `window_bg_color` 仍是 `#131318`（dark）—— 因为无条件定义优先级高于 `@media`
- Nautilus 读 `window_bg_color` 画窗口背景 → 永远 dark

### 为什么不是 `prefer-dark-theme` 的锅

最初怀疑 `gtk-4.0/settings.ini` 的 `gtk-application-prefer-dark-theme` 干扰了
libadwaita。实机验证推翻了这个假设：

1. 删掉该 key 后 Nautilus **仍不跟**（视觉卡 dark）
2. 真正起作用的是把 `gtk.css` 改成 `@media` 双块
3. 该 key 只产生一条 `Adwaita-WARNING`（cosmetic，不影响功能）
4. 但 Brave 依赖该 key 检测暗色 → **不能删**

### 解决方案

把所有 M3 `@define-color` 和 widget 规则包进两个 `@media` 块：

```css
@media (prefers-color-scheme: dark) {
    @define-color window_bg_color  {{ colors.background.dark.hex }};
    /* widget rules with .dark. colors */
}

@media (prefers-color-scheme: light) {
    @define-color window_bg_color  {{ colors.background.light.hex }};
    /* widget rules with .light. colors */
}
```

Noctalia 模板引擎支持 `.dark.` / `.light.` 两种模式取色
（见 Noctalia 文档 `05_THEMING_PALETTES_AND_TEMPLATES.md` §3.2）。
一个文件同时输出两套配色，由 GTK4 运行时 `@media` 选择。

模式无关的部分留在 `@media` 外：
- 语义色（`warning_color`、`success_color` 等）
- GTK3 legacy 命名色（`theme_bg_color` 等，GTK4 不读）
- M3 调色板参照色（`STRAWBERRY`、`BLUEBERRY` 等）
- shade/shadow（`rgba(0,0,0,...)` 固定值）

---

## 5. settings.ini Key 保留决策

### 为什么留着 deprecated key

`gtk-application-prefer-dark-theme` 在 GTK4 标记为 deprecated，libadwaita
会打印 warning。但：

1. **Brave (Chromium 114+) 启动时通过 `GtkSettings` 读该 key 做冷启动兜底**
2. 删掉后 Brave 冷启动时可能无法正确检测暗色
3. warning 是 cosmetic，不影响 libadwaita 功能
4. libadwaita 靠 portal `color-scheme` + `@media` CSS，不依赖该 key

### 鲁棒性分析

- **key 被 GTK 移除** → 写入变 no-op，Brave 那条路失效，
  Nautilus 不受影响（单点失效不崩）
- **Brave 未来改读 portal** → key 变 no-op，留着重启无影响
- **两套机制独立**：Nautilus 走 `@media`，Brave 走 `settings.ini`，
  任一失效另一个不受影响

---

## 6. GTK Material You 模板移植 (Porting Notes)

`templates/gtk-{3,4}.0.css` 移植自 [HyprYou](https://github.com/hyprland-material-you)
的 `gtk3.scss` / `gtk4.scss`。不引入 dart-sass 依赖，直接把 SCSS 展平为纯 CSS +
Noctalia Jinja2 模板，Noctalia 在壁纸/明暗切换时自动渲染到
`~/.config/gtk-{3,4}.0/gtk.css`。

### 6.1 SCSS → Noctalia 模板转换规则

| SCSS 写法 | Noctalia 模板写法 | 说明 |
|---|---|---|
| `$primary` | `{{ colors.primary.default.hex }}` | 变量 → M3 token |
| `#{"" + $onSurface}` | `{{ colors.on_surface.default.hex }}` | 同上 |
| `color.mix($X, transparent, 38%)` | `rgba({{ colors.x.default.rgb_csv }}, 0.38)` | 与透明色混合 = 设 alpha，用 `rgb_csv` 输出 `r, g, b`，手写 `rgba()` |
| `color.mix(transparent, $X, 92%)` | `rgba({{ colors.x.default.rgb_csv }}, 0.08)` | 反向，alpha = 1 − N% |
| `color.mix($A, $B, 90%)` 两色混合 | CSS `color-mix(in srgb, A 90%, B)` 双行 fallback | 见 §6.3 |
| `&:hover { ... }` | `selector:hover { ... }` | 嵌套展平 |
| `@use` / `@at-root` / `// <post:...>` | 删除 | SCSS 专用指令 |

### 6.2 为什么零过滤器

Noctalia 文档只展示了 `blend` / `set_alpha` 接受**字面量**参数的用法，没有变量
参数。nyxmellow 模板（项目唯一已验证的 user template）**不用任何过滤器**，只用
`{{ colors.X.default.hex }}`。GTK 模板对标 nyxmellow 做到零过滤器：

- `set_alpha N` → `rgba({{ colors.X.default.rgb_csv }}, N)`（`rgb_csv` 是格式访问器，
  不是过滤器）
- `blend: colors.Y, N` → CSS `color-mix(in srgb, ...)` 双行 fallback

### 6.3 color-mix 双行 fallback

SCSS `color.mix($A, $B, N%)` = N% × A + (100−N)% × B，等价于 CSS
`color-mix(in srgb, A N%, B)`。GTK4 4.10+ 原生支持 `color-mix()`，GTK3 不支持，
用 CSS cascade 兜底：

```css
switch:hover {
    /* GTK3 fallback (flat token) */
    background-color: {{ colors.surface_container_highest.default.hex }};
    /* GTK4 (color-mix，cascade 覆盖上行) */
    background-color: color-mix(in srgb, {{ colors.surface_container_highest.default.hex }} 92%, {{ colors.on_surface.default.hex }});
}
```

GTK3 跳过第二行用 flat 色，GTK4 用第二行覆盖。`@define-color` 中的 `color-mix`
同理（GTK4 4.10+ 支持）；GTK3 `@define-color` 不支持，用近似 flat token。

### 6.4 @define-color 分层

文件里的 `@define-color` 块分三层，按顺序：

1. **GTK3 legacy → M3**（`theme_bg_color`、`theme_fg_color`…）：旧 GTK3 应用读
   这些名字，映射到 M3 token，换壁纸就跟着变。
2. **语义色**（`STRAWBERRY`、`BANANA`…）：硬编码，不跟壁纸。Nemo 等文件管理器
   用它们给文件类型标色。
3. **libadwaita → M3**（`accent_bg_color`、`window_bg_color`…）：libadwaita /
   adw-gtk3 读这些，映射到 M3 token。

### 6.5 决策记录

**保留**：
- 水果色（STRAWBERRY/BANANA/BLUEBERRY…）——语义色，不应跟壁纸变。
- `@define-color` 的 M3 映射块（`accent_bg_color → primary` 等）——libadwaita /
  adw-gtk3 接入 M3 的核心。
- GTK3 legacy named colors（`theme_bg_color` 等）——让不走 libadwaita 的旧 GTK3
  应用也跟随壁纸。

**删除**：
- `window.hypryou-dialog`（gtk4.scss:555-591）——HyprYou 专有弹窗 widget。
- Budgie named colors（`budgie_tasklist_indicator_color` 等）——NyxNiri 不用 Budgie。

**修正**：
- `through` → `trough`——原 SCSS progressbar 块里是拼写错误，GTK 的槽叫 `trough`。

### 6.6 部署与渲染流程

```
configs/noctalia/templates/gtk-3.0.css / gtk-4.0.css  (模板源)
  ↓ nyxniri deploy（atomic_replace_item，随 noctalia 目录部署）
~/.config/noctalia/templates/gtk-3.0.css / gtk-4.0.css
~/.config/noctalia/noctalia-config.toml  (/home/user → $HOME 替换)
  ↓ Noctalia 壁纸/明暗切换时自动渲染
~/.config/gtk-3.0/gtk.css
~/.config/gtk-4.0/gtk.css
```

`noctalia-config.toml` 注册（`/home/user` 占位符由部署引擎替换为 `$HOME`）：

```toml
[theme.templates.user.nyxniri_gtk3]
index = 3
input_path = "/home/user/.config/noctalia/templates/gtk-3.0.css"
output_path = "/home/user/.config/gtk-3.0/gtk.css"

[theme.templates.user.nyxniri_gtk4]
index = 4
input_path = "/home/user/.config/noctalia/templates/gtk-4.0.css"
output_path = "/home/user/.config/gtk-4.0/gtk.css"
```

模板部署后由 `nyxniri/modules/gtktheme.py` 的 `gtktheme_trigger_render()` 调用
`noctalia msg config-reload && noctalia msg templates-apply` 触发渲染；安装时
`nyxniri/deploy/deploy.py:_phase_post_install_services()` 自动调用，手动触发用 `nyxniri gtk install`。

### 6.7 theme-sync.sh 关系

`theme-sync.sh`（深浅切换时运行，见 §3 信号流）做两件与 GTK 相关的事：

1. **gsettings / INI**：设 `gtk-theme = adw-gtk3(-dark)` 与 `color-scheme`。
   adw-gtk3 提供布局，`gtk.css` 覆盖颜色——结构基底，不需要改。
2. **清理 legacy CSS**：删除含 `libadwaita.css` / `noctalia.css` / `iNiR theming`
   标记的 `gtk.css`。本目录模板生成的 CSS 不含这些标记，不会被误删（已确认）。

壁纸切换时 Noctalia 重新渲染 `gtk.css`，`theme-sync.sh` 不运行——不需要，
颜色更新由 Noctalia 模板引擎完成。

### 6.8 已知陷阱

- **`foreground` token 不可用**：Noctalia 模板引擎不暴露 `foreground`，虽然 palette
  JSON schema 有 `foreground` 字段，但 `{{ colors.foreground.default.hex }}` 会渲染
  失败。`window_fg_color` 必须用 `on_background` 替代（语义相同，M3 规范里
  `foreground` 就是 `onBackground` 的别名）。
- **`gtk-dark.css` 软链接覆盖 M3 配色**：`~/.config/gtk-{3,4}.0/gtk-dark.css` 若是
  指向 adw-gtk3 的软链接，内容是 `@import url('libadwaita.css')`，libadwaita.css
  定义 110 个 `@define-color`（硬编码灰），在 `gtk.css` **之后**加载会覆盖 M3 定义。
  必须删除该软链接，由 `theme-sync.sh` 清理逻辑与 `gtktheme.py:_clean_legacy_overrides()`
  双重保障。

### 6.9 Qt 自动跟随

niri `config.kdl` 设了 `QT_QPA_PLATFORMTHEME="gtk3"`，Qt 应用读 GTK 主题。GTK 有
M3 配色后，Qt 应用自动跟随，不需要 Kvantum（Kvantum 仅给走 Kvantum 引擎的 Qt 应用
用，二者独立）。

### 6.10 更新 HyprYou 上游

若 HyprYou 的 `gtk3.scss` / `gtk4.scss` 有更新：

1. diff 上游变更，判断是否需要同步。
2. 按 §6.1 转换规则表手动转换 SCSS → CSS + Jinja2。
3. `python3 -m unittest discover -s tests -q`。
4. `HOME=$(mktemp -d) ./install.sh test` 确认部署正常。
5. 实机换壁纸验证 GTK 应用跟随。

---

## 7. 问题与解决全记录 (Problem Log)

### Problem 1: `nyxniri theme toggle` 不广播 gsettings

- **症状**：toggle 后 Chrome/Edge/Brave/Kitty 深浅色不跟随
- **根因**：`toggle` 分支调用 `noctalia msg theme-mode-toggle` 后直接
  `exit 0`，跳过 `set_system_theme`、INI 同步、kitty reload
- **修复**：toggle 后 `sleep 0.3` → 读回新 mode → 继续跑完整 sync 流程
- **状态**：已解决

### Problem 2: `theme-sync.sh` step 8 有害（config-reload + templates-apply）

- **症状**：gtk.css 渲染错色（切 light 时仍为 dark 配色）+ 调色板更新延迟翻倍
- **根因**：hook 在 Noctalia 调色板重算**之前**触发，`templates-apply` 用旧
  调色板渲染。且 `config-reload` 会拖慢 Noctalia 调色板更新（从 ~6s 拖到
  12-20s）
- **修复**：移除 step 8。Noctalia 调色板更新后会自动渲染 user templates
  （实测 ~6s），无需手动触发
- **状态**：已解决

### Problem 3: GTK Material You 模板未部署

- **症状**：`templates-apply` 不碰 gtk.css
- **根因**：工作树的 `noctalia-config.toml` GTK 注册块 + `templates/` 目录
  从未通过 `nyxniri install config` 部署到实机。`templates-apply` 不碰
  gtk.css 是因为 toml 里没注册，不是缓存 bug
- **修复**：部署 toml + 模板目录，注册后 `templates-apply` 完全正常
  （0.023s 重渲染，无占位符残留）
- **状态**：已解决

### Problem 4: `atomic_update_ini` 未转义 regex 特殊字符

- **症状**：key 含 `.`、`[` 等 regex 特殊字符时 `[[ =~ ]]` 匹配失败
- **修复**：key 经 `sed 's/[][\.^$*+?(){}|/]/\\&/g'` 转义后再用于匹配
- **状态**：已解决

### Problem 5: Nautilus (GTK4/libadwaita) 深浅模式不跟随

- **症状**：切换 dark↔light 后，Nautilus 窗口一直保持 dark，重启才跟
- **误判过程**：
  1. 怀疑 `gtk-4.0/settings.ini` 的 `prefer-dark-theme` 干扰 libadwaita
  2. 删除该 key → Nautilus 仍不跟（视觉卡 dark）
  3. 但 Brave 不跟了（回归）
- **真根因**：`gtk-4.0.css` 用无条件 `@define-color` 写死 dark 颜色，
  覆盖了 libadwaita 自身的 `@media (prefers-color-scheme)` 块
- **修复**：`gtk-4.0.css` 重构为双 `@media (dark/light)` 块，
  用 Noctalia `.dark.` / `.light.` 取色
- **教训**：删 `prefer-dark-theme` 前未验证 Brave 依赖 → 回归。
  最终方案：保留 key（喂 Brave）+ `@media` CSS（喂 Nautilus），双保险
- **状态**：已解决

### Problem 6: Brave (Chromium) 深浅模式不跟随

- **症状**：删除 `prefer-dark-theme` 后 Brave 不跟随深浅切换；恢复 key 后
  Brave 只在启动时跟随，toggle 时不实时变色
- **根因**：Brave 通过 `GtkSettings` 读 `prefer-dark-theme` 检测暗色。
  `GtkSettings` 只在启动时读 `settings.ini`，运行中不监视文件变化。
  `settings.ini` 中的 `gtk-modules=colorreload-gtk-module` 不可靠
  （GTK3 不会自动读该 key 加载模块）
- **修复**：
  1. 恢复向 `gtk-4.0/settings.ini` 写入 `prefer-dark-theme`（启动时跟随）
  2. （未采用）曾考虑在 niri config `environment` 加
     `GTK_MODULES "colorreload-gtk-module"`，但反编译验证该模块只监视
     `~/.config/gtk-3.0/colors.css`，不读 `settings.ini`，对 Brave 无用，
     从未加入 config.kdl
- **状态**：部分解决。`prefer-dark-theme` 解决冷启动跟随（启动读对深浅）；
  toggle 实时跟随未解决，见 Problem 11

### Problem 7: Noctalia 调色板更新延迟 ~6 秒

- **症状**：模式切换后，gtk.css（M3 配色）约 6 秒后才更新
- **根因**：Noctalia 调色板重算本身需要时间（壁纸 Material You 算法），
  这是 Noctalia 固有速度，NyxNiri 侧无法再快
- **状态**：可接受。深浅模式立即跟，M3 颜色 6 秒跟

### Problem 8: `gtk uninstall` 不持久

- **根因**：GTK 模板注册写在源 `noctalia-config.toml`，每次 `nyxniri install`
  会重新部署并自动重渲染。`nyxniri gtk uninstall` 从已部署的 toml 删除注册
  并删 gtk.css，但下次 install 会完全恢复
- **对比**：fcitx/greeter 在安装时动态写入 toml，卸载是持久的
- **状态**：可接受。核心特性定位下不影响功能

### Problem 9: `gtk-3.0.css` 含 GTK4 专有属性 `transform`

- **症状**：Brave 报 `Theme parsing error: 'transform' is not a valid property`
- **根因**：从 HyprYou `gtk3.scss` 展平时没删干净，`transform` 是 GTK4 专有
- **修复**：删除 `gtk-3.0.css` 中 `scale.marks-after slider` 的
  `transform: none`。`gtk-4.0.css` 保留该属性（GTK4 需要）
- **状态**：已解决

### Problem 10: 重启后 Nautilus 延迟显示 M3 主题

- **症状**：重启电脑后 Nautilus 显示 libadwaita 默认外观（adw），过一会儿
  或手动 toggle 后才变成 M3 主题
- **根因**：冷启动时 Noctalia 需要时间算壁纸调色板，gtk.css 在渲染完成前
  不存在或为旧内容。Nautilus 启动时加载到空/旧 CSS → 显示默认外观。
  Noctalia 渲染完成后不会主动通知 Nautilus 重新加载 CSS
- **修复**：niri config 加 `spawn-at-startup "bash" "-c" "sleep 8;
  noctalia msg config-reload && noctalia msg templates-apply"`，
  冷启动 8 秒后强制重新渲染 gtk.css。但 Nautilus 仍需一次 toggle 或重启
  才能加载新 CSS（GTK4 不热重载 CSS 文件）
- **状态**：部分解决（gtk.css 更快就绪，但 Nautilus 仍需 toggle 触发 CSS 重载）

### Problem 11: Brave (Chromium) toggle 时不实时变色

- **症状**：`nyxniri theme toggle` 后 Nautilus 秒跟，但 Brave 不变色，需重启
- **调查**：
  - Chromium 114+ 官方用 XDG Desktop Portal `color-scheme` 检测暗色
    （[ArchWiki](https://wiki.archlinux.org/title/Chromium#Dark_mode) 确认），
    dissociated from GTK theme
  - `theme-sync.sh` step 6 已 `gsettings set color-scheme` → portal 广播
    `SettingChanged`，portal 值正确（`uint32 1` = dark）
  - NyxNiri 侧信号链路正确，问题在 Brave 自身
  - `colorreload-gtk-module`（`kde-gtk-config` 包）经反编译验证只监视
    `~/.config/gtk-3.0/colors.css`，不读 `settings.ini`，对 Brave 无用，
    从未加入 config.kdl
- **根因**：Brave 在非 GNOME 的 Wayland 复合器（如 Niri）上冷启动时，
  portal `SettingChanged` 信号订阅未正确初始化。这是 Brave/Chromium
  自身的冷启动 bug，不是 NyxNiri 的信号链路问题。
  实测直接 `gsettings set org.gnome.desktop.interface color-scheme`（绕开
  theme-sync.sh）Brave 亦不变色——gsettings 值正确变化、portal 信号确实
  发出，但 Brave 不处理；偶尔跟一次是 portal 订阅 race 命中，不可靠。
  v2.3.3 时代 Brave 版本能稳定处理 gsettings 信号（CHANGELOG 声称"实时
  跟随"属实），后续 Brave 更新引入 portal 订阅 race
- **按钮唤醒现象**：在 `brave://settings/appearance` 手动切换一次主题模式
  （如"经典"→"GTK"→"经典"），Brave 内部重新初始化 `NativeTheme` 观察者，
  portal 订阅被激活，此后 toggle 即可实时跟随
- **排障指引**：如果 Brave 不跟随 toggle，去 `brave://settings/appearance`
  切一次模式即可唤醒，无需重启 Brave
- **状态**：已确认 Brave upstream bug，NyxNiri 侧无法修复。方案 A
  （延迟广播）实机证伪；方案 B（CDP）因 `brave://` 禁 CDP 导航不可行；
  两全方案（toggle 跳过 gsettings 广播让 Noctalia hook 异步独占）实测
  gsettings 值正确变化但 Brave 仍不响应
- **方案 A 证伪的机制**：`gsettings set color-scheme` 重设**同值**时 dconf
  去重，不写 dconf → 不发 changed 信号 → portal 无 `SettingChanged` 可重
  广播。`dconf watch` 实测：单次 toggle 仅 1 次 color-scheme 写入（即时
  那次），0.5s 后延迟重设**零写入**；连发两次同值 `gsettings set` 也是 0
  次。延迟重广播对未变值是纯 no-op，Brave 收不到二次信号。
- **延迟重广播的 flock 逃逸竞态**：`( sleep 0.5; gsettings set ... ) &` 是
  分离子壳，不受 step 2 `flock` 约束。0.5s 内快速 toggle 到反模式时，旧
  模式的延迟子壳撞上已变更的值，触发真实写入并回退用户选择。实测
  （light→dark 连发）：`dconf watch` 捕获 4 次 `light, dark, light, dark`，
  后 2 次是 spurious 回退，Nautilus 闪烁、Brave 被多余信号干扰。
  PR #26 的延迟重广播 hunk 经此实测证伪，未合并。

### Problem 12: GTK4 标题栏最小化/最大化/关闭按钮显示成同心圆

- **症状**：Nautilus、GTK Demo 等 GTK4 应用标题栏右侧三个按钮显示成
  同心圆（一个外圆套一个内圆）
- **误判**：最初以为 `GtkWindowControls` 的按钮只带 `.minimize/.maximize/.close`、
  没有 `.image-button`，根因是 libadwaita 通用 `button` 规则上底色 +
  `button:not(.combo)` 掰成圆。按此修了 `windowcontrols button:not(.combo)`
  重置（特异性 `(0,1,2)`），实机**无变化**。
- **真根因**：`GtkButton` 在子部件是图标时**自动加 `.image-button`**
  （`gtkbutton.c: update_style_classes_from_child_type`，文档明说"the node
  will get .image-button if the content is just an image"）。`GtkWindowControls`
  的 minimize/maximize/close 按钮塞了一个 `GtkImage`、不带 `.flat` →
  自动获得 `.image-button`。GTK4 user CSS（`~/.config/gtk-4.0/gtk.css`，
  provider 优先级 `USER=800`）压过 libadwaita（`THEME`）—— 这点"同心圆
  能出现"本身就是证据：若 libadwaita 的
  `windowcontrols > button:...image-button { background: none }` 生效，
  按钮就透明、没外圆了。于是我们的 `.image-button` 规则给按钮
  `secondary_container` 底色 + `100%` 圆角 = **外圆**；libadwaita 给
  `windowcontrols > button > image` 加 `border-radius:100%` + 底色 = **内圆** →
  同心圆。
- **修复**：`gtk-4.0.css` 在 `@media` 块外加 `windowcontrols > button > image
  { background: none; border-radius: 0 }`，只清掉 libadwaita 给图标加的**内圆**
  （底色 + `border-radius:100%`），**保留**按钮本体的 `.image-button` 规则
  （`secondary_container` 底色 + `100%` 圆角 = 大圆 + `:hover`/`:active` 混色）。
  结果：窗口按钮变成标准的 M3 image-button（大圆 + 图标），与其它 image-button
  一致；图标颜色由已有的 `.image-button image { color: on_secondary_container }`
  给。user CSS（`USER=800`）压过 libadwaita（`THEME`），一条 base 规则即覆盖
  libadwaita 的 `:hover`/`:active` 内圆（provider 优先级先于特异性）。
- **代价**：失去 libadwaita 原生"图标内圈 hover/active 变深"反馈，改为大圆
  整体变色（与其它 image-button 一致）；窗口按钮从低调变显眼（实色大圆）；
  外观与 `.image-button` 规则耦合，将来改那条规则窗口按钮会跟着变。
- **只改 GTK4**：GTK3/adw-gtk3 的 titlebutton 没有 libadwaita"图标圆"设计，
  无此问题，`gtk-3.0.css` 不动
- **坑**：GTK4 不热重载 CSS 文件（见 Problem 10），改完 gtk.css 必须重启
  GTK4 应用才会生效
- **状态**：已解决

---

## 8. 旧文档的错误假设纠正

原 `notes/主题问题.md` 和 `主题问题总结.md` 的多个结论经实机验证是错误的：

| 旧结论 | 实机真相 |
|---|---|
| 模板已注册部署 | **从未部署**——工作树 toml 改动 + templates 目录从未 sync 到 `~/.config/` |
| `templates-apply` 有缓存/不可靠 | 注册后**完全正常**，0.023s 重渲染，无缓存问题 |
| Noctalia 不自动渲染 user templates | **会自动渲染**（调色板更新后 ~6s）|
| `config-reload` 卡 30s 网络超时 | 实测 0.045s，无超时 |
| `gtk-dark.css` 软链接是根因 | 无关（GTK4 下 gtk-theme-name 无效）|
| `.rgb_csv` 渲染风险 | 实机验证成功，0 个占位符残留 |
| `palette-export --format gtk-css` 子命令 | **不存在**（`unknown command`）。PR #20 的 GTK 方案依赖此子命令，不可行；其 GTK Material You 目标已被当前用户模板架构（nyxniri_gtk3/gtk4）取代，PR #20 已关闭 |
| `prefer-dark-theme` 是 Nautilus 不跟的根因 | 真根因是 `gtk-4.0.css` 无条件 `@define-color` 覆盖 libadwaita `@media` |

---

## 9. 排障速查 (Troubleshooting)

| 症状 | 检查点 |
|---|---|
| Nautilus 不跟深浅 | `gtk-4.0/gtk.css` 是否含 `@media` 块？`grep @media ~/.config/gtk-4.0/gtk.css` |
| Brave 启动时不跟深浅 | `gtk-4.0/settings.ini` 是否有 `gtk-application-prefer-dark-theme`？ |
| Brave toggle 时不实时变色 | 去 `brave://settings/appearance` 切一次模式唤醒（Brave 冷启动 bug，见 Problem 11） |
| 重启后 Nautilus 显示 adw（非 M3） | Noctalia 是否已渲染 gtk.css？等 ~8s 或手动 toggle 一次 |
| 所有应用都不跟 | `gsettings get org.gnome.desktop.interface color-scheme` 是否正确？`theme-sync.sh` 是否运行？ |
| gtk.css 不更新 | `noctalia-config.toml` 是否注册了 `theme.templates.user.nyxniri_gtk4`？ |
| gtk.css 渲染错色 | Noctalia 调色板是否已更新？（等 ~6s）`noctalia msg config-reload && noctalia msg templates-apply` |
| Brave 报 Theme parsing error | `gtk-3.0.css` 是否含 GTK4 专有属性？ |
| M3 颜色覆盖不了 | `gtk-dark.css` 软链接是否已删？`ls -la ~/.config/gtk-4.0/gtk-dark.css` |
| GTK4 标题栏按钮显示成同心圆 | `gtk-4.0/gtk.css` 是否含 `windowcontrols button` 重置？`grep windowcontrols ~/.config/gtk-4.0/gtk.css` |

---

## 10. 调试命令 (Debug Commands)

```bash
# 手动触发 Noctalia 渲染
noctalia msg config-reload && noctalia msg templates-apply

# 查看渲染结果（应有 @media 块 + 两套 window_bg_color）
grep "@media\|window_bg_color" ~/.config/gtk-4.0/gtk.css

# 查看当前 gsettings 信号源
gsettings get org.gnome.desktop.interface color-scheme
gsettings get org.gnome.desktop.interface gtk-theme

# 查看 portal color-scheme（uint32: 0=no pref, 1=dark, 2=light）
gdbus call --session --dest org.freedesktop.portal.Desktop \
  --object-path /org/freedesktop/portal/desktop \
  --method org.freedesktop.portal.Settings.ReadOne \
  "org.freedesktop.appearance" "color-scheme"

# 查看 Noctalia 模式
noctalia msg theme-mode-get

# 查看 AdwStyleManager 状态（需 Python + gi）
python3 -c "
import gi; gi.require_version('Adw', '1')
from gi.repository import Adw
sm = Adw.StyleManager.get_default()
print('dark:', sm.get_dark())
"

# 验证 toggle 是否真的触发 gsettings/portal 信号（dconf 同值去重检验）
# 一终端 watch，另一终端 toggle；看 color-scheme 写入次数
dconf watch /org/gnome/desktop/interface/

# 手动切换
nyxniri theme toggle
nyxniri theme dark
nyxniri theme light
```

---

## 11. 相关文件索引

| 文件 | 职责 |
|---|---|
| `configs/noctalia/theme-sync.sh` | 深浅切换调度中枢 |
| `configs/noctalia/noctalia-config.toml` | hook + user template 注册 |
| `configs/noctalia/templates/gtk-3.0.css` | GTK3 M3 模板 |
| `configs/noctalia/templates/gtk-4.0.css` | GTK4 M3 模板（双 @media） |
| `configs/noctalia/wallpaper-hook.sh` | 壁纸切换 hook |
| `configs/noctalia/mpvpaper-sync.sh` | mpvpaper 同步 |
| `nyxniri/modules/gtktheme.py` | `nyxniri gtk install\|status\|uninstall` |
| `nyxniri/cli.py` | `nyxniri theme` 子命令 |
| `nyxniri/deploy/deploy.py` | 部署 + 模板渲染触发 |

> 历史移植/排查笔记原在 `notes/`（本地开发笔记，不入库），内容已并入本文 §6 与 §7。

# 设置仪表盘：end4-pC 分析与复现要点

本文是「把 nyxuri 的设置仪表盘对齐 end4-pC」的分析结论与复现清单，重构前先读。
对象是 end4-pC 的 `modules/ii/settings/`，参照物是 nyxuri 的 `shell/modules/settings/dashboard/`。

参照树固定在 `~/.config/quickshell/end4-pC/modules/ii/settings/`（下称「上游」），
nyxuri 侧路径省略前缀 `shell/modules/settings/dashboard/`。

---

## 1. 结论先行：上游没有响应式

最重要的一条，先说清楚，因为它决定重构方向。

**上游的布局机制是固定几何，不存在响应式。** 证据：

| 位置 | 值 | 性质 |
|---|---|---|
| 上游 `Dashboard.qml` | `implicitWidth: 1100` / `implicitHeight: 680` / `minimumSize: Qt.size(900, 600)` | 硬编码，无缩放因子 |
| 上游 `DashboardContent.qml:283` | `anchors.margins: 16` | 硬编码 |
| 上游 `DashboardContent.qml:284` | `spacing: 12` | 硬编码 |
| 上游 `DashboardContent.qml:291` | 工具栏 `implicitHeight: 56` | 硬编码 |
| 上游 `DashboardContent.qml:522` | `columns: 4` | 硬编码，无断点 |
| 上游 `DashboardContent.qml:524` | `rowSpacing/columnSpacing: 12` | 硬编码 |
| 上游 `DashboardSettingsPage.qml:23` | `rowHeight: 140` / `headerHeight: 36` / `gap: 12` | 硬编码 |

全库没有任何按窗口宽高切换列数、间距或行高的分支。上游的「尺寸联动」只发生在
**窗口内**：`ColumnLayout` + `GridLayout` 让卡片随窗口拉伸，卡片内部用
`Layout.fillWidth/fillHeight` 吸收剩余空间。窗口被拖到 900×600 时，卡片一起变小，
内容不重排；更小则直接被 `minimumSize` 挡住。

**这与本次任务书里的「确保各界面在不同屏幕尺寸下显示正常且布局合理」是冲突的。**

两条路，必须选一条：

- **A. 严格 1:1**：接受固定 1100×680 与硬编码 4 列。优点是像素级还原上游观感；
  代价是 1080p 上占屏 57%、4K 上占屏 29%，且与「不同屏幕尺寸下布局合理」互斥。
- **B. 固定几何 + 最小适配层**（推荐）：骨架、间距、圆角、动效全部照抄上游常量，
  只在外层加一层「等比缩放 + 窄屏降列」：窗口 ≤ 某宽度时 `columns: 4 → 2`，
  卡片行高按窗口高度插值。视觉在标称尺寸下与上游一致，尺寸变化时不破版。

下面第 2–5 节描述的是**上游原貌**，即 A 与 B 共用的复现目标；第 6 节列出两者分歧。

---

## 2. 窗口与外壳

上游 `Dashboard.qml`（49 行）是薄壳：

- `Scope { active: settingsOpen && style === "dashboard" }` 内挂 `Loader`
- `FloatingWindow`：`1100×680`、`minimumSize 900×600`、`color` 交给 `DashboardContent` 自己画
- `settled` 门控：`onWidthChanged/onHeightChanged` 重启 70ms `Timer`，`settled` 为真后才
  建 `DashboardContent`。目的是让卡片入场动画发生在窗口几何稳定之后，否则首帧会跳。
- 没有 `screen` 绑定、没有标题栏、没有拖动处理器 —— 移动完全交给合成器。

nyxuri 侧差异：`Dashboard.qml` 直接是 `FloatingWindow`（而非 Scope+Loader）＋ 自带
圆角背景＋`CompositorBlurRegion`＋尺寸持久化。这是必要的偏差，`SettingsBackend`
要 `registerWindow` / `showWindow` / `hideWindow` / `openPage` 一套协议。

---

## 3. 配色注入（「听歌时好看」的全部机制）

上游是三段式，全在 `DashboardContent.qml:30-96` 与 `DashboardMediaState.qml`：

1. **取色**：`DashboardMediaState` 把 `player.trackArtUrl` 下载到
   `Directories.coverArt/<md5>`，`ColorQuantizer` 量化出主色，
   `mix(colors[0], colPrimaryContainer, 0.8)` 得到 `artDominantColor`。
2. **派生方案**：`AdaptedMaterialScheme { color: artDominantColor }`（27 行纯 QML）
   用 `mix` + `adaptToAccent` 把主题色与封面色按比例混出 14 个色键。
   `adaptToAccent(base, accent)` 是关键：**保留 base 的明度与 alpha，只取 accent 的
   色相与饱和度**，所以 accent 家族的文字对比度不会随封面崩掉。
3. **注入**：`mediaColors = mediaVisible ? blendedColors : Appearance.colors`；
   `ui` 对象把 11 个语义名（surface / toolbar / fgSurface / subtext / hover / accent /
   accentHover / accentActive / fgAccent / container / fgContainer）映射到上面两者之一。
   页面、工具栏、导航、搜索框、头像全部读 `ui.*`，不读 `Appearance.colors`。

另外两层背景（`DashboardContent.qml:255-281`）：
隐藏的 `dashboardArtSource`（封面原图）→ `FastBlur radius 64` → 一个
`blendedColors.colLayer0` 的 0.6 透明度遮罩。模糊单独不够：亮封面糊开还是亮，
文字会消失，必须有遮罩压一层。

`mediaVisible` 同时看 `currentPage` 与 `pendingPage`，因为翻页动画期间两页并存，
只判 `currentPage` 会让整个表面在交叉淡入时闪一次颜色。

nyxuri 现状：已按此实现。`CoverScheme.qml` = `AdaptedMaterialScheme`，
`DashboardMediaState.qml` = 取色适配层（委托给已有的 `MediaPalette`，不重复实现下载与量化），
`DashboardContent.ui` + `mediaColors` + 背景三层齐备。

---

## 4. 布局机制

### 4.1 外壳三层

```
ColumnLayout(margins 16, spacing 12)
├─ Item(implicitHeight 56)          ← 工具栏行
│  ├─ 左：发行版胶囊（44 高，圆角 height/2，2px 主色描边）
│  ├─ 中：Toolbar 导航（5 个 RippleButton，38 高，圆角 height/2）
│  └─ 右：RowLayout(spacing 10) = 搜索胶囊 + 通知 + 头像
└─ Loader（当前页，Layout.fillWidth/fillHeight）
```

搜索胶囊展开：`implicitWidth: searchOpen ? 280 : 44`，220ms `OutCubic`。
导航按钮里**只有选中项显示文字**（`visible: navBtn.toggled`），未选中是纯图标，
所以 Toolbar 宽度会随选中项变化 —— 这是上游刻意的，不是 bug。

### 4.2 卡片网格（占位页）

`GridLayout columns: 4`，只服务「尚未实现」的页；五个真实页各自 `Loader` 覆盖。
`layouts` 是每页的 span 表，`buildPage()` 按 span 生成占位卡，
随机 `travelX/travelY`（±250/±200）用于入场方向。

### 4.3 设置页的装箱器（`DashboardSettingsPage.qml`）

自适应之外的算法：`computeLayout()` 把「标题行 + 卡片」切成 item，
标题占满整行并重置 floor，卡片按 span 塞进第一个空位；
`packRows()` 按 span 分 full/wide/small 桶，按桶顺序填行。
`rowHeight 140`、`headerHeight 36`、`gap 12` 是行高基准。

**span 表（上游 `DashboardSettingsPage.qml:32-41`）：**

| type | span |
|---|---|
| style / schemes / barpos / shape / iconpicker | [2, 2] |
| weathermap | [4, 2] |
| barlayout | [4, 3] |
| palette | [4, 1] |
| toggle / spin | [1, 1] |
| 其余 | [2, 1] |

### 4.4 入场动效

卡片进场：`scale 0.25 → 1`、`opacity 0 → 1`，`animIndex * staggerMs`（45ms）错峰，
位移从 `travelX/travelY` 归零。翻页时 `pageExitRequested` 让当前页按同序飞出。
切页定时器 `320 + n * (staggerMs - 4)` ms，即等待飞出 + 飞入跑完。

---

## 5. 交互逻辑

键位（`DashboardContent.qml:101-148`，全部在上游，nyxuri 已移植基础部分）：

| 键 | 行为 |
|---|---|
| `Esc` | 预设页二级视图先返回，否则关窗 |
| `←/→` | 媒体页：上一首/下一首；其余页：网格方向选择 |
| `Space`/`Enter` | 媒体页：播放暂停；其余页：激活选中卡 |
| `Ctrl+F` | 开关搜索 |
| `Tab`/`Shift+Tab` | 下一页/上一页 |
| 可打印字符 | 直接进搜索框（type-to-search） |
| `/` | 设置页打开搜索 |
| `PgUp/PgDn` `↑/↓` | 设置页滚动 420/120 |
| `L` | 壁纸页锁定 |

`moveSelection(dx, dy)` 用「轴向投影 + 垂直距离」选最近邻，不是简单行列索引，
所以跨 span 的卡片也能正确跳转。

搜索：设置页按 token 匹配，命中项参与打分；`isSearchablePage` 决定哪些页接受输入。

---

## 6. 尚缺的部分（复现清单）

按「上游有、nyxuri 无」列出。括号内是上游行数。

### 6.1 组件（设置页专用瓦片）

| 组件 | 用途 | 行数 |
|---|---|---|
| `DashboardStyleCard` | 面板样式选择（按钮＋实时预览） | 140 |
| `DashboardSchemeCard` | matugen 方案画廊（含 `DashboardSwatchDot`） | 358 |
| `DashboardPaletteCard` | 自定义调色板编辑 | 176 |
| `DashboardSwatchCard` | 单色块编辑（含 `DashboardSwatchDot`） | 77 |
| `DashboardIconCard` | 图标主题选择 | 103 |
| `DashboardShapeCard` | MaterialShape 选择 | 104 |
| `DashboardDurationCard` | 动画时长滑块 | 172 |
| `DashboardBarLayoutCard` | 状态栏部件拖拽排布（含 `DashboardBarWidgets`） | 492 |
| `DashboardBarPositionCard` | 状态栏位置/对齐 | 152 |
| `DashboardWeatherMapCard` | 天气地图（上游自身也是重件） | 107 |
| `DashboardPresetsPage` + `DashboardPresetDetail` | 预设画廊与详情 | 717 + 501 |

nyxuri 用 `DashboardThemesPage.qml`（435 行）替代 Presets 页 —— 但 nyxuri 没有预设系统，
所以这不是「缺」，是「换」；重构时须明确是保留换法还是补预设机制。

### 6.2 机制

1. **`heroEntries`**（上游 `DashboardSettingsPage.qml:44-51`）：置顶精选瓦片，
   不参与分区装箱。`hero: true` 的条目走独立行。
2. **`isVisibleEntry`**（上游同文件 83-87）：
   - `when: "material"` → 已选 matugen 方案时隐藏
   - `when: "hyprland"` → 非 hyprland 合成器隐藏
   - `requires: <widget>` → 依赖的状态栏部件未启用时隐藏
   nyxuri 完全无此门控，等于把合成器/依赖相关的设置项无条件暴露。
3. **搜索打分**：上游 `matches()` 有 `scored` 排序，nyxuri 只做包含过滤。

### 6.3 与 nyxuri 契约的冲突项

- 上游目录键是 `Config.options` 的嵌套点路径（如 `desktop:Blur wall`），
  nyxuri 是扁平属性＋显式 setter（`SettingsControlCatalog`）。**这一层不要照抄**，
  照抄就是引入上游的配置 schema，与 `two-axis-config.md` 冲突。
- 上游 `DashboardWeatherMapCard` 依赖天气地图后端，nyxuri 的
  `AGENTS.md` 红线 2 把「复杂天气地图」列为封存项。**不要复现**。
- `DashboardPresetsPage` 依赖上游预设机制，nyxuri 无（见 `preset-mechanism.md`）。

---

## 7. 复现顺序建议

先做骨架一致性，再补组件，最后补机制。每步独立可验证。

1. **几何对齐**：把上游常量（margins 16 / spacing 12 / toolbar 56 / 胶囊 44 / 导航 38 /
   搜索 44→280 / rowHeight 140 / headerHeight 36 / gap 12 / span 表）在 nyxuri 侧
   逐项对齐，并决定第 1 节的 A/B 路线。
2. **配色对齐**：已完成（`CoverScheme` + `DashboardMediaState` + `ui` + 背景三层）。
   待补：`DashboardSchemeCard` / `DashboardPaletteCard` 等取色类瓦片。
3. **机制补齐**：`heroEntries` → `isVisibleEntry` → 搜索打分。后者改动小、收益直接。
4. **组件补齐**：按 6.1 表从简到繁（Swatch → Icon/Shape → Style/Duration →
   BarPosition → BarLayout → Scheme/Palette）。
5. **不建议复现**：WeatherMap、Presets（除非先引入预设机制）。

---

## 9. 复现进度（本轮）

已按 **A 路线（严格 1:1，固定几何）** 推进。

### 已完成

| 项 | 上游 | nyxuri 改前 | 现状 |
|---|---|---|---|
| 仪表盘窗口尺寸 | `1100x680`，`color: colLayer0` 平面窗 | 自适应缩放 + 圆角 + 合成器模糊 | 已改为 `1100x680` + `colLayer0`，去掉自绘圆角与模糊区域 |
| 非仪表盘设置窗口 | `PanelWindow` 浮层 `980x665`（minimal ×0.75） | 自绘缩放 | 尺寸已改为 `980x665 × styleScale`；**仍是 FloatingWindow，未转 PanelWindow** |
| `rowHeight/headerHeight/gap` | `140 / 36 / 12` | 按窗口尺寸插值 | 已还原为常量 |
| 栅格列数 | 固定 `4` | `width < 720 ? 2 : 4` | 已还原为 `4` |
| 区块标题 | `colPrimaryContainer` 胶囊（32 高，内容 +22，图标 18 + 标题） | 裸图标 22 + titleLarge 文字 | 已改为上游胶囊写法 |
| `packRows` 收尾 | 末行剩余宽度右到左摊到卡片上 | 无 | 已补上 `leftover` 分发 |
| 滑块 tile 跨度 | `[2, 1]`（`slider` 走默认分支） | `[2, 2]` | 已还原 `[2, 1]` |

滑块高度是唯一的等价替代：上游 `StyledSlider` 只有一条轨道那么高，nyxuri 的
`MaterialSlider` 是 78px 的控件，塞不进 140 的格子，因此 tile 里固定用 48px。

### 未完成（下一步）

1. `heroEntries`：上游置顶精选瓦片，nyxuri 无。
2. `isVisibleEntry`：按合成器 / 依赖开关隐藏条目，nyxuri 无（等于无条件暴露）。
3. 搜索打分：上游 `matches()` 有 `scored` 排序，nyxuri 只做包含过滤。
4. 6.1 表的 11 个瓦片 + `DashboardPresetsPage` / `DashboardPresetDetail`。
5. `ControlCenterWindow` 由 `FloatingWindow` 转 `PanelWindow`（上游是 layer-shell 浮层）。
6. 窗口持久化已按用户要求移除（不再记忆手调尺寸）。

### 已明确不做

- 窗口位置 / 尺寸 / 是否浮动：交给合成器（niri）。仓库侧只在
  `configs/niri/rules.kdl` 提供 `org.quickshell → open-floating true`。
- 不自绘圆角、不加合成器模糊区域 —— 与上游一致，圆角由 niri 的
  `geometry-corner-radius` 提供。


---

## 10. 复现进度（第二轮：瓦片补齐）

### 10.1 已落地：`DashboardStyleCard`（上游 140 行）

上游 `DashboardStyleCard` 是「设置面板」三档选择器（默认 / 极简 / 仪表盘），
span `[2,2]`。本轮按第 7 节顺序把它作为第一块瓦片落地。

**与上游的结构差异（一处，刻意的）：** 上游把选项数组
`{value, name, detail, icon, shape}` 硬编码在卡内，与 `Config.options.settings.style`
并存，于是标签有两份真值。nyxuri 侧改成：value 与 label 取自
`SettingsControlCatalog`（同一批已持有 getter/setter 的对象），卡内只保留
「按 value 索引的装饰」（图标、字形、一行说明）。这样瓦片与 shell 其它部分写入的
值不可能漂移。

新增/改动文件：

| 文件 | 改动 |
|---|---|
| `modules/settings/dashboard/DashboardStyleCard.qml` | 新增（186 行） |
| `modules/settings/dashboard/qmldir` | 注册 `DashboardStyleCard` |
| `modules/settings/dashboard/DashboardSettingsCatalog.qml` | `interface:Settings panel style` 由 `select` 卡改为 `style` 卡，去掉 `w: 4`（改由 span 表给 `[2,2]`） |
| `modules/settings/dashboard/DashboardSettingsPage.qml` | `baseSpan()` 增加 `style → [2,2]`；新增 `styleComponent`；把 Loader 的 type→component 嵌套三元链换成显式 `tileFor` 表（上游那条链每个卡型长一级缩进，后面还有 8 个瓦片要接） |
| `assets/i18n/zh_CN.toml` | 补 `Compact overlay panel` / `Floating window with cards` / `Full overlay panel` 三键（i18n 契约要求代码引用的键必须存在） |

### 10.2 本轮踩到的两个坑（下次直接照做）

1. **`lint-qml.sh` 默认只检查 changed 范围。** 首次运行时既有文件 0 告警、
   新文件 30 条 `not found on type "QObject"`，看起来像新文件有问题。跑
   `lint-qml.sh --all` 才知道该告警遍布全库（ToggleCard 16 / MediaPage 19 /
   MaterialSlider 60），根因是 `Appearance.colors` 声明为弱类型 `property QtObject`，
   qmllint 无法静态解析其成员。**属既有噪声，不是回归。**
2. ~~**i18n 改动必须重建 + 重启进程。**~~ **（2026-10-05 作废）**
   这条是纯 QML 迁移前的写法。`f31179e` 已切到`shared/i18n/I18n.qml` +
   `Translations.js` 内存字典，`shell/native/` 目录（`plugin/i18n/CMakeLists.txt`、
   `i18n_manager.cpp`、`libClavisI18n.so`）**已不存在**，`.qm` / `rcc` 那条链
   整条消失。现在的规则是：改 TOML 后热重载即可；只有改了 `I18n.qml` /
   `Translations.js` 本身才需要重启进程。

### 10.3 视觉验证回路（替代 qsmcp）

本机没有 `qsmcp` / `qs_preview`，改用合成器原生能力：

```bash
# 1. 让仪表盘切到 settings 页并置顶
qs ipc --path ~/dev/Nyxuri/shell call settings open settings
niri msg action focus-window --id "$(niri msg --json windows | python3 -c '...')"

# 2. 读浮窗几何，按区域截图（不要全屏，避免带入无关窗口）
niri msg --json windows | ...   # layout.tile_pos_in_workspace_view + window_size
grim -g "401,146 1100x680" shot.png
```

注意：`tile_pos_in_workspace_view` 是 **workspace 视图**坐标，窗口不在当前
活动 workspace 时照此截图会截到别的窗口 —— 需先 `focus-workspace <idx>`。

纯静态验证（无副作用，推荐每次都跑）：
```bash
QT_QPA_PLATFORM=offscreen QML_IMPORT_PATH=build/shell-test/qml \
  timeout 20s qs -p shell -n     # 已启动实例时会拒绝，改在实例停机时跑
```

### 10.4 本轮验证结果

| 项 | 结果 |
|---|---|
| `lint-qml.sh` | passed（本次触碰的 3 个文件 0 告警；其余为第 10.2 条既有噪声） |
| `python3 -m unittest discover -s tests -q` | Ran 517, failures=4 —— 与基线一致，未新增 |
| `audit-lifecycle.py` | clean (8 files) |
| `generate-tree-inventory.py` | 674 entries，已重生成 |
| `format-qml.sh` 口径 | 本次触碰文件 qmlformat 零差异；`check.sh` 仍红，因上一轮遗留的 11 个文件未格式化（见 §10.5） |
| 运行时 | 重建 i18n 插件后重启实例，`IPC_READY`，Home/Settings 页渲染正常 |
| 视觉 | 与上游对照截图逐项吻合（见 §10.6） |

### 10.5 遗留：`check.sh` 目前是红的

`check: qml-format failed`。

> **（2026-10-05 修正）** 本文初稿写的是「11 个文件未格式化」，那是当时用
> `format-qml.sh` 无参数（changed 范围）得到的结论，**是错的**。
> 跑 `format-qml.sh --check-all` 的真实结果是 **92 个文件**未格式化，
> 覆盖 `app/` `modules/` `shared/` 各域，差一个量级。
>
> 这意味着 qmlformat 从未被全量应用过——`--check-all` 会报出大量「既有文件
> 与qmlformat 输出不一致」，包括一些从未被本次重构触碰的模块。
>
> **不要在仪表盘这条线上顺手格式化。** 92 个文件的机械格式化会把
> 「仪表盘重构」的 diff 完全冲淡，且跨 6 个功能域，属于独立 commit 的工作。
> 需要时：`shell/scripts/dev/format-qml.sh --all`（作用于全库），
> 单独成commit，不要与功能改动混在一起。
>
> 与本轮触碰链直接相关的未格式化文件（4 个）：
> ```
> app/AppShell.qml
> app/Paths.qml
> modules/settings/dashboard/DashboardContent.qml
> modules/settings/dashboard/SettingsControlCatalog.qml
> ```

### 10.6 与上游的剩余视觉差异（对照截图逐项核过）

「设置面板」StyleCard 全部锚点一致：卡外形与底、头部 Gem 图标与配色、标题与副标题
层级、三子卡等宽排布、图标字形（Cookie9 / Clover4 / SoftBurst）、图标底色反转、
名称字号字重、detail 小号灰字、选中态整卡主色 + 白底勾选圆、未选中空心圆。

仅一处文案差异：

| 位置 | 上游 | nyxuri |
|---|---|---|
| 副标题 | 选择设置窗口的打开方式 | 选择设置的打开方式 |

来源是 nyxuri `zh_CN.toml:254` 的既有译文，不是本次新增。改它只需一行，但会牵动
所有引用 `Choose how settings open` 的位置，故未擅自动。

### 10.7 下一步

1. 按 §10.1 同一形状继续轻量瓦片：`DashboardSwatchDot` → `DashboardSwatchCard`
   → `DashboardIconCard` → `DashboardShapeCard` → `DashboardDurationCard`。
2. 再上重瓦片：`DashboardSchemeCard` + `DashboardPaletteCard`（对应「配置方案 /
   调色板风格」两块），`DashboardBarPositionCard`，`DashboardBarLayoutCard`。
3. `heroEntries` 必须**等 style / schemes / palette 三块瓦片就位后**再挂：
   现在挂上去，这三项会解析成空卡片（`tileFor` 查不到对应组件），属未接线。
4. `isVisibleEntry`（`when: "material"` / `requires:`）与搜索打分尚未做。

---

## 11. 复现进度（第三轮：几何层逐项验收）

**目标：几何 1:1，行为按需。** 功能继续走 nyxuri 自己的
`PersonalizationConfig` / `ThemeService` / `MatugenTemplateService`，不移植上游
那套依赖 `Config.options` 嵌套点路径 + `ColorSchemes` 单例的瓦片。

### 11.1 逐项核对结果：几何已全部对齐

| 项 | 上游 | nyxuri | 状态 |
|---|---|---|---|
| 窗口尺寸 | `1100×680` | `1100×680` | 对齐 |
| 窗口下界 | `minimumSize: Qt.size(900, 600)` | **无** | **本轮补上** |
| 窗口底色 | `colLayer0` | `colLayer0` | 对齐 |
| 外壳边距 / 间距 | `16` / `12` | `16` / `12` | 对齐 |
| 工具栏行高 | `56` | `56` | 对齐 |
| 发行版胶囊 | 高 44 · `radius h/2` · border 2 · 宽 `内容+28` · spacing 8 | 同 | 对齐 |
| 导航按钮 | 高 38 · `radius h/2` · padding 14 · icon/文字 spacing 6 | 同 | 对齐 |
| 搜索胶囊 | 高 44 · 宽 44↔280 · 220ms OutCubic · `radius h/2` | 同 | 对齐 |
| 头像 | `44×44` · `radius w/2` | 同 | 对齐 |
| 栅格列数 / 间距 | `4` / 12 / 12 | `4` / 12 / 12 | 对齐 |
| `rowHeight/headerHeight/gap` | `140 / 36 / 12` | `140 / 36 / 12` | 对齐 |
| 标题胶囊 | 高 32 · 宽 `内容+22` · icon 18 · spacing 8 | 同 | 对齐 |
| 瓦片内边距 | 通用 14；Style/Palette 主12 | 同 | 对齐 |
| 卡片基类 | `animScale 0.25` · spring 2.6/0.32 · 220 OutQuad · 260 InBack · 280 InQuad · `staggerMs-4` | 同 | 对齐 |

**唯一差异是 `minimumSize`**，已补。理由写进代码注释：整套布局是固定几何，
低于 900×600 时 4 列装不下最大 span 的卡片，开始裁切。

### 11.2 差异的性质：不再是「视觉差距」，是「瓦片种数」

几何对齐后，剩下的差异全部落在**组件种数**上，不落在视觉：

| 组件 | 上游行数 | nyxuri | 裁决 |
|---|---|---|---|
| `BarLayoutCard` + `BarPositionCard` + `BarWidgets` | 492+152+87 | 无 | **砍** —依赖 `bar.layouts.{left,middle,right}Layout` 三段布局模型，nyxuri 无此模型，移植是假功能 |
| `WeatherMapCard` | 107 | 无 | **砍** — 复杂天气地图已在 `shell/AGENTS.md` 红线 2 封存 |
| `PresetsPage` + `PresetDetail` | 717+501 | `DashboardThemesPage` | **换** — 已有主题页承担同一职责，不重复实现 |
| — | — | `DashboardLyricsPane` | nyxuri 独有（上游无歌词面板） |
| `SwatchDot` / `SwatchCard` | 39 / 77 | 无 | 待补（零依赖，先补这两张） |
| `IconCard` / `ShapeCard` / `DurationCard` | 103 / 104 / 172 | 无 | 待补（数据模型兼容） |
| `SchemeCard` | 358 | 无 | 待补，但须适配 `ThemeService`，不照搬 `ColorSchemes` |

**12 项缺失 → 砍 5、换 1、待补 6。**

### 11.3 下一步（按依赖顺序，不是按行数）

1. `SwatchDot`（39 行，零依赖）→ `SwatchCard` 依赖它，**必须先补**，
   否则后面颜色类瓦片各自重复实现一遍色点。
2. `IconCard` / `ShapeCard` / `DurationCard` —— 三张都是纯 card，只依赖
   `control.get/set` 与形状枚举。
3. `SchemeCard` —— 需先定数据适配层：`ColorSchemes.schemeOptions()` /
   `currentAccent()` / `setAccent()` 三个API 要映射到
   `ThemeService` / `MatugenTemplateService`。**这是本轮唯一需要设计决策的补齐项**，
   先写清映射关系再动代码。
4. `isVisibleEntry` + 搜索打分 —— 纯机制，不依赖新瓦片，可与上面并行。
5. `heroEntries` 仍然**不挂**：style 与palette 已在位，但 `hero:schemes` 依赖
   SchemeCard，挂上去会解析成空卡片。

### 11.4 与 skill 的分工

`~/.workbuddy/skills/dashboard-settings-panel/` 是**自包含的通用规格书**，
面向「从零新建」与「移植裁决」。本文是**本项目的验收记录与裁决台账**，
记录「为什么不做某些上游组件」——判据比规格活得久，两者不要合并。

---



---

## 8. 验证口径

```bash
cd /home/xibie/dev/Nyxuri
shell/scripts/dev/lint-qml.sh                     # 期望 lint-qml: passed
python3 -m unittest discover -s tests -q          # 基线 4 个失败，不得新增
shell/scripts/dev/audit-lifecycle.py              # 期望 clean
python3 shell/scripts/dev/generate-tree-inventory.py   # 新增 QML 后必须重生成
```

新增 QML 会改变 `tree-inventory.md` 的计数，**不要手改，必须用生成器**。

# 设计契约与抄件宪章 (Design System)

> 本页是全 Shell 表面的设计契约唯一权威：字号、圆角、间距、色彩角色、动效、交互反馈、
> 出生律，以及从参考树借件的方法论（抄件宪章）。数值基准 1:1 取自
> `references/caelestia/plugin/src/Caelestia/Config/tokens.hpp`（= Material 3 官方 dp 值）。
> 实施状态：契约值已钉；**字号一张表（D-1）与状态层合一均已落地（2026-11-21）**
> （门禁 `tests/shell/test_type_scale.py` 与 `tests/shell/test_d1_design_unification.py`）；
> 剩余清账见本页末节。运行行为以源码为准，本页管「应该是什么」；
> 阶段与验收归 ROADMAP。

## 抄件宪章（怎么抄）

缝合感的来源不是「抄了多棵树」，而是**同一层认了两个爹**。正确抄法 = 分层认亲，
每层只有一个监护人；表面可以有不同母体，但必须共认更低的层。

### 分层认亲

| 层 | 内容 | 唯一母体 | 其它树的角色 |
| --- | --- | --- | --- |
| L1 设计宪法 | 字号/圆角/间距/色彩角色/动效数值 | **caelestia**（M3 官方数值） | 任何树的原件进库先换血成本页 token |
| L2 交互语言 | 状态层/ripple/hover 生长/形态 morph | **caelestia 语义**（hover 8%/press 10%）+ **end4 的 bar 密度语法**（26↔54 槽位展开） | iNiR/dux 只借参数（如 150ms 防误触） |
| L3 组件原子 | 按钮/滑杆/开关/行/卡/弹层/tooltip | **caelestia nexus 套件**为正典（T3 已入，6 域服役） | **同类禁止第二实现**；表面特有类（胶囊/槽位/岛面）除外 |
| L4 表面骨架 | 窗口/面板/布局壳 | 分表面认亲：bar=end4 · settings=caelestia · launcher=orbit 自研 · 数据壳=iNiR | omarchy=宿主架构（已收口） |
| L5 数据服务 | niri 面/投影 | iNiR + 自研 | 用户不可见，与统一无关 |

### 抄件四问（任何新组件需求必走）

1. 这是哪一层的哪一类组件？
2. 正典库里已有同类原子吗？→ 有：直接用或扩展，**禁止再抄第二个同类**。
3. 没有 → 去该表面在 L4 认的母体树物理 `cp` 原件 → 剪裁依赖 → **换血** → 再做 Nyxuri 特有修改。
4. 母体树也没有 → 直接在本契约上自研（吃同一套 token 与交互语言长出来的组件自动是亲生的）。

### 换血纪律（Fork & Trim 四步）

物理 cp 原件 → 剪裁依赖 → **换血到 L1/L2**（重接 token 与交互语言，剥除母体私有
字号/颜色/圆角/间距/hover 语义）→ Nyxuri 特有修改。第三步是强制步骤，跳过即产生缝合。

### 冲突裁决顺序

宪法（L1/L2）> 表面母体（L4）> 组件原籍习惯。抄来的东西永远不携带母体私有值。

## Type Scale（全库一张表，D-1 定案，已落地）

唯一定义点 = `shell/commons/NexusStyle.qml`（D-1 时自 ui/ 迁入 Token 归宿 commons）；
`pixelSize` 直接收 dp 值（96dpi 下 dp=px）。Typography 单例与 `Appearance.font`
的 end4 字号阶梯已双双退役删除；全库字面 `pixelSize` 清零。

| 阶 | 档 | px | weight |
| --- | --- | --- | --- |
| Label | small | 11 | Regular (400) |
| Label | medium | 12 | Medium (500) |
| Label | large | 14 | Medium (500) |
| Body | small | 12 | Regular (400) |
| Body | medium | 14 | Regular (400) |
| Body | large | 16 | Regular (400) |
| Title | small | 14 | Medium (500) |
| Title | medium | 16 | Medium (500) |
| Title | large | 22 | Medium (500) |
| Headline | small | 24 | Medium (500) |
| Headline | medium | 28 | Medium (500) |
| Headline | large | 32 | Medium (500) |
| Display | small/medium/large | 36/45/57 | Regular（M3 规格档；caelestia 未消费，锁屏/时钟大数字用） |
| Mono | small/medium/large | 12/14/16 | Regular |
| Icon | small/medium/large/extraLarge | 20/24/32/48 | Material Symbols |

退役映射（2026-11-21 定案，按最近值原则、平值向下）：

- **Typography → NexusStyle**：同名恒等（M3 命名一致），文件删除。
- **end4 `Appearance.font.pixelSize` → NexusStyle**：`smallest 10→labelSmall 11 ·
  smaller 12→bodySmall · smallie 13→bodySmall · small 15→bodyMedium 14 ·
  normal 16→bodyLarge · large 17→bodyLarge · larger 19→icon.small 20（消费点全部是
  glyph 槽位 iconSize）· huge/title 22→titleLarge`；阶梯删除（family 字符串保留）。
- **字面值 → token**：文字按最近值（平值向下，如 13→12、15→14、18/19→16、20→22）；
  Material Symbols 家族的 glyph 文本走 icon 档；`Fonts.mono` 家族走 mono 档。
  bar 图标槽几何（19/17px iconSize）按 B-2/D-1 保留 end4 基线，不属字号。

正文主力 = `body.small`（UI 默认文字）；bar 密度表面以 Label 档起步。字族不内嵌、
跟随系统回退（红线：不为视觉引入内嵌字体或启动下载）；时钟/工作区数字字族保留
现有可配键。全局字号缩放轴（`fontScale` 乘算）保留为用户配置。

## 圆角（9 档 + 三个固定惯例）

`extraSmall 4 · small 8 · medium 12 · large 16 · largeIncreased 20 · extraLarge 28 ·
extraLargeIncreased 32 · extraExtraLarge 48 · full(=圆形)`。

固定惯例：**面板/弹层/大卡片 = extraLarge(28)**；**按钮圆角 morph：default=large(16)、
checked=medium(12)、pressed=small(8)**；**圆形元素（头像/开关/滑块手柄/搜索条）= full**。
列表容器 ConnectedRect：首尾 extraLarge(28)、中间 extraSmall(4)。bar 胶囊
`fullRadius=height/2` 为 end4 表面特例，保留。

## 间距（8 档，两个职责）

`extraSmall 4 · small 8 · medium 12 · large 16 · largeIncreased 20 · extraLarge 28 ·
extraLargeIncreased 32 · extraExtraLarge 48`。容器内边距用 padding、元素间隙用
spacing，同阶梯不同职。

## 色彩角色（MCUT 全集 + 消费惯例）

角色命名与 material-color-utilities 的 `SchemeWithPalettes` JSON 完全一致
（caelestia `services/Colours.qml:230-305` 为全集清单）：调色板键色 ×5、中性/表面系
（`surfaceContainerLowest/Low/基础/High/Highest` 阶梯、`onSurface/onSurfaceVariant`、
`outline/outlineVariant`、`inverseSurface/inverseOnSurface`、`surfaceDim/Bright`）、
primary/secondary/tertiary 各容器系与 fixed 系、error 系；`success` 系为登记扩展。

消费惯例（契约，违反即缝合）：

- **填充**：primary/secondary（含 on* 前景）；强调容器用 tertiaryContainer。
- **分层**：surfaceContainer 五级阶梯——弹层底首选基础档，菜单 `surfaceContainerLow`。
- **描线**：outline / outlineVariant。
- **文字**：onSurface（主）、onSurfaceVariant（次）。
- **状态层**：hover 8% · focus 10% · press 10% · drag 16%（M3 标准；onSurface 墨色浸染，
  **绝不全不透明填充**）。bar 的 end4 hover 语义（mix 8%）与本条等价，统一归此口径。
- **单色源纪律**：全库颜色只经色彩角色出口，字面色值零残留；颜色变化统一走动画。

## 动效

时长档：small 200 / normal 400 / large 600 / extraLarge 1000 ms；效果系 150/200/300；
expressive 空间系 350/500/650。曲线：M3 emphasized（进出减速）/standard 家族。
bar 的 end4 `elementMove*` 家族（200/320/400）映射入上述档位。出生律的生长动画
归 expressive 空间系（锚边生长 500ms 弹性，keystone 基准）。

## 出生律（联动的感知法律）

每个弹层/面板/抽屉必须过四条，机制可选、法律不豁免：

1. **有原点**：声明从哪生长（哪个槽位/图标/边）。
2. **有生长**：开合为生长/缩回动画（统一曲线族）；禁止凭空 fade-in 新矩形。
3. **材质连续**：打开时继承源胶囊的色/圆角/边框规格，闭合时归还。
4. **机制按最便宜够用选型**：窗内生长（已在同窗）→ 跨窗锚定几何+同文法（不同窗但
   看起来长出来）→ 同窗共生+SDF 融合（重武器，clavis `long_split.frag.qsb` 纯 QML
   ShaderEffect，D3 试点暂时放弃，恢复验证前不启用）。

## 表面来源映射表（Fork & Trim）

| 表面 | 母体 | 状态 |
| --- | --- | --- |
| settings（nexus） | caelestia nexus | T3 已抄，M3/M4 收尾 |
| bar 视觉/几何 | end4-pC | B 卷基线 |
| bar 数据面/托盘 | iNiR | B9.1 已抄 |
| 字号/圆角/间距/色彩/动效数值 | caelestia tokens.hpp | 本页即契约 |
| 联动机制库 | caelestia drawers（同窗架构）+ clavis keystone（全屏窗+mask+SDF） | D3 试点（暂时放弃） |
| quicksettings / sidebar | caelestia sidebar/popouts + iNiR | **D5 定母体** |
| lock / session | 候选 caelestia lock/session | **D5 定母体** |
| launcher | orbit 自研（保留） | 吃宪法与出生律 |
| OSD / 通知 | end4 岛 OSD / 既有通知链 | D5 过堂 |

## 不移植清单

- caelestia **blob C++ 形状系统**与 transparency layer 调色系统（含 tPalette 透明度分层）；
  以同色矩形 + blur + 纯 QML SDF ShaderEffect 近似（D-5 澄清：禁的是 C++，不是液态融合）。
- dux 的 Go 后端、matugen 全量联动、插件市场与 lock、Frame、哥特切角、多合成器修补层。
- caelestia per-monitor 配置层（多屏真实需求出现再议，见 delayed-decisions）。

## 清账清单（D0/D5 输入）

- ~~**字号四套并存**~~ **已清（2026-11-21，D-1 落地）**：NexusStyle 升格 commons
  全库唯一 type scale；Typography 与 `Appearance.font` 阶梯删除；字面 `pixelSize`
  275 处全迁移（映射见 Type Scale 节）；门禁 `tests/shell/test_type_scale.py`。
- ~~**两份 StateLayer**~~ **已清（2026-11-21，随 D1）**：bar 私有 end4 枚举版与
  StateOverlay 退役，`ui/StateLayer.qml` 补 `dragged` 态为唯一正典；
  `RippleButton.colBackgroundToggledHover/Toggled` 死属性激活、
  `hoverOpacity` 默认链直取本页 8%/10%/10%/16%；门禁
  `tests/shell/test_d1_design_unification.py`。
- **tooltip 双套**（`M3ToolTip`/`PopupToolTip`）合一（D5）。
- **ui/ 单域控件归位**：quicksettings 专用群（QuickToggle* 等 15 个）、dock 的
  `AttachedEdgeCurve`、lock 的 `PlayPauseButton`/`RippleEffect`、settings 的
  ThinReadOnlySlider 群——归唯一消费单元或升格真共享，二选一。

## 验收方式

- 契约测试逐值钉死（type scale/圆角/间距/状态层透明度）；
- 字面 `pixelSize` 与散落色值扫描门禁零残留；
- 同类组件全库一个正典（发现第二实现即合并或处决）；
- 逐表面过七条检查表：单色源 · 单几何源 · 单字号 · 单交互反馈 · 物理同窗（豁免，
  由出生律替代）· 单数据面 · **出生律**。

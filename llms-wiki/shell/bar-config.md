# Bar 自定义引擎契约 (D4)

> 本页是 bar 自定义引擎（D4 五期）的架构契约：配置 schema、默认值回退、最小化写入、
> 版本化迁移、部件注册表与属性注入协议。分期交付与验收归
> [shell/ROADMAP](../../shell/ROADMAP.md) D 卷；D4a/D4b/D4c/D4d 于 2026-11-22 落地，
> 后续期次在此页增量补节。运行行为以源码与契约测试（`tests/shell/test_d4a_bar_config.py`、
> `tests/shell/test_d4b_bar_config.py`、`tests/shell/test_d4c_bar_config.py`、
> `tests/shell/test_d4d_bar_config.py`）为准。

## 铁原则

所有可调轴的默认值来自 [design-system](design-system.md) 契约；自定义引擎不另立默认
审美。用户调整是宪法之上的表达自由，高自定义与统一性不冲突。

## barConfigs schema（D4a）

存储真相是 `[[bar.configs]]` 数组（`config.toml`），**单条起步、多 bar 就绪**
（D4e 解锁多实例）。每条 bar：

```toml
[[bar.configs]]
id = "default"
name = "Bar"

[bar.configs.lanes]
left = ["launcherButton", "workspaces"]           # 字符串条目
middle = [{ id = "island" }]                       # 对象条目（可带状态）
right = ["tray", { id = "clock", enabled = false }]  # 混排
```

- **lane 条目两种形态**：`"clock"` 字符串（= 默认态）或 `{id, enabled, ...overrides}`
  对象（= 有偏离默认的状态）。解析后统一为内存条目
  `{widgetId, uid, enabled, overrides}`。
- **lane 缺失 = 默认 lane；显式空 lane = 空**（最小化写入只省略等于默认的 lane）。
  这是 D4a 实现时踩过并写进 probe 的坑：缺失回退成空会把全新配置变成空 bar。
- **uid 是会话身份**，永不持久化：`widgetId@zone序号`，跨 bar 唯一，用于逐条目变更
  （enabled 开关、D4b 每实例轴）不误伤同类条目。
- **单例部件**（island）：全 bar 至多一条，normalize 期去重（岛占通知宿主，第二条
  会偷 islandHost）；其余部件允许同类型多实例（spacer/时钟可重复）。

bar 级几何/样式轴已随 D4c 迁入 configs 条目（见「bar 级轴（D4c）」节）。

## 三层默认值回退 + 单一取值入口（D4a）

`services/BarWidgetDefaults.js` 的 `option(widgetId, entry, key)` 是唯一取值入口：

```
entry.overrides[key] → DEFAULTS[widgetId][key] → GLOBAL_DEFAULTS[key]
```

**部件代码从不直接碰存储**：宿主（BarContent 单宿主，D4g 起横竖两向共用）把 lane 条目经
**属性注入协议**推进部件——声明 `property var widgetEntry` 的部件在 Loader
`onLoaded` 时收到条目对象，自身轴经 `option()` 解析。首个消费者是 Spacer
（`size` 轴）；D4b 随每部件实例配置逐个迁移存量扁平轴读取。

派生视图（`PersonalizationConfig`）：`barLayout*`（id 字符串视图，含禁用）、
`barLayoutEntries*`（条目视图，UI 消费）、`barLayoutEnabledIds(zone)`（enabled-only
id 视图，Config 桥对 vendor 供应这个——禁用部件不算「在场」）。

## 最小化写入（D4a，范围 `[bar]` 段）

`toJson()` 的 `[bar]` 段是 diff-against-defaults 的稀疏对象：

- 全默认 `[bar]` **整段消失**（不是空表头）；
- 改一个轴只落一个键；fresh-boot 空段由 probe 钉死（`d4aPersistence`）；
- 条目无偏离坍缩回字符串；override 键等于类型默认时自我删除；
- 段级写入仍是整段重建（与其他段一致）：段内手改未知键会丢——与 D4a 前行为等价。

其他段（wallpaper/theme…）暂保持全量写；全文件最小化另立清账。

## configVersion 版本链（D4a）

- 文件双处带版本：`# nyxuri-config-schema: N` 头戳（ConfigService 快路径探针，
  2 与 3 都走快路径）+ 顶层真实键 `configVersion`。
- `services/ConfigMigrations.js` 逐级迁移：每步收 parsed、原地改造、幂等、保留
  非自有键；v2→v3 把 legacy 布局键折叠进 `[[bar.configs]]`，**显式键名映射表**
  `LEGACY_LAYOUT_KEYS`（dux `MIGRATED_GLOBALS` 模式——改键名必须改表）。
- 迁移种子复用纯函数 `resolveBarLayouts`（one-shot 岛种子、legacy `island.enabled`
  闸门、leading/trailing 双区映射）；迁移后 `configVersionDirty` 触发一次落盘。
- 升级零感知由 probe 断言：v2 文件迁移后 legacy 键剥除、别名归一（`divisor`→
  `separator` 等）、幂等（二次运行零变更）。

## 部件注册表：加部件 = 固定三处（D4a）

| 登记 | 文件 | 职责 |
| --- | --- | --- |
| 1 | `services/BarWidgetDefaults.js` | `IDS` 白名单 + `DEFAULTS` 默认值 + `LEGACY_ID_ALIASES` + `SINGLETON_IDS`（存储侧校验与回退源） |
| 2 | `ui/BarWidgetCatalog.qml` | id → label/icon（跨表面共享展示目录；label 惰性翻译，见 DashboardBarWidgets 前例） |
| 3 | `plugins/bar/BarWidgetFiles.js` | id → 组件文件（实例化映射；未知 id 落空并 warn，大小写兜底已处决） |

- 三处 id 集合相等由 `test_d4a_bar_config.py` 契约钉死；**D4b 起第四注册点**（设置页
  options 映射，见下节）由 `test_d4b_bar_config.py` 钉死。
- 旧三份分散目录已归一退役：`PersonalizationConfig.barComponentOptions`、
  `ui/DashboardBarWidgets.qml`、BarContent/VerticalBarContent 内联 url map。
- 形状预留三方部件：注册表是纯数据，未来三方 id → file:// URL 直接可挂。

## id 命名与别名（D4a）

`divisor` 更名 `separator`（对齐 dux 键名，D4b/D4e 整抄设置页免翻译）；新增
`spacer` 一等部件（`Spacer.qml`，默认尺寸 = design-system 间距 largeIncreased=20）。
legacy 别名在 load/normalize 期归一：`clockWidget→clock`、`sysTray→tray`、
`resources→systemMonitor`、`batteryIndicator→battery`、`divider/divisor→separator`、
`dynamicIsland→island`。`barWidgetStyles` 里存的旧 widget 名同样归一。

## 设置面（D4a 不重建）

- `BarComponentsCard` 三 lane 卡消费条目视图 + 共享目录；chip 有显隐开关
  （visibility 图标，禁用态 0.45 透明度保持几何）；可用池允许重复添加
  （spacer 类）；拖拽身份是 uid（重复 id 的 chip 各自独立隐藏/移动）。
- `LayoutDragCoordinator.dropped(uid, id, zone, index)`：uid 非空 = 移动既有条目
  （保 enabled/overrides），空 = 池内新增。
- Dashboard 布局卡走 `setBarLayouts` id 替换 API（该编辑器不感知 per-entry 状态，
  属有意边界）；`setBarLayouts` 语义 = 整段替换（禁用/覆盖状态重置）。

## bar 级轴（D4c）

bar 级几何/样式轴以 **configs 条目平键**存储（id/name/lanes 之外的一切键），正典表 =
`services/BarDefaults.js`（对齐 BarWidgetDefaults 的注册点模式）。**哨兵原则**：
几何轴默认 `-1`/`"default"`/`1.0`，解析时落回 per-style 硬编码基线（B 卷 end4 验收值，
由 BarDefaults 的 baseline 函数承载）——默认配置零视觉变化、零写入，显式值只覆写一项。

- 轴表：`spacing`/`innerPadding`/`widgetPadding`（哨兵 −1 = per-style 基线）、
  `sideMarginPercent`（每侧边距 % 屏宽，0 = 通栏；吃掉 dux barLengthMode 三键）、
  `squareCorners` + `radius`（bar 壳圆角：显式值 > 方角 > 主题 screenRounding）、
  `fontScale`（乘算 NexusStyle type scale）、`surfaceColor`/`surfaceTransparency`、
  `border×4`（bar 面）、`widgetTransparency` + `widgetOutline×4`（部件层）、
  行为键 position/autoHide/screenList（D4e 多 bar 前置）。
- **解析出口唯一**：`PersonalizationConfig.resolvedBarSpacing/InnerPadding/WidgetPadding/
  ShellRadius`（消费面零哨兵分支）；样式上下文 `barStyleContext` 单点。
- **融合角**：`plugins/bar/SegmentRoles.js`（dux 原件整抄）算 lane 级 run 角色
  （solo/first/middle/last），宿主经活跃分支 Repeater 的 `hasContent` 供 participation
  ——隐藏部件（无曲目的 Media）重排邻居圆角、spacer/separator 断 run；BarGroup 以
  `segmentRole` 取代 totalCount/currentIndex。
- **flat 第五档**：borderless 词表加 `flat`（无胶囊几何的裸部件；`transparent` 保留
  「胶囊几何 + 透明填充」语义）。逐部件背景 = 右键弹层样式随条目走（见下）。
- **字体缩放**：`plugins/bar/BarScale.qml` 单例（qmldir 登记）乘算 bar 表面全部
  type-scale 读取（115 处绑定 `* BarScale.font`，权值枚举不缩放）；settings 页与
  双表面卡（dashboard 天气/资源卡）永不缩放。
- **v5 迁移**：`MIGRATED_BAR_GLOBALS` 显式键名映射（v4 的 [bar] 扁平框轴 → 条目，
  跳默认、幂等）+ `barWidgetStyles`（per-(mode,widget)）折叠进**当前 borderless 档**
  的条目 overrides（per-mode 维度随 D4c 退役，样式跟实例走）；头戳升 5，快路径收 2–5。
- **明确不迁（登记边界）**：`iconScale`（bar 图标槽是 97 处 end4 字面基线，归 D4e
  密度预设——dux maximizeWidgetIcons 同族）；`shadow×5`（dux 阴影长在其 Frame 翼形
  窗口基建上，今日窗口内画必裁切，随 D4e 窗口增长基建回归）；island 时钟数字与
  quickpanel 子目录不参与 fontScale（隐式单例解析不可达 + display 档几何）。

## 行为与溢出（D4d）

行为轴与溢出系统，2026-11-22 落地。**默认全部 = D4d 前现行行为**，唯一例外：
`hoverPopoutDelay` 默认 150ms（D4d-1 拍板对齐 D2 intent 语义；旧 400ms 是
StyledPopup 硬编码，不是被认可的默认）。全部新键、无改名——**无 configVersion
迁移**（版本链停在 5）。

### 轴表（`BarDefaults.DEFAULTS` 增量）

| 轴 | 默认 | 语义 |
| --- | --- | --- |
| `autoHideDelay` | 0 | 离开宽限（hide grace）：指针离开后延迟收起，0=立即（现行） |
| `autoHideStrict` | false | 严格模式：**只解除弹层类锚定**（右键菜单/媒体弹层不再钉住 bar）；sidebar/快捷面板类保持锚定（几何上从 bar 生长，藏了断锚）——D4d-2 拍板 |
| `hideOnFullscreen` | false | 输出上有全屏 toplevel 时抬 Overlay 层并入 autoHide 通道（边缘条揭示）；默认关=现行 Top 层被全屏覆盖 |
| `clickThrough` | false | 输入掩码缩到三条 lane 矩形：空隙点击穿透到窗口；边缘滚轴/ScrollHint 在此模式下失效（登记边界） |
| `hoverPopouts` | true | 部件弹层 hover 打开（吸收退役的 tooltips 硬编码；false=点击打开） |
| `hoverPopoutDelay` | 150 | 弹层 intent 时长（D2 同源 150ms） |
| `left/middle/rightOverflowMode` | "auto" | 每 lane 溢出默认（词表 auto/bar），是逐部件 `section` 模式的回退值 |

条目轴（overrides 自由键，无需注册）：`overflowMode("section"/auto/bar/always)`、
`overflowPriority(数，低者先让位)`。

### 溢出系统（dux `OverflowLayout.js` + `CenterLayout.js` verbatim 整抄）

- **解算器**：两个 JS 原样入库（头注 Fork & Trim；契约测试钉 verbatim）。核心
  `resolve(sections, options, previous)`：flexible 先收缩（shrink-to-fit）再按
  priority 让位、`always` 直接入溢出、pinned（spacer/separator/island）永不离开、
  迟滞恢复（restoreMargin + previous 状态）。lane 名 middle↔center 在宿主边界映射。
- **引擎**（BarContent 单宿主，D4g 起横竖两向共用）：活跃分支 Repeater 测量 →
  `resolve()`（1ms Timer 防抖——**禁 Qt.callLater**：初始绑定求值排入的 callLater
  会在孵化完成前触发，引擎方法尚未挂载，probe 实证崩溃）→ 隐藏集回写
  `BarGroup.inOverflow`（融合角经 SegmentRoles 参与度自动重排）+ flexible 配给
  （`allottedPrimarySize`）。
- **测量协议**（BarGroup）：`overflowEntrySize/Min` 从部件本体读（组自身 implicit
  在溢出后塌 0，不能喂解算器）；flexible 部件暴露 `naturalPrimarySize`/
  `minimumPrimarySize`（现仅 Media：natural=未钳制行宽、min=minWidth 轴）。
  dux `placement()/priority()` 读**顶层**键，宿主测量时把 overrides 摊平传入。
- **迁居协议**：部件 Loader 在「lane 组 ↔ 溢出弹层」间 re-parent，**实例永不销毁**
  （状态保留、服务租约不断）。`BarGroup.widgetLoader` 在完成期一次性捕获——
  children 绑定会在迁居瞬间判 null（恢复变 no-op、部件随弹窗销毁，probe 实证）。
- **溢出按钮**（`LaneOverflowHost.qml`，dux SectionOverflow 换血）：BarGroup 胶囊
  chevron（`expanderIcon` 随 bar 边转向），按钮位用 dux 默认（right/bottom lane 首、
  余者尾=面向屏中心内侧）；弹层复用 StyledPopup（D4d-3 拍板，`pinnedOpen` 显式开
  路径）。**关闭必先迁回再灭活**——弹窗树随 LazyLoader 销毁。溢出弹层无滚动
  （隐藏集按构造很小，登记边界）。
- **按钮插入位不暴露设置**（登记边界，用 dux 默认）。

### 全屏检测

`NiriDriver._enrichWindow` 透传 `is_fullscreen`；`fullscreenToplevelOnScreen(output)`
经 `CompositorDriver` 门面（单一状态源原则）。Bar.qml 据此切 `WlrLayer.Overlay`。

### clickThrough × autoHide 组合

移植 dux `gapEnterSuppressed`/`inEdgeStrip`/`revealSettle` 语义：隐藏态掩码=边缘
条，揭示须真抵达边缘条（带宽 15%、最小 8px）；掩码随滑入动画扩张会制造伪 enter，
隐藏在 settle 窗口（600ms）内顺延。

### hoverPopouts 换绑

六消费者（clock/resources/battery/networkspeed/weather/media）从退役硬编码换到
`!PersonalizationConfig.barAxes.hoverPopouts`；StyledPopup `hoverOpenDelay` 吃轴。

## 每部件实例轴（D4b）
D4b 把 per-widget 轴从 `[bar]` 扁平键迁到 lane 条目 overrides，交付部件实例编辑页。
**每个默认值 = D4b 前的现行行为**：迁移键照搬原值，新轴默认现视觉——引擎不另立审美。

### 轴表（`BarWidgetDefaults.DEFAULTS`）

| 部件 | 轴（默认值） |
| --- | --- |
| spacer | size(20) |
| separator | style(rect)/spacing(4) |
| clock | showDate(true)/dateFormat("")/click·middle·rightAction(none)/clickCommand([]) |
| workspaces | showAppIcons(false)/alwaysShowNumbers(true)/indicatorStyle(dot)/style(default)/numberStyle(normal)/shown(10)/activeColorMode(theme)+activeCustomColor/occupiedColorMode(theme)+occupiedCustomColor |
| systemMonitor | cpu(true)/cpuTemp(false)/ram(true)/disk(false)/swap(false)/iconStyle(outline)/showValue(false) |
| utilButtons = quickSettings | screenSnip(true)/colorPicker(true)/keyboardToggle(false)/micToggle(false)/wallpaperToggle(false)/darkModeToggle(true)/performanceProfile(false) |
| tray | tintIcons(true)/hidePassive(true)/showItemId(false) |
| battery | showPercent(true)/showPower(false)/click 三键(none)/clickCommand([]) |
| media | minWidth(160)/maxWidth(300)/showTitle(true)/scrollAction(none) |
| activeWindow | maxWidth(280)/click 三键(none)/clickCommand([]) |
| weather / launcherButton / powerButton | click 三键(default = 内建行为)/clickCommand([]) |

- `quickSettings` 与 `utilButtons` 是同一组件（`BarWidgetFiles` 同映射
  `UtilButtons.qml`），**表按引用共享**（`DEFAULTS.quickSettings = DEFAULTS.utilButtons`）。
- workspaces 状态色只作用于默认皮肤（四皮肤里只有它承载状态色语义）；
  `numberStyle` 的 han/roman 字形数组是 `BarWidgetDefaults.workspaceNumberMap()` 纯函数。

### 点击与滚轮协议

- 词表 `plugins/bar/BarWidgetActions.qml`（单例，qmldir 登记）：
  `default/none/dashboard/quicksettings/launcher/overview/power-menu/lock/command`。
  `default` 返回 false（部件落回内建行为）；`command` 执行**argv 数组**经
  `ActionGateway.execute(args, "bar-widget:<id>")`——不存 shell 字符串、不 `sh -c`
  （shell/AGENTS.md 红线）；设置页输入按空白拆分、不支持引号（登记边界）。
- 消费形状：`BarWidgetActions.dispatchMouse(widgetId, entry, button)` 一行接入；
  L/M/R 各自一轴（clickAction/middleClickAction/rightClickAction）。
- 滚轮：`media.scrollAction`（none/volume，步进与 bar 边缘滚动一致 0.05）。

### v4 迁移（`ConfigMigrations.js`）

- `MIGRATED_WIDGET_GLOBALS` 显式键名映射（entryKey → [section, flatKey]，"" 段 =
  [bar] 直键）；`quickSettings` 条目按引用共享 utilButtons 的映射（一组件一表）。
- 唯一例外：`[time].dateFormat` 折叠进 clock 条目（该键在 [bar] 外）。
- dux `migrateBarWidgetGlobals` 语义：逐实例复制、条目已有键赢、**等于默认值跳过**
  （最小写入本就会删）、折叠后删全局键；幂等（跑完版本即 4）。
- 头戳升 4；ConfigService 快路径接受 2/3/4（老文件 QML 侧迁移，不走 python helper）。

### tray 边界（域共享状态 vs 逐实例轴）

- 逐实例：tintIcons/hidePassive/showItemId——passive 过滤移到 `SysTray` 部件侧
  （`TrayService` 只供原始成员桶，永不过滤 `Status.Passive`）；tint/showItemId 由
  SysTray 委托注入 `SysTrayItem`。
- 域共享：`pinnedItems`/`invertPinnedItems` 留在 `[bar.tray]`——pin 是托盘域单事实
  （一份 pin 列表，多实例共享；`isPinned` 按成员资格取模反转推导）。

### 第四注册点与设置面

- `ui/BarWidgetCatalog.qml` 增 `optionsFiles` 映射（id → `plugins/bar/options/`
  页面文件）；契约：keys ⊆ IDS、文件存在、quickSettings == utilButtons 页。
- `BarWidgetPage.qml`：实例编辑页宿主——uid 定位条目、`value()/set()` facade
  （选项页存储盲写，全走 `page.*`）、通用卡（显隐 + lane 位置）+ Loader 载选项页。
  **不是 manifest 路由**：uid 参数化页面不进导航/搜索（登记边界；bar.modules.tray
  搜索锚迁移到 TrayOptions 页内）。
- 入口：chip 齿轮（`SortableMultiSelectField.configureRequested(entryKey)` →
  `BarComponentsCard` → `BarModulesSection` → `GeneralBarPage.openWidgetEditor`）。
- 退役：`BarModulesSection` 的 widget-scoped 组（Workspaces/Utility/Resources/Tray
  约 25 行）与 end4 `isUsed` 门（条目的选项随条目存在而存在）、
  `BarAppearanceSection` 的 divider 三行与 Clock dateFormat 段。
- 共享行留存：`barShowValues`/`barShowNames` 是 **quickpanel 弹层**的数据面形状键
  （全局一份，消费者 `plugins/bar/quickpanel/*`），入口迁 UtilButtonsOptions
  "Hover popouts" 段，不进轴表。

### 明确不迁（登记边界）

- **island\* 轴**：岛设置页独立架构（D3 搁置连带），待 D4e 处置；岛条目暂无轴。
- ~~`barWidgetStyles`（右键改色弹层，per-(mode,widget)）~~ **已随 D4c 处置**：折叠进
  当前 borderless 档的条目 overrides（uid 寻址，重复部件各配各的），per-mode 维度退役。
- `quickSettingsComponents`（quickpanel 域组件集合）不在 bar 条目轴。
- ~~overflow/placement = D4d 材料~~ **已随 D4d 落地**：`overflowMode`/`overflowPriority`
  条目轴 + lane 溢出默认轴（见「行为与溢出（D4d）」节）；密度/多 bar = D4e 材料。

## 多 bar 存储 / 窗口 / 轴穿线（D4e e1–e3）

D4e 落地时单 bar 闸门解除。三段交付按引擎连贯性落地（e1 存储 → e2 窗口 →
e3 轴穿线）；设置面（WidgetsTab 列表式/barSelector/reset 感知）与岛接入、
密度/iconScale 属后续 e4–e6，本页届时增量。

### e1 存储解锁

- `normalizeBarConfigs` 保留全部条目：id 去重（首个赢，无 id 条目按序生成
  确定性 id `default` / `bar<n>`），**单例（island）跨整个数组去重**——共享
  `usedSingletons` 桶依次传给每个条目的 lanes 归一化，第一个条目赢。
- 条目根新增 `enabled`（机械键，与 id/name 同级，非样式轴）；稀疏写只在
  `enabled === false` 时落键。**多条目时每个条目必须落盘**（纯净兄弟条目以
  `{id}` 持久化——丢弃它会删掉那条 bar）；单条且全默认整段消失（快照不破）。
- **uid 带 bar 域**：`widgetId@barId.zoneindex`，跨 bar 唯一；迁移/替换 lane
  重新生成（会话身份，不持久化）。
- `selectedBarId` 会话态（不持久化，"" = 首条，失效回退首条）：设置面编辑哪条；
  **窗口层实例化全部条目，选择只是编辑器概念**。
- 变更核心 `withBarConfig(barId, mutator)`（mutator 收到条目与整个数组——
  跨 bar 单例守卫要看见兄弟）；`withBarConfigs` 路由到 settings-facing 条目。
  存储 API：`addBarConfig`（生成空闲 id，默认 lanes 尊重单例归属）、
  `deleteBarConfig`（拒绝 factory 条目与最后一条）、`setBarEnabled`、
  `renameBarConfig`。
- 单例守卫全链覆盖：`setBarLayouts`/`setBarLaneEntries`/`addBarEntry`/
  `moveBarComponent` 的加路径都按 `singletonIdsInUse` 拒绝宿主外的第二个岛
  （顺带修掉旧洞：同 bar 他 lane 编辑器可加第二个岛，直到下次 reload 才去重）。
- `islandInLayout` 扫描整个数组（通知槽仲裁真值）。
- **无 configVersion 迁移**：旧文件天然单条（D4a 起就只写单元素），数组 schema
  早已就位。

### e2 窗口多实例

- `Bar.qml`：Scope 持 IPC/签名/装载序；**`Item{ Repeater }`**（Repeater 需要
  Item 父级才能物化 delegate——Scope 是非视觉 QObject，挂 Scope 下 count 有值但
  delegate 为 null，无任何错误日志，probe 实测）→ delegate Item（持 `barConfig`
  实时绑定 + `enabled` + 就绪位）→ **delegate 内声明**的 `Component`
  （delegate 局部 id 按声明作用域词法解析，声明在文档级会静默拿不到 `barHost`）
  → Item → Variants（该条目 screenList 的屏）→ LazyLoader → PanelWindow。
  每窗口根持 `barConfig`/`axes`（`BarDefaults.DEFAULTS` 兜底信号重建空隙）。
- **签名重建**：`barLayoutStateJson()`（id/enabled/position/screenList，横向先
  按 id 排序）变化才重建窗口；样式编辑经 barConfig 绑定热更新。
- 装载序：横向 bar 先 claim exclusive zone，纵向等
  `horizontalReady >= horizontalWanted`（dux ShellCore 语义）。
- 屏幕热插拔靠 Variants model 重算跟随；**不搬** dux 恢复风暴机制（登记边界）。
- 遗留边界：`Appearance.sizes` 厚度链（barThickness/barStyleBoost）、fontScale
  （BarScale 单例，104 处）与经 Config 桥消费的样式叶仍跟随
  settings-facing 条目（= 首条/ui 选择条目）——随 e6 叶级清扫完成 per-bar。

### e3 轴穿线与解算层

- `PersonalizationConfig`：`barStyleContextOf(axes)` + `resolvedBar*` /
  `barStyleContext` / `barWidgetOutline*` / `barSurfaceBorder*` 全部接受可选
  `axes` 尾参（缺省 = settings-facing 条目）——宿主与 BarGroup 传自己的。
- 内容宿主（BarContent 单宿主，D4g 起横竖两向共用）：`barConfig` 注入（默认绑定
  active 保证 probe/独立装载可用，窗口覆写）；`axes` 别名；lanes 视图直接读
  `barConfig.lanes.*`；`isMaterial/isMaterialHug/isPanel`、laneMargin、
  shellRadius、背景色、rowSpacing/laneSpacing、overflow 回退、`onRight` 全部走
  自己的 axes。**盲替换踩过的坑**：`!Config.options.bar.bottom` 这类前缀取反
  必须改成 `position !== "bottom"`（`!string === "bottom"` 恒 false，圆角几何
  静默坏掉）。
- BarGroup：`barAxes` 注入（12 个实例化点传 `root.axes`）；borderless/groupColor/
  isMaterial/cornerStyle 判定、capsule padding/color、描边全部走 `barAxes`。
- 部件级：`injectWidgetEntry` 顺手推 `widgetBar`（第二注入，D4a 协议扩展）；
  hoverPopouts 六消费者、StyledPopup 延迟与弹层锚定轴（barEdge/edgeMargin/
  cornerStyle）、LaneOverflowHost 转发全部按"自己的 bar 优先，缺省回退
  settings-facing"解析。
- **顺带修掉的既有 bug**（probe 撞出）：Workspaces 5 处 `elementMoveSmall`
  令牌在 Nyxuri Animations 阶梯不存在（end4 同名令牌 = expressiveFastSpatial =
  Nyxuri `elementMoveFast`，动画此前静默失效 + 运行时 TypeError）；DynamicIsland
  的 `Qt.callLater` 补宿主守卫（销毁竞态下不得碰服务）。门禁：`test_d1`
  新增「全库 `Appearance.animation.<token>` 必须落在 Animations.qml 令牌表」。

### D4e e4–e6 设置面、岛接入与叶级收口（2026-11-28）

- **e4 设置面与共享原子**：
  - `shell/ui/` 新增四件复用原子 `PreferenceGroup.qml`（自动识别 `isPreferenceRow` 可见子行打圆角，避免手动 `first`/`last` 漂移）、`PreferenceCollapsibleGroup.qml`（高度裁剪折叠容器，规避 Quickshell `ColumnLayout` 切换 `visible` 的零宽 bug）、`PreferenceControlledBy.qml`、`PreferenceVisualPicker.qml`（`edge` / `icon` 视觉选择卡），并为 `PreferenceHeader` 与输入原子（Toggle / Slider / Select / Input）统一补齐 `modified` / `showReset` / `resetRequested` 复位槽。
  - `BarManagerCard.qml` 在 `GeneralBarPage` 顶部管理 `barConfigs`（单选激活 `selectBar`、内联重命名、新增（上限 4）、启停切换、保护默认/末条不删、全停警示）。
  - 退役 `BarComponentsCard.qml` / `SortableMultiSelectField.qml` / `LayoutDragCoordinator.qml`（chip 卡），改用 `BarModulesSection.qml` 中的跨栏拖拽协调器 + 三栏 `BarLaneSection.qml` 列表编辑器（拖拽手柄、溢出模式折页、spacer 内联 `MaterialStepper`、行点进 `BarWidgetPage`、单部件开关/删除、`BarWidgetPickerPopup` 添加并守卫 `island` 单例）；`quickSettingsComponents` 独立收口在 `QuickSettingsListCard.qml`。
  - 部件选项页 schema 化评估结论：**保留 13 页手写 `options/*.qml`**，`Manifest`/`SchemaSettingsPage.qml` 的 5 型 `controls` 词表绑定 `PluginSettings` 且缺节标题、`visibleWhen`、hex 校验、`PreferenceAction`、`argv` 拆分与 `SettingsSearchAnchor`；改为在手写页内升级 `PreferenceGroup` 与复位槽。
- **e5 灵动岛迁入条目与 v6 迁移**：
  - `BarWidgetDefaults.DEFAULTS.island` 接管五项外形键（`satellite: "clock"`、`showAvatar: true`、`showMediaControls: false`、`visualizerStyle: "dots"`、`hideDate: false`）。
  - `ConfigMigrations` 升至 **`CURRENT_VERSION = 6`**（`ConfigService.qml` 头标 `# nyxuri-config-schema: 6`，fast-path `2..6`）；`MIGRATED_ISLAND_KEYS` 在 `version < 6` 时将非默认键折叠进各 bar 的 `island` / `dynamicIsland` 条目、剥离旧平铺键与废弃 `layoutMigrated`、仅在无 `[island.horizontalClock]` 等子节时删除空 `[island]`；`horizontalClock`（字体轴/字形排版）与 `bar.island` 状态灯保持独立配置节。
  - `DynamicIsland` 接收 `widgetEntry`/`widgetBar` 并暴露 `option(key)`；`DiIdle`（含按 `di.widgetBar.lanes` 判定 `systemIconsElsewhere`）与 `DiMedia` 改读条目覆盖；新增 `options/IslandOptions.qml` 并注册到 `BarWidgetCatalog`。
- **e6 `DensityPresets`、`iconScale` 与叶级清扫**：
  - `DensityPresets.js`（Fork & Trim 自 dux `DensityPresets.js`）提供 `compact` / `comfortable`（对齐 `BarDefaults.DEFAULTS` 基线）/ `spacious` 三档预设，作用域为当前选中 bar（`applyBarDensityPreset`）。
  - `BarDefaults.DEFAULTS` 新增 `iconScale: 1.0`；`BarScale.qml` 提供 `fontFor(widgetBar)` 与 `iconFor(widgetBar)`；`PersonalizationConfig` 提供 `resolvedBarHeight(axes)` / `resolvedVerticalBarWidth(axes)` / `barStyleBoostFor(axes)`，解耦设置态与每窗实况高度。
  - `Bar` / `BarContent` / `VerticalBarContent` / `BarGroup` / `BarGroupStylePopup` / `StyledPopup` / `LaneOverflowHost` 及全部 bar 部件叶组件收敛为消费各自 `widgetBar` / `barAxes`、`resolved*` 尺寸与 `BarScale.fontFor` / `BarScale.iconFor`，断开对全局 `Config.options.bar.bottom` / `vertical` / `cornerStyle` 的回源依赖。

### D4e e1–e3 证据

- probe `d4e` 节（store / signature / windows 三段）：双 bar 存储往返、
  uid 唯一、单例归属、跨 bar 守卫、per-entry 稀疏写、回环归一；签名只随路由
  变化；窗口场景 `two`（bottombar 自带 clock-only lanes，窗口各 1、内容按条目）、
  `off`（禁用条目窗口归零）、`clean`（复原单 bar）。scene 模式全绿。
- 契约测试 `tests/shell/test_d4e_bar_config.py`（16 例）+ d4a–d4d 及
  bar_end4/shell_architecture 的钉随形态升级；全量 784 例绿。
- 实机待验：多 bar 排布手感、屏幕集合、双 bar 弹层锚定。

## 单宿主与轨（D4g）

> 竖置 = 轨（rail），不是转 90° 的横条（D-9）。同一组轴横竖同值；orientation
> 真相是 `axes.position`（left/right → 轨），不再有第二份竖向宿主。

- **单宿主**（2026-11-28 批一）：`VerticalBarContent.qml` 退役并回
  `BarContent.qml`——一份 lane 树经 `AxisContext`（dux 原件整抄剪裁，61 行：
  `edge`/`isVertical`/`primarySize`/`crossSize`）在行与轨两种方向下排版。
  `Bar.qml` 单挂载（`sourceComponent: barContent`），翻边不再重建内容：
  几何绑定轴条件化重算，部件经 `injectWidgetEntry` 注入的
  `Qt.binding(() => root.axis.isVertical)` 活体换轴（widgetEntry/widgetBar
  注入协议不变）。
- **显式几何铁律**（承 Bar.qml 翻边回归）：所有随轴翻转的位置绑定用
  x/y/width/height 显式表达式，禁止条件锚（QML 绑定产出 `undefined` 不清锚）。
  三个 lane 的行/列布局合并为单个 `GridLayout`：`columns: vertical ? 1 :
  lane.length + 1`，子项 `fillWidth`/`fillHeight` 轴翻转。
- **zone 即真相**：lane 内部 id 与宿主引擎沿用 left/middle/right 存储区名——
  轨上 left = 起点（top）、right = 终点（bottom）；溢出按钮六 id
  （`left/middle/rightOverflowHost(Material)`）双方向共用。probe 面横竖并集
  导出（`laneCenterX/Width` + `laneCenterY/Height`、`laneLeft/RightWidth` +
  `laneTop/BottomHeight`、`centerPillX/Y/Width/Height`），各方向探针读自己那组。
- **轨保留 end4 竖向行为**：middle lane 过滤 island（竖向岛形状归批三）、
  竖向 spacing ladder（`resolvedBarSpacing(true, axes)`）、融合角/胶囊壳半径
  按「镜像面朝屏幕附着边」逐角轴分支（行：top/bottom，轨：left/right）。
  边缘滚动条在轨上零延展（轨向滚动动作归 D4h）。
- 批次：批一单宿主并回（本节）→ 批二部件能力目录（本节批二段）→ 批三
  clock/systemMonitor 竖向语法 + 竖向岛 → 批四a 竖置默认布局 + 仲裁收口（本节批四段，
  已落地）→ 批四b 避让让位基建 + 横竖转角接合（待开始）。
- **批二（部件能力目录，2026-11-28）**：设置面据此对轨禁用并说明，引擎零消费。
  - `ui/BarWidgetCatalog.qml` 每条目声明 `orientations`（横/竖支持）；竖向可用的
    再加 `verticalMode`，词表闭合 D-9 三语法（`stack` 沿轨重排/`rotate` ±90°/
    `iconPopup` 轨上图标面 + 弹层）。**缺 `verticalMode` = 无轨面判定**，无第四值。
  - 分类是逐部件审计结果（今日轨上实态，B9.4 轨化遗产，非愿望）：`stack` =
    tray/systemIcons/utilButtons+quickSettings/workspaces/visualizer/weather/
    separator/spacer/launcherButton/powerButton；`rotate` = battery（进度条
    -90°）；`iconPopup` = activeWindow/media（轨上是裸图标退化面——dux 竖向
    退化基线，悬停弹层半边未建）；无轨面 = island（轨上被 middle lane 过滤，
    紧凑面归批三）/clock（批三首位）/systemMonitor（表盘未适配轨宽）。
  - 设置面三处消费 `supportsVertical()`（选中 bar 为轨时生效）：添加 picker
    禁用（block 图标 + 「竖向状态栏上暂不可用」）、`BarLaneSection` 在册行
    subtitle 追加说明、`BarWidgetPage` 实例页 capability 提示行；**不删除用户
    配置，装载不变**（批三语法落地前轨上照挂现状）。
  - helper `supportsVertical(id)` / `verticalMode(id)` 纯函数读目录声明；
    probe `d4gCatalog` 节做数据级断言（分类判定 + 词表闭合 + 逐行
    vertical⟺mode 配对），设置面禁用手感归作者实机。
- **批三（竖向岛紧凑面 + clock 轨面升级，2026-11-28）**：
  - **竖向岛**：撤销 end4 的轨上岛过滤——岛作为 middle lane 成员在轨上装载，
    pill 沿轨生长（宽 = 轨厚 `resolvedVerticalBarWidth`，高 = 活动面沿轨长度
    `railPillLength`），整胶囊 `min(w,h)/2`，宽/高动画各随己轴（`Behavior
    enabled` 门，禁条件锚）。四面 column 变体（dux `compactColumn` /
    `pillTarget(along, cross)` 血统；岛住 middle lane，用整胶囊代 dux 贴边角
    拆分）：idle = 头像上 / 时钟卫星（`ClockContent` vertical，edge =
    `axes.position`）中 / 状态图标列下，长度经 `idleRailContentLength` 回调
    上报（同 `idleTextContentWidth` 模式）；OSD = 图标上 + 数值下（dux
    `SystemLevelCompact` `verticalFace` 血统，无滑杆故无轨道）；媒体 = 封面上
    + 播放键下，文字/控制/频谱半边是行面专属（挂窗口增长基建）；会话 = 四动作
    竖排（`ActionDelegate` inline component 复用）；通知 = 图标紧凑面（文本面
    同窗口增长基建）；电池警报 = 图标 + 百分数。badges 行仍横面专属。
  - **clock 轨面升级**：caelestia `modules/bar/components/Clock.qml` Fork &
    Trim 换血 colDefault/colMaterial——单 `RailClockFace` inline component
    （`materialSkin` 分色），日期块（weekday/日/分隔线，`showDate` 轴门控）+
    HH/MM 逐行 TextMetrics 光学匹配（`fontFor` 血统：窄行最多 +5%、"11" 固定
    +15%）+ am/pm 行；dateFormat 长格式仍是行面专属。两处对原件的偏离如实
    登记：fit 阶段（轨厚是 28–64 轴，基号向最宽行收缩，原件内宽固定充裕）与
    像素缩放代替可变字体 width 轴（钟体可配置不保证 variable）。
  - **systemMonitor**：轨面早已存在（五仪表竖排 colDefault/colMaterial），
    批三仅修正目录判定，无新语法。
  - **目录判定修正（批二勘误）**：clock/systemMonitor/island → 轨可用
    （stack）——批二按 roadmap「clock 与 systemMonitor 没有竖向处理」钉的判定
    与代码不符（两者都有 B9.4 轨面），批三以证据拨正；「缺 verticalMode = 无
    轨面」协议保留（现行 17 部件全部轨可用，该判定空集待未来部件使用）。
  - 机器证据：契约测试 `test_d4g_bar_config.py`（判定翻转 + IslandRailFaceTest
    批三钉）+ bar 系 286 例绿；probe `d4gCatalog` 判定翻转 + 竖排 rail 实况节
    （default 场景 middle=[island]、idle 紧凑胶囊 36×132 沿轨居中、`ipc osd
    volume` 触发 OSD 轨面 36×76）；会话 probe exit=0 全绿零 logErrors。
    实机项归作者：轨上岛四面观感与手感、clock 堆叠轨宽适配实观。
- **批四a（轨默认布局 + 仲裁收口，2026-11-28）**：
  - **轨默认集**（D-9，作者拍板裁剪版）：`defaultRailLayout*` 独立成表——
    起点（left zone）`[launcherButton, workspaces]`、middle `[island]`、
    终点（right zone）`[tray, systemIcons, powerButton]`。activeWindow 不进轨
    默认（悬停弹层半边未建，裸图标无信息量），quickSettings 让位 SystemIcons
    的 hover 展开面。横排三表原样保留。
  - **单入口解析**：`defaultBarLayoutsFor(position)` 是「缺 lane 读默认」的唯一
    入口——load normalize（`normalizeConfigLanes` 增 `position` 参）、lane 复位
    （`resetBarLanes` 传条目 `axes.position`）、sparse 写入比较三方同源，不漂移。
  - **翻边活体语义**：`setBarPosition` 先判 `barLanesMatchOrientationDefaults`
    （lanes 等于**当前方向**默认 = 未定制），翻边后未定制条目随新方向重解析
    （top↔rail 活体换默认集），定制过的随人。新建 bar 默认仍 top。
  - **sparse 方向感知**（坑修复）：`sparseBarConfigEntry` 的 lane 比较基线改
    `defaultBarLayoutsFor(truth.axes.position)`——原实现拿横排 fallback 比较，
    零定制轨条目会整段落盘，破最小化写入。
  - **落盘合并根因修复**（批四踩响的既有潜伏 bug）：`updateSections` 按键合并
    覆盖，而 `toJson` 对全默认段 `delete json.bar`——段「非默认→变默认」的那次
    保存清不掉 `rawConfig` 里上一轮的旧段，debounce 落盘写回瞬态（翻边
    top→rail→top 实测复现）。修法：`toJson` 保留空段对象，`ConfigService.saveNow`
    落盘前统一剔除空段——文件契约不变（全默认 `[bar]` 仍整段消失）。
  - **桥视图退役**：`Config.options.bar.bottom`/`.vertical` 零消费者退役
    （`SystemIconSlot` tooltip 改读注入 `barAxes`，对齐 UtilButton 先例）；
    probe 舞台改读 `PersonalizationConfig.barPosition`。
  - **岛仲裁收口**：`shell.qml` popup:notification 仲裁删竖排豁免——批三轨面
    岛已落地，`islandInLayout` 即岛独占槽（轨上 DiNotifs 走图标紧凑面）。
  - **probe `d4g.defaults` 节**：store 视图断言轨默认集/横排集双向读回 +
    toml 稀疏快照（`left\t0`/`top\t0`，lanes 键零写入）。
  - 机器证据：`test_d4g_bar_config.py` RailDefaultLayoutTest（轨默认表/单入口/
    sparse 方向感知/翻边重解析/仲裁无方向门/桥零残留）；tests/shell 全量
    827 例绿；会话 probe exit=0 全绿零 logErrors。遗留补账：批三岛轨钉
    （test_bar_runtime ×6）、D4f schema 钉（stamp 6→7）、D4f 词典清账
    （死键 ×4 + 缺失文案 ×13）一并修复。实机项归作者：翻边手感与轨默认观感。
- **批四b（避让让位基建 + 转角接合，2026-11-28）**：
  - **投影单例**（唯一让位真相）：`services/ScreenBarLayout.qml` + 纯库
    `commons/BarScreenLayout.js`（dux `LayoutResolver.js` Fork & Trim：岛/
    帧/哥特翼/行堆叠等 dux 特有分支全裁）。输入只取 barConfigs × 屏（配置
    真相，不读窗口实例），输出每屏每边 band 预留 + 逐 bar tuck insets；
    预留 = `BarGeometry.exclusiveZone`（窗口绑定的同一函数），autoHide 条目
    预留 0（dux `reserves` 血统）。屏幕列表语义沿 D4e（空 = 全屏，无匹配
    回落全屏）。
  - **转角接合**（作者拍板，偏离 dux）：同角相遇按 configOrder 裁决——先建
    图者通长占角、贴屏装饰归它；后建图者让出共享沿轴端 = 对方 band 预留 +
    4px 接缝（dux `spacing ?? 4` 血统）。逐角独立裁决，双端可同时 tuck
    （两侧轨都早于横 bar 时横 bar 让两端）。tuck 走窗口 margins 叠加
    （`windowMargins` 逐轴相加），exclusiveZone 不变；内容随缩短的窗口
    自动重排，融合角/胶囊装饰随内容边缘走。
  - **消费面**：通知 popup（per-screen 每边预留 + 12 呼吸，裸角 16 基线）、
    两侧栏面板（同边轨吃 x 跨度，上下横 bar 吃 y 跨度——Overlay 不再压过
    Top 层 bar）。**登记边界**：启动器（全屏 overlay 居中内容）不让位不改
    （登记）；dock 角接合不做（dock 不在 barConfigs，resolver 可扩）；通知
    只避 top/right（窄屏左轨重叠登记）；quickpanel 按钮（BluetoothButton/
    Network）仍读选中 bar 的 `barPosition`，归后续部件轴收口。
  - **桥键全退**：`Config.options.bar` 的 `edge`/`bottom`/`vertical` 三派生
    视图退役——StyledPopup 七实例全部由宿主 widget 注入 `widgetBar`（逐点
    核实），不可达 fallback 删除；通知 popup 迁投影；SystemIconSlot tooltip
    读注入 `barAxes`（批四a）。
  - **probe `d4g.avoid` 节**：配置侧三幕（solo 基线 41/0 → 后建轨 tuck
    top=45=topBand+4、top 零 tuck → autoHide 轨预留归零且 tuck 随塌 → 反序
    轨先建、后建 top bar tuck left=45）；窗口侧钉 margins 绑定
    （top = sideMargin + tuck，逐轴）+ 高度上界（session probe 与作者
    live shell 同屏，窗口高吸收环境 zone，不做精确断言——weston 沙箱可
    精确复验）。
  - 机器证据：`test_d4g_bar_config.py` CornerJunctionTest（fork 头/configOrder
    裁决/单源投影/margins 合并/消费面/桥零残留/probe 钉）；tests/shell 全量
    834 例绿；会话 probe exit=0 全绿零 logErrors。实机项归作者：双 bar 转角
    观感与接缝、通知/侧栏让位手感、autoHide 往返下的让位节奏。

## 证据

- **D4a**：probe `d4a` 节——条目几何（禁用不实例化/lane 塌陷/spacer 注入 40 vs
  默认 20/单例去重）、迁移（版本/别名/种子/剥除/幂等）、持久化（默认空段/单键
  （条目平键形态）/恢复空/configVersion=5）。契约测试 `tests/shell/test_d4a_bar_config.py`。
- **D4b**：probe `d4b` 节——迁移（v4 折叠/跳默认/剥除/pin 保留/dateFormat 折叠/
  幂等）、双实例隔离（默认态坍缩回字符串）、点击词表（闭合 id、argv 形状、未知
  id 回退）；`d4bSet` IPC 写单轴（b97 系列部件行为随动全部改走条目路径）。
  契约测试 `tests/shell/test_d4b_bar_config.py`（38 例）。
- **D4c**：probe `d4c` 节——v5 迁移（框轴折叠/跳默认/widgetStyles 当前档折叠+他档丢弃/
  剥除/幂等）、哨兵解析（spacing 显式覆写/复位回基线/inset=4/padding=5/radius
  auto→square→override 链）、融合角色（run 融合/隐藏重排/spacer 断 run/live 角标）。
  契约测试 `tests/shell/test_d4c_bar_config.py`（34 例）；weston 沙箱 probe 全绿
  （含 d4a/d4b/b96/b97 回归）。
- **D4d**：probe `d4d` 节——行为轴往返（默认保现行/稀疏写入/复位）、解算器单跑
  （词表/priority 让位/always/pinned/迟滞恢复）、实况挤压（300px 舞台：隐藏集含
  侧栏全部非 pinned 部件、island 留守、按钮在场、弹层迁居-迁回双程、复位清零）。
  契约测试 `tests/shell/test_d4d_bar_config.py`（30 例）；weston 沙箱 probe 全绿。
  实机项归作者：溢出按钮手感、穿透空隙点击、strict 收起节奏、全屏进出 reveal、
  150ms 弹层体感。
- **D4f**：样式原子化 + v7 迁移（2026-11-28）——
  - `cornerStyle`（6 档）× `borderless`（5 档）× `showBackground` 退役为正交原子轴，存储在 `[[bar.configs]].axes`：
    - 结构/材质：`backplate`（bool）、`lanePill`（bool）、`tint`（bool）
    - 外边距：`edgeMargin`（int，`0` = 贴边，`>0` = 悬浮，默认 `5`）、`sideMargin`（int，哨兵 `-1` = `floating && backplate` 时解析为 `gapsOut`，否则 `0`）
    - 部件外观：`widgetStyle`（`"fused"` / `"separate"` / `"flat"`）、`capsuleRadius`（`"pill"` / `"rounded"` / `"px"`）、`widgetRadius`（`0..32`，`capsuleRadius === "px"` 时生效）、`groupColor` 补齐 `"transparent"`
  - 两层纯解析：`services/BarDefaults.js` 提供 `deriveStyle(axes, gapsOut)` / `styleBoost(style)` / `resolvedSideMargin(axes, style, gapsOut)` / `capsuleFullRadius` / `capsuleMidRadius`；`plugins/bar/BarStyle.js` 组合 `deriveStyle` 输出窗口/内容/分组/岛/弹层消费的展示上下文（满足插件与服务解耦边界）。
  - 外形起点配方：`services/BarStylePresets.js` 定义六档只写轴不落盘配方（`hug` / `floating` / `islands` / `material` / `materialHug` / `panel`），`applyBarStylePreset(key)` 按键写入、`currentPreset(axes)` 匹配高亮（偏离任何样式键即失亮为自定义）。
  - 单一外边距真值与 D-8 暗加成清账：`Bar.qml` `windowMargins` 统一承担外边距，废除 `layerGap` / `m3OuterGap` / `barBackground.anchors.margins` 叠套；`styleBoost` 仅保留 `isLaneHug`（`lanePill && !backplate && edgeMargin === 0`）的 `+4` 贴角装饰余量，退役 Islands `-6` exclusiveZone、Islands 8px 内角（统一 `6`）与 Panel `+4` 高度/exclusiveZone；`BarGeometry.margins` 与 `exclusiveZone` 不再接收 `cornerStyle`/`layerGap`。
  - schema v7：`ConfigMigrations.CURRENT_VERSION = 7`（头标 `# nyxuri-config-schema: 7`，fast-path `2..7`），`version < 7` 通过显式映射表将历史 `cornerStyle`/`borderless`/`showBackground` 折叠为上述原子轴并剥离旧键与平铺遗留键。
  - 设置面重排：`BarAppearanceSection.qml` 顺序收敛为 `Appearance`（6 枚 `PreferenceVisualPicker` 预设卡）→ `Layout`（可折叠 `Advanced` 数值微调）→ `Screens` → `Structure` → `Surface`（可折叠 `Widget layer`）→ `Behavior`。
  - 机器证据：契约测试 `tests/shell/test_d4f_bar_style.py` + `tests/shell/` 回归绿；probe `d4f` 节（v7 迁移、预设写入/自定义失亮、D-8 退役校验、`capsuleRadius` + `groupColor: "transparent"`、`vertical` 仅 `materialHug` +4）与 Weston 运行态 probe 全绿；实机视觉过目（六档外观等价与设置页折叠体验）归作者。
- **D4g 批一（单宿主并回）**：`AxisContext.qml` 整抄（dux 61 行剪裁）+
  `VerticalBarContent` 并回 `BarContent` + `Bar.qml` 单挂载（翻边不重建）+
  probe 装载轴驱动。机器证据：bar 相关契约测试 275 例绿（end4/d4a–f/runtime/
  manifests/architecture）；会话 probe 全绿零 logErrors——`vertical` 六例
  （左右 × floating/materialHug/centerOnly，轨宽 36/40、居中 678/84、岛过滤）、
  `windowProbe` top→left→right→bottom→top 往返零残留（条件锚回归门）、
  d4a–d4f/b96/b97 回归节全 OK。`VerticalBarContent.qml` 删除（-716 行）。
  实机项归作者：左右轨排布与融合角视觉（B9.4 验收项不变）。




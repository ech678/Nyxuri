# Bar 自定义引擎契约 (D4)

> 本页是 bar 自定义引擎（D4 五期）的架构契约：配置 schema、默认值回退、最小化写入、
> 版本化迁移、部件注册表与属性注入协议。分期交付与验收归
> [shell/ROADMAP](../../shell/ROADMAP.md) D 卷；D4a 于 2026-11-21 落地，后续期次在此页
> 增量补节。运行行为以源码与契约测试（`tests/shell/test_d4a_bar_config.py`）为准。

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

bar 级几何/样式轴（spacing/胶囊样式/长度模式等）D4c 才迁入 configs 条目；当前仍在
`[bar]` 扁平键。

## 三层默认值回退 + 单一取值入口（D4a）

`services/BarWidgetDefaults.js` 的 `option(widgetId, entry, key)` 是唯一取值入口：

```
entry.overrides[key] → DEFAULTS[widgetId][key] → GLOBAL_DEFAULTS[key]
```

**部件代码从不直接碰存储**：宿主（BarContent/VerticalBarContent）把 lane 条目经
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

- 三处 id 集合相等由 `test_d4a_bar_config.py` 契约钉死；D4b 起 + 第四处（设置页）。
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

## 证据

probe（`scripts/dev/probe-bar.sh`）`d4a` 节：条目几何（禁用不实例化/lane 塌陷/
spacer 注入 40 vs 默认 20/单例去重）、迁移（版本/别名/种子/剥除/幂等）、持久化
（默认空段/单键/恢复空/configVersion=3）。契约测试
`tests/shell/test_d4a_bar_config.py` 32 例。

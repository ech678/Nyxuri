# Bar & Island 统一工作页（B 卷）

> B 卷（keystone 并入 bar）的整抄基线台账与四类裁剪清单。决策记录（D1–D6）、
> 分期目标与验收标准以 [shell/ROADMAP](../../shell/ROADMAP.md) §B 为准，本页
> 不重复；本页回答：基线抄了什么、每件怎么裁、什么不抄为什么、豁免到几时。
> 状态随分期推进更新，B5 结账后本页归档。
> B1 已执法（正名后全库称 island/屿）：岛并入 `plugins/bar/island/` 成为 bar
> 布局部件，本页下文以旧名 keystone 指称的引擎与部件即今 island 侧同名件。

## 基线清单（B0 入库，inert）

物理 `cp` 自 `references/`（仓库根、gitignored），落在
`shell/plugins/bar/vendor/`，保持源相对子路径。inert：无消费者、不进装载
闭包、零运行时影响。

### 皮肤源 end4（`vendor/end4/`，B3 消费）

| 基线文件 | 源（end4-pC） | 承载能力 |
| --- | --- | --- |
| `modules/ii/bar/Bar.qml` | `modules/ii/bar/` | cornerStyle 窗口壳：exclusiveZone 分档、贴顶/悬浮边距、屏幕圆角装饰带、autohide 角落揭示、IPC/全局快捷键（④类死路径） |
| `modules/ii/bar/BarContent.qml` | 同上 | 皮肤核心：三段布局、材质胶囊（左/中/右 ×3）、center-only 纯岛形态与拼角、部件 URL 解析 |
| `modules/ii/bar/BarGroup.qml` | 同上 | 分组圆角 start/mid/end 逻辑、borderless 三模式、每部件样式覆写（padding/色/边框/圆角） |
| `modules/ii/bar/BarGroupStylePopup.qml` | 同上 | 部件级样式编辑器弹窗（BarGroup 右键消费者） |
| `modules/ii/bar/Divisor.qml` | 同上 | 分隔件三形态（rect/dot/space）、竖排适配 |
| `modules/ii/bar/StyledPopupHeaderRow.qml` | 同上 | 弹窗标题行词汇（B3 弹窗同语言重皮） |
| `modules/ii/bar/StyledPopupValueRow.qml` | 同上 | 弹窗取值行词汇（同上） |
| `modules/common/widgets/RoundCorner.qml` | `modules/common/widgets/` | 屏幕圆角衔接原语（Shapes/PathAngleArc 反圆角方块） |

### 机制源 dux（`vendor/dux/`，B4 消费）

| 基线文件 | 源（dux-shell/quickshell） | 承载能力 |
| --- | --- | --- |
| `Modules/DBar/WidgetModel.js` | `Modules/DBar/` | 布局条目规范化（字符串/对象双形态 → widgetId+id+enabled）与 componentNames 注册表映射 |
| `Modules/SurfaceWidgets/SurfaceWidgetFactory.qml` | `Modules/SurfaceWidgets/` | 注册表心脏：内联 Component 映射 + `getWidgetComponent`/`getWidgetVisible`、按需装载与 section 归属 |
| `Modules/SurfaceWidgets/SurfaceWidgetHost.qml` | 同上 | 注册表消费端：Loader 形态、默认值应用、surfaceContext 注入、orientation/visibility 门控 |
| `Modules/SurfaceWidgets/SurfaceContext.qml` | 同上 | host/factory 共享上下文契约（kind/section/axis/screen/宿主窗口） |
| `Common/settings/BarWidgetDefaults.js` | `Common/settings/` | 每部件默认值模式（DEFAULTS 表 + `option()` 回退读取；含 island 条目全集） |
| `Common/settings/DensityPresets.js` | 同上 | 4 级密度预设（spacious→dense）+ `transition()` 语义：切预设只搬仍停留在旧预设上的键，用户自定值不动 |

## 四类裁剪清单

裁剪只做四类（ROADMAP §B0 方法论红线），超出即为私改。逐件过堂：

| 基线件 | ① 外部依赖桥接 | ② 接 ThemeTokens/Sizes | ③ 接 I18n | ④ 砍上游死路径 |
| --- | --- | --- | --- | --- |
| end4 `Bar.qml` | `Quickshell.Hyprland`（HyprlandData 全屏/special 判定）→ CompositorDriver 等价投影或降级；`CompositorGlobalShortcut` → 树内 shortcut 意图面 | `Appearance.sizes.*`/`Appearance.rounding.*` → Sizes/ThemeTokens | IPC 无文案 | autohide 三 Timer、super 显示、死像素 workaround、cornerOpen 挖洞 mask、bar IPC/快捷键（开关真相在引擎账本） |
| end4 `BarContent.qml` | —（纯 QtQuick） | `Appearance.colors.*` → ThemeTokens；`hyprlandGapsOut` → Sizes 常量 | — | UPower/SystemTray/Mpris import（数据部件走树内服务）；`dynamicIsland` 分支（岛=island morph 引擎，B2 接管）；borderless 特例值待 B3 裁决 |
| end4 `BarGroup.qml` | — | `Appearance.rounding.*`、groupColor 解析 → ThemeTokens | — | `Config.options.bar.widgetStyles` 右键样式编辑器通路（B3 决定去留，砍则连带 StylePopup） |
| end4 `BarGroupStylePopup.qml` | `Qt5Compat.GraphicalEffects` → 树内效果件或 blur 近似 | 同上 | 弹窗文案 qsTr → I18n 词典 | 随 BarGroup 裁决连坐 |
| end4 `Divisor.qml` | — | `Config.options.bar.divider.*` → bar 配置键 | — | — |
| end4 `StyledPopup*Row.qml` | `Qt5Compat.GraphicalEffects`（若有）→ 树内效果件 | 色/字号 → ThemeTokens | 文案 qsTr → I18n | — |
| end4 `RoundCorner.qml` | —（QtQuick.Shapes 树内可用） | `implicitSize` 消费方接 `Appearance.rounding.screenRounding` 等价键 | — | — |
| dux `WidgetModel.js` | —（纯 JS） | componentNames 表按树内部件重写（workspaces/clock/tray/media/sysmonitor/quickpanel + island） | — | dux 专属部件 id（appsDock/dwl/vpn/notepad…）不入表 |
| dux `SurfaceWidgetFactory.qml` | `qs.Services`/`qs.Modules.*`/`qs.DCommon` import → 树内服务；SystemTray/Mpris → 树内数据服务 | `Theme.*` 代币 → ThemeTokens/Sizes | `I18n.tr` → 树内 I18n | 内联部件 Component 换树内部件（数据部件保留原生实现，D5）；popout 路由、dash 触发、dgop 探测 |
| dux `SurfaceWidgetHost.qml` | `qs.Services`（BarWidgetService 注册/按需名单）→ B4 桥接或收敛进注册表本体 | `Theme.*` → Sizes | — | 注册回调（registrationId 三段式）按需裁决 |
| dux `SurfaceContext.qml` | —（纯 QtQml 上下文对象） | — | — | — |
| dux `BarWidgetDefaults.js` | —（纯 JS） | island 键位对齐 B1 正名后的 `island*` 配置键 | — | dux 专属部件默认值段（workspaceSwitcher 长表等）随注册表裁 |
| dux `DensityPresets.js` | —（纯 JS） | PRESETS 数值按 Nyxuri 视觉基准重钉（D6：Sizes 降为默认值层） | — | dock/frame 段（无对应单元） |

## 不抄清单（B0 已裁决，后继不补）

| 上游件 | 不抄理由 |
| --- | --- |
| end4 `DynamicIsland.qml` + `Di*.qml` | 上游孤儿件（全树零消费者，未接线实验）。morph 引擎仍是 B 卷机制层保护对象（抄我们的活引擎优于抄上游死件）；但岛的**样式层保留 Fork & Trim 抄袭权**——该族可作为设计参考源（provider 注册形态与 dux 注册表同构），整抄前须先考据其未接线原因 |
| end4/dux 全部数据部件（Workspaces、ClockWidget、SysTray*、Media、Resources、Weather*、Battery*、Network*、Widgets/* 等） | D5：数据部件保留 Nyxuri niri 原生实现，只换外壳 |
| end4 `ScrollHint.qml`、dux `OverflowLayout.js`/`SectionOverflow.qml` | 溢出滚动在停车场（明确不承诺，触发再立项） |
| dux `BarMetrics.qml` | dux Theme 代币派生表；D6 已定 Sizes 降为默认值层，厚度键走 Sizes+密度预设。且 `pragma Singleton` 与 inert 基线互斥（qmldir 登记门禁） |
| dux `SettingsStore.js`/`ManagedSettings.js`/`SessionStore.js`/`SessionSpec.js`/`SettingsSpec.js` | dux 设置持久化生态；树内已有 PersonalizationConfig/PluginSettings，B4 按需桥接 |
| dux `Services/BarWidgetService.qml` | 绑定 dux Services 单例生态与 popout 路由；注册表模式由 WidgetModel+Factory+Host 三件承载，B4 裁剪时按需裁决 |
| dux `DBar.qml`/`DBarWindow`/`DBarBody`/`DBarContent`/BarSurface/Section* 等 DBar 骨架 | B 卷换皮走 end4 皮肤源（D5），bar 窗口/布局骨架保留树内实现；DBar 骨架与 end4 皮肤混抄即私改 |
| dux `Popouts/*` | 大面板锚定弹窗走树内 `QuickSettings.qml` 范式（B2 点名），不引入 dux popout 生态 |

## 晋升与豁免

- **晋升**：B3/B4 从 vendor/ 将目标件 `cp` 至 `plugins/bar/` 活跃位后定向
  裁剪（四类清单逐项执行）；晋升件脱离 vendor/ 路径即恢复 format/lint/
  audit/单例全部门禁。vendor/ 内原件保留至 B5 对账后处决。
- **豁免登记（B0 起，B5 止）**——所有豁免都以 `vendor` 路径段为界，文件
  晋升脱离 vendor/ 即自动恢复受检：
  - `shell/scripts/dev/files.sh`：`nyxuri_qml_files` 跳过 `*/vendor/*`
    （qmlformat/qmllint 不吃 vendored 基线原格式）；
  - `tests/shell/test_qml_structure.py`：单例 import 扫描排除 `vendor`
    路径段（上游基线自带 import 形态，如 dux `qs.Common` 读 `I18n`）；
  - `tests/shell/test_i18n_catalog.py`：语料排除 `vendor`（基线字面量
    `I18n.tr` 非我方词典义务，基线文本不算真实消费者）；
  - `tests/shell/test_shell_architecture.py`：三处树级扫描排除 `vendor`
    （plugins 目录小写卫牛——基线保源相对布局含 `Modules/` 驼峰；
    废弃 import 禁令——基线上游词表 `qs.Common`/`qs.Services`/
    `qs.modules.*`；`Quickshell.execDetached` 网关禁令——dux factory
    内 exec 属④类裁剪目标）；
  - `audit-lifecycle.py` 本就按 `vendor` 路径段排除，零改动；
  - 「每文件有真实消费者」门禁对 vendor/ 基线豁免——现有扫描池（`ui/`
    平面池、`plugins/settings` 根）本就不含 `plugins/bar/`，无需改测试，
    B5 结账时统一清算。
- **verbatim 偏离登记**：end4 `Bar.qml`/`BarContent.qml` 剥离行尾空白
  共 9 行（git whitespace 门禁），其余基线件与源逐字节一致。

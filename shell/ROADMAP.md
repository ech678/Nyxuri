# Nyxuri Shell 路线图

> 本页只回答：现在在哪、下一步是什么、什么已定死。运行行为以源码与契约测试为准；
> 开发契约见 [AGENTS](AGENTS.md)；设计契约见 [design-system](../llms-wiki/shell/design-system.md)；
> 知识库索引见 [llms.txt](../llms-wiki/llms.txt)。
> 阶段状态仅在有可复现证据时更新；实施明细只进追加式台账
> [shell-roadmap-ledger](../llms-wiki/archive/shell-roadmap-ledger.md)，本页不承载实施记录。
> 已知 BUG 与症状登记见 [known-issues](../llms-wiki/shell/known-issues.md)。
> 当前卷：**第四卷「设计统一」（D 卷）**——存量验收清账 + Material You 契约 + 跨表面统一。
> TUI 计划维持搁置（归主线 T2）。

## 目标与边界

- **体验统一为一等目标**：全 Shell 表面（bar/岛/侧栏/quicksettings/launcher/设置/锁屏/
  OSD/通知）遵循同一设计契约与抄件宪章，拒绝缝合感。统一 = 「同一套宪法 + 同一个身体」，
  不是所有表面对齐同一种长相。
- **抄件纪律（Fork & Trim 四步）**：物理 `cp` 原件 → 剪裁依赖 → **换血到设计契约 token**
  → Nyxuri 特有修改。换血是强制步骤；分层认亲与四问流程见 design-system。
- **Material You（M3）为设计基准**：字号/圆角/间距/色彩角色/状态层/动效的数值源唯一
  （caelestia tokens.hpp = M3 官方数值，已 1:1 钉入 design-system）。
- Shell 冷启动路径小而可解释；可选功能按需加载，停用后释放实例及其 Timer、Process、
  请求、连接、监听和回调。
- 模块按功能域自治；UI 通过 Action Gateway 表达桌面意图；全局 singleton 仅用于确有
  跨域共享状态的能力。
- 清理和重构不得降低视觉品质、动效、可读性、几何精度或对齐。
- 以原版 Niri 为基础兼容目标；外部能力缺失时局部降级，不让可选依赖阻断核心 Shell。
- Wiki 只保留现行契约；历史资料归档，不冒充当前事实。

## 状态规则

任务状态只使用 `待开始`、`进行中`、`阻断`、`待验收`、`已完成`。合并前置、实现、
行为验证和视觉验收分别记录；测试失败、环境跳过与未验证不得混为通过。每项任务明确
旧实现的保留、迁移、归档或删除方式。

## 验收积压（存量清账，不新增工作量）

> 以下各项机器证据已齐，等待作者人工验收；攒成「验收证据包」批量过审。
> B9 系列的对照基线冻结于 [b9-baseline-matrix](../llms-wiki/archive/b9-baseline-matrix.md)
> （2026-11-14 审计快照）。硬件 GPU、真实设备、全部生产界面键鼠/焦点/多屏和安全锁屏
> 不能由 headless 容器替代，不得将缺项改为通过。

| 项 | 状态 | 剩余人工项 |
| --- | --- | --- |
| B9.0 token/圆角基线 | 待验收 | bar 六档样式截图对照 |
| B9.1 SysTray | 待验收 | 实机托盘 pin/unpin、菜单开合、外点关闭、重启保留、Tray 四设置落盘 |
| B9.2 SystemIcons | 待验收 | 实机 hover/tooltip/滚轮音量、真实外设低电通知 |
| B9.3 岛真相 | 待验收 | 岛增删/重启不复活、通知宿主恢复、idle 横向时钟视觉 |
| B9.4 竖向 bar | 待验收 | 左右边缘实机排布、弹层/通知避让手感 |
| B9.5 外边距 | 待验收 | 0/12/24 三档截图与 exclusiveZone 跟随 |
| B9.6 表现基线归零 | 待验收 | 四工作区样式、右键改色弹层、弹层令牌逐项过目 |
| B9.7 设置清账 | 待验收 | 多屏选择、autoHide 手感、space 分隔条、utilButtons 七槽、Resources 五表盘 |
| D1 Bar 收尾与快修包 | 待验收 | 四快修实机过目（托盘箭头 hover 浅深两模式、DiIdle 三段几何、铃铛不复活）、岛媒体面六态截图、天气有/无数据视觉、visualizer 实机频谱、dateFormat 实机切换 |
| D2 SystemIcons QS 化 | 待验收 | 实机 hover 手感、150ms intent 防误触体感、浅深两底色可读性 |
| D4a 配置架构与部件目录 | 待验收 | 实机 chip 显隐开关手感、spacer/separator 添加与拖拽、设置页目录 17 项过目、升级配置一次迁移零感知 |
| T3 M3/M4 设置页积木化 | 待验收 | 核心四页 + 全页面实机视觉过目 |
| P4 主题契约/取色引擎 | 待验收 | 壁纸切换、深浅代调链路、模板 hooks 实机行为；镜像色板长期策略拍板 |
| A1–A8 性能调查 | 待验收 | A6/A8 进行中；明细与各自剩余项见 [performance-plan](../llms-wiki/shell/performance-plan.md) |

## D 卷：设计统一（第四卷主线）

> 依据：2026-11-21 规划定案（D-1~D-6，作者拍板）。
> 执行序：**D0 → D1 → D2 → D4a → D4b → D5 → D4c → D4d → D4e**（自定义核心在统一
> 过堂之前）；D3 试点暂时放弃（D-6，恢复触发条件见
> [delayed-decisions](../llms-wiki/delayed-decisions.md)）。
> **D0 先行是铁律**——契约缺位是 Media 溢出、hover 色错误、字号四套并存这类问题的
> 共同根因，先建宪法再修部件，否则修完还会长回来。

### D0 设计契约基石（源头断根）

- 契约页 [design-system](../llms-wiki/shell/design-system.md) 落地：type scale 一张表、
  圆角 9 档、间距 8 档、MCUT 色彩角色与消费惯例、状态层（hover 8%/focus 10%/
  press 10%/drag 16%）、动效时长曲线、出生律、抄件宪章。
- **字号一张表（D-1）**：NexusStyle 升格全局唯一 type scale；Typography 的 end4 阶梯与
  `Appearance.font` 双轨退役映射（逐键按最近值原则）；全库字面 `pixelSize` 清零。
- **交互反馈合一**：**已落地（2026-11-21，随 D1）**——两份 StateLayer（bar 私有
  end4 枚举版 + ui/ M3 版）合一：end4 枚举版与 StateOverlay 退役，ui/ 版补
  `dragged` 态（press 10 > drag 16 > hover 8 > focus 10）成为唯一正典，
  Workspaces 内联消费；`RippleButton.colBackgroundToggled/ToggledHover` 死属性
  激活为真背景填充、`stateLayerOpacity:1` 隐形压制链删除（全库 25 处手动绕行
  赋值一并清除，四个透明度默认直取 `Appearance.interaction`）；press 0.12→0.10
  对齐契约。门禁 `tests/shell/test_d1_design_unification.py`。
- 来源：caelestia tokens.hpp/appearanceconfig 数值 1:1；end4 motion 参数。
- 验收：契约测试逐值钉死；字面字号/散落色值扫描门禁零残留；probe 全绿；
  托盘 hover 色修复为首个落地验证（浅深两模式截图归作者）。

### D1 Bar 收尾与快修包（2026-11-21 实现落地，机器证据齐，待作者实机验收）

快修四件（原诊断登记见 known-issues，已全部修复；Media 项根因经复刻实验修正）：

- **Media 胶囊两行文字溢出**：复刻实验证明 `Layout.maximumWidth` 参与布局
  implicitWidth 求值，真正机制是 lane 压缩把部件压到比 implicitWidth 窄时
  material 分支（centerIn + 无 fillWidth + 无 clip）不收缩省略。修法：material
  Loader 改 `anchors.fill` + 文本 `fillWidth`（保留 120 帽）+ 根 Item `clip`；
  iNiR 钳制公式不动，默认 min/max 维持 160/300（作者拍板不收窄）。
- **岛水平时钟不居中**：DiIdle 三段式重排（头像左锚 / 时钟簇 `centerIn` /
  状态图标右锚）；probe 钉死 `clockCenterX == faceWidth/2`。
- **DiIdle 通知铃铛处决**：未读 Revealer 块删除；未读唯一归宿 SystemIcons 通知槽
  （默认 8px 圆点、`showUnreadCount` 可配）。边界：`systemIconsElsewhere=false`
  时 idle 面无未读指示（end4 同答案，DiNotifs 实时通知仍在）。
- **托盘箭头 hover 色**：D0 交互反馈合一落地验证项（见 D0 节完成注记）。

部件清账（原 B9.9，2026-11-15 截图审计遗留）：

- **岛媒体面解冻（B-10）**：已落地——`islandShowMediaControls` 三按钮 +
  `islandVisualizerStyle` dots/wave/none（end4 默认 controls off/dots）；
  `WaveVisualizer.qml` 已在 ui/（Dashboard 先行入库）；cava 经
  `IslandVisualizerService` 单进程租约，wave 的 `CavaProcess` 仅在 wave 选中
  且播放时 active。probe 六态矩阵断言全绿。
- **天气接线**：已落地——WeatherBar/Popup 换绑 `WeatherService`（消费租约，
  不建转发别名），`weather` 进白名单；无数据降级 `--°`；日出日落取
  dailyForecast[0]、降雨概率/降水取 hourlyForecast[0]。
- **Visualizer 接线**：已落地——进白名单，probe 断言 lane 挂载可实例化、
  移除后零租约残留。
- **Xkb 核实（结论）**：niri IPC **有**键盘布局数据面——`niri msg -j
  keyboard-layouts` 自 B8.4 起由 `KeyboardLayoutService` 消费，经
  `KeyboardIndicators` 落在 SystemIcons 键盘槽（布局码 + Caps/Num）。独立
  Xkb 部件与该槽同类重复（P3 同类只留一个），**登记不做**。
- **`time.dateFormat` 可配键**：已落地——iNiR 语义（Qt 格式串，默认空回退
  `dddd, dd/MM`），持久化于 PersonalizationConfig `time` 段、经 Config 桥
  暴露，Bar 设置页 Appearance tab 提供 "ddd, dd/MM" 提示的输入行。
- 来源：end4 `DiMedia`/`WaveVisualizer`/`BarConfig`、本树 Weather 三件 fork、iNiR `DateTime`。
- 验收：probe（controls×visualizer 六态、天气租约、visualizer 租约、dateFormat
  随动、media 几何、DiIdle 三段几何）**全绿**；实机截图对照 end4 原图归作者。

### D2 SystemIcons QS 化（hover 展开 + 数据）（2026-11-21 实现落地，机器证据齐，待作者实机验收）

- 方案（D-2）：**已落地**——UtilButton 26↔54px hover 展开骨架（200ms）+ 展开区一行数据
  （音量 %/SSID/蓝牙设备数/低电 %/静音/DND）+ 150ms intent 防误触 + 点击仍开 sidebar；
  键盘指示器维持 26px 固定槽。
- 来源：end4 `UtilButton.qml` 原件骨架 + caelestia bar popouts 数据形态 + dux
  `hoverPopoutDelay` 参数。**登记有意原创**：end4/iNiR 原版均为固定图标流，
  end4 代码中音量百分比文本是 `visible:false` 化石，无完整上游先例。
- 验收：契约测试 `tests/shell/test_d2_system_icons.py`（14 用例全绿）；probe（展开态槽宽 54px、防误触时序、移出收回 26px）；实机 hover 手感、浅深两底色可读性待作者验收。

### D3 岛屿定案评审 + 联动机制试点（暂时放弃，2026-11-21）

> **暂时放弃**（D-6）：三形态收益表与撑大岛试点整体暂缓，恢复另立项（触发条件见
> [delayed-decisions](../llms-wiki/delayed-decisions.md)）；end4 岛为唯一现行形态。
> 以下设计要点留档备查，不占执行位。

- 产出三形态收益表：end4 固定厚度岛（现状默认）/ Clavis 撑大岛 / dux 多模式
  （docked/overlay/floating）。
- **撑大岛作为联动重武器机制验证试点**：clavis Keystone 三窗口架构整抄剪裁——
  全屏交互窗（exclusiveZone −1）+ 贴边细条预留窗（只预留收起态厚度）+ 1×1 键盘窗；
  岛本体为窗内 Item 锚边向屏内生长（500ms 弹性贝塞尔）；窗口级 mask Region 限定输入；
  SDF 融合用 clavis `long_split.frag.qsb`（纯 QML ShaderEffect，不违纯 QML 红线）。
- 定位（D-3）：opt-in 可选风格，默认仍是 end4 岛；试点失败只是少一个风格，主线不动。
- 全屏常驻窗的性能代价进 probe 度量（A 卷口径）。
- 验收：试点实机开合流畅度、输入 mask 正确性（不挡桌面点击）、性能数据写回本页。

### D4 Bar 自定义引擎（dux 程度，五期）——进行中（D4a 实现落地，2026-11-21，机器证据齐，待作者实机验收）

> 目标定案：自定义度对齐 dux-shell（「GUI 设置面板驱动」流派的天花板），轴覆盖
> **布局 / 几何 / 样式 / 行为 / 逐部件实例**五层。架构六件套：schema 分层、默认值
> fallback、最小化写入、版本化迁移、部件目录注册表、属性注入协议。
> **铁原则：所有可调轴的默认值来自 [design-system](../llms-wiki/shell/design-system.md)
> 契约**——用户调整是宪法之上的表达自由，自定义引擎不另立默认审美，高自定义与
> 统一性不冲突。
> 现有基础（升级而非重建）：config.toml 单真相、PersonalizationConfig、
> LayoutDragCoordinator 拖拽、BarComponentsCard 三 lane 卡。
> 不搬：Go 后端、matugen 全量联动、插件市场与 lock（注册表形状留接口即可）、Frame、
> 哥特切角、多合成器修补层。

| 期 | 交付 | dux 来源 |
| --- | --- | --- |
| 期 | 交付 | dux 来源 |
| --- | --- | --- |
| D4a 配置架构与部件目录 | **已落地（2026-11-21）**：`[[bar.configs]]` 数组 schema（lane 混用字符串与 `{id, enabled, ...overrides}` 对象，单条起步）；三层默认回退 + `option()` 单一取值入口 + `widgetEntry` 属性注入协议（首个消费者 Spacer）；`[bar]` 段最小化写入（全默认整段消失、条目坍缩回字符串）；`configVersion` 版本链（v2→v3 + 显式键名映射表，头戳升 3）；部件注册固定三处（`BarWidgetDefaults.js` IDS/DEFAULTS + `ui/BarWidgetCatalog.qml` + `plugins/bar/BarWidgetFiles.js`，契约测试钉死三处 id 集相等）；`divisor`→`separator` 更名（legacy 别名归一）+ `spacer` 一等部件；三份分散目录（`barComponentOptions`/`DashboardBarWidgets`/内联 url map）归一退役；chip 显隐开关 + uid 拖拽身份（重复部件不互吸）。契约 `llms-wiki/shell/bar-config.md`。实现时根因修复：缺失 lane 回退默认 lane（非空数组——fresh config 曾变空 bar）、moveBarComponent 保留「不在场即添加」语义（岛恢复链路） | `SettingsSpec.js` / `BarWidgetDefaults.js` / `WidgetModel.js` |
| D4b 每部件实例配置 | 格式串（时钟日期等）；显隐子项开关（电池 percent/time/power 各自开关那类）；点击动作（预设动作或自定义命令，左/中/右键）+ 滚轮 X/Y 行为；状态级颜色模式（主题/无/自定义 hex × 各状态）；图标模式与覆盖；尺寸/最小宽；同类型多实例多配置 | `BarWidgetDefaults.js` / `XxxOptions.qml` 每部件设置页模式 |
| D4c bar 级几何与样式 | spacing/innerPadding/widgetPadding/inset；长度模式（通栏/百分比居中）；胶囊样式 pills / segments 融合 / flat + 逐部件背景开关 + 裸背景；方角开关；fontScale/iconScale；边框/描边/阴影/透明度（bar 面与部件层分调） | `SegmentRoles.js` 融合角算法 / bar config 60+ 键裁剪 |
| D4d 行为与溢出 | autoHide（delay/strict/全屏隐藏）、点击穿透；溢出系统：每 lane 溢出按钮 + 每部件 `overflowMode`（section/auto/bar/always）+ priority；hoverPopouts（与 D2/D5a 同机制，150ms intent） | `OverflowLayout.js` / HoverController 只借 intent 语义不搬 32KB 实现 |
| D4e 多 bar 与编辑体验 | 任意数量 bar 实例（每条独立全配置 + 屏幕集合 screenPreferences）；per-widget 设置页；行级 reset-to-default 感知（每项知道自己是不是默认态）；密度预设（只迁移用户未改过的键） | `ShellCore` Variants / `WidgetsTab` / `DensityPresets.js` |

验收（各期）：probe 断言几何/持久化/迁移/溢出行为；配置文件最小化快照测试
（只含非默认键，升级用户零感知）；D4e 多屏多 bar 实机排布。

### D5 跨表面统一清账 + 联动层铺开

- **D5a bar 系同窗**：一切从 bar 长出来的弹层（托盘/音量/网络/时钟/快捷设置挂靠）以
  「从源槽位生长 + 胶囊 morph」呈现（StyledPopup 升级）；材质连续规则落地。
- **D5b sidebar 挂靠**：侧栏从 bar/岛生长展开；D3 暂时放弃，默认同规格 morph +
  blur（仍然连续），SDF 融合待 D3 恢复再议。
- **D5c launcher/settings 联动**：orbit launcher 保留自研，但吃出生律（原点锚/
  生长文法/材质连续）；settings 同理。
- **原子正典化清账**：ui/ 单域控件归位（quicksettings 群 15 个、dock/lock/settings
  各若干——归唯一消费单元或升格真共享）；tooltip 双套合一。
- **表面母体补全**：quicksettings/sidebar、lock/session 定母体（候选 caelestia
  sidebar/popouts + iNiR），写入 design-system 来源映射表后不再临时发挥。
- **逐表面过堂**：bar → settings → quicksettings/sidebar → dashboard → launcher →
  lock/session → OSD/通知；每表面过七条检查表（单色源/单几何源/单字号/单交互反馈/
  物理同窗豁免/单数据面/出生律），出截图证据。
- 验收：七条检查表逐表面截图；字面字号与色彩角色消费契约测试全绿。

## 定案登记（D 卷，2026-11-21 作者拍板）

| # | 决策 | 结论 |
| --- | --- | --- |
| D-1 | 字号一张表 | 全库唯一 type scale = NexusStyle 的 M3 表（caelestia/M3 官方数值），bar 一并迁移。**修订 B-2 字号条款**：end4 基线保留几何/间距/圆角，字号升级 M3 |
| D-2 | SystemIcons 交互 | hover 展开 + 数据（26↔54px / 200ms / 150ms 防误触）；登记有意原创 |
| D-3 | 岛屿终局 | end4 岛为默认形态；Clavis 撑大岛为 opt-in 可选风格，兼联动机制试点（D3）；不催办不关闭 |
| D-4 | 旧账处置 | B 卷差异矩阵冻结为 [b9-baseline-matrix](../llms-wiki/archive/b9-baseline-matrix.md)，作 B9 验收依据 |
| D-5 | 抄件宪章 | 分层认亲/四问/换血纪律/出生律为唯一抄法，契约落 design-system；「不移植 blob C++ 形状系统」维持，但纯 QML SDF ShaderEffect 融合不在此限 |
| D-6 | D3 试点处置 | 撑大岛联动试点暂时放弃（恢复触发条件登记 delayed-decisions）；主线转入 D4 五期按既定执行序推进 |

### 沿用定案（B 卷，2026-11-14）

B-1 三 lane 自由拖拽、空 lane 不占位 · B-2 end4 相对几何为准绳（**字号条款已被 D-1
修订**）、Float/Hug/Panel 高度加成、padding/间距/圆角关系照 end4 · B-3 岛的唯一真相是
布局成员 · B-4 Timer/Recording 下架 · B-5 验收只认运行态 · B-6 有上游源一律 cp 原件
再剪裁 · B-7 SysTray Windows 式可见区+overflow · B-8 SystemIcons 抄 UtilButton 按钮语言
（展开交互由 D-2 增补）· B-9 外边距两项设置 · B-10 岛媒体面恢复 end4 原样（执行归 D1）。

## 已确认的历史决策（不重开）

- 自有 C++ 构建链已移除；运行实现收敛为纯 QML/JS/脚本，公开标识统一为 `nyxuri`。
- 原版参考树仅本地查阅，不进运行时；上游历史材料与 Nyxuri 契约分开维护。
- Cava、地图、歌词和窗口预览不属核心能力；Cava 与歌词以按需消费者形态保留
  （媒体面可见且播放时才拉起，停用即释放）。
- 设置双轨终局保留（dashboard 不合并）；Caelestia nexus 原子为 settings 正典；
  blob C++ 形状系统不移植（同色矩形 + blur 近似，见 D-5 澄清）；设置搜索框对齐原版
  纯视觉占位，过滤+深层直通独立立项暂缓（深链机器保留由 Spotlight 通达）。
- 资源策略区分运行时资产、生成文件、缓存和测试 fixture；天气图标用 Material Symbols。
- 文档体系按 [docs-charter](../llms-wiki/docs-charter.md) 分层治理；归档只进不改。

## 后续阶段

- **设置内搜索**（过滤 + 深层直通）独立立项维持暂缓，待独立设计后实施。
- **P6 整体验收与未来移植**（前置：D 卷主体完成）：固定机器与版本基线，验收离线、
  缺插件/设备、锁屏、SIGTERM、目标崩溃和失败恢复；视觉、行为、资源和文档证据齐备
  后才接纳封存功能或多合成器移植。
- T4（可控性与透明化）、T5（多合成器解耦，门禁触发）见根 [ROADMAP](../ROADMAP.md)。
- B 卷遗留的下架件与恢复条件见 [PARKED](plugins/bar/PARKED.md)。

## 门禁

- 每个保留文件必须有真实消费者；每个设置项和动作必须有唯一业务 owner。
- Niri 运行态只允许单一服务状态源；模块不得复制窗口、工作区或输出状态。
- 字面字号与散落色值零残留（契约测试）；同类组件全库一个正典。
- 抄件四步缺「换血」不算完成；新表面/弹层必须过出生律。
- 每阶段完成前源码、测试、资源、部署和文档状态相互一致；测试跳过与环境阻断单独报告。

## 已交付基线

R1–R12、KM4.5/4.6、B8 结构回归、B9.0–B9.7 实现（机器证据齐，验收见积压表）、T3 M0–M2、
主线三卷（KM0–KM5 / G0–S1 / P0–P5）均已按当时标准交付；明细见
[shell-roadmap-ledger](../llms-wiki/archive/shell-roadmap-ledger.md) 与
[roadmap-history](../llms-wiki/archive/roadmap-history.md)，此处不复述。

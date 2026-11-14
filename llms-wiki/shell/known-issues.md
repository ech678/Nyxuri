# 已知问题与暂缓缺口

> Nyxuri Shell 完全处于开发阶段，已知问题较多，外观尚未开发，暂不推荐日常使用。
> 本页只记录「现在哪里是坏的」和「今天跳过了什么」；修一个勾一个，不修也不碍事。
> 架构契约见 [AGENTS.md](../../shell/AGENTS.md)，阶段计划见 [ROADMAP.md](../../shell/ROADMAP.md)。

## 未修复 BUG

- [ ] **下架件与孤儿**：`NetworkSpeed*`/`Weather*`/`DocktoPanel`/
  `LeftSidebarButton` 等依赖 iNiR 单例名的部件仍未接线；`Resources`/`ClockWidget`/
  `BatteryIndicator` 已随 B8.2 基件整抄解冻并进选装集。清单见
  [shell/plugins/bar/PARKED.md](../../shell/plugins/bar/PARKED.md)。

## 基础设施缺口（快速上线时跳过，回来先做这些）

- [ ] **TUI 未接入**：`menus.py` 无 shell 切换菜单，`translations.toml` 无桌面外壳词条；目前只有 CLI `nyxuri shell` 一条路

## 已修复

- [x] **状态图标与外设电池（B9.2，2026-11-14）**：SystemIcons 从裸 Flow 改为七个固定
  26px 槽（hover 胶囊、17px 图标、tooltip、独立点击）；新增 end4 `PeripheralBattery`
  整抄服务与 `Config` 外设阈值；未读徽标并入通知槽。运行态由 `systemIcons` 探针
  断言槽宽/组宽/假外设低电。
- [x] **岛真相与横向时钟（B9.3，2026-11-14）**：`islandInLayout` 取代第二开关，
  `layoutMigrated` 读键修正，通知槽仲裁改看布局成员；idle 头像接 `AvatarService` 并
  加 `person` 兜底（可用 `islandShowAvatar` 隐藏）；横向时钟 `ClockContent` 接入 idle 面
  （`islandHideDate` 落地）。
  运行态由 `islandOff/islandRestored/islandMigration/idleFace` 探针覆盖。

- [x] **无媒体时 Media 组残留空胶囊 + 探针矩阵缺口（2026-11-14）**：Media 隐藏时
  `BarGroup` 仍按 padding 画 10px 空胶囊，lane 的 material/hug/中段胶囊也留 padding。
  新增 `barWidgetVisible` 契约（缺省视为可见），组与三条 lane 胶囊按内容宽度收缩；
  运行态由 `probe-bar.sh` 的 `mediaOnly` 场景在非材质/material 两条路径断言宽度为 0。
  同轮探针从 cornerStyle 1/3/4/5 扩到 0–5，并新增 borderless 四模式覆盖。
- [x] **岛收口与设置空承诺（B8.4/B8.5，2026-11-14）**：OSD 生产者接线（音量/亮度/
  caps/num/布局走 `GlobalStates.osdKind`，`DiOsd` 不再调用不存在的值方法）；
  `KeyboardLockService` 换成 iNiR `KeyboardIndicators` 的 Fork & Trim
  （sysfs LED 聚合 + panel/popup 分离），并新增 `KeyboardLayoutService` 读
  `niri msg -j keyboard-layouts`；SystemIcons/XkbIndicator 整抄 iNiR barM3 版。
  key-cli 退役后原 backend 永远不可用，这是 caps/num OSD 消失的根因。
  `islandEnabled` 真正隐藏岛；`islandSatellite` 替换反掉的 `leftWidget` 天气硬编码；
  媒体面改 end4 点阵；`islandStyle/overlay/position/hoverAction/click*/media*Style/
  keyhole` 全链路退役。`ActiveWindow` 按 end4 重抄（Niri 数据面 + `contentColor`），
  material 判定收敛到 `PersonalizationConfig.barIsMaterial`；cornerStyle 4/5 窗口层
  exclusive/圆角装饰补齐。
- [x] **Bar/Island 无运行态测试（B8.6，2026-11-14）**：新增
  `scripts/dev/probe-bar.sh` + `probe-bar.qml`，隔离 shell 装载 `BarContent`，覆盖
  cornerStyle 1/3/4/5，断言所有 active `Loader.Ready`、无 pending/failed、几何有限且
  中段居中，并扫描 TypeError/ReferenceError/compiled empty；`tests/shell/test_bar_runtime.py`
  消费 JSON，无 Wayland 显式跳过。首轮即撞出：材质/非材质两套 lane 同时实例化部件
  （每屏两个岛、隐藏岛抢 `islandHost`），已改为按 `isMaterial` 门控 Loader。
- [x] **Bar 整抄轮（B8.1–B8.3，2026-11-14）**：`BarGroup`/`BarContent` 重新 `cp` end4
  原件再剪裁（删除 hostScale 压缩链、DI 卫星、重复胶囊角），`groupColor`/`paintBackground`/
  `segmented`/material 4-5 档/右键调色全部接线；`DateTime`、`launcherButton`、
  `powerButton`、`systemIcons` 上岗；`BarWidgetSwitcher*`/`ClippedProgressBar`/
  `Clipped*CircularProgress`/`ResourceUsage` 基件整抄后 `clock`/`systemMonitor`/`battery`
  解冻；`Workspaces.qml` 以 iNiR 876 行原件剪裁为 Niri-only end4 视觉；
  `information` 假部件（映射到不存在的 `Information.qml`，导致默认左栏重复活动窗口）
  从选装集与迁移中删除。冷启动无 compiled empty / TypeError / ReferenceError。
- [x] **cornerStyle 判定不一致**：BarGroup/BarContent/Island/未读徽标统一按
  `cornerStyle === 3 || 4` 走 material；4/5 的 hug/panel 几何随 end4 原件落地。
- [x] **BarComponentLoader 不存在**：`e03c449` 之后 `BarContent` 才是唯一分发点；
  `DashboardBarWidgets` 注释与 `getWidgetUrl` 同步。

- [x] **Bar 中段贴左重叠、部件挤在一起**（2026-11-14）：`Appearance.fontSizeScale`
  未桥接，`hostGap = 6 * undefined → NaN` 污染 `minimumCenterX/maximumCenterX`，
  `centerHostX` 变 NaN 后 `absoluteCenter.x` 落到 0。补 `fontSizeScale=1` + 几何链
  `Number.isFinite` 兜底，空 lane 不再计入 host/gap，压缩态不再把中段钉到最左。
  实机探针复核：2560 屏、259 宽中段 → `centerX=1150.5`（正中）。
- [x] **Style 下拉当前值显示成数字**（2026-11-14）：`SplitMenuButton.currentValue`
  声明为 `string`，整型 3 被转成 `"3"`，与数字 model 值严格比较失败后回落到原值。
  改为非类型化属性 + `String()` 归一比较，菜单勾选态同修。
- [x] **Bar 动画每帧报 createObject of undefined**（2026-11-14）：iNiR 的
  `animation.elementMove*.colorAnimation/numberAnimation` 是 Component 工厂，
  Nyxuri 只留了 duration/type/curve。补齐工厂与 `elementMove`/`elementMoveEnter`
  别名。
- [x] **Divisor/Media/Notification 刷 TypeError**（2026-11-14）：Config 桥缺
  `bar.m3.divider`/`resources`/`indicators`/`verbose`/`clock`，补齐；`CompositorService`
  正名 `CompositorDriver`，删除 `SysTrayMenuEntry` 里不存在的 `buttonColor` 赋值。
- [x] **Timer/Recording 岛面空转**（2026-11-14，按作者决定下架）：provider、
  内联组件、`island stopRecording` IPC、`IslandPage` 录制目录 UI + `FilePickerWindow`、
  manifest 路由与 i18n 词条一并移除；`DiTimers.qml` 留文件待接 `TimerService`。

- [x] **key-cli 依赖彻底废弃与清理**（2026-11-07）：确认并执行纯减法，废弃外部
  AUR 包 key-cli；清理控制面探活诊断与面向用户的安装提示，宿主机卸载后 Shell 各单元
  100% 正常稳定运行，无额外残留。
- [x] **settings 开关全部无反应**（2026-10-17，同日复核发现）：开关派发本身正常
  （状态落记录、`unit switch done`），但桌面纹丝不动——`nyxuri/system/
  shell.py` 的 `probe_running_shells()` 把 `os.getppid()` 一并排除，
  而 shell 的 UnitControlService 派生 nyxuri 时父进程恰是待通知的 qs 实例，
  bridge 探测永远扑空、unit-changed 静默丢失。修为只排除自身（wrapper 以
  `exec qs` 收尾，父进程不可能是 wrapper 脚本残留；非 shell 父进程由
  classify 过滤）。回归测试以真实进程拓扑复现：argv0 伪装的 fake qs → 子进程
  probe，旧代码必败、新代码必过（shebang 脚本会改写 cmdline，须用二进制
  execve；`-c` 须先于 `-p`，否则 CPython 自吞该参数）。
- [x] **desktopcards/sidebars 永久 compiled empty + 自愈无限重试**（2026-10-17，KM4.6 实机
  验收发现）：`settings` 窗口逐个 on/off 时 `shell.desktopcards`、`shell.sidebars`
  反复「enabled but compiled empty」直至放弃。终局根因是重构残留的两条失效相对
  import——文件不存在属硬错误，预热与自愈救不了：① `units/desktopcards/
  DesktopCardCanvas.qml` import `../systemcards/SystemCardPlacement.js`（SystemCards
  模块 KM4.5 解散后真身在 `shared/cards/`）；② `app/cards/SystemCardContent.qml`
  import `../shared/cards/SystemCardCatalog.js` 少一级 `../`（真身 `shared/cards/`），
  经 DrawerGridTile 拖死 sidebars 整条链。两处正名为 `../../shared/cards/` 后恢复。
  同场附带修复：settings `ShellPage.qml` 引用不存在的 `UnitControl` 单例（实名
  `UnitControlService`），每点一次开关刷两条 ReferenceError、开关全部失效。
  保留的两项修正各自独立成立：`qs.app.cards` 进 SlotHost 预热名单（0.3.2 约束①的
  防御性条款）；自愈上限坐实（原 "/2" 是写死字符串，per-unit `failedHeals` 计数、
  超限给决断性 ERROR、unit-changed 清零重新武装）。
- [x] **quickshell 依赖未声明**（2026-10-17 KM4 清算）：根 `catalog.toml` 新增
  `quickshell` 条目（`detect` + `packages_aur`），`deps apps` 菜单与 gen-deps
  optdepends 同源可见；顺带修复 KM3.5 搬家后 PKGBUILD 生成标记 stale 导致
  `gen-deps --update` 静默 no-op 的预存 bug。
- [x] **卸载残留**（2026-10-17 复核）：`state/uninstall.py` 已随 cli 条目清理
  `~/.local/bin/nyxuri-shell` 软链（含 `/shell/bin/` 旧路径形态）；沙箱实证
  `nyxuri uninstall --all` 双软链清零。登记时该代码尚未存在，现已过时。

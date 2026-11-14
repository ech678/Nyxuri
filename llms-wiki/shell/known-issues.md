# 已知问题与暂缓缺口

> Nyxuri Shell 完全处于开发阶段，已知问题较多，外观尚未开发，暂不推荐日常使用。
> 本页只记录「现在哪里是坏的」和「今天跳过了什么」；修一个勾一个，不修也不碍事。
> 架构契约见 [AGENTS.md](../../shell/AGENTS.md)，阶段计划见 [ROADMAP.md](../../shell/ROADMAP.md)。

## 未修复 BUG

- [ ] **Bar 工作区/活动窗口未真整抄**（2026-11-14 审计）：`Workspaces.qml`（88 行）
  与 `ActiveWindow.qml`（81 行）是自研缩水，不是 `references/iNiR/modules/ii/bar/`
  的 876 行原件；`barM3/` 里只有转发门面。`NetworkSpeed*` 同类。复现：看工作区仍是
  旧圆点样式，无应用图标/数字/indicatorStyle。
- [ ] **岛设置大半是空承诺**（2026-11-14 审计）：`islandStyle`/`islandOverlay`/
  `islandPosition`/`islandHoverAction`/`islandLeftClickAction`/`islandMiddleClickAction`/
  `islandMedia*Style`/`islandKeyholeCard`/`islandCapsLockOsd`/`islandNumLockOsd` 全库
  **零运行时消费者**，只有 `islandHideDate` 生效。`BarGroupStylePopup.qml` 零消费者
  （D5 右键就地调色未接线）。
- [ ] **cornerStyle 6 选 4 落空**：设置提供 Hug/Floating/Plain/Material/Material hug/
  Panel，实现只覆盖 0–3；4/5 落入非 material 分支。`isMaterial` 判定也不一致
  （`BarGroup` 只认 3，`DynamicIsland` 认 3/4）。
- [ ] **选装集缺口**：`barComponentOptions` 无 `island`/`clock`，中段纯岛形态只能在
  配置里手写 `["island"]`；`clock` 已于 2026-11-14 从 `barComponentIds` 移除。
- [ ] **下架件与孤儿**：`Resources`/`ClockWidget`/`BatteryIndicator`（缺
  `BarWidgetSwitcher*`/`ClippedProgressBar`/`ResourceUsage`，上游参考树里也没有）
  以及一批依赖 iNiR 单例名的部件——清单与恢复条件见
  [shell/plugins/bar/PARKED.md](../../shell/plugins/bar/PARKED.md)。

## 基础设施缺口（快速上线时跳过，回来先做这些）

- [ ] **Bar/Island 无运行态测试**（2026-11-14）：`tests/shell/test_bar_end4.py`、
  `test_island_end4.py` 全是 `assertIn("leftMaterialPill", source)` 这类字符串断言；
  432 项全绿也拦不住布局 NaN 与 compiled empty。修法：`qs -p <fixture>` 逐件装载
  断言 `Loader.Ready` + 布局求值数值，纳入 shell 测试。
- [ ] **TUI 未接入**：`menus.py` 无 shell 切换菜单，`translations.toml` 无桌面外壳词条；目前只有 CLI `nyxuri shell` 一条路

## 已修复

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

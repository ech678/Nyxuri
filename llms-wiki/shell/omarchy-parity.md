# Omarchy 资产清点（S1 整抄执行清单）

> **战略定调：留我们的皮，换 Omarchy 的心**。
> - **皮（The Skin，誓死守护）**：Clavis / Caelestia 的现代视觉、MD3 几何精度、流体动画、NexusStyle Token、Niri 原版合成器驱动（`CompositorDriver` + `NiriDriver`）、Python 引擎与账本（单一开关真相）。
> - **心（The Heart，代码物理整抄）**：Omarchy 经过实战检验的插件微内核调度中枢——806 行 `PluginRegistry.qml`（进程守护、inotify 实时热监听、分段输出解析流）、7 个 `Plugin*Api.qml` 安全隔离门面、`BarWidgetRegistry.qml` 二级挂载、按需召唤（summon/hide）生命周期。
> - **缝合切口（最小侵入适配）**：
>   1. **插件目录**：Omarchy `~/.config/omarchy/plugins` ➔ Nyxuri `~/.local/share/nyxuri/plugins/<id>/`（XDG 数据物理隔离，守住不变量 1）；
>   2. **清单载体**：Omarchy `manifest.json` ➔ Nyxuri `manifest.toml`（单文件、已走通的 `Toml.parse` 与 `PluginManifest.js`）；
>   3. **开关状态**：删除 Omarchy 原版写 `shell.json` 的逻辑，统一读取 `StateProjection` / 引擎账本；
>   4. **宿主装配**：`SlotHost.qml` 吸收 Omarchy 的 Loader property 注入模式（`item.pluginRegistry = ...`, `item.shell = ...`, `item.manifest = ...`）。

**基准**：`0740d1b`（与 references.md 登记一致；`shell/` + `docs/` +
`agents/skills/` + `manual/32-shell-plugins.md` 四部分，3.7M）。

## 裁决三栏

- **照抄**：语义 1:1 落地，允许机械改名（PascalCase→小写）与换载体（JSON→TOML），
  行为契约不许走样。
- **改造**：以参考树原件为基线物理拷入，按本站既有契约（账本开关、niri、五层边界）做定向剪裁；
  偏差点必须在本页登记理由。
- **拒绝**：不进本站；理由与出处必须写明，防止后人翻案时找不到当时的决策。

S1 开工执行以本页裁决为机器验收基准（全局门禁 4）。

## A. 代码资产（`shell/`）

| 资产 | 规模 | 内容 | 服务站点 | 裁决 | 理由与落地动作 |
| --- | --- | --- | --- | --- | --- |
| `services/PluginRegistry.qml` | 806 行 | 三方目录扫描、enable/disable 经 shell.json、trust/capabilities、clone/卸载、本地变更热重载（inotifywait + 150ms timer）、`pluginLoadFailed` 信号、`watcherReaper` | S1 核心中枢 | **改造（以原版为基准物理拷入）** | 物理复制至 `shell/services/` 作为基线，保留 `localPluginWatcher`、`watcherReaper`、`parseScanOutput` 与能力标记；剪裁点：扫描路径换 `~/.local/share/nyxuri/plugins/<id>/`，调用已定稿的 `PluginManifest.js` (TOML)，开关改读 `StateProjection`，删除原版 `shell.json` 写入代码。 |
| `services/PluginRegistryApi.qml` | 32 行 | 注册表暴露给插件的 API 面（installedPlugins、entryPointUrl） | S1 门面 | **照抄** | 物理复制至 `shell/services/`，为插件提供只读安全门面，隔绝宿主私有方法与未授权操作。 |
| `services/PluginShellApi.qml` | 70 行 | 宿主 API（summon / hide / toggle / isPluginOpen 等） | S1 门面 | **改造（原版整抄后对接）** | 物理复制至 `shell/services/`，暴露受限宿主召唤与控制门面，底层动作桥接 `ActionGateway`。 |
| `services/PluginBarStateApi.qml` | 23 行 | bar 状态 API（只读状态投影） | S1 门面 | **照抄** | 物理复制至 `shell/services/`，状态栏状态只读门面，供小部件安全感知桌面状态。 |
| `services/PluginAppLibraryApi.qml` | 46 行 | 应用库 API | S1 门面 | **照抄** | 物理复制至 `shell/services/`，应用库搜索门面，供启动器/菜单类插件调用。 |
| `services/PluginBarWidgetRegistryApi.qml` | 24 行 | bar widget 注册 API | S1 门面 | **照抄** | 物理复制至 `shell/services/`，向状态栏小部件暴露注册接口。 |
| `services/PluginFirstPartyServiceApi.qml` | 53 行 | 一方服务 API | S1 门面 | **照抄** | 物理复制至 `shell/services/`，一方插件受信任服务访问门面。 |
| `services/BarWidgetRegistry.qml` | 49 行 | widget 级二级注册表（widget 也是插件） | S1 小部件 | **照抄** | 物理复制至 `shell/services/`，管理小部件二级注册与槽位映射。 |
| `Ui/PluginBarApi.qml` | 100 行 | widget 侧持有的 bar API 对象（property 注入，非单例） | S1 小部件 | **照抄（入 `ui/`）** | 物理复制至 `shell/ui/PluginBarApi.qml`，状态栏注入对象。 |
| `Commons/IpcRegistry.qml` + `Commons/ShellIpc.qml` | 77+12 行 | IPC 面注册与分发骨架 | S1 IPC | **改造** | 物理复制至 `shell/commons/`，与 Nyxuri 既有 `shell --action` 通道核对对齐，支持插件自带 IPC target 动态注册。 |
| `plugins/*/manifest.json` + `widgets/*.manifest.json` | — | 协议字段实样全集；widget 微 manifest 形态 | S1 协议校验 | **改造（换载体 TOML）** | 字段语义 1:1 对位，载体统一使用 `manifest.toml`，S0-2/S0-3 已定稿。 |
| `shell.qml` 宿主装配模式 | 1959 行 | property 注入服务实例、`summon` / `hide` 按需召唤机制、`reloadPlugins` | S1 宿主装配 | **改造** | `SlotHost.qml` 吸收其 Loader 门面属性注入模式（`item.pluginRegistry = ...`, `item.shell = ...`）与按需 summon 装载，取代当前无脑全量静态 Loader。 |
| `plugins/dev-gallery` | — | Ui 组件视觉画廊插件（契约可视化） | 参考 | **拒绝** | 外部组件画廊，非核心生命周期，纯本地参考不进生产。 |

## B. 协议文档（`docs/` + `manual/32` + `agents/skills/`）

| 文档 | 内容 | 服务站点 | 裁决 | 理由与落地动作 |
| --- | --- | --- | --- | --- |
| `docs/omarchy-shell.md` | 插件 manifest、三方安装、IPC、shell.json、theme tokens、custom bar modules | S1 协议真值 | **照抄** | 作为 S1 协议字段、IPC 语义与门面特性的权威真值。 |
| `manual/32-shell-plugins.md` | 用户视角：查看 / 开关 / git 添加 / 自写 / 分享 | S1 动词语义 | **照抄** | 规范 `nyxuri add / remove / update` 的用户行为契约与终端交互确认。 |
| `agents/skills/shell-dev.md` | 开发契约：plugin contract、IPC、无轮询状态同步 | S1 插件作者契约 | **照抄** | 作为未来第三方插件编写者的契约规范。 |
| `docs/file-layout.md` | 仓库→安装路径映射 | S1 落位 | **改造** | 第三方插件物理落位改造为 `~/.local/share/nyxuri/plugins/<id>/`。 |
| `docs/lifecycle-dispatch.md` | 生命周期命令分发 | S1 动词路由 | **改造** | 生命周期命令分发由 Python 引擎承担，对接所有权账本与快照。 |
| `docs/testing.md` | 测试套件契约（base-test.sh） | S1 审计扩展 | **改造** | 将其测试与审计边界吸收进 `audit-lifecycle.py`。 |
| `docs/update-process.md` | 更新流程（状态协调、迁移、回退护栏） | S1 update | **改造** | `update` 命令实现 diff 预览、拒绝非 fast-forward，校验失败咬合引擎快照自动回退。 |

## C. Hyprland 负空间地图(S0-5 核对完毕,2026-11-01)

Omarchy 是 Hyprland 宿主,其合成器耦合点即「插件化 shell 里合成器假设藏在哪」
的全集地图。S0-5 已按此清单逐组核对完毕,落 **CompositorDriver 面 +
NiriDriver 首驱动**(`services/CompositorDriver.qml` 单例投影 +
`services/NiriDriver.qml` 实现)。**本站代码经 grep 证实零
`Quickshell.Hyprland` import**(`hypr` 字样仅剩 `hyprpicker` 外部取色工具
依赖与 end-4 出处注释)。

触点 30 文件(`shell/` 内 `hypr` 命中,按层分组)与核对判定:

| Omarchy 触点组 | 本站对位 | 判定 |
| --- | --- | --- |
| Commons:`Border` `InputDevices` `Style` | `commons/` 纯展示层,色板/尺寸全注入 | 不适用(纯展示无触达) |
| Ui:`KeyboardPanel` `OverlayWindow` `PopupCard` `ScreenMoveRemap` `Toggle` `ToggleSwitch` | `ui/` 原子控件库,不触合成器 | 不适用(同上) |
| bar `Workspaces` / `Bar` `BarModel` | `CompositorDriver.workspaces`(socket 事件流) | **覆盖** |
| bar `KeyboardLayout(.qml/Model)` | 本站无键盘布局 widget | 不适用(事件链零消费,随 S0-5 处决) |
| dock `Dock` `DockWindow` | `DockService`/`DockSurface` → 驱动 windows/searchWindows | **覆盖**;minimize 走能力位**降级**(`supportsMinimize: false`,上游 niri 无此 IPC) |
| lock `LockView` `Service` | session-lock Wayland 协议,不经合成器 IPC;idle 电源走 `setMonitorsPower` | **覆盖**(电源路径) |
| menu `MenuModel` | 全局菜单走 niri binds(`niri-actions.json`)与 keystone | 不适用 |
| notifications `Service` | Wayland notification 协议 | 不适用 |
| panels/monitor `Panel` | 驱动 `outputs` / `outputSnapshot()` | **覆盖** |
| services `media` `nightlight` `remote-session` | MPRIS / wlr-gamma / 无此功能 | 不适用(非合成器协议) |
| 宿主 `BackgroundIntro` `BackgroundSwitch` | `WallpaperSceneService` → 驱动工作区/窗口状态 | **覆盖**;视差走 `setFloatingParallaxOffsets` 桩**降级**(上游 niri 无此 IPC) |
| 宿主 `BrightnessKeys` | `BrightnessService.currentOutput` ← 驱动 | **覆盖** |
| `shell.qml` 宿主 | `AppShell` overview 意图 → `toggleOverview()`;logout → `quitSession()`(execDetached,niri msg 真相在驱动) | **覆盖** |

**驱动接口缺口(本次勘察暴露并补齐)**:
- `setMonitorsPower(off, callback)` —— 带 exit-code 回调的受管执行
  (IdleService 原先绕过协议单例直接起 `niri msg` 进程);无回调形态 =
  execDetached(teardown 时必须脱离宿主存活)
- `quitSession()` —— 原 ActionGateway 硬编码 argv 收编
- `compositorVersion/Ready/Error` —— 原 BlurService 私有 `niri --version`
  探针收编(版本**解释**留在消费域:blur 需要 ≥ 26.4 是 blur 的知识)

**S0-5 处决面**(零消费者,搬家时处决而非搬运):工作区导航动词全家
(focusColumn*/moveColumn*/maximizeColumn/consume/expel/setColumnWidth/
switchLayout 等——合成器 binds 直接执行 `niri msg`,不经 shell)、键盘布局
状态链、foreign-toplevel 映射全家(sortToplevels 等)、MRU、displayScales、
socket 版 quit/powerOff/powerOn(被进程版动词取代)。

**key-cli 收敛判定(实勘修正)**:ROADMAP 原句「key-cli 收敛进一个驱动」,
实勘后判定——key-cli 命令真相已单源于 `app/Paths.qml` 的 `stableKey`
(`NYXURI_KEY` 重定向),9 个消费文件(SystemMonitor/KeyboardLock/
FileSearch/Spotlight tool/Recording 等)是各自域的流管理与生命周期,
塞进合成器驱动会造上帝对象、违反「新抽象必须减少复杂度」门禁。收敛点
= `Paths.stableKey` 唯一命令源(既有事实),驱动不重复登记;此判定如需
翻案,出入口在本页。

**登记例外(niri 字面量允许存在,非驱动面)**:
`scripts/system/niri_config.py` + `display_preview.py`(合成器**配置管理**
域,直连 socket 是其本职)、`niri-actions.json`(binds 真值,S0-2 定稿)、
词典/文案中的事实陈述(如 "Niri session not detected")。
契约焊接:`tests/shell/test_shell_architecture.py`
`test_r4c_niri_single_runtime_entry`(NiriService 死刑 + argv 白名单 +
双文件契约)与 `shell/scripts/dev/audit-lifecycle.py`(驱动 argv 豁免)。

引擎侧(Python)同站收编:`nyxuri/compositors.py` 注册表吃掉
`SUPPORTED_WMS` 元组、安装器 WM radio 特判与 doctor 三处字面量
(T5 前置兑现,见 delayed-decisions)。

## D. 预裁决项（作者已拍板，出处可溯）

| Omarchy 设计 | 裁决 | 出处 |
| --- | --- | --- |
| 开关状态记在 shell.json（`plugins[]` / `disabledPlugins[]` / bar layout 引用） | **拒绝**：单一开关真相在引擎账本 | delayed-decisions「开关状态存储」 |
| manifest 载体 JSON | **拒绝**：TOML 单文件，彻底换代零兼容 | ROADMAP S0「manifest 载体定案」 |
| widget 设置值与 bar 布局塞 shell.json | **拒绝**：settings schema 进 manifest（S0-3b 已定稿 controls 词表）+ 值落宿主 PluginSettings 存储；bar 布局落点已定稿（PersonalizationConfig 外观轴，见 delayed-decisions「开关状态存储」） | ROADMAP S0「shell.json 非开关部分不跟」+ S0-3 收口 |
| Hyprland 合成器耦合（workspace/lock corners/dock 布局） | **拒绝**：CompositorDriver 面 + niri 首驱动 | ROADMAP S0-5 |
| 安装执行包内代码 / install hook / sudo | **拒绝**（S1 安全立场：明说不沙箱但不做安全剧场；三方 v1 拒钩子） | ROADMAP S1 |

## S1 动词 ↔ 资产映射（开工首日按此过堂）

| 动词 | 首要参考 |
| --- | --- |
| `add <git-url>` | A·PluginRegistry 三方扫描 + `docs/omarchy-shell.md`「Installing a third-party plugin」+ `manual/32`「Adding a plugin from git」 |
| `remove` | A·clone/卸载 + 本站 PR #148 所有权账本（非 Omarchy 素材，回植清单见 ROADMAP 分支策略） |
| `update` | `docs/update-process.md` + 咬合引擎快照 |
| `doctor` / `validate` | A·validateManifest 语义 + `docs/testing.md` |
| trust / 能力声明 | A·trustedCapabilities / capabilities / stampHostCapabilities（改造：v1 三方拒钩子） |
| `on / off / use / list` | 本站既有引擎动词，Omarchy 无对应（其开关即 shell.json，已预裁决拒绝） |

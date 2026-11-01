# Omarchy 资产清点（S1 整抄执行清单）

> 本页把根 [ROADMAP](../../ROADMAP.md) 的「整抄裁决」拆成逐文件可勾选的台账：
> 每一项 Omarchy 资产过堂一次，落一个裁决，S1 按表执行。
> 参考树怎么来、基准提交与重现命令见 [references](references.md) §4；
> 本页只回答「抄什么、怎么抄、什么不抄」。manifest 字段权威在
> [manifest-schema](../manifest-schema.md)，本页不改字段定义。

**基准**：`0740d1b`（与 references.md 登记一致；`shell/` + `docs/` +
`agents/skills/` + `manual/32-shell-plugins.md` 四部分，3.7M）。

## 裁决三栏

- **照抄**：语义 1:1 落地，允许机械改名（PascalCase→小写）与换载体（JSON→TOML），
  行为契约不许走样。
- **改造**：保留设计意图，按本站既有契约（账本开关、niri、五层边界）重实现；
  偏差点必须在本页登记理由。
- **拒绝**：不进本站；理由与出处必须写明，防止后人翻案时找不到当时的决策。

状态列留「待裁」表示 S1 尚未过堂；**任何「已完成」的整抄声明以本页表格填满
且测试绿为准**（全局门禁 4）。

## A. 代码资产（`shell/`）

| 资产 | 规模 | 内容 | 服务站点 | 裁决 | 理由 |
| --- | --- | --- | --- | --- | --- |
| `services/PluginRegistry.qml` | 806 行 | 三方目录扫描（`~/.config/omarchy/plugins`）、enable/disable 经 shell.json、trust/capabilities（first-party vs `clonedFrom`）、clone/卸载、本地变更热重载（150ms timer）、`pluginLoadFailed` 信号 | S1 add/remove/update/doctor | 待裁 | — |
| `services/PluginRegistryApi.qml` | 32 行 | 注册表暴露给插件的 API 面 | S1 | 待裁 | — |
| `services/PluginShellApi.qml` | 70 行 | 宿主 API（summon 等） | S1 | 待裁 | — |
| `services/PluginBarStateApi.qml` | 23 行 | bar 状态 API | S1 | 待裁 | — |
| `services/PluginAppLibraryApi.qml` | 46 行 | 应用库 API | S1 | 待裁 | — |
| `services/PluginBarWidgetRegistryApi.qml` | 24 行 | bar widget 注册 API | S1 | 待裁 | — |
| `services/PluginFirstPartyServiceApi.qml` | 53 行 | 一方服务 API | S1 | 待裁 | — |
| `services/BarWidgetRegistry.qml` | 49 行 | widget 级二级注册表（widget 也是插件） | S1 | 待裁 | — |
| `Ui/PluginBarApi.qml` | 100 行 | widget 侧持有的 bar API 对象（property 注入，非单例） | S1 | 待裁 | — |
| `Commons/IpcRegistry.qml` + `Commons/ShellIpc.qml` | 77+12 行 | IPC 面注册与分发骨架 | S1 / 对照单元自有 IPC | 待裁 | — |
| `plugins/*/manifest.json`（32 份）+ `widgets/*.manifest.json`（8 份） | — | 协议字段实样全集；widget 微 manifest 形态 | S1 协议校验 | 待裁 | — |
| `shell.qml` 宿主装配模式 | 1959 行 | property 注入服务实例（相对 import 单例状态分裂的教训）、`reloadPlugins`、内置 fallback config | S1 热重载设计 | 待裁 | — |
| `plugins/dev-gallery` | — | Ui 组件视觉画廊插件（契约可视化） | 参考 | 待裁 | — |

## B. 协议文档（`docs/` + `manual/32` + `agents/skills/`）

| 文档 | 内容 | 服务站点 | 裁决 | 理由 |
| --- | --- | --- | --- | --- |
| `docs/omarchy-shell.md` | 插件 manifest、三方安装、IPC、shell.json、theme tokens、custom bar modules | S1 协议真值 | 待裁 | — |
| `manual/32-shell-plugins.md` | 用户视角：查看 / 开关 / git 添加 / 克隆内置 / 自写 / 分享 | S1 动词语义 | 待裁 | — |
| `agents/skills/shell-dev.md` | 开发契约：plugin contract、IPC、无轮询状态同步 | S1 插件作者契约 | 待裁 | — |
| `docs/file-layout.md` | 仓库→安装路径映射 | S1 落位（`~/.local/share/nyxuri/plugins/`） | 待裁 | — |
| `docs/lifecycle-dispatch.md` | 生命周期命令分发 | S1 动词路由 | 待裁 | — |
| `docs/testing.md` | 测试套件契约（base-test.sh） | S1 `audit-lifecycle.py` 扩展 | 待裁 | — |
| `docs/update-process.md` | 更新流程（状态协调、迁移、回退护栏） | S1 update（diff 预览 / 拒非 ff / 自动回退） | 待裁 | — |

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

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

## C. Hyprland 负空间地图（S0-5 专用）

Omarchy 是 Hyprland 宿主，其合成器耦合点即「插件化 shell 里合成器假设藏在哪」
的全集地图。S0-5 抽 CompositorDriver 面时按此清单核对 NiriService 覆盖度，
缺口即驱动接口。**本站代码经 grep 证实零 `Quickshell.Hyprland` import**
（`hypr` 字样仅剩 `hyprpicker` 外部取色工具依赖与 end-4 出处注释）。

触点 30 文件（`shell/` 内 `hypr` 命中，按层分组）：

- **Commons**：`Border` `InputDevices` `Style`
- **Ui**：`KeyboardPanel` `OverlayWindow` `PopupCard` `ScreenMoveRemap` `Toggle` `ToggleSwitch`
- **plugins**：bar（`Bar` `BarModel` + widgets `KeyboardLayout(.qml/Model)` `Workspaces`）、
  dock（`Dock` `DockWindow`）、lock（`LockView` `Service`）、menu（`MenuModel`）、
  notifications（`Service`）、panels/monitor（`Panel`）、
  services（`media` `nightlight` `remote-session(.qml/Model)`）
- **services + 宿主**：`BackgroundIntro` `BackgroundSwitch` `BrightnessKeys` `shell.qml`

## D. 预裁决项（作者已拍板，出处可溯）

| Omarchy 设计 | 裁决 | 出处 |
| --- | --- | --- |
| 开关状态记在 shell.json（`plugins[]` / `disabledPlugins[]` / bar layout 引用） | **拒绝**：单一开关真相在引擎账本 | delayed-decisions「开关状态存储」 |
| manifest 载体 JSON | **拒绝**：TOML 单文件，彻底换代零兼容 | ROADMAP S0「manifest 载体定案」 |
| widget 设置值与 bar 布局塞 shell.json | **拒绝**：settings schema 进 manifest + 状态投影存储；布局落点随 S0-3 定稿登记 | ROADMAP S0「shell.json 非开关部分不跟」 |
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

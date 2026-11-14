# Delayed Decisions — 暂缓事项与已定决策

> 本页记录暂缓事项的触发条件，并保留已作出的架构决策，避免重复讨论。

## 仍延迟（触发条件未到 / 主动暂缓）

| 事项 | 触发条件 | 当前决策 |
|---|---|---|
| **硬件适配 Overlay**（NVIDIA / AMD / 多显示器…） | 出现多个明确的硬件适配需求 | 当前无自动驱动补丁，不引入硬件 overlay；应用预设底版继承（Base Overlay）保持独立。历史案卷见 [archive/nvidia-patch](archive/nvidia-patch.md) |
| **插件服务声明字段**（manifest 声明 systemd unit 等服务副作用） | 出现跨插件或系统级服务效果的真实需求 | **已部分落地（KM3）**：副作用走插件钩子（`post_install` / `post_remove`）+ `[privilege]` 声明（greeter 案例：服务启停在钩子内部，manifest 只声明事实）。独立服务字段仍不设，出现真实需求再议。详见 [plugin-model](plugin-model.md) §4 与 [manifest-schema](manifest-schema.md) |
| **多合成器 (Multi-WM) 驱动抽象**（原 mango-adaptation 页的债务登记，KM3.5 并入） | 第三个合成器（Hyprland/Sway）接入前必须收编，禁止再往注册表外的角落塞字面量 | **前置已兑现（S0-5，2026-11-01）**：QML 侧 `CompositorDriver` 面 + `NiriDriver` 首驱动（niri 方言锁定单文件，触点核对表见 [omarchy-parity](shell/omarchy-parity.md) §C）；Python 侧 `nyxuri/compositors.py` 注册表吃掉 `SUPPORTED_WMS` 元组、`installer/menus.py` radio 特判、`sysdoctor.py` 三处 `("mango","niri")` 字面量与 `theme.py` 的 reload argv。第三合成器 = 注册表加一行 + 新 QML 驱动，消费者零改动。不属于债务：`plugins/mango/` 整目录（插件形态）、theme 的 `mmsg` 探针、`/home/user` 占位符渲染 |
| **dashwindow 手写目录接注册表**（S0-3 拍板暂缓） | S1 第三方插件实际携带 settings schema 入场，或 schema 通用渲染器（S0-3b）验证成熟后重估收益 | dashboard 轨的 `DashboardSettingsCatalog`（版面）与 `SettingsControlCatalog`（控件 get/set 注册表）保持手写真值：它们是 dashboard 轨对 PersonalizationConfig 外观轴的**表现层编排**，与 manifest 路由表不同源不同义；在 schema 渲染器刚落地、存量零转换时先行迁移顺序颠倒。收敛方向：简单控件逐步改由 manifest `controls` 声明、dashboard 卡片从注册表取值 |

## 这次重构已落地（主动覆盖延迟）

| 事项 | 原触发 | 实际 |
|---|---|---|
| **CLI 菜单与流程分离** | 阶段二职责收束 | `cli.py` 保留命令路由，`menus.py` 管菜单，`workflows.py` 管安装与更新编排 |
| **形态槽位轴与底版继承** | 形态差异细粒度化、按需局部替换 | **已落地**（R0-2 并轨为形态字段）。`atomic_replace_item` 支持底版继承；`manifest.toml` 在 `[forms]` 单节声明槽位轴（如 Niri 的 `effects` 与 `glow` 均为独立热插拔轴，无需重载全部配置）。详见 [forms](forms.md) 与 [manifest-schema](manifest-schema.md) |
| **子目录分组**（deploy/state/modules 子包） | >28 文件 或 某子领域 >5 文件 | **已做**。重构前 17 个 .py（< 28 触发未到），但为贯彻子包架构目标主动拆了四个子包。详见 [archive/subpackages](archive/subpackages.md) |
| **doctor 形态漂移检查** | 形态系统落地后即加 | **已加** `_check_form_drift`（R0-2 正名）：扫所有插件的活动形态是否还在仓库/用户形态目录，给汇总。平时不 update 也能在 doctor 撞见"你的 kitty transparent 形态已不在上游"。符合扩展指南（写 `_check_xxx` append 到 `DOCTOR_CHECKS`，不碰 `run_doctor`） |

## `manifest.toml` 字段契约

全可选字段参考与边界契约见唯一权威页 [manifest-schema](manifest-schema.md)。

## 被拒绝的规则（原 agent-rules-provenance 页收录，拒绝即决策）

完整事故溯源与回归映射见 [archive/agent-rules-provenance](archive/agent-rules-provenance.md)。
经评估明确拒绝、不得反复提出的：用户 drop-in app 目录、manifest 声明 doctor 项/i18n 键、
stable+git 双 AUR 包、Nix 式纯函数引擎、按 PCI 设备选驱动变量、`.nyxignore`、
安装方式优先级表、`preset diff`、`detect` 前缀 DSL（详见 [manifest-schema](manifest-schema.md) 边界节）、
启动期 `Qt.createComponent` 预热救 qs-import 装载、以升级 Quickshell 修 qs-import 装载缺陷
（S0-0 双证：预热 0/20、master 逐格同行为，详见 [shell/loader-form](shell/loader-form.md)）。

## 架构重塑卷定案与落选（2026-10-31，随 ROADMAP 重置登记）

| 事项 | 裁决 | 理由与落选 |
|---|---|---|
| 插件概念定名 | **Plugin / 插件**；三词术语收敛为插件 · manifest · 账本 | 与 Omarchy 协议同词、中文零学习成本。落选：格/Cell（几何味足，输给同词红利）、Mod/模组（游戏味 + QML module 缩写撞词）、积木/Brick（物是活的，隐喻呆板）、星/Star（诗意越界）。「单元」中文语感不佳（作者裁决） |
| 形态轴不命名 | 由 `use` 动词承载，不设名词 | 词越少越和谐；预设 + 零件合并为形态字段（ROADMAP R0-2） |
| QML 侧插件协议 | 整包采纳 Omarchy 协议与骨架（目录小写化），不引任何第三方框架 | 同生态（Quickshell 0.3.2）实跑验证；pluggy / stevedore 管 Python-import 式扩展，与「声明 + 文件 + 钩子」形状不符；Caelestia C++ Blobs 延续不移植裁决 |
| Python 侧插件框架 | 不建框架 | 引擎即插件管理器本体，一套协议两个运行时；entry points（stdlib）为预留通道，第二个真实用例出现才建；pkg 后端走窄驱动（pacman/apt） |
| 插件沙箱 | 不做运行时沙箱 | 插件是用户信任的代码，明说不沙箱、不做安全剧场；替代 = 第三方 v1 拒绝钩子 + 能力声明静态审计 |
| **开关状态存储** | 不抄 Omarchy `shell.json` | 单一开关真相已在本引擎账本，不留第二本账。widget 设置值与 bar 布局的落点随 S0-3 定稿（2026-11-01）：**bar 三轨布局 = PersonalizationConfig 外观轴（现状即终态）**；**schema 控件值 = 宿主 `PluginSettings` 存储（`~/.config/nyxuri/plugin-settings.json`，键 `<pluginId>.<key>`）**；dashboard 网格版面（Catalog 分区/卡序）= dashwindow 表现层数据，非用户状态 |
| v1 非目标 | 插件间依赖声明、schemaVersion 迁移框架均不做 | 包依赖走 manifest packages、运行冲突走槽仲裁已覆盖；未知版本直接拒绝 |
| 导入语义 | 配置导入与插件导入两条线永不混合 | 用户已有配置走保留策略（carry / vault）；第三方插件走 add/validate/remove |

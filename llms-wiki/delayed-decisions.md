# Delayed Decisions — 留待触发条件 vs 已落地

> §11 列的是"真正留待触发条件的事项，已做的不列"。这次重构落地了一部分，这里**诚实区分**
> 哪些仍延迟、哪些已做。

## 仍延迟（触发条件未到 / 主动暂缓）

| 事项 | 触发条件 | 当前决策 |
|---|---|---|
| **硬件适配 Overlay**（NVIDIA / AMD / 多显示器…） | 出现多个明确的硬件适配需求 | 当前无自动驱动补丁，不引入硬件 overlay；应用预设底版继承（Base Overlay）保持独立。详见 [nvidia-patch](nvidia-patch.md) |

## 这次重构已落地（主动覆盖延迟）

| 事项 | 原触发 | 实际 |
|---|---|---|
| **CLI 菜单与流程分离** | 阶段二职责收束 | `cli.py` 保留命令路由，`menus.py` 管菜单，`workflows.py` 管安装与更新编排 |
| **通用零件插槽与底版继承** | 预设差异细粒度化、按需局部替换 | **已落地**。`atomic_replace_item` 支持底版继承；`.module.toml` 支持 `[parts.<slot>]` 声明通用零件插槽（如 Niri 的 `effects` 与 `glow` 均为独立热插拔零件，无需重载全部配置）。详见 [preset-mechanism](preset-mechanism.md) 与 [manifest-schema](manifest-schema.md) |
| **子目录分组**（deploy/state/modules 子包） | >28 文件 或 某子领域 >5 文件 | **已做**。重构前 17 个 .py（< 28 触发未到），但为贯彻 §13 目标结构主动拆了四个子包——有意识覆盖 §11 的延迟决策。详见 [subpackages](subpackages.md) |
| **doctor 预设漂移检查** | preset 系统落地后即加 | **已加** `_check_preset_drift`：扫所有 app 的 active 预设是否还在仓库/用户预设目录，给汇总。平时不 update 也能在 doctor 撞见"你的 kitty 透明预设已不在上游"。符合 §4 扩展指南（写 `_check_xxx` append 到 `DOCTOR_CHECKS`，不碰 `run_doctor`） |

## `.module.toml` schema（字段全可选，无文件 = 全默认）

详见 [manifest-schema](manifest-schema.md)。如 fastfetch 这种"目录名=二进制名=单包=无例外"的直接不写 manifest。kitty 仅声明 `[presets] reload` 信号。niri 声明 `preserve` 与 `[parts.*]` 零件插槽。fcitx5-rime 在 `.optional-apps.toml` 的 `[[app]]` 块里声明包名与 `post_install` 钩子。

不放进 manifest 的：doctor 检查项、i18n 键（防 manifest 膨胀成 DSL）。

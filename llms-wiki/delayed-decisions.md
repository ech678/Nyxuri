# Delayed Decisions — 留待触发条件 vs 已落地

> §11 列的是"真正留待触发条件的事项，已做的不列"。这次重构落地了一部分，这里**诚实区分**
> 哪些仍延迟、哪些已做。

## 仍延迟（触发条件未到 / 主动暂缓）

| 事项 | 触发条件 | 当前决策 |
|---|---|---|
| **硬件适配 Overlay**（NVIDIA / AMD / 多显示器…） | 硬件适配累积到 >3 处 | 保持 `_phase_hardware_patches` 硬编码。当前 ≤1 处（NVIDIA），不值得引入硬件 overlay 抽象。注意：此项专指硬件自适应，与已落地的**应用预设底版继承（Base Overlay）**不是同一概念。详见 [nvidia-patch](nvidia-patch.md) |
| **拆 `cli.py`** 出 `workflow.py` | >900 行 或 menu_loop 重复模式 | 保持现状。`cli.py` 当前 924 行（虽触及 >900 参考线，但命令字典与菜单结构清晰内聚、模式稳定）。不为死抠数字硬拆，留待复杂度实质上升时再做加法拆解 |

## 这次重构已落地（主动覆盖延迟）

| 事项 | 原触发 | 实际 |
|---|---|---|
| **应用预设底版继承（Base Overlay）** | 预设文件量大、仅少数文件有差异 | **已落地**。`atomic_replace_item` 支持底版拷贝与白黑名单过滤（manifest `[presets]` 表 `allow`/`include`/`exclude`），Niri `glow` 仅需 49 行 `layout.kdl`。详见 [preset-mechanism](preset-mechanism.md) 与 [manifest-schema](manifest-schema.md) |
| **子目录分组**（deploy/state/modules 子包） | >28 文件 或 某子领域 >5 文件 | **已做**。重构前 17 个 .py（< 28 触发未到），但为贯彻 §13 目标结构主动拆了四个子包——有意识覆盖 §11 的延迟决策。详见 [subpackages](subpackages.md) |
| **doctor 预设漂移检查** | preset 系统落地后即加 | **已加** `_check_preset_drift`：扫所有 app 的 active 预设是否还在仓库/用户预设目录，给汇总。平时不 update 也能在 doctor 撞见"你的 kitty 透明预设已不在上游"。符合 §4 扩展指南（写 `_check_xxx` append 到 `DOCTOR_CHECKS`，不碰 `run_doctor`） |

## `.module.toml` schema（字段全可选，无文件 = 全默认）

详见 [manifest-schema](manifest-schema.md)。kitty 这种"目录名=二进制名=单包=无例外"的，
直接不写 manifest。niri 只写 `preserve`。fcitx5-rime 在 `.optional-apps.toml` 的 `[[app]]` 块里写 `repo`/`aur`。

不放进 manifest 的：doctor 检查项、i18n 键、post-install hook（会让 manifest 膨胀成小语言）。

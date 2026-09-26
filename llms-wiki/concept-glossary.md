# Concept Glossary — 路径 / 动作 / 内容术语

> 术语统一，避免歧义。路径在 `nyxuri/core.py` 的 `Environment` 定义。

## 路径术语

| 术语 | 定义 | 实际路径 |
|---|---|---|
| `repo_dir` | 源码所在地（cache / clone / system 三选一，谁被跑谁赢） | `~/.cache/nyxuri` / clone 路径 / `/usr/share/nyxuri` |
| `config_dir` | 部署目标，恒定 | `~/.config` |
| `nyx_dir` | Nyxuri 自己的家：backups / presets / active / hooks | `~/.config/nyxuri` |
| `state_dir` | 运行时状态账本（`state.json`）与瞬态（lock + log） | `~/.local/state/nyxuri`（XDG_STATE_HOME） |
| `cache_dir` | curl 装法的源码缓存 | `~/.cache/nyxuri` |
| `configs_src` | 仓库配置源 | `repo_dir/configs` |
| `assets_src` | 仓库静态资产源 | `repo_dir/assets` |
| `presets_dir` | 用户预设 + active 状态 | `nyx_dir/presets` |
| `hooks_dir` | 用户自定义部署后置钩子脚本 | `nyx_dir/hooks` |

## 动作术语

| 术语 | 定义 | 命令 |
|---|---|---|
| `deploy` | repo_dir → config_dir 的原子对账（Dunder 保留） | install 内部 |
| `update` | 刷新 repo_dir（git pull 或 pacman） | `nyxuri update` |
| `install` | deploy + deps + 壁纸 + 模块流水线 | `nyxuri install [full\|config]` |
| `snapshot` | 保存 config_dir 当前状态 | `nyxuri snapshot [note]` |
| `rollback` | 从 snapshot 恢复 config_dir | `nyxuri rollback [index]` |
| `preset` | 切换某 app 的活动变体 | `nyxuri preset <app> …` |
| `module` | fcitx / fisher / greeter / gtk 同款三件套动词 | `nyxuri <module> [install\|status\|uninstall]` |

## 内容术语（三层叠加）

| 术语 | 定义 | 覆盖优先级 |
|---|---|---|
| Configs | 仓库 `configs/<app>/` ship 的默认配置 | 最低 |
| Presets | app 的风味变体（官方在 repo、用户在 nyx_dir） | 中 |
| Customs | `__custom__` 文件，跨一切保留 | 最高 |

## 边界规则

- Nyxuri 元数据**只许在 `~/.config/nyxuri/`**，不许往 `~/.config/<app>/` 里塞 Nyxuri 自己
  的东西（`__custom__` 是约定保留名，属 app 配置一部分，不算"拉屎"；`.module.toml` 是仓库
  元数据，deploy 时被跳过，不进 dest）。
- `~/.config/nyxuri/` 放用户数据（backups、presets）；`~/.local/state/nyxuri/` 放运行时
  状态账本（`state.json`，记录活动外壳与零件状态）及瞬态（lock、log）。不混用。

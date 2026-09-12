---
type: Playbook
title: NyxNiri 项目总纲
description: NyxNiri 桌面配置原子部署引擎的完整蒸馏——架构、合约、领域模型、运行时序与扩展指南。
resource: https://github.com/ech678/NyxNiri
tags: [nyxniri, dotfiles, niri, noctalia, atomic-deploy, tui, python]
timestamp: "2026-09-12T14:16:52Z"
atelier:
  weight: 1.0
  tier: long
  verdict: verified
  use_count: 1
---

# NyxNiri 项目总纲

> NyxNiri 把精选桌面配置（niri / kitty / fish / noctalia …）原子部署到 `~/.config`。
> 三层叠加（默认 → 预设 → `__custom__`），三模式安装（curl|bash / git clone / AUR），
> 纯 Python 标准库引擎（零 pip 依赖，需 3.11+ 因 tomllib）。repo = 真值，`~/.config` = 派生物。

## 领域模型

### 核心概念

- **Config App**：`configs/<name>/` 目录即一个可部署应用（niri、fish、kitty、noctalia …）
- **Manifest**：`.module.toml` 声明 preserve 列表、chmod 规则、可选包源
- **Optional Apps**：`.optional-apps.toml` 描述安装器菜单中的可选软件（无配置，只装包）
- **Preset**：`configs/<app>/presets/<name>/` 用户可选的变种布局（如 glow / glow-material-you）
- **Active Preset**：`~/.config/NyxNiri/presets/<app>.active` 记录当前激活状态
- **State Dir**：`~/.config/NyxNiri/`——快照、active 文件、模块标记都住这里
- **Dunder File**：文件名含 `__custom__`（如 `__custom__.kdl`）在每次更新时自动保留

### 三域隔离

```
仓库源码（configs/ + assets/）  ←→  ~/.config/（部署目标）
```

两者严格隔离，仅允许通过 `atomic_replace_item` 写盘；禁止在 `~/.config/` 内建软链连回仓库。

## 引擎结构（子包职责）

| 子包 | 职责 | 关键符号 |
|---|---|---|
| `core.py` | Environment 路径解析、锁、日志、path 原语（copy/remove temp）、进程超时包装 | `get_env()`, `timed_run()`, `copy_path()`, `remove_path()` |
| `i18n.py` | 双语文案引擎，msg() 键查找 + 参数格式化 | `msg(key, *args)`, `text(zh, en)` |
| `constants.py` | 项目常量（路径、包名、ANSI 色阶、仓库 URL） | `PROJECT_NAME`, `MAIN_WM`, `CORE_DEPS` |
| `cli.py` | 命令分发（COMMANDS dict）+ 进程入口 | `_cmd_*` handlers |
| `tui.py` | TUI 组件：Menu / CheckboxList / PresetSwitcher / TerminalGuard | `Menu`, `CheckboxList`, `PromptConfirm` |
| `menus.py` | 主菜单 / 子菜单导航编排 | `main_menu_loop()`, `run_master_component_menu()` |
| `workflows.py` | 安装/更新全流程编排 + 预检 | `install_configs_workflow()`, `_phase_preflight_check()` |
| `deps.py` | 依赖检测 + 安装菜单 | `get_missing_deps()`, `run_dep_menu_loop()` |
| `doctor.py` | 系统诊断（_check_* 追加到 DOCTOR_CHECKS） | `run_doctor()`, `generate_bug_report()` |
| `clean.py` | 缓存清理交互面板 | `main(argv)` |
| `network.py` | 多镜像 git pull / clone，自带超时降级 | `safe_git_pull()`, `safe_git_checkout_ref()` |
| `pkg/__init__.py` | 包管理命令构造（pacman/paru/yay/shelly） | `run()`, `command()`, `install()` |
| `pkg/detection.py` | 依赖探测（独立缓存，每轮重扫） | `DependencyProbe` |
| `deploy/atomic.py` | 原子替换核心：swap + preserve + Dunder walk | `atomic_replace_item()` |
| `deploy/manifest.py` | .module.toml 解析 + 两轴发现（配置 vs 可选） | `load_manifest()`, `discover_deployable_apps()` |
| `deploy/templates.py` | 模板渲染：`/home/user` → 真实 $HOME | `_phase_render_templates()` |
| `deploy/assets.py` | 壁纸部署（离线 fallback + 外部 pack 下载） | `deploy_wallpapers()`, `WallpaperDeployResult` |
| `deploy/preset.py` | 预设切换（active 文件读写 + src 四分支解析） | `apply_preset()`, `list_presets()`, `resolve_preset_src()` |
| `deploy/deploy.py` | 部署编排器 | `deploy_selected_configs()`, `discover_config_items()` |
| `state/backup.py` | 快照 / 回滚（上限 30 个，自动 prune） | `backup_configs()`, `rollback_configs()` |
| `state/uninstall.py` | 勾选式卸载 | `uninstall_nyxniri()` |
| `modules/fcitx.py` | NyxMellow 输入法皮肤 | `fcitx_install()`, `fcitx_uninstall()` |
| `modules/greeter.py` | Noctalia greetd 登录界面 | `greeter_install()`, `greeter_uninstall()` |
| `modules/fisher.py` | fisher 插件管理器 | `fisher_install()`, `fisher_uninstall()` |
| `modules/gtktheme.py` | GTK Material You 主题 | `gtktheme_install()`, `gtktheme_uninstall()` |
| `packaging/gen-deps.py` | 扫所有 manifest 聚合 AUR/Repo 依赖 → 重写 PKGBUILD | 脚本 |

## 关键合约（必须遵守）

### 部署合约
- 只走 `atomic_replace_item`，永远不建软链从 `~/.config` 指回仓库
- Dunder `__custom__` 文件每次更新自动保留（atomic walk 内处理）
- manifest `preserve` 字段声明的文件在 swap 前快照、swap 后还原
- 模板渲染中 `/home/user` 占位符由引擎替换，不得硬编码

### 外部命令合约
- 所有对外部程序调用经 `core.timed_run()` 包装，超时返回 None 不抛异常
- 包管理命令经 `pkg.run()`，超时 1800s、查询 30s
- curl / git 调用必须带 `--connect-timeout`

### TUI 合约
- `TerminalGuard` 绝对保障光标恢复（trap atexit + signal handler）
- 所有交互确认走 `prompt_confirm()`，非交互式（管道/CI）静默通过
- 输出用 ANSI 色阶（constants.Colors），不用 emoji 图标

### 测试合约
- 所有新测试必须用 `tests/utils.py:TempEnv`，禁止碰实 `~/.config`
- mock 层级紧贴被测代码——mock 打太高会绕过命令构造逻辑
- 外部命令构造函数必须有"参数列表形状"契约测试

## 扩展路径（加法不是重构）

**加 CLI 命令**：写 `_cmd_xxx(sub_args) -> int`，加一行到 `COMMANDS` 字典。

**加可选模块**（同款 install|status|uninstall 三件套）：用 `_module_handler()` 工厂，一行注册。

**加 doctor 检查项**：写 `_check_xxx(env) -> None`，append 到 `DOCTOR_CHECKS`。

**加 i18n 键**：`nyxniri/translations.toml` 加 `[键名]` 及 `zh` + `en`，test_i18n.py 校验。

## 运行入口

```bash
python3 -m nyxniri install [--yes]
python3 -m nyxniri update
python3 -m nyxniri preset
python3 -m nyxniri doctor
python3 -m nyxniri clean
python3 -m nyxniri snapshot
python3 -m nyxniri rollback
python3 -m nyxniri uninstall
python3 -m nyxniri test
```

## 参考链接

- [[infra/constants]] — 所有常量定义
- [[infra/core]] — 环境解析、锁、path 原语
- [[deploy/atomic]] — 原子替换核心合约
- [[deploy/preset]] — 预设叠加机制
- [[state/backup]] — 快照生命周期
- [[module/greeter]] — greetd 登录界面管理
- [[test/strategy]] — 测试隔离原则
- [[package/abuild]] — AUR 打包流程

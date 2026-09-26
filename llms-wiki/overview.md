# Overview — 精神、三概念、叠加规则

> Nyxuri 是精选桌面配置的原子部署引擎。核心张力：精选默认值要强（开箱即用、有审美），
> 用户的修改不能丢（更新不暴力覆盖）。三层叠加化解这对张力。

## 精神

三条原则（呼应 AGENTS.md §0、§7）：

1. **秩序**：每一层职责明确，对齐规整，不堆砌。
2. **做减法**：能不引入的概念就不引入。一个机制能覆盖两处就用一个。
3. **无熵**：不产生依赖地狱、体积膨胀、卸载残留。纯标准库能做就不加依赖。

## 三个概念（用户面）

用户只需懂三个名词，按覆盖优先级从底到高叠加，像 CSS：

```
默认 config  ←  官方预设  ←  __custom__ 文件
（最低）         （中）       （最高，永远赢）
```

### Configs（默认配置）

仓库 `configs/<app>/` 里 ship 的。`nyxuri install` 部署到 `~/.config/<app>/`。
当前 ship 8 个 app：fastfetch、fish、kitty、niri、noctalia、starship.toml、
xdg-desktop-portal、zed（`starship.toml` 是文件型 app，其余是目录）。

### Presets（官方/用户预设）

某些 app 有多套"风味"——kitty 可以有 transparent。`nyxuri preset kitty list` 看，
`apply transparent` 切。切的是**整棵配置目录树**，不是 include 片段。

- **官方预设**住仓库 `configs/<app>/presets/<name>/`，跟仓库更新走。用户不能直接改
  （下次 update 被 atomic_replace 覆盖）。当前示例：`configs/kitty/presets/transparent/`。
- **用户预设**住 `~/.config/nyxuri/presets/<app>/<name>/`，`nyxuri preset <app> save <name>`
  把当前配置存下来（save 时过滤 `__custom__`）。`default` 是保留字（`apply default` = reset），
  save 拒跟官方同名（官方优先）。

### Customs（自定义）

任何命名为 `__custom__` 的文件（`__custom__.conf`、`__custom__.kdl`，或 `__custom__/`
目录），跨更新、跨预设切换都保留。想改几行：把内容贴进 `__custom__`，永远赢过预设。
机制见 [file-preservation](file-preservation.md)。

## 叠加规则

每层可选。只要默认 = 只跑 install。想要风味 = 用 preset。要私有 = 编辑 `__custom__`。
`nyxuri install` = 读 active 预设 + 对账到 `~/.config` + 跑命令式副作用（deps、主题、fcitx）。

## 两个动作动词

- `install`：repo → `~/.config` 的原子对账（Dunder 保留）+ deps + 壁纸 + 模块流水线。
- `update`：刷新 repo（git pull 或 pacman）+ 重新部署。预设住在仓库里，仓库更新了预设源
  就更新了，下次 deploy 自动读到新源——**声明式核心**。

详见 [operation-map](operation-map.md) 和 [install-modes](install-modes.md)。

## 引擎结构与子包职责

| 子包 / 模块 | 职责与关键能力 | 核心接口 |
|---|---|---|
| `core.py` | 环境检测（Environment 单例）、文件锁、symlink-aware 路径原语、进程超时包装 | `get_env()`, `timed_run()`, `acquire_lock()` |
| `i18n.py` | 双语文案引擎（`translations.toml`），宏变量安全替换与性能缓存 | `msg(key, *args)`, `text(zh, en)` |
| `constants.py` | 项目常量、ANSI 色阶表、核心系统与 AUR 依赖清单 | `PROJECT_NAME`, `CORE_DEPS`, `Colors` |
| `deploy/` | 原子替换核心（swap+preserve+Dunder）、模板渲染、预设切换、壁纸部署 | `atomic_replace_item()`, `apply_preset()`, `deploy_wallpapers()` |
| `pkg/` | 包管理器抽象后端（pacman/paru/yay/shelly）、依赖状态只读探测与缓存 | `pkg.run()`, `DependencyProbe` |
| `state/` | 配置快照与回滚管理（上限 30 个自动 prune）、勾选式卸载 | `backup_configs()`, `rollback_configs()`, `uninstall_nyxuri()` |
| `modules/` | 系统级可选组件（fcitx5 皮肤、greetd 登录器、fisher 插件、GTK 主题）与生命周期错误边界 | `module_action()`, 各模块 `*_install()/*_uninstall()` |
| `packaging/` | 自动汇总 Manifest 依赖并生成 AUR PKGBUILD 依赖块 | `gen-deps.py` |
| `tui.py` / `menus.py` | 终端 TUI 组件（TerminalGuard 光标保护、Menu、CheckboxList、PresetSwitcher）与菜单编排 | `TerminalGuard`, `main_menu_loop()` |
| `doctor.py` | 系统健康与环境诊断（_check_* 注册模式）与 bug 报告导出 | `run_doctor()`, `generate_bug_report()` |


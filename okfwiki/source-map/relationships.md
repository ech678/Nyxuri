---
type: Source
title: 概念溯源映射
description: 每个 okfwiki 概念对应哪些源文件，支持双向定位。
resource: okfwiki/source-map/
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.6
  tier: long
  verdict: verified
  use_count: 1
---

# 概念溯源映射（Source Map）

> 格式：[[概念 ID]] → [源文件路径]:[行号范围]。用 rg 可直接跳转。

## nyx → 全仓库
- `AGENTS.md`: 全文件（架构约定、铁律、工作流）
- `nyxniri/constants.py`: 1-120（项目常量、依赖列表）
- `nyxniri/core.py`: 1-455（Environment、path 原语、锁）
- `nyxniri/i18n.py`: 全文件（msg/text 协议）
- `nyxniri/deploy/atomic.py`: 1-237（atomic_replace_item）
- `nyxniri/deploy/manifest.py`: 1-277（.module.toml 解析）
- `nyxniri/deploy/preset.py`: 1-716（预设切换）
- `nyxniri/state/backup.py`: 1-317（快照生命周期）
- `nyxniri/state/uninstall.py`: 1-208（勾选卸载）
- `nyxniri/cli.py`: 1-369（命令分发）
- `nyxniri/menus.py`: 1-383（菜单导航）
- `nyxniri/tui.py`: 1-1395（TUI 组件）
- `nyxniri/doctor.py`: 1-551（诊断检查项）
- `nyxniri/network.py`: 1-447（多镜像网络）
- `nyxniri/deps.py`: 1-248（依赖管理）
- `nyxniri/workflows.py`: 1-272（安装编排）
- `nyxniri/clean.py`: 1-697（缓存清理）
- `nyxniri/modules/fcitx.py`: 1-319
- `nyxniri/modules/greeter.py`: 1-546
- `nyxniri/modules/fisher.py`: 1-197
- `nyxniri/modules/gtktheme.py`: 1-172
- `nyxniri/pkg/__init__.py`: 1-90
- `nyxniri/pkg/detection.py`: 1-45
- `configs/.optional-apps.toml`: 全文件
- `configs/niri/.module.toml`: 全文件
- `configs/noctalia/.module.toml`: 全文件

## infra/constants → nyxniri/constants.py
- `PROJECT_NAME`, `CLI_CMD`, `MAIN_WM`, `THEME_ENGINE`
- `CORE_DEPS`, `AUR_DEPS`（完整包列表）
- `Colors` 类（ANSI 色阶）
- `REPO_URL`, `GIT_MIRROR_REGISTRY`, `RAW_MIRROR_TEMPLATES`

## infra/core → nyxniri/core.py
- `Environment` 数据类（home/config/state/cache/pictures）
- `get_env()` 单例 + run_mode 检测（system/repo/standalone）
- `acquire_lock()` / `release_lock()`（fcntl 文件锁）
- `copy_path()` / `remove_path()`（symlink-aware 原语）
- `timed_run()`（subprocess 超时包装，不抛 TimeoutExpired）
- `init_logger()` / `log_msg()`（日志）

## infra/i18n → nyxniri/i18n.py + translations.toml
- `msg(key, *args)` — 键查找 + 参数格式化 + 缓存
- `text(zh, en)` — 一次性双语字符串（诊断/状态行）
- `_load_translations()` — tomllib 加载 + constants 常量注入
- `translations.toml`：[[key]] 结构，zh/en 双语字段

## infra/network → nyxniri/network.py
- `safe_git_pull()` — 多镜像重试，cancelable via tty
- `safe_git_checkout_ref()` — 指定 ref 切换
- `_GIT_NET` flags（lowSpeedLimit/timeout/connectTimeout）
- `git_clone_timeout()` — 带超时 + 镜像重试的 clone

## deploy/atomic → nyxniri/deploy/atomic.py
- `atomic_replace_item(src, dest, preserve=None, chmod=None)` — swap+preserve 核心
- `_deploy_ignore_factory()` — copytree ignore（删 repo-only 条目）
- `_matches_pattern()` — glob 匹配（支持 `scripts/*.sh` 风格）
- Dunder `__custom__` walk：含 `__custom__` 的文件自动跳过替换，原样保留

## deploy/manifest → nyxniri/deploy/manifest.py
- `ModuleManifest` 数据类（preserve/chmod/include/presets 字段）
- `load_manifest(app)` — 读 `configs/<app>/.module.toml` + 缓存
- `discover_deployable_apps()` — 有 manifest 的 dirs
- `discover_optional_apps()` — `.optional-apps.toml` 解析
- 两轴设计：有 manifest（配置型）vs 仅 optional-apps（包型）

## deploy/preset → nyxniri/deploy/preset.py
- `read_active_preset(app)` / `write_active_preset(app, name)` — state dir 读写
- `resolve_preset_src(app, active, dest)` — 四分支：user preset / official preset / default
- `apply_preset(app, name)` — deploy first, then write active（时序铁律）
- `PresetInfo` / `PresetSrcResult` dataclass
- `InvalidActivePresetError` — 路径穿越/软链/异常内容冻结保护

## deploy/templates → nyxniri/deploy/templates.py
- `_phase_render_templates(only_app=None)` — 仅改目标文件
- `configs/niri/config.kdl`：`/home/user` → $HOME，screenshot-path 动态路径
- `configs/noctalia/noctalia-config.toml`：directory/video_directory + /home/user
- `configs/fish/fish_variables`：/home/user → $HOME

## deploy/assets → nyxniri/deploy/assets.py
- `WallpaperDeployResult` dataclass（download_attempted/downloaded/pack_present/fallback_synced）
- `deploy_wallpapers(do_download)` — no-clobber sync + 多镜像 clone
- `wallpapers_pack_present()` — 检测已部署 wallpaper pack
- 离线 fallback：`assets/wallpapers/` 内文件只补缺不覆盖

## deploy/deploy → nyxniri/deploy/deploy.py
- `discover_config_items()` — 有 manifest 的可部署 app 列表
- `deploy_selected_configs(items, ...)` — 逐 app 调用 atomic_replace_item
- `_phase_atomic_deployment()` — 调用 resolve_preset_src + atomic_replace_item
- `_phase_post_install_services()` — 触发 noctalia/gtktheme 渲染
- `run_user_hooks()` — 运行用户自定义收尾脚本（timeout 30s）
- `render_completion_screen()` — 完成界面

## state/backup → nyxniri/state/backup.py
- `backup_configs(note, interactive, protected_snapshot)` — 快照创建
- `rollback_configs(snapshot_path)` — 回滚
- `list_backups()` / `get_all_backups()` — 快照列表
- `_prune_old_snapshots()` — 自动清理（MAX_SNAPSHOTS=30）
- `_MANAGED_SNAPSHOT_RE` — 命名规范：`snapshot_*` / `pre_rollback_*` / `dotfiles_backup_*`

## state/uninstall → nyxniri/state/uninstall.py
- `uninstall_nyxniri(mode)` — 勾选式卸载
- 执行顺序铁律：模块卸载先于 nyx_dir 删除
- 支持 legacy alias：`1`=safe/standard, `2`=restore（折叠到 rollback）

## module/fcitx → nyxniri/modules/fcitx.py
- `fcitx5_installed()` / `fcitx_enabled()` — 状态探测
- `fcitx_install()` / `fcitx_uninstall()` — 皮肤部署/清退
- `fcitx_templates_registered()` — 模板是否已注册
- 主题路径：`~/.local/share/fcitx5/themes/nyxmellow/templates/`

## module/greeter → nyxniri/modules/greeter.py
- `greeter_installed()` / `greeter_status()` — 状态
- `greeter_install()` / `greeter_uninstall()` — /etc/greetd、polkit、/var/lib 写入
- 安全约束：只从 trusted exec dirs（/usr/bin, /usr/local/bin）读取二进制

## module/fisher → nyxniri/modules/fisher.py
- `fisher_installed()` / `fisher_install()` — 插件管理器安装
- 版本固定：插件固定到已审查版本
- 卸载只清理 NyxNiri 安装的文件

## module/gtktheme → nyxniri/modules/gtktheme.py
- `gtktheme_registered()` / `gtktheme_rendered()` — 主题状态
- `gtktheme_install()` / `gtktheme_uninstall()` — GTK4 @media 块 + settings.ini 兼容
- `gtktheme_trigger_render()` — 主动触发主题重绘

## module/lifecycle → nyxniri/modules/lifecycle.py
- `module_action()` context manager — 模块写入失败返回 False，中断继续上抛
- 所有模块的 install/uninstall 都应包在此 context manager 内

## ui/cli → nyxniri/cli.py
- `COMMANDS` dict：`{_cmd_xxx: (handler, desc)}` 结构
- `_module_handler(module_name, triad_name)` 工厂 — 懒加载 `importlib`
- `main()` 入口：解析 argv → dispatch → exit code 自动传播

## ui/menus → nyxniri/menus.py
- `main_menu_loop()` — 主菜单导航
- `run_master_component_menu(is_update, mode)` — 组件选择子菜单
- 各子菜单：`snapshot_menu_loop`, `deps_menu_loop`, `preset_switcher_loop`, `greeter_menu_loop` 等

## ui/tui → nyxniri/tui.py
- `TerminalGuard` — atexit + signal handler 保障光标恢复
- `Menu` / `CheckboxList` / `CategoryCheckboxList` — 交互组件
- `PresetSwitcher` — 预设切换工作台（Accordion Tree）
- `prompt_confirm()` — 确认对话框（非 TTY 时静默 true）
- `show_logo()` — 启动 Logo

## ui/doctor → nyxniri/doctor.py
- `DOCTOR_CHECKS` — 所有检查项（append 式扩展）
- `DOCTOR_SECTIONS` — 检查项按类别分组
- `_check_*` 函数模式：接受 env，打印 msg() 结果
- `generate_bug_report()` — 汇总为文本块供用户粘贴

## pkg/backend → nyxniri/pkg/__init__.py
- `command(action, packages, source, manager)` — 构造 pacman/paru/yay/shelly 命令
- `run(argv, capture, timeout)` — 包装 subprocess，超时 1800s/查询 30s
- `install()` / `install_flatpaks()` — 高层接口
- FLATHUB_REMOTE_URL = "https://dl.flathub.org/repo/flathub.remote"

## pkg/detection → nyxniri/pkg/detection.py
- `DependencyProbe` — 独立缓存，每轮重扫（无全局缓存）
- `installed(cmd)` — shutil.which + 版本验证
- `flatpaks` — flatpak list --system 探测

## package/abuild → nyxniri/packaging/gen-deps.py + PKGBUILD
- `gen-deps.py` — 扫所有 .module.toml 聚合 AUR+Repo 依赖，重写 PKGBUILD dep 块
- `PKGBUILD` — nyxniri-git rolling 包，依赖由 gen-deps.py 自动生成

## test/strategy → tests/utils.py + test_*.py
- `TempEnv` context manager — 隔离 HOME/config/cache/state 到 mktemp 目录
- mock 层级：紧贴被测代码，不打太高
- 契约测试：外部命令构造函数必须有参数列表形状断言

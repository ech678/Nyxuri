# Subpackages — nyxniri/{pkg, deploy, state, modules, packaging}

> 引擎按职责分包，顶层保留入口与基础设施。子包 `__init__.py` 提供公共接口——
> **外部 import 不变深**。懒加载/测试打补丁用直接子模块路径。

## 结构

```
nyxniri/
├── __init__.py · __main__.py          包入口
├── constants.py                        路径 / 包名 / ANSI 色阶常量
├── core.py                             Environment（run_mode、路径）、锁、日志、path 原语（remove_path/copy_path）、CLI 软链、PATH 遮蔽、timed_run
├── i18n.py                             msg()、语言选择、颜色与项目名替换
├── translations.toml                   双语文案（zh/en，test_i18n 校验字段、引用与参数）
├── tui.py                              Menu / CheckboxList / PresetSwitcher / 原语
├── network.py                          git pull / curl（带 connect-timeout + 容错）
├── cli.py                              命令分发（COMMANDS dict）与进程入口
├── menus.py                            主菜单、子菜单与组件选择
├── workflows.py                        安装 / 更新编排、预检、完成反馈
├── deps.py                             依赖批次、AUR 引导、可选软件菜单（无全局探测缓存）
├── clean.py                            缓存清理，入口 nyxniri clean
├── doctor.py                           体检（_check_* 追加到 DOCTOR_CHECKS）
│
├── pkg/                                Fish 与安装器共用的包管理
│   ├── __init__.py                     后端选择、命令构造、安装与超时结果
│   ├── cli.py                          pkg 命令、搜索、详情、已安装列表
│   └── detection.py                    软件包、字体与 GI 的只读状态探测；每轮检查独立缓存
│
├── deploy/                             部署子包
│   ├── atomic.py                       atomic_replace_item（swap+preserve）+ Dunder walk + manifest preserve 快照
│   ├── manifest.py                     .module.toml + .optional-apps.toml 解析、app 发现（两轴解耦，见下页）
│   ├── templates.py                    _phase_render_templates（/home/user → $HOME、screenshot 路径）
│   ├── assets.py                       壁纸部署（WallpaperDeployResult、no-clobber 同步 + 外部包下载）
│   ├── hardware.py                     classify_gpu_devices（诊断报告的纯文本 PCI 设备分类）
│   ├── preset.py                       预设切换（active 状态、src 四分支、apply 窄路径）
│   └── deploy.py                       编排器：discover_config_items、_phase_atomic_deployment、
│                                       _phase_post_install_services、run_user_hooks、
│                                       render_completion_screen、deploy_selected_configs、test_deploy
│
├── state/                              状态子包
│   ├── backup.py                       快照 / 回滚 / 删除（path 原语 copy_path/remove_path 在 core.py）
│   └── uninstall.py                    勾选式卸载（模块恢复先于 nyx_dir 删除）
│
├── modules/                            模块子包（同款 install|status|uninstall 三件套）
│   ├── fcitx.py                        NyxMellow 皮肤、主题字段恢复、旧 QuickPhrase 备份清退
│   ├── lifecycle.py                    模块写入失败返回 False；中断继续上抛
│   ├── fisher.py                       fisher 插件管理器（部署自动装，亦可单独 status/uninstall）
│   ├── greeter.py                      Noctalia Greeter（/etc/greetd、polkit、/var/lib）
│   └── gtktheme.py                     GTK Material You 主题渲染
│
└── packaging/                          AUR 打包
    ├── PKGBUILD                        nyxniri-git rolling 包
    └── gen-deps.py                     扫所有 manifest 聚合依赖 → 重写 PKGBUILD 块
```

基础设施（core/i18n/constants/tui/network）留顶层——被到处引用的底座，埋子包里让 import
变深，不值得。

## __init__.py re-export（外部 import 不变深）

每个子包 `__init__.py` 把关键公共符号 re-export 到子包根：

- `nyxniri.deploy/__init__`：`atomic_replace_item`、`discover_config_items`、`deploy_selected_configs`、
  `deploy_wallpapers`、`wallpapers_pack_present`、`run_user_hooks`、`render_completion_screen`、`test_deploy`、
  preset 全套（`apply_preset`/`list_presets`/…）、manifest 全套
  （`load_manifest`/`discover_deployable_apps`/`discover_optional_apps`）…
- `nyxniri.state/__init__`：`backup_configs`、`rollback_configs`、`list_backups`、`delete_backup`、
  `get_all_backups`、`get_backup_base_dir`、`uninstall_nyxniri`（path 原语 `copy_path`/`remove_path` 在 core.py，按需直连）
- `nyxniri.modules/__init__`：fcitx/fisher/greeter/gtktheme 四件套动词（`fcitx_install`/`fisher_uninstall`/…）

## Import 约定（两套路径，按场景选）

**顶层调用方**（cli.py、doctor.py、deps.py 的 top-level import）：用 re-export，保持浅。
```python
from nyxniri.deploy import deploy_selected_configs, discover_config_items
from nyxniri.state import backup_configs, uninstall_nyxniri
```

**懒加载 + 测试打补丁**：用**直接子模块路径**。因为 mock.patch 命中的是被测代码运行时
读的源模块；re-export 在 `__init__` import 时已绑定旧引用，patch 源不影响 re-export 绑定。
```python
# 引擎内懒加载（state/uninstall.py 内）
from nyxniri.deploy.deploy import discover_config_items
from nyxniri.modules.fisher import fisher_uninstall
from nyxniri.deploy.atomic import atomic_replace_item
# 测试打补丁
patch("nyxniri.deploy.atomic.atomic_replace_item", return_value=False)
patch("nyxniri.deploy.deploy._phase_post_install_services")
```

## 动态 import（cli.py `_module_handler`）

CLI 的 `greeter`/`fcitx`/`gtk` 命令经 `_module_handler(module_name, triad_name)` 工厂分发，
懒加载 `importlib.import_module(f"nyxniri.modules.{module_name}")`——这样测试 `patch` 能命中
（架构 §13：`_module_handler` 动态 import 改 `nyxniri.modules.{name}`，一处）。

## 外部命令超时（timed_run，铁律）

部署与诊断的有界调用经 `core.timed_run`：超时降级为返回
`None` + WARN 日志，**不抛** `TimeoutExpired`。背景：v3.0.3 给外部命令加了超时
防卡死，但只有 network.py 自己接了异常——fisher install 弱网 60s 超时直接炸穿
整个部署（真实事故：配置已部署完，完成界面没渲染，用户拿到裸 traceback）。
原则：外部命令是"锦上添花"，超时 = 跳过该步继续走，绝不阻断主流程。调用方
拿到 `None` 按各处语义降级（探测失败/未运行/依赖未知）。

包管理用 `pkg.run` 返回 `CompletedProcess`：命令退出码原样保留，超时为 124，
无法执行为 127。查询上限 30 秒，安装上限 1800 秒；失败不自动换后端重试。
安装接口返回 bool，依赖安装失败会阻止安装流程继续报告成功。

## install.sh 完整性校验

`install.sh` 的 `engine_is_complete` 按**子包结构**校验 curl 装法下载的缓存是否完整：

- 顶层：`__init__ __main__ clean cli constants core deps doctor i18n menus network tui workflows`，以及 `translations.toml`
- `pkg/`：`__init__ cli detection`
- `deploy/`：`__init__ atomic assets deploy hardware manifest preset templates`
- `state/`：`__init__ backup uninstall`
- `modules/`：`__init__ fcitx fisher greeter gtktheme lifecycle`

缺任何一个 `make install` 前就拦下，避免半残引擎跑起来。

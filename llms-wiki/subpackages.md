# Subpackages — nyxniri/{deploy, state, modules, packaging}

> 引擎拆四个职责子包 + 顶层基础设施。子包 `__init__.py` re-export 关键符号——
> **外部 import 不变深**。懒加载/测试打补丁用直接子模块路径。

## 结构

```
nyxniri/
├── __init__.py · __main__.py          包入口
├── constants.py                        路径 / 包名 / ANSI 色阶常量
├── core.py                             Environment（run_mode、路径）、锁、日志、path 原语（remove_path/copy_path）、CLI 软链、PATH 遮蔽、timed_run
├── i18n.py                             msg() + TRANSLATIONS（zh/en，test_i18n 自动校验）
├── tui.py                              Menu / CheckboxList / PresetSwitcher / 原语
├── network.py                          git pull / curl（带 connect-timeout + 容错）
├── cli.py                              命令分发（COMMANDS dict）+ 主菜单 / 工作流
├── deps.py                             依赖检测、AUR 引导、可选软件菜单
├── doctor.py                           体检（_check_* 追加到 DOCTOR_CHECKS）
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
│   ├── fcitx.py                        NyxMellow fcitx5 皮肤（classicui + quickphrase 备份/恢复）
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

所有带 `timeout=` 的 `subprocess.run` 必须走 `core.timed_run`：超时降级为返回
`None` + WARN 日志，**不抛** `TimeoutExpired`。背景：v3.0.3 给外部命令加了超时
防卡死，但只有 network.py 自己接了异常——fisher install 弱网 60s 超时直接炸穿
整个部署（真实事故：配置已部署完，完成界面没渲染，用户拿到裸 traceback）。
原则：外部命令是"锦上添花"，超时 = 跳过该步继续走，绝不阻断主流程。调用方
拿到 `None` 按各处语义降级（探测失败/未运行/依赖未知）。

## install.sh 完整性校验

`install.sh` 的 `engine_is_complete` 按**子包结构**校验 curl 装法下载的缓存是否完整：

- 顶层：`__init__ __main__ cli constants core deps doctor i18n network tui`
- `deploy/`：`__init__ atomic assets deploy hardware manifest preset templates`
- `state/`：`__init__ backup uninstall`
- `modules/`：`__init__ fcitx fisher greeter gtktheme`

缺任何一个 `make install` 前就拦下，避免半残引擎跑起来。

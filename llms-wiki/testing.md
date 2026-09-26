# Testing — 策略、形状、隔离

> 对照 AGENTS.md §9（TempEnv 隔离、参数形状契约、mock 紧贴被测代码）。

## 隔离（铁律）

**所有测试必须用 `tests/utils.py:TempEnv`，禁止碰真实 `~/.config` / `~/.local` / `~/.cache`。**

TempEnv 把 HOME 指向 tmpdir、建目录骨架、override `XDG_*` 环境变量、reset `core._ENV` 和
模块级缓存（core 的 `_PICS_DIR_CACHE`、deploy 的 `_CONFIG_ITEMS_CACHE`、
manifest 的 `_MANIFEST_CACHE`、deps 的 pacman/fc-list/GI/AUR 助手缓存、greeter 状态缓存）
防止跨测试泄漏。反例：早期测试把实仓库 `configs/niri/config.kdl` 写成桩文件——已修。

## 验证哲学：纯本地秒级收归，零云端 CI 依赖

commit `b470af0` 彻底移除了 GitHub Actions 工作流。Nyxuri 的所有契约测试与静态检查**纯粹收归本地**：
- **零网络秒级测试**：纯 Python 标准库 + 离线 unittest，400+ 项测试在普通笔记本上 10 秒内跑完。
- **免非 Arch 杂音**：避免了在非 Arch 环境（如 Ubuntu Actions Runner）上因依赖缺失和包管理器模拟产生的虚假报错与调试熵增。
- **改动必测门禁**：所有提交必须通过本地 `compileall` + `unittest` + 沙箱隔离部署。

## mock 层级（紧贴被测代码）

mock 打得太高会绕过命令构造逻辑。反例：测 `safe_git_pull` 时 mock `_run_git_transfer` 跳过了
`_with_git_progress` 的参数变形。

**更隐蔽的反例**：`test_orbit_lock` 曾 mock `_is_orbit_process` 本身——被测函数读 `/proc` 的
argv[0]（shebang 直启下是解释器名，不是脚本名），验证恒假、orbit toggle 失灵，mock 把回归
盖得严严实实。修正：真实子进程 + 真实 `/proc` 验证匹配逻辑，**验证函数本身永不 mock**。
（附带发现：`Popen` 返回后立即读 `/proc/<pid>/cmdline` 大概率还是空的，argv 发布与 exec
有竞态——测试需轮询等 cmdline 落地，真实运行场景不受影响。）

正确做法：被测代码**懒加载**（函数内 `from nyxuri.deploy.atomic import X`），测试
`patch("nyxuri.deploy.atomic.X")` 直接打**源模块**——运行时懒加载读到 patched 属性。
（re-export 绑定在 `__init__` import 时，patch 源不影响 re-export，所以测试用直接子模块路径。）

## 核心测试覆盖（按功能）

| 功能领域 | 契约与测试形状 | 测试文件 |
|---|---|---|
| 预设与通用零件插槽 | 四分支解析、写时序、零件热插拔、`_reconcile_active_parts` 防覆写、账本写入 | `test_preset.py` |
| 桌面外壳路由与网关 | `active_shell` 路由、自研 Shell 崩溃回退告警、账本记录 | `test_shell.py` |
| 线性迁移与品牌重命名 | 历史 `NyxNiri` 小写迁移、静态 Tombstone 孤儿清理、软链接自愈 | `test_migrations.py`, `test_migration_rebrand.py` |
| Fcitx5 与输入法生态 | 雾凇方案挂载与预编译、皮肤解耦激活、深浅切换无损跟随、对等卸载 | `test_fcitx.py`, `test_fcitx_theme_assets.py` |
| 登录器模块 | Noctalia Greeter 安装、状态侦测、Polkit 规则、对等卸载 | `test_greeter.py` |
| 主题同步与模板中枢 | `nyxuri.theme` 动态同步 GTK3/4 与 Qt、TOML 模板原子管理 | `test_theme_sync.py`, `test_template_registry.py` |
| 合成器与网关脚本 | `session-shell.sh`、`shell-action.sh` 8 大动作分发契约与回退行为 | `test_config_scripts.py` |
| 预设工作台双栏 TUI | Dual-Pane 分栏穿梭、左右键切栏、`●` 标记、窄 deploy 路径 | `test_preset.py` |
| 原子部署与保留 | 文件/目录原子 swap、中断保护栈、`__custom__` 与 preserve 保留 | `test_deploy.py`, `test_manifest.py` |
| 勾选卸载与安全清除 | 依赖按需清理、受管壁纸清单过滤（绝不误删私人壁纸）、孤儿清理 | `test_uninstall.py` |
| 系统安装模式探测 | System / Repo / Standalone 三模式识别与 PATH 遮蔽警告 | `test_system_mode.py` |
| 硬件诊断与驱动中立 | PCI 设备分类、默认不强制 NVIDIA 环境变量、跨应用隔离 | `test_hardware.py` |
| i18n 完整性约束 | AST 符号 vs `translations.toml`，无孤儿、无缺失，参数对齐 | `test_i18n.py` |
| 包管理抽象与 Shelly 适配 | 后端分流、超时控制、取消不重试、Shelly 解析 | `test_pkg.py`, `test_deps.py` |
| 网络弹性 | HTTP 超时、多镜像回退、网络中断软降级 | `test_network.py` |

## 必跑命令

```bash
python3 -m compileall nyxuri                                    # 语法/静态检查
bash -n install.sh configs/noctalia/*.sh configs/niri/scripts/*.sh
shellcheck install.sh
python3 -m unittest discover -s tests -q                        # 行为契约
HOME=$(mktemp -d) ./install.sh test                             # 沙箱隔离部署
```

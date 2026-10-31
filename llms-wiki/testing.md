# Testing — 策略、形状、隔离

> 对照 AGENTS.md 测试规范（TempEnv 隔离、参数形状契约、mock 紧贴被测代码）。

## 隔离（铁律）

**所有测试必须用 `tests/utils.py:TempEnv`，禁止碰真实 `~/.config` / `~/.local` / `~/.cache`。**

TempEnv 把 HOME 指向 tmpdir、建目录骨架、override `XDG_*` 环境变量、reset `core._ENV` 和
模块级缓存（core 的 `_PICS_DIR_CACHE`、deploy 的 `_CONFIG_ITEMS_CACHE`、
manifest 的 `_MANIFEST_CACHE`），防止路径跨测试泄漏。
`units_src` 默认仍指向真实仓库，适合只读检查交付蓝图；需要写入 manifest 或配置夹具时，
先在 `TempEnv.home` 下创建源目录，再将 `units_src` 指向它。不能直接向默认源目录写桩文件。

## 验证哲学：纯本地秒级收归，零云端 CI 依赖

commit `b470af0` 彻底移除了 GitHub Actions 工作流。Nyxuri 的所有契约测试与静态检查**纯粹收归本地**：
- **离线行为测试**：引擎使用 Python 标准库与 unittest；外部包安装命令由测试替身接收，不能实际安装软件。
- **显式平台夹具**：Arch、Ubuntu 和未知平台分别指定发行版输入；测试结果不应由宿主的发行版或已安装包决定。
- **改动按域验证**：按下文验证分级选择定向测试；真实 QML/GTK 运行时检查单独列出所需工具与跳过原因。

## 平台与运行时边界

发行版识别测试替换 `/etc/os-release` 等外部输入，保留被测识别逻辑；包后端测试断言
命令参数、退出结果与超时。平台无关的部署夹具显式声明所需包，Arch 专属用例可以固定
Arch 视图，但不能在整个套件入口统一伪装平台。Ubuntu 的包查询、依赖映射、安装与失败
路径必须有独立用例，不能由 Arch 测试通过推断。

依赖检测的缓存只在一次检查对象内复用；测试应验证新一轮检查能发现后装的包或资源。
对安装前拒绝、安装失败、安装后重检等场景，同时断言配置、账本和外部命令的副作用边界。

QML 测试使用 Qt6 工具，不能把 PATH 中的 Qt5 `qmltestrunner` 当成等价替代。
真实 Shell 测试隔离 HOME/XDG、D-Bus 和显示服务器；缺少 Quickshell、Weston 或 GTK
绑定时可以明确跳过，但汇报须区分通过与跳过。离屏组件加载和 IPC 检查不能替代真实 Niri
会话中的锁屏认证、重登、双屏定位与屏幕共享验收。

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
| 预设与通用零件插槽 | 四分支解析、写时序、零件热插拔、`_reconcile_active_parts` 防覆写、账本写入 | `tests/deploy/test_preset.py` |
| 桌面外壳路由与网关 | `active_shell` 路由、自研 Shell 崩溃回退告警、账本记录 | `tests/shell/test_shell.py` |
| 线性迁移与品牌重命名 | 历史 `NyxNiri` 小写迁移、静态 Tombstone 孤儿清理、软链接自愈 | `tests/deploy/test_migrations.py` |
| Fcitx5 与输入法生态 | 雾凇方案挂载与预编译、皮肤解耦激活、深浅切换无损跟随、对等卸载 | `tests/desktop/test_fcitx.py` |
| 登录器模块 | Noctalia Greeter 安装、状态侦测、Polkit 规则、对等卸载 | `tests/desktop/test_greeter.py` |
| 主题同步中枢 | `nyxuri.desktop.theme` 动态同步 GTK3/4 与 Qt、原子写 INI | `tests/desktop/test_theme_sync.py` |
| 合成器与网关脚本 | `session-shell.sh`、`shell-action.sh` 9 大动作分发契约与回退行为 | `tests/desktop/test_config_scripts.py` |
| 原子部署与保留 | 文件/目录原子 swap、中断保护栈、`__custom__` 与 preserve 保留 | `tests/deploy/test_deploy.py`, `tests/deploy/test_manifest.py` |
| 勾选卸载与安全清除 | 依赖按需清理、受管壁纸清单过滤（绝不误删私人壁纸）、孤儿清理 | `tests/state/test_uninstall.py` |
| 系统安装模式探测 | System / Repo / Standalone 三模式识别与 PATH 遮蔽警告 | `tests/deploy/test_system_mode.py` |
| 硬件诊断与驱动中立 | PCI 设备分类、默认不强制 NVIDIA 环境变量、跨应用隔离 | `tests/deploy/test_hardware.py` |
| i18n 完整性约束 | AST 符号 vs `translations.toml`，无孤儿、无缺失，参数对齐 | `tests/test_i18n.py` |
| 发行版与原生包数据库 | 发行版识别、APT 来源与候选、dpkg 状态与多架构、查询失败 | `tests/pkg/test_platform.py` |
| 平台依赖与手动资源 | Arch/Ubuntu 映射、非法声明拒绝、字体与 Rime 探针、原始打包声明保留 | `tests/pkg/test_requirements.py`, `tests/pkg/test_detection.py`, `tests/deploy/test_manifest.py`, `tests/pkg/test_packaging.py` |
| 包管理抽象 | APT/Arch 后端参数、分渠道供给、超时与失败、取消不重试 | `tests/pkg/test_pkg.py`, `tests/pkg/test_deps.py` |
| 安装流程 | full/config 边界、所选单元依赖、手动资源部分完成、非交互默认选择 | `tests/installer/test_workflows.py`, `tests/test_cli.py` |
| 桌面兼容诊断与主题钩子 | 原生包诊断、GI Cairo 转换器、渲染失败报告、GTK3 模板语法 | `tests/desktop/test_doctor.py`, `tests/desktop/test_noctalia_hook.py`, `tests/desktop/test_gtk_template.py` |
| 划词翻译工具 | 渠道协议与解析、定位几何、ResultRelay、凭据脱敏、TUI（含 PTY）、Alt+E / Orbit 入口契约；经 `tests/tools/translate/support.py` 套 `TempEnv` | `tests/tools/translate/` |
| 网络弹性 | HTTP 超时、多镜像回退、网络中断软降级 | `tests/pkg/test_network.py` |

## 验证分级（按需测试，拒绝无谓浪费）

**严禁一刀切乱跑全量测试，禁止无谓耗时**：
- **纯文档 / 文本 / 规划改动**：免跑引擎测试；涉及相对链接或索引时仅需 `python3 -m unittest tests/test_ai_specs.py`（0.06s）。
- **日常单域代码改动**：只跑上表对应的定向测试文件（秒级返回）。
- **发版或重大引擎重构全量把关**：
  ```bash
  python3 -m compileall nyxuri                                    # 语法/静态检查
  bash -n install.sh units/noctalia/*.sh units/niri/scripts/*.sh
  shellcheck install.sh
  python3 -m unittest discover -s tests -q                        # 全量行为契约
  HOME=$(mktemp -d) python3 -m nyxuri test                        # 沙箱隔离部署
  ```

# Operation Map — 全部 CLI 命令

> 命令分发在 `nyxuri/cli.py` 的 `COMMANDS` dict。退出码自动传播。
> KM3.5 起 `COMMANDS` 收敛为 20 键 = 17 活动词 + enable/disable 长动词 + help；
> 旧命令别名 ×12 与倒计时表已处决——旧名就是普通 unknown command。
> KM5：`install.sh` 退役为一次性引导（无参数透传，常驻入口 = `nyxuri/launcher.sh`）；
> `migrations/` 与 nyxniri 兼容层（别名 / `NYXNIRI_*`）处决。

## 单元动词（4 动词接管）

所有命令在迁移、锁与日志写入前校验四个 XDG 根目录。当前只支持 HOME 下的默认布局；
自定义路径会报错退出，启动器不会静默改写调用者环境。目录契约见
[文件保留](file-preservation.md)。

| 命令 | 干啥 |
|---|---|
| `list [unit]` | 单元全景（开关状态 × 当前预设），或单个单元详情（manifest 声明 × 账本记录 × 对账态） |
| `on <unit> [--preset <name>] [--force]`（等价 `enable`） | 启用单元：依赖闭包披露 → 当前平台包与手动资源预检 → 缺失包披露确认 → 事务落账 + `unit-changed` 事件 |
| `off <unit> [--cascade]`（等价 `disable`） | 停用单元：反向依赖强阻断（显式 `--cascade` 才级联）→ 修改与自定义逐文件入 Vault → 撤回受管文件；报告列明幸存外部文件与保留的包 |
| `doctor [unit]` | 单元对账（`Synced` / `Drifted` / `Ghost` / `Pending` / `Orphan`）；无参时在对账表后附加系统体检段（`sysdoctor`） |

切换前披露、切换后交报告是产品定论：`plan_on` / `plan_off`（只读）供界面披露，
写入只走 `transaction.unit_on` / `unit_off` 唯一事务路径。

## 领域动词（过渡期，退役排期见 unit-model §7）

| 命令 | 干啥 |
|---|---|
| `install [full\|config]` | 所选单元及依赖通过 `unit_on` 部署并登记；`full` 检查供应并执行钩子，`config` 只复制并标记 `config-only`，后续 `on` 补完依赖与钩子 |
| `update [--local] [--force\|--deploy\|--no-deploy] [--to <tag\|commit>]` | 默认先更新源码，再刷新账本中已启用且仍有蓝图的单元（含 merge）；`--local` 直接应用当前源码，不能与 `--to` / `--no-deploy` 组合；`--deploy` 是正常保留策略，`--force` 在快照成功后采用模板冲突路径；`--no-deploy` 仅更新源码 |
| `preset <app> [list\|apply <name>\|save <name>\|edit <name>\|delete <name>\|parts\|part <slot> <name>]` | 切/管理预设与零件插槽（状态接入 `state.json` 账本） |
| `theme [toggle\|dark\|light\|sync\|status]` | 原生切换/同步深浅主题（纯 Python 调度 gsettings、GTK settings.ini、Noctalia IPC 与 Kitty 信号） |
| `shell [get\|set <noctalia\|nyxuri-shell> [bin_path]\|switch [\|bin_path]\|status]` | 查看或切换桌面外壳运行插槽。**[EXPERIMENTAL]** nyxuri-shell 开发中，输出带实验性警告 |
| `deps [core\|apps]` | 装软件包：core = 核心依赖勾选单，apps = catalog.toml + 可选单元同源菜单 |
| `pkg <install\|upgrade\|remove\|search\|info\|installed>` | 包管理直通（Fish 与安装器共用）；`repo` / `pac` 搜索本机仓库，`aur` 仅 Arch 可用；Ubuntu 使用 APT/dpkg |
| `clean [-n] [--only <任务>]` | 缓存清理；`-n` 只预览，Fish 的 `clean` 指向此入口 |
| `snapshot [note\|list\|delete [index]]` | 存档当前配置 / 列出 / 删除快照 |
| `rollback [index]` | 从存档恢复 |
| `uninstall [--all\|standard\|restore\|purge]` | 卸载（勾选式）；`--all` 等价三选一路径直达 |
| `bug` | 导出诊断报告 |
| `test` | 开发者沙箱部署测试（`HOME=$(mktemp -d) python3 -m nyxuri test` 的落点；install.sh 已不透传参数） |
| `help` | 用法 |

首次安装的交互菜单与非交互入口共用 `installer.candidates.discover_install_config_items()`，
候选覆盖所有有配置载荷的目录、单文件与 merge 单元（包括 Portal、Fcitx 和主题）；排除
runtime 与仅声明软件包的单元。壁纸保留独立资源选项。窗口管理器选择及可选供给筛选沿用
原规则：Ubuntu 非交互 full 不顺带安装尚未具备供给的 optional 单元。底层原子部署批次与
预设目录发现仍排除 merge，不能为了安装候选扩张共享目录的交换范围。

Ubuntu 的来源准备及手动依赖边界见
[Ubuntu 兼容指南](ubuntu-compatibility.md)。

拉取源码后的 `update` 重启（命令行与控制面板两条路径都算）一律 `os.execve` 回常驻启动器
`nyxuri/launcher.sh`（`core.exec_cli`）——repo / standalone 模式下只有 launcher 会把
引擎塞进 `sys.path`，自己拼 `python -m nyxuri` 离开仓库根目录就必炸（#138）。

冲突确认在 `on`、安装、更新和预设切换中共用：展示路径，选择保留、备份后覆盖或取消。
非交互默认保留，`--force` 才明确采用模板；普通备份复选框不会关闭强制覆盖的保险快照。
更新跳过未启用/Ghost 单元；源码工作区不干净导致拉取跳过时，CLI 返回非零并提示 `--local`。
单元钩子失败报告部分完成并保留待重试阶段，重跑相应 `on` / `off`，不将失败显示为完成。
预设 `apply` / `part` 同样接受 `--force`，仅操作已启用且支持目录预设的单元，详见
[预设机制](preset-mechanism.md)。快照与卸载的恢复边界见 [状态操作](state-ops.md)。

## 已处决（KM3.5 + KM5，调用即 unknown command）

KM3.5：`deploy` `backup` `restore` `remove` `purge` `recommended` `apps` `wp` `wallpapers`
`report` `-h/--help`，以及幽灵指针 `greeter` `fcitx` `gtk` `fisher`。
KM5：系统软链与用户端别名 `nyxniri`、`NYXNIRI_*` 环境变量回退（原「兼容别名」节随
`migrations/` 清算一并处决——一个变量一个前缀 `NYXURI_*`）。
替代能力：`on/off <unit>`（单元能力）、`snapshot`/`rollback`/`uninstall`（状态域）、
`deps apps`（可选软件）、`bug`（诊断）；壁纸能力 = `on wallpapers`
（外部大包走 `units/wallpapers/hooks/install-pack`）。

# Operation Map — 全部 CLI 命令

> 命令分发在 `nyxuri/cli.py` 的 `COMMANDS` dict。退出码自动传播。
> KM3.5 起 `COMMANDS` 收敛为 20 键 = 17 活动词 + enable/disable 长动词 + help；
> 旧命令别名 ×12 与倒计时表已处决——旧名就是普通 unknown command。
> KM5：`install.sh` 退役为一次性引导（无参数透传，常驻入口 = `nyxuri/launcher.sh`）；
> `migrations/` 与 nyxniri 兼容层（别名 / `NYXNIRI_*`）处决。

## 单元动词（4 动词接管）

| 命令 | 干啥 |
|---|---|
| `list [unit]` | 单元全景（开关状态 × 当前预设），或单个单元详情（manifest 声明 × 账本记录 × 对账态） |
| `on <unit> [--preset <name>]`（等价 `enable`） | 启用单元：依赖闭包披露 → 缺失包披露确认（repo/AUR/Flatpak 按 manifest 三方分流）→ 事务落账 + `unit-changed` 事件 |
| `off <unit> [--cascade]`（等价 `disable`） | 停用单元：反向依赖强阻断（显式 `--cascade` 才级联）→ 自定义入 Vault → 实机抹白；报告列明幸存外部文件与保留的包 |
| `doctor [unit]` | 单元三态对账（`Synced` / `Drifted` / `Ghost`）；无参时在对账表后附加系统体检段（`sysdoctor`） |

切换前披露、切换后交报告是产品定论：`plan_on` / `plan_off`（只读）供界面披露，
写入只走 `transaction.unit_on` / `unit_off` 唯一事务路径。

## 领域动词（过渡期，退役排期见 unit-model §7）

| 命令 | 干啥 |
|---|---|
| `install [full\|config]` | 旧世界整装流水线（配置 + 壁纸单元 + 钩子重放）；市场化后由 `on <unit>` 接管 |
| `update [--force\|--no-deploy] [--to <tag\|commit>]` | 拉新版本 + 重新部署（KM5：线性迁移机制已清算，账本即真相）；`--to` 锁到指定版本（system 模式 → 提示 pacman）。部署走所有权 carry（#139）：用户改动与自放文件原样搬入、Ghost 单元冻结并提示 `on` 收编；`--force` = 采纳模板侧（payload 名全部认领 + 账本重登记），不是清剿 |
| `preset <app> [list\|apply <name>\|save <name>\|edit <name>\|delete <name>\|parts\|part <slot> <name>]` | 切/管理预设与零件插槽（状态接入 `state.json` 账本） |
| `theme [toggle\|dark\|light\|sync\|status]` | 原生切换/同步深浅主题（纯 Python 调度 gsettings、GTK settings.ini、Noctalia IPC 与 Kitty 信号） |
| `shell [get\|set <noctalia\|nyxuri-shell> [bin_path]\|switch [\|bin_path]\|status]` | 查看或切换桌面外壳运行插槽。**[EXPERIMENTAL]** nyxuri-shell 开发中，输出带实验性警告 |
| `deps [core\|apps]` | 装软件包：core = 核心依赖勾选单，apps = catalog.toml + 可选单元同源菜单 |
| `pkg <install\|upgrade\|remove\|search\|info\|installed>` | 包管理直通（Fish 与安装器共用）；搜索支持 `aur` / `pac` 前缀 |
| `clean [-n] [--only <任务>]` | 缓存清理；`-n` 只预览，Fish 的 `clean` 指向此入口 |
| `snapshot [note\|list\|delete [index]]` | 存档当前配置 / 列出 / 删除快照 |
| `rollback [index]` | 从存档恢复 |
| `uninstall [--all\|standard\|restore\|purge]` | 卸载（勾选式）；`--all` 等价三选一路径直达 |
| `bug` | 导出诊断报告 |
| `test` | 开发者沙箱部署测试（`HOME=$(mktemp -d) python3 -m nyxuri test` 的落点；install.sh 已不透传参数） |
| `help` | 用法 |

`update` 的重启（命令行与控制面板两条路径都算）一律 `os.execve` 回常驻启动器
`nyxuri/launcher.sh`（`core.exec_cli`）——repo / standalone 模式下只有 launcher 会把
引擎塞进 `sys.path`，自己拼 `python -m nyxuri` 离开仓库根目录就必炸（#138）。

## 已处决（KM3.5 + KM5，调用即 unknown command）

KM3.5：`deploy` `backup` `restore` `remove` `purge` `recommended` `apps` `wp` `wallpapers`
`report` `-h/--help`，以及幽灵指针 `greeter` `fcitx` `gtk` `fisher`。
KM5：系统软链与用户端别名 `nyxniri`、`NYXNIRI_*` 环境变量回退（原「兼容别名」节随
`migrations/` 清算一并处决——一个变量一个前缀 `NYXURI_*`）。
替代能力：`on/off <unit>`（单元能力）、`snapshot`/`rollback`/`uninstall`（状态域）、
`deps apps`（可选软件）、`bug`（诊断）；壁纸能力 = `on wallpapers`
（外部大包走 `plugins/wallpapers/hooks/install-pack`）。

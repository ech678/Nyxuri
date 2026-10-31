# Operation Map — 全部 CLI 命令

> 命令分发在 `nyxuri/cli.py` 的 `COMMANDS` dict。退出码自动传播。
> KM3.5 起 `COMMANDS` 收敛为 20 键 = 17 活动词 + enable/disable 长动词 + help；
> 旧命令别名 ×12 与倒计时表已处决——旧名就是普通 unknown command。
> KM5：`install.sh` 退役为一次性引导（无参数透传，常驻入口 = `nyxuri/launcher.sh`）；
> `migrations/` 与 nyxniri 兼容层（别名 / `NYXNIRI_*`）处决。

## 插件动词（R0-2 起：形态轴并轨，动词清单见 vision §1）

| 命令 | 干啥 |
|---|---|
| `list [plugin]` | 插件全景（开关状态 × 当前形态），或单个插件详情（manifest 声明 × 账本记录 × 对账态） |
| `on <plugin> [--form <name>]`（等价 `enable`） | 启用插件：依赖闭包披露 → 缺失包披露确认（repo/AUR/Flatpak 按 manifest 三方分流）→ 事务落账 + `plugin-changed` 事件 |
| `off <plugin> [--cascade]`（等价 `disable`） | 停用插件：反向依赖强阻断（显式 `--cascade` 才级联）→ 自定义入 Vault → 实机抹白；报告列明幸存外部文件与保留的包 |
| `use <plugin> [list\|<name>\|save <name>\|edit <name>\|delete <name>\|slots\|slot <axis> <name>]` | 形态动词（R0-2 杀词并轨）：整型形态轴裸值直切，`slot` 子动作切槽位轴，`save`/`edit`/`delete` 管用户私有形态 |
| `doctor [plugin]` | 插件三态对账（`Synced` / `Drifted` / `Ghost`）；无参时在对账表后附加系统体检段（`sysdoctor`） |

切换前披露、切换后交报告是产品定论：`plan_on` / `plan_off`（只读）供界面披露，
写入只走 `transaction.plugin_on` / `plugin_off` 唯一事务路径。

## 领域动词（过渡期，退役排期见 plugin-model §7）

| 命令 | 干啥 |
|---|---|
| `install [full\|config]` | 旧世界整装流水线（配置 + 壁纸插件 + 钩子重放）；后由 `on <plugin>` 接管 |
| `update [--force\|--no-deploy] [--to <tag\|commit>]` | 拉新版本 + 重新部署（KM5：线性迁移机制已清算，账本即真相）；`--to` 锁到指定版本（system 模式 → 提示 pacman）。部署走所有权 carry（#139）：用户改动与自放文件原样搬入、Ghost 插件冻结并提示 `on` 收编；`--force` = 采纳模板侧（payload 名全部认领 + 账本重登记），不是清剿 |
| `use <plugin> …` | 见上「插件动词」表（形态轴唯一入口） |
| `theme [toggle\|dark\|light\|sync\|status]` | 原生切换/同步深浅主题（纯 Python 调度 gsettings、GTK settings.ini、Noctalia IPC 与 Kitty 信号） |
| `shell [get\|set <noctalia\|nyxuri-shell> [bin_path]\|switch [\|bin_path]\|status]` | 查看或切换桌面外壳运行插槽。**[EXPERIMENTAL]** nyxuri-shell 开发中，输出带实验性警告 |
| `deps [core]` | 装软件包：核心依赖勾选单（可选软件供给面已随 R0-2 步 5 处决，插件装包走 `on <plugin>`） |
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

## 已处决（KM3.5 + KM5 + R0-2 + R0-3，调用即 unknown command）

KM3.5：`deploy` `backup` `restore` `remove` `purge` `recommended` `apps` `wp` `wallpapers`
`report` `-h/--help`，以及幽灵指针 `greeter` `fcitx` `gtk` `fisher`。
KM5：系统软链与用户端别名 `nyxniri`、`NYXNIRI_*` 环境变量回退（原「兼容别名」节随
`migrations/` 清算一并处决——一个变量一个前缀 `NYXURI_*`）。
替代能力：`on/off <plugin>`（插件能力，装包同路）、`snapshot`/`rollback`/`uninstall`（状态域）、
`bug`（诊断）；壁纸能力 = `on wallpapers`
（外部大包走 `plugins/wallpapers/hooks/install-pack`）。
R0-2 步 5：`deps apps`（可选软件菜单）处决——推荐软件不再有专用安装入口，
`deps` 收敛为核心依赖勾选单（`deps [core]`）。
R0-3：`preset` 命令别名与 `on --preset` 旗标处决——形态切换入口收敛为 `use`，启用形态参数收敛为 `--form`。

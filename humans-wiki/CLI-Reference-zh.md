`nyxuri` 管理安装、快照和系统诊断。交互式部署默认先在 `~/.config/nyxuri/backups/` 创建快照。

> 旧版 Bash 用户需先运行新版引导，再用以下命令；旧版 `nyxniri update` 无法完成目录迁移。

---

## 插件动词

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri list [插件]` | 插件全景（开关状态 × 当前形态），或单个插件详情 |
| `nyxuri on <插件> [--form <形态>]` | 启用插件（先披露依赖与缺失包），等价 `enable`；`--preset` 为 deprecated 别名 |
| `nyxuri off <插件> [--cascade]` | 停用插件——自定义文件收存、受管文件抹净，等价 `disable` |
| `nyxuri use <插件> [list\|<形态>\|save\|edit\|delete\|slots\|slot <轴> <变体>]` | 切换 / 管理形态（详见 [形态与槽位轴](Forms-zh)）；`preset` 命令为 deprecated 别名 |
| `nyxuri doctor [插件]` | 插件三态对账（`Synced` / `Drifted` / `Ghost`）+ 系统体检 |

桌面上一切皆插件——壁纸也是：`nyxuri on wallpapers` 部署内置 fallback 到
`~/Pictures/Wallpapers`；完整视频包属用户内容，用 `plugins/wallpapers/hooks/install-pack` 安装。

---

## 部署与主题

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri install [full\|config]` | 旧式整装流水线（配置 + 壁纸插件 + 钩子重放），或只同步配置 |
| `nyxuri update [--force\|--no-deploy] [--to <tag\|commit>]` | 更新源码，强制部署或跳过；`--to` 锁定版本 |
| `nyxuri theme [toggle\|dark\|light\|sync\|status]` | 切换或同步系统深浅主题 |
| `nyxuri shell [get\|set <noctalia\|nyxuri-shell> [bin_path]\|switch [<目标> [bin_path]]\|status]` | 查看或热切换桌面外壳插槽（实验性） |

---

## 供给

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri deps [core\|apps]` | 核心依赖勾选单，或常用软件勾选单（Nautilus / Steam 等 18 款，同为插件声明） |
| `nyxuri pkg <install\|upgrade\|remove\|search\|info\|installed>` | 包管理直通；搜索支持 `aur` / `pac` 前缀 |
| `nyxuri clean [-n] [--only <任务>]` | 缓存清理；`-n` 只预览 |

---

## 快照

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri snapshot [备注]` | 保存当前配置快照 |
| `nyxuri snapshot list` | 查看快照列表 |
| `nyxuri snapshot delete [序号]` | 删除快照（未指定序号则可批量勾选） |
| `nyxuri rollback [序号]` | 恢复历史快照 |

---

## 系统

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri doctor [插件]` | 插件对账 + 依赖与系统健康检查 |
| `nyxuri bug` | 生成诊断报告 |
| `nyxuri test` | 开发者沙箱测试部署（不备份、保留 monitor.kdl） |
| `nyxuri uninstall [--all\|standard\|restore\|purge]` | 勾选式卸载——逐项选择清理内容（亦可直接传入 standard、restore、purge、--all 直达） |
| `nyxuri help` | 显示命令行帮助与用法 |

---

## 已处决的旧名（KM3.5）

`deploy` `backup` `restore` `remove` `purge` `recommended` `apps` `wp` `wallpapers`
`report` 与模块动词 `greeter` `fcitx` `gtk` `fisher` 已全部退役——调用即未知命令。
请改用插件动词（`on` / `off` / `use`）与状态动词（`snapshot` / `rollback` / `uninstall`）。

---

## 终端速查手册 nyxhelp

`nyxhelp` 是基于 `fzf` 的简明速查，覆盖 CLI、Shell 助手和核心快捷键：

| 指令 | 作用 |
| :--- | :--- |
| `nyxhelp` | 双栏交互式速查菜单 |
| `nyxhelp keys` | Niri 快捷键 |
| `nyxhelp proxy` | 代理控制（`proxy_on [port]`、`proxy_off`、`proxy_status`） |
| `nyxhelp pkg` | 包管理快捷指令（`up`、`in`、`se`、`un`、`clean`） |
| `nyxhelp all` | 完整速查手册 |

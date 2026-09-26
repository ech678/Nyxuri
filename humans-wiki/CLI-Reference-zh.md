`nyxuri` 管理安装、快照和系统诊断。交互式部署默认先在 `~/.config/nyxuri/backups/` 创建快照。

> 旧版 Bash 用户需先运行新版引导，再用以下命令；旧版 `nyxniri update` 无法完成目录迁移。

---

## 顶层

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri` | 交互式菜单 |
| `nyxuri test` | 开发者实机测试部署（不备份、保留 monitor.kdl） |

---

## 部署

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri install [full\|config]` | 全量部署，或只同步配置 |
| `nyxuri update [--force\|--no-deploy]` | 更新源码，并强制部署或跳过配置部署 |

---

## 快照

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri snapshot [备注]` | 保存当前配置快照 |
| `nyxuri snapshot delete [序号]` | 删除快照（未指定序号则可批量勾选） |
| `nyxuri rollback [序号]` | 恢复历史快照 |
| `nyxuri list` | 查看快照列表 |

---

## 系统

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri doctor` | 依赖与系统健康检查 |
| `nyxuri deps` | 打开依赖检查与安装菜单 |
| `nyxuri apps` | 常用软件安装菜单（按用途分组：浏览器、社交通讯、游戏等） |
| `nyxuri wallpapers` | 从外部仓库下载全套壁纸和动态视频包 |
| `nyxuri theme [toggle\|dark\|light\|sync\|status]` | 切换或同步系统深浅主题 |
| `nyxuri bug` / `nyxuri report` | 生成诊断报告 |

---

## 卸载

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri uninstall [--all\|standard\|restore\|purge]` | 勾选式卸载——逐项选择清理内容（配置、CLI、模块、快照、壁纸），默认勾选等同标准范围 |
| `nyxuri purge` | `uninstall --all` 的简写 |

---

## 扩展

| 指令 | 作用 |
| :--- | :--- |
| `nyxuri fcitx [install\|status\|uninstall]` | NyxMellow fcitx5 皮肤 |
| `nyxuri greeter [install\|status\|uninstall]` | Noctalia Greeter（登录界面） |
| `nyxuri gtk [install\|status\|uninstall]` | Material You GTK3/4 主题 |
| `nyxuri fisher [install\|status\|uninstall]` | Fish 的 fisher 插件管理器 |

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

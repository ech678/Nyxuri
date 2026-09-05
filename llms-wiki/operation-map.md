# Operation Map — 全部 CLI 命令

> 命令分发在 `nyxniri/cli.py` 的 `COMMANDS` dict。退出码自动传播。aliases 并列。

## 管"配置内容"的

| 命令 | 干啥 |
|---|---|
| `install [full\|config]`（alias `deploy`） | 部署配置（full = + 壁纸 + 模块） |
| `update [--force\|--no-deploy] [--to <tag\|commit>]` | 拉新版本 + 重新部署;`--to` 锁到指定版本（system 模式 → 提示 pacman） |
| `preset <app> [list\|apply <name>\|save <name>\|edit <name>\|delete <name>]` | 切/管理预设 |

## 管"安装方式"的

| 命令 | 干啥 |
|---|---|
| `deps [core\|apps]` | 装软件包 |
| `apps`（alias `recommended`） | 装可选软件 |
| `wallpapers`（alias `wp`） | 装壁纸包 |
| `<module> [install\|status\|uninstall]` | fcitx / fisher / greeter / gtk 四件套模块（动态 import `nyxniri.modules.<name>`，其中 `gtk` 映射至 `gtktheme`） |
| `theme [toggle\|dark\|light\|sync\|status]` | 切换/同步深浅主题 |

## 管"状态"的

| 命令 | 干啥 |
|---|---|
| `snapshot [note]`（alias `backup`） | 存档当前配置 |
| `rollback [index]`（alias `restore`） | 从存档恢复 |
| `list` | 看所有存档 |
| `doctor` | 体检（_check_* 列表） |
| `uninstall [--all\|standard\|restore\|purge]`（alias `remove`）/ `purge` | 卸载（勾选式） |
| `bug`（alias `report`） | 导出诊断报告 |
| `test` | 开发者沙箱部署测试 |
| `help` | 用法 |

## 三层配置模型是内容侧的灵魂

三层（configs < presets < customs）是内容侧，其他都是围绕它的操作。详见
[overview](overview.md)、[preset-mechanism](preset-mechanism.md)。

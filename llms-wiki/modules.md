# Modules — 可选扩展模块与生命周期契约

> 除了基础 dotfiles 部署外，Nyxuri 提供一系列系统级可选组件（输入法皮肤、登录管理器、Shell 插件、GTK 主题）。
> 源码：`nyxuri/modules/`。

## 模块列表与职责

| 模块 | 源码文件 | 核心职责 |
|---|---|---|
| **fcitx** | `modules/fcitx.py` | 安装/卸载 NyxMellow 输入法皮肤，支持跟随暗色/亮色模式切换，防 reload 重复拉起守护进程 |
| **greeter** | `modules/greeter.py` | Noctalia greetd 登录界面集成，接管 `/etc/greetd/config.toml`，配置备份与 Polkit 免密规则 |
| **fisher** | `modules/fisher.py` | Fish shell 插件管理，免 root 自动化引导并固定插件版本 |
| **gtktheme** | `modules/gtktheme.py` | 基于 Material You 调色板渲染 GTK3/GTK4/Libadwaita 主题与 `settings.ini` |

## 生命周期与异常边界 (`lifecycle.py`)

所有模块的入口函数均通过 `@module_action` 装饰器纳管：

```python
def module_action(action):
    """Expected file/config failures return False; interruption still propagates."""
    @wraps(action)
    def run(*args, **kwargs) -> bool:
        try:
            return action(*args, **kwargs)
        except (OSError, ValueError, configparser.Error) as error:
            log_msg("ERROR", f"{action.__name__}: {error}")
            print(text(f"操作未完成: {error}", f"Operation incomplete: {error}"))
            return False
    return run
```

### 契约约定：
1. **已知可预期失败收敛**：权限不足、配置损坏、磁盘 I/O 错误等（`OSError`, `ValueError`, `configparser.Error`）捕获后记录日志并输出双语提示，返回 `False`，避免粗暴 crash 导致终端损坏。
2. **意外异常与中断透传**：`KeyboardInterrupt`、`SystemExit` 等控制流信号严格不吞，保证终端光标清理钩子与事务中断能够正常响应。

## 模块标准化结构

每个扩展模块统一暴露标准动作：
- `*_install()`：安装、部署配置文件、注册系统服务或应用模板（在执行写磁盘前展示 Pre-flight Checklist）。
- `*_status()` / `is_*_installed()`：探测当前实机是否处于已安装状态。
- `*_uninstall()`：完整还原原系统配置，恢复备份，清理状态标记，实现无残留卸载。

### 细粒度解耦动作（以 Fcitx 为例）：
为捍卫知情权与零强加原则，复杂模块将“素材部署”与“设为默认”解耦：
- `fcitx_deploy_assets()` / `nyxuri fcitx deploy`：仅释放皮肤素材并注册模板，不静默改写当前主题；
- `fcitx_activate()` / `nyxuri fcitx activate`：显式将已部署的主题设为活动主题；
- `setup_rime_ice()`：由 `.optional-apps.toml` 的 `post_install` 钩子自动触发，挂载雾凇拼音方案、预编译 schema 并写入 profile。

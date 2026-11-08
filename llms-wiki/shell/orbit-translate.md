# Orbit Translate — 外迁工具边界

> 划词翻译浮窗独立于 Nyxuri：开发、测试、CI、issue、文档在上游
> [WALKERKILLER/orbit-translate](https://github.com/WALKERKILLER/orbit-translate)
> （R0-5 取消自带；PDF 划词问题随迁上游 issue #1）。S1-4 起上游声明 `manifest.toml`，
> 由 `nyxuri add <repo-url>`（裸名 `orbit-translate`）直接接管，物理落位于 Nyxuri
> 数据域 `~/.local/share/nyxuri/plugins/orbit-translate/`。

## Nyxuri 接线契约（S1-4 终态）

- 插件管理：`nyxuri add <git-url>`、`nyxuri on orbit-translate`。
- 网关动态解析：`Alt+E` → `binds.kdl` → `shell-action.sh translate` 通过 `find_action_tool`
  按动作动态命中执行体（零硬编码，老安装 `~/.config/noctalia/tools/` 保留兼容兜底）。
- Orbit 菜单 `translate` 项 → `niri-scratch-toggle.sh` → 设置 TUI（动态寻路交付 Kitty 浮窗）。
- 巡检与诊断：`nyxuri doctor` 动态巡检插件脚本执行权限，并校验 GtkLayerShell 环境。

工具未安装时动作失败但不影响其他功能，装回即恢复。契约细节以上游
`llms-wiki/nyxuri-integration.md` 为准，测试钉在
`tests/shell/test_shell_switcher.py` 与 `tests/desktop/test_config_scripts.py`。

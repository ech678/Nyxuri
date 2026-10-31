# Orbit Translate — 外迁工具边界

> 划词翻译浮窗完全独立于 Nyxuri：开发、测试、CI、issue、文档、安装器全部在上游
> [WALKERKILLER/orbit-translate](https://github.com/WALKERKILLER/orbit-translate)
> （R0-5 取消自带；PDF 划词问题随迁上游 issue #1）。Nyxuri 不携带 payload，
> 用户经上游 `./install.sh` 自装；S1 落地后由 `nyxuri add <repo-url>` 接管安装
> （接入清单见 ROADMAP S1）。

## Nyxuri 保留的接线（S1 前维持现状）

- 部署位置契约：`~/.config/noctalia/tools/`（上游 install.sh 与历史部署同位）
- `Alt+E` → `binds.kdl` → `shell-action.sh translate`
- Orbit 菜单 `translate` 项 → `niri-scratch-toggle.sh` → 设置 TUI
- noctalia manifest 包声明：python-gobject / gtk-layer-shell / wl-clipboard
  （外部安装的翻译器仍依赖）

工具未安装时动作失败但不影响其他功能，装回即恢复。契约细节以上游
`llms-wiki/nyxuri-integration.md` 为准，测试钉在
`tests/shell/test_shell_switcher.py` 与 `tests/desktop/test_config_scripts.py`。

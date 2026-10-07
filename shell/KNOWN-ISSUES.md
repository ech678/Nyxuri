# 已知问题与暂缓缺口

> Nyxuri Shell 完全处于开发阶段，已知问题较多，外观尚未开发，暂不推荐日常使用。
> 本页只记录「现在哪里是坏的」和「今天跳过了什么」；修一个勾一个，不修也不碍事。
> 架构契约见 [AGENTS.md](AGENTS.md)，阶段计划见 [ROADMAP.md](ROADMAP.md)。

## 未修复 BUG

- [ ] （待登记：症状一句话 + 复现路径 + 发现日期）

## 基础设施缺口（快速上线时跳过，回来先做这些）

- [ ] **TUI 未接入**：`menus.py` 无 shell 切换菜单，`translations.toml` 无桌面外壳词条；目前只有 CLI `nyxuri shell` 一条路
- [ ] **quickshell 依赖未声明**：不在任何 package manifest，目前靠 `noctalia` AUR 包传递引入；单独选用 nyxuri-shell 时 deps 体系无感知
- [ ] **卸载残留**：`state/uninstall.py` 只清 `~/.local/bin/nyxuri`，不清 `~/.local/bin/nyxuri-shell` 软链（违反 H7 无残留）

## 已修复

- （空）

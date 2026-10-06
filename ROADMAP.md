# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段台账、已确认决策与门禁见
> [shell/ROADMAP.md](shell/ROADMAP.md)。历史全景见
> [archive/roadmap-history](llms-wiki/archive/roadmap-history.md)；
> 设计哲学见 [vision](llms-wiki/vision.md)。

## 自研 Shell（当前：R12 文档架构重塑）

- 阶段台账与当前进度：见 [shell/ROADMAP.md](shell/ROADMAP.md)，此处不复述。
- [ ] **原生壁纸管理与 M3 调色直出**：Shell 模式下算法直出同构 `palette.toml`，无需外部 Python GUI 伴生脚本（P4 交付；启动器与壁纸域已在 R4-C 完成代码自治）。
- [x] **六大标准动作与双 Shell 切换**：`launcher` / `session` / `settings` / `clipboard` / `lock` / `wallpaper-random` 经 `shell-action.sh` 零改动响应；`nyxuri shell set` 热切换与异常安全回滚已交付（P1/P2，证据见 Shell 台账）。
- [ ] **Noctalia Template 兼容 (TemplateAdapter)**：支持 Jinja 风格模板规范与变量命名空间，GTK CSS、Fcitx SVG、Kitty、Starship 和用户模板无需重写（P4 交付）。
- [ ] **Noctalia + Wallpaper Picker 协同稳固验收**：双轨方案互不干扰、各自纯白（P5 验收）。

## Shell 后生态

- [ ] **TUI 视觉风格化与纯净感 (Terminal Rice)**：Alternate Screen Buffer 保护终端历史，DEC 2025 协议消除高刷频闪，单行微动 Zen Spinner 就地收拢滚屏日志。
- [ ] **多合成器 (Multi-WM) 架构解耦**：`CompositorDriver` 驱动抽象层，热重载、浮动便签与屏幕探测跨合成器适配（Hyprland/Sway 按需扩展），`doctor` 诊断与 `greeter` 会话自适应。
- [ ] **安全 Downdate 体系（高级储备）**：现场快照优先还原 + Git 逆向检出的安全版本回退。

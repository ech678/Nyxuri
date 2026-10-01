# Nyxuri 活跃演进路线与待办

> 历史全景痛点、已治理病灶与阶段 0-3 已完成事项已全面归档至 [llms-wiki/archive/roadmap-history.md](llms-wiki/archive/roadmap-history.md)。
> 设计哲学与核心原则见 [llms-wiki/vision.md](llms-wiki/vision.md)。

---

## 活跃进行中：自研 Shell 阶段

> 设计宣言原文、相关目标与详细阶段见 [Shell ROADMAP](shell/ROADMAP.md)；开发约束见 [Shell AGENTS](shell/AGENTS.md)。

### 1. 开发 Shell 时 (During Shell Development)
> **核心目标**：专注自研 Material You Shell 本体，以及它与现有契约的连接。

- [ ] **原生内置启动器、壁纸管理与 M3 调色引擎**：原生承载应用启动检索与壁纸管理；算法直出同构 `palette.toml`，在自研 Shell 模式下无需安装任何外部 Python GUI 伴生脚本；
- [ ] **兼容 Noctalia Template 系统 (TemplateAdapter)**：支持其 Jinja 风格模板规范与变量命名空间，让现有 GTK CSS、Fcitx SVG、Kitty、Starship 和用户模板无需重写；
- [ ] **Shell 生命周期与动作响应网关对接**：打通与 `session-shell.sh` 的守护拉起及 `shell-action.sh` 的 6 大标准动作（`launcher` / `session` / `settings` / `clipboard` / `lock` / `wallpaper-random`）IPC/CLI 接口，外围快捷键零改动即刻响应。
- [ ] **双 Shell 切换 (`nyxuri shell set`)**：支持 `nyxuri shell set <noctalia|custom>` 或快捷键切换 Noctalia 与自研 Shell；可靠即时切换提前在 Shell P1 交付，完整生态协同在 P5 验收。

---

### 2. 开发 Shell 后 (Post-Shell Ecosystem & Polish)
> **核心目标**：在自研 Shell 雏形落地后，完善双轨切换心流、终端美学跃迁、多合成器生态解耦与版本安全降级。

- [ ] **Noctalia + Wallpaper Picker 协同方案稳固验收**：验证 Noctalia 模式下伴生套件的按需部署与运行，确保双轨方案互不干扰、各自纯白；
- [ ] **TUI 视觉风格化与纯净感 (Terminal Rice)**：接入 Alternate Screen Buffer（`\033[?1049h/l`）保护终端历史（运行 `doctor` / 查看快照不被抹除），DEC 2025 协议消除高刷频闪撕裂，引入单行微动 Zen Spinner 就地收拢命令滚屏日志；
- [ ] **多合成器 (Multi-WM) 架构解耦与驱动抽象**：构建 `CompositorDriver` 驱动抽象层，实现热重载、浮动便签与屏幕探测的跨合成器适配（Hyprland/Sway 等按需扩展），`doctor` 诊断与 `greeter` 会话自适应；
- [ ] **安全 Downdate 体系（高级储备）**：落地基于现场快照优先还原与 Git 逆向检出的安全版本回退机制。

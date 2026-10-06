# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段台账、已确认决策与门禁见
> [shell/ROADMAP.md](shell/ROADMAP.md)。历史全景见
> [archive/roadmap-history](llms-wiki/archive/roadmap-history.md)；
> 设计哲学见 [vision](llms-wiki/vision.md)。

## 自研 Shell（当前：R12 文档架构重塑）

- 阶段台账与当前进度：见 [shell/ROADMAP.md](shell/ROADMAP.md)，此处不复述。
- [ ] **原生壁纸管理与 MD3 取色内生**：壁纸域自治之上取色引擎可插拔——短期经契约层走 matugen，长期以 material-color-utilities 纯 JS 移植替换并退役 matugen，直出色板契约、无外部取色二进制（P4 落契约、后置收口；启动器与壁纸域已在 R4-C 完成代码自治）。
- [x] **六大标准动作与双 Shell 切换**：`launcher` / `session` / `settings` / `clipboard` / `lock` / `wallpaper-random` 经 `shell-action.sh` 零改动响应；`nyxuri shell set` 热切换与异常安全回滚已交付（P1/P2，证据见 Shell 台账）。
- [ ] **Noctalia Template 兼容与主题契约 (TemplateAdapter)**：落地 palette JSON 色板契约与 Noctalia 模板规范（`{{ }}` 表达式、`<* *>` 块与过滤器）适配层，GTK CSS、Fcitx5、Kitty、Starship 和用户模板无需重写；深浅模式系统同步收敛到 `nyxuri theme` 单一实现；运行时不依赖 noctalia 二进制（P4 交付）。
- [ ] **Noctalia + Wallpaper Picker 协同稳固验收**：双轨方案互不干扰、各自纯白（P5 验收）。

## Shell 后生态

- [ ] **TUI 视觉风格化与纯净感 (Terminal Rice)**：Alternate Screen Buffer 保护终端历史，DEC 2025 协议消除高刷频闪，单行微动 Zen Spinner 就地收拢滚屏日志。
- [ ] **多合成器 (Multi-WM) 架构解耦**：`CompositorDriver` 驱动抽象层，热重载、浮动便签与屏幕探测跨合成器适配（Hyprland/Sway 按需扩展），`doctor` 诊断与 `greeter` 会话自适应。
- [ ] **安全 Downdate 体系（高级储备）**：现场快照优先还原 + Git 逆向检出的安全版本回退。

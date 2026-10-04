# Nyxuri 活跃演进路线与待办

> 历史全景痛点、已治理病灶与阶段 0-3 已完成事项已全面归档至 [llms-wiki/archive/roadmap-history.md](llms-wiki/archive/roadmap-history.md)。
> 设计哲学与核心原则见 [llms-wiki/vision.md](llms-wiki/vision.md)。

---

## 活跃进行中：自研 Shell 阶段

> 设计宣言原文、相关目标与详细阶段见 [Shell ROADMAP](shell/ROADMAP.md)；开发约束见 [Shell AGENTS](shell/AGENTS.md)。

### 1. 开发 Shell 时 (During Shell Development)
> **核心目标**：专注自研 Material You Shell 本体，以及它与现有契约的连接。

- [ ] **原生内置启动器、壁纸管理与 M3 调色引擎**：原生承载应用启动检索与壁纸管理；算法直出同构 `palette.toml`，在自研 Shell 模式下无需安装任何外部 Python GUI 伴生脚本；（注：启动器与壁纸域已在 R4-C 完成代码自治，全面解耦 Native 插件走向纯 QML，M3 调色直出留待 P4 阶段）
- [ ] **兼容 Noctalia Template 系统 (TemplateAdapter)**：支持其 Jinja 风格模板规范与变量命名空间，让现有 GTK CSS、Fcitx SVG、Kitty、Starship 和用户模板无需重写；（计划在 P4 阶段交付）
- [x] **Shell 生命周期与动作响应网关对接**：打通与 `session-shell.sh` 的守护拉起及 `shell-action.sh` 的 6 大标准动作（`launcher` / `session` / `settings` / `clipboard` / `lock` / `wallpaper-random`）IPC/CLI 接口，外围快捷键零改动即刻响应。（已在 P1/P2 阶段完成对接，单测覆盖命令参数与守护脚本形状）
- [x] **双 Shell 切换 (`nyxuri shell set`)**：支持 `nyxuri shell set <noctalia|custom>` 或快捷键切换 Noctalia 与自研 Shell；可靠即时切换提前在 Shell P1 交付，完整生态协同在 P5 验收。（CLI、热切换、异常安全回滚与状态落盘已全面交付并通过单测验证）
- [x] **极简减负与负资产大清扫 (P3-R11 / P3-R12)**：彻底切除上游个人网盘（rclone）、3.9MB 内置变体字体（回退系统字体栈）、繁体中文字典（统一 zh_CN）、搜索引擎与死图片资产；shell/assets 体积缩减 75%（6.1MB → 1.5MB）；切除 paru 30m 查包与多项常驻后台轮询。
- [x] **全面去 C++ 与纯 QML 架构收口 (R4-C-01 ~ R4-C-06)**：彻底移除 113 项自有 C++ 插件与 CMake 构建体系（免除 cmake/ninja/gcc/clang 编译依赖）；架构彻底收敛为 `app/` -> `modules/` -> `shared/` 三级纯 QML 体系；Niri 确立单一运行时状态源（`NiriService`）；生命周期审计 0 违规，全量单测与沙箱部署全绿。
- [x] **资源治理、文档契约与五分类测试套件 (R5-01 ~ R5-03)**：彻底清除废弃 FA 图标与 SvgIcon.qml，修复 Zen 着色器离线预编译（zen-palette.frag.qsb），归档历史恢复比对文档；建立 run-tests.py 分类测试运行器（STATIC/LOGIC/RESOURCE/NATIVE/GRAPHICS），五分类独立运行全绿通过无跳过。（已于 c4fc653 交付）
- [x] **纯 QML/JS 动态国际化闭环 (Pure QML/JS I18n Closure)**：彻底切除对 Qt C++ Linguist / .qm 二进制的隐式运行时依赖；在 `shared/i18n/` 建立纯 QML 单例 `I18n.qml` 与 `Translations.js` 内存字典，引入纯脚本 `Toml.js` 实现启动时直接热解析 `zh_CN.toml`；全库 228 个 QML/JS 源码文件 100% 迁出 `qsTr`/`qsTranslate` 直通 `I18n.tr`，实现真正的零 Native 编译、离线零依赖多语言热切换。
- [x] **能耗基线、事件循环与稳态治理 (R6-01 ~ R6-03)**：彻底淘汰 48.5MB (3,806 文件) 的 meteocons 外部包，采用 Material Symbols 纯字体方案做极致减法；MPRIS DBus 建立订阅式引用计数与安全注销，根除断联日志风暴；清零全库 Timer interval: 0 隐式空转并降频高频秒表；静态审计新增 LIFE007/LIFE008 门禁；单测契约与五分类测试全绿。


---

### 2. 开发 Shell 后 (Post-Shell Ecosystem & Polish)
> **核心目标**：在自研 Shell 雏形落地后，完善双轨切换心流、终端美学跃迁、多合成器生态解耦与版本安全降级。

- [ ] **Noctalia + Wallpaper Picker 协同方案稳固验收**：验证 Noctalia 模式下伴生套件的按需部署与运行，确保双轨方案互不干扰、各自纯白；
- [ ] **TUI 视觉风格化与纯净感 (Terminal Rice)**：接入 Alternate Screen Buffer（`\033[?1049h/l`）保护终端历史（运行 `doctor` / 查看快照不被抹除），DEC 2025 协议消除高刷频闪撕裂，引入单行微动 Zen Spinner 就地收拢命令滚屏日志；
- [ ] **多合成器 (Multi-WM) 架构解耦与驱动抽象**：构建 `CompositorDriver` 驱动抽象层，实现热重载、浮动便签与屏幕探测的跨合成器适配（Hyprland/Sway 等按需扩展），`doctor` 诊断与 `greeter` 会话自适应；
- [ ] **安全 Downdate 体系（高级储备）**：落地基于现场快照优先还原与 Git 逆向检出的安全版本回退机制。

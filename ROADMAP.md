# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段、D 卷明细与验收积压唯一见
> [shell/ROADMAP.md](shell/ROADMAP.md)。设计契约唯一见
> [design-system](llms-wiki/shell/design-system.md)。
> 状态词只用五态；历史明细只在 archive，此处不复述。

## 卷宗结构

| 卷 | 内容 | 状态 |
| --- | --- | --- |
| 第一卷「插件市场化改造」KM0–KM5 | 内核（registry · store · engine · catalog）+ 万物皆插件 + 单一真相 | 已完成（台账冻结于 [roadmap-history](llms-wiki/archive/roadmap-history.md)） |
| 第二卷「架构重塑与三方插件」G0–S1 | 定名 Plugin、Omarchy 五件套骨架整抄、S1 第三方生命周期 | 已完成（台账冻结于 [reconstruction-history](llms-wiki/archive/reconstruction-history.md)） |
| 第三卷「架构整理」P0–P5 | 根目录纯度、插件控制面、解耦、TOML 统一、引擎四域、并发审查 | 已完成（明细已迁入 [roadmap-history](llms-wiki/archive/roadmap-history.md)） |
| 第四卷「设计统一」D0–D5 | Material You 契约、bar 收尾与快修、SystemIcons QS 化、联动层、自定义引擎、跨表面过堂 | 进行中（唯一明细见 [shell/ROADMAP](shell/ROADMAP.md)） |

## 活跃路线（执行序即优先级）

| 站 | 交付 | 状态 |
| --- | --- | --- |
| D卷 | 设计统一：契约基石 → bar 快修 → SystemIcons QS 化 → 自定义引擎（D4a–D4h）→ 跨表面统一与联动（D5） | 进行中 |
| T4 | Shell 可控性与透明化（开工时立细则） | 待开始 |
| T5 | 多合成器解耦（门禁触发型） | 待开始 |
| T2 | TUI Textual inline 重写：美学定稿 → inline 实测 → 引擎/界面接缝 → 逐屏 → 旧界面退役 → 实机验收 | 进行中 |

### T4 Shell 可控性与透明化（立项三件套）

- **T4-1 启动可见性**：`Terminal=true` 与桌面应用经 `xdg-terminal-exec` / `gio open`
  启动失败时，由发后即忘升级为状态捕获与用户通知反馈，终态消除「点击无声无息失败」。
- **T4-2 运行时透明度**：`nyxuri doctor` 与 `shell status` 输出插件挂载几何插槽状态、
  IPC 连通性与事件延迟指标。
- **T4-3 异常隔离**：UI 插件或脚本运行时崩溃时局部熔断隔离并上报错误横幅，
  主宿主与其它常驻插槽不瓦解。

### T5 多合成器解耦

S0 的 niri 适配层（`CompositorDriver` + `NiriDriver` 单文件方言）已兑现前置；
第三个合成器接入前收编残余字面量（债务登记见
[delayed-decisions](llms-wiki/delayed-decisions.md)）。

### T2 TUI Textual inline 重写

从零重写，形态参照 Claude Code / Codex CLI 的“记录 + 活动区”（原地展开，退出后历史还在），
版式参照 Omarchy 安装器的居中栏。
`archive/t2-textual-market` 与 `refactor/t2-tui-pytermgui` 两条分支放弃，代码不沿用。
视觉契约见 [tui-design-system](llms-wiki/tui-design-system.md)，交互原则见
[tui-charter](llms-wiki/tui-charter.md)。

**边界**

- 引擎（`nyxuri/` 除 `nyxuri/tui/` 外）保持纯标准库；`textual` 只许出现在 `nyxuri/tui/`，测试静态断言。
- `python-textual`（Arch `extra`）进 PKGBUILD `depends`；launcher 去掉 `-S`，保留 `-I`。
- 所有 CLI 动词不经过 Textual 也能跑：引擎里的交互统一走纯标库行式基座。
- 无参数启动走 Textual；导入失败打印一行原因并退出，不悄悄降级。
- TUI 只是 `state.json` / catalog 的投影，动作走 `engine`，文案复用 `format_steps`。
- **操作全覆盖**：`COMMANDS` 每个动词在 TUI 里都有入口；TUI 内绝不掉回行式提示或让用户“去运行 CLI”
  （细则与例外见 [tui-design-system](llms-wiki/tui-design-system.md) §6）。

**Textual 依据（基线 `python-textual 8.2.8`）**

实现只用下表里有文档或源码出处的能力；表外的东西不自己发明，先查
[Textual 文档](https://textual.textualize.io/)，查不到就列进“待实测”，M1 跑出结论再用。

| 设计需求 | Textual 能力 | 出处 |
| --- | --- | --- |
| 原地展开 | `App.run(inline=True)` | [Style Inline Apps](https://textual.textualize.io/how-to/style-inline-apps/) |
| 退出后历史还在 | `run(inline_no_clear=True)` | [App Basics](https://textual.textualize.io/guide/app/)；`app.py` `run_async` 参数 |
| 鼠标不追踪 | `run(mouse=False)` | `App.run` 签名 |
| 去掉顶部空行 | `INLINE_PADDING = 0` | Style Inline Apps |
| inline 专属样式 | `:inline` 伪类；`Screen:inline` 默认带上下 `tall` 边框，需覆盖为 `none` | Style Inline Apps；`screen.py` 默认 CSS |
| 跟随终端 16 色 | `ansi_color=True` + `ansi_*` 颜色；`register_theme()` 注册自有主题 | [Themes](https://textual.textualize.io/guide/design/) |
| 强调色 = magenta | 内置 `ansi-dark` 的 accent 是 `ansi_green`，不合用；自有主题以 `ansi-dark` 为底，`accent` / `primary` 改 `ansi_magenta` | `theme.py` `BUILTIN_THEMES` |
| 居中栏 | `Screen { align: center top; }` + 容器 `width: 72; max-width: 100%` | [Center things](https://textual.textualize.io/how-to/center-things/)；[Align](https://textual.textualize.io/styles/align/)、[Max-width](https://textual.textualize.io/styles/max_width/) |
| 单选 / 菜单 | `OptionList` | [OptionList](https://textual.textualize.io/widgets/option_list/) |
| 多选 / 勾选 | `SelectionList` | [SelectionList](https://textual.textualize.io/widgets/selection_list/) |
| 输入 | `Input` | [Input](https://textual.textualize.io/widgets/input/) |
| 装包日志尾 | `Log` | [Log](https://textual.textualize.io/widgets/log/) |
| spinner | `LoadingIndicator` | [LoadingIndicator](https://textual.textualize.io/widgets/loading_indicator/) |
| 文本 / 详情行 | `Static` / `Label` | [Static](https://textual.textualize.io/widgets/static/) |
| 引擎调用不卡界面 | `run_worker()` / `@work(thread=True)` | [Workers](https://textual.textualize.io/guide/workers/) |
| 键位 | `BINDINGS` / actions | [Input](https://textual.textualize.io/guide/input/)、[Actions](https://textual.textualize.io/guide/actions/) |
| 结束并返回结果 | `App.exit(result, return_code, message)` | `App.exit` |
| 测试 | `run_test()` + `Pilot` | [Testing](https://textual.textualize.io/guide/testing/) |

**已知限制（源码核实）**

- `App.suspend()` 在 inline 模式不可用：`LinuxInlineDriver` 沿用基类 `can_suspend = False`，
  调用抛 `SuspendNotSupported`。所以 sudo / pacman / `$EDITOR` 只能放在两次 inline 运行之间，
  不能在一次运行里挂起。
- 内置 `Header` / `Footer` 和默认主题都不用，样式只写在 `nyxuri.tcss`。

**待实测（文档没写，M1 出结论前不当成事实）**

1. 同一进程里连续多次 inline `App.run()`：每次启动开销、光标位置是否接得上。
2. `inline_no_clear` 留在历史里的最后一帧长什么样，有没有残留边框或空行。
3. inline 模式下改终端宽度，重排是否干净。
4. 中文和全角符号在 `OptionList` / `SelectionList` 里的列对齐。
5. 记录区（运行之间用标准库输出）和 Textual 活动区的居中边距能不能逐列对齐。
6. Ctrl+C 中断时，inline 区域能否收干净。

任一项不过，回到 [tui-design-system](llms-wiki/tui-design-system.md) 改设计，不在代码里打补丁。

**M1 实测结论（2026-11-28，kitty + tmux，`feat/t2-textual-inline`）**

1. 通过。同进程连跑 3 次 inline，光标衔接无错位，记录紧跟；每次 ready 25–40ms，
   冷启动（`python3 -I` 到可交互）约 150 + 40ms。
2. 不符设计。`inline_no_clear=True` 把最后一帧整块（框 + 详情 + 提示行）原样留进历史，
   无残边、无空行，但与 §1/§9“历史里只剩记录”冲突。M1 实现改用默认清除，
   决定后由记录写一行结果。作者接受，§1 已改。
3. 不过。`LinuxInlineDriver` 收到 SIGWINCH 先写 `\x1b[2J` 清整屏（源码
   `linux_inline_driver.py` `on_terminal_resize`）：活动区按新宽度重新居中正确，
   但运行期间视口内已写的记录被抹空（kitty 实见两次，退出后是否复原不稳定）；
   tmux 缩窄时旧帧被重排成两份残影。作者接受，§4 已登记。
4. 通过。中文、全角字母与全角标点在 `OptionList` 里按显示宽度同列对齐。
5. 通过。100 列左边线均为第 14 列，124 列均为第 26 列；< 60 列断点去框、边距 1。
6. 通过。Ctrl+C 覆盖了 Textual 默认的 `help_quit`：活动区收净，记录写 `└ 已取消`，退出码 130。

换主题：输出只含 SGR 35 / 39 / 90（无 truecolor），`kitty @ set-colors` 改 color5 后强调色跟随。

| 期 | 交付 | 门禁 | 状态 |
| --- | --- | --- | --- |
| M0 美学定稿 | [tui-design-system](llms-wiki/tui-design-system.md)：记录 + 活动区、Omarchy 式居中栏、跟随终端 16 色（强调 = ANSI magenta）、符号、空间、交互、线框 | 作者确认后冻结，冻结前不写 TUI 代码 | 已完成 |
| M1 inline 实测 | `nyxuri/tui/` 骨架 + `nyxuri.tcss` + 自有 ANSI 主题 + 插件工坊一屏接真实数据；逐条回答上面 6 项待实测 | kitty 实机：单次 inline 运行启动 < 300ms、6 项待实测全部有结论并回写本节、换主题颜色跟随；**作者看过点头，否则停** | 已完成 |
| M2 接缝 | `deploy` / `backup` / `uninstall` / `pkg` / `net` / `clean` 不再 import `nyxuri.ui.tui`；引擎交互点抽成“提问”接口（确认 / 单选 / 多选 / 输入 / 进度），行式和 TUI 各给一份实现；`textual` 隔离断言入库 | `python3 -I -S` 导入引擎绿；路由表对应定向单测绿；TUI 实现下引擎零 `input()` 调用 | 待开始 |
| M3 全动词 | 无参数启动切到 TUI，同时 launcher 去 `-S`、PKGBUILD `depends` 加 `python-textual`（M1 合入 main 时刻意不带，免得用户先装上用不到的依赖）；主菜单覆盖全部动词：插件（list / on / off / use / add / remove / update / doctor）、整装与自更新、主题、外壳、依赖、包管理、清理、快照 / 回滚、卸载、诊断导出、语言 | 动词对等测试（`COMMANDS` ⊆ TUI 入口 − 例外）绿；各流程 pilot 测试；transaction / forms 现有测试零退化 | 待开始 |
| M4 退役 | 删 `nyxuri/ui/tui.py`、`menus.py`，清 i18n 孤儿键；同步 AGENTS 不变量 3、overview、operation-map、tui-charter、PKGBUILD、CHANGELOG | 全量回归 + 沙箱部署 | 待开始 |
| M5 验收 | 80 / 120 / 200 列逐屏过目，清过渡代码 | 作者实机确认 | 待开始 |

## 分支策略（PR #148 · Ubuntu 支持）

- PR #148（138 文件，+10519/−2532）整包暂存：自 main 建立 `legacy/ubuntu-support`，
  `gh pr edit 148 --base legacy/ubuntu-support` 后 merge（保署名）；该分支永不 rebase，
  仅作参考实现。分支操作待作者点头执行。
- 回植清单（R0-3 / S1 落地后按图索骥）：包后端窄驱动（pacman/apt、os-release 探测）、
  文件所有权账本。生命周期统一部分不回植。

## 冻结与挂起

- **Shell 功能阉割档：整档挂起（作者裁决）**。dashboard 双轨合并已划掉——双轨终局
  保留。其余候选留档备查：cookie 时钟链（约 −870）、lock 双风格链（约 −1,000）、
  通知双渲染实现合一、regionselector、PersonalizationConfig 死函数（约 −340）、
  mango 第二合成器去留、BezierCurveLayerEditor（1,153 行）、WeatherBackground（1,226 行）；
  零风险小件（约 −490 行）若迁移触及则顺带处置，不立项。

## 已收口（本卷前置）

- **T0 终端体验**：复制粘贴终审（`Ctrl+Shift+C/V` 唯一路径）；终端桥系统侧已修。
- **T1 上架 AUR**：`nyxuri-git` 上架；key-cli 废弃移除。
- **T3 设置界面替换**：Caelestia 原子套件 M0–M2 完成，M3/M4 待验收（状态见
  [shell/ROADMAP](shell/ROADMAP.md) 验收积压）。

## Shell 侧

阶段台账、D 卷分期、定案登记与门禁唯一见 [shell/ROADMAP.md](shell/ROADMAP.md)。
长期目标保留不减：启动器、壁纸/M3 调色、Noctalia TemplateAdapter、六大标准动作、
双 Shell 切换与伴生套件协同（契约见 [shell/AGENTS.md](shell/AGENTS.md)）。

## 全局门禁（每阶段验收都过）

1. 五原则验收给可复现证据（真诚透明 / 绝对主权 / 骨架包容 / 轻盈生长 /
   通用自然，见 [vision](llms-wiki/vision.md)）。
2. 单一开关真相与插件边界不变量的唯一权威在
   [plugin-model](llms-wiki/plugin-model.md) 与 [AGENTS.md](AGENTS.md)，此处只链接不复述。
3. 架构 / 命令 / manifest / 设计契约变更同步对应 wiki 页与台账（路由见 AGENTS.md）。
4. 完成声明防幻觉：状态改「已完成」前必须有独立复核命令的原始输出作证，AI 转述
   不算证据；查不出证据就不算完成，发现假象状态立即回退。

## 储备（不承诺）

- 第三方目录站、信任分级与签名——git URL 即源成立后再议。
- README 视觉素材：截图画廊（Monet 多壁纸对比 / NyxMellow / Fastfetch / Orbit）、
  SVG 字标（深浅两版，字形转路径）、特点卡片 Material Symbols 图标（入库
  `.github/assets/`，不引外链）——作者备好素材时接入。
- 安全 Downdate 体系：现场快照优先还原 + Git 逆向检出的安全版本回退。
- i18n 三处（引擎 translations.toml / shell i18n / humans-wiki 双语页）受众不同，
  低优登记不动；humans-wiki 与 operation-map 的受众重叠同理。

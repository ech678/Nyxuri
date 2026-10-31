# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段台账、当前阶段与门禁见
> [shell/ROADMAP.md](shell/ROADMAP.md)。主线「插件市场化改造」KM0–KM5 已全数
> 落地收口，整卷台账冻结于 [archive/roadmap-history](llms-wiki/archive/roadmap-history.md)；
> 设计哲学与五条简洁标准见 [vision](llms-wiki/vision.md)。

## 主线收口

「桌面插件市场」产品形态成立：内核（registry · resolver · transaction · ledger）+
目录（万物皆单元）+ 市场界面（4 动词 + TUI 工坊），安装器退役为一次性引导。
术语四词（单元 / 内核 / 源 / manifest）与内核契约的唯一权威在
[unit-model](llms-wiki/unit-model.md)，此处不复述。

## 活跃路线（执行序即优先级）

| 站 | 交付 | 状态 |
| --- | --- | --- |
| T0 | 终端体验修复：复制粘贴终审 + 终端程序启动失败可见 | 进行中 |
| T1 | 上架 AUR：单包全量 nyxuri-git | 进行中 |
| T2 | TUI 重做：Textual 全量迁移（暂缓，分支已有雏形） | 待开始 |
| T3 | 设置界面替换：Caelestia 安卓风味默认 + Dashboard 双轨 | 进行中 |
| T4 | Shell 可控性与透明化 | 待开始 |
| T5 | 多合成器 (Multi-WM) 架构解耦（门禁触发） | 待开始 |
| M1 | 单元生命周期、冲突保护与状态恢复统一 | 已完成 |
| U1 | Ubuntu 26.04 包管理、依赖声明与桌面兼容 | 已完成 |
| U2 | Ubuntu Greeter 登录与显示管理器恢复 | 已完成 |
| U3 | Ubuntu 视频壁纸播放器自动构建与安装 | 待开始 |

### T0 终端体验修复（复制粘贴最终之战）

- **复制粘贴终审（已定案：正统方案）**：`Ctrl+Shift+C/V` 为唯一复制粘贴路径，
  零劫持——kitty 三处 Windows 式劫持（`ctrl+c` 智能中断、`ctrl+v` 粘贴、
  `ctrl+a` 全选复制）全部退役，右键粘贴随 `ctrl+v` 同块一并退役（定案扩充），
  Ctrl+C/V 还给终端程序；`copy_on_select no` 保留为显式复制语义。
  **已落地（2026-10-18）**：两份 kitty.conf + 回归护栏测试；剩 fish/vim/fzf/htop
  全矩阵实机验收。一次定案，此后不再翻烧饼。
- **终端程序启动失败可见**：msedit/micro 等 `Terminal=true` 桌面项当前无声失败
  （从启动器/文件管理打开 → 什么都没有）。实机诊断根因（xdg-terminal-exec
  在位性、默认终端登记、`gio open` 行为）→ 补终端桥与默认终端登记 →
  Shell 侧启动失败给通知反馈。终态：任何文件要么打开，要么给得出
  「为什么没打开」。**系统侧已修（2026-10-18）**：`xdg-terminal-exec` 入位
  （extra 0.14.3-2），shell 启动器 / GLib（≥2.76）/ key-cli 三条打开路径的
  汇合桥补齐；Shell 侧失败通知反馈降级为待办（现 `execDetached` 即发即忘，
  非阻塞项，留待需要时或 T4 一并做）。

### T1 上架 AUR（已定案：单包全量）

- **已落地（2026-10-18，含实机冒烟）**：PKGBUILD 重构——source 加 `pkgname::` 重命名修复
  克隆目录断裂（原 PKGBUILD 从未通过 makepkg，实测实锤）；单包全量
  `shell/` 树同船（`shell.*` 单元包模式下激活，实机 `nyxuri list`/`doctor` 验证）
  + 剪枝（tests、scripts/dev、过程文档；references/ 由 .gitignore 天然隔离）+
  `CHANGELOG.md` 进包（系统模式 `get_version` 真实化）+ `/usr/bin/nyxuri-shell`
  系统入口 + 双 LICENSE + `.install` 升级提示（升级不自动重部署，`nyxuri list`
  对账、`nyxuri install full` 显式应用）。依赖策略翻转：`depends=('python')`
  引擎运行时唯一，全部单元包 + CORE/AUR 会话工具链 + `ENGINE_OPTDEPENDS`
  （quickshell）转 optdepends——pacman 不再强塞桌面，干净 chroot 从此可解；
  catalog.toml 与 PKGBUILD 脱钩（只喂 `deps apps` 菜单）。
  实机冒烟全过：`/usr/bin/nyxuri` 系统模式识别、update 拒 git pull 提示 pacman
  （顺带修复系统包无 `.git` 时误报「更新失败」的短路顺序 bug）、doctor 三态对账、
  包版 shell 冷启动 IPC ready + 零包目录写入 + qmlcache/.qsb 全落用户缓存、
  `--stop` 干净退出不扰原会话。
  key-cli 暂缓：Clavis 上游独立后端，登记 [shell/KNOWN-ISSUES](shell/KNOWN-ISSUES.md)，
  待收回仓库内化后再落依赖。
- 上架完成（2026-10-18）：AUR `nyxuri-git` 已上架（2026-10-20 更新），
  README 安装段已回填。代码与验证全数收口：makepkg 实测、干净 chroot 构建、
  namcap E 清零（假阳性定性见 [packaging/README](packaging/README.md)）。
  遗留：humans-wiki Home 顶部 AUR 安装块回填（见 packaging/README 步骤 4）。

### T2 TUI 重做（已定案：Textual，一次全搬）

- **暂缓说明（2026-10-24）**：选型 Textual 与一次全搬定案不变。原型雏形已在分支
  `archive/t2-textual-market` 落地（已完成无参入口全量切入 Textual 市场 App 的验证）。
  因当前阶段工作重心转向自研 Shell 桌面端核心交互演进（T3 设置界面替换），决定暂缓
  该分支主线合并与后续分期，将精力集中于桌面端。分支归档备用，后续择机重启。
- **定案（2026-10-24）**：选型 Textual，迁移范围一次全搬——市场三屏
  （工坊 / 预设 / doctor）与全部过渡交互屏（组件清单 / deps / 快照回滚 /
  卸载 / clean）进同一个 App；tui.py 手搓组件层（~1500 行）全数退役。
  开工首日先做 spike：kitty 下跑 pacman 的终端交接、中文对齐、退出后
  终端干净、测试可用性，有硬伤才回退 urwid。
- **终态分层**：`nyxuri/ux.py` 零依赖基座（确认提示 / 步骤报告 / 宽度
  工具）+ `nyxuri/market/` 唯一声明依赖层（全库唯一 `import textual`）。
  CLI 四动词与非交互路径零依赖不变，装不装 textual 都完整可用。
- **投影而非状态**：界面只读账本，开关照走 `transaction` 同一条事务
  路径；pacman 等交互式子进程暂时交出终端、跑完收回；直达动词
  （clean / uninstall / deps）复用同一 App。
- **依赖策略**：否决 vendor（拖 6 个传递包，塞进仓库就是无主文件）；
  python-textual 入 PKGBUILD `optdepends` + install.sh 引导装齐；缺席时
  交互入口提示 `pacman -S python-textual`，不留旧界面兜底。
- **契约修订**：AGENTS 不变量 3 收窄为「引擎核心零依赖，TUI 层为唯一
  声明依赖」，vision §3、tui-charter、overview、operation-map、
  testing 一并同步。
- **分期**：M0 spike → M1 骨架+契约 → M2 工坊+首页（无参入口切 App）→
  M3 预设+doctor → M4 过渡屏全迁 → M5 删旧收口。每期过全量单测、
  沙箱部署与 kitty 实机冒烟。

### T3 设置界面替换（Caelestia 安卓风味）

- **形态重构与双轨定案**：以 Caelestia Shell（https://github.com/caelestia-dots/shell）的
  Nexus 设置界面形态，替换现 Default + Minimal 两个旧面板样式并成为默认；Dashboard（卡片网格）
  保留为双轨之二——`settingsPanelStyle` 轴三值（default, minimal, dashboard）收敛为两值
  （default, dashboard）。历史配置中的 `minimal` 自动平滑折叠为 `default`，消灭 0.75 缩放瑕疵。
- **策略与单一事实**：先抽象原子控件全套拷入重构为纯 QML 标准库，拒绝散装拼凑（No picking）；
  settings 模型、路由、搜索、动作与持久化（SettingsBackend / settings-routes.json）完全不动。
- **详细台账**：偏好原子套件解构、NavPane 双行安卓卡片规范与 M0–M4 分期台账唯一见
  [shell/ROADMAP.md](shell/ROADMAP.md#t3-设置界面替换caelestia-安卓风味当前进行中)。

### T4 Shell 可控性与透明化

- 开工时立细则。方向：单元运行态可观测（进程 / 资源 / 副作用）、doctor 对账
  接入 Shell、日志与诊断直通——每样能力答得出「它为什么在这」。

### T5 多合成器解耦（门禁触发）

- 第三个合成器（Hyprland/Sway）接入前必须执行：`CompositorDriver` 驱动抽象
  收编过渡形态——`SUPPORTED_WMS` 硬编码元组、组件菜单 WM 特判、doctor 三处
  合成器字面量（债务登记见 [delayed-decisions](llms-wiki/delayed-decisions.md)）。
- 热重载、浮动便签与屏幕探测跨合成器适配，`doctor` 诊断与 `greeter` 会话自适应。

### M1 单元生命周期与状态恢复

统一安装、更新、预设与单元事务；强制前备份、停用保护修改、失败待重试及生成文件归属。
契约见 [单元模型](llms-wiki/unit-model.md)、[预设机制](llms-wiki/preset-mechanism.md)
与 [状态操作](llms-wiki/state-ops.md)。

### U1 Ubuntu 26.04 兼容

- **已落地**：APT/dpkg 后端、平台依赖声明、Shell 运行时预检、默认 XDG 布局门禁，
  以及 Fcitx 旧布局与 Portal 多会话规则迁移。
- **已验收**：Ubuntu 26.04 GNOME/Niri 会话、个人配置首次部署、升级、恢复与卸载重装；
  物理多屏及其他 GPU 不由单屏虚拟机结果代表。
- **交付边界**：Niri 多输出截图及可选运行时仍有限制；普通安装不切换显示管理器或编译源码。
- **实现与限制**：见 [Ubuntu 兼容指南](llms-wiki/ubuntu-compatibility.md)；平台字段见
  [manifest-schema](llms-wiki/manifest-schema.md#平台依赖覆盖)。

### U2 Ubuntu Greeter 适配

- 使用现有 APT 源提供的 `greetd` 与 `noctalia-greeter`，适配包内会话入口、运行用户、
  生效配置和外观同步权限；启用前保存原显示管理器，停用后恢复，保留包自带的配置与数据。
- **已验收（2026-10-28）**：Ubuntu 26.04 虚拟机完成公开命令安装/启停、Greeter 登录
  Niri、外观同步、配置错误拒绝切换及重启恢复 GDM；本机完成 Greeter 登录 Niri 与外观
  同步写入。修正无关单元开关触发主题迁移的问题，保留已有内置主题并检查替代模板输入。

### U3 Ubuntu 视频壁纸播放器供给

- 用户选择视频壁纸后，明确提示安装构建依赖；固定已验证的 `mpvpaper` release/tag，
  在临时目录以普通用户执行上游 Meson/Ninja 构建流程。
- 将构建结果制成本地 `.deb`，由 APT 安装并管理版本与卸载；仅依赖安装与最终安装使用
  sudo，不额外维护 APT 源。成功后清理源码和构建目录；失败保留诊断日志并清理临时目录。
- 不顺带执行 `autoremove`，保留运行依赖；播放器、视频素材分别管理，静态壁纸不依赖
  此流程。完成后同步 Ubuntu 当前手动供给契约，并验证播放、主题取色与静态壁纸切换。

## Shell 侧

阶段台账、P4 验收与 P6 整体验收门禁唯一见 [shell/ROADMAP.md](shell/ROADMAP.md)，
此处不复述。未收口项（壁纸域取色内生、matugen 退役）随 Shell 阶段推进。

## 全局门禁（每阶段验收都过）

1. 五原则验收给可复现证据（真诚透明 / 绝对主权 / 骨架包容 / 轻盈生长 /
   通用自然，见 [vision](llms-wiki/vision.md)）。
2. 单一开关真相与单元边界不变量的唯一权威在
   [unit-model](llms-wiki/unit-model.md) 与 [AGENTS.md](AGENTS.md)，
   此处只链接不复述。
3. 架构 / 命令 / manifest 变更同步对应 wiki 页与台账（路由见 AGENTS.md）。

## 储备（不承诺）

- 第三方源信任分级与签名。
- 安全 Downdate 体系：现场快照优先还原 + Git 逆向检出的安全版本回退。

# Nyxuri 演进路线与待办

> 暂放根目录，供接下来几个月推进时逐项勾选；这轮底座工作告一段落后再归档。
> 这是愿景与待办草案，不是当前架构说明。早期排查中的行号、规模和问题判断可能已变化，动手前按当前代码复核。
> 2026-09-12：阶段零已完成并通过验证，详见 [阶段零清单](llms-wiki/phase-zero.md)。其余未勾选项尚未按整项验收。

> **核心原则**：
> 1. **白纸洁癖**：系统是一张新纸。Nyxuri 带来的每一处改动都要有记录、能撤回、不留孤儿文件。
> 2. **流畅但不越俎代庖**：安装过程少打断，真正需要取舍时把决定权还给用户。
> 3. **结构要规整**：职责分清、路径对齐，别让例外和依赖越堆越多。
> 4. **做减法与反失控感**：能不产生的依赖绝不产生，能不增加的体积绝不增加；拒绝无谓的技术自嗨与依赖地狱。

---

## 第一部分：我重装机后的全景痛点与真实困惑

### 1. 白纸洁癖：别在系统里留下擦不掉的东西
- **真实感受**：
  新系统对我来说就像一张纯白无瑕的特种画纸。我跑这个脚本时，心里最深层的不安全感是：**它会不会在我的画纸上留下擦不掉的污渍？如果我反悔了、或者哪一步走错了，我能不能 100% 毫无悬念地一键撤回？**
  我极度受不了卸载残留、幽灵状态文件和不可逆的暗改。任何工具进入我的系统，必须做到**干干净净地来，清清白白地退**，绝不拉排泄物，绝不留暗坑。

### 2. 菜单流转割裂、“隐身机制”切碎心流，但我绝不要傻瓜向导
- **真实感受**：
  新系统运行脚本后，直接掉进一个包含 10 个选项的大面板，子菜单逻辑非常割裂。
  最严重的是**“未安装即隐身”机制**：如果我想装 Fcitx5 输入法，在「应用配置」列表里根本看不到它（因为检测到宿主机还没装该软件，条目直接隐身消失了！）；我必须退出并退回主菜单，进入「软件与依赖」->「常用软件」勾选安装；装完后再退回主菜单，重新进入「应用配置」勾选皮肤。
  用户在平行的子菜单之间被迫反复横跳，心流完全被切碎。虽然我不喜欢横跳，但**我依然想要清晰、可控、完整的全局掌控力**，绝对不想要被剥夺控制权、像 Windows 一样强制“下一步→下一步”的死板流水线向导。界面的视觉和排版我想要自己亲自操刀。

### 3. Fcitx5 + 雾凇拼音：能正常出字，但用的是自带默认方案
- **真实感受**：
  在常用软件里我安装了“Fcitx5 + 雾凇拼音”，之后输入法启动了，也可以正常敲键盘出字。但是**打出来的并不是雾凇拼音，而是它自带的默认方案**。
  雾凇词库并没有真正生效接管，缺少 profile 激活项、缺少在 Rime 目录挂载 `rime_ice` 补丁以及 schema 自动预编译闭环，留下了半截子工程。

### 4. NyxMellow 皮肤：好用，但我纠结于“自动设置 vs 用户知情权”
- **真实感受**：
  在应用配置里勾选了 NyxMellow 皮肤，之后去 Fcitx5 设置里确实能看到这个皮肤存在，手动选中该主题后完全能正常使用。
  我一直在思考：**要不要做成无需手动去 Fcitx5 里面设置？**
  如果脚本直接在后台替用户改了，我觉得太放肆了。**这样的修改必须可选：部署素材与“设为当前默认”分开，动手前把清单摆明白。**

### 5. 全项目包管理需要解耦、CachyOS Shelly 适配边界、以及 AUR 拦截
- **真实感受**：
  我觉得整个项目的包管理不好（依赖安装部分、Fish 里的 `se`/`in`/`up` 包搜索安装器等，全项目所有地方），散落在各处，**应该统一解耦出来**。
  在 CachyOS 上使用自带的现代包管理器 `shelly`，发现没有适配或者不完善。
  另外，开启 VPN 时访问 AUR 会被 Cloudflare 拦截，整个流程随之卡死；这里需要明确的超时和跳过路径。

### 6. 对标 iNiR 的未来野心 vs 当前对 Noctalia 的隐式寄生陷阱
- **真实感受**：
  虽然当前依赖 Noctalia 提供桌面外壳，但我**明确计划做一个自己的 Shell，总体构想是对标 [iNiR](https://github.com/snowarch/iNiR)**：完整的 M3 交互、服务 Niri，名称暂不预设。
  但反观全库现状，代码里暗中滋生了大量对 Noctalia 的“寄生硬编码”：
  - `binds.kdl` 和 `config.kdl` 写死了十几处 `noctalia msg ...` 快捷键与启动项；
  - Orbit 和壁纸选择器为了拿到 Material You 颜色，**硬编码偷读 `~/.cache/noctalia/starship-palette.toml`**，并且为了迎合 Starship 的 Catppuccin 别名，在代码里写了一堆别扭的二次反推推断（如把 `sapphire/mauve` 猜成 `primary/secondary`）。
  一旦哪天关掉 Noctalia，周边小工具直接崩塌。这种隐式寄生与二次反推逻辑严重阻碍了未来自研 Shell 的平滑演进。

---

## 第二部分：架构愿景——对齐、对称、各管一件事

> 这里的“对称”，**严格仅限于软件架构层面**。
> 剔除所有生硬拼接与不对称的特判代码，让模块、空间与时间在架构图纸上呈现严密的几何对齐。

### 1. 空间的对偶对称（源码蓝图 vs 宿主现实）
- **左象限（仓库源码）**：`configs/` 是只读的静态蓝图，零软链接、零宿主绝对路径硬编码。
- **右象限（用户系统）**：`~/.config/` 是真实运转的生活空间，受 `__custom__` 私域保护。
- **中轴对称镜面（`deploy.atomic`）**：严格进行真实物理替换与哈希比对。源码不侵犯宿主，宿主不反噬源码，两者严丝合缝平面对称。

### 2. 时间的反演对称（操作完全可逆，动作正负守恒）
整个引擎不存在任何单向塌陷的黑洞操作，每一个正向构建动词，都在架构上存在一个绝对等价的逆动词：
- `pkg.install` (包引入)  <═════ 完全反演守恒 ═════>  `pkg.remove` (包除净)
- `deploy.apply` (配置铺设) <═════ 完全反演守恒 ═════>  `state.rollback` (快照溯源)
- `setup` (接管系统)       <═════ 完全反演守恒 ═════>  `purge` (纯白清退)

### 3. 模块的四象限笛卡尔对称（各司其职，消除缝合怪）
整个 Python 核心引擎划分为结构对齐的四大承重子包，东西对仗、南北守衡：

```
                           【 空间构建 (Space) 】
                                     ▲
                                     │
            nyxuri.pkg               │              nyxuri.deploy
       ( 外部供给：吸纳包与依赖 )       │         ( 内部雕刻：原子替换与渲染 )
                                     │
    【 外部世界 (External) 】 ───────┼───────> 【 内部系统 (Internal) 】
                                     │
            nyxuri.doctor            │              nyxuri.state
       ( 外部诊断：体检与排障 )         │         ( 内部回溯：快照与无痕清退 )
                                     │
                                     ▼
                           【 时间守护 (Time) 】
```
- **中央贯穿**：底层是零第三方依赖的 `nyxuri.core`，顶层是负责展示的 `nyxuri.tui`（我自己的留白与审美门面）。

### 4. 数据声明的几何规整（消灭引擎特判）
- 90% 纯配置应用保持为纯静态的 `.toml` 声明，丢进目录即生效，零代码开发。
- 10% 复杂组件（如 Fcitx5 编译 schema）通过标准生命周期 Hook 接入。
- **架构红线**：引擎中彻底消灭 `if app == "fcitx5-rime"` 这种打破架构对称性的硬编码特例，所有应用在引擎眼里都是平权且对称的数据单元。

---

## 第三部分：全库失控点排查

为了捍卫“纯白画布”与“架构对称”，全库曾存在以下 9 处破坏几何秩序的历史病灶：

1. **双脑分裂 (Shell vs Python)**：`config.fish` 与 `nyxniri/deps.py` 各自独立实现包管理，破坏一致性。[已治理 · 阶段二]
2. **数据伪装成代码 (i18n 膨胀)**：`nyxniri/i18n.py` 膨胀至 1794 行大字典，沉重负累。[已治理 · 阶段二]
3. **厨房水槽大管家 (cli.py 堆叠)**：`cli.py` 逼近 1000 行，路由、UI、流程、提权混杂。[已治理 · 阶段二]
4. **错位工具存放 (物理隔离击穿)**：独立清理工具 `clean-cache.py` 寄生在 `configs/fish/` 里。[已治理 · 阶段二]
5. **模块职责越界 (modules/fcitx.py)**：越权动配置文件、改快捷键、重启进程。[已治理 · 阶段二与阶段三]
6. **伪声明式特判泄漏**：底层写死 `if app == "fcitx5-rime"` 特判。[已治理 · 阶段三]
7. **时序耦合的全局状态**：`deps.py` 遍布全局可变变量引发隐式依赖。[已治理 · 阶段二]
8. **调色板隐式寄生与别扭反推**：硬编码偷读 starship 色板并蹩脚反推 Catppuccin。[已治理 · 阶段三]
9. **Niri 桌面服务硬编码绑定**：快捷键与启动直绑 `noctalia msg`。[已治理 · 阶段三]

---

### 最近一次全库审计：6 个深层问题

为了让自研 Shell、双 Shell、多合成器、版本迁移和 TUI 继续往前走，全库审计列出以下 6 个问题。原则不变：**一切皆可选，按需组装。**

1. **项目改名、大小写分裂与卸载孤儿 (Naming & Case Split)**：
   - 路径硬编码：配置根目录 `~/.config/NyxNiri`、状态 `~/.local/state/NyxNiri`、卸载归档、日志等处处绑定 `PROJECT_NAME`；
   - 大小写分裂历史包袱：Python 底座用大写 `~/.cache/NyxNiri`（`core.py:98`），而 Noctalia 模板（`noctalia-config.toml:254`）与壁纸脚本（`scanner.py:25`）硬编码小写 `~/.cache/nyxniri`，在 Linux 大小写敏感文件系统上造成目录分裂；
   - 卸载残留孤儿：`uninstall.py:201` 卸载时仅清除了大写的 `~/.cache/NyxNiri`，而小写目录内数十兆缩略图缓存与色板永久腐烂在磁盘上；
   - 软链防误删校验 `core.py:is_nyxniri_cli_symlink()` 字符串硬匹配，改名后合法的软链反被判定为外来文件无法接管或卸载；
   - 内部代码 `importlib.import_module("nyxniri.modules.*")` 写死顶层绝对包名。
2. **双 Shell 运行时插槽、主题总线寄生与假声明式 (Multi-Shell Slots & Sneaky Side Effects)**：
   - 主题总线寄生：系统级主题同步脚本 `theme-sync.sh`（232 行）本应调度 GTK/Qt/Kitty/GSettings，却被锁在 `configs/noctalia/theme-sync.sh`，底座代码（`cli.py:224`, `deploy.py:173`, `doctor.py:75`）通过 `THEME_ENGINE` 硬编码寻址；应收归为 `nyxuri theme`；
   - 部署引擎偷塞命令式私货：`deploy.py:131-139` 偷摸为 niri 创建 `effects.kdl` 软链；`deploy.py:183` 在文件部署中途突然通过 IPC 唤起外部守护进程执行 `noctalia msg plugins enable mpvpaper` 并触发 `templates-apply`；
   - 外围脚本仍有 14 处直接调用 `noctalia msg`（`session-shell.sh` 直接 `exec noctalia` 并杀 scope；`shell-action.sh` 6 个核心动作直连 noctalia；`niri-brightness.sh` 和 `toggle-eyecare.sh` 私自读写 `~/.config/noctalia`）；
   - 合成器启动存在脆弱补丁：`niri/config.kdl` 硬编码 `sleep 8; noctalia msg config-reload && templates-apply` 盲等补丁，换其他 Shell 会产生报错残留与竞态冲突；
   - 外部模板单向劫持：`gtktheme.py` 与 `fcitx.py` 直接操作读写 `noctalia-config.toml` 注入模板块，停用 Noctalia 会导致 GTK 与 Fcitx 失去配色来源。
3. **公共桌面工具物理囚禁与合成器死绑 (Compositor Agnostic Gap)**：
   - 近 3700 行重型 Python GUI 工具（`orbit/` 1728 行、`wallpaper_picker/` 1856 行）被物理囚禁在 `configs/niri/scripts/` 下；`orbit-items__custom__.toml` 被粗暴扔在 Niri 配置根目录下；它们本质是 Noctalia 的外挂伴生套件，应移入 `configs/noctalia/tools/`，在未来自研 Shell 下实现**零部署、纯白无残留**；
   - 历史旧包装残留：`configs/niri/scripts/start-noctalia.sh` 仅 8 行且单纯转调 `session-shell.sh`，属于未清理的幽灵别名；
   - 底座强制依赖：`constants.py:MAIN_WM = "niri"` 且被塞入必装 `CORE_DEPS`；`install.sh:132-136` 预检强制断言 `configs/niri/config.kdl` 与 `noctalia-config.toml` 必须存在；`doctor.py` 诊断、`greeter.py` 会话探测、`deploy.py` 护眼软链初始化与下一步提示固定绑定 `niri`；
   - 预设热重载硬编码：`preset.py:573-585` 内部用 `if app == "niri"` 和 `elif app == "kitty"` 特判热重载指令。
4. **升级系统缺乏代码执行能力、孤儿清理与状态账本 (Zero Migration Framework)**：
   - 废弃项永久腐烂：更新只做现有项覆盖，一旦重命名目录或废弃旧模块，旧目录永久滞留在用户 `~/.config/` 中成为无人清理的死数据；需要轻量级静态墓碑清单（Tombstone List）与顺序纯 Python 迁移钩子顺手清理；
   - 状态多头分裂散落：预设存放在 `~/.config/NyxNiri/presets/<app>.active`，卸载回退与开关标记散落在 `~/.local/state/NyxNiri/`（`*.prev`、`*.enabled`），护眼开关靠反推软链目标；亟需单一事实源 `state.json`；
   - 发布通道与游离头指针陷阱：`update --to <tag>` 导致本地 Git 进入 Detached HEAD 状态，下次执行 `nyxuri update` 时 `git pull --ff-only` 直接崩溃；
   - 升级安全带缺失：非交互模式更新写死 `workflows.py:191: do_backup=False`；拉取更新前未暂存 Git HEAD SHA，拉取或安装失败时无原子回滚，停留在半破坏状态（Half-deployed State）；运行时原地覆盖自身 Python 源码存在 AST/Bytecode 错乱与锁丢失竞争风险；
   - 黑盒体验：升级完毕后缺乏 What's New / Release Notes 提示与重大破坏性变更警告。
5. **底座遗留边角防御与信号处理隐患 (Base Architecture Deficiencies)**：
   - 🔴 高危存留：`atomic.py:221` 遇 Ctrl+C 时 `old_dest` 仍未进清理栈，且 `tui.py` 的 `sys.exit(130)` 绕过了 `except Exception:` 回滚逻辑；
   - 🔴 高危存留：`uninstall.py:183` 壁纸卸载依然直接 `shutil.rmtree` 整个用户 Wallpapers 目录，误删私人壁纸；
   - 🔴 高危存留：`theme-sync.sh:221` 在切换动态光晕时直接全盘覆写包含核心布局规则的 `layout.kdl`，违反核心布局不可动原则；
   - 🔴 卸载盲区：`fcitx.py:354-410` 安装雾凇拼音注入的 Rime 补丁在 `fcitx_uninstall` 中缺乏逆向清除逻辑，留下一堆半截子脏数据；
   - 锁机制与单一数据源缺陷：`nyxuri pkg` 与 `clean` 绕过排他锁；状态文件分散在 `.local/state` 与 `.config/NyxNiri`。
6. **TUI 终端秩序与质感痛点 (TUI Ergonomics & Polish Gap)**：
   - 未启用备用屏幕缓冲区 (Alternate Screen Buffer `\033[?1049h/l`)：终端 Scrollback 历史被反复抹除和污染；主菜单运行完 `doctor` 或快照查看后，按任意键结果被 `clear_screen()` 瞬间销毁，用户无法回头查阅细节；
   - 焦点移动全屏重绘：每按一次方向键就完整重新打印 15 行 ASCII Logo，未启用 DEC 2025（`\033[?2025h/l`）原子帧同步，在高刷终端有肉眼可见的频闪与撕裂感；
   - 缺乏即时模糊搜索：数十款常用应用与预设列表无法打字过滤；
   - 长时间操作原始日志失控滚屏：`pacman/paru/git` 原始输出冲毁终端，缺乏单行就地收拢的 Spinner 与耗时汇总；
   - 交互模式断层：`clean.py` 在终端可用行较小时退化为 `input("> ")` 字符串输入，快照备注行式输入打断 TUI。

---

## 第四部分：吸收协作者 (@Accel-White) 精髓的工程现实法则

Issue #102 把一些漂亮但站不住脚的设想拉回了现实。愿景最终要落到几条能执行的工程规则上：

### 法则 1：破除“绝对可逆”魔法，确立“四级受管对象回滚机制”
- **工程现实**：任何编程语言（哪怕是 Rust 的内存所有权和 RAII）都无法保证断电下的磁盘原子性，也无法凭空证明外部包安装命令绝对可逆。
- **现实落地**：把“绝对可逆”从虚幻的“撤销一切系统副作用”，收敛为**“对受管对象与文件的明确追踪与分级回滚”**：
  1. **安装失败恢复**：按依赖组恢复失败部分，保留独立且已验证成功的模块，明确报告部分完成；
  2. **产品版本回退**：回退产品与默认配置，完整保留用户个人覆盖（`__custom__`）；
  3. **配置快照恢复**：用户明确选择时点时，恢复该时点配置，遇到冲突保留双方供选择；
  4. **受管卸载 vs 彻底清除**：正常卸载恢复受管改动、清理安全文件，保留用户数据；彻底清除另作显式二次确认。

### 法则 2：确立“底座先行、契约冻结”的交付纪律
- **工程纪律**：**严禁边改底座边改具体业务组件！**
- **执行顺序**：必须先搭齐 `pkg / deploy / doctor / state` 四包底层与统一公共接口（Schema、错误模型、锁与事务日志），用测试样本充分验收通过并冻结契约后，才允许逐一迁移 Fcitx5、主题、Fish 等业务组件。

### 法则 3：底座语言战略定调——坚守 Python 纯标库，拒绝虚妄繁荣
- **为什么不随波逐流重写 Rust？**
  1. **瓶颈不在语言**：管理底座 99% 的等待时间在网络（`git`/`curl`）和外部包管理器 I/O（`pacman`/`paru`），换 Rust 根本不会变快；
  2. **拒绝依赖地狱**：当前 Python 纯标库**零 pip 依赖、`arch=('any')` 免编译分发、改完秒测**；换 Rust 会引入 Cargo 依赖树，也会让 AUR 用户承担编译成本；
  3. **测试资产保护**：仓库现有近 7,000 行纯标库测试，推倒重写的代价极其高昂。
- **结论**：管理底座锁死在 Python 纯标准库。

### 法则 4：动手前列清单，执行时少打断
- 将“安装软件”、“接管配置”、“启用功能”、“设为默认”在概念与数据层彻底解耦；
- 在真正执行写磁盘与安装前，集中向用户展示**“即将变更的操作清单与文件影响”**，并提前 `sudo -v` 索取权限；
- 一旦用户确认，执行流程安静流淌、就地状态收拢（In-place update），绝不中途频繁弹出 `Y/n` 阻断心流。

---

## 第五部分：多 Shell 与多合成器蓝图

> **方向**：
> 1. **双 Shell 并立共存，不清退 Noctalia**：确立 **Noctalia + 自研 Shell** 双一等公民架构。`wallpaper_picker.py` 维持作为 Noctalia 的亲密搭档永久保留并协同运作；自研 Shell 则原生内置 Material You 灵动交互、桌面背景与 M3 取色引擎。
> 2. **一切皆可选 (Everything is Optional)**：Shell 和合成器都按需组合，不强制捆绑。
> 3. **多合成器 (Multi-WM)**：构建通用桌面组件层与 Compositor 适配层，先服务 Niri，再按需扩展 Hyprland、Sway 等。

---

### 1. 双 Shell 平等插槽与四大 Provider 契约

为了实现 Noctalia 与自研 Material You Shell 的平等共存与秒级切换，构建标准化的 **`ShellProvider` 协议**：

```
                            [ Compositor 会话 ]
                                     │
           ┌─────────────────────────┴────────────────────────┐
           ▼                                                  ▼
[ configs/desktop/session-shell.sh ]         [ configs/desktop/shell-action.sh ]
           │                                                  │
           │ 读取活动 Shell 标记                                │ 读取活动 Shell 标记
           │  (~/.local/state/nyxuri/state.json)               │  (~/.local/state/nyxuri/state.json)
           ▼                                                  ▼
┌──────────────────────────────────────┐          ┌──────────────────────────────────────┐
│       SessionProvider (生命周期)      │          │        ActionProvider (动作网关)      │
│  - noctalia: 拉起 noctalia 守护进程    │          │  - launcher / session / settings     │
│  - custom: 启动自研 Shell 二进制       │          │  - clipboard / lock / wallpaper      │
└──────────────────────────────────────┘          └──────────────────────────────────────┘
                                     │
                                     ▼
                ┌──────────────────────────────────────────┐
                │        PaletteProvider (调色基准)        │
                │  - Noctalia: 模板输出至 palette.toml     │
                │  - 自研 Shell: 原生算法直出 palette.toml  │
                └──────────────────────────────────────────┘
                                     │
                                     ▼
                       ~/.cache/nyxuri/palette.toml
                   (Single Source of Truth 色板单点基准)
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
[ Orbit Launcher ]           [ Wallpaper Picker ]         [ Theme Dispatcher ]
(直接读取语义 Token)           (Noctalia 忠实搭档)           (nyxuri theme 调度)
```

#### 四大 Provider 契约规范：
1. **SessionProvider (`session-shell.sh`)**：
   - 依据 `active_shell` 标记分发启动命令；
   - 移除 `config.kdl` 中的 `sleep 8; noctalia msg ...` 盲等补丁，冷启动由各自 Shell 自己处理。
2. **ActionProvider (`shell-action.sh`)**：
   - 标准动词：`launcher` | `session` | `settings` | `clipboard` | `lock` | `wallpaper-random`；
   - 若当前为 Noctalia：分发至 `noctalia msg`（未安装星环启动器时回退 `fuzzel`）；
   - 若当前为自研 Shell：分发至自研 Shell 的 IPC/CLI，外围快捷键零改动。
3. **PaletteProvider 与 Theme Dispatcher (调色板与主题中枢)**：
   - 固化 `~/.cache/nyxuri/palette.toml` 为唯一事实源；
   - Noctalia 走原生 TOML 模板渲染；自研 Shell 凭借 M3 算法直出同构文件；下游 Orbit、Kitty、GTK 无感消费；
   - **主题调度归入 Python 底座**：由 `nyxuri theme <toggle|sync|dark|light>` 统一处理 GTK3/4 与 Qt INI，Noctalia 只需在 hook 中调用 `["nyxuri", "theme", "sync"]`。
4. **TemplateAdapter (模板适配解耦与 Noctalia Template 兼容)**：
   - **兼容 Noctalia Template 系统**：自研 Shell 支持 Noctalia 的 Jinja 风格模板规范与变量命名空间（`{{ colors.primary.default.hex }}`、`{{ colors.surface.default.hex }}` 等）；
   - 现有 GTK CSS、Fcitx SVG、Kitty、Starship 和用户自定义模板无需重写，可直接共享；
   - 拔除 `gtktheme.py` 与 `fcitx.py` 直接改写 `noctalia-config.toml` 的越权代码，由模板适配层面向通用的 template 规范进行统一注册与渲染。

---

### 2. 多合成器 (Multi-WM) 架构解耦体系

#### (1) 桌面伴生工具归位与合成器脚本纯洁化 (Scoped Tools & Clean Compositor)
- **核心原则**：自研 Shell 追求极致的纯白与简洁，原生内置启动器、壁纸管理与 M3 引擎，**绝不强加任何外部 Python GUI 脚本**。
- **精准归位**：
  - **Noctalia 专属伴生工具集 (`configs/noctalia/tools/`)**：将重型 Python GUI 工具 `orbit/`（1728 行）、`wallpaper_picker/`（1856 行）以及 `orbit-items__custom__.toml` 菜单配置文件全数收归至 Noctalia 伴生目录。仅在用户选择启用 Noctalia 时才会释放至 `~/.config/noctalia/tools/`；使用自研 Shell 时**零释放、零代码残留、绝对纯白**！
  - **`configs/niri/scripts/` 极简化胶水层**：移走上述两个大型 GUI 目录并彻底物理删除废弃的 `start-noctalia.sh` 包装后，合成器脚本目录彻底瘦身，仅保留 5 个精简纯粹的 Bash 胶水脚本（`session-shell.sh`, `shell-action.sh`, `niri-brightness.sh`, `toggle-eyecare.sh`, `niri-scratch-toggle.sh`），专注服务于合成器会话与快捷键分发。

#### (2) 核心依赖解耦与声明式化
- 将 `niri` 从 `nyxuri/constants.py:CORE_DEPS` 强依赖中解绑；
- 将合成器下放为普通可选组件：在 `configs/niri/.module.toml`、`configs/hypr/.module.toml` 中按需声明各自的包名与预设；
- 预设热重载指令下放至各模块的 manifest（消除 `preset.py` 中的 `if app == "niri"` 硬编码）。

#### (3) CompositorDriver 驱动抽象层
- 在 Python 底座中抽象 `CompositorDriver` 接口，抹平各合成器底层差异：
  - **热重载 (Reload)**：`niri msg action load-config-file` vs `hyprctl reload` vs `swaymsg reload`；
  - **浮动便签 (Scratchpad)**：统一调度 Kitty 浮动窗口；
  - **屏幕输出探测 (Focused Output)**：内屏与外接屏亮度分流；
- **智能诊断与会话引导**：`doctor.py` 根据当前 `$XDG_CURRENT_DESKTOP` 自适应诊断，不再对非 niri 会话虚假报红；`greeter.py` 动态扫描并提供会话选项。

---

## 第六部分：迁移与升级体系

> 不引入额外包管理器或数据库，用 Python 标准库完成线性、可追踪的迁移。

### 1. 痛点破除：解决“升级时需要执行额外代码”的核心诉求
- **现状缺陷**：当前更新仅为简单的 `git pull` + 原子覆盖。一旦版本迭代需要重命名目录、修改配置键值、转换快照结构或清理废弃旧配置，系统完全无能为力。
- **极简解决方案**：
  1. **单一事实源版本账本 (`state.json`)**：
     在 `~/.local/state/nyxuri/state.json` 中记录运行时与模块状态，替代散落在 `state_dir` 的零碎标记（如 `fcitx-*.prev`、`*.enabled`）：
     ```json
     {
       "installed_version": "3.1.0",
       "migration_level": 4,
       "channel": "stable",
       "active_shell": "noctalia",
       "active_wm": "niri",
       "active_presets": { "niri": "default", "kitty": "transparent" },
       "modules": { "fcitx": { "enabled": true, "prev_theme": "classic" } }
     }
     ```
  2. **线性 Migration 与静态墓碑清单 (`nyxuri/migrations/`)**：
     - **静态墓碑清单 (Tombstone List)**：维护极简废弃路径表（如历史废弃脚本、已重构目录），升级时自动探测并安全清理孤儿文件，防止死数据在用户磁盘腐烂；
     - **纯标库微型迁移函数**：每个迁移脚本仅需几十行简洁代码：
     ```python
     # nyxuri/migrations/0004_v3_1_noctalia_tools_reorganize.py
     def up(env: Environment) -> bool:
         """将旧 niri/scripts 下的伴生套件平移至 noctalia/tools 并清理旧幽灵别名。"""
         ...
         return True
     ```
     执行 `nyxuri update` 时，对比 `migration_level`，按顺序运行新版本需要的一次性迁移并更新账本。

### 2. 升级安全带与两阶段防错机制
- **强制升级前受保快照 (Guaranteed Snapshot)**：
  彻底废除 `workflows.py:191` 在非交互更新时跳过备份的漏洞（`do_backup=False`），任何更新启动前强制生成带 Git Commit SHA 的 `pre_update` 快照；
- **Git HEAD SHA 锚点记录与原子回滚**：
  在执行 `git pull` 前暂存当前 Commit SHA。若拉取后语法自检（`compileall`）失败或部署流程异常中断，提供一键原路复原到该 SHA 的自愈能力，绝不让用户停留在破坏性的半安装状态（Half-deployed State）；
- **修复 Detached HEAD 游离头指针陷阱**：
  规范化版本切换逻辑，切换 Tag 时自动建立本地受管状态，杜绝下一次 `git pull` 崩溃；
- **沙箱化预检与两阶段交接**：
  代码拉取与预检在临时隔离域完成，全部校验通过后再原子切换，部署过程发生中断或异常立即就地提示并保持现场。

### 3. 远期储备：安全 Downdate（版本回退/降级）体系
- **战略定位**：作为后续阶段的高级能力，优先级排在基础迁移引擎之后。
- **落地机制（快照优先 + 逆向检出）**：
  1. **现场快照优先还原**：用户指定降级至旧版本时，优先检索并恢复该版本升级前留存的原版受保快照（100% 保真还原）；
  2. **逆向 Git 检出兜底**：若本地无对应快照，稳妥检出目标 Tag，执行向下兼容检查并原子替换，保留用户 `__custom__`。

---

## 第七部分：TUI 视觉与终端秩序

> 当前 TUI 已经可用。下一步处理留白、重绘和日志，让它与自研 Material You Shell 的气质一致。

### 1. 终端纯净感：备用屏幕缓冲区 (Alternate Screen Buffer)
- 引入 ANSI `\033[?1049h` 与 `\033[?1049l`：
  - 进入 TUI 控制面板时自动切入备用屏幕；
  - 退出 TUI 时完整恢复进入前的终端历史，Scrollback 零污染、零残留；
  - 运行 `doctor` 或查看快照时，执行结果永久驻留在终端主屏上供对照查阅，绝不再被主菜单粗暴抹除。

### 2. 消除重绘闪烁：DEC 2025 帧同步与区域解耦
- 引入终端原子帧同步更新协议（`\033[?2025h/l`），减少高刷终端上的菜单撕裂；
- 将巨型 ASCII Banner 与动态菜单列表区域物理解耦，焦点移动时仅局部差分重绘，杜绝高频整屏闪烁。

### 3. 控制感与微动动效 (Zen Spinner)
- 废弃 `pacman/paru/git` 原始命令直通滚屏导致的屏幕失控；
- 引入纯标库极简单行微动 Spinner（显示当前步骤、最新摘要与已耗时间），任务成功就地收拢为规整徽章 `[✓]`，仅在异常时展开最后 10 行错误日志。

---

## 第八部分：项目重命名与双轨平滑迁移 (Project Rebranding & Dual-Track Migration)

> 随着项目从单一 Niri 合成器迈向多 WM、多 Shell 的全景桌面生态，项目名脱敏与重命名成为顺应演进的必然之举。

### 1. 常量集中与双轨兼容
- 集中统一品牌常量于 `nyxuri/constants.py`（如 `PROJECT_NAME`, `CLI_CMD`, `LEGACY_NAMES`）；
- 环境变量提供双向自动兼容：优先读取新前缀变量，无设置时自动平滑回退读取 `NYXNIRI_*`。

### 2. 存储路径迁移与大小写规范化
- **三级路径迁移**：启动时检测旧配置、状态和缓存目录，把内容迁移到小写的 `nyxuri` 目录，再清理旧路径；
- **大小写统一**：配置、状态和缓存都使用小写目录，结束 `NyxNiri` 与 `nyxniri` 并存的历史。

### 3. 动态 Import 与 CLI 软链自愈
- 将内部 `importlib.import_module("nyxniri.modules.*")` 升级为基于 `__package__` 的相对/动态导入；
- 升级软链防误删探测算法，自动接管并清理旧软链接，杜绝孤儿文件。

---

## 第九部分：排查发现的【边角防御与安全补丁】备忘 (Secondary & Defensive Edge Cases)

> **定位与原则**：属于底层极端边界防御，在推进底座与模块演进时顺手抹平。

### 1. [高危 · 状态安全] `atomic_replace_item` 遇 Ctrl+C 原子交换保护
- **代码位置**: `nyxuri/deploy/atomic.py:221-237`, `nyxuri/tui.py:59-62`
- **问题**: 在刚执行完 `dest.rename(old_dest)` 瞬间若用户敲击 Ctrl+C，`tui.py` 的 `sys.exit(130)` 绕过了 `except Exception:` 回滚栈，导致原配置变成孤儿。
- **修复**: 将 `old_dest` 统一登记入 swap 临时保护栈，捕获 `BaseException` 确保中断时安全回滚。

### 2. [高危 · 资产安全] 卸载壁纸时避免粗暴 `rmtree` 用户壁纸目录
- **代码位置**: `nyxuri/state/uninstall.py:182-184`
- **问题**: 卸载勾选 `wallpapers` 时，直接 `shutil.rmtree` 用户 Wallpapers 目录，误删私人壁纸。
- **修复**: 改为严格按照官方素材文件清单精准删除，严禁物理抹除用户壁纸总目录。

### 3. [高危 · 边界防护] Niri 动态光晕预设解耦
- **代码位置**: `configs/noctalia/noctalia-config.toml:248`, `configs/noctalia/theme-sync.sh:220`
- **问题**: Noctalia 切换光晕预设时直接覆写包含核心布局规则的 `layout.kdl`。
- **修复**: 将光晕抽取为独立的 `colors.kdl` include，严禁外围脚本覆写 `layout.kdl`。

### 4. [系统安全] 拔除 AUR 引导中的 `pacman -Rdd` 暴力拆包
- **代码位置**: `nyxuri/deps.py:166`
- **修复**: 移除 `-Rdd` 暴力参数，走常规依赖冲突提示。[已完成核心清理]

### 5. [真实反馈] 修复 `install_selected_deps` 恒真返回与外部超时
- **代码位置**: `nyxuri/deps.py:247-282`
- **修复**: 如实反映命令退出码，并为外部调用补充合理超时控制。

### 6. [架构解绑] 清除 `install.sh` / `doctor.py` 对特定组件名的断言
- **代码位置**: `install.sh:133`, `nyxuri/constants.py:10`, `nyxuri/doctor.py:43-80`
- **修复**: 解绑特定组件名检测，仅检测通用核心模块。

### 7. [依赖纯白 · 伴生包隔离] 解除 `CORE_DEPS` 对 Python GTK 绑定包的污染
- **代码位置**: `nyxuri/constants.py:72-73`, `configs/noctalia/.module.toml`
- **问题**: `python-gobject` 与 `gtk-layer-shell` 仅为 Noctalia 伴生套件（Orbit 与壁纸选择器）所需，却被错误塞入全局必装的 `CORE_DEPS`；管理底座、Niri 合成器与未来的纯原生自研 Shell 均完全不需要它们。
- **修复**: 从 `CORE_DEPS` 移除，下放至 `configs/noctalia/.module.toml:packages:repo` 伴生作用域；`doctor.py` 的 Orbit 检查改为条件触发（仅在伴生工具存在时体检），消灭全域虚警。

### 8. [合成器中立 · 快捷键网关化] 拔除 `binds.kdl` 对外壳伴生脚本的物理路径硬编码
- **代码位置**: `configs/niri/binds.kdl:52,64-65`, `configs/niri/scripts/shell-action.sh`
- **问题**: `Mod+W` 与 `Mod+A` 分别写死 `~/.config/noctalia/tools/wallpaper-picker.py` 与 `orbit-launcher.py`，破坏了合成器与桌面外壳的物理隔离。
- **修复**: 收归 `shell-action.sh` 动作网关（`wallpaper-picker` / `radial-launcher` 动作），合成器快捷键不再直接依赖桌面外壳。

### 9. [运行时恢复 · 双 Shell CLI] 落地 `nyxuri shell` 管理与故障提示
- **代码位置**: `nyxuri/cli.py`, `nyxuri/state/ledger.py`, `configs/niri/scripts/session-shell.sh`
- **问题**: 缺乏切换与查看 Shell 的便捷 CLI 指令；自定义 Shell 路径未落盘账本；若自定义 Shell 缺失或执行异常，会导致启动阶段黑屏卡死且无通知。
- **修复**: 新增 `nyxuri shell [get|set|status]`；在 `state.json` 中记录 `active_shell` 与 `custom_shell_bin`；启动异常时发送桌面通知并回退到 Noctalia。

### 10. [部署 · Python 主题中枢] 后置流程移除外部 Bash 转调
- **代码位置**: `nyxuri/deploy/deploy.py:164-169`, `nyxuri/theme.py`
- **问题**: `_phase_post_install_services` 通过 `timed_run(["bash", ...])` 跨目录唤起 `configs/noctalia/theme-sync.sh`，存在子进程开销与对特定外壳脚本的偶合。
- **修复**: 部署后置流程直接调用 `from nyxuri.theme import sync; sync()`，不再跨目录启动 Bash 脚本。

### 11. [规范对齐 · M3 调色板与轻量模板系统] 补齐色板核心角色与注册原语
- **代码位置**: `configs/noctalia/templates/palette.toml`, `nyxuri/template_registry.py`
- **说明**: 真正的 M3 取色留给后续专用工具；目前只在 `palette.toml` 补齐 `background` 与 `on_background`，并为 `template_registry.py` 增加 `has_section` 与 `add_section`。

### 12. [结构完备性 · 升级引导自愈] 检查项同步全库新增核心子模块
- **代码位置**: `install.sh:114-127`
- **修复**: 在 `engine_is_complete()` 完备性断言中，同步增补对 `ledger.py`、`theme.py`、`template_registry.py` 的校验，防止不完整安装。

### 13. [Dunder 规整 · 预设目录语义化] `presets/` 全库重命名为 `__presets__/`
- **代码位置**: `configs/niri/presets/` -> `configs/niri/__presets__/`, `configs/kitty/presets/` -> `configs/kitty/__presets__/`, `nyxuri/deploy/preset.py`
- **问题**: 现存的 `presets/` 目录容易与具体软件本身的合法子目录冲突，且与项目核心的 Dunder 保留协议（`__custom__`）割裂，缺少元数据特征。
- **修复**: 全面推行 `__presets__` Dunder 命名规范；部署原子替换引擎与预设切换引擎原生识别 `__presets__` 隔离层。

### 14. [全应用通用 · 乐高积木式零件体系] 从死板整包预设进化为声明式零件插槽
- **代码位置**: `configs/*/.module.toml`, `nyxuri/deploy/preset.py`
- **问题**: 当前预设机制是针对单应用的整盘替换（如 Niri 切换整个包含按键和布局的预设），无法做到“只换视觉光晕特效、完全保留用户按键习惯”，缺乏细粒度自由拔插能力；且 Niri 与 Kitty 的预设切换存在硬编码逻辑。
- **修复**: 在 `.module.toml` 引入通用的 `[parts.<slot>]` 声明原语（如 `[parts.effects]`、`[parts.binds]`、`[parts.theme]`），指定目标文件、`__presets__` 零件来源目录与默认值；预设引擎变为 100% 数据驱动，任何软件均可通过声明式 TOML 拥有热插拔零件。

### 15. [文档极简 · 归位 GitHub Wiki 与双轨 i18n] 仓库瘦身与多语言体系
- **代码位置**: `README.md`, `README.zh-CN.md`, GitHub Wiki, `nyxuri/translations.toml`
- **问题**: 根目录 README 高达 390 行，充斥着庞大的代码目录树、历史迁移警告和繁杂安装细节，破坏首屏极简美感；胶水脚本中存在语言硬编码。
- **修复**: 
  - 根目录 README 大瘦身（目标 150 行以内），打造纯粹的视觉门面与极简单行安装入口；
  - 长篇技术架构、设计哲学、模块手册与故障排查全量移交面向人类读者的 `humans-wiki/`（双轨中英 `Home.md` / `Home-zh.md`，与 `llms-wiki/` 形成对偶秩序并自动镜像至 GitHub Wiki）；
  - **文风铁律**：GitHub Wiki 遵循 `AGENTS.md` §8：清楚、具体、像人说话，保留 Nyxuri 自己的脾气；
  - `translations.toml` 作为终端和 CLI 唯一事实源，消除脚本中的硬编码双语字符串。

### 16. [终端优雅 · PowerShell 级复制粘贴] Kitty 交互贴合直觉
- **代码位置**: `configs/kitty/kitty.conf`
- **问题**: 缺少右键一键粘贴；`Ctrl+C` 绑定存在冲突风险；默认缺少无干扰剪贴板体验。
- **修复**: 引入经典 Windows Terminal / PowerShell 交互习惯：鼠标右键直接粘贴剪贴板、键盘 `Ctrl+C`（有选中文本复制，无选中文本中断）、`Ctrl+V` 原生粘贴；不启用划词自动污染剪贴板，保留干净的阅读选择体验。

### 17. [工程规整 · 仓库标准化与换行符锁定]
- **涉及文件**: `.gitattributes`
- **极简方案**:
  - `.gitattributes`：锁死 `*.sh`/`*.py`/`*.kdl`/`*.fish` 为 LF 换行符，防跨平台克隆带入 CRLF 搞坏脚本；排除资产目录语言统计，保持仓库语言纯净；
  - **验证收归本地**：遵循 AGENTS.md 减法与防熵增原则，不引入非 Arch 平台（Ubuntu CI）的云端杂音与维护负担，验证完全收归本地秒级契约（`python3 -m unittest`）。

---

## 第十部分：落地清单

### 阶段零：主配置纯白画布与过时硬件补丁拔除 (Zero Entropy Phase 0 - Immediate Cleanup)
- [x] **移除默认 NVIDIA 环境变量**：删除驱动变量及旧 Electron 设置；
- [x] **移除部署驱动改写**：删除硬件补丁阶段，保留路径适配；
- [x] **硬件层退回纯文本分类**：报告复用 PCI 输出，常规 doctor 不增加输出；
- [x] **同步契约测试与文档**：393 项测试与隔离部署验证通过。

### 阶段一：四包底座与契约冻结 (Groundwork Phase 1)
- [x] 固化 `nyxuri.pkg` 统一包管理接口；
- [x] 完善 `nyxuri.deploy` 声明式与原子替换规则，保留 `__custom__`；
- [x] 强化 `nyxuri.state` 四级回滚能力；
- [x] 编写契约测试样本，覆盖中断、失败、快照与配置漂移。

### 阶段二：全库大做减法与防熵增专项 (Groundwork Phase 2)
- [x] **消灭双脑分裂**：统一 Fish 与 Python 包管理逻辑；
- [x] **数据与代码解耦**：`i18n.py` 结构化瘦身至 TOML；
- [x] **收束单一职责**：拆解 `cli.py` 臃肿代码；
- [x] **纠正错位工具**：将 `clean-cache.py` 挪出，回归系统维护领域；
- [x] **约束模块越界**：重构 `modules/fcitx.py`，规范生命周期 Hook。

### 阶段三：业务痛点闭环与 Shell 解耦插槽 (Groundwork Phase 3)
- [x] **Fcitx5 + 雾凇闭环**：安装时自动挂载 `rime_ice` 补丁，预编译 schema，写入 profile；
- [x] **NyxMellow 知情权**：素材部署与激活解耦，展示 Pre-flight 清单；
- [x] **Niri 快捷键插槽化**：落地 `shell-action.sh` 与 `session-shell.sh`；
- [x] **调色板迁移**：新增 `palette.toml` 模板，Orbit 与壁纸选择器直读 M3 色板。

### 未来规划：自研 Shell 三个阶段

#### 1. 开发 Shell 前的准备工作 (Pre-Shell Groundwork)
> **核心目标**：动工自研 Shell 前，处理路径硬编码、大小写分裂、伴生工具错位、隐式副作用和脆弱补丁。

- [x] **项目全局重命名与双轨平滑迁移 (Project Rebranding)**：在自研 Shell 动工前彻底完成品牌定名脱敏（Nyxuri），常量集中统一（`constants.py`），环境变量双向兼容（优先新前缀，回退 `NYXNIRI_*`），`~/.config/NyxNiri` 与 `~/.local/state/NyxNiri` 自动安全平移并彻底清理历史残留，`nyxuri` 模块平滑迁移；
- [x] **消灭 Linux 大小写分裂与孤儿清理**：全库规范为统一小写路径（如 `~/.cache/<project>`），彻底终结历史大小写分裂包袱，卸载时完整清理历史缩略图与色板孤儿；
- [x] **伴生套件归位与合成器配置纯洁化**：将近 3700 行的 `orbit/`、`wallpaper_picker/` 及 `orbit-items__custom__.toml` 整体收归进 `configs/noctalia/tools/`，物理删除废弃的 `start-noctalia.sh` 包装；`configs/niri/scripts/` 彻底瘦身为仅含 5 个纯粹胶水脚本；确立自研 Shell 下**零外部 Python GUI 释放、绝对纯白**；
- [x] **打通双 Shell 运行时插槽基座 (ShellProvider Slots)**：重构 `session-shell.sh` 与 `shell-action.sh`，基于 `state.json` 的 `active_shell` 动态路由（Noctalia vs 自研 Shell），彻底告别写死 `exec noctalia`；彻底移除 `config.kdl` 中脆弱的 `sleep 8; noctalia msg ...` 盲等补丁；
- [x] **调色基准单点事实源 (PaletteProvider)**：固化 `~/.cache/<project>/palette.toml` 为唯一事实源，Noctalia 走原生 TOML 模板渲染直出，下游 Orbit、Kitty、GTK 等无感消费，为后续自研 Shell 原生直出色板铺平标准契约；
- [x] **主题调度归入 Python 底座**：由 `nyxuri theme <toggle|sync|dark|light>` 原子改写 GTK3/4 与 Qt INI，不再依赖 Noctalia 目录中的脚本；
- [x] **解除模板单向劫持与核心布局保护**：将 Niri 动态光晕抽离为独立的 `colors.kdl`，严禁覆写核心布局 `layout.kdl`；解耦 `gtktheme` 与 `fcitx` 对 `noctalia-config.toml` 的正则篡改，使模板资产面向自研 Shell 直接共享；
- [x] **版本账本与线性迁移 (`state.json`)**：用 `~/.local/state/<project>/state.json` 收拢预设、状态与模块标记；通过 `nyxuri/migrations/` 和 `TOMBSTONES` 处理配置迁移与废弃路径；
- [x] **纯化部署引擎与解绑核心依赖偏见**：解绑 `MAIN_WM` 与 `noctalia` 核心依赖强绑定，消除 `install.sh:132-136` 预检中对其配置文件的强制断言；消除 `preset.py` 中的 `if app == "niri"` 热重载特判；剔除 `deploy.py:131-139` 硬编码为 niri 创建 `effects.kdl` 软链的特判，拔除部署途中私自触发守护进程 IPC（`noctalia msg plugins enable mpvpaper`、`templates-apply`）的隐式副作用；
- [x] **升级安全带机制与高危边角防护抹平**：
  - 修复 `workflows.py:191` 非交互更新跳过备份漏洞，升级前强制生成受保快照并记录 Git HEAD SHA 锚点，失败可原子回滚；
  - 修复 Detached HEAD 游离头指针陷阱；
  - 补强 `atomic.py` 的 swap 保护栈，捕获中断确保 Ctrl+C 时原配置不丢失；
  - `uninstall.py` 壁纸卸载改为白名单精准删除官方素材，严禁暴力 `rmtree` 用户壁纸目录；
  - 补充 `fcitx.py` 雾凇拼音 Rime 补丁的对等卸载撤销逻辑；
  - 拔除 AUR 引导中的暴力 `-Rdd`，修复 `install_selected_deps` 如实反映退出码并添加合理超时；
- [x] **隔离伴生包依赖**：从 `nyxuri/constants.py:CORE_DEPS` 移除 `python-gobject` 与 `gtk-layer-shell`，下放至 `configs/noctalia/.module.toml`；补上 Shelly 引导和网络超时；
- [x] **适配 Shelly**：`nyxuri.pkg`、Fish 搜索和依赖安装支持 `standard` / `aur` 分流、`--no-confirm`、JSON 搜索结果与提权；
- [x] **合成器快捷键完全中立与网关调度**：`binds.kdl` 中直连 `noctalia/tools/*.py` 的路径全部拔除，收归 `shell-action.sh` 统一调度网关（`wallpaper-picker` / `radial-launcher`），实现 Compositor 与桌面外壳物理隔离；
- [x] **双 Shell CLI（`nyxuri shell`）**：`state.json` 记录当前 Shell；启动失败时通知用户并回退到 Noctalia；`doctor.py` 按当前 Shell 检查；
- [x] **部署后主题同步**：`_phase_post_install_services` 直接调用 `nyxuri.theme.sync()`，移除 Bash 转调；
- [x] **M3 调色板与模板注册**：`palette.toml` 补齐 `background` 与 `on_background`；`nyxuri/template_registry.py` 增加 `has_section` 与 `add_section`；
- [x] **升级引导结构完备性自愈**：`install.sh:engine_is_complete()` 对齐新增的 `ledger`、`theme`、`template_registry` 模块检查；
- [x] **`__presets__` Dunder 命名规整与全软件通用零件化插槽体系**：将 `presets/` 重命名为 `__presets__/`，在 `.module.toml` 中支持通用 `[parts.<slot>]` 规则声明，使所有软件均可通过纯声明式 TOML 像替换零件一样切换视觉、按键与规则；
- [x] **终端 Windows PowerShell 级优雅交互体验**：Kitty 配置右键直接粘贴剪贴板、键盘 `Ctrl+C` 智能识别复制/中断、`Ctrl+V` 原生粘贴（无自动划词进剪贴板干扰）；Fish 常用终端函数与窗口快捷键冻结原样保持；
- [x] **GitHub 仓库工程标准化**：增补 `.gitattributes` 锁死 LF 换行符杜绝跨平台脚本损坏与 Wiki 自动化同步流，保持验证收归本地。

#### 2. 开发 Shell 时 (During Shell Development)
> **核心目标**：专注自研 Material You Shell 本体，以及它与现有契约的连接。
- [ ] **原生内置启动器、壁纸管理与 M3 调色引擎**：原生承载应用启动检索与壁纸管理；算法直出同构 `palette.toml`，在自研 Shell 模式下无需安装任何外部 Python GUI 伴生脚本；
- [ ] **兼容 Noctalia Template 系统 (TemplateAdapter)**：支持其 Jinja 风格模板规范与变量命名空间，让现有 GTK CSS、Fcitx SVG、Kitty、Starship 和用户模板无需重写；
- [ ] **Shell 生命周期与动作响应网关对接**：打通与 `session-shell.sh` 的守护拉起及 `shell-action.sh` 的 6 大标准动作（`launcher` / `session` / `settings` / `clipboard` / `lock` / `wallpaper-random`）IPC/CLI 接口，外围快捷键零改动即刻响应。

#### 3. 开发 Shell 后 (Post-Shell Ecosystem & Polish)
> **核心目标**：在自研 Shell 雏形落地后，完善双轨切换心流、终端美学跃迁、多合成器生态解耦与版本安全降级。

- [ ] **双 Shell 切换 (`nyxuri shell set`)**：支持 `nyxuri shell set <noctalia|custom>` 或快捷键切换 Noctalia 与自研 Shell；
- [ ] **Noctalia + Wallpaper Picker 协同方案稳固验收**：验证 Noctalia 模式下伴生套件的按需部署与运行，确保双轨方案互不干扰、各自纯白；
- [ ] **TUI 视觉风格化与纯净感 (Terminal Rice)**：接入 Alternate Screen Buffer（`\033[?1049h/l`）保护终端历史（运行 `doctor` / 查看快照不被抹除），DEC 2025 协议消除高刷频闪撕裂，引入单行微动 Zen Spinner 就地收拢命令滚屏日志；
- [ ] **多合成器 (Multi-WM) 架构解耦与驱动抽象**：构建 `CompositorDriver` 驱动抽象层，实现热重载、浮动便签与屏幕探测的跨合成器适配（Hyprland/Sway 等按需扩展），`doctor` 诊断与 `greeter` 会话自适应；
- [ ] **安全 Downdate 体系（高级储备）**：落地基于现场快照优先还原与 Git 逆向检出的安全版本回退机制。

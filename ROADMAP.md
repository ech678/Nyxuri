# NyxNiri 演进路线与待办

> 暂放根目录，供接下来几个月推进时逐项勾选；这轮底座工作告一段落后再归档。
> 这是愿景与待办草案，不是当前架构说明。早期排查中的行号、规模和问题判断可能已变化，动手前按当前代码复核。
> 2026-09-12：阶段零已完成并通过验证，详见 [阶段零清单](llms-wiki/phase-zero.md)。其余未勾选项尚未按整项验收。

> **核心哲学与终极追求**：
> 1. **纯白画布上的洁癖**：**“零残留与受管可逆”**。系统是一张崭新无暇的特种画纸，任何动作必须进退自如、绝不散落一粒尘埃。
> 2. **苹果般的顺畅节奏**：毫无顿挫的开箱心流，高掌控感与静谧感拉满，坚决拒绝剥夺控制权的死板流水线向导。
> 3. **架构上的完全对称几何之美**：对齐规整、职责守恒，杜绝屎山与熵增，让所有事物井井有条。
> 4. **做减法与反失控感**：能不产生的依赖绝不产生，能不增加的体积绝不增加；拒绝无谓的技术自嗨与依赖地狱。

---

## 第一部分：我重装机后的全景痛点与真实困惑

### 1. 纯白画布上的洁癖：“零残留与绝对可逆”的戒备感 (核心心结)
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
  如果脚本直接在后台替用户改了，我觉得太放肆了、没有告知用户。我的原则非常坚定：**这样的修改必须是可选的！素材释放与“设为当前默认”必须彻底解耦。改动前必须列出清晰清单，在所有地方保证极高的透明度和用户的知情度。**

### 5. 全项目包管理需要解耦、CachyOS Shelly 适配边界、以及 AUR 拦截
- **真实感受**：
  我觉得整个项目的包管理不好（依赖安装部分、Fish 里的 `se`/`in`/`up` 包搜索安装器等，全项目所有地方），散落在各处，**应该统一解耦出来**。
  在 CachyOS 上使用自带的现代包管理器 `shelly`，发现没有适配或者不完善。
  另外，开启 VPN 时访问 AUR 会直接被 Cloudflare 拦截，导致整个流程卡死，缺乏有界超时与优雅跳过机制。

### 6. 对标 iNiR 的未来野心 vs 当前对 Noctalia 的隐式寄生陷阱
- **真实感受**：
  虽然当前依赖 Noctalia 提供桌面外壳，但我**明确计划在半年后做一个自己的 Shell，总体构想是对标 [iNiR](https://github.com/snowarch/iNiR)**（体验顶级、全套 M3 交互的 Niri 桌面外壳，但坚决不基于 Quickshell，暂不预设名称与框架）。
  但反观全库现状，代码里暗中滋生了大量对 Noctalia 的“寄生硬编码”：
  - `binds.kdl` 和 `config.kdl` 写死了十几处 `noctalia msg ...` 快捷键与启动项；
  - Orbit 和壁纸选择器为了拿到 Material You 颜色，**硬编码偷读 `~/.cache/noctalia/starship-palette.toml`**，并且为了迎合 Starship 的 Catppuccin 别名，在代码里写了一堆别扭的二次反推推断（如把 `sapphire/mauve` 猜成 `primary/secondary`）。
  一旦哪天关掉 Noctalia，周边小工具直接崩塌。这种隐式寄生与二次反推逻辑严重阻碍了未来自研 Shell 的平滑演进。

---

## 第二部分：架构愿景——完全对称的几何之美 (Symmetrical Architecture)

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
           nyxniri.pkg               │             nyxniri.deploy
       ( 外部供给：吸纳包与依赖 )       │         ( 内部雕刻：原子替换与渲染 )
                                     │
    【 外部世界 (External) 】 ───────┼───────> 【 内部系统 (Internal) 】
                                     │
           nyxniri.doctor            │             nyxniri.state
       ( 外部诊断：体检与排障 )         │         ( 内部回溯：快照与无痕清退 )
                                     │
                                     ▼
                           【 时间守护 (Time) 】
```
- **中央贯穿**：底层为纯粹零依赖的基础设施 `nyxniri.core`，顶层为纯粹的展示层 `nyxniri.tui`（我自己的留白与审美门面）。

### 4. 数据声明的几何规整（消灭引擎特判）
- 90% 纯配置应用保持为纯静态的 `.toml` 声明，丢进目录即生效，零代码开发。
- 10% 复杂组件（如 Fcitx5 编译 schema）通过标准生命周期 Hook 接入。
- **架构红线**：引擎中彻底消灭 `if app == "fcitx5-rime"` 这种打破架构对称性的硬编码特例，所有应用在引擎眼里都是平权且对称的数据单元。

---

## 第三部分：顶级架构师眼中的全库“熵增”排查地图

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

### 全库最新穿透审计：新时代 6 大深层技术痛点与问题汇总

随着项目向**自研 Shell、双 Shell 平等共存、多合成器 (Multi-WM) 扩展、高鲁棒更新迁移与 TUI 风格化**纵深迈进，全库穿透审计定位出以下 6 大深层技术病灶（**坚持“一切皆可选、按需自由组装”原则**）：

1. **项目改名、大小写分裂与卸载孤儿 (Naming & Case Split)**：
   - 路径硬编码：配置根目录 `~/.config/NyxNiri`、状态 `~/.local/state/NyxNiri`、卸载归档、日志等处处绑定 `PROJECT_NAME`；
   - 大小写分裂历史包袱：Python 底座用大写 `~/.cache/NyxNiri`（`core.py:98`），而 Noctalia 模板（`noctalia-config.toml:254`）与壁纸脚本（`scanner.py:25`）硬编码小写 `~/.cache/nyxniri`，在 Linux 大小写敏感文件系统上造成目录分裂；
   - 卸载残留孤儿：`uninstall.py:201` 卸载时仅清除了大写的 `~/.cache/NyxNiri`，而小写目录内数十兆缩略图缓存与色板永久腐烂在磁盘上；
   - 软链防误删校验 `core.py:is_nyxniri_cli_symlink()` 字符串硬匹配，改名后合法的软链反被判定为外来文件无法接管或卸载；
   - 内部代码 `importlib.import_module("nyxniri.modules.*")` 写死顶层绝对包名。
2. **双 Shell 运行时插槽、主题总线寄生与假声明式 (Multi-Shell Slots & Sneaky Side Effects)**：
   - 主题总线寄生：系统级全局主题同步脚本 `theme-sync.sh`（232 行）本应调度全系统 GTK/Qt/Kitty/GSettings，却被物理锁在 `configs/noctalia/theme-sync.sh`，底座代码（`cli.py:224`, `deploy.py:173`, `doctor.py:75`）通过 `THEME_ENGINE` 硬编码寻址；亟需彻底 Python 化收归为底座原生 `nyxniri theme` 指令；
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
   - 发布通道与游离头指针陷阱：`update --to <tag>` 导致本地 Git 进入 Detached HEAD 状态，下次执行 `nyxniri update` 时 `git pull --ff-only` 直接崩溃；
   - 升级安全带缺失：非交互模式更新写死 `workflows.py:191: do_backup=False`；拉取更新前未暂存 Git HEAD SHA，拉取或安装失败时无原子回滚，停留在半破坏状态（Half-deployed State）；运行时原地覆盖自身 Python 源码存在 AST/Bytecode 错乱与锁丢失竞争风险；
   - 黑盒体验：升级完毕后缺乏 What's New / Release Notes 提示与重大破坏性变更警告。
5. **底座遗留边角防御与信号处理隐患 (Base Architecture Deficiencies)**：
   - 🔴 高危存留：`atomic.py:221` 遇 Ctrl+C 时 `old_dest` 仍未进清理栈，且 `tui.py` 的 `sys.exit(130)` 绕过了 `except Exception:` 回滚逻辑；
   - 🔴 高危存留：`uninstall.py:183` 壁纸卸载依然直接 `shutil.rmtree` 整个用户 Wallpapers 目录，误删私人壁纸；
   - 🔴 高危存留：`theme-sync.sh:221` 在切换动态光晕时直接全盘覆写包含核心布局规则的 `layout.kdl`，违反核心布局不可动原则；
   - 🔴 卸载盲区：`fcitx.py:354-410` 安装雾凇拼音注入的 Rime 补丁在 `fcitx_uninstall` 中缺乏逆向清除逻辑，留下一堆半截子脏数据；
   - 锁机制与单一数据源缺陷：`nyxniri pkg` 与 `clean` 绕过排他锁；状态文件分散在 `.local/state` 与 `.config/NyxNiri`。
6. **TUI 终端秩序与质感痛点 (TUI Ergonomics & Polish Gap)**：
   - 未启用备用屏幕缓冲区 (Alternate Screen Buffer `\033[?1049h/l`)：终端 Scrollback 历史被反复抹除和污染；主菜单运行完 `doctor` 或快照查看后，按任意键结果被 `clear_screen()` 瞬间销毁，用户无法回头查阅细节；
   - 焦点移动全屏重绘：每按一次方向键就完整重新打印 15 行 ASCII Logo，未启用 DEC 2025（`\033[?2025h/l`）原子帧同步，在高刷终端有肉眼可见的频闪与撕裂感；
   - 缺乏即时模糊搜索：数十款常用应用与预设列表无法打字过滤；
   - 长时间操作原始日志失控滚屏：`pacman/paru/git` 原始输出冲毁终端，缺乏单行就地收拢的 Spinner 与耗时汇总；
   - 交互模式断层：`clean.py` 在终端可用行较小时退化为 `input("> ")` 字符串输入，快照备注行式输入打断 TUI。

---

## 第四部分：吸收协作者 (@Accel-White) 精髓的工程现实法则

Issue #102 下的深度探讨为本项目的工程落地注入了极其宝贵的现实清醒剂。哲学愿景必须由硬核工程规则承托：

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
  2. **拒绝依赖地狱**：当前 Python 纯标库**零 pip 依赖、`arch=('any')` 免编译源码分发、改完秒测**，这是极简与秩序的巅峰；换 Rust 会立刻引入上百个 Cargo crate 依赖树，AUR 变成沉重的二进制编译，这是赤裸裸的熵增；
  3. **测试资产保护**：仓库现有近 7,000 行纯标库测试，推倒重写的代价极其高昂。
- **结论**：管理底座锁死在 Python 纯标准库。

### 法则 4：部署前预检清单 (Pre-flight Checklist) 与执行期非交互心流
- 将“安装软件”、“接管配置”、“启用功能”、“设为默认”在概念与数据层彻底解耦；
- 在真正执行写磁盘与安装前，集中向用户展示**“即将变更的操作清单与文件影响”**，并提前 `sudo -v` 索取权限；
- 一旦用户确认，执行流程安静流淌、就地状态收拢（In-place update），绝不中途频繁弹出 `Y/n` 阻断心流。

---

## 第五部分：多 Shell 平等共存与多合成器 (Multi-WM) 泛化解耦蓝图

> **战略定调**：
> 1. **双 Shell 并立共存，不清退 Noctalia**：确立 **Noctalia + 自研 Shell** 双一等公民架构。`wallpaper_picker.py` 维持作为 Noctalia 的亲密搭档永久保留并协同运作；自研 Shell 则原生内置 Material You 灵动交互、桌面背景与 M3 取色引擎。
> 2. **一切皆可选 (Everything is Optional)**：无论 Shell 还是合成器，全系统杜绝强加捆绑，用户可按需自由组合、平滑插拔。
> 3. **多合成器 (Multi-WM) 支持正式立项**：打破单一绑定，构建通用的桌面组件层与 Compositor 适配层，让系统同时兼备 Niri 极致滚轴与新合成器（Hyprland/Sway 等）的高自由度。

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
           │ (~/.local/state/NyxNiri/active_shell)            │ (~/.local/state/NyxNiri/active_shell)
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
                      ~/.cache/nyxniri/palette.toml
                   (Single Source of Truth 色板单点基准)
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
[ Orbit Launcher ]           [ Wallpaper Picker ]         [ Theme Dispatcher ]
(直接读取语义 Token)           (Noctalia 忠实搭档)          (nyxniri theme 原生调度)
```

#### 四大 Provider 契约规范：
1. **SessionProvider (`session-shell.sh`)**：
   - 依据 `active_shell` 标记分发启动命令；
   - 彻底移除 `config.kdl` 中脆弱的 `sleep 8; noctalia msg ...` 盲等补丁，冷启动由各自 Shell 自主保底。
2. **ActionProvider (`shell-action.sh`)**：
   - 标准动词：`launcher` | `session` | `settings` | `clipboard` | `lock` | `wallpaper-random`；
   - 若当前为 Noctalia：分发至 `noctalia msg`（未安装星环启动器时回退 `fuzzel`）；
   - 若当前为自研 Shell：分发至自研 Shell 的 IPC/CLI，外围快捷键零改动。
3. **PaletteProvider 与 Theme Dispatcher (调色板与主题中枢)**：
   - 固化 `~/.cache/nyxniri/palette.toml` 为唯一事实源；
   - Noctalia 走原生 TOML 模板渲染；自研 Shell 凭借 M3 算法直出同构文件；下游 Orbit、Kitty、GTK 无感消费；
   - **主题调度彻底 Python 原生化**：彻底告别寄生在 Noctalia 目录下的脆弱 Bash 脚本 `theme-sync.sh`，由底座纯标库直接承载 `nyxniri theme <toggle|sync|dark|light>` 指令。利用 Python 的 `configparser` 安全原子改写 GTK3/4 与 Qt INI，免除复杂的 Shell 正则拼接；Noctalia 配置仅需 hook 调用 `["nyxniri", "theme", "sync"]`，快捷键亦直接绑定该命令。
4. **TemplateAdapter (模板适配解耦与 Noctalia Template 兼容)**：
   - **全面兼容 Noctalia Template 系统**：自研 Shell 原生兼容并支持 Noctalia 的 Jinja 风格模板规范与变量命名空间（`{{ colors.primary.default.hex }}`、`{{ colors.surface.default.hex }}` 等）；
   - **零摩擦无缝复用**：现存的 GTK CSS、Fcitx SVG、Kitty、Starship 以及用户自定义的 `[theme.templates.user.*]` 模板资产在自研 Shell 下**无需重写、直接共享**；
   - 拔除 `gtktheme.py` 与 `fcitx.py` 直接改写 `noctalia-config.toml` 的越权代码，由模板适配层面向通用的 template 规范进行统一注册与渲染。

---

### 2. 多合成器 (Multi-WM) 架构解耦体系

#### (1) 桌面伴生工具归位与合成器脚本纯洁化 (Scoped Tools & Clean Compositor)
- **核心原则**：自研 Shell 追求极致的纯白与简洁，原生内置启动器、壁纸管理与 M3 引擎，**绝不强加任何外部 Python GUI 脚本**。
- **精准归位**：
  - **Noctalia 专属伴生工具集 (`configs/noctalia/tools/`)**：将重型 Python GUI 工具 `orbit/`（1728 行）、`wallpaper_picker/`（1856 行）以及 `orbit-items__custom__.toml` 菜单配置文件全数收归至 Noctalia 伴生目录。仅在用户选择启用 Noctalia 时才会释放至 `~/.config/noctalia/tools/`；使用自研 Shell 时**零释放、零代码残留、绝对纯白**！
  - **`configs/niri/scripts/` 极简化胶水层**：移走上述两个大型 GUI 目录并彻底物理删除废弃的 `start-noctalia.sh` 包装后，合成器脚本目录彻底瘦身，仅保留 5 个精简纯粹的 Bash 胶水脚本（`session-shell.sh`, `shell-action.sh`, `niri-brightness.sh`, `toggle-eyecare.sh`, `niri-scratch-toggle.sh`），专注服务于合成器会话与快捷键分发。

#### (2) 核心依赖解耦与声明式化
- 将 `niri` 从 `nyxniri/constants.py:CORE_DEPS` 强依赖中解绑；
- 将合成器下放为普通可选组件：在 `configs/niri/.module.toml`、`configs/hypr/.module.toml` 中按需声明各自的包名与预设；
- 预设热重载指令下放至各模块的 manifest（消除 `preset.py` 中的 `if app == "niri"` 硬编码）。

#### (3) CompositorDriver 驱动抽象层
- 在 Python 底座中抽象 `CompositorDriver` 接口，抹平各合成器底层差异：
  - **热重载 (Reload)**：`niri msg action load-config-file` vs `hyprctl reload` vs `swaymsg reload`；
  - **浮动便签 (Scratchpad)**：统一调度 Kitty 浮动窗口；
  - **屏幕输出探测 (Focused Output)**：内屏与外接屏亮度分流；
- **智能诊断与会话引导**：`doctor.py` 根据当前 `$XDG_CURRENT_DESKTOP` 自适应诊断，不再对非 niri 会话虚假报红；`greeter.py` 动态扫描并提供会话选项。

---

## 第六部分：极简高鲁棒代码迁移与升级体系 (Lean Migration Engine & Safe Downdate)

> **设计哲学**：拒绝笨重的第三方包管理与复杂数据库依赖，依托 Python 纯标准库实现**轻量、线性、绝对受控**的升级迁移体系。

### 1. 痛点破除：解决“升级时需要执行额外代码”的核心诉求
- **现状缺陷**：当前更新仅为简单的 `git pull` + 原子覆盖。一旦版本迭代需要重命名目录、修改配置键值、转换快照结构或清理废弃旧配置，系统完全无能为力。
- **极简解决方案**：
  1. **单一事实源版本账本 (`state.json`)**：
     在 `~/.local/state/nyxniri/state.json` 中持久化记录全部运行时与模块状态，彻底废除散落在 `state_dir` 的零碎标记（如 `fcitx-*.prev`、`*.enabled`）：
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
  2. **轻量线性 Migration 与静态墓碑清单 (`nyxniri/migrations/`)**：
     - **静态墓碑清单 (Tombstone List)**：维护极简废弃路径表（如历史废弃脚本、已重构目录），升级时自动探测并安全清理孤儿文件，防止死数据在用户磁盘腐烂；
     - **纯标库微型迁移函数**：每个迁移脚本仅需几十行简洁代码：
     ```python
     # nyxniri/migrations/0004_v3_1_noctalia_tools_reorganize.py
     def up(env: Environment) -> bool:
         """将旧 niri/scripts 下的伴生套件平移至 noctalia/tools 并清理旧幽灵别名。"""
         ...
         return True
     ```
     执行 `nyxniri update` 时，自动对比 `migration_level`，按顺序链式触发新版本所需的全部一次性代码，并落盘账本。

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

## 第七部分：TUI 视觉风格化与终端美学跃迁 (TUI Stylization & Aesthetic Polish)

> **设计哲学**：当前 TUI 逻辑完全可用，未来的重心是**视觉质感、艺术留白与纯粹秩序**，打造与自研 Material You Shell 气质协调一致的 Terminal Rice。

### 1. 终端纯净感：备用屏幕缓冲区 (Alternate Screen Buffer)
- 引入 ANSI `\033[?1049h` 与 `\033[?1049l`：
  - 进入 TUI 控制面板时自动切入备用屏幕；
  - 退出 TUI 时完整恢复进入前的终端历史，Scrollback 零污染、零残留；
  - 运行 `doctor` 或查看快照时，执行结果永久驻留在终端主屏上供对照查阅，绝不再被主菜单粗暴抹除。

### 2. 消除重绘闪烁：DEC 2025 帧同步与区域解耦
- 引入终端原子帧同步更新协议（`\033[?2025h/l`），彻底消除高刷终端上的菜单撕裂；
- 将巨型 ASCII Banner 与动态菜单列表区域物理解耦，焦点移动时仅局部差分重绘，杜绝高频整屏闪烁。

### 3. 控制感与微动动效 (Zen Spinner)
- 废弃 `pacman/paru/git` 原始命令直通滚屏导致的屏幕失控；
- 引入纯标库极简单行微动 Spinner（显示当前步骤、最新摘要与已耗时间），任务成功就地收拢为规整徽章 `[✓]`，仅在异常时展开最后 10 行错误日志。

---

## 第八部分：项目重命名与双轨平滑迁移 (Project Rebranding & Dual-Track Migration)

> 随着项目从单一 Niri 合成器迈向多 WM、多 Shell 的全景桌面生态，项目名脱敏与重命名成为顺应演进的必然之举。

### 1. 常量集中与双轨兼容
- 集中统一品牌常量于 `nyxniri/constants.py`（如 `PROJECT_NAME`, `CLI_CMD`, `LEGACY_NAMES`）；
- 环境变量提供双向自动兼容：优先读取新前缀变量，无设置时自动平滑回退读取 `NYXNIRI_*`。

### 2. 存储路径自动平移与大小写规范化
- **三级路径透明平移**：启动时检测旧路径 `~/.config/NyxNiri`，自动安全平移至新目录，并保留兼容软链接 `~/.config/NyxNiri -> ~/.config/<NewName>`；
- **大小写彻底统一**：借重命名契机统一规范化为规范小写目录，消灭 `NyxNiri` 与 `nyxniri` 在 Linux 缓存目录下的历史分裂。

### 3. 动态 Import 与 CLI 软链自愈
- 将内部 `importlib.import_module("nyxniri.modules.*")` 升级为基于 `__package__` 的相对/动态导入；
- 升级软链防误删探测算法，自动接管并清理旧软链接，杜绝孤儿文件。

---

## 第九部分：排查发现的【边角防御与安全补丁】备忘 (Secondary & Defensive Edge Cases)

> **定位与原则**：属于底层极端边界防御，在推进底座与模块演进时顺手抹平。

### 1. [高危 · 状态安全] `atomic_replace_item` 遇 Ctrl+C 原子交换保护
- **代码位置**: `nyxniri/deploy/atomic.py:221-237`, `nyxniri/tui.py:59-62`
- **问题**: 在刚执行完 `dest.rename(old_dest)` 瞬间若用户敲击 Ctrl+C，`tui.py` 的 `sys.exit(130)` 绕过了 `except Exception:` 回滚栈，导致原配置变成孤儿。
- **修复**: 将 `old_dest` 统一登记入 swap 临时保护栈，捕获 `BaseException` 确保中断时安全回滚。

### 2. [高危 · 资产安全] 卸载壁纸时避免粗暴 `rmtree` 用户壁纸目录
- **代码位置**: `nyxniri/state/uninstall.py:182-184`
- **问题**: 卸载勾选 `wallpapers` 时，直接 `shutil.rmtree` 用户 Wallpapers 目录，误删私人壁纸。
- **修复**: 改为严格按照官方素材文件清单精准删除，严禁物理抹除用户壁纸总目录。

### 3. [高危 · 边界防护] Niri 动态光晕预设解耦
- **代码位置**: `configs/noctalia/noctalia-config.toml:248`, `configs/noctalia/theme-sync.sh:220`
- **问题**: Noctalia 切换光晕预设时直接覆写包含核心布局规则的 `layout.kdl`。
- **修复**: 将光晕抽取为独立的 `colors.kdl` include，严禁外围脚本覆写 `layout.kdl`。

### 4. [系统安全] 拔除 AUR 引导中的 `pacman -Rdd` 暴力拆包
- **代码位置**: `nyxniri/deps.py:166`
- **修复**: 移除 `-Rdd` 暴力参数，走常规依赖冲突提示。[已完成核心清理]

### 5. [真实反馈] 修复 `install_selected_deps` 恒真返回与外部超时
- **代码位置**: `nyxniri/deps.py:247-282`
- **修复**: 如实反映命令退出码，并为外部调用补充合理超时控制。

### 6. [架构解绑] 清除 `install.sh` / `doctor.py` 对特定组件名的断言
- **代码位置**: `install.sh:133`, `nyxniri/constants.py:10`, `nyxniri/doctor.py:43-80`
- **修复**: 解绑特定组件名检测，仅检测通用核心模块。

---

## 第十部分：全景改造终极落地清单 (Master Action Checklist)

### 阶段零：主配置纯白画布与过时硬件补丁拔除 (Zero Entropy Phase 0 - Immediate Cleanup)
- [x] **移除默认 NVIDIA 环境变量**：删除驱动变量及旧 Electron 设置；
- [x] **移除部署驱动改写**：删除硬件补丁阶段，保留路径适配；
- [x] **硬件层退回纯文本分类**：报告复用 PCI 输出，常规 doctor 不增加输出；
- [x] **同步契约测试与文档**：393 项测试与隔离部署验证通过。

### 阶段一：四包底座与契约冻结 (Groundwork Phase 1)
- [x] 固化 `nyxniri.pkg` 统一包管理接口；
- [x] 完善 `nyxniri.deploy` 声明式与原子替换规则，确保 `__custom__` 绝对安全；
- [x] 强化 `nyxniri.state` 四级回滚能力；
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
- [x] **调色板舒缓迁移落地**：新增原生 `nyxniri-palette.toml` 模板，Orbit 与壁纸选择器直读 M3 色板。

### 未来规划：自研 Shell 三步冲刺战役

#### 1. 开发 Shell 前的准备工作 (Pre-Shell Groundwork)
> **核心目标**：在动工自研 Shell 之前，将全库现存的路径硬编码、大小写分裂、伴生工具倒挂、假声明式副作用与脆弱补丁彻底拔除，把底座打造成一尘不染的纯白画布。

- [ ] **项目全局重命名与双轨平滑迁移 (Project Rebranding)**：在自研 Shell 动工前彻底完成品牌定名脱敏，常量集中统一（`constants.py`），环境变量双向兼容（优先新前缀，回退 `NYXNIRI_*`），`~/.config/NyxNiri` 与 `~/.local/state/NyxNiri` 自动安全平移并留兼容软链，`importlib` 动态导入升级；
- [ ] **消灭 Linux 大小写分裂与孤儿清理**：全库规范为统一小写路径（如 `~/.cache/<project>`），彻底终结历史大小写分裂包袱，卸载时完整清理历史缩略图与色板孤儿；
- [ ] **伴生套件归位与合成器配置纯洁化**：将近 3700 行的 `orbit/`、`wallpaper_picker/` 及 `orbit-items__custom__.toml` 整体收归进 `configs/noctalia/tools/`，物理删除废弃的 `start-noctalia.sh` 包装；`configs/niri/scripts/` 彻底瘦身为仅含 5 个纯粹胶水脚本；确立自研 Shell 下**零外部 Python GUI 释放、绝对纯白**；
- [ ] **打通双 Shell 运行时插槽基座 (ShellProvider Slots)**：重构 `session-shell.sh` 与 `shell-action.sh`，基于 `state.json` 的 `active_shell` 动态路由（Noctalia vs 自研 Shell），彻底告别写死 `exec noctalia`；彻底移除 `config.kdl` 中脆弱的 `sleep 8; noctalia msg ...` 盲等补丁；
- [ ] **调色基准单点事实源 (PaletteProvider)**：固化 `~/.cache/<project>/palette.toml` 为唯一事实源，Noctalia 走原生 TOML 模板渲染直出，下游 Orbit、Kitty、GTK 等无感消费，为后续自研 Shell 原生直出色板铺平标准契约；
- [ ] **主题调度彻底 Python 原生化**：将 `theme-sync.sh` 彻底重构为底座原生 `nyxniri theme <toggle|sync|dark|light>` 指令，利用 Python 标准库 `configparser` 安全原子改写 GTK3/4 与 Qt INI，拔除对 Noctalia 目录脚本的寻径耦合；
- [ ] **解除模板单向劫持与核心布局保护**：将 Niri 动态光晕抽离为独立的 `colors.kdl`，严禁覆写核心布局 `layout.kdl`；解耦 `gtktheme` 与 `fcitx` 对 `noctalia-config.toml` 的正则篡改，使模板资产面向自研 Shell 直接共享；
- [ ] **单一事实源版本账本与线性迁移框架 (`state.json`)**：引入 `~/.local/state/<project>/state.json` 单一事实源，收拢预设、状态与模块标记（消灭散落的 `.prev`、`.enabled` 碎片）；引入轻量迁移钩子（`nyxniri/migrations/`）与静态墓碑清单（`TOMBSTONES`），支持升级时顺手清理废弃目录与配置迁移；
- [ ] **纯化部署引擎与解绑核心依赖偏见**：解绑 `MAIN_WM` 与 `noctalia` 核心依赖强绑定，消除 `install.sh:132-136` 预检中对其配置文件的强制断言；消除 `preset.py` 中的 `if app == "niri"` 热重载特判；剔除 `deploy.py:131-139` 硬编码为 niri 创建 `effects.kdl` 软链的特判，拔除部署途中私自触发守护进程 IPC（`noctalia msg plugins enable mpvpaper`、`templates-apply`）的隐式副作用；
- [ ] **升级安全带机制与高危边角防护抹平**：
  - 修复 `workflows.py:191` 非交互更新跳过备份漏洞，升级前强制生成受保快照并记录 Git HEAD SHA 锚点，失败可原子回滚；
  - 修复 Detached HEAD 游离头指针陷阱；
  - 补强 `atomic.py` 的 swap 保护栈，捕获中断确保 Ctrl+C 时原配置不丢失；
  - `uninstall.py` 壁纸卸载改为白名单精准删除官方素材，严禁暴力 `rmtree` 用户壁纸目录；
  - 补充 `fcitx.py` 雾凇拼音 Rime 补丁的对等卸载撤销逻辑；
  - 拔除 AUR 引导中的暴力 `-Rdd`，修复 `install_selected_deps` 如实反映退出码并添加合理超时。

#### 2. 开发 Shell 时 (During Shell Development)
> **核心目标**：专注于自研 Material You Shell 本体的高质感构建与契约接驳，做到零外部侵入、原生直连。

- [ ] **自研 Material You Shell 核心架构研发**：纯粹单一风格、极致几何秩序，原生直连 Niri/Wayland IPC，坚决不依赖 Quickshell；
- [ ] **原生内置启动器、壁纸管理与 M3 调色引擎**：原生承载应用启动检索与壁纸管理；算法直出同构 `palette.toml`，在自研 Shell 模式下无需安装任何外部 Python GUI 伴生脚本；
- [ ] **原生兼容 Noctalia Template 系统 (TemplateAdapter)**：自研 Shell 原生支持 Noctalia 的 Jinja 风格模板规范与变量命名空间（`{{ colors.primary.default.hex }}`、`{{ colors.surface.default.hex }}` 等），现存的 GTK CSS、Fcitx SVG、Kitty、Starship 以及用户自定义模板资产**无需重写、零摩擦直接复用**；
- [ ] **Shell 生命周期与动作响应网关对接**：打通与 `session-shell.sh` 的守护拉起及 `shell-action.sh` 的 6 大标准动作（`launcher` / `session` / `settings` / `clipboard` / `lock` / `wallpaper-random`）IPC/CLI 接口，外围快捷键零改动即刻响应。

#### 3. 开发 Shell 后 (Post-Shell Ecosystem & Polish)
> **核心目标**：在自研 Shell 雏形落地后，完善双轨切换心流、终端美学跃迁、多合成器生态解耦与版本安全降级。

- [ ] **双 Shell 平滑自由切换 (`nyxniri shell set`)**：支持 `nyxniri shell set <noctalia|custom>` 或快捷键即时热插拔，无缝在 Noctalia 与自研 Shell 之间来回穿梭；
- [ ] **Noctalia + Wallpaper Picker 协同方案稳固验收**：验证 Noctalia 模式下伴生套件的按需部署与运行，确保双轨方案互不干扰、各自纯白；
- [ ] **TUI 视觉风格化与纯净感 (Terminal Rice)**：接入 Alternate Screen Buffer（`\033[?1049h/l`）保护终端历史（运行 `doctor` / 查看快照不被抹除），DEC 2025 协议消除高刷频闪撕裂，引入单行微动 Zen Spinner 就地收拢命令滚屏日志；
- [ ] **多合成器 (Multi-WM) 架构解耦与驱动抽象**：构建 `CompositorDriver` 驱动抽象层，实现热重载、浮动便签与屏幕探测的跨合成器适配（Hyprland/Sway 等按需扩展），`doctor` 诊断与 `greeter` 会话自适应；
- [ ] **安全 Downdate 体系（高级储备）**：落地基于现场快照优先还原与 Git 逆向检出的安全版本回退机制。


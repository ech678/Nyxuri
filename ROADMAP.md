# Nyxuri 活跃演进路线

> 本页只保留跨域活跃待办与长期目标；Shell 阶段台账、已确认决策与门禁见
> [shell/ROADMAP.md](shell/ROADMAP.md)。历史全景见
> [archive/roadmap-history](llms-wiki/archive/roadmap-history.md)；
> 设计哲学与五条简洁标准见 [vision](llms-wiki/vision.md)。

## 主线：插件市场化改造

> 当前未启动；前置：Shell P4 验收通过。
> 产品重定义：Nyxuri 从「安装器」收敛为「桌面插件市场」，安装器退役为一次性引导。
> 终态：内核（registry · resolver · transaction · ledger）+ 目录（万物皆单元）+
> 市场界面（TUI 目录浏览器为主，CLI 等价动词）。任何东西——config、模块、壁纸包、
> Shell 域——都是可独立开关的单元：off ↔ on 原子切换，切换前披露、切换后交报告，
> doctor 持续对账「声明 vs 实机」。术语全库统一四词：**单元 / 内核 / 源 / manifest**；
> pacman 与 AUR 包不是单元，是单元声明的依赖。

### 阶段台账

| 阶段 | 交付 | 状态 |
| --- | --- | --- |
| KM0 | 内核契约冻结（`llms-wiki/unit-model.md`） | 待开始 |
| KM1 | 内核落地：注册表与多源目录 | 待开始 |
| KM2 | 开关事务与知情披露 | 待开始 |
| KM3 | 市场主界面与 CLI 重设计 | 待开始 |
| KM4 | Shell 彻底模块化 + 市场直通运行态（吸收原 Shell P5） | 待开始 |
| KM5 | 引导转化、退役清单与五原则总验收 | 待开始 |

P6（整体验收与未来移植）保持在 KM5 之后，台账见 [shell/ROADMAP.md](shell/ROADMAP.md)。
KM0 完成前，下方阶段要点即契约草案；KM0 落地后契约上收 `llms-wiki/unit-model.md`
（届时创建并进 [llms.txt](llms-wiki/llms.txt) 索引），此处退回纯台账。

- **KM0 内核契约冻结**：单元状态机（off ↔ on；Shell 类单元另含宿主内运行态）；
  manifest schema v2 统一 `.module.toml` 与 `modules/` 代码约定，含 shell 类字段
  （UI 挂载点、capability 需求、宿主兼容声明）；多源模型（本仓库降格为默认源）；
  知情协议（pre / post 披露格式，外部源首次启用加严披露）；事务语义（快照绑定、
  失败回滚、`__custom__` 归档不删）；内核边界清单。验收：schema golden 与契约测试绿。
- **KM1 内核落地**：registry 惰性发现，未启用单元零 import；ledger 升级为单元状态
  账本；configs / modules / wallpapers / deps 全部 manifest 化进目录；多源添加与
  刷新。验收：新单元接入 = 加目录 + manifest、零内核改动（测试单元证明）；坏单元
  只降级自身，不拖垮目录。
- **KM2 开关事务**：per-unit 开关；依赖闭包披露与依赖关闭语义；doctor「声明 vs
  实机」审计。验收：任一单元独立开关零残留；未知文件容忍，缺可选依赖局部降级。
- **KM3 市场与 CLI**：TUI 目录浏览器（分类 / 搜索 / 详情 / 开关 / 事务历史）成为
  主界面；CLI 重设计为市场语义动词（列举 / 详情 / 开关 / 源管理 / 诊断），旧命令
  别名过渡；install / update 退役为市场操作组合。验收：operation-map 契约与双语
  文案全量改写，相关测试门禁绿。
- **KM4 Shell 彻底模块化 + 市场直通运行态**（吸收原 Shell P5）：Shell 内核（装配 /
  生命周期 / Action Gateway / IPC）零业务，一切功能域成模块；UI 挂载点契约、能力
  统一探测注入、启动闭包审计（未启用模块零实例化、零读文件）、一方与第三方同契约；
  部署 → IPC → 热加载链路；双 Shell 仲裁随宿主兼容声明收敛；原 P5 验收标准
  （六动作、部署契约接入、共享池中立化、双轨仲裁）平移，明细见
  [shell/ROADMAP.md](shell/ROADMAP.md)。验收记录归 shell 台账。
- **KM5 引导转化与退役**：install.sh → 市场引导（拉内核 → 进市场）；
  `engine_is_complete` 手工清单换版本探针；旧 CLI 别名与旧安装流程按退役清单逐项
  退役。完成条件：退役清单清空 + 五原则逐条可复现证据。

### 全局门禁（每阶段验收都过）

1. **单一开关真相**：市场 TUI、CLI、Shell 设置面板都是同一张开关的皮，翻转状态只走
   同一条事务路径落 ledger；Shell 运行态是投影，不持久化、不分叉。
2. **桥接零新通道**：市场 ↔ Shell 运行态通知只复用 Shell 既有 IPC（`nyxuri shell set`
   已验证的通道），不新增第二条。
3. **单元边界**：能力不设限，副作用必须声明——单元内部可管服务、写 `/etc`、装包，
   但一切外部效果必须写进 manifest；单元之间不许伸手，只走声明的依赖与显式契约。
   市场是知情系统，不是沙箱。
4. **退役清单制**：每个过渡物（CLI 别名、旧安装流程、`.module.toml` 兼容层、
   `engine_is_complete` 清单）登记名字与死刑阶段；清单不空，KM5 不算完成。
5. **五原则验收**：阶段收口按 [vision](llms-wiki/vision.md) 五条标准给出可复现证据
   （真诚透明 / 绝对主权 / 骨架包容 / 轻盈生长 / 通用自然）。

### KM0 必答设计题（只立题，不预设答案）

- 市场动词命名与语义槽位（enable / disable 还是 on / off；refresh 的边界）。
- 外部源信任模型底线：首启完整披露是底线；签名与信任分级入储备。
- 依赖关闭语义：阻断并列出依赖者，用户决策。
- `__custom__` 归档位置与恢复方式：零残留与可找回的平衡。
- preset 与单元的关系：折叠为 manifest variant，或书面证明正交，不许悬置。

### 储备（不承诺）

- 第三方源信任分级与签名。
- 多合成器、安全 Downdate 等长期储备沿「Shell 后生态」条目，市场化后以单元形态
  实施，不在两处重复展开。

## 自研 Shell（当前：P4 主题契约）

- 阶段台账与当前进度：见 [shell/ROADMAP.md](shell/ROADMAP.md)，此处不复述。
- [ ] **原生壁纸管理与 MD3 取色内生**：壁纸域自治之上取色引擎可插拔——短期经契约层走 matugen，长期以 material-color-utilities 纯 JS 移植替换并退役 matugen，直出色板契约、无外部取色二进制（P4 落契约、后置收口；启动器与壁纸域已在 R4-C 完成代码自治）。
- [x] **六大标准动作与双 Shell 切换**：`launcher` / `session` / `settings` / `clipboard` / `lock` / `wallpaper-random` 经 `shell-action.sh` 零改动响应；`nyxuri shell set` 热切换与异常安全回滚已交付（P1/P2，证据见 Shell 台账）。
- [ ] **Noctalia Template 兼容与主题契约 (TemplateAdapter)**：落地 palette JSON 色板契约与 Noctalia 模板规范（`{{ }}` 表达式、`<* *>` 块与过滤器）适配层，GTK CSS、Fcitx5、Kitty、Starship 和用户模板无需重写；深浅模式系统同步收敛到 `nyxuri theme` 单一实现；运行时不依赖 noctalia 二进制（P4 交付）。
- [ ] **Noctalia + Wallpaper Picker 协同稳固验收**：双轨方案互不干扰、各自纯白——原 P5 验收项，随 P5 吸收为主线 KM4 验收。

## Shell 后生态

- [ ] **TUI 视觉风格化与纯净感 (Terminal Rice)**：Alternate Screen Buffer 保护终端历史，DEC 2025 协议消除高刷频闪，单行微动 Zen Spinner 就地收拢滚屏日志。
- [ ] **多合成器 (Multi-WM) 架构解耦**：`CompositorDriver` 驱动抽象层，热重载、浮动便签与屏幕探测跨合成器适配（Hyprland/Sway 按需扩展），`doctor` 诊断与 `greeter` 会话自适应。
- [ ] **安全 Downdate 体系（高级储备）**：现场快照优先还原 + Git 逆向检出的安全版本回退。
